import os
import time
import json
import subprocess
import io
import sys
import traceback
from datetime import datetime

# 콘솔 출력 UTF-8 강제 지정 (윈도우 환경 이모지 출력 에러 방지, 가로채기 방어)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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

# [오리지널 코드 보존]
# def run_tentacles():
#     print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🐙 문어발 데몬 사이클 시작...")
#     errors = load_errors()
#     
#     config = {}
#     if os.path.exists(CONFIG_FILE):
#         try:
#             with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
#                 config = json.load(f)
#         except: pass
#         
#     for filename in os.listdir(BASE_DIR):
#         if filename.endswith(".py") and filename not in ["tentacle_daemon.py", "__init__.py"]:
#             if config.get(filename, True) is False:
#                 print(f"  ⏭️ 스킵됨 (OFF 설정): {filename}")
#                 continue
#                 
#             script_path = os.path.join(BASE_DIR, filename)
#             print(f"  -> 실행 중: {filename}")
#             
#             try:
#                 result = subprocess.run(["python", script_path], capture_output=True, text=True, timeout=60)
#                 if result.returncode != 0:
#                     print(f"  ❌ 에러 발생: {filename}")
#                     errors[filename] = {
#                         "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                         "error_log": result.stderr.strip()[-2000:] # 끝부분 에러 추적 2000자
#                     }
#                 else:
#                     print(f"  ✅ 정상 완료: {filename}")
#                     if filename in errors:
#                         # 자가 치유 완료 (에러 목록에서 삭제)
#                         del errors[filename]
#             except subprocess.TimeoutExpired:
#                 print(f"  ⏳ 타임아웃: {filename}")
#                 errors[filename] = {
#                     "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                     "error_log": "TimeoutExpired: 60초 초과로 프로세스 강제 종료됨. 무한 루프 가능성."
#                 }
#             except Exception as e:
#                 errors[filename] = {
#                     "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                     "error_log": f"SystemException: {str(e)}"
#                 }
#                 
#     save_errors(errors)
#     print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🐙 문어발 데몬 사이클 종료.\n")

def run_tentacles():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🐙 [최적화 - InProcess] 문어발 데몬 사이클 시작...")
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
            print(f"  -> 실행 중 (동적 컴파일): {filename}")
            
            # 표준 입출력 및 표준 에러 가로채기
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            captured_stdout = io.StringIO()
            captured_stderr = io.StringIO()
            sys.stdout = captured_stdout
            sys.stderr = captured_stderr
            
            # 독립된 전역 네임스페이스 준비
            script_globals = {
                "__file__": script_path,
                "__name__": "__main__",
            }
            
            has_error = False
            err_msg = ""
            
            try:
                with open(script_path, "r", encoding="utf-8") as f:
                    code = compile(f.read(), script_path, "exec")
                exec(code, script_globals)
            except SystemExit as e:
                # sys.exit()가 명시적으로 불린 경우
                if e.code is not None and e.code != 0:
                    has_error = True
                    err_msg = f"SystemExit code: {e.code}"
            except Exception as e:
                has_error = True
                err_msg = traceback.format_exc()
            finally:
                # 표준 입출력 즉시 복구
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
            stdout_content = captured_stdout.getvalue()
            stderr_content = captured_stderr.getvalue()
            
            if has_error:
                print(f"  ❌ 에러 발생: {filename}")
                combined_err = f"{err_msg}\n[Console Output (stderr)]:\n{stderr_content}\n[Console Output (stdout)]:\n{stdout_content}"
                errors[filename] = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "error_log": combined_err[-2000:]  # 2000자 제한
                }
            else:
                print(f"  ✅ 정상 완료: {filename}")
                if filename in errors:
                    del errors[filename]
                    
    save_errors(errors)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🐙 [최적화 - InProcess] 문어발 데몬 사이클 종료.\n")

if __name__ == "__main__":
    while True:
        run_tentacles()
        time.sleep(60) # 1분 대기 (테스트용)
