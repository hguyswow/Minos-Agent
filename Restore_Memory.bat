@echo off
chcp 65001 > nul
title 안티그래비티 기억 복구 도구 (Memory Restore)
color 0A

echo ==================================================
echo       안티그래비티 기억력 복구 (Restore)
echo ==================================================
echo.
echo 새 PC 또는 포맷된 PC에서 기존 대화 기억을 완벽하게 되살립니다.
echo (기존에 백업해둔 'memory_backup' 폴더의 내용이 시스템에 적용됩니다.)
echo.
pause

if not exist "%~dp0memory_backup" (
    echo [에러] '%~dp0memory_backup' 폴더를 찾을 수 없습니다. 백업을 먼저 진행해 주세요.
    pause
    exit
)

echo [진행 중] 백업된 기억을 시스템(C:\ai\memory_logs)으로 복원합니다...
if not exist "C:\ai\memory_logs" mkdir "C:\ai\memory_logs"
xcopy /E /I /Y /H /C "%~dp0memory_backup" "C:\ai\memory_logs"

echo.
echo [완료] 모든 기억이 성공적으로 복구(활성화)되었습니다!
echo 이제 텔레그램 봇을 실행하면 예전 대화를 그대로 기억합니다.
echo.
pause
