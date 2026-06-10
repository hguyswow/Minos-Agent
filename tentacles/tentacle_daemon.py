import os
import time
import json
import subprocess
import io
import sys
import traceback
from datetime import datetime

#   UTF-8   (     ,  )
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

# [  ]
# def run_tentacles():
#     print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]     ...")
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
#                 print(f"  ⏭  (OFF ): {filename}")
#                 continue
#                 
#             script_path = os.path.join(BASE_DIR, filename)
#             print(f"  ->  : {filename}")
#             
#             try:
#                 result = subprocess.run(["python", script_path], capture_output=True, text=True, timeout=60)
#                 if result.returncode != 0:
#                     print(f"  [X]  : {filename}")
#                     errors[filename] = {
#                         "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                         "error_log": result.stderr.strip()[-2000:] #    2000
#                     }
#                 else:
#                     print(f"  [CHECK]  : {filename}")
#                     if filename in errors:
#                         #    (  )
#                         del errors[filename]
#             except subprocess.TimeoutExpired:
#                 print(f"  ⏳ : {filename}")
#                 errors[filename] = {
#                     "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                     "error_log": "TimeoutExpired: 60    .   ."
#                 }
#             except Exception as e:
#                 errors[filename] = {
#                     "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                     "error_log": f"SystemException: {str(e)}"
#                 }
#                 
#     save_errors(errors)
#     print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]     .\n")

def run_tentacles():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]  [ - InProcess]    ...")
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
                print(f"  ⏭  (OFF ): {filename}")
                continue
                
            script_path = os.path.join(BASE_DIR, filename)
            print(f"  ->   ( ): {filename}")
            
            #      
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            captured_stdout = io.StringIO()
            captured_stderr = io.StringIO()
            sys.stdout = captured_stdout
            sys.stderr = captured_stderr
            
            #    
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
                # sys.exit()   
                if e.code is not None and e.code != 0:
                    has_error = True
                    err_msg = f"SystemExit code: {e.code}"
            except Exception as e:
                has_error = True
                err_msg = traceback.format_exc()
            finally:
                #    
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
            stdout_content = captured_stdout.getvalue()
            stderr_content = captured_stderr.getvalue()
            
            if has_error:
                print(f"  [X]  : {filename}")
                combined_err = f"{err_msg}\n[Console Output (stderr)]:\n{stderr_content}\n[Console Output (stdout)]:\n{stdout_content}"
                errors[filename] = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "error_log": combined_err[-2000:]  # 2000 
                }
            else:
                print(f"  [CHECK]  : {filename}")
                if filename in errors:
                    del errors[filename]
                    
    save_errors(errors)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]  [ - InProcess]    .\n")

if __name__ == "__main__":
    while True:
        run_tentacles()
        time.sleep(60) # 1  ()
