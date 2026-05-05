# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: calendar_sync
# AGENT_SKILL_DESC: 구글 캘린더에서 오늘 또는 이번 주 일정을 조회합니다. 최초 실행 시 브라우저 인증 필요.
# AGENT_SKILL_ARGS: range(str) - today/week
# AGENT_SKILL_RETURNS: 일정 목록 (제목, 시간, 장소)
#
# calendar_sync: 구글 캘린더(Google Calendar) API를 통해 오늘/이번 주 일정을 조회합니다.
# 최초 실행 시 브라우저 인증이 필요합니다. credentials.json 파일이 필요합니다.
# 사용 예: <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\calendar_sync.py today</CMD>
# <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\calendar_sync.py week</CMD>
# <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\calendar_sync.py setup</CMD>
#
import sys
import io
import warnings
warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(BASE_DIR, "google_credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "google_token.json")

SETUP_GUIDE = """
[Google Calendar 연동 설정 가이드]

1. https://console.cloud.google.com/ 에 접속
2. 프로젝트 생성 → API 및 서비스 → Google Calendar API 활성화
3. 사용자 인증 정보 → OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
4. 다운로드한 JSON 파일을 아래 경로에 저장:
   {}
5. 다시 이 스킬을 실행하면 브라우저 인증 창이 뜹니다.
""".format(CREDS_FILE)

def get_events(mode: str = "today") -> str:
    # credentials.json 파일 확인
    if not os.path.exists(CREDS_FILE):
        return SETUP_GUIDE

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        return ("[calendar_sync] 필요한 라이브러리가 없습니다.\n"
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib 을 실행하세요.")

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        now_utc = datetime.now(timezone.utc)

        if mode == "week":
            time_min = now_utc.isoformat()
            time_max = (now_utc + timedelta(days=7)).isoformat()
            period_label = "이번 주 (7일간)"
        else:  # today
            time_min = now_utc.replace(hour=0, minute=0, second=0).isoformat()
            time_max = now_utc.replace(hour=23, minute=59, second=59).isoformat()
            period_label = "오늘"

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return f"[calendar_sync] {period_label} 일정이 없습니다."

        lines = [f"[Google Calendar - {period_label} 일정 ({len(events)}건)]"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date', ''))
            if 'T' in start:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                start_str = dt.strftime("%m/%d %H:%M")
            else:
                start_str = start

            summary = event.get('summary', '(제목 없음)')
            location = event.get('location', '')
            loc_str = f" 📍{location}" if location else ""
            lines.append(f"• {start_str} - {summary}{loc_str}")

        return '\n'.join(lines)

    except Exception as e:
        return f"[calendar_sync] Google Calendar API 오류: {e}"

if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "today"

    if mode == "setup":
        print(SETUP_GUIDE)
    elif mode in ["today", "week"]:
        print(get_events(mode))
    else:
        print("사용법: python calendar_sync.py [today|week|setup]")
