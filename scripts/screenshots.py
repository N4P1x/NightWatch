#!/usr/bin/env python3
"""Take screenshots of NightWatch platform pages."""
import asyncio
import urllib.request
import urllib.parse
import json
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:3000"
API_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = "/home/n4p1/NightWatch/media"


async def take_screenshots():
    # First, get a token via the API
    print("[*] Getting auth token via API...")
    data = urllib.parse.urlencode({"username": "admin", "password": "testpass123"}).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/v1/auth/login",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read())["access_token"]
        print(f"[+] Token: {token[:20]}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )

        page = await context.new_page()

        # Visit app to establish origin, then set token
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await page.evaluate(f"localStorage.setItem('token', '{token}')")
        print("[+] Auth token set in localStorage")

        # ============ 1. Dashboard ============
        print("[1/9] Dashboard...")
        await page.goto(f"{BASE_URL}/", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        # Check if still on login
        current = page.url
        print(f"    Current URL: {current}")
        await page.screenshot(path=f"{OUTPUT_DIR}/dashboard.png", full_page=True)
        print("    -> dashboard.png")

        # ============ 2. Leaks ============
        print("[2/9] Leaks...")
        await page.goto(f"{BASE_URL}/leaks", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        print(f"    Current URL: {page.url}")
        await page.screenshot(path=f"{OUTPUT_DIR}/leaks.png", full_page=True)
        print("    -> leaks.png")

        # ============ 3. Threat Actors ============
        print("[3/9] Threat Actors...")
        await page.goto(f"{BASE_URL}/actors", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        print(f"    Current URL: {page.url}")
        await page.screenshot(path=f"{OUTPUT_DIR}/threat-actors.png", full_page=True)
        print("    -> threat-actors.png")

        # ============ 4. IOCs ============
        print("[4/9] IOCs...")
        await page.goto(f"{BASE_URL}/iocs", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        print(f"    Current URL: {page.url}")
        await page.screenshot(path=f"{OUTPUT_DIR}/iocs.png", full_page=True)
        print("    -> iocs.png")

        # ============ 5. Sources ============
        print("[5/9] Sources...")
        await page.goto(f"{BASE_URL}/sources", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        print(f"    Current URL: {page.url}")
        await page.screenshot(path=f"{OUTPUT_DIR}/sources.png", full_page=True)
        print("    -> sources.png")

        # ============ 6. Alerts ============
        print("[6/9] Alerts...")
        await page.goto(f"{BASE_URL}/alerts", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        print(f"    Current URL: {page.url}")
        await page.screenshot(path=f"{OUTPUT_DIR}/alerts.png", full_page=True)
        print("    -> alerts.png")

        # ============ 7. Settings ============
        print("[7/9] Settings...")
        await page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        print(f"    Current URL: {page.url}")
        await page.screenshot(path=f"{OUTPUT_DIR}/settings.png", full_page=True)
        print("    -> settings.png")

        # ============ 8. Login page (without token) ============
        print("[8/9] Login page...")
        await page.evaluate("localStorage.removeItem('token')")
        await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{OUTPUT_DIR}/login.png", full_page=True)
        print("    -> login.png")

        # ============ 9. API Docs ============
        print("[9/9] API Docs...")
        await page.goto(f"{API_URL}/docs", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{OUTPUT_DIR}/api-docs.png", full_page=True)
        print("    -> api-docs.png")

        await browser.close()
        print("\n[+] All screenshots saved to media/")

if __name__ == "__main__":
    asyncio.run(take_screenshots())
