@echo off
chcp 65001 >nul
title Cao Ton Phieu - Auto Update Sheet (Day Du + Loai + Trang Thai)
cd /d "E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\Cao_Ton_Phieu"
echo ==================================================
echo   CAO TAT CA BUU CUC - LOAI PHIEU + TRANG THAI
echo ==================================================
echo.
echo  B1: Login web van hanh + scrape ALL bưu cục (theo từng loại Hối giao/lấy/trả)
echo  B2: Ghi Loai phieu + Trang thai vao Google Sheet
echo.
python cao_ton_phieu.py --v2
echo.
echo ==================================================
echo   DONE! Press any key to close.
echo ==================================================
pause >nul