# -*- coding: utf-8 -*-
#
# push_notify: 알쫑이가 스스로 형님의 텔레그램으로 메시지를 직접 발송할 때 사용하는 스킬입니다.
# 긴급 알림, 작업 완료 보고, 자율 메시지 등에 활용합니다.
# 사용 예: <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\push_notify.py "형님, 요청하신 작업이 완료되었습니다!"</CMD>
#
import sys
import io
import warnings
warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_config():
    """봇 설정에서 Token과 Chat ID를 불러옵니다."""
    token = ""
    chat_id = ""

    # bot_config.json 에서 토큰 로드
    bot_config_path = os.path.join(BASE_DIR, "state", "bot_config.json")
    if os.path.exists(bot_config_path):
        try:
            with open(bot_config_path, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                token = config.get("telegram_token", "")
                chat_id = config.get("default_chat_id", "")
        except:
            pass

    # user_settings.json 에서 첫 번째 등록된 채팅 ID를 Chat ID로 사용
    if not chat_id:
        settings_path = os.path.join(BASE_DIR, "user_settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                if settings:
                    chat_id = list(settings.keys())[0]
            except:
                pass

    return token, chat_id

def push(message: str, token: str = "", chat_id: str = "") -> str:
    if not token or not chat_id:
        t, c = load_config()
        token = token or t
        chat_id = chat_id or c

    if not token:
        return "[push_notify] 텔레그램 토큰을 찾을 수 없습니다. state/bot_config.json을 확인하세요."
    if not chat_id:
        return "[push_notify] Chat ID를 찾을 수 없습니다. state/bot_config.json에 default_chat_id를 추가하거나 먼저 대화를 시작하세요."

    try:
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }).encode('utf-8')

        req = urllib.request.Request(
            api_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            result = json.loads(res.read().decode('utf-8'))

        if result.get("ok"):
            return f"[push_notify] ✅ 메시지 발송 완료! (chat_id: {chat_id})"
        else:
            return f"[push_notify] ❌ 발송 실패: {result}"
    except Exception as e:
        return f"[push_notify] 오류: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용법: python push_notify.py "보낼 메시지"')
        sys.exit(1)
    message = " ".join(sys.argv[1:])
    result = push(message)
    print(result)
