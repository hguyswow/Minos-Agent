# -*- coding: utf-8 -*-
import time
import json
import os
import requests

TOKEN = "8701884214:AAG8bcGb4j7L0qMdSco4N2v793Kea9DYTpg"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# 원본 경로 백업 (2026-05-24)
# SCRATCH_DIR = r"C:\Users\hguys\.gemini\antigravity\scratch"
# C:\ai 이관 경로 적용
SCRATCH_DIR = r"C:\ai\Antigravity_Memory_Engine"

INBOX_PATH = os.path.join(SCRATCH_DIR, "telegram_inbox.json")
OUTBOX_PATH = os.path.join(SCRATCH_DIR, "telegram_outbox.json")
LOG_PATH = os.path.join(SCRATCH_DIR, "telegram_bridge.log")

def log_message(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

def save_json(path, data):
    try:
        temp_path = path + ".tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except Exception as e:
        log_message(f"Error saving JSON to {path}: {e}")

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_message(f"Error loading JSON from {path}: {e}")
    return []

def main():
    offset = None
    log_message("Telegram Bridge started successfully.")
    print("Telegram Bridge is running...")
    
    # Ensure files exist
    if not os.path.exists(INBOX_PATH):
        save_json(INBOX_PATH, [])
    if not os.path.exists(OUTBOX_PATH):
        save_json(OUTBOX_PATH, [])

    while True:
        try:
            # 1. Outbox check & Send replies
            outbox = load_json(OUTBOX_PATH)
            if outbox:
                remaining = []
                for msg in outbox:
                    chat_id = msg.get("chat_id")
                    text = msg.get("text")
                    reply_to = msg.get("reply_to_message_id")
                    
                    url = f"{BASE_URL}/sendMessage"
                    payload = {
                        "chat_id": chat_id, 
                        "text": text,
                        "parse_mode": "Markdown"
                    }
                    if reply_to:
                        payload["reply_to_message_id"] = reply_to
                        
                    try:
                        res = requests.post(url, json=payload, timeout=10)
                        if res.status_code == 200:
                            log_message(f"Sent reply to chat {chat_id}: {text[:30]}...")
                        else:
                            log_message(f"Failed to send to chat {chat_id}: {res.text}")
                            remaining.append(msg)
                    except Exception as e:
                        log_message(f"HTTP error sending message: {e}")
                        remaining.append(msg)
                
                save_json(OUTBOX_PATH, remaining)

            # 2. Telegram updates polling
            url = f"{BASE_URL}/getUpdates"
            params = {"timeout": 10}
            if offset:
                params["offset"] = offset
                
            res = requests.get(url, params=params, timeout=15)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if not message:
                        continue
                        
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "")
                    msg_id = message["message_id"]
                    
                    inbox = load_json(INBOX_PATH)
                    if not any(m.get("message_id") == msg_id for m in inbox):
                        log_message(f"Received message from chat {chat_id}: {text[:30]}")
                        inbox.append({
                            "chat_id": chat_id,
                            "message_id": msg_id,
                            "text": text,
                            "timestamp": time.time()
                        })
                        save_json(INBOX_PATH, inbox)
                        
                        # Inform user of receipt
                        ack_text = "🤖 *[Antigravity 2.0]*\n요청을 접수했습니다. 로컬 시스템 제어 및 코드 탐색 분석을 직접 수행 중이오니 잠시만 기다려 주십시오..."
                        try:
                            requests.post(f"{BASE_URL}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": ack_text,
                                "reply_to_message_id": msg_id,
                                "parse_mode": "Markdown"
                             }, timeout=5)
                        except:
                            pass
            elif res.status_code != 409:
                log_message(f"Telegram updates HTTP error: {res.status_code} - {res.text}")
                
        except Exception as e:
            log_message(f"Error in main loop: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    main()
