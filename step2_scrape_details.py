"""
第二步：抓取详情页数据
========================
本脚本读取 `output/links.json` 中的链接列表，逐个访问详情页，
提取页面中的结构化数据（表格、键值对、正文等）。

用法:
    python step2_scrape_details.py

功能特性:
    1. **断点续传**: 自动记录已抓取的记录 ID 到 `output/progress.json`。
       如果脚本中断，再次运行会自动跳过已完成的记录。
    2. **自动重试**: 遇到网络错误或反爬验证时会自动重试。
    3. **JSL 绕过**: 启动时自动通过 JSL 验证。

输出:
    - output/details.csv (Excel 可打开)
    - output/details.json (原始数据)
"""

import json
import csv
import os
import re
import time
from playwright.sync_api import sync_playwright

# ============ 配置 ============
PAGE_URL = "https://www.cqggzy.com/jyxx/transaction_detail.html"
INPUT_FILE = "output/links.json"
OUTPUT_CSV = "output/details.csv"
OUTPUT_JSON = "output/details.json"
PROGRESS_FILE = "output/progress.json"
BATCH_SIZE = 10  # 每 N 条保存一次进度
# ==============================


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "details": []}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def extract_detail_data(page) -> dict:
    """从详情页 DOM 提取所有结构化数据"""
    return page.evaluate(r"""
    () => {
        const result = {};

        // 1. 页面标题
        const h2 = document.querySelector('.detail-title, .article-title, h2, h3');
        if (h2) result['页面标题'] = h2.textContent.trim();

        // 2. 项目编号
        const projNum = document.querySelector('.detail-code, .project-code');
        if (projNum) result['项目编号'] = projNum.textContent.replace(/项目编号[：:]\s*/, '').trim();

        // 3. 信息时间
        const bodyText = document.body.innerText;
        const timeMatch = bodyText.match(/【信息时间[：:]?\s*(\d{4}[-/]\d{2}[-/]\d{2})/);
        if (timeMatch) result['信息时间'] = timeMatch[1];

        // 4. 表格 key-value
        document.querySelectorAll('table tr').forEach(tr => {
            const cells = Array.from(tr.querySelectorAll('td, th'));
            if (cells.length === 2) {
                const key = cells[0].textContent.trim().replace(/[：:]/g, '');
                const val = cells[1].textContent.trim();
                if (key && key.length < 30) result[key] = val;
            } else if (cells.length >= 4 && cells.length % 2 === 0) {
                for (let i = 0; i < cells.length; i += 2) {
                    const key = cells[i].textContent.trim().replace(/[：:]/g, '');
                    const val = cells[i+1].textContent.trim();
                    if (key && key.length < 30 && val) result[key] = val;
                }
            }
        });

        // 5. 正文 "一、xxx：yyy" 格式
        const contentEl = document.querySelector('.ewb-article-info, .article-content, .detail-content, .content-box');
        if (contentEl) {
            const text = contentEl.innerText;
            const kvPattern = /[一二三四五六七八九十\d]+[、.．]\s*([^：:]+)[：:]\s*([^\n]+)/g;
            let m;
            while ((m = kvPattern.exec(text)) !== null) {
                const key = m[1].trim();
                const val = m[2].trim();
                if (key.length < 30 && val.length < 500 && !result[key]) result[key] = val;
            }
        }

        // 6. 正文全文
        const main = contentEl || document.querySelector('.ewb-article, .article, .main-content, main');
        if (main) result['正文内容'] = main.innerText.trim().substring(0, 3000);

        return result;
    }
    """)


