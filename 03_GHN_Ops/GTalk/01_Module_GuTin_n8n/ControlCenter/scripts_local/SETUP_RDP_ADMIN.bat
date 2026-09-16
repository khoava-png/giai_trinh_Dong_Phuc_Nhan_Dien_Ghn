@echo off
chcp 65001 >nul
title SETUP RDP + User khoava - Chay voi quyen Admin

echo ================================================
echo   SETUP RDP + User khoava
echo   Chay voi quyen Administrator
echo ================================================
echo.

:: Kiem tra quyen Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [LOI] Chua co quyen Administrator!
    echo       Hay chuot phai file nay -> Run as Administrator
    pause
    exit /b 1
)

echo [1/6] Bat RDP (Remote Desktop)...
reg add "HKLM\System\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f >nul
echo       OK - RDP da bat

echo [2/6] Mo Firewall cho RDP (port 3389)...
netsh advfirewall firewall set rule group="Remote Desktop" new enable=Yes >nul
echo       OK - Firewall da mo

echo [3/6] Tao user khoava voi pass 7395...
net user khoava 7395 /add /fullname:"Khoa Va" /passwordchg:no /expires:never >nul 2>&1
if %errorLevel% equ 0 (
    echo       OK - User khoava da tao
) else (
    echo       [!] User co the da ton tai, thu dat lai pass...
    net user khoava 7395 >nul
    echo       OK - Da dat lai pass
)

echo [4/6] Them khoava vao nhom Administrators...
net localgroup Administrators khoava /add >nul 2>&1
echo       OK

echo [5/6] Them khoava vao nhom Remote Desktop Users...
net localgroup "Remote Desktop Users" khoava /add >nul 2>&1
echo       OK

echo [6/6] Tat password complexity (cho phep pass don gian)...
powershell -Command "$cfg = [System.IO.Path]::Combine($env:TEMP, 'secpol.cfg'); secedit /export /cfg $cfg /quiet 2>$null; if (Test-Path $cfg) { (Get-Content $cfg) -replace 'PasswordComplexity = 1','PasswordComplexity = 0' | Set-Content $cfg; secedit /configure /db ([System.IO.Path]::Combine($env:TEMP,'secpol.sdb')) /cfg $cfg /quiet 2>$null; Write-Host 'OK - Complexity da tat' } else { Write-Host 'SKIP - Khong can thiet' }"

echo.
echo ================================================
echo   HOAN TAT! Ket qua:
echo ================================================
echo.
echo   RDP : BAT (port 3389)
echo   User: khoava / Pass: 7395
echo   Role: Administrators + Remote Desktop Users
echo.
echo   Tu laptop, mo Remote Desktop Connection:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :showip
)
:showip
set IP=%IP: =%
echo   - Computer : %IP%
echo   - User     : khoava
echo   - Password : 7395
echo.
echo ================================================
pause
