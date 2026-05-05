# -*- coding: utf-8 -*-
"""
price_tracker_tentacle.py
등록된 상품 URL의 가격이 목표가 이하로 내려가면 텔레그램 알림
설정 파일: tentacles/data/price_targets.json

설정 파일 예시:
[
  {
    "name": "맥북 프로 M3",
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

# 기본 설정 파일 생성 (없을 경우)
if not os.path.exists(CONFIG_FILE):
    default_config = [
        {
            "name": "예시 상품 (수정 필요)",
            "url": "https://www.coupang.com/vp/products/example",
            "target_price": 100000,
            "site": "coupang",
            "active": False
        }
    ]
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 설정 파일 생성됨: {CONFIG_FILE}")
    print("[INFO] 상품 URL과 목표가를 설정한 후 active를 true로 변경하세요.")
    sys.exit(0)

# 설정 로드
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        targets = json.load(f)
except Exception as e:
    print(f"[ERROR] 설정 파일 로드 실패: {e}")
    sys.exit(1)

# 가격 히스토리 로드
try:
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        history = json.load(f)
except Exception:
    history = {}

now = datetime.now()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_coupang_price(url):
    """쿠팡 가격 스크래핑"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        # 쿠팡 가격 패턴: "판매가" 또는 class="price-value"
        match = re.search(r'"priceValue"\s*:\s*(\d+)', res.text)
        if not match:
            match = re.search(r'class="price-value[^"]*"[^>]*>([0-9,]+)', res.text)
        if match:
            price_str = match.group(1).replace(',', '')
            return int(price_str)
    except Exception as e:
        print(f"[ERROR] 쿠팡 가격 조회 실패: {e}")
    return None

def get_naver_price(url):
    """네이버쇼핑 가격 스크래핑"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        match = re.search(r'"lowPrice"\s*:\s*"?(\d+)"?', res.text)
        if not match:
            match = re.search(r'class="price[^"]*"[^>]*>\s*([0-9,]+)', res.text)
        if match:
            return int(match.group(1).replace(',', ''))
    except Exception as e:
        print(f"[ERROR] 네이버 가격 조회 실패: {e}")
    return None

alerts = []
updated_history = dict(history)

for item in targets:
    if not item.get("active", True):
        continue

    name = item.get("name", "알수없음")
    url = item.get("url", "")
    target_price = item.get("target_price", 0)
    site = item.get("site", "").lower()

    print(f"[CHECK] {name} ({site}) 가격 확인 중...")

    current_price = None
    if "coupang" in site or "coupang" in url:
        current_price = get_coupang_price(url)
    elif "naver" in site or "naver" in url or "smartstore" in url:
        current_price = get_naver_price(url)

    if current_price is None:
        print(f"  [SKIP] 가격 조회 실패")
        continue

    prev_price = updated_history.get(name, {}).get("price")
    updated_history[name] = {
        "price": current_price,
        "timestamp": now.strftime("%Y-%m-%d %H:%M"),
        "url": url
    }

    print(f"  현재가: {current_price:,}원 / 목표가: {target_price:,}원")

    if current_price <= target_price:
        diff = target_price - current_price
        alert_msg = (
            f"🛒 [가격 알림] 목표가 달성!\n\n"
            f"📦 {name}\n"
            f"💰 현재가: {current_price:,}원\n"
            f"🎯 목표가: {target_price:,}원 (💸 {diff:,}원 저렴)\n"
            f"🔗 {url}"
        )
        if prev_price:
            alert_msg += f"\n📊 이전 확인: {prev_price:,}원"
        alerts.append(alert_msg)
        print(f"  [ALERT] 목표가 달성!")

# 히스토리 저장
tmp = HISTORY_FILE + ".tmp"
try:
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(updated_history, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HISTORY_FILE)
except Exception as e:
    print(f"[ERROR] 히스토리 저장 실패: {e}")

# 신호 전송
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
        print(f"[SUCCESS] 가격 알림 {len(alerts)}건 전송 완료")
    except Exception as e:
        print(f"[ERROR] 신호 저장 실패: {e}")
else:
    print(f"[INFO] 목표가 달성 상품 없음. 모니터링 중...")
