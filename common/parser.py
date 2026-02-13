"""
数据解析工具
============
- parse_api_records: 解析搜索 API 返回的 JSON
- parse_detail_html: 解析详情页 HTML（BeautifulSoup，不需要浏览器）
- clean_record:      清洗 API 记录为统一格式
"""

import json
import re

from bs4 import BeautifulSoup

from .config import BASE_URL


# ------------------------------------------------------------------
#  API 数据解析
# ------------------------------------------------------------------

def parse_api_records(api_data: dict) -> tuple[list[dict], int]:
    """解析 getFullTextDataNew 接口返回的 JSON

    Returns:
        (records, totalcount)
    """
    if api_data.get("code") != 200:
        print(f"  ❌ API 错误: code={api_data.get('code')} msg={api_data.get('msg', '')}")
        return [], 0

    content = api_data.get("content", "")
    if isinstance(content, str):
        content = json.loads(content)

    result = content.get("result", {})
    return result.get("records", []), result.get("totalcount", 0)


def clean_record(record: dict) -> dict:
    """清洗 API 返回的单条记录"""
    link = record.get("linkurl", "")
    return {
        "标题": record.get("title", "").strip(),
        "发布日期": record.get("pubinwebdate", ""),
        "业务类型": record.get("categorytype", ""),
        "区域": record.get("infoc", ""),
        "记录ID": record.get("newid", ""),
        "详情链接": f"{BASE_URL}{link}" if link else "",
    }


# ------------------------------------------------------------------
#  详情页 HTML 解析
# ------------------------------------------------------------------

def parse_detail_html(html: str) -> dict:
    """从服务端渲染的详情页 HTML 中提取结构化数据

    替代原来的 Playwright page.evaluate() 方案，
    使用 BeautifulSoup 纯 Python 解析，无需浏览器。
    """
    soup = BeautifulSoup(html, "lxml")
    result = {}

    # 1. 页面标题
    title_el = soup.select_one(".detail-title, .article-title, h2, h3")
    if title_el:
        result["页面标题"] = title_el.get_text(strip=True)

    # 2. 项目编号
    proj_el = soup.select_one(".detail-code, .project-code")
    if proj_el:
        text = proj_el.get_text(strip=True)
        result["项目编号"] = re.sub(r"^项目编号[：:]\s*", "", text)

    # 3. 信息时间
    body_text = soup.get_text()
    time_match = re.search(r"【信息时间[：:]?\s*(\d{4}[-/]\d{2}[-/]\d{2})", body_text)
    if time_match:
        result["信息时间"] = time_match.group(1)

    # 4. 表格 key-value
    for tr in soup.select("table tr"):
        cells = tr.select("td, th")
        if len(cells) == 2:
            key = re.sub(r"[：:]", "", cells[0].get_text(strip=True))
            val = cells[1].get_text(strip=True)
            if key and len(key) < 30:
                result[key] = val
        elif len(cells) >= 4 and len(cells) % 2 == 0:
            for i in range(0, len(cells), 2):
                key = re.sub(r"[：:]", "", cells[i].get_text(strip=True))
                val = cells[i + 1].get_text(strip=True)
                if key and len(key) < 30 and val:
                    result[key] = val

    # 5. 正文 "一、xxx：yyy" 格式
    content_el = soup.select_one(
        ".ewb-article-info, .article-content, .detail-content, .content-box"
    )
    if content_el:
        text = content_el.get_text()
        kv_pattern = re.compile(
            r"[一二三四五六七八九十\d]+[、.．]\s*([^：:]+)[：:]\s*([^\n]+)"
        )
        for m in kv_pattern.finditer(text):
            key = m.group(1).strip()
            val = m.group(2).strip()
            if key and len(key) < 30 and len(val) < 500 and key not in result:
                result[key] = val

    # 6. 正文全文（截断到 3000 字符）
    main_el = content_el or soup.select_one(
        ".ewb-article, .article, .main-content, main"
    )
    if main_el:
        result["正文内容"] = main_el.get_text(strip=True)[:3000]

    return result
