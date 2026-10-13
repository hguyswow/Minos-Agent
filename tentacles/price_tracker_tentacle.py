# -*- coding: utf-8 -*-
"""
price_tracker_tentacle.py
  URL      
 : tentacles/data/price_targets.json

  :
[
  {
    "name": "  M3",
    "url": "https://www.coupang.com/vp/products/...",
    "target_price": 1500000,
    "site": "coupang"
  }
]
"""
import os
import sys
import json
import re
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
CONFIG_FILE = os.path.join(DATA_DIR, "price_targets.json")
HISTORY_FILE = os.path.join(DATA_DIR, "price_history.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

#     ( )
if not os.path.exists(CONFIG_FILE):
    default_config = [
        {
            "name": "  ( )",
            "url": "https://www.coupang.com/vp/products/example",
            "target_price": 100000,
            "site": "coupang",
            "active": False
        }
    ]
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    print(f"[INFO]   : {CONFIG_FILE}")
    print("[INFO]  URL    active true .")
    sys.exit(0)

#  
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        targets = json.load(f)
except Exception as e:
    print(f"[ERROR]    : {e}")
    sys.exit(1)

#   
try:
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        history = json.load(f)
except Exception:
    history = {}

now = datetime.now()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_coupang_price(url):
    """  """
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        #   : ""  class="price-value"
        match = re.search(r'"priceValue"\s*:\s*(\d+)', res.text)
        if not match:
            match = re.search(r'class="price-value[^"]*"[^>]*>([0-9,]+)', res.text)
        if match:
            price_str = match.group(1).replace(',', '')
            return int(price_str)
    except Exception as e:
        print(f"[ERROR]    : {e}")
    return None

def get_naver_price(url):
    """  """
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        match = re.search(r'"lowPrice"\s*:\s*"?(\d+)"?', res.text)
        if not match:
            match = re.search(r'class="price[^"]*"[^>]*>\s*([0-9,]+)', res.text)
        if match:
            return int(match.group(1).replace(',', ''))
    except Exception as e:
        print(f"[ERROR]    : {e}")
    return None

alerts = []
updated_history = dict(history)

for item in targets:
    if not item.get("active", True):
        continue

    name = item.get("name", "")
    url = item.get("url", "")
    target_price = item.get("target_price", 0)
    site = item.get("site", "").lower()

    print(f"[CHECK] {name} ({site})   ...")

    current_price = None
    if "coupang" in site or "coupang" in url:
        current_price = get_coupang_price(url)
    elif "naver" in site or "naver" in url or "smartstore" in url:
        current_price = get_naver_price(url)

    if current_price is None:
        print(f"  [SKIP]   ")
        continue

    prev_price = updated_history.get(name, {}).get("price")
    updated_history[name] = {
        "price": current_price,
        "timestamp": now.strftime("%Y-%m-%d %H:%M"),
        "url": url
    }

    print(f"  : {current_price:,} / : {target_price:,}")

    if current_price <= target_price:
        diff = target_price - current_price
        alert_msg = (
            f" [ ]  !\n\n"
            f" {name}\n"
            f"[MONEY] : {current_price:,}\n"
            f"[TARGET] : {target_price:,} ( {diff:,} )\n"
            f" {url}"
        )
        if prev_price:
            alert_msg += f"\n[CHART]  : {prev_price:,}"
        alerts.append(alert_msg)
        print(f"  [ALERT]  !")

#  
tmp = HISTORY_FILE + ".tmp"
try:
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(updated_history, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HISTORY_FILE)
except Exception as e:
    print(f"[ERROR]   : {e}")

#  
if alerts:
    full_message = "\n\n---\n\n".join(alerts)
    try:
        signals = {}
        if os.path.exists(SIGNAL_FILE):
            try:
                with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
            except Exception:
                signals = {}
        signals["price_tracker_tentacle.py"] = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "message": full_message
        }
        tmp = SIGNAL_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(signals, f, indent=4, ensure_ascii=False)
        os.replace(tmp, SIGNAL_FILE)
        print(f"[SUCCESS]   {len(alerts)}  ")
    except Exception as e:
        print(f"[ERROR]   : {e}")
else:
    print(f"[INFO]    .  ...")
