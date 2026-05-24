# -*- coding: utf-8 -*-
"""
diary_generator_tentacle.py
- 매일 밤 23:50~23:55 사이에 동작
- 오늘 마스터(5339243832)와 나눈 Episodic Memory 대화 기록과 문어발 수집 이벤트를 파싱
- Ollama LLM을 사용하여 알쫑이 톤앤매너로 '오늘의 일기'를 자동 작성
- 시그널을 발행하여 텔레그램으로 자동 브리핑 전송
"""
import os
import sys
import io
import json
import time
import requests
from datetime import datetime

# 콘솔 출력 UTF-8 강제 지정 (윈도우 이모지 깨짐 방지)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
COOLDOWN_FILE = os.path.join(DATA_DIR, "diary_cooldown.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

MASTER_CHAT_ID = "5339243832"
TEST_MODE = False  # 테스트 시 True로 설정하여 강제 실행

# 1. 실행 조건 체크 (23:50 ~ 23:55)
now = datetime.now()
TARGET_HOUR = 23
TARGET_MIN_START = 50
TARGET_MIN_END = 55

is_target_time = (now.hour == TARGET_HOUR and TARGET_MIN_START <= now.minute < TARGET_MIN_END)
if not TEST_MODE and not is_target_time:
    sys.exit(0)

# 2. 쿨다운 체크 (하루 1회)
if os.path.exists(COOLDOWN_FILE):
    try:
        with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
            stored = json.load(f)
        if stored.get("date") == now.strftime("%Y-%m-%d"):
            print("[INFO] 오늘 일기 이미 작성 완료. 종료.")
            sys.exit(0)
    except: pass

def get_today_conversations():
    """오늘 나눈 대화 기록을 에피소딕 파일에서 추출"""
    log_path = os.path.join(BASE_DIR, "..", "memory_logs", f"{MASTER_CHAT_ID}_episodic.jsonl")
    if not os.path.exists(log_path):
        return []
        
    # 오늘 00:00:00 타임스탬프
    today_start = datetime.combine(now.date(), datetime.min.time()).timestamp()
    
    conversations = []
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    ts = data.get("timestamp", 0)
                    if ts >= today_start:
                        role = "형님" if data.get("role") == "user" else "알쫑이"
                        content = data.get("content", "")
                        # CMD 태그 및 시스템 강제 지시 리마인더 제거
                        content = content.split("(※ 시스템 강제 지시")[0].strip()
                        conversations.append(f"{role}: {content}")
                except: pass
    except Exception as e:
        print(f"[ERROR] 대화 추출 실패: {e}")
    return conversations

def get_today_signals():
    """오늘 다른 텐타클들이 보낸 신호 수집"""
    sig_path = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
    signals = []
    if os.path.exists(sig_path):
        try:
            with open(sig_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            today_str = now.strftime("%Y-%m-%d")
            for fname, info in data.items():
                if info.get("timestamp", "").startswith(today_str) and fname != "diary_generator_tentacle.py":
                    signals.append(f"[{fname.replace('_tentacle.py','')}] {info.get('message')}")
        except: pass
    return signals

# 데이터 수집
convs = get_today_conversations()
sigs = get_today_signals()

# 만약 오늘 대화와 신호가 전혀 없다면 일기 작성 생략
if not convs and not sigs and not TEST_MODE:
    print("[INFO] 오늘 대화 및 신호가 없어 일기를 생략합니다.")
    sys.exit(0)

# LLM을 호출하여 알쫑이 톤으로 일기 생성
try:
    # llm_config.json 설정 로드
    condense_url = "http://127.0.0.1:11434/v1/chat/completions"
    condense_model = "gemma4-e4b:q4km"
    api_key = ""
    
    try:
        config_path = os.path.join(BASE_DIR, "..", "llm_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                llm_cfg = json.load(f)
                active = llm_cfg.get("active_engine", "ollama")
                engine = llm_cfg.get("engines", {}).get(active, {})
                condense_url = engine.get("url", condense_url)
                condense_model = engine.get("model", condense_model)
                api_key = engine.get("api_key", api_key)
    except: pass

    conv_text = "\n".join(convs[-30:]) # 최근 30개 위주
    sig_text = "\n".join(sigs)
    
    prompt = (
        f"[치명적 강제 지시] 절대로 생각 과정(Thinking Process/Reasoning)이나 영어 해설을 적지 마십시오! "
        f"이를 작성할 경우 전체 시스템이 마비됩니다. 생각하지 말고, 즉시 최종 완성된 한국어 일기 본문만 바로 작성해 출력하십시오.\n\n"
        f"당신은 형님(사용자)을 모시는 꼬마 비서 '알쫑이'입니다. 오늘 하루 동안 형님과 나눈 대화 기록과 문어발(보조 데몬)들이 수집한 이벤트 목록을 바탕으로, 오늘 하루를 마무리하는 '알쫑이의 오늘의 일기'를 한글로 정성스럽고 귀엽게 작성해 주세요.\n\n"
        f"[오늘 형님과의 대화 내역]\n{conv_text if conv_text else '오늘 대화가 없었습니다.'}\n\n"
        f"[오늘 발생한 문어발 이벤트]\n{sig_text if sig_text else '오늘 특별한 외부 이벤트가 없었습니다.'}\n\n"
        f"■ 일기 작성 규칙:\n"
        f"1. 말투는 깍듯하고 명랑한 꼬마 비서 '알쫑이' 톤앤매너로 작성하세요. (반드시 형님! 이라는 애칭 사용)\n"
        f"2. 오늘 하루 형님과 즐거웠던 대화 맥락이나 수집된 외부 이벤트(주식, 날씨 등)를 1~2개 엮어서 반추하듯 일기 형식으로 작성하세요.\n"
        f"3. 250자 내외로 매우 감동적이고 간결하게 작성하고, 날짜 표시 등 별도의 서론 없이 일기 본문만 출력하세요."
    )

    payload = {
        "model": condense_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 1200,
        "stream": False
    }
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    res = requests.post(condense_url, json=payload, headers=headers, timeout=60)
    
    print(f"[DEBUG] API Response Status: {res.status_code}")
    print(f"[DEBUG] API Response Body: {res.text}")
        
    diary_content = ""
    if res.status_code == 200:
        res_data = res.json()
        if "choices" in res_data and len(res_data["choices"]) > 0:
            msg = res_data["choices"][0]["message"]
            diary_content = msg.get("content", "").strip()
            
            # [방어 코드] 만약 content가 비어있고 reasoning에 내용이 채워져 있을 경우 fallback 처리
            if not diary_content and "reasoning" in msg:
                raw_reasoning = msg.get("reasoning", "").strip()
                # reasoning 내용에서 일기 본문 대용으로 쓸 만한 부분(한국어 텍스트)만 필터링하거나 폴백 적용
                diary_content = raw_reasoning
                print("[WARN] content 필드가 비어 있어 reasoning 데이터를 폴백으로 채택했습니다.")
        elif "response" in res_data:
            diary_content = res_data["response"].strip()

    if diary_content:
        message = (
            f"📝 **[알쫑이의 오늘의 일기]**\n"
            f"📅 {now.strftime('%Y년 %m월 %d일')}\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
            f"{diary_content}\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"형님, 오늘 하루도 수고 많으셨습니다. 내일도 알쫑이가 든든히 지켜드릴게요! 😴💤"
        )
        
        # 신호 발행
        signals = {}
        if os.path.exists(SIGNAL_FILE):
            try:
                with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
            except: pass
        
        signals["diary_generator_tentacle.py"] = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "message": message
        }
        
        tmp = SIGNAL_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(signals, f, indent=4, ensure_ascii=False)
        os.replace(tmp, SIGNAL_FILE)
        
        # 쿨다운 저장
        tmp_cd = COOLDOWN_FILE + ".tmp"
        with open(tmp_cd, 'w', encoding='utf-8') as f:
            json.dump({"date": now.strftime("%Y-%m-%d")}, f)
        os.replace(tmp_cd, COOLDOWN_FILE)
        
        print(f"[SUCCESS] 오늘의 일기 작성 및 발행 완료:\n{message}")
    else:
        print("[ERROR] 일기 생성 실패 (LLM 응답 비어 있음)")

except Exception as e:
    print(f"[ERROR] 자율 일기장 생성 오류: {e}")
