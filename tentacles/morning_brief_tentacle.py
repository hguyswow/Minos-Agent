# -*- coding: utf-8 -*-
"""
morning_brief_tentacle.py (v4 - 중복 방지 강화)
- 구글 뉴스 IT/과학 RSS를 파싱해 새 뉴스만 알림
- 뉴스 제목 해시(SHA256)를 히스토리에 저장하여 중복 원천 차단
- 하루 1회 쿨다운 유지
"""
import os
import sys
import json
import hashlib
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
HISTORY_FILE = os.path.join(DATA_DIR, "news_history.json")
COOLDOWN_FILE = os.path.join(DATA_DIR, "morning_brief_cooldown.txt")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

# RSS 피드 목록
RSS_FEEDS = [
    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=ko&gl=KR&ceid=KR:ko",
]

def title_hash(title):
    """뉴스 제목의 핵심 부분을 해시화 (출처명 제거 후)"""
    core = title.split(" - ")[0].strip()
    return hashlib.sha256(core.encode("utf-8")).hexdigest()[:16]

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_history(history_set):
    """원자적 저장으로 파일 손상 방지"""
    tmp = HISTORY_FILE + ".tmp"
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(list(history_set)[-200:], f, ensure_ascii=False)
        os.replace(tmp, HISTORY_FILE)
    except Exception as e:
        print(f"[ERROR] 히스토리 저장 실패: {e}")

def get_new_news(limit=5):
    history = load_history()
    new_items = []

    for url in RSS_FEEDS:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            res.encoding = 'utf-8'
            root = ET.fromstring(res.text)
            for item in root.findall('.//item'):
                try:
                    title_el = item.find('title')
                    link_el = item.find('link')
                    if title_el is None or link_el is None:
                        continue
                    title = title_el.text or ""
                    link = link_el.text or ""
                    h = title_hash(title)
                    if h in history:
                        continue
                    new_items.append({"title": title, "link": link, "hash": h})
                except Exception:
                    continue
        except Exception as e:
            print(f"[ERROR] RSS 파싱 실패 ({url}): {e}")

    # 중복 제목 제거 후 limit개 선택
    seen = set()
    unique = []
    for item in new_items:
        core = item["title"].split(" - ")[0].strip()
        if core in seen:
            continue
        seen.add(core)
        unique.append(item)
        if len(unique) >= limit:
            break

    return unique

def emit_signal(message, now):
    """신호 파일에 원자적 저장"""
    try:
        signals = {}
        if os.path.exists(SIGNAL_FILE):
            try:
                with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
            except Exception:
                signals = {}
        signals["morning_brief_tentacle.py"] = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "message": message
        }
        tmp = SIGNAL_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(signals, f, indent=4, ensure_ascii=False)
        os.replace(tmp, SIGNAL_FILE)
    except Exception as e:
        print(f"[ERROR] 신호 저장 실패: {e}")

# ─── 메인 실행 ───
now = datetime.now()

# 하루 1회 쿨다운 체크
if os.path.exists(COOLDOWN_FILE):
    try:
        with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
            last_date = f.read().strip()
        if last_date == now.strftime("%Y-%m-%d"):
            print("[INFO] 오늘 이미 전송 완료. 종료.")
            sys.exit(0)
    except Exception:
        pass

# 새 뉴스 가져오기
news_list = get_new_news(5)

if not news_list:
    print("[INFO] 새로운 뉴스 없음 (히스토리에 모두 있음).")
    sys.exit(0)

# 메시지 조합
msg_parts = ["✨ **오늘의 IT/과학 뉴스 브리핑** ✨\n"]
new_hashes = set()
for i, news in enumerate(news_list, 1):
    title = news["title"].rsplit(" - ", 1)[0]
    link = news.get("link", "")
    msg_parts.append(f"{i}. **{title}**\n   🔗 {link}")
    new_hashes.add(news["hash"])

msg_parts.append("\n오늘도 좋은 하루 되세요! 😊")
full_message = "\n".join(msg_parts)

# 히스토리 업데이트 (신호 발송 성공 후에 저장)
emit_signal(full_message, now)

history = load_history()
history.update(new_hashes)
save_history(history)

# 쿨다운 파일 기록
try:
    with open(COOLDOWN_FILE, 'w', encoding='utf-8') as f:
        f.write(now.strftime("%Y-%m-%d"))
except Exception as e:
    print(f"[ERROR] 쿨다운 파일 저장 실패: {e}")

print(f"[SUCCESS] 뉴스 브리핑 전송 완료 ({len(news_list)}건):\n{full_message}")
