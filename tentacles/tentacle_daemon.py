import os
import time
import json
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
ERROR_FILE = os.path.join(LOGS_DIR, "tentacle_errors.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "tentacle_config.json")

def load_errors():
    if os.path.exists(ERROR_FILE):
        try:
            with open(ERROR_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_errors(errors):
    with open(ERROR_FILE, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=4, ensure_ascii=False)

def run_tentacles():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🐙 문어발 데몬 사이클 시작...")
    errors = load_errors()
    
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except: pass
        
    for filename in os.listdir(BASE_DIR):
        if filename.endswith(".py") and filename not in ["tentacle_daemon.py", "__init__.py"]:
            if config.get(filename, True) is False:
                print(f"  ⏭️ 스킵됨 (OFF 설정): {filename}")
                continue
                
            script_path = os.path.join(BASE_DIR, filename)
            print(f"  -> 실행 중: {filename}")
            
            try:
                result = subprocess.run(["python", script_path], capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    print(f"  ❌ 에러 발생: {filename}")
                    errors[filename] = {
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "error_log": result.stderr.strip()[-2000:] # 끝부분 에러 추적 2000자
                    }
                else:
                    print(f"  ✅ 정상 완료: {filename}")
                    if filename in errors:
                        # 자가 치유 완료 (에러 목록에서 삭제)
                        del errors[filename]
            except subprocess.TimeoutExpired:
                print(f"  ⏳ 타임아웃: {filename}")
                errors[filename] = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "error_log": "TimeoutExpired: 60초 초과로 프로세스 강제 종료됨. 무한 루프 가능성."
                }
            except Exception as e:
                errors[filename] = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "error_log": f"SystemException: {str(e)}"
                }
                
    save_errors(errors)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🐙 문어발 데몬 사이클 종료.\n")

if __name__ == "__main__":
    while True:
        run_tentacles()
        time.sleep(60) # 1분 대기 (테스트용)
