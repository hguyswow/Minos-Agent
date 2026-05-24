# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Telegram_Bridge_Manager
# AGENT_SKILL_DESC: 다이렉트 텔레그램 브릿지 프로세스의 상태(status)를 확인하고 시작(start)/종료(stop)하거나 시작프로그램(enable_startup/disable_startup) 자동 실행 여부를 설정합니다.
# AGENT_SKILL_ARGS: action(str) - status/start/stop/enable_startup/disable_startup
# AGENT_SKILL_RETURNS: 텔레그램 브릿지의 작동 상태 및 시작프로그램 관리 결과
import sys
import os
import io
import psutil
import subprocess

# Force stdout to use UTF-8 to prevent Windows CP949 encoding errors with emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 원본 경로 백업 (2026-05-24)
# BRIDGE_PATH = r"C:\Users\hguys\.gemini\antigravity\scratch\telegram_bridge.py"
BRIDGE_PATH = r"C:\ai\Antigravity_Memory_Engine\telegram_bridge.py"
PYTHON_EXE = r"C:\Users\hguys\hermes\venv\Scripts\python.exe"
STARTUP_PATH = r"C:\Users\hguys\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Start-TelegramBridge.bat"

def check_status():
    running = False
    pids = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = p.info['cmdline']
            if cmdline:
                cmd_str = " ".join(cmdline).lower()
                if "telegram_bridge.py" in cmd_str:
                    running = True
                    pids.append(p.info['pid'])
        except Exception as e:
            pass
            
    startup_enabled = os.path.exists(STARTUP_PATH)
    
    print("[텔레그램 브릿지 모니터 리포트]\n")
    print(f"- 작동 상태: {'🟢 RUNNING' if running else '🔴 STOPPED'}")
    if running:
        print(f"  · 감지된 PID: {', '.join(map(str, pids))}")
    print(f"- 윈도우 시작프로그램 자동 실행: {'✅ ENABLED' if startup_enabled else '❌ DISABLED'}")

def start_bridge():
    running = False
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = p.info['cmdline']
            if cmdline:
                cmd_str = " ".join(cmdline).lower()
                if "telegram_bridge.py" in cmd_str:
                    running = True
        except:
            pass
            
    if running:
        print("[INFO] 텔레그램 브릿지가 이미 실행 중입니다.")
        return

    try:
        cmd = f'powershell -Command "Start-Process -FilePath \'{PYTHON_EXE}\' -ArgumentList \'{BRIDGE_PATH}\' -WindowStyle Hidden"'
        subprocess.run(cmd, shell=True, check=True)
        print("[OK] 텔레그램 브릿지를 백그라운드에서 성공적으로 시작했습니다.")
    except Exception as e:
        print(f"[ERROR] 브릿지 시작 실패: {e}")

def stop_bridge():
    stopped = False
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = p.info['cmdline']
            if cmdline:
                cmd_str = " ".join(cmdline).lower()
                if "telegram_bridge.py" in cmd_str:
                    p.kill()
                    print(f"[OK] 텔레그램 브릿지 프로세스 종료 성공 (PID: {p.info['pid']})")
                    stopped = True
        except Exception as e:
            pass
            
    if not stopped:
        print("[INFO] 종료할 활성 브릿지 프로세스가 없습니다.")

def enable_startup():
    try:
        content = f'@echo off\nchcp 65001 > nul\nset PYTHONIOENCODING=utf-8\n"{PYTHON_EXE}" "{BRIDGE_PATH}"\n'
        with open(STARTUP_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[OK] 윈도우 시작프로그램(Startup)에 텔레그램 브릿지 실행 배치 파일을 성공적으로 등록했습니다.")
    except Exception as e:
        print(f"[ERROR] 시작프로그램 등록 실패: {e}")

def disable_startup():
    if os.path.exists(STARTUP_PATH):
        try:
            os.remove(STARTUP_PATH)
            print("[OK] 윈도우 시작프로그램에서 텔레그램 브릿지 기동 스크립트를 제거했습니다.")
        except Exception as e:
            print(f"[ERROR] 시작프로그램 제거 실패: {e}")
    else:
        print("[INFO] 시작프로그램에 등록된 기동 스크립트가 없습니다.")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        check_status()
    else:
        action = sys.argv[1].lower()
        if action == "status":
            check_status()
        elif action == "start":
            start_bridge()
        elif action == "stop":
            stop_bridge()
        elif action == "enable_startup":
            enable_startup()
        elif action == "disable_startup":
            disable_startup()
        else:
            print("알 수 없는 액션입니다. 사용 가능한 액션: status, start, stop, enable_startup, disable_startup")
