@echo off
chcp 65001 > nul
title Minos Engine Switcher
color 0E

cd /d "%~dp0"

echo ========================================================
echo     Minos Memory Engine - LLM Backend Switcher
echo ========================================================
echo.
echo 현재 설정된 엔진 상태:
python -c "import json; print(' - Active Engine:', json.load(open('llm_config.json'))['active_engine'])" 2>nul
echo.
echo [1] Ollama (Gemma 4 E4B) - 안정성, 표준 서버
echo [2] TurboQuant (Hermes 3) - VRAM 4~6x 절감, 초고속 추론
echo [3] OpenCode Go API - 외부 클라우드 API 연동
echo [Q] 취소
echo.
set /p choice="사용할 엔진 번호를 선택하세요: "

if "%choice%"=="1" (
    echo.
    echo Ollama 모드로 변경합니다...
    python -c "import json; data=json.load(open('llm_config.json')); data['active_engine']='ollama'; json.dump(data, open('llm_config.json', 'w', encoding='utf-8'), indent=4)"
    echo.
    echo 설정을 변경했습니다. 시스템을 재시작합니다!
    timeout /t 2 > nul
    call Start-Minos.bat
    exit
) else if "%choice%"=="2" (
    echo.
    echo TurboQuant 모드로 변경합니다...
    python -c "import json; data=json.load(open('llm_config.json')); data['active_engine']='turboquant'; json.dump(data, open('llm_config.json', 'w', encoding='utf-8'), indent=4)"
    echo.
    echo 설정을 변경했습니다. 시스템을 재시작합니다!
    timeout /t 2 > nul
    call Start-Minos.bat
    exit
) else if "%choice%"=="3" (
    goto :api_model_select
) else (
    echo 취소되었습니다.
    pause
    exit
)

:api_model_select
echo.
echo OpenCode Go API 모드로 변경합니다...
echo.
echo 사용할 세부 모델을 선택하세요 (OpenCode Go 전용):
echo [1] DeepSeek V4 Pro (코딩/수학 특화, 압도적 성능)
echo [2] DeepSeek V4 Flash (초고속 추론, 가성비 우수)
echo [3] GLM-5.1 (범용 대화, 논리 추론 강력)
echo [4] Qwen3.6 Plus (속도/성능 밸런스, 다국어 우수)
echo [5] Kimi K2.6 (긴 문맥/문서 처리 특화)
echo [6] MiMo-V2-Omni (다재다능 옴니 모델, 유연함)
echo [7] MiniMax M2.7 (창의성, 자연스러운 대화)
echo [8] 직접 입력 (예: mimo-v2-pro, glm-5 등)
set /p sub="모델 번호 선택 (1~8): "

set "MODEL_NAME=deepseek-v4-pro"
if "%sub%"=="1" set "MODEL_NAME=deepseek-v4-pro"
if "%sub%"=="2" set "MODEL_NAME=deepseek-v4-flash"
if "%sub%"=="3" set "MODEL_NAME=glm-5.1"
if "%sub%"=="4" set "MODEL_NAME=qwen3.6-plus"
if "%sub%"=="5" set "MODEL_NAME=kimi-k2.6"
if "%sub%"=="6" set "MODEL_NAME=mimo-v2-omni"
if "%sub%"=="7" set "MODEL_NAME=minimax-m2.7"
if "%sub%"=="8" set /p MODEL_NAME="정확한 모델명 입력: "

python -c "import json, sys; data=json.load(open('llm_config.json', encoding='utf-8')); data['active_engine']='api'; data['engines']['api']['model']='%MODEL_NAME%'; json.dump(data, open('llm_config.json', 'w', encoding='utf-8'), indent=4)"
echo.
echo 설정을 변경했습니다. (선택된 모델: %MODEL_NAME%)
echo 시스템을 재시작합니다!
timeout /t 2 > nul
call Start-Minos.bat
exit
