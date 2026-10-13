# -*- coding: utf-8 -*-
"""
daily_digest_tentacle.py
  8  +  TOP3 +     
"""
import os
import sys
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
COOLDOWN_FILE = os.path.join(DATA_DIR, "daily_digest_cooldown.txt")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

now = datetime.now()
TARGET_HOUR = 8
TEST_MODE = False

#   ( 8:00~8:05)
if not TEST_MODE and not (now.hour == TARGET_HOUR and now.minute < 5):
    sys.exit(0)

#  1 
if os.path.exists(COOLDOWN_FILE):
    try:
        with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == now.strftime("%Y-%m-%d"):
                print("[INFO]    . .")
                sys.exit(0)
    except Exception:
        pass

#  1.   (Open-Meteo) 
def get_weather():
    try:
        url = ("https://api.open-meteo.com/v1/forecast"
               "?latitude=37.5665&longitude=126.9780"
               "&current=temperature_2m,weather_code,wind_speed_10m"
               "&timezone=Asia%2FSeoul")
        res = requests.get(url, timeout=8)
        data = res.json()["current"]
        temp = data.get("temperature_2m", "?")
        code = data.get("weather_code", 0)
        desc = {0:"",1:" ",2:" ",3:"",
                45:"",51:"",61:"",71:"",80:"",95:""}.get(code, "")
        return f" {temp}°C / {desc}"
    except Exception as e:
        return f"   ({e})"

#  2.  TOP3 (Google News RSS) 
def get_news():
    try:
        url = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(res.text)
        items = root.findall('.//item')[:3]
        lines = []
        for i, item in enumerate(items, 1):
            title = item.find('title').text or ""
            title = title.rsplit(" - ", 1)[0].strip()
            lines.append(f"  {i}. {title}")
        return "\n".join(lines) if lines else "   "
    except Exception as e:
        return f"     ({e})"

#  3.  (  API) 
def get_stock():
    STOCK_CODE = "396650"
    STOCK_NAME = "TIGER FnTOP10"
    try:
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{STOCK_CODE}"
        res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        item = res.json()['result']['areas'][0]['datas'][0]
        price = int(item.get("nv", 0))
        change = int(item.get("cv", 0))
        rate = float(item.get("cr", 0.0))
        sign = "" if change > 0 else "" if change < 0 else "-"
        return f"  {STOCK_NAME}: {price:,} {sign}{abs(change):,} ({rate:+.2f}%)"
    except Exception:
        #  API  
        if now.weekday() >= 5:
            return "   (  )"
        return f"  https://finance.naver.com/item/main.naver?code={STOCK_CODE}"

#    
weather_str = get_weather()
news_str = get_news()
stock_str = get_stock()

weekdays_ko = ["", "", "", "", "", "", ""]
day_ko = weekdays_ko[now.weekday()]

message = f""" [{now.strftime(f'%Y-%m-%d ({day_ko})')}  ]

 ** **
  {weather_str}

 ** IT  TOP3**
{news_str}

 ** **
{stock_str}

  ! """

#    
def emit_signal(msg):
    try:
        signals = {}
        if os.path.exists(SIGNAL_FILE):
            try:
                with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
            except Exception:
                signals = {}
        signals["daily_digest_tentacle.py"] = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "message": msg
        }
        tmp = SIGNAL_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(signals, f, indent=4, ensure_ascii=False)
        os.replace(tmp, SIGNAL_FILE)
    except Exception as e:
        print(f"[ERROR]   : {e}")

emit_signal(message)

#  
try:
    with open(COOLDOWN_FILE, 'w', encoding='utf-8') as f:
        f.write(now.strftime("%Y-%m-%d"))
except Exception as e:
    print(f"[ERROR]   : {e}")

print(f"[SUCCESS]    :\n{message}")
