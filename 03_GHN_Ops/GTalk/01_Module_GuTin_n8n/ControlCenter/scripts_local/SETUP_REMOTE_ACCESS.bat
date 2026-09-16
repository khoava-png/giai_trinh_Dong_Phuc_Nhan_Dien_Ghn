@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title SETUP REMOTE ACCESS - Control Center GTalk

:: ============================================================
::  SETUP_REMOTE_ACCESS.bat
::  Tac gia: Khoa Va (GHN)
::  Muc tieu: Cho phep quan tri Control Center tu laptop,
::             khong phu thuoc vao nguoi dung may PC nay.
::
::  Script nay lam 3 viec:
::    [A] Cai cloudflared -> tao tunnel ra internet (Web UI)
::    [B] Cai NSSM -> dang ky control_center.py la Windows Service
::    [C] Dang ky cloudflared la Windows Service
::
::  Ket qua: ca 2 thu tu khoi dong khi may bat,
::           khong can login, khong can ai giu terminal.
:: ============================================================

echo.
echo  =====================================================
echo    SETUP REMOTE ACCESS - Control Center GTalk
echo  =====================================================
echo.

:: --- Kiem tra quyen Admin ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  [LOI] Chua co quyen Administrator!
    echo        Chuot phai file nay ^-^> Run as Administrator
    echo.
    pause
    exit /b 1
)
echo  [OK] Dang chay voi quyen Administrator

:: --- Cau hinh duong dan ---
set PROJECT_DIR=E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\ControlCenter
set PYTHON_EXE=C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe
set TOOLS_DIR=C:\GHN_Tools
set NSSM=%TOOLS_DIR%\nssm.exe
set CLOUDFLARED=%TOOLS_DIR%\cloudflared.exe
set PORT=8090

:: Kiem tra thu muc du an
if not exist "%PROJECT_DIR%\control_center.py" (
    echo  [LOI] Khong tim thay control_center.py tai:
    echo        %PROJECT_DIR%
    echo        Kiem tra lai duong dan!
    pause
    exit /b 1
)
echo  [OK] Tim thay du an tai: %PROJECT_DIR%

:: --- Dung process control_center.py dang chay (neu co) ---
echo  [..] Kiem tra process control_center.py dang chay...
for /f "tokens=2" %%i in ('netstat -ano ^| findstr ":8090 " ^| findstr "LISTENING"') do set OLD_PID=%%i
if defined OLD_PID (
    echo  [..] Dang dung process cu PID !OLD_PID! de tranh xung dot port 8090...
    taskkill /F /PID !OLD_PID! >nul 2>&1
    timeout /t 2 /nobreak >nul
    echo  [OK] Da dung process cu
) else (
    echo  [OK] Khong co process nao dang chiem port 8090
)

:: Tao thu muc tools
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

echo.
echo  =====================================================
echo   BUOC A: Cai cloudflared
echo  =====================================================

if exist "%CLOUDFLARED%" (
    echo  [SKIP] cloudflared da co san
) else (
    echo  [..] Dang tai cloudflared tu GitHub...
    curl -L -o "%CLOUDFLARED%" "https://github.com/cloudflare/cloudflared/releases/download/2026.8.3/cloudflared-windows-amd64.exe" --progress-bar
    if not exist "%CLOUDFLARED%" (
        echo  [LOI] Tai cloudflared that bai! Kiem tra internet.
        pause
        exit /b 1
    )
    echo  [OK] cloudflared da tai xong
)

:: Kiem tra version
"%CLOUDFLARED%" --version 2>nul | head -1
echo.

echo  =====================================================
echo   BUOC B: Cai NSSM (service manager)
echo  =====================================================

if exist "%NSSM%" (
    echo  [SKIP] NSSM da co san
) else (
    echo  [..] Dang tai NSSM...
    curl -L -o "%TOOLS_DIR%\nssm.zip" "https://nssm.cc/release/nssm-2.24.zip" --progress-bar
    if not exist "%TOOLS_DIR%\nssm.zip" (
        echo  [LOI] Tai NSSM that bai! Kiem tra internet.
        pause
        exit /b 1
    )
    echo  [..] Giai nen NSSM...
    powershell -Command "Expand-Archive -Path '%TOOLS_DIR%\nssm.zip' -DestinationPath '%TOOLS_DIR%\nssm_extracted' -Force"
    copy "%TOOLS_DIR%\nssm_extracted\nssm-2.24\win64\nssm.exe" "%NSSM%" >nul
    if not exist "%NSSM%" (
        echo  [LOI] Giai nen NSSM that bai!
        pause
        exit /b 1
    )
    del "%TOOLS_DIR%\nssm.zip" >nul 2>&1
    echo  [OK] NSSM da cai xong
)
echo.

echo  =====================================================
echo   BUOC C: Dang ky ControlCenter la Windows Service
echo  =====================================================

