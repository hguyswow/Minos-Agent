@echo off
chcp 65001 > nul
title Minos System Initial Setup
color 0B

echo ========================================================
echo       Minos System Environment Setup (Virtual Environment)
echo ========================================================
echo.
echo 이 스크립트는 Minos 시스템 구동을 위한 가상환경(venv)을 구축하고,
echo 필수 요소(Python, Ollama, 파이썬 라이브러리)를 자동으로 설치합니다.
echo.
pause

echo.
echo [1/5] Python 3.12 설치 여부 확인 및 설치...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python이 감지되지 않았습니다. winget을 통해 Python 3.12를 설치합니다...
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo [오류] Python 자동 설치에 실패했습니다. 수동으로 Python을 설치한 뒤 다시 시도해 주세요.
        pause
        exit /b 1
    )
) else (
    echo [OK] Python이 이미 설치되어 있습니다.
)

echo.
echo [2/5] Ollama 설치 여부 확인 및 설치...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama가 감지되지 않았습니다. winget을 통해 Ollama를 설치합니다...
    winget install Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements
) else (
    echo [OK] Ollama가 이미 설치되어 있습니다.
)

echo.
echo [3/5] 파이썬 가상환경(venv) 생성 및 활성화...
if not exist venv (
    echo 가상환경(venv)을 생성하는 중입니다...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [오류] 가상환경 생성에 실패했습니다. 파이썬 설치 버전을 확인해 주세요.
        pause
        exit /b 1
    )
)
echo [OK] 가상환경(venv) 준비 완료.

REM 가상환경 활성화
call venv\Scripts\activate

echo.
echo [4/5] 필수 파이썬 라이브러리 설치 (requirements.txt)...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [오류] 라이브러리 설치 중 문제가 발생했습니다.
    pause
    exit /b 1
)

echo.
echo [4.5/5] Playwright Chromium 브라우저 엔진 구축...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo [오류] Playwright 브라우저 엔진 설치 실패. 웹 검색 기능이 제한될 수 있습니다.
)

echo.
echo [5/5] Ollama 백그라운드 엔진 가동 및 필수 모델 다운로드...
start /B ollama serve >nul 2>&1
echo 5초 대기 후 임베딩 모델(nomic-embed-text) 다운로드 진행...
timeout /t 5 /nobreak > nul
ollama pull nomic-embed-text

echo.
echo ========================================================
echo  All setup complete! 🚀
echo  이제 Start-Minos.bat 파일을 더블클릭하여 에이전트를 가동해 주세요.
echo ========================================================
pause
