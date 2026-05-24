# -*- coding: utf-8 -*-
"""
stock_tiger_tentacle.py (v2 - 실시간 API)
- 네이버 금융 실시간 API로 TIGER Fn반도체TOP10 (396650) 주가 조회
- 전일 종가 대비 변동폭이 1% 이상일 때만 알림 전송
- 하루 1회 쿨다운
"""
import os
import sys
import io
import json
import requests
from datetime import datetime

# 콘솔 출력 UTF-8 강제 지정 (윈도우 환경 이모지 출력 에러 방지, 가로채기 방어)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
DATA_FILE = os.path.join(DATA_DIR, "stock_tiger.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

# [오리지널 코드 보존]
# STOCK_CODE = "396650"
# STOCK_NAME = "TIGER Fn반도체TOP10"

# [수정 코드] 동적 설정 로드 및 오타 정정(396650 -> 396500) 폴백 적용
STOCK_CODE = "396500"
STOCK_NAME = "TIGER Fn반도체TOP10"
ALERT_THRESHOLD = 1.0

try:
    CONFIG_FILE = os.path.join(DATA_DIR, "stock_config.json")
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            STOCK_CODE = config.get("stock_code", STOCK_CODE)
            STOCK_NAME = config.get("stock_name", STOCK_NAME)
            ALERT_THRESHOLD = float(config.get("alert_threshold_percent", ALERT_THRESHOLD))
except Exception as e:
    print(f"[WARN] 설정 파일 로드 실패, 기본값 사용: {e}")

# 실행 시각 조건 (오전 10:00~10:05 사이)
now = datetime.now()
TARGET_HOUR = 10
TEST_MODE = False  # True로 설정하면 시간 무시하고 즉시 실행

is_target_time = (now.hour == TARGET_HOUR and 0 <= now.minute < 5)
if not TEST_MODE and not is_target_time:
    sys.exit(0)

# 주말 스킵
if not TEST_MODE and now.weekday() >= 5:
    print("[INFO] 주말 - 주식 알림 스킵")
    sys.exit(0)

# 하루 1회 쿨다운 체크
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            stored = json.load(f)
        if stored.get("date") == now.strftime("%Y-%m-%d"):
            print("[INFO] 오늘 이미 전송. 종료.")
            sys.exit(0)
    except Exception:
        pass

def get_stock_price():
    """네이버 금융 실시간 API로 현재가 조회"""
    try:
        url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{STOCK_CODE}"
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
        data = res.json()
        item = data['result']['areas'][0]['datas'][0]
        return {
            "price": int(item.get("nv", 0)),       # 현재가
            "change": int(item.get("cv", 0)),       # 전일 대비
            "rate": float(item.get("cr", 0.0)),     # 등락률(%)
        }
    except Exception as e:
        print(f"[ERROR] 네이버 금융 API 실패: {e}")
        return None

def emit_signal(message):
    try:
        signals = {}
        if os.path.exists(SIGNAL_FILE):
            try:
                with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
            except Exception:
                signals = {}
        signals["stock_tiger_tentacle.py"] = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "message": message
        }
        tmp = SIGNAL_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(signals, f, indent=4, ensure_ascii=False)
        os.replace(tmp, SIGNAL_FILE)
    except Exception as e:
        print(f"[ERROR] 신호 저장 실패: {e}")

def save_cooldown():
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({"date": now.strftime("%Y-%m-%d")}, f, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except Exception as e:
        print(f"[ERROR] 쿨다운 저장 실패: {e}")

# 주가 조회
stock = get_stock_price()

if stock is None:
    # API 실패 시 링크만 전달
    message = (
        f"📈 [{STOCK_NAME} ({STOCK_CODE})] 주가 조회 실패\n"
        f"👉 직접 확인: https://finance.naver.com/item/main.naver?code={STOCK_CODE}"
    )
else:
    price_str = f"{stock['price']:,}"
    change = stock["change"]
    rate = stock["rate"]
    sign = "▲" if change > 0 else "▼" if change < 0 else "-"

    # [오리지널 코드 보존]
    # # 등락률 1% 미만이면 알림 스킵 (노이즈 감소)
    # if abs(rate) < 1.0 and not TEST_MODE:
    #     print(f"[INFO] 등락률 {rate:.2f}% - 1% 미만이라 알림 생략.")
    #     save_cooldown()
    #     sys.exit(0)

    # [수정 코드] 동적 임계값 비교 및 알림 제어 (임계값이 0.0이면 항상 알림)
    if ALERT_THRESHOLD > 0.0 and abs(rate) < ALERT_THRESHOLD and not TEST_MODE:
        print(f"[INFO] 등락률 {rate:.2f}% - {ALERT_THRESHOLD}% 미만이라 알림 생략.")
        save_cooldown()
        sys.exit(0)

    message = (
        f"📈 [주식 변동 알림]\n\n"
        f"**{STOCK_NAME} ({STOCK_CODE})**\n"
        f"현재가: {price_str}원\n"
        f"전일 대비: {sign}{abs(change):,}원 ({rate:+.2f}%)\n\n"
        f"👉 https://finance.naver.com/item/main.naver?code={STOCK_CODE}"
    )

emit_signal(message)
save_cooldown()
print(f"[SUCCESS] 주식 알림 전송 완료:\n{message}")
