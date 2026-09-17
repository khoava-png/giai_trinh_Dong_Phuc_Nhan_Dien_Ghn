
import asyncio
from playwright.async_api import async_playwright
import subprocess
import time
import sys
import os

async def main():
    repo_dir = r"E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\ControlCenter"
    proc = subprocess.Popen([sys.executable, "control_center.py"], cwd=repo_dir, env={**os.environ, "PORT": "8104"})
    time.sleep(3)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto("http://localhost:8104/")
        await page.wait_for_load_state("networkidle")
        
        # Take screenshot of landing page
        os.makedirs(r"E:\GHN\AntiGravity\Khua_Ho_Tro\workspace\screenshots", exist_ok=True)
        path1 = r"E:\GHN\AntiGravity\Khua_Ho_Tro\workspace\screenshots\landing_page.png"
        await page.screenshot(path=path1)
        
        # Click login button to enter cockpit
        await page.click("#loginBtn")
        await page.wait_for_timeout(1000)
        
        # Take screenshot of cockpit with Audit Log table
        path2 = r"E:\GHN\AntiGravity\Khua_Ho_Tro\workspace\screenshots\cockpit_audit_log.png"
        await page.screenshot(path=path2)
        
        await browser.close()
        proc.terminate()
        proc.wait()
        print("SCREENSHOTS_CAPTURED_SUCCESSFULLY")

asyncio.run(main())
