# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: calendar_add
# AGENT_SKILL_DESC: 구글 캘린더에 새로운 일정을 추가합니다. (최초 실행 시 브라우저 인증 필요)
# AGENT_SKILL_ARGS: --title "제목" --start "YYYY-MM-DDTHH:MM:SS" [--end "YYYY-MM-DDTHH:MM:SS"] [--location "장소"] [--desc "설명"]
# AGENT_SKILL_RETURNS: 일정 추가 결과 메시지
#
# 사용 예: <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\calendar_add.py --title "개발 회의" --start "2026-05-06T14:00:00" --end "2026-05-06T15:00:00" --location "회의실 A"</CMD>
# 시작 시간(start)은 필수이며, 종료 시간(end)이 없으면 시작 시간으로부터 1시간 후로 자동 설정됩니다.

import sys
import io
import warnings
warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import argparse
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(BASE_DIR, "google_credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "google_token.json")

def add_event(title, start_str, end_str=None, location="", description=""):
    if not os.path.exists(CREDS_FILE):
        return "[calendar_add] google_credentials.json 파일이 없습니다. calendar_sync 스킬의 안내를 확인하세요."

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        return "[calendar_add] 필요한 라이브러리가 없습니다. (google-api-python-client, google-auth-oauthlib)"

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and not creds.has_scopes(SCOPES):
            creds = None
            try:
                os.remove(TOKEN_FILE)
            except: pass

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                try: os.remove(TOKEN_FILE)
                except: pass
                return "[calendar_add] 토큰 갱신 실패. 다시 실행하여 재인증하세요."
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        # 파싱 (start_str 예: "2026-05-06T14:00:00")
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except ValueError:
            return f"[calendar_add] 시작 시간 형식이 올바르지 않습니다: {start_str} (ISO 8601 형식 필요)"

        if start_dt.tzinfo is None:
            # 로컬 시간대로 설정
            import time
            local_tz = timezone(timedelta(seconds=-time.timezone))
            start_dt = start_dt.replace(tzinfo=local_tz)

        if end_str:
            try:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=start_dt.tzinfo)
            except ValueError:
                return f"[calendar_add] 종료 시간 형식이 올바르지 않습니다: {end_str}"
        else:
            end_dt = start_dt + timedelta(hours=1)

        event_body = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
            },
            'end': {
                'dateTime': end_dt.isoformat(),
            },
        }

        event = service.events().insert(calendarId='primary', body=event_body).execute()
        return f"[calendar_add] 📅 일정 추가 완료! (제목: '{title}', 시작: {start_dt.strftime('%m/%d %H:%M')})"

    except Exception as e:
        return f"[calendar_add] Google Calendar API 오류: {e}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--title', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=False, default=None)
    parser.add_argument('--location', required=False, default="")
    parser.add_argument('--desc', required=False, default="")
    
    args = parser.parse_args()
    print(add_event(args.title, args.start, args.end, args.location, args.desc))
