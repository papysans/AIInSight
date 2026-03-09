#!/Users/napstablook/.pyenv/versions/3.11.9/bin/python
"""
本地 headed 浏览器登录小红书，导出 cookies 并注入到 xhs-mcp。
用法: python scripts/xhs_login_local.py
"""
import asyncio
import json
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_OUTPUT = Path(__file__).resolve().parent.parent / "runtime" / "xhs" / "data" / "cookies.json"


def to_go_rod(cookies: list[dict]) -> list[dict]:
    result = []
    for c in cookies:
        result.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c["path"],
            "expires": c["expires"] if c["expires"] > 0 else -1,
            "size": len(c["name"]) + len(c["value"]),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "session": not (c["expires"] > 0),
            "priority": "Medium",
            "sameParty": False,
            "sourceScheme": "Secure" if c.get("secure") else "NonSecure",
            "sourcePort": 443 if c.get("secure") else 80,
        })
    return result


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = await context.new_page()
        await page.goto("https://www.xiaohongshu.com")

        print()
        print("=" * 50)
        print("请在弹出的浏览器中使用小红书 App 扫码登录")
        print("登录成功后（看到首页推荐内容），按 Enter 键继续...")
        print("=" * 50)
        print()

        input(">>> 按 Enter 继续 <<<")

        cookies = await context.cookies()
        ws = next((c for c in cookies if c["name"] == "web_session"), None)
        if not ws:
            print("❌ 未找到 web_session，可能登录未成功")
            await browser.close()
            return

        go_rod_cookies = to_go_rod(cookies)
        COOKIES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        COOKIES_OUTPUT.write_text(json.dumps(go_rod_cookies, ensure_ascii=False, indent=2))
        print(f"✅ 导出 {len(go_rod_cookies)} 个 cookies -> {COOKIES_OUTPUT}")
        await browser.close()

        print("\n现在请重启 xhs-mcp 容器加载新 cookies：")
        print("  docker restart aiinsight-xhs-mcp")


if __name__ == "__main__":
    asyncio.run(main())
