import os
import sys
import json
from datetime import datetime

# --- 설정 ---
TARGET_HOUR = 10
TARGET_MINUTE = 0

# [테스트 모드] True로 설정하면 시간을 무시하고 무조건 1회 실행
TEST_MODE = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "stock_tiger.json")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")

now = datetime.now()

is_target_time = (now.hour == TARGET_HOUR and TARGET_MINUTE <= now.minute < TARGET_MINUTE + 5)

if not TEST_MODE and not is_target_time:
    sys.exit(0)

# 이미 오늘 알림을 보냈는지 확인
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_date = data.get("date")
            if last_date == now.strftime("%Y-%m-%d"):
                sys.exit(0)
    except:
        pass

print(f"[INFO] TIGER 반도체 주가 정보 수집 시작...")

message = "TIGER Fn반도체TOP10 (396500) 현재가 변동 알림 시간입니다.\n자세한 정보는 아래 알파스퀘어 링크를 확인하세요:\nhttps://alphasquare.co.kr/home/stock-summary?code=396500"

# 데이터 저장 (중복 방지용)
output_data = {
    "date": now.strftime("%Y-%m-%d")
}
with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False)

# 신호망(Signal)에 쏘기
try:
    if os.path.exists(SIGNAL_FILE):
        with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
            signals = json.load(f)
    else:
        signals = {}
except:
    signals = {}

signals["stock_tiger_tentacle.py"] = {
    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
    "message": message
}

with open(SIGNAL_FILE, 'w', encoding='utf-8') as f:
    json.dump(signals, f, indent=4, ensure_ascii=False)

print("[INFO] 주식 신호 발송 완료.")
