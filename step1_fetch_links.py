"""
第一步：获取交易结果链接列表
===============================
本脚本使用 Playwright 模拟浏览器操作，绕过 JSL 反爬保护，
通过页面 UI 设置筛选条件后，拦截 API 请求，翻页获取所有符合条件的链接。

用法示例:
    # 使用默认配置 (关键词="", 区域=全部, 业务=全部, 信息=交易结果, 时间=近三月)
    python step1_fetch_links.py

    # 自定义筛选
    python step1_fetch_links.py -k "出租" -r "渝北区" -t "近一月" -b "中介超市" -i "招选公告"

参数说明:
    -k, --keyword       标题关键词 (默认: "")
    -r, --region        行政区域 (默认: "")
    -b, --biz-type      业务类型 (默认: "")
    -i, --info-type     信息类型 (默认: "交易结果")
    -t, --time-period   发布时间 (默认: "近三月")

输出:
    output/links.json
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# ============ 配置 ============
API_URL = "https://www.cqggzy.com/inteligentsearch/rest/esinteligentsearch/getFullTextDataNew"
PAGE_URL = "https://www.cqggzy.com/jyxx/transaction_detail.html"
BASE_URL = "https://www.cqggzy.com"
OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "links.json")
DEFAULT_KEYWORD = ""
DEFAULT_REGION = ""  # 默认无区域限制
DEFAULT_BIZ_TYPE = ""  # 默认无业务类型限制
DEFAULT_INFO_TYPE = "交易结果"  # 默认信息类型
DEFAULT_TIME_PERIOD = "近三月"  # 默认时间范围
PAGE_SIZE = 20  # 每页条数
# ==============================


def get_time_range():
    now = datetime.now()
    start = now - timedelta(days=90)
    return start.strftime("%Y-%m-%d 00:00:00"), now.strftime("%Y-%m-%d 23:59:59")


def parse_records(api_data: dict) -> tuple[list[dict], int]:
    if api_data.get("code") != 200:
        print(f"  ❌ API 错误: code={api_data.get('code')} msg={api_data.get('msg', '')}")
        return [], 0
    content = api_data.get("content", "")
    if isinstance(content, str):
        content = json.loads(content)
    result = content.get("result", {})
    return result.get("records", []), result.get("totalcount", 0)


def clean_record(record: dict) -> dict:
    link = record.get("linkurl", "")
    return {
        "标题": record.get("title", "").strip(),
        "发布日期": record.get("pubinwebdate", ""),
        "业务类型": record.get("categorytype", ""),
        "区域": record.get("infoc", ""),
        "记录ID": record.get("newid", ""),
        "详情链接": f"{BASE_URL}{link}" if link else "",
    }


def pass_jsl(page) -> bool:
    """通过 JSL 反爬验证"""
    print("🔑 通过 JSL 反爬验证...")
    page.goto(PAGE_URL, wait_until="commit", timeout=30000)
    for i in range(15):
        time.sleep(2)
        try:
            title = page.title()
            if "公共资源" in title or "交易" in title:
                print(f"  ✅ 验证通过! ({(i + 1) * 2}s)")
                return True
        except Exception:
            continue
    print("  ⚠ 验证超时")
    return False


FETCH_SCRIPT = """
async (params) => {
    const resp = await fetch(params.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params.body),
    });
    return await resp.json();
}
"""



def smart_click(page, text, timeout=2000):
    """尝试点击文本对应的元素"""
    if not text:
        return
    try:
        # 针对不同类型的筛选项尝试定位
        # 1. 尝试直接文本匹配的 label-item
        loc = page.locator(f"a.label-item:has-text('{text}')").first
        if loc.count() > 0:
            if "active" not in (loc.get_attribute("class") or ""):
                loc.click()
                time.sleep(1.5)
            print(f"  ✅ 已选中: {text}")
            return
        
        # 2. 尝试包含文本的链接
        loc = page.locator(f"a:has-text('{text}')").first
        if loc.count() > 0:
            loc.click()
            time.sleep(1.5)
            print(f"  ✅ 已点击: {text}")
            return

        print(f"  ⚠ 未找到筛选项: {text}")
    except Exception as e:
        print(f"  ❌ 点击失败 {text}: {e}")


def main():
    parser = argparse.ArgumentParser(description="抓取交易结果链接")
    parser.add_argument("-k", "--keyword", default=DEFAULT_KEYWORD, help="标题关键词 (默认: 全部)")
    parser.add_argument("-r", "--region", default=DEFAULT_REGION, help="行政区域 (默认: 全部)")
    parser.add_argument("-b", "--biz-type", default=DEFAULT_BIZ_TYPE, help="业务类型 (默认: 全部)")
    parser.add_argument("-i", "--info-type", default=DEFAULT_INFO_TYPE, help=f"信息类型 (默认: {DEFAULT_INFO_TYPE})")
    parser.add_argument("-t", "--time-period", default=DEFAULT_TIME_PERIOD, help=f"发布时间 (默认: {DEFAULT_TIME_PERIOD})")

    args = parser.parse_args()

    keyword = args.keyword.strip()
    region = args.region.strip()
    biz_type = args.biz_type.strip()
    info_type = args.info_type.strip()
    time_period = args.time_period.strip()

    s, e = get_time_range()
    print("=" * 60)
    print("📋 第一步：获取交易结果链接列表")
    print("=" * 60)
    print(f"关键词: {keyword if keyword else '全部'}")
    print(f"区域: {region if region else '全部'} | 业务: {biz_type if biz_type else '全部'}")
    print(f"信息: {info_type} | 时间: {time_period}")
    print(f"时间范围: {s[:10]} ~ {e[:10]}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # 1. 通过 JSL
        if not pass_jsl(page):
            browser.close()
            return

        # 2. 拦截 API 获取正确的请求体
        print("\n🔧 设置筛选条件...")
        captured_body = None

        def on_response(response):
            nonlocal captured_body
            if API_URL in response.url:
                try:
                    captured_body = json.loads(response.request.post_data)
                except Exception:
                    pass

        page.on("response", on_response)

        # 点击信息类型 (如: 交易结果)
        if info_type:
            smart_click(page, info_type)

        # 点击发布时间 (如: 近三月)
        if time_period:
            smart_click(page, time_period)
            
        # 点击行政区域
        if region:
            smart_click(page, region)

        # 点击业务类型
        if biz_type:
            smart_click(page, biz_type)

        # 输入关键词搜索
        try:
            inp = page.locator("input#search, input.input-box").first
            inp.clear()
            inp.fill(keyword)
            inp.press("Enter")
            time.sleep(3)
            print(f"  ✅ 已搜索: {keyword}")
        except Exception:
            print("  ⚠ 搜索框未找到")

        time.sleep(2)

        # 3. 使用拦截到的请求体翻页获取数据
        if not captured_body:
            print("  ❌ 未能拦截到 API 请求体")
            browser.close()
            return

        print(f"\n📊 开始获取链接 (每页 {PAGE_SIZE} 条)...")
        captured_body["pn"] = 0
        captured_body["rn"] = PAGE_SIZE

        resp = page.evaluate(FETCH_SCRIPT, {"url": API_URL, "body": captured_body})
        records, total = parse_records(resp)

        if not records:
            print("  ❌ 无数据")
            browser.close()
            return

        all_records = list(records)
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        print(f"  ✅ 总计 {total} 条, {total_pages} 页")

        for pn in range(1, total_pages):
            captured_body["pn"] = pn
            try:
                resp = page.evaluate(FETCH_SCRIPT, {"url": API_URL, "body": captured_body})
                recs, _ = parse_records(resp)
                all_records.extend(recs)
                if (pn + 1) % 10 == 0 or pn == total_pages - 1:
                    print(f"    {pn + 1}/{total_pages} 页 (累计 {len(all_records)} 条)")
            except Exception as ex:
                print(f"    ❌ 第{pn + 1}页: {ex}")
                break
            time.sleep(0.3)

        browser.close()

    # 清洗并保存
    links = [clean_record(r) for r in all_records]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存 {len(links)} 条链接 → {OUTPUT_FILE}")
    cats = {}
    for r in links:
        k = r["业务类型"] or "未知"
        cats[k] = cats.get(k, 0) + 1
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v} 条")
    print(f"\n{'=' * 60}")
    print(f"✅ 第一步完成! 接下来运行: python step2_scrape_details.py")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
