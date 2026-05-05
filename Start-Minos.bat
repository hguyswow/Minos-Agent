@echo off
chcp 65001 > nul
title Minos System Launcher
color 0B

echo ========================================================
echo       Minos System Full Startup
echo ========================================================
echo.

echo [1/4] Stopping existing Minos processes...
wmic process where "name='python.exe' and commandline like '%%antigravity_telegram%%'" delete >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%dashboard_server%%'" delete >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%tentacle_daemon%%'" delete >nul 2>&1
taskkill /F /IM llama-server-turbo.exe >nul 2>&1
timeout /t 2 /nobreak > nul

echo [2/4] Checking Ollama AI Engine...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo - Ollama is already running.
) else (
    echo - Starting Ollama in background...
    start "" "ollama" serve
    timeout /t 5 /nobreak > nul
)

echo [2.5/4] Checking Dual Engine Config...
cd /d "%~dp0"
python -c "import json; print(json.load(open('llm_config.json'))['active_engine'])" > temp_engine.txt
set /p ACTIVE_ENGINE=<temp_engine.txt
del temp_engine.txt

if "%ACTIVE_ENGINE%"=="turboquant" (
    echo - Active Engine is TurboQuant. Launching llama-server-turbo...
    start "TurboQuant LLM Server" cmd /c "title TurboQuant Server & C:\ai\llama-server-turbo.exe --model C:\Users\hguys\.openclaw\Hermes-3-Llama-3.1-8B.Q4_K_M.gguf --ctx-size 8192 -ngl 99 --cache-type-k turbo3 --cache-type-v turbo3 --port 8080"
    timeout /t 3 /nobreak > nul
) else (
    echo - Active Engine is Ollama.
)

echo [3/4] Checking python packages...
pip install -q flask psutil requests gputil pyttsx3 SpeechRecognition faster-whisper pydub imageio-ffmpeg

echo [4/4] Launching Minos Modules in sequence...
cd /d "%~dp0"

echo - Starting Web Dashboard Server...
start "Minos Dashboard" cmd /k "title Minos Dashboard & python dashboard_server.py"

echo - Waiting for Dashboard to initialize...
timeout /t 3 /nobreak > nul

echo - Starting Telegram Bot & Core Engine...
start "Minos Telegram Bot" cmd /k "title Minos Telegram Bot & python antigravity_telegram.py"

echo.
echo ========================================================
echo  All systems are GO! 🚀
echo  Dashboard is available at: http://localhost:5000
echo ========================================================
pause
