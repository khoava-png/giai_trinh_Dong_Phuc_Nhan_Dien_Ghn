#!/usr/bin/env python3
"""CDP: Chup anh 12 tieu chi tu Google Slides GHN CDDV"""

import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"
SLIDES_URL = "https://docs.google.com/presentation/d/16krO55NhTLZN9nnrDbrUPUgWaLBOBHYsApJZHC1f1QI/edit#slide=id.g3bca658d551_2_148"
OUTPUT_DIR = r"e:\GHN\AntiGravity\Khứa Hỗ Trợ\cddv_eform_portal\assets\criteria"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("CDP: Chup 12 tieu chi tu Google Slides GHN CDDV")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        
        # Check if slides already open
        page = None
        for p_check in context.pages:
            if "16krO55NhTLZN9nnrDbrUPUgWaLBOBHYsApJZHC1f1QI" in p_check.url:
                page = p_check
                print(f"✓ Da tim thay tab Google Slides: {p_check.title()}")
                break
        
        if not page:
            page = context.new_page()
            print(f"± Dang mo Google Slides...")
            # Use domcontentloaded instead of networkidle to avoid timeout on Google Slides
            page.goto(SLIDES_URL, wait_until="domcontentloaded", timeout=30000)
            # Wait extra for the presentation engine to initialize
            page.wait_for_timeout(8000)
        
        page.bring_to_front()
        page.wait_for_timeout(2000)

        # Try clicking "Present" button or use full-screen view
        # Google Slides filmstrip has clickable thumbnails
        print("± Tim kiem filmstrip thumbnails...")
        
        # Get all thumbnails
        thumbs = page.locator('[data-slide-id]').all()
        if len(thumbs) == 0:
            thumbs = page.locator('[id*="filmstrip"] [role="button"]').all()
        
        thumb_count = len(thumbs)
        print(f"± Phat hien {thumb_count} thumbnails")

        screenshot_count = 0
        
        # Try clicking each thumbnail and screenshot
        for i, thumb in enumerate(thumbs):
            try:
                # Scroll thumbnail into view then click
                thumb.scroll_into_view_if_needed()
                thumb.click()
                page.wait_for_timeout(2000)
                
                # Screenshot the main slide canvas
                slide_container = page.locator('[class*="punch-viewer-content"]').first
                if slide_container.count() == 0:
                    slide_container = page.locator('svg').first
                
                if slide_container.count() > 0:
                    fname = f"tc_slide_{screenshot_count:02d}.png"
                    fpath = os.path.join(OUTPUT_DIR, fname)
                    slide_container.screenshot(path=fpath)
                    screenshot_count += 1
                    print(f"   ✅ [{screenshot_count}] Da chup: {fname}")
                else:
                    print(f"   ⚠️ Thumb {i}: Khong tim thay slide canvas")
                    
            except Exception as e:
                print(f"   ⚠️ Loi thumb {i}: {str(e)[:80]}")
        
        print(f"\n≡ Tong cong: {screenshot_count} slide da chup xong!")
        browser.close()

if __name__ == "__main__":
    main()
