import os
import sys
import json
from datetime import datetime
import urllib.request
import xml.etree.ElementTree as ET

# --- 설정 ---
TARGET_HOUR = 5
TARGET_MINUTE = 15

# [테스트 모드] True로 설정하면 시간을 무시하고 무조건 1회 실행 후 당일 날짜를 기록합니다.
TEST_MODE = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "morning_brief.json")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")

now = datetime.now()

# 1. 쿨타임 및 시간 체크
is_target_time = (now.hour == TARGET_HOUR and TARGET_MINUTE <= now.minute < TARGET_MINUTE + 5)

if not TEST_MODE and not is_target_time:
    sys.exit(0)

# 이미 오늘 브리핑을 했는지 확인
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_date = data.get("date")
            if last_date == now.strftime("%Y-%m-%d"):
                sys.exit(0) # 오늘 이미 완료함
    except:
        pass

print(f"[INFO] 출근길 브리핑 스크래핑 시작...")

# 2. 데이터 스크래핑 (동아일보 IT/과학 RSS 파싱)
try:
    url = "https://rss.donga.com/science.xml"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read()
    
    root = ET.fromstring(html)
    items = root.findall('.//item')[:3]
    
    news_list = []
    for item in items:
        title = item.find('title').text
        link = item.find('link').text
        news_list.append(f"- {title} ({link})")
        
    news_text = "\n".join(news_list)
except Exception as e:
    news_text = f"뉴스 스크래핑 실패: {e}"

# 3. 데이터 저장
output_data = {
    "date": now.strftime("%Y-%m-%d"),
    "news": news_text
}
with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False)

# 4. 신호망(Signal)에 쏘기
try:
    if os.path.exists(SIGNAL_FILE):
        with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
            signals = json.load(f)
    else:
        signals = {}
except:
    signals = {}

signals["morning_brief_tentacle.py"] = {
    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
    "message": f"오늘의 출근길 IT 뉴스 브리핑입니다.\n\n{news_text}"
}

with open(SIGNAL_FILE, 'w', encoding='utf-8') as f:
    json.dump(signals, f, indent=4, ensure_ascii=False)

print("[INFO] 브리핑 신호 발송 완료.")
