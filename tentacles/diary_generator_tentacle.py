# -*- coding: utf-8 -*-
"""
diary_generator_tentacle.py
-   23:50~23:55  
-  (5339243832)  Episodic Memory      
- Ollama LLM    ' '  
-      
"""
import os
import sys
import io
import json
import time
import requests
from datetime import datetime

#   UTF-8   (   )
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
TEST_MODE = False  #   True   

# 1.    (23:50 ~ 23:55)
now = datetime.now()
TARGET_HOUR = 23
TARGET_MIN_START = 50
TARGET_MIN_END = 55

is_target_time = (now.hour == TARGET_HOUR and TARGET_MIN_START <= now.minute < TARGET_MIN_END)
if not TEST_MODE and not is_target_time:
    sys.exit(0)

# 2.   ( 1)
if os.path.exists(COOLDOWN_FILE):
    try:
        with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
            stored = json.load(f)
        if stored.get("date") == now.strftime("%Y-%m-%d"):
            print("[INFO]     . .")
            sys.exit(0)
    except: pass

def get_today_conversations():
    """      """
    log_path = os.path.join(BASE_DIR, "..", "memory_logs", f"{MASTER_CHAT_ID}_episodic.jsonl")
    if not os.path.exists(log_path):
        return []
        
    #  00:00:00 
    today_start = datetime.combine(now.date(), datetime.min.time()).timestamp()
    
    conversations = []
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    ts = data.get("timestamp", 0)
                    if ts >= today_start:
                        role = "" if data.get("role") == "user" else ""
                        content = data.get("content", "")
                        # CMD       
                        content = content.split("(※   ")[0].strip()
                        conversations.append(f"{role}: {content}")
                except: pass
    except Exception as e:
        print(f"[ERROR]   : {e}")
    return conversations

def get_today_signals():
    """     """
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

#  
convs = get_today_conversations()
sigs = get_today_signals()

#         
if not convs and not sigs and not TEST_MODE:
    print("[INFO]       .")
    sys.exit(0)

# LLM     
try:
    # llm_config.json  
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

    conv_text = "\n".join(convs[-30:]) #  30 
    sig_text = "\n".join(sigs)
    
    prompt = (
        f"[  ]   (Thinking Process/Reasoning)    ! "
        f"     .  ,         .\n\n"
        f" ()    ''.        ( )    ,    '  '     .\n\n"
        f"[   ]\n{conv_text if conv_text else '  .'}\n\n"
        f"[   ]\n{sig_text if sig_text else '    .'}\n\n"
        f"   :\n"
        f"1.      ''  . ( !   )\n"
        f"2.         (,  ) 1~2     .\n"
        f"3. 250     ,         ."
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
            
            # [ ]  content  reasoning     fallback 
            if not diary_content and "reasoning" in msg:
                raw_reasoning = msg.get("reasoning", "").strip()
                # reasoning       ( )   
                diary_content = raw_reasoning
                print("[WARN] content    reasoning   .")
        elif "response" in res_data:
            diary_content = res_data["response"].strip()

    if diary_content:
        message = (
            f"[MEMO] **[  ]**\n"
            f" {now.strftime('%Y %m %d')}\n"
            f"\n\n"
            f"{diary_content}\n\n"
            f"\n"
            f",    .    ! "
        )
        
        #  
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
        
        #  
        tmp_cd = COOLDOWN_FILE + ".tmp"
        with open(tmp_cd, 'w', encoding='utf-8') as f:
            json.dump({"date": now.strftime("%Y-%m-%d")}, f)
        os.replace(tmp_cd, COOLDOWN_FILE)
        
        print(f"[SUCCESS]      :\n{message}")
    else:
        print("[ERROR]    (LLM   )")

except Exception as e:
    print(f"[ERROR]    : {e}")
