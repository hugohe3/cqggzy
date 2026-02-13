"""
浏览器工具
=========
只在"过 JSL 验证"和"拦截 API 请求体"时使用浏览器，
拿到 Cookie 后立即关闭，后续全部走 HTTP。
"""

import json
import os
import time

from playwright.sync_api import sync_playwright

from .config import PAGE_URL, COOKIES_FILE, USER_AGENT, OUTPUT_DIR


# ------------------------------------------------------------------
#  JSL 验证
# ------------------------------------------------------------------

def pass_jsl(page) -> bool:
    """通过 JSL 反爬验证（加速乐 JS Challenge）"""
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


# ------------------------------------------------------------------
#  浏览器 Context 工厂
# ------------------------------------------------------------------

def create_browser_context(playwright):
    """创建统一配置的浏览器 context"""
    browser = playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent=USER_AGENT,
        locale="zh-CN",
        viewport={"width": 1280, "height": 800},
    )
    return browser, context


# ------------------------------------------------------------------
#  Cookie 管理
# ------------------------------------------------------------------

def extract_cookies(context) -> dict:
    """从浏览器 context 提取 cookies 为 {name: value} 字典"""
    return {c["name"]: c["value"] for c in context.cookies()}


def save_cookies(cookies: dict):
    """持久化 cookies 到文件，供 step2 复用"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f)


def load_cookies() -> dict | None:
    """从文件加载 cookies"""
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ------------------------------------------------------------------
#  UI 交互
# ------------------------------------------------------------------

def smart_click(page, text: str):
    """尝试点击页面上文本匹配的筛选按钮"""
    if not text:
        return
    try:
        # 优先匹配 label-item 类型的筛选标签
        loc = page.locator(f"a.label-item:has-text('{text}')").first
        if loc.count() > 0:
            if "active" not in (loc.get_attribute("class") or ""):
                loc.click()
                time.sleep(1.5)
            print(f"  ✅ 已选中: {text}")
            return

        # 退化到任意 <a> 标签
        loc = page.locator(f"a:has-text('{text}')").first
        if loc.count() > 0:
            loc.click()
            time.sleep(1.5)
            print(f"  ✅ 已点击: {text}")
            return

        print(f"  ⚠ 未找到筛选项: {text}")
    except Exception as e:
        print(f"  ❌ 点击失败 {text}: {e}")
