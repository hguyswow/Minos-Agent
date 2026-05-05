# -*- coding: utf-8 -*-
"""
스킬명: Memory_Cleaner
기능: memory_logs 디렉터리를 스캔하여 깨진 JSON, 중복 대화,
      오래된 불필요한 기억 항목을 탐지하고 정리합니다.
사용법:
  Memory_Cleaner.py              — 실제 정리 실행
  Memory_Cleaner.py --dry-run   — 분석만 하고 실제 삭제는 안 함
  Memory_Cleaner.py --report    — 기억 용량 현황만 리포트
"""
import os
import sys
import json
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEMORY_DIR  = os.path.join(BASE_DIR, 'memory_logs')

def get_size_str(nbytes):
    if nbytes < 1024:
        return f"{nbytes}B"
    elif nbytes < 1024 * 1024:
        return f"{nbytes/1024:.1f}KB"
    else:
        return f"{nbytes/1024/1024:.1f}MB"

def main():
    dry_run   = '--dry-run' in sys.argv
    report_only = '--report' in sys.argv

    if dry_run:
        print("[Memory_Cleaner] 드라이런 모드 — 분석만 실행, 실제 변경 없음")
    elif report_only:
        print("[Memory_Cleaner] 리포트 모드")

    if not os.path.exists(MEMORY_DIR):
        print(f"[Memory_Cleaner] 기억 폴더가 없습니다: {MEMORY_DIR}")
        sys.exit(0)

    mem_files = [f for f in os.listdir(MEMORY_DIR) if f.endswith('.json')]
    total_size = sum(os.path.getsize(os.path.join(MEMORY_DIR, f)) for f in mem_files)

    print(f"\n[Memory_Cleaner] 기억 파일 현황: {len(mem_files)}개 ({get_size_str(total_size)})")
    print("=" * 60)

    broken_files    = []   # JSON 파싱 불가
    empty_memories  = []   # working_memory가 빈 파일
    oversized       = []   # 100KB 초과 파일
    cleaned_count   = 0
    saved_bytes     = 0

    for fname in mem_files:
        fpath = os.path.join(MEMORY_DIR, fname)
        fsize = os.path.getsize(fpath)

        # 1. JSON 파싱 체크
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            broken_files.append((fname, str(e)))
            print(f"  ❌ 깨진 JSON: {fname} — {e}")
            if not dry_run and not report_only:
                os.remove(fpath)
                cleaned_count += 1
                saved_bytes   += fsize
                print(f"     → 삭제 완료")
            continue
        except UnicodeDecodeError as e:
            broken_files.append((fname, f"인코딩 오류: {e}"))
            print(f"  ❌ 인코딩 오류: {fname}")
            continue

        # 2. 빈 기억 체크
        wm = data.get('working_memory', [])
        lm_keys = [k for k in data if k not in ('working_memory',)]
        if not wm and not lm_keys:
            empty_memories.append(fname)
            print(f"  ⚠️  빈 기억 파일: {fname}")
            if not dry_run and not report_only:
                os.remove(fpath)
                cleaned_count += 1
                saved_bytes   += fsize
                print(f"     → 삭제 완료")
            continue

        # 3. 초과 크기 체크 및 working_memory 압축
        if fsize > 100 * 1024:  # 100KB 초과
            oversized.append((fname, fsize))
            print(f"  ⚠️  대용량 기억: {fname} ({get_size_str(fsize)})")

            if not dry_run and not report_only and wm:
                # 최근 30개만 남기고 나머지 트리밍
                original_len = len(wm)
                data['working_memory'] = wm[-30:]
                trimmed_len = len(data['working_memory'])
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                new_size = os.path.getsize(fpath)
                diff = fsize - new_size
                saved_bytes += diff
                cleaned_count += 1
                print(f"     → 기억 트리밍 완료: {original_len}개 → {trimmed_len}개 ({get_size_str(diff)} 절약)")

        # 4. 간단한 중복 메시지 탐지
        if wm:
            seen = set()
            dupes = 0
            for msg in wm:
                key = (msg.get('role', ''), msg.get('content', '')[:50])
                if key in seen:
                    dupes += 1
                seen.add(key)
            if dupes > 0:
                print(f"  ℹ️  중복 메시지 {dupes}개 감지: {fname}")

    print("\n" + "=" * 60)
    print(f"[결과 요약]")
    print(f"  ❌ 깨진 파일: {len(broken_files)}건")
    print(f"  ⚠️  빈 기억 파일: {len(empty_memories)}건")
    print(f"  📦 대용량 파일: {len(oversized)}건")
    if not dry_run and not report_only:
        print(f"  🧹 정리된 항목: {cleaned_count}건 ({get_size_str(saved_bytes)} 절약)")
    else:
        print(f"  [드라이런/리포트 모드] 실제 변경 없음")
    print("=" * 60)

    total_issues = len(broken_files) + len(empty_memories)
    if total_issues == 0:
        print("✅ 기억 데이터가 건강한 상태입니다!")
    else:
        print(f"⚠️  총 {total_issues}건의 이슈가 발견되었습니다.")
        if dry_run:
            print("   '--dry-run' 옵션 없이 실행하면 자동 정리됩니다.")

if __name__ == "__main__":
    main()
