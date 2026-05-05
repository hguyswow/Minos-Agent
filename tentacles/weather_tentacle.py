# -*- coding: utf-8 -*-
"""
weather_tentacle.py
Open-Meteo 무료 API로 실시간 날씨 조회 후 신호 발송 (3시간 쿨다운)
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

# 3시간 쿨다운 체크
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        last_str = cache.get("updated", "")
        if last_str:
            last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M")
            if datetime.now() - last_dt < timedelta(hours=INTERVAL_HOURS):
                print(f"[INFO] {INTERVAL_HOURS}시간 쿨다운 중. 종료.")
                sys.exit(0)
    except Exception:
        pass

# Open-Meteo API (서울 좌표)
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

        # WMO 날씨 코드 → 한국어 설명
        weather_desc = {
            0: "맑음", 1: "대체로 맑음", 2: "부분적 흐림", 3: "흐림",
            45: "안개", 48: "안개(빙결)", 51: "가랑비", 53: "보통 가랑비",
            55: "강한 가랑비", 61: "약한 비", 63: "보통 비", 65: "강한 비",
            71: "약한 눈", 73: "보통 눈", 75: "강한 눈", 80: "소나기",
            95: "뇌우", 99: "강한 뇌우"
        }.get(code, f"날씨코드:{code}")

        return temp, weather_desc, wind
    except Exception as e:
        print(f"[ERROR] 날씨 API 실패: {e}")
        return None, None, None

temp, desc, wind = get_weather()

if temp is None:
    sys.exit(1)

now = datetime.now()
message = (
    f"🌤 [서울 날씨 업데이트]\n\n"
    f"🌡 기온: {temp}°C\n"
    f"☁ 날씨: {desc}\n"
    f"💨 풍속: {wind} km/h\n\n"
    f"📅 {now.strftime('%Y-%m-%d %H:%M')} 기준"
)

# 신호 저장
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
    print(f"[ERROR] 신호 저장 실패: {e}")

# 캐시 저장
try:
    cache_data = {"temperature": temp, "desc": desc, "wind": wind, "updated": now.strftime("%Y-%m-%d %H:%M")}
    tmp = DATA_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)
except Exception as e:
    print(f"[ERROR] 캐시 저장 실패: {e}")

print(f"[SUCCESS] 날씨 알림 전송 완료:\n{message}")