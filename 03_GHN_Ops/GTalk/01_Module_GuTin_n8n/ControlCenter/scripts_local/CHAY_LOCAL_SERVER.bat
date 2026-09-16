@echo off
title GHN Control Center - Local Studio Server
color 0B
echo ========================================================
echo       GHN CONTROL CENTER - LOCAL DEV SERVER (5050)
echo ========================================================
echo.
echo Dang khoi chay HTTP Server ho tro Stream Video (Range 206)...
echo.

start "" "http://localhost:5050/demo_landing_login.html"
python range_server.py

pause
