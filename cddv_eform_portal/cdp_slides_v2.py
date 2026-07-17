#!/usr/bin/env python3
"""CDP v2: Chup viewport Google Slides Presentation tu Chrome ca nhan"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"
# Use PRESENT mode URL - much cleaner for screenshots
PRESENT_URL = "https://docs.google.com/presentation/d/16krO55NhTLZN9nnrDbrUPUgWaLBOBHYsApJZHC1f1QI/present#slide=id.g3bca658d551_2_148"
OUTPUT_DIR = r"e:\GHN\AntiGravity\Khứa Hỗ Trợ\cddv_eform_portal\assets\criteria"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("CDP v2: Chup viewport Slides Presentation Mode")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]

        # Check existing tabs
        page = None
        for p_check in context.pages:
            if "16krO55NhTLZN9nnrDbrUPUgWaLBOBHYsApJZHC1f1QI" in p_check.url:
                page = p_check
                # Reload to present mode
                page.goto(PRESENT_URL, wait_until="domcontentloaded", timeout=30000)
                print(f"✓ Tab ton tai, reloaded to present mode")
                break

        if not page:
            page = context.new_page()
            page.goto(PRESENT_URL, wait_until="domcontentloaded", timeout=30000)
            print(f"± Da mo Present mode")

        page.bring_to_front()
        page.wait_for_timeout(5000)  # Wait for presentation to stabilize

        # Now just use PageDown to navigate through slides and screenshot viewport
        for i in range(25):  # Max 25 slides
            try:
                page.wait_for_timeout(1200)
                fname = f"tc_slide_{i:02d}.png"
                fpath = os.path.join(OUTPUT_DIR, fname)
                page.screenshot(path=fpath)
                print(f"   ✅ [{i+1}] {fname}")

                # Next slide
                page.keyboard.press("ArrowDown")
                page.wait_for_timeout(800)

            except Exception as e:
                print(f"   ⚠️ Slide {i}: {str(e)[:60]}")
                break

        print(f"\n≡ Done! Kiem tra {OUTPUT_DIR}")
        browser.close()

if __name__ == "__main__":
    main()