:: Dung service cu neu dang chay
sc query ControlCenter >nul 2>&1
if %errorLevel% equ 0 (
    echo  [..] Dung service cu...
    "%NSSM%" stop ControlCenter >nul 2>&1
    "%NSSM%" remove ControlCenter confirm >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo  [..] Dang ky ControlCenter service...
"%NSSM%" install ControlCenter "%PYTHON_EXE%" "control_center.py"
"%NSSM%" set ControlCenter AppDirectory "%PROJECT_DIR%"
"%NSSM%" set ControlCenter DisplayName "GHN Control Center - GTalk"
"%NSSM%" set ControlCenter Description "Control Center quan tri ton phieu GTalk GHN - port 8090"
"%NSSM%" set ControlCenter Start SERVICE_AUTO_START
"%NSSM%" set ControlCenter AppStdout "%PROJECT_DIR%\service_stdout.log"
"%NSSM%" set ControlCenter AppStderr "%PROJECT_DIR%\service_stderr.log"
"%NSSM%" set ControlCenter AppRotateFiles 1
"%NSSM%" set ControlCenter AppRotateSeconds 86400
"%NSSM%" set ControlCenter AppRotateBytes 5242880

echo  [..] Khoi dong ControlCenter service...
"%NSSM%" start ControlCenter
timeout /t 3 /nobreak >nul

:: Kiem tra service chay chua
sc query ControlCenter | findstr "RUNNING" >nul
if %errorLevel% equ 0 (
    echo  [OK] ControlCenter service dang CHAY
) else (
    echo  [CANH BAO] Service chua chay - kiem tra log tai:
    echo             %PROJECT_DIR%\service_stderr.log
)
echo.

echo  =====================================================
echo   BUOC D: Dang ky cloudflared la Windows Service
echo  =====================================================

:: Dung service cu neu co
sc query CloudflaredTunnel >nul 2>&1
if %errorLevel% equ 0 (
    echo  [..] Dung tunnel cu...
    "%NSSM%" stop CloudflaredTunnel >nul 2>&1
    "%NSSM%" remove CloudflaredTunnel confirm >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo  [..] Dang ky CloudflaredTunnel service...
"%NSSM%" install CloudflaredTunnel "%CLOUDFLARED%" "tunnel --url http://localhost:%PORT% --no-autoupdate"
"%NSSM%" set CloudflaredTunnel DisplayName "GHN Cloudflare Tunnel - port %PORT%"
"%NSSM%" set CloudflaredTunnel Description "Tao duong ham ra internet cho Control Center GHN"
"%NSSM%" set CloudflaredTunnel Start SERVICE_AUTO_START
"%NSSM%" set CloudflaredTunnel AppStdout "%TOOLS_DIR%\tunnel.log"
"%NSSM%" set CloudflaredTunnel AppStderr "%TOOLS_DIR%\tunnel.log"
"%NSSM%" set CloudflaredTunnel AppRotateFiles 1
"%NSSM%" set CloudflaredTunnel AppRotateSeconds 86400
"%NSSM%" set CloudflaredTunnel AppRotateBytes 2097152

echo  [..] Khoi dong tunnel...
"%NSSM%" start CloudflaredTunnel
echo  [..] Doi 15 giay de lay URL tunnel...
timeout /t 15 /nobreak >nul

:: Doc URL tunnel tu log
echo  [..] URL tunnel cua ban:
echo.
findstr /i "trycloudflare.com" "%TOOLS_DIR%\tunnel.log" 2>nul | tail -3
echo.

:: Neu chua co URL trong log thi huong dan doc thu cong
findstr /i "trycloudflare.com" "%TOOLS_DIR%\tunnel.log" >nul 2>&1
if %errorLevel% neq 0 (
    echo  [i] URL chua hien ngay, chay lenh nay sau 30 giay de xem:
    echo      findstr trycloudflare.com "%TOOLS_DIR%\tunnel.log"
)
echo.

echo  =====================================================
echo   KIEM TRA CUOI
echo  =====================================================
echo.
sc query ControlCenter | findstr "STATE"
sc query CloudflaredTunnel | findstr "STATE"
echo.

:: Hien thi IP noi bo
echo  IP noi bo may nay:
ipconfig | findstr "IPv4" | findstr /v "169.254"
echo.

echo  =====================================================
echo   HOAN TAT! GHI LAI THONG TIN NAY:
echo  =====================================================
echo.
echo   Service ControlCenter : tu khoi dong khi may bat
echo   Service CloudflaredTunnel : tu khoi dong khi may bat
echo   Port noi bo           : http://localhost:%PORT%
echo   URL tu xa             : xem file %TOOLS_DIR%\tunnel.log
echo   Log dich vu           : %PROJECT_DIR%\service_stderr.log
echo   Quan ly service       : nssm start/stop/restart ControlCenter
echo.
echo   De xem URL tunnel bat ky luc nao:
echo     type "%TOOLS_DIR%\tunnel.log" ^^| findstr trycloudflare
echo.
echo  =====================================================
pause
