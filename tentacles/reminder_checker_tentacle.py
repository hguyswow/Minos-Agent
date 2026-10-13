# -*- coding: utf-8 -*-
"""
reminder_checker_tentacle.py
tentacle_daemon.py 1  →       
"""
import os
import sys
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")

#     (tentacles/  )
PROJECT_DIR = os.path.dirname(BASE_DIR)
REMINDER_FILE = os.path.join(PROJECT_DIR, "state", "reminders.json")

os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

if not os.path.exists(REMINDER_FILE):
    sys.exit(0)

try:
    with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
        reminders = json.load(f)
except Exception:
    sys.exit(0)

now = datetime.now()
triggered = []
updated = []

for r in reminders:
    if r.get("sent"):
        updated.append(r)
        continue
    try:
        target_dt = datetime.strptime(r["target"], "%Y-%m-%d %H:%M:%S")
    except Exception:
        updated.append(r)
        continue

    if now >= target_dt:
        triggered.append(r)
        r["sent"] = True
    updated.append(r)

if not triggered:
    sys.exit(0)

#   
tmp = REMINDER_FILE + ".tmp"
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(updated, f, ensure_ascii=False, indent=2)
os.replace(tmp, REMINDER_FILE)

#  
full_msg = "\n\n".join([
    f"⏰ []\n\n{r['message']}"
    for r in triggered
])

try:
    signals = {}
    if os.path.exists(SIGNAL_FILE):
        try:
            with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                signals = json.load(f)
        except Exception:
            signals = {}
    signals["reminder_checker_tentacle.py"] = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "message": full_msg
    }
    tmp = SIGNAL_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(signals, f, indent=4, ensure_ascii=False)
    os.replace(tmp, SIGNAL_FILE)
    print(f"[SUCCESS]  {len(triggered)} ")
except Exception as e:
    print(f"[ERROR]   : {e}")
