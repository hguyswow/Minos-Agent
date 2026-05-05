@echo off
chcp 65001 >nul
title 🐙 Minos System Launcher
color 0B

echo.
echo  ██╗███╗   ███╗██╗███╗   ██╗ ██████╗ ███████╗
echo  ██║████╗ ████║██║████╗  ██║██╔═══██╗██╔════╝
echo  ██║██╔████╔██║██║██╔██╗ ██║██║   ██║███████╗
echo  ██║██║╚██╔╝██║██║██║╚██╗██║██║   ██║╚════██║
echo  ██║██║ ╚═╝ ██║██║██║ ╚████║╚██████╔╝███████║
echo  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝
echo.
echo  [ Antigravity Memory Engine v2.0 ]
echo  ================================================
echo.

cd /d "%~dp0"

REM ──────────────────────────────────────────────────
REM  STEP 1: 찌꺼기 정리 (Cleanup)
REM ──────────────────────────────────────────────────
echo  [1/5] 🧹 찌꺼기 정리 중...

REM 기존 프로세스 종료
wmic process where "name='python.exe' and commandline like '%%antigravity_telegram%%'" delete >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%dashboard_server%%'" delete >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%tentacle_daemon%%'" delete >nul 2>&1
taskkill /F /IM llama-server-turbo.exe >nul 2>&1

REM __pycache__ 정리
for /d /r "%~dp0" %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" >nul 2>&1
)

REM .pyc 파일 정리
del /s /q "%~dp0*.pyc" >nul 2>&1

REM 스테일 신호 파일 초기화 (봇 재시작 시 오래된 신호 재전송 방지)
if exist "tentacles\logs\tentacle_signals.json" (
    echo {} > "tentacles\logs\tentacle_signals.json"
)

REM 이전 런처 temp 파일 정리
if exist temp_engine.txt del temp_engine.txt >nul 2>&1
if exist minos_pid.txt del minos_pid.txt >nul 2>&1

echo  [OK] 정리 완료
timeout /t 1 /nobreak >nul

REM ──────────────────────────────────────────────────
REM  STEP 2: Ollama 엔진 확인
REM ──────────────────────────────────────────────────
echo  [2/5] 🤖 AI 엔진 확인 중...

REM 엔진 설정 읽기
python -c "import json,sys; d=json.load(open('llm_config.json')); print(d.get('active_engine','ollama'))" >temp_engine.txt 2>nul
set /p ACTIVE_ENGINE=<temp_engine.txt
del temp_engine.txt >nul 2>&1

if "%ACTIVE_ENGINE%"=="turboquant" (
    echo  [--] TurboQuant 엔진 기동 중...
    start "TurboQuant Server" cmd /c "title TurboQuant LLM Server & C:\ai\llama-server-turbo.exe --model C:\Users\hguys\.openclaw\Hermes-3-Llama-3.1-8B.Q4_K_M.gguf --ctx-size 8192 -ngl 99 --cache-type-k turbo3 --cache-type-v turbo3 --port 8080"
    timeout /t 4 /nobreak >nul
) else (
    REM Ollama 실행 확인
    tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >nul
    if errorlevel 1 (
        echo  [--] Ollama 시작 중...
        start "" "ollama" serve
        timeout /t 5 /nobreak >nul
    ) else (
        echo  [OK] Ollama 이미 실행 중
    )
)

REM ──────────────────────────────────────────────────
REM  STEP 3: 텔레그램 봇 정보 읽기
REM ──────────────────────────────────────────────────
echo  [3/5] 📱 텔레그램 봇 정보 확인 중...

python -c "
import json, sys
try:
    cfg = json.load(open('state/bot_config.json', encoding='utf-8-sig'))
    token = cfg.get('telegram_token','')
    if token and ':' in token:
        bot_id = token.split(':')[0]
        print(bot_id)
    else:
        print('UNKNOWN')
except:
    print('UNKNOWN')
" >temp_botid.txt 2>nul
set /p BOT_ID=<temp_botid.txt
del temp_botid.txt >nul 2>&1

python -c "
import json, sys, requests
try:
    cfg = json.load(open('state/bot_config.json', encoding='utf-8-sig'))
    token = cfg.get('telegram_token','')
    if not token: sys.exit(1)
    r = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=5)
    data = r.json()
    if data.get('ok'):
        name = data['result'].get('username','')
        print(name)
    else:
        print('UNKNOWN')
except:
    print('UNKNOWN')
" >temp_botname.txt 2>nul
set /p BOT_NAME=<temp_botname.txt
del temp_botname.txt >nul 2>&1

if "%BOT_NAME%"=="UNKNOWN" (
    echo  [!!] 봇 이름 조회 실패 (네트워크 확인)
) else (
    echo  [OK] 봇 확인: @%BOT_NAME%
)

REM ──────────────────────────────────────────────────
REM  STEP 4: 패키지 확인 (빠른 확인만)
REM ──────────────────────────────────────────────────
echo  [4/5] 📦 필수 패키지 확인 중...
python -c "import flask,psutil,telegram,requests; print('OK')" >nul 2>&1
if errorlevel 1 (
    echo  [--] 누락 패키지 설치 중...
    pip install -q flask psutil requests python-telegram-bot pyttsx3
) else (
    echo  [OK] 패키지 정상
)

REM ──────────────────────────────────────────────────
REM  STEP 5: 모듈 순차 기동
REM ──────────────────────────────────────────────────
echo  [5/5] 🚀 Minos 모듈 기동 중...

echo  [--] 웹 대시보드 서버 시작...
start "Minos Dashboard" cmd /k "title 🖥 Minos Dashboard ^| http://localhost:5000 & color 0A & set PYTHONIOENCODING=utf-8 & python dashboard_server.py"

echo  [--] 대시보드 초기화 대기 (3초)...
timeout /t 3 /nobreak >nul

echo  [--] 텔레그램 봇 & 코어 엔진 시작...
start "Minos Telegram Bot" cmd /k "title 📱 Minos Telegram Bot & color 0E & set PYTHONIOENCODING=utf-8 & python antigravity_telegram.py"

timeout /t 2 /nobreak >nul

REM ──────────────────────────────────────────────────
REM  완료 화면
REM ──────────────────────────────────────────────────
echo.
echo  ================================================
echo  ✅  MINOS 전체 시스템 기동 완료!
echo  ================================================
echo.
echo  🖥  웹 대시보드  :  http://localhost:5000
if not "%BOT_NAME%"=="UNKNOWN" (
    echo  📱  텔레그램 봇  :  https://t.me/%BOT_NAME%
) else (
    echo  📱  텔레그램 봇  :  @%BOT_ID% (이름 조회 불가)
)
echo.
echo  ================================================
echo.
echo  아래 번호를 선택하세요:
echo  [1] 대시보드 브라우저에서 열기
echo  [2] 텔레그램 봇 브라우저에서 열기
echo  [3] 둘 다 열기
echo  [Enter] 그냥 닫기
echo.
set /p OPEN_CHOICE= 선택 (1/2/3/Enter): 

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
echo  창을 닫으면 런처가 종료됩니다 (서버는 계속 실행 중).
echo.
pause >nul
