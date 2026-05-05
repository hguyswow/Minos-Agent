@echo off
chcp 65001 >nul
title Minos System Launcher
color 0B

echo.
echo  =====================================================
echo    MINOS - Antigravity Memory Engine v2.0
echo  =====================================================
echo.

cd /d "%~dp0"

REM =====================================================
REM  STEP 1: Cleanup - Remove stale files and processes
REM =====================================================
echo  [1/5] Cleanup - Removing stale processes and files...

wmic process where "name='python.exe' and commandline like '%%antigravity_telegram%%'" delete >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%dashboard_server%%'" delete >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%tentacle_daemon%%'" delete >nul 2>&1
taskkill /F /IM llama-server-turbo.exe >nul 2>&1

REM __pycache__ cleanup
for /d /r "%~dp0" %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" >nul 2>&1
)

REM .pyc file cleanup
del /s /q "%~dp0*.pyc" >nul 2>&1

REM Reset stale tentacle signal file
if exist "tentacles\logs\tentacle_signals.json" (
    echo {} > "tentacles\logs\tentacle_signals.json"
)

REM Remove temp files
if exist temp_engine.txt del temp_engine.txt >nul 2>&1
if exist minos_pid.txt del minos_pid.txt >nul 2>&1

echo  [1/5] Done.
timeout /t 1 /nobreak >nul

REM =====================================================
REM  STEP 2: Check AI Engine
REM =====================================================
echo  [2/5] Checking AI Engine...

python -c "import json,sys; d=json.load(open('llm_config.json')); print(d.get('active_engine','ollama'))" >temp_engine.txt 2>nul
set /p ACTIVE_ENGINE=<temp_engine.txt
del temp_engine.txt >nul 2>&1

if "%ACTIVE_ENGINE%"=="turboquant" (
    echo  [2/5] TurboQuant engine detected. Starting llama-server-turbo...
    start "TurboQuant Server" cmd /c "title TurboQuant LLM Server & C:\ai\llama-server-turbo.exe --model C:\Users\hguys\.openclaw\Hermes-3-Llama-3.1-8B.Q4_K_M.gguf --ctx-size 8192 -ngl 99 --cache-type-k turbo3 --cache-type-v turbo3 --port 8080"
    timeout /t 4 /nobreak >nul
) else (
    tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >nul
    if errorlevel 1 (
        echo  [2/5] Starting Ollama...
        start "" "ollama" serve
        timeout /t 5 /nobreak >nul
    ) else (
        echo  [2/5] Ollama already running.
    )
)

REM =====================================================
REM  STEP 3: Get Telegram Bot Info
REM =====================================================
echo  [3/5] Checking Telegram Bot info...

python -c "import json,sys,requests; cfg=json.load(open('state/bot_config.json',encoding='utf-8-sig')); token=cfg.get('telegram_token',''); r=requests.get(f'https://api.telegram.org/bot{token}/getMe',timeout=5).json(); print(r['result']['username'] if r.get('ok') else 'UNKNOWN')" >temp_botname.txt 2>nul
set /p BOT_NAME=<temp_botname.txt
del temp_botname.txt >nul 2>&1

if "%BOT_NAME%"=="UNKNOWN" (
    echo  [3/5] Bot name lookup failed - check network
) else (
    echo  [3/5] Bot confirmed: @%BOT_NAME%
)

REM =====================================================
REM  STEP 4: Check Python Packages
REM =====================================================
echo  [4/5] Checking required packages...

python -c "import flask,psutil,telegram,requests; print('OK')" >nul 2>&1
if errorlevel 1 (
    echo  [4/5] Installing missing packages...
    pip install -q flask psutil requests python-telegram-bot pyttsx3
) else (
    echo  [4/5] All packages OK.
)

REM =====================================================
REM  STEP 5: Launch Minos Modules
REM =====================================================
echo  [5/5] Launching Minos modules...

echo  Starting Web Dashboard...
start "Minos Dashboard" cmd /k "title Minos Dashboard - http://localhost:5000 & color 0A & set PYTHONIOENCODING=utf-8 & python dashboard_server.py"

echo  Waiting for Dashboard to initialize (3s)...
timeout /t 3 /nobreak >nul

echo  Starting Telegram Bot and Core Engine...
start "Minos Telegram Bot" cmd /k "title Minos Telegram Bot & color 0E & set PYTHONIOENCODING=utf-8 & python antigravity_telegram.py"

timeout /t 2 /nobreak >nul

REM =====================================================
REM  Startup Complete
REM =====================================================
echo.
echo  =====================================================
echo    All systems are GO!
echo  =====================================================
echo.
echo    Dashboard  : http://localhost:5000
if not "%BOT_NAME%"=="UNKNOWN" (
    echo    Telegram   : https://t.me/%BOT_NAME%
) else (
    echo    Telegram   : Bot name unavailable
)
echo.
echo  =====================================================
echo.
echo  Select an option:
echo    [1] Open Dashboard in browser
echo    [2] Open Telegram bot in browser
echo    [3] Open both
echo    [Enter] Close launcher
echo.
set /p OPEN_CHOICE= Choice (1/2/3 or Enter): 

if "%OPEN_CHOICE%"=="1" (
    start "" "http://localhost:5000"
)
if "%OPEN_CHOICE%"=="2" (
    if not "%BOT_NAME%"=="UNKNOWN" start "" "https://t.me/%BOT_NAME%"
)
if "%OPEN_CHOICE%"=="3" (
    start "" "http://localhost:5000"
    if not "%BOT_NAME%"=="UNKNOWN" start "" "https://t.me/%BOT_NAME%"
)

echo.
echo  Launcher closed. Minos services continue running in background.
echo.
pause >nul
