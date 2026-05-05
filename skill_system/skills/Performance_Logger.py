# -*- coding: utf-8 -*-
"""
스킬명: Performance_Logger
기능: 스킬 실행 결과, 응답 시간, 성공/실패율을 누적 로그로 기록하고
      기간별 통계 리포트를 생성합니다.
사용법:
  Performance_Logger.py log "스킬명" "OK/FAIL" "응답시간(초)"  — 결과 기록
  Performance_Logger.py report                                  — 전체 통계 리포트
  Performance_Logger.py report "스킬명"                         — 특정 스킬 리포트
"""
import os
import sys
import json
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR  = os.path.join(BASE_DIR, 'state')
LOG_FILE = os.path.join(LOG_DIR, 'performance_log.json')

def load_log():
    os.makedirs(LOG_DIR, exist_ok=True)
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"entries": []}
    return {"entries": []}

def save_log(data):
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    if len(sys.argv) < 2:
        print("[오류] 사용법: Performance_Logger.py [log/report] [인자...]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == 'log':
        if len(sys.argv) < 5:
            print("[오류] 사용법: Performance_Logger.py log \"스킬명\" \"OK/FAIL\" \"응답시간\"")
            sys.exit(1)
        skill_name = sys.argv[2]
        status     = sys.argv[3].upper()
        try:
            elapsed = float(sys.argv[4])
        except ValueError:
            elapsed = 0.0

        data = load_log()
        entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "skill":     skill_name,
            "status":    status,
            "elapsed":   elapsed
        }
        data["entries"].append(entry)
        # 최근 1000건만 유지
        data["entries"] = data["entries"][-1000:]
        save_log(data)
        print(f"[Performance_Logger] 기록 완료: {skill_name} | {status} | {elapsed}s")

    elif action == 'report':
        target_skill = sys.argv[2] if len(sys.argv) > 2 else None
        data = load_log()
        entries = data.get("entries", [])

        if not entries:
            print("[Performance_Logger] 기록된 데이터가 없습니다.")
            sys.exit(0)

        # 필터링
        if target_skill:
            entries = [e for e in entries if target_skill.lower() in e.get("skill", "").lower()]
            print(f"[Performance_Logger] '{target_skill}' 전용 리포트 ({len(entries)}건)")
        else:
            print(f"[Performance_Logger] 전체 성능 리포트 ({len(entries)}건)")

        print("=" * 60)

        # 스킬별 집계
        from collections import defaultdict
        skill_stats = defaultdict(lambda: {"ok": 0, "fail": 0, "times": []})
        for e in entries:
            sk = e.get("skill", "unknown")
            st = e.get("status", "UNKNOWN")
            el = e.get("elapsed", 0)
            if st == "OK":
                skill_stats[sk]["ok"] += 1
            else:
                skill_stats[sk]["fail"] += 1
            skill_stats[sk]["times"].append(el)

        for sk, stats in sorted(skill_stats.items()):
            total = stats["ok"] + stats["fail"]
            rate = round(stats["ok"] / total * 100, 1) if total > 0 else 0
            avg_t = round(sum(stats["times"]) / len(stats["times"]), 2) if stats["times"] else 0
            max_t = round(max(stats["times"]), 2) if stats["times"] else 0
            ok_icon = "✅" if rate >= 80 else ("⚠️" if rate >= 50 else "❌")
            print(f"{ok_icon} {sk}")
            print(f"     성공률: {rate}%  |  평균 {avg_t}s  |  최대 {max_t}s  |  총 {total}회")

        # 최근 7일간 일별 실행 수
        print("\n[최근 7일 일별 실행 현황]")
        today = datetime.now().date()
        for i in range(6, -1, -1):
            day = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            day_entries = [e for e in entries if e.get("timestamp", "").startswith(day)]
            ok_cnt  = sum(1 for e in day_entries if e.get("status") == "OK")
            fail_cnt = len(day_entries) - ok_cnt
            bar = "█" * min(ok_cnt, 20)
            print(f"  {day}: {bar} OK={ok_cnt} FAIL={fail_cnt}")

        print("=" * 60)

    else:
        print(f"[오류] 알 수 없는 명령: '{action}'")
        print("사용 가능: log, report")
        sys.exit(1)

if __name__ == "__main__":
    main()
