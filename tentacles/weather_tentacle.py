# -*- coding: utf-8 -*-
"""
weather_tentacle.py
Open-Meteo  API       (3 )
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
DATA_FILE = os.path.join(DATA_DIR, "weather_cache.json")
INTERVAL_HOURS = 3

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

# 3  
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        last_str = cache.get("updated", "")
        if last_str:
            last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M")
            if datetime.now() - last_dt < timedelta(hours=INTERVAL_HOURS):
                print(f"[INFO] {INTERVAL_HOURS}  . .")
                sys.exit(0)
    except Exception:
        pass

# Open-Meteo API ( )
LATITUDE = 37.5665
LONGITUDE = 126.9780

def get_weather():
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={LATITUDE}&longitude={LONGITUDE}"
            f"&current=temperature_2m,weather_code,wind_speed_10m"
            f"&timezone=Asia%2FSeoul"
        )
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        current = data.get("current", {})
        temp = current.get("temperature_2m", "N/A")
        code = current.get("weather_code", 0)
        wind = current.get("wind_speed_10m", 0)

        # WMO   →  
        weather_desc = {
            0: "", 1: " ", 2: " ", 3: "",
            45: "", 48: "()", 51: "", 53: " ",
            55: " ", 61: " ", 63: " ", 65: " ",
            71: " ", 73: " ", 75: " ", 80: "",
            95: "", 99: " "
        }.get(code, f":{code}")

        return temp, weather_desc, wind
    except Exception as e:
        print(f"[ERROR]  API : {e}")
        return None, None, None

temp, desc, wind = get_weather()

if temp is None:
    sys.exit(1)

now = datetime.now()
message = (
    f" [  ]\n\n"
    f" : {temp}°C\n"
    f" : {desc}\n"
    f" : {wind} km/h\n\n"
    f" {now.strftime('%Y-%m-%d %H:%M')} "
)

#  
try:
    signals = {}
    if os.path.exists(SIGNAL_FILE):
        try:
            with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                signals = json.load(f)
        except Exception:
            signals = {}
    signals["weather_tentacle.py"] = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "message": message
    }
    tmp = SIGNAL_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(signals, f, indent=4, ensure_ascii=False)
    os.replace(tmp, SIGNAL_FILE)
except Exception as e:
    print(f"[ERROR]   : {e}")

#  
try:
    cache_data = {"temperature": temp, "desc": desc, "wind": wind, "updated": now.strftime("%Y-%m-%d %H:%M")}
    tmp = DATA_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)
except Exception as e:
    print(f"[ERROR]   : {e}")

print(f"[SUCCESS]    :\n{message}")