def save_csv(details: list[dict]):
    """保存为 UTF-8 BOM 编码的 CSV"""
    if not details:
        return
    base = ["序号", "标题", "发布日期", "业务类型", "区域", "详情链接"]
    extra = set()
    for d in details:
        for k in d.keys():
            if k not in base:
                extra.add(k)
    extra_sorted = sorted(extra - {"正文内容", "错误"})
    if "错误" in extra:
        extra_sorted.append("错误")
    if "正文内容" in extra:
        extra_sorted.append("正文内容")
    all_fields = base + extra_sorted

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(details)
    print(f"💾 CSV → {OUTPUT_CSV} ({len(details)} 条, {len(all_fields)} 列)")


def main():
    print("=" * 60)
    print("📄 第二步：抓取详情页数据")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        print(f"❌ 未找到 {INPUT_FILE}，请先运行 step1_fetch_links.py")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"📄 加载 {len(records)} 条链接")

    progress = load_progress()
    completed_ids = set(progress["completed"])
    all_details = progress["details"]
    print(f"📊 已完成: {len(completed_ids)} 条")

    pending = [(i, r) for i, r in enumerate(records) if r["记录ID"] not in completed_ids]
    print(f"⏳ 待处理: {len(pending)} 条")

    if not pending:
        print("✅ 全部已完成!")
        save_csv(all_details)
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # 通过 JSL 验证
        print("\n🔑 通过 JSL 反爬验证...")
        page.goto(PAGE_URL, wait_until="commit", timeout=30000)
        for i in range(15):
            time.sleep(2)
            try:
                title = page.title()
                if "公共资源" in title or "交易" in title:
                    print(f"  ✅ 验证通过! ({(i + 1) * 2}s)")
                    break
            except Exception:
                continue
        else:
            print("  ⚠ 验证超时, 继续...")
        time.sleep(2)

        # 逐条抓取
        error_count = 0
        for idx, (orig_idx, record) in enumerate(pending):
            rid = record["记录ID"]
            title = record["标题"][:40]
            url = record["详情链接"]
            pct = (orig_idx + 1) / len(records) * 100

            print(f"\n[{orig_idx + 1}/{len(records)}] ({pct:.1f}%) {title}...")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(1.5)
                detail = extract_detail_data(page)

                merged = {
                    "序号": len(completed_ids) + idx + 1,
                    "标题": record["标题"],
                    "发布日期": record["发布日期"],
                    "业务类型": record["业务类型"],
                    "区域": record["区域"],
                    "详情链接": url,
                }
                merged.update(detail)
                all_details.append(merged)
                completed_ids.add(rid)
                progress["completed"].append(rid)
                error_count = 0

                keys = [k for k in detail if k != "正文内容"]
                print(f"  ✅ {len(keys)} 个字段: {', '.join(keys[:5])}")

            except Exception as e:
                error_count += 1
                print(f"  ❌ {e}")
                all_details.append({
                    "序号": len(completed_ids) + idx + 1,
                    "标题": record["标题"],
                    "发布日期": record["发布日期"],
                    "业务类型": record["业务类型"],
                    "区域": record["区域"],
                    "详情链接": url,
                    "错误": str(e),
                })
                completed_ids.add(rid)
                progress["completed"].append(rid)

                if error_count >= 5:
                    print("  ⚠ 连续错误, 重新验证...")
                    try:
                        page.goto(PAGE_URL, wait_until="commit", timeout=30000)
                        time.sleep(5)
                        error_count = 0
                    except Exception:
                        pass

            if (idx + 1) % BATCH_SIZE == 0:
                progress["details"] = all_details
                save_progress(progress)
                print(f"  💾 进度已保存 ({len(completed_ids)} 条)")

            time.sleep(0.5)

        browser.close()

    # 最终保存
    progress["details"] = all_details
    save_progress(progress)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON → {OUTPUT_JSON}")

    save_csv(all_details)

    cats = {}
    for c in all_details:
        k = c.get("业务类型") or "未知"
        cats[k] = cats.get(k, 0) + 1
    print(f"\n📊 业务类型分布:")
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v} 条")

    print(f"\n{'=' * 60}")
    print(f"✅ 第二步完成! 共 {len(all_details)} 条详情")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
