@echo off
chcp 65001 >nul
title GTalk Sender
cd /d "E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\GuTin_Theo_MaNV"
echo ==========================================
echo   GTALK - SEND MESSAGES BY EMPLOYEE CODE
echo ==========================================
echo.
python gtalk_bulk_sender.py
echo.
echo ==========================================
echo   DONE! Press any key to close.
echo ==========================================
pause >nul