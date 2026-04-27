@echo off
title Antigravity Web Dashboard Server
color 0B
echo ========================================================
echo       Antigravity Web Dashboard Server Startup
echo ========================================================
echo.
echo [1/3] Checking requirements...
pip install -q flask psutil requests gputil

echo [2/3] Initializing System Core...
echo [3/3] Starting Local Web Server on Port 5000...
echo.
echo ========================================================
echo  Dashboard is available at: http://localhost:5000
echo  Press Ctrl+C to stop the server.
echo ========================================================
echo.
python dashboard_server.py
pause
