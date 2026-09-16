@echo off
chcp 65001 >nul
title GTalk DryRun
cd /d "E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\GuTin_Theo_MaNV"
echo DRY-RUN MODE - WILL NOT SEND ANY REAL MESSAGE
python gtalk_bulk_sender.py --dry-run
echo.
echo DONE! Press any key to close.
pause >nul