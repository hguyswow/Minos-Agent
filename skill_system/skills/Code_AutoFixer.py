# -*- coding: utf-8 -*-
"""
스킬명: Code_AutoFixer
기능: Python 파일에 autopep8/black으로 자동 포매팅 + isort로 임포트 정리
사용법: Code_AutoFixer.py "파이썬파일절대경로"
"""
import sys
import os
import subprocess

def run_formatter(cmd_args, tool_name):
    try:
        result = subprocess.run(
            cmd_args,
            capture_output=True, text=True, encoding='utf-8'
        )
        if result.returncode == 0:
            print(f"  ✅ {tool_name}: 성공")
        else:
            print(f"  ⚠️ {tool_name}: 경고/오류 발생")
            if result.stdout: print(f"     stdout: {result.stdout.strip()[:300]}")
            if result.stderr: print(f"     stderr: {result.stderr.strip()[:300]}")
    except FileNotFoundError:
        print(f"  ❌ {tool_name}: 설치되어 있지 않습니다. (pip install {tool_name.lower()}) 로 설치하세요.")

def main():
    if len(sys.argv) < 2:
        print("[오류] 사용법: Code_AutoFixer.py \"파이썬파일절대경로\"")
        sys.exit(1)

    target_file = sys.argv[1]
    if not os.path.exists(target_file):
        print(f"[오류] 파일을 찾을 수 없습니다: {target_file}")
        sys.exit(1)
    if not target_file.endswith('.py'):
        print("[오류] .py 파일만 지원합니다.")
        sys.exit(1)

    print(f"[Code_AutoFixer] 대상 파일: {target_file}")
    print("-" * 50)

    # 1. autopep8 - PEP8 기본 스타일 교정
    print("1️⃣ autopep8 실행 중...")
    run_formatter([sys.executable, "-m", "autopep8", "--in-place", "--aggressive", "--aggressive", target_file], "autopep8")

    # 2. isort - import 순서 정리
    print("2️⃣ isort 실행 중...")
    run_formatter([sys.executable, "-m", "isort", target_file], "isort")

    # 3. black 최종 포매팅 (가장 강력)
    print("3️⃣ black 실행 중...")
    run_formatter([sys.executable, "-m", "black", "--quiet", target_file], "black")

    print("-" * 50)
    print(f"🎉 포매팅 완료! 파일이 PEP8 표준에 맞게 정리되었습니다.")
    print(f"   📄 {target_file}")

if __name__ == "__main__":
    main()
