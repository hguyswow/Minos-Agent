# -*- coding: utf-8 -*-
"""
daily_digest_tentacle.py
매일 오전 8시 날씨 + 뉴스 TOP3 + 주식을 하나의 메시지로 통합 전송
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

# 시간 체크 (오전 8:00~8:05)
if not TEST_MODE and not (now.hour == TARGET_HOUR and now.minute < 5):
    sys.exit(0)

# 하루 1회 쿨다운
if os.path.exists(COOLDOWN_FILE):
    try:
        with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == now.strftime("%Y-%m-%d"):
                print("[INFO] 오늘 다이제스트 이미 전송. 종료.")
                sys.exit(0)
    except Exception:
        pass

# ─── 1. 날씨 조회 (Open-Meteo) ───
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
        desc = {0:"맑음",1:"대체로 맑음",2:"구름 조금",3:"흐림",
                45:"안개",51:"가랑비",61:"비",71:"눈",80:"소나기",95:"뇌우"}.get(code, "알수없음")
        return f"🌡 {temp}°C / {desc}"
    except Exception as e:
        return f"날씨 조회 실패 ({e})"

# ─── 2. 뉴스 TOP3 (Google News RSS) ───
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
        return "\n".join(lines) if lines else "  뉴스 없음"
    except Exception as e:
        return f"  뉴스 조회 실패 ({e})"

# ─── 3. 주식 (네이버 금융 API) ───
def get_stock():
    STOCK_CODE = "396650"
    STOCK_NAME = "TIGER Fn반도체TOP10"
    try:
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{STOCK_CODE}"
        res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        item = res.json()['result']['areas'][0]['datas'][0]
        price = int(item.get("nv", 0))
        change = int(item.get("cv", 0))
        rate = float(item.get("cr", 0.0))
        sign = "▲" if change > 0 else "▼" if change < 0 else "-"
        return f"  {STOCK_NAME}: {price:,}원 {sign}{abs(change):,} ({rate:+.2f}%)"
    except Exception:
        # 주말이거나 API 실패 시
        if now.weekday() >= 5:
            return "  주말 (주식 시장 휴장)"
        return f"  https://finance.naver.com/item/main.naver?code={STOCK_CODE}"

# ─── 메시지 조합 ───
weather_str = get_weather()
news_str = get_news()
stock_str = get_stock()

weekdays_ko = ["월", "화", "수", "목", "금", "토", "일"]
day_ko = weekdays_ko[now.weekday()]

message = f"""☀️ [{now.strftime(f'%Y-%m-%d ({day_ko})')} 모닝 다이제스트]

🌤 **서울 날씨**
  {weather_str}

📰 **오늘의 IT 뉴스 TOP3**
{news_str}

📈 **주식 현황**
{stock_str}

좋은 하루 되세요! 💪"""

# ─── 신호 저장 ───
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
        print(f"[ERROR] 신호 저장 실패: {e}")

emit_signal(message)

# 쿨다운 저장
try:
    with open(COOLDOWN_FILE, 'w', encoding='utf-8') as f:
        f.write(now.strftime("%Y-%m-%d"))
except Exception as e:
    print(f"[ERROR] 쿨다운 저장 실패: {e}")

print(f"[SUCCESS] 모닝 다이제스트 전송 완료:\n{message}")
