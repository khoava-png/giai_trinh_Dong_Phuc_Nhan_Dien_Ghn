#!/usr/bin/env python3
"""CDP v3: Chup man hinh viewport khi nhan PageDown tren Google Slides tab co san"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"
OUTPUT_DIR = r"e:\GHN\AntiGravity\Khứa Hỗ Trợ\cddv_eform_portal\assets\criteria"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("CDP v3: Screenshot viewport on PageDown in Google Slides")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]

        # Find the slides tab (currently open)
        page = None
        for p_check in context.pages:
            if "16krO55NhTLZN9nnrDbrUPUgWaLBOBHYsApJZHC1f1QI" in p_check.url:
                page = p_check
                break

        if not page:
            print("❌ Khong tim thay tab Google Slides!")
            browser.close()
            return

        page.bring_to_front()
        page.wait_for_timeout(2000)
        
        # Maximize viewport for best screenshot quality
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.wait_for_timeout(1000)

        # Click on the main canvas to focus it (so keyboard events work)
        # Try clicking center of the page
        page.mouse.click(960, 400)
        page.wait_for_timeout(1000)

        for i in range(25):
            try:
                # Simple viewport screenshot
                fname = f"tc_slide_{i:02d}.png"
                fpath = os.path.join(OUTPUT_DIR, fname)
                page.screenshot(path=fpath)
                print(f"   ✅ [{i+1}] {fname}")

                # Next slide
                page.keyboard.press("PageDown")
                page.wait_for_timeout(1500)

            except Exception as e:
                print(f"   ⚠️ Slide {i}: {str(e)[:60]}")
                break

        print(f"\n≡ Xong! Kiem tra: {OUTPUT_DIR}")
        browser.close()

if __name__ == "__main__":
    main()
