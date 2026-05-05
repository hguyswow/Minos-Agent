@echo off
chcp 65001 > nul
title Minos System Initial Setup
color 0B

echo ========================================================
echo       Minos System Environment Setup (Portable)
echo ========================================================
echo.
echo 이 스크립트는 아무것도 없는 새 PC에서 Minos 시스템을 구동하기 위한
echo 필수 요소(Python, Ollama, 파이썬 라이브러리)를 자동으로 설치합니다.
echo (경고: 설치 중 관리자 권한을 요구하는 팝업이 뜰 수 있습니다.)
echo.
pause

echo.
echo [1/4] Installing Python 3.12 (if not exists)...
winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements

echo.
echo [2/4] Installing Ollama (if not exists)...
winget install Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements

echo.
echo 2. Installing Python libraries...
pip install -q -r requirements.txt
pip install -q flask psutil requests gputil pyttsx3 chromadb rank_bm25 SpeechRecognition faster-whisper pydub imageio-ffmpeg duckduckgo-search playwright

echo.
echo [2.5/4] Installing Playwright Chromium browser (for web search)...
python -m playwright install chromium
echo [OK] Playwright Chromium installed.

echo.
echo [4/4] Starting Ollama and Pulling Base Models...
echo (Ollama 엔진을 켜고 필수 모델인 nomic-embed-text를 다운로드합니다)
echo (용량이 크므로 시간이 다소 걸릴 수 있습니다.)
start /B ollama serve >nul 2>&1
timeout /t 5 /nobreak > nul
ollama pull nomic-embed-text

echo.
echo ========================================================
echo  All setup complete! 🚀
echo  이제 Start-Minos.bat 파일을 더블클릭하여 시스템을 켜주세요.
echo ========================================================
pause
