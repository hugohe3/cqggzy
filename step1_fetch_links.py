"""
第一步：获取交易结果链接列表（优化版）
=========================================
架构：浏览器开门 + HTTP 干活

Phase 1: 用 Playwright 通过 JSL 验证，设置筛选条件，拦截 API 请求体，拿到 Cookie
Phase 2: 立即关闭浏览器，用 httpx 高速翻页获取所有链接

对比原版:
  - 浏览器仅用于 JSL 验证和拦截请求体，翻页全走 HTTP
  - 翻页速度提升 ~3x（无需浏览器渲染开销）
  - Cookie 自动保存，供 step2 复用

用法:
    python step1_fetch_links.py
    python step1_fetch_links.py -k "出租" -r "渝北区" -t "近一月"

参数:
    -k, --keyword       标题关键词 (默认: "")
    -r, --region        行政区域 (默认: "")
    -b, --biz-type      业务类型 (默认: "")
    -i, --info-type     信息类型 (默认: "交易结果")
    -t, --time-period   发布时间 (默认: "近三月")

输出:
    output/links.json
    output/cookies.json  (供 step2 复用)
"""

import argparse
import json
import os
import time

import httpx
from playwright.sync_api import sync_playwright

from common.config import (
    API_URL, PAGE_URL, OUTPUT_DIR, LINKS_FILE,
    DEFAULT_KEYWORD, DEFAULT_REGION, DEFAULT_BIZ_TYPE,
    DEFAULT_INFO_TYPE, DEFAULT_TIME_PERIOD,
    PAGE_SIZE, USER_AGENT, REQUEST_TIMEOUT,
)
from common.browser import (
    pass_jsl, create_browser_context,
    extract_cookies, save_cookies, smart_click,
)
from common.parser import parse_api_records, clean_record


def main():
    # ========== 参数解析 ==========
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

    print("=" * 60)
    print("📋 第一步：获取交易结果链接列表")
    print("=" * 60)
    print(f"关键词: {keyword or '全部'}")
    print(f"区域: {region or '全部'} | 业务: {biz_type or '全部'}")
    print(f"信息: {info_type} | 时间: {time_period}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ===================================================================
    #  Phase 1: 浏览器 — 过 JSL + 设置筛选 + 拦截请求体 + 拿 Cookie
    # ===================================================================
    print("\n🌐 Phase 1: 浏览器获取验证 Cookie 和 API 请求体...")

    captured_body = None
    cookies = None

    with sync_playwright() as p:
        browser, context = create_browser_context(p)
        page = context.new_page()

        # 1) 通过 JSL 反爬验证
        if not pass_jsl(page):
            browser.close()
            return

        # 2) 拦截 API 请求体
        def on_response(response):
            nonlocal captured_body
            if API_URL in response.url:
                try:
                    captured_body = json.loads(response.request.post_data)
                except Exception:
                    pass

        page.on("response", on_response)

        # 3) 通过 UI 设置筛选条件（触发第一次 API 请求）
        print("\n🔧 设置筛选条件...")
        if info_type:
            smart_click(page, info_type)
        if time_period:
            smart_click(page, time_period)
        if region:
            smart_click(page, region)
        if biz_type:
            smart_click(page, biz_type)

        # 4) 输入关键词搜索
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

        if not captured_body:
            print("  ❌ 未能拦截到 API 请求体，请检查网络")
            browser.close()
            return

        # 5) 提取 Cookie，立即关闭浏览器
        cookies = extract_cookies(context)
        save_cookies(cookies)
        browser.close()
        print("  ✅ 已获取 Cookie，浏览器已关闭\n")

    # ===================================================================
    #  Phase 2: HTTP 快速翻页
    # ===================================================================
    print(f"🚀 Phase 2: HTTP 快速翻页 (每页 {PAGE_SIZE} 条)...")

    captured_body["pn"] = 0
    captured_body["rn"] = PAGE_SIZE

    headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": USER_AGENT,
        "Referer": PAGE_URL,
    }

    with httpx.Client(cookies=cookies, headers=headers, timeout=REQUEST_TIMEOUT) as client:
        # 首页
        resp = client.post(API_URL, json=captured_body)
        records, total = parse_api_records(resp.json())

        if not records:
            print("  ❌ 无数据")
            return

        all_records = list(records)
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        print(f"  ✅ 总计 {total} 条, {total_pages} 页")

        # 翻页
        for pn in range(1, total_pages):
            captured_body["pn"] = pn
            try:
                resp = client.post(API_URL, json=captured_body)
                recs, _ = parse_api_records(resp.json())
                all_records.extend(recs)
                if (pn + 1) % 10 == 0 or pn == total_pages - 1:
                    print(f"    {pn + 1}/{total_pages} 页 (累计 {len(all_records)} 条)")
            except Exception as ex:
                print(f"    ❌ 第{pn + 1}页: {ex}")
                break
            time.sleep(0.1)  # 轻量间隔，HTTP 无需长等待

    # ===================================================================
    #  保存结果
    # ===================================================================
    links = [clean_record(r) for r in all_records]

    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存 {len(links)} 条链接 → {LINKS_FILE}")

    # 统计业务类型分布
    cats = {}
    for r in links:
        k = r["业务类型"] or "未知"
        cats[k] = cats.get(k, 0) + 1
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v} 条")

    print(f"\n{'=' * 60}")
    print("✅ 第一步完成! 接下来运行: python step2_scrape_details.py")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
