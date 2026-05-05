# -*- coding: utf-8 -*-
"""
스킬명: Self_Code_Analyzer
기능: 알쫑이 자신의 핵심 소스 파일을 분석하여 TODO, 에러 핸들링 누락,
      개선 가능 지점을 탐지하고 리포트를 출력합니다.
사용법: Self_Code_Analyzer.py ["파일명(선택, 없으면 전체 핵심 파일 분석)"]
"""
import os
import sys
import ast
import re

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CORE_FILES = [
    "core_engine.py",
    "antigravity_telegram.py",
    "memory_engine.py",
    "dashboard_server.py",
    "tts_engine.py",
]

def analyze_file(fpath):
    issues = []
    fname = os.path.basename(fpath)

    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
    except UnicodeDecodeError:
        return [f"[CRITICAL] UTF-8 읽기 실패 — 인코딩 선언 누락 의심"]
    except Exception as e:
        return [f"[ERROR] 파일 열기 실패: {e}"]

    # 1. UTF-8 선언 누락
    if '# -*- coding: utf-8 -*-' not in content[:200]:
        issues.append("[WARN] UTF-8 인코딩 선언(# -*- coding: utf-8 -*-) 누락")

    # 2. open() encoding 미지정 탐지
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if ('open(' in stripped
                and 'encoding=' not in stripped
                and "'rb'" not in stripped and '"rb"' not in stripped
                and "'wb'" not in stripped and '"wb"' not in stripped
                and not stripped.startswith('#')):
            issues.append(f"[WARN] L{i}: open() encoding= 미지정 — {stripped[:80]}")

    # 3. subprocess encoding 미지정 탐지
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if ('subprocess.run(' in stripped or 'subprocess.Popen(' in stripped):
            if 'encoding=' not in stripped and 'capture_output' in stripped:
                issues.append(f"[WARN] L{i}: subprocess encoding= 미지정 — {stripped[:80]}")

    # 4. TODO / FIXME / HACK 탐지
    for i, line in enumerate(lines, 1):
        if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', line, re.IGNORECASE):
            issues.append(f"[TODO] L{i}: {line.strip()[:80]}")

    # 5. except: pass (빈 예외 처리) 탐지
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped in ('except:', 'except Exception:', 'except Exception as e:'):
            # 다음 줄이 pass인지 확인
            if i < len(lines) and lines[i].strip() == 'pass':
                issues.append(f"[WARN] L{i}: except + pass — 에러가 묵살됨 (로깅 추가 권장)")

    # 6. 함수 길이 탐지 (50줄 초과)
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = node.end_lineno - node.lineno
                if func_lines > 50:
                    issues.append(f"[INFO] 함수 '{node.name}()' 길이 {func_lines}줄 — 분리 검토 권장")
    except SyntaxError as e:
        issues.append(f"[CRITICAL] 문법 오류 발생: {e}")

    return issues

def main():
    target_name = sys.argv[1] if len(sys.argv) > 1 else None

    if target_name:
        fpath = os.path.join(BASE_DIR, target_name)
        if not os.path.exists(fpath):
            print(f"[오류] 파일을 찾을 수 없습니다: {fpath}")
            sys.exit(1)
        targets = [(target_name, fpath)]
    else:
        targets = [(name, os.path.join(BASE_DIR, name)) for name in CORE_FILES if os.path.exists(os.path.join(BASE_DIR, name))]

    print("=" * 60)
    print("[Self_Code_Analyzer] 자기 소스 코드 분석 시작")
    print("=" * 60)

    total_issues = 0
    for fname, fpath in targets:
        issues = analyze_file(fpath)
        line_count = sum(1 for _ in open(fpath, encoding='utf-8', errors='replace'))
        print(f"\n📄 {fname} ({line_count}줄) — 이슈 {len(issues)}건")
        if issues:
            for issue in issues:
                print(f"  {issue}")
            total_issues += len(issues)
        else:
            print("  ✅ 이슈 없음")

    print("\n" + "=" * 60)
    print(f"분석 완료: {len(targets)}개 파일, 총 {total_issues}건 이슈 발견")
    print("=" * 60)

if __name__ == "__main__":
    main()
