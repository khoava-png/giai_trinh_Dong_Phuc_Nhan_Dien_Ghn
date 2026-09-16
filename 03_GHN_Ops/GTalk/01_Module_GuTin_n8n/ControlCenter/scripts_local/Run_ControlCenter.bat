@echo off
chcp 65001 >nul
title Control Center - GTalk AM/QL Vung
cd /d "E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\ControlCenter"
echo ================================================
echo   CONTROL CENTER - GTalk AM / QL Vung
echo ================================================
echo   Mo Chrome tu dong http://localhost:8090
echo   BAM CTRL+C de tat server
echo ================================================
start "" http://localhost:8090
python control_center.py
pause >nul