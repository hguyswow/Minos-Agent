# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: reminder_skill
# AGENT_SKILL_DESC: 텔레그램 알람 예약. "N분 후에 ~해줘", "오후 3시에 ~알려줘" 같은 자연어로 예약 가능.
# AGENT_SKILL_ARGS: message(str) - 알람 메시지, time_str(str) - 시간 표현 (예: "30분 후", "오후 3시", "2026-05-06 09:00")
# AGENT_SKILL_RETURNS: 예약 결과 메시지
import sys
import os
import json
import re
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_DIR = os.path.join(BASE_DIR, "state")
REMINDER_FILE = os.path.join(STATE_DIR, "reminders.json")
os.makedirs(STATE_DIR, exist_ok=True)

def parse_time(time_str: str) -> datetime:
    """자연어 시간 표현을 datetime으로 변환"""
    now = datetime.now()
    time_str = time_str.strip()

    # 패턴 1: N분 후
    m = re.match(r'(\d+)\s*분\s*후', time_str)
    if m:
        return now + timedelta(minutes=int(m.group(1)))

    # 패턴 2: N시간 후
    m = re.match(r'(\d+)\s*시간\s*후', time_str)
    if m:
        return now + timedelta(hours=int(m.group(1)))

    # 패턴 3: 오전/오후 N시 (N분)
    m = re.match(r'(오전|오후)?\s*(\d{1,2})시\s*(\d{1,2})?분?', time_str)
    if m:
        am_pm = m.group(1) or ""
        hour = int(m.group(2))
        minute = int(m.group(3)) if m.group(3) else 0
        if am_pm == "오후" and hour < 12:
            hour += 12
        elif am_pm == "오전" and hour == 12:
            hour = 0
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)  # 이미 지난 시간이면 내일로
        return target

    # 패턴 4: YYYY-MM-DD HH:MM
    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        pass

    # 패턴 5: HH:MM
    try:
        t = datetime.strptime(time_str, "%H:%M")
        target = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target
    except ValueError:
        pass

    raise ValueError(f"시간 형식을 인식할 수 없습니다: '{time_str}'")

def load_reminders():
    if os.path.exists(REMINDER_FILE):
        try:
            with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_reminders(reminders):
    tmp = REMINDER_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)
    os.replace(tmp, REMINDER_FILE)

def add_reminder(message: str, time_str: str) -> str:
    try:
        target_dt = parse_time(time_str)
    except ValueError as e:
        return f"❌ 시간 파싱 실패: {e}\n사용 예: '30분 후', '오후 3시', '오전 10시 30분', '2026-05-06 09:00'"

    reminders = load_reminders()
    reminders.append({
        "id": len(reminders) + 1,
        "message": message,
        "target": target_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sent": False
    })
    save_reminders(reminders)

    diff = target_dt - datetime.now()
    mins = int(diff.total_seconds() // 60)
    time_label = target_dt.strftime("%Y-%m-%d %H:%M")

    return (
        f"⏰ 알람이 등록되었습니다!\n\n"
        f"📌 내용: {message}\n"
        f"🕐 예정: {time_label} ({mins}분 후)\n"
        f"📋 총 예약 수: {len(reminders)}개"
    )

def list_reminders() -> str:
    reminders = [r for r in load_reminders() if not r.get("sent")]
    if not reminders:
        return "📭 예약된 알람이 없습니다."
    lines = ["⏰ 예약된 알람 목록:\n"]
    for r in reminders:
        lines.append(f"  [{r['id']}] {r['target']} - {r['message']}")
    return "\n".join(lines)

# ─── 메인 실행 (스킬로 호출될 때) ───
if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 2:
        result = add_reminder(args[0], args[1])
        print(result)
    elif len(args) == 1 and args[0] == "list":
        print(list_reminders())
    else:
        print("사용법:")
        print('  python reminder_skill.py "약 먹기" "30분 후"')
        print('  python reminder_skill.py "회의 준비" "오후 2시 30분"')
        print('  python reminder_skill.py list')
