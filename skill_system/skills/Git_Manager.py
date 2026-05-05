# -*- coding: utf-8 -*-
"""
스킬명: Git_Manager
기능: git diff 분석 및 자동 커밋, 백업(stash) 수행
사용법: Git_Manager.py "명령어(status|diff|commit|stash)" ["커밋메시지"]
"""
import os
import sys
import subprocess
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return result.stdout.strip() + "\n" + result.stderr.strip()
    except Exception as e:
        return f"[오류] {e}"

def main():
    if len(sys.argv) < 2:
        print("[오류] 사용법: Git_Manager.py \"명령어(status|diff|commit|stash)\" [\"커밋메시지\"]")
        sys.exit(1)

    command = sys.argv[1].lower()
    
    if command == "status":
        print("📊 [Git 상태]")
        print(run_cmd("git status -s"))
    elif command == "diff":
        print("🔍 [Git 변경점 (diff)]")
        print(run_cmd("git diff"))
    elif command == "stash":
        print("📦 [Git 임시 백업 (stash)]")
        print(run_cmd("git stash push -m 'Auto backup by Git_Manager'"))
    elif command == "commit":
        if len(sys.argv) < 3:
            print("[오류] commit 명령은 커밋 메시지가 필요합니다.")
            sys.exit(1)
        msg = sys.argv[2]
        print(f"📝 [Git 자동 커밋: {msg}]")
        run_cmd("git add .")
        print(run_cmd(f"git commit -m \"{msg}\""))
    else:
        print(f"[오류] 알 수 없는 명령어: {command}")

if __name__ == "__main__":
    main()
