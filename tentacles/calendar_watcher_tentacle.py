# -*- coding: utf-8 -*-
#    cooldown/history  
"""
calendar_watcher_tentacle.py
10 .    30      .
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
SKILLS_DIR = os.path.join(PROJECT_DIR, "skill_system", "skills")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
HISTORY_FILE = os.path.join(BASE_DIR, "data", "calendar_history.json")
CREDS_FILE = os.path.join(SKILLS_DIR, "google_credentials.json")
TOKEN_FILE = os.path.join(SKILLS_DIR, "google_token.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"alerted_events": []}

def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    tmp = HISTORY_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HISTORY_FILE)

def run():
    #   ( On/Off )
    config_file = os.path.join(BASE_DIR, "data", "tentacle_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if not cfg.get("calendar_watcher_tentacle.py", True):
                    return
        except: pass

    if not os.path.exists(CREDS_FILE) or not os.path.exists(TOKEN_FILE):
        return

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        return

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds.valid:
            from google.auth.transport.requests import Request
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            else:
                return
    except Exception:
        return

    try:
        service = build('calendar', 'v3', credentials=creds)
        now_utc = datetime.now(timezone.utc)
        
        time_min = now_utc.isoformat()
        time_max = (now_utc + timedelta(hours=1)).isoformat()
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        if not events:
            return

        history = load_history()
        alerted = history.get("alerted_events", [])
        
        #         
        if len(alerted) > 1000:
            alerted = alerted[-500:]
        
        new_alerts = []
        for event in events:
            event_id = event['id']
            if event_id in alerted:
                continue
                
            start = event['start'].get('dateTime', event['start'].get('date', ''))
            if 'T' in start:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                diff_mins = (dt - now_utc).total_seconds() / 60.0
                
                if 0 <= diff_mins <= 35:
                    summary = event.get('summary', '( )')
                    loc = event.get('location', '')
                    loc_str = f"\n : {loc}" if loc else ""
                    
                    import time
                    local_tz = timezone(timedelta(seconds=-time.timezone))
                    local_time_str = dt.astimezone(local_tz).strftime("%H:%M")
                    
                    msg = f"⏰ [ ]   {local_time_str}  .\n- {summary}{loc_str}"
                    new_alerts.append(msg)
                    alerted.append(event_id)
            else:
                pass
                
        if new_alerts:
            history["alerted_events"] = alerted
            save_history(history)
            
            full_msg = "\n\n".join(new_alerts)
            
            signals = {}
            if os.path.exists(SIGNAL_FILE):
                try:
                    with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                        signals = json.load(f)
                except Exception:
                    pass
                    
            now = datetime.now()
            signals["calendar_watcher_tentacle.py"] = {
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "message": full_msg
            }
            
            os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
            tmp = SIGNAL_FILE + ".tmp"
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(signals, f, indent=4, ensure_ascii=False)
            os.replace(tmp, SIGNAL_FILE)
            
    except Exception as e:
        pass

if __name__ == "__main__":
    run()
