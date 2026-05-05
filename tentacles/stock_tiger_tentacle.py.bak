import os
import sys
import json
from datetime import datetime

# ---  ---
TARGET_HOUR = 10
TARGET_MINUTE = 0

# [ ] True     1 
TEST_MODE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "stock_tiger.json")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")

now = datetime.now()

is_target_time = (now.hour == TARGET_HOUR and TARGET_MINUTE <= now.minute < TARGET_MINUTE + 5)

if not TEST_MODE and not is_target_time:
    sys.exit(0)

#     
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_date = data.get("date")
            if last_date == now.strftime("%Y-%m-%d"):
                sys.exit(0)
    except:
        pass

print(f"[INFO] TIGER     ...")

message = "TIGER FnTOP10 (396500)    .\n     :\nhttps://alphasquare.co.kr/home/stock-summary?code=396500"

#   ( )
output_data = {
    "date": now.strftime("%Y-%m-%d")
}
temp_data_file = DATA_FILE + ".tmp"
with open(temp_data_file, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False)
os.replace(temp_data_file, DATA_FILE)

# (Signal) 
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

temp_signal_file = SIGNAL_FILE + ".tmp"
with open(temp_signal_file, 'w', encoding='utf-8') as f:
    json.dump(signals, f, indent=4, ensure_ascii=False)
os.replace(temp_signal_file, SIGNAL_FILE)

print("[INFO]    .")
