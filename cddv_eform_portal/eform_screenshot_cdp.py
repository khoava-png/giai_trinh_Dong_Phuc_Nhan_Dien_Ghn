#!/usr/bin/env python3
"""CDP Screenshot: Chup 4 loai EForm tu Chrome ca nhan cua GHN"""

import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"
OUTPUT_DIR = r"e:\GHN\AntiGravity\Khứa Hỗ Trợ\cddv_eform_portal\assets\screenshots"

# 4 EForm targets
EFORM_TARGETS = [
    {
        "name": "eform_hang_tuan",
        "url": "https://noibo.ghn.vn/eform/form/create?flowId=6a058c7b0f879cdfe070e687",
        "title": "EForm [HANG TUAN]"
    },
    {
        "name": "eform_quan_ly",
        "url": "https://noibo.ghn.vn/eform/form/create?flowId=6a599687d9bea4bea0d3fb39",
        "title": "EForm [CAP QUAN LY]"
    },
    {
        "name": "pl_hang_tuan",
        "url": "https://noibo.ghn.vn/eform/form/create?flowId=6a06c78b89813c378cacc25e",
        "title": "EForm [PL HANG TUAN - Khac Phuc]"
    },
    {
        "name": "pl_camera",
        "url": "https://noibo.ghn.vn/eform/form/create?flowId=69d371b7af6a207f9ca7ce12",
        "title": "EForm [PL CAMERA - Khac Phuc]"
    },
]

def screenshot_eform(page, target):
    """Navigate to EForm URL and take full page screenshot"""
    name = target["name"]
    url = target["url"]
    print(f"\n📸 [{name}] Dang mo: {url}")
    
    # Navigate
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)  # Extra wait for SPA render
    
    # Take full page screenshot
    output_path = os.path.join(OUTPUT_DIR, f"{name}.png")
    page.screenshot(path=output_path, full_page=True)
    print(f"   ✅ Da luu: {output_path}")
    return output_path

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("CDDV EFORM SCREENSHOT TOOL - CDP Mode")
    print("=" * 60)
    
    with sync_playwright() as p:
        # Connect to Chrome CDP
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        
        # Use a single new page for all screenshots
        page = context.new_page()
        
        for target in EFORM_TARGETS:
            try:
                screenshot_eform(page, target)
            except Exception as e:
                print(f"   ❌ Loi: {e}")
        
        # Close page and CDP connection
        page.close()
        browser.close()
    
    print(f"\n{'='*60}")
    print("✅ HOAN TAT! Anh da duoc luu vao:")
    for t in EFORM_TARGETS:
        p = os.path.join(OUTPUT_DIR, f"{t['name']}.png")
        if os.path.exists(p):
            size = os.path.getsize(p)
            print(f"   📄 {t['name']}.png ({size} bytes)")
    print("=" * 60)

if __name__ == "__main__":
    main()
