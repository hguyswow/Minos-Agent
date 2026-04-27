import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(BASE_DIR, "state", "bot_config.json")

print("File exists?", os.path.exists(config_file))
try:
    with open(config_file, "r", encoding="utf-8-sig") as f:
        print("Raw content:", f.read())
        f.seek(0)
        config = json.load(f)
        token = config.get('telegram_token', '').strip()
        print("Token loaded:", repr(token))
except Exception as e:
    print("Error:", str(e))
