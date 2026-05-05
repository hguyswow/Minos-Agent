# -*- coding: utf-8 -*-
"""
스킬명: Dependency_Manager
기능: pip 패키지 설치/업그레이드/requirements.txt 생성 및 현재 설치 목록 조회
사용법:
  Dependency_Manager.py install "패키지명1 패키지명2 ..."  - 패키지 설치
  Dependency_Manager.py upgrade "패키지명1 패키지명2 ..."  - 패키지 업그레이드
  Dependency_Manager.py list                              - 설치된 패키지 목록
  Dependency_Manager.py freeze "저장할경로(선택)"          - requirements.txt 생성
  Dependency_Manager.py check "패키지명"                  - 특정 패키지 설치 여부 확인
"""
import sys
import os
import subprocess

def run_pip(args):
    result = subprocess.run(
        [sys.executable, "-m", "pip"] + args,
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    return result

def main():
    if len(sys.argv) < 2:
        print("[오류] 사용법: Dependency_Manager.py [install/upgrade/list/freeze/check] [인자]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "install":
        if len(sys.argv) < 3:
            print("[오류] 설치할 패키지명을 입력하세요.")
            sys.exit(1)
        packages = sys.argv[2].split()
        print(f"[Dependency_Manager] 설치 대상: {packages}")
        for pkg in packages:
            print(f"\n📦 '{pkg}' 설치 중...")
            r = run_pip(["install", pkg])
            if r.returncode == 0:
                print(f"  ✅ '{pkg}' 설치 성공!")
            else:
                print(f"  ❌ '{pkg}' 설치 실패:")
                print(f"     {r.stderr.strip()[:500]}")

    elif action == "upgrade":
        if len(sys.argv) < 3:
            print("[오류] 업그레이드할 패키지명을 입력하세요.")
            sys.exit(1)
        packages = sys.argv[2].split()
        print(f"[Dependency_Manager] 업그레이드 대상: {packages}")
        for pkg in packages:
            print(f"\n⬆️ '{pkg}' 업그레이드 중...")
            r = run_pip(["install", "--upgrade", pkg])
            if r.returncode == 0:
                print(f"  ✅ '{pkg}' 업그레이드 성공!")
            else:
                print(f"  ❌ '{pkg}' 업그레이드 실패: {r.stderr.strip()[:300]}")

    elif action == "list":
        print("[Dependency_Manager] 현재 설치된 패키지 목록:")
        r = run_pip(["list", "--format=columns"])
        if r.returncode == 0:
            lines = r.stdout.strip().splitlines()
            print(f"  총 {len(lines)-2}개 패키지 설치됨\n")
            # 상위 30개만 출력 (너무 길어지지 않도록)
            for line in lines[:32]:
                print(f"  {line}")
            if len(lines) > 32:
                print(f"  ... (외 {len(lines)-32}개 생략)")
        else:
            print(f"  오류: {r.stderr.strip()}")

    elif action == "freeze":
        save_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.getcwd(), "requirements.txt")
        print(f"[Dependency_Manager] requirements.txt 생성 중...")
        r = run_pip(["freeze"])
        if r.returncode == 0:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(r.stdout)
            lines = r.stdout.strip().splitlines()
            print(f"  ✅ requirements.txt 생성 완료! ({len(lines)}개 패키지)")
            print(f"  📄 저장 경로: {save_path}")
        else:
            print(f"  ❌ 오류: {r.stderr.strip()}")

    elif action == "check":
        if len(sys.argv) < 3:
            print("[오류] 확인할 패키지명을 입력하세요.")
            sys.exit(1)
        pkg = sys.argv[2]
        r = run_pip(["show", pkg])
        if r.returncode == 0:
            print(f"  ✅ '{pkg}' 설치됨!")
            for line in r.stdout.strip().splitlines():
                print(f"     {line}")
        else:
            print(f"  ❌ '{pkg}'는 설치되어 있지 않습니다.")
            print(f"  💡 설치하려면: Dependency_Manager.py install \"{pkg}\"")
    else:
        print(f"[오류] 알 수 없는 명령: '{action}'")
        print("사용 가능한 명령: install, upgrade, list, freeze, check")
        sys.exit(1)

if __name__ == "__main__":
    main()
