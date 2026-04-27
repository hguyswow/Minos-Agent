@echo off
chcp 65001 > nul
title 안티그래비티 기억 백업 도구 (Memory Backup)
color 0B

echo ==================================================
echo       안티그래비티 기억력 백업 (Backup)
echo ==================================================
echo.
echo 봇의 모든 기억(단기/장기/일화 기억)을 이 엔진 폴더 안으로 안전하게 복사합니다.
echo PC를 이동하거나 윈도우를 포맷할 때 이 폴더만 챙기시면 됩니다!
echo.
pause

if not exist "C:\ai\memory_logs" (
    echo [에러] 기억 저장소(C:\ai\memory_logs)를 찾을 수 없습니다. 아직 대화 기록이 없을 수 있습니다.
    pause
    exit
)

echo [진행 중] 기억 백업 폴더를 생성하고 복사합니다...
xcopy /E /I /Y /H /C "C:\ai\memory_logs" "%~dp0memory_backup"

echo.
echo [완료] 성공적으로 백업되었습니다! 
echo 백업 위치: %~dp0memory_backup
echo.
pause
