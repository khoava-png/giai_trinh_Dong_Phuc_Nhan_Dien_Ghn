@echo off
chcp 65001 >nul
title GHN Tunnel - Dung tat cua so nay

:: --- Tai cloudflared neu chua co ---
set CF=%~dp0cloudflared.exe
if not exist "%CF%" (
    echo [..] Dang tai cloudflared, vui long cho ~30 giay...
    curl -L -o "%CF%" "https://github.com/cloudflare/cloudflared/releases/download/2026.8.3/cloudflared-windows-amd64.exe" --progress-bar 2>nul
    if not exist "%CF%" (
        echo [LOI] Tai that bai, kiem tra internet roi thu lai.
        pause
        exit /b 1
    )
    echo [OK] Da tai xong.
)

echo.
echo  =========================================
echo    GHN Tunnel - Control Center
echo    Dung tat cua so nay khi dang lam viec
echo  =========================================
echo.
echo  [..] Dang khoi dong tunnel...
echo  [..] Vui long cho URL hien ra ben duoi...
echo.

:: Chay tunnel - hien URL ra man hinh
"%CF%" tunnel --url http://localhost:8090 --no-autoupdate 2>&1

pause
