@echo off
chcp 65001 > nul
title Minos System Launcher
color 0B

echo ========================================================
echo       Minos System Full Startup
echo ========================================================
echo.

echo [1/3] Stopping existing processes...
wmic process where "name='python.exe' and commandline like '%%antigravity_telegram%%'" delete >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%dashboard_server%%'" delete >nul 2>&1
timeout /t 2 /nobreak > nul

echo [2/3] Checking python packages...
pip install -q flask psutil requests gputil pyttsx3 SpeechRecognition faster-whisper pydub imageio-ffmpeg

echo [3/3] Launching Modules...
cd /d "%~dp0"

echo - Starting Telegram Bot...
start "Minos Telegram Bot" cmd /k "title Minos Telegram Bot & python antigravity_telegram.py"

echo - Starting Web Dashboard Server...
start "Minos Dashboard" cmd /k "title Minos Dashboard & python dashboard_server.py"

echo.
echo ========================================================
echo  All systems are GO! 🚀
echo  Dashboard is available at: http://localhost:5000
echo ========================================================
pause
