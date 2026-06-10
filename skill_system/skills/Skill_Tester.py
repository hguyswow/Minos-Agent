# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Skill_Tester
# AGENT_SKILL_DESC: 특정 스킬을 테스트 인수로 실행하고 결과를 검증합니다. 스킬 개발 후 동작 확인 시 사용합니다.
# AGENT_SKILL_ARGS: skill_name(str) - 테스트할 스킬 파일명, test_args(str) - 테스트 인수
# AGENT_SKILL_RETURNS: 테스트 실행 결과 및 성공/실패 여부
"""
스킬명: Skill_Tester
기능: skills_index.txt에 등록된 스킬들을 테스트 인자로 실행하고
      성공/실패/출력값을 검증하여 리포트를 반환합니다.
사용법:
  Skill_Tester.py              — 전체 스킬 테스트
  Skill_Tester.py "스킬파일명"  — 단일 스킬 테스트 (예: web_search.py)
"""
import os
import sys
import subprocess
import time

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(BASE_DIR, 'skill_system', 'skills')
INDEX_FILE = os.path.join(BASE_DIR, 'skill_system', 'skills_index.txt')

# 스킬별 테스트 인자 정의 (인자 없이 실행 가능한 스킬들은 빈 리스트)
TEST_ARGS = {
    'current_time.py':      [],
    'PC_System_Status.py':  [],
    'clipboard_manager.py': [],
    'process_manager.py':   [],
    'screen_ocr.py':        [],
    'Self_Code_Analyzer.py':['core_engine.py'],
    'Memory_Cleaner.py':    ['--dry-run'],
    'Performance_Logger.py':['report'],
    'todo_note.py':         ['테스트 메모 - Skill_Tester 자동 생성'],
    'Regex_Tester.py':      [r'\d+', 'abc123def456'],
    'Dependency_Manager.py':['check', 'requests'],
    'wiki_search.py':       ['인공지능'],
    'web_search.py':        ['파이썬 최신 버전'],
    'Weather_API_Caller.py':[],
}

def test_skill(skill_file, extra_args=None):
    fpath = os.path.join(SKILLS_DIR, skill_file)
    if not os.path.exists(fpath):
        return 'SKIP', 0, '', f'파일 없음: {fpath}'

    args = extra_args if extra_args is not None else TEST_ARGS.get(skill_file, [])
    cmd = [sys.executable, fpath] + [str(a) for a in args]

    start = time.time()
    try:
        # 기존 subprocess.run 코드 주석 보존
        # result = subprocess.run(
        #     cmd,
        #     capture_output=True,
        #     text=True,
        #     encoding='utf-8',
        #     errors='replace',
        #     timeout=20
        # )
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=20,
            env=env
        )
        elapsed = round(time.time() - start, 2)
        if result.returncode == 0:
            return 'OK', elapsed, result.stdout.strip()[:200], ''
        else:
            return 'FAIL', elapsed, result.stdout.strip()[:100], result.stderr.strip()[:200]
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', 20, '', '20초 타임아웃 초과'
    except Exception as e:
        return 'ERROR', 0, '', str(e)

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        skill_files = [target]
    else:
        # skills_index.txt에서 스킬 파일 목록 추출
        skill_files = []
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # CMD 태그 안에서 .py 파일명 추출
                    import re
                    match = re.search(r'skills\\(\S+\.py)', line)
                    if match:
                        skill_files.append(match.group(1))
        if not skill_files:
            skill_files = [f for f in os.listdir(SKILLS_DIR) if f.endswith('.py')]

    print("=" * 60)
    print(f"[Skill_Tester] 총 {len(skill_files)}개 스킬 테스트 시작")
    print("=" * 60)

    results = {'OK': [], 'FAIL': [], 'TIMEOUT': [], 'SKIP': [], 'ERROR': []}

    for sf in skill_files:
        status, elapsed, out, err = test_skill(sf)
        results[status].append(sf)
        icon = {'OK': '✅', 'FAIL': '❌', 'TIMEOUT': '⏳', 'SKIP': '⏭️', 'ERROR': '💥'}.get(status, '?')
        print(f"\n{icon} [{status}] {sf} ({elapsed}s)")
        if out:
            print(f"   출력: {out[:100]}")
        if err:
            print(f"   오류: {err[:100]}")

    print("\n" + "=" * 60)
    print(f"[결과 요약]")
    print(f"  ✅ 성공: {len(results['OK'])}건")
    print(f"  ❌ 실패: {len(results['FAIL'])}건  {results['FAIL']}")
    print(f"  ⏳ 타임아웃: {len(results['TIMEOUT'])}건")
    print(f"  ⏭️ 스킵: {len(results['SKIP'])}건")
    print(f"  💥 오류: {len(results['ERROR'])}건")
    print("=" * 60)

if __name__ == "__main__":
    main()
