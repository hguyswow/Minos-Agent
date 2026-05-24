# -*- coding: utf-8 -*-
import os
import sys
import io
import json
import psutil

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from flask import Flask, render_template, request, Response, jsonify
from core_engine import generate_response_stream
from memory_engine import MemoryEngine
from core_engine import generate_response_stream
from memory_engine import MemoryEngine
from tts_engine import tts
import subprocess

try:
    import GPUtil
except ImportError:
    GPUtil = None

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
memory = MemoryEngine()

import requests

def get_main_chat_id():
    memory_dir = os.path.join(BASE_DIR, "memory_logs")
    if os.path.exists(memory_dir):
        for f in os.listdir(memory_dir):
            if f.endswith("_memory.json"):
                cid = f.replace("_memory.json", "")
                if cid != "web_dashboard" and cid.isdigit():
                    return cid

    state_file = os.path.join(BASE_DIR, "state", "user_states.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for cid in data.keys():
                    if cid != "web_dashboard" and str(cid).isdigit():
                        return str(cid)
        except: pass
    return "web_dashboard"

def get_telegram_token():
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8-sig') as f:
                return json.load(f).get('telegram_token', '')
        except: pass
    return ""

def sync_to_telegram(chat_id, text):
    if chat_id == "web_dashboard":
        return
    token = get_telegram_token()
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # 1차 시도: Markdown
    payload_md = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload_md, timeout=3)
        if res.status_code != 200:
            # 마크다운 파싱 에러 시 일반 텍스트로 재시도
            payload_plain = {"chat_id": chat_id, "text": text}
            requests.post(url, json=payload_plain, timeout=3)
    except Exception as _e:
        print(f"[Dashboard] 텔레그램 메시지 전송 실패 (무시): {_e}")

def sync_voice_to_telegram(chat_id, audio_path):
    if chat_id == "web_dashboard":
        return
    token = get_telegram_token()
    if not token or not audio_path or not os.path.exists(audio_path):
        return
    url = f"https://api.telegram.org/bot{token}/sendVoice"
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'voice': f}
            data = {'chat_id': chat_id}
            requests.post(url, data=data, files=files, timeout=10)
    except Exception as e:
        print(f"동기 텔레그램 음성 발송 실패: {e}")

def handle_tts_output(chat_id, text):
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
        except: pass
        
    if not config.get("tts_enabled", False):
        return
        
    dest = config.get("tts_destination", "local")
    from tts_engine import tts, generate_tts_file
    
    if dest in ["local", "both"]:
        tts.speak(text)
        
    if dest in ["telegram", "both"]:
        audio_path = generate_tts_file(text, config)
        if audio_path:
            sync_voice_to_telegram(chat_id, audio_path)
            try: os.remove(audio_path)
            except: pass

def get_user_state():
    chat_id = get_main_chat_id()
    state_file = os.path.join(BASE_DIR, "state", "user_states.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(chat_id, {"auto_skills": []})
        except: pass
    return {"auto_skills": []}

def save_user_state(state):
    chat_id = get_main_chat_id()
    os.makedirs(os.path.join(BASE_DIR, "state"), exist_ok=True)
    state_file = os.path.join(BASE_DIR, "state", "user_states.json")
    data = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except: pass
    data[chat_id] = state
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@app.route('/')
def index():
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    has_token = False
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                if config.get('telegram_token'):
                    has_token = True
        except: pass
    return render_template('index.html', has_token=has_token)

def get_gpu_status_nvidia_smi():
    """nvidia-smi 명령어를 활용한 상세 GPU 상태 수집 (윈도우 환경 대응 및 폴백 완비)"""
    try:
        creationflags = 0
        if sys.platform == 'win32':
            import subprocess
            creationflags = subprocess.CREATE_NO_WINDOW
            
        cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', timeout=5, creationflags=creationflags)
        
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(',')
            if len(parts) >= 4:
                gpu_load = float(parts[0].strip())
                vram_used = float(parts[1].strip())
                vram_total = float(parts[2].strip())
                gpu_temp = float(parts[3].strip())
                
                vram_percent = (vram_used / vram_total) * 100 if vram_total > 0 else 0.0
                
                return {
                    "load": f"{gpu_load:.1f}",
                    "vram_percent": f"{vram_percent:.1f}",
                    "vram_used": f"{vram_used:.0f}",
                    "vram_total": f"{vram_total:.0f}",
                    "temperature": f"{gpu_temp:.0f}"
                }
    except Exception as e:
        print(f"[get_gpu_status_nvidia_smi] nvidia-smi 호출 실패 (폴백 가동): {e}")
    return None

@app.route('/api/status')
def get_status():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    # 1. GPU 상세 정보 조회 (nvidia-smi 우선)
    gpu_percent = "--"
    vram_percent = "--"
    gpu_temp = "--"
    vram_used = "--"
    vram_total = "--"
    
    nvidia_data = get_gpu_status_nvidia_smi()
    if nvidia_data:
        gpu_percent = nvidia_data["load"]
        vram_percent = nvidia_data["vram_percent"]
        gpu_temp = nvidia_data["temperature"]
        vram_used = nvidia_data["vram_used"]
        vram_total = nvidia_data["vram_total"]
    elif GPUtil:
        # GPUtil 폴백
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_percent = f"{gpus[0].load * 100:.1f}"
                vram_percent = f"{(gpus[0].memoryUsed / gpus[0].memoryTotal) * 100:.1f}"
                gpu_temp = f"{gpus[0].temperature:.0f}"
                vram_used = f"{gpus[0].memoryUsed:.0f}"
                vram_total = f"{gpus[0].memoryTotal:.0f}"
        except Exception as e:
            print(f"[get_status] GPUtil 수집 에러: {e}")
            
    # 2. 문어발 상태
    tentacles_dir = os.path.join(BASE_DIR, "tentacles")
    config_file = os.path.join(tentacles_dir, "data", "tentacle_config.json")
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except: pass
        
    tentacles = []
    if os.path.exists(tentacles_dir):
        for tf in os.listdir(tentacles_dir):
            if tf.endswith('.py') and tf not in ["__init__.py", "tentacle_daemon.py"]:
                tentacles.append({
                    "name": tf,
                    "is_on": config.get(tf, True)
                })
                
    # 3. 에러 로그
    errors = {}
    error_file = os.path.join(tentacles_dir, "logs", "tentacle_errors.json")
    if os.path.exists(error_file):
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except: pass

    # 4. 스킬(자동 승인) 상태
    skills_dir = os.path.join(BASE_DIR, "skill_system", "skills")
    state = get_user_state()
    auto_skills = state.get("auto_skills", [])
    
    skills = []
    if os.path.exists(skills_dir):
        for sf in os.listdir(skills_dir):
            if sf.endswith('.py') and sf != "__init__.py":
                skills.append({
                    "name": sf,
                    "is_auto": sf in auto_skills
                })

    # 5. Ollama 컨텍스트 (working_memory) 모니터링 데이터 추가
    chat_id = get_main_chat_id()
    mem_data = memory.load_memory(chat_id)
    working_mem = mem_data.get("working_memory", [])
    mem_count = len(working_mem)
    mem_max = getattr(memory, "max_working_memory", 20)
    mem_percent = (mem_count / mem_max) * 100 if mem_max > 0 else 0.0

    return jsonify({
        "cpu": cpu,
        "ram": ram,
        "gpu": gpu_percent,
        "vram": vram_percent,
        "gpu_temp": gpu_temp,
        "vram_used": vram_used,
        "vram_total": vram_total,
        "memory_count": mem_count,
        "memory_max": mem_max,
        "memory_percent": f"{mem_percent:.1f}",
        "tentacles": tentacles,
        "errors": errors,
        "skills": skills
    })


@app.route('/api/toggle_tentacle', methods=['POST'])
def toggle_tentacle():
    data = request.json
    tentacle_name = data.get('name')
    
    tentacles_dir = os.path.join(BASE_DIR, "tentacles")
    config_file = os.path.join(tentacles_dir, "data", "tentacle_config.json")
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except: pass
        
    current = config.get(tentacle_name, True)
    config[tentacle_name] = not current
    
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        
    return jsonify({"success": True})

@app.route('/api/toggle_skill', methods=['POST'])
def toggle_skill():
    data = request.json
    skill_name = data.get('name')
    
    state = get_user_state()
    auto_skills = state.get("auto_skills", [])
    
    if skill_name in auto_skills:
        auto_skills.remove(skill_name)
    else:
        auto_skills.append(skill_name)
        
    state["auto_skills"] = auto_skills
    save_user_state(state)
    
    return jsonify({"success": True})

@app.route('/api/editor/read', methods=['GET'])
def editor_read():
    file_type = request.args.get('type') # 'skill', 'tentacle', 'config'
    file_name = request.args.get('name')
    
    if not file_name or '..' in file_name or '/' in file_name or '\\' in file_name:
        return jsonify({"error": "Invalid file name"}), 400
        
    if file_type == 'skill':
        target_dir = os.path.join(BASE_DIR, "skill_system", "skills")
    elif file_type == 'tentacle':
        target_dir = os.path.join(BASE_DIR, "tentacles")
    elif file_type == 'config':
        target_dir = os.path.join(BASE_DIR, "tentacles", "data")
    else:
        return jsonify({"error": "Invalid type"}), 400
        
    file_path = os.path.join(target_dir, file_name)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    return jsonify({"content": content})

@app.route('/api/editor/save', methods=['POST'])
def editor_save():
    data = request.json
    file_type = data.get('type')
    file_name = data.get('name')
    content = data.get('content')
    
    if not file_name or '..' in file_name or '/' in file_name or '\\' in file_name:
        return jsonify({"success": False, "error": "Invalid file name"})
        
    if file_type == 'skill':
        target_dir = os.path.join(BASE_DIR, "skill_system", "skills")
    elif file_type == 'tentacle':
        target_dir = os.path.join(BASE_DIR, "tentacles")
    elif file_type == 'config':
        target_dir = os.path.join(BASE_DIR, "tentacles", "data")
    else:
        return jsonify({"success": False, "error": "Invalid type"})
        
    file_path = os.path.join(target_dir, file_name)
    
    if not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File not found"})
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return jsonify({"success": True})

@app.route('/api/config_reset', methods=['POST'])
def config_reset():
    data = request.json
    file_name = data.get('name')
    
    if not file_name or '..' in file_name or '/' in file_name or '\\' in file_name:
        return jsonify({"success": False, "error": "Invalid file name"})
        
    target_dir = os.path.join(BASE_DIR, "tentacles", "data")
    file_path = os.path.join(target_dir, file_name)
    
    default_data = None
    if file_name == "weather_config.json":
        default_data = {
            "cities": ["Seoul"],
            "language": "ko",
            "description": "원하는 도시 이름을 영문으로 배열에 추가하세요 (예: Busan, Jeju, Tokyo)"
        }
    elif file_name == "keyword_config.json":
        default_data = {
            "keywords": ["RTX 5090", "특가", "LLM", "업데이트"]
        }
    elif file_name == "email_config.json":
        default_data = {
            "email": "your_email@gmail.com",
            "password": "your_app_password",
            "imap_server": "imap.gmail.com",
            "keywords": ["결제", "청구", "중요", "환불"]
        }
    else:
        return jsonify({"success": False, "error": "이 파일은 초기화(기본값 복원)를 지원하지 않습니다."})
        
    os.makedirs(target_dir, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(default_data, f, ensure_ascii=False, indent=4)
        
    return jsonify({"success": True})

@app.route('/api/create_tentacle', methods=['POST'])
def create_tentacle():
    """사용자 지정 BeautifulSoup 크롤링 문어발 스크립트 동적 생성 API"""
    data = request.json
    filename = data.get('filename')
    url = data.get('url')
    selector = data.get('selector')
    keyword = data.get('keyword', '')
    alert_threshold = data.get('alert_threshold', 'changed') # 'contains' or 'changed'
    interval_minutes = int(data.get('interval_minutes', 60))
    
    if not filename or not url or not selector:
        return jsonify({"success": False, "error": "파일명, 대상 URL, HTML CSS Selector는 필수 항목입니다."})
        
    filename = filename.replace(".py", "").strip()
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({"success": False, "error": "부적절한 파일명입니다."})
        
    filename_py = f"{filename}_tentacle.py"
    tentacles_dir = os.path.join(BASE_DIR, "tentacles")
    file_path = os.path.join(tentacles_dir, filename_py)
    
    if os.path.exists(file_path):
        return jsonify({"success": False, "error": "이미 동일한 이름의 문어발이 존재합니다."})
        
    # [오리지널 코드 보존 기법] 신규 템플릿 파일 생성 로직
    template_code = f'''# -*- coding: utf-8 -*-
"""
Generated by Minos Tentacle Factory
Target: {url}
"""
import os
import sys
import io
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 콘솔 출력 CP949 방어 및 UTF-8 강제 래핑
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIGNAL_FILE = os.path.join(BASE_DIR, "logs", "tentacle_signals.json")
DATA_FILE = os.path.join(DATA_DIR, "{filename}_cache.json")
INTERVAL_MINUTES = {interval_minutes}

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

# 쿨다운 체크
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        last_str = cache.get("updated", "")
        if last_str:
            last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M")
            if datetime.now() - last_dt < timedelta(minutes=INTERVAL_MINUTES):
                print(f"[INFO] 쿨다운 대기 중... 다음 주기에 실행됩니다.")
                sys.exit(0)
    except Exception:
        pass

def check_site():
    try:
        headers = {{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}}
        res = requests.get("{url}", headers=headers, timeout=15)
        res.raise_for_status()
        
        # 인코딩 자동 디코딩
        res.encoding = res.apparent_encoding
        
        soup = BeautifulSoup(res.text, 'html.parser')
        elements = soup.select("{selector}")
        if not elements:
            print("[INFO] HTML 요소를 찾지 못했습니다. Selector 설정을 확인해 보세요.")
            return None
            
        content_text = " ".join([el.get_text().strip() for el in elements if el.get_text().strip()])
        return content_text
    except Exception as e:
        print(f"[ERROR] 크롤링 실패: {{e}}")
        return None

content = check_site()
if content is None or not content.strip():
    sys.exit(0)

keyword_val = "{keyword}"
alert_type = "{alert_threshold}"

is_alert = False
msg_suffix = ""

# 캐시에서 이전 데이터 조회
prev_content = ""
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            prev_content = cache.get("content", "")
    except Exception:
        pass

if alert_type == "contains":
    if keyword_val and keyword_val in content:
        is_alert = True
        msg_suffix = f"🎯 지정 키워드 '{{keyword_val}}' 발견!"
elif alert_type == "changed":
    if content.strip() != prev_content.strip():
        is_alert = True
        msg_suffix = f"🔄 콘텐츠 데이터 변동 감지!"
else:
    if content.strip() != prev_content.strip():
        is_alert = True
        msg_suffix = f"📈 신규 데이터 업데이트 완료!"

if is_alert:
    now = datetime.now()
    summary = content[:300] + "..." if len(content) > 300 else content
    message = (
        f"🐙 **[자율 문어발 모니터링 알림]**\\n"
        f"🏷️ 문어발: {filename_py}\\n"
        f"🔗 대상: {url}\\n"
        f"📢 상태: {{msg_suffix}}\\n\\n"
        f"📝 실시간 요약 내용:\\n{{summary}}\\n\\n"
        f"📅 수집 일시: {{now.strftime('%Y-%m-%d %H:%M')}}"
    )
    
    # 텔레그램 알림용 신호 데이터 기록 (원자적 교체)
    try:
        signals = {{}}
        if os.path.exists(SIGNAL_FILE):
            try:
                with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
            except:
                pass
        signals["{filename_py}"] = {{
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "message": message
        }}
        tmp = SIGNAL_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(signals, f, indent=4, ensure_ascii=False)
        os.replace(tmp, SIGNAL_FILE)
        print(f"[SUCCESS] {filename_py} 신호 발행 성공")
    except Exception as e:
        print(f"[ERROR] 신호 파일 쓰기 실패: {{e}}")

# 현재 콘텐츠 캐싱 갱신
try:
    cache_data = {{
        "content": content,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }}
    tmp = DATA_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)
except Exception as e:
    print(f"[ERROR] 캐싱 갱신 실패: {{e}}")

sys.exit(0)
'''

    try:
        os.makedirs(tentacles_dir, exist_ok=True)
        # 파일 저장 (원자적 쓰기)
        tmp_file = file_path + ".tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.write(template_code)
        os.replace(tmp_file, file_path)
        
        # tentacle_config.json에 활성화(True) 등록
        config_file = os.path.join(tentacles_dir, "data", "tentacle_config.json")
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except: pass
        config[filename_py] = True
        
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        tmp_config = config_file + ".tmp"
        with open(tmp_config, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        os.replace(tmp_config, config_file)
        
        return jsonify({"success": True, "filename": filename_py})
    except Exception as e:
        if os.path.exists(file_path + ".tmp"): os.remove(file_path + ".tmp")
        return jsonify({"success": False, "error": f"문어발 코드 생성 중 오류 발생: {str(e)}"})

@app.route('/api/config_list')
def get_config_list():
    target_dir = os.path.join(BASE_DIR, "tentacles", "data")
    configs = []
    if os.path.exists(target_dir):
        for f in sorted(os.listdir(target_dir)):
            if f.endswith('.json'):
                configs.append(f)
    return jsonify(configs)

@app.route('/api/skill_descs')
def get_skill_descs():
    """각 스킬 파일의 AGENT_SKILL_DESC 메타데이터를 읽어 반환"""
    skills_dir = os.path.join(BASE_DIR, "skill_system", "skills")
    result = {}
    if not os.path.exists(skills_dir):
        return jsonify(result)
    for fname in os.listdir(skills_dir):
        if not fname.endswith('.py'):
            continue
        try:
            fpath = os.path.join(skills_dir, fname)
            desc = ""
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('# AGENT_SKILL_DESC:'):
                        desc = line.replace('# AGENT_SKILL_DESC:', '').strip()
                        break
                    if not line.startswith('#') and line:
                        break
            if desc:
                result[fname] = desc
        except Exception:
            pass
    return jsonify(result)

@app.route('/api/memory')
def get_memory():
    chat_id = get_main_chat_id()
    mem_data = memory.load_memory(chat_id)
    return jsonify(mem_data.get("working_memory", []))

@app.route('/api/tts/stop', methods=['POST'])
def tts_stop():
    try:
        from tts_engine import tts
        tts.stop()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    chat_id = get_main_chat_id()
    data = request.json
    user_message = data.get('message', '')
    
    if user_message.strip().lower() in ["/voice off", "/voice on"]:
        action = user_message.strip().lower().split()[1]
        config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8-sig') as f:
                    config = json.load(f)
            except: pass
            
        config["tts_enabled"] = (action == "on")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w', encoding='utf-8-sig') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        msg = "🔊 자동 음성 출력이 활성화되었습니다." if action == "on" else "🔇 자동 음성 출력이 중지되었습니다."
        def quick_reply():
            yield f"data: {json.dumps({'status': 'chunk', 'content': msg})}\n\n"
        return Response(quick_reply(), mimetype='text/event-stream')
    
    memory.add_message(chat_id=chat_id, role="user", content=user_message)
    sync_to_telegram(chat_id, f"💻 **[대시보드 입력]**:\n{user_message}")
    
    def generate():
        has_yielded = False
        full_reply = ""
        for status, content in generate_response_stream(chat_id, user_message, 'embedding'):
            has_yielded = True
            if status == 'chunk':
                full_reply += content
            yield f"data: {json.dumps({'status': status, 'content': content})}\n\n"
        if not has_yielded:
            yield f"data: {json.dumps({'status': 'error', 'content': '엔진에서 응답이 없습니다. Ollama 서버를 확인하세요.'})}\n\n"
        elif full_reply:
            sync_to_telegram(chat_id, full_reply)
            handle_tts_output(chat_id, full_reply)
            
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/chat/voice', methods=['POST'])
def chat_voice():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400
        
    audio_file = request.files['audio']
    
    import tempfile
    import stt_engine
    
    # 봇 환경설정에서 STT 엔진 정보 가져오기
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    stt_engine_type = "google"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            stt_engine_type = cfg.get('stt_engine', 'google')
    except: pass

    fd, temp_audio = tempfile.mkstemp(suffix=".webm")
    os.close(fd)
    
    try:
        audio_file.save(temp_audio)
        text = stt_engine.process_audio(temp_audio, engine=stt_engine_type)
        if not text or text.startswith("[STT 오류"):
            return jsonify({"error": text or "음성 인식 실패"}), 400
            
        chat_id = get_main_chat_id()
        memory.add_message(chat_id=chat_id, role="user", content=text)
        sync_to_telegram(chat_id, f"🎙️ **[음성 입력]**:\n{text}")
        
        def generate():
            yield f"data: {json.dumps({'status': 'user_text', 'content': text})}\n\n"
            has_yielded = False
            full_reply = ""
            for status, content in generate_response_stream(chat_id, text, 'embedding'):
                has_yielded = True
                if status == 'chunk':
                    full_reply += content
                yield f"data: {json.dumps({'status': status, 'content': content})}\n\n"
            if not has_yielded:
                yield f"data: {json.dumps({'status': 'error', 'content': '엔진에서 응답이 없습니다. Ollama 서버를 확인하세요.'})}\n\n"
            elif full_reply:
                sync_to_telegram(chat_id, full_reply)
                handle_tts_output(chat_id, full_reply)
                
        return Response(generate(), mimetype='text/event-stream')
    finally:
        if os.path.exists(temp_audio):
            try: os.remove(temp_audio)
            except: pass

@app.route('/api/command/approve', methods=['POST'])
def approve_command():
    chat_id = get_main_chat_id()
    data = request.json
    cmd = data.get('command')
    
    def execute_and_stream():
        yield f"data: {json.dumps({'status': 'system', 'content': f'명령어 실행 중: {cmd}'})}\n\n"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
            output = str(result.stdout or "") + "\n" + str(result.stderr or "")
            if not output.strip():
                output = "(출력 없음)"
        except Exception as e:
            output = f"[오류]: {str(e)}"
            
        if len(output) > 2000:
            output = output[:2000] + "\n... (생략됨)"
            
        memory.add_message(chat_id=chat_id, role="user", content=f"[터미널 명령어 실행 결과]\n명령어: {cmd}\n결과:\n{output}\n\n위 결과를 바탕으로 분석하거나 사용자에게 답변을 이어나가세요.")
        
        full_reply = ""
        for status, content in generate_response_stream(chat_id, "", 'embedding'):
            if status == 'chunk':
                full_reply += content
            yield f"data: {json.dumps({'status': status, 'content': content})}\n\n"
            
        if full_reply:
            sync_to_telegram(chat_id, full_reply)
            handle_tts_output(chat_id, full_reply)
            
    return Response(execute_and_stream(), mimetype='text/event-stream')

@app.route('/api/command/decline', methods=['POST'])
def decline_command():
    chat_id = get_main_chat_id()
    memory.add_message(chat_id=chat_id, role="user", content="[시스템 알림]: 사용자가 해당 명령어 실행을 거부/취소했습니다. 다른 방법으로 해결하거나 답변을 마무리하세요.")
    
    def stream_rejection():
        full_reply = ""
        for status, content in generate_response_stream(chat_id, "", 'embedding'):
            if status == 'chunk':
                full_reply += content
            yield f"data: {json.dumps({'status': status, 'content': content})}\n\n"
            
        if full_reply:
            sync_to_telegram(chat_id, full_reply)
            handle_tts_output(chat_id, full_reply)
            
    return Response(stream_rejection(), mimetype='text/event-stream')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    if request.method == 'GET':
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8-sig') as f:
                    config = json.load(f)
            except: pass
        return jsonify(config)
        
    elif request.method == 'POST':
        data = request.json
        config = {}
        if os.path.exists(config_file):
            for attempt in range(3):
                try:
                    with open(config_file, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                        if content.strip():
                            config = json.loads(content)
                        break
                except Exception as e:
                    import time
                    time.sleep(0.1)
                    if attempt == 2:
                        return jsonify({"error": "Config is busy"}), 500
            
        config['telegram_token'] = data.get('telegram_token', config.get('telegram_token', ''))
        if 'tts_enabled' in data: config['tts_enabled'] = data['tts_enabled']
        if 'tts_volume' in data: config['tts_volume'] = float(data['tts_volume'])
        if 'tts_rate' in data: config['tts_rate'] = int(data['tts_rate'])
        if 'tts_engine' in data: config['tts_engine'] = data['tts_engine']
        if 'tts_voice' in data: config['tts_voice'] = data['tts_voice']
        if 'stt_engine' in data: config['stt_engine'] = data['stt_engine']
        if 'tg_voice_enabled' in data: config['tg_voice_enabled'] = data['tg_voice_enabled']
        if 'tts_skip_symbols' in data: config['tts_skip_symbols'] = data['tts_skip_symbols']
        if 'tts_destination' in data: config['tts_destination'] = data['tts_destination']
        
        import tempfile
        import shutil
        temp_file = config_file + ".tmp"
        try:
            with open(temp_file, 'w', encoding='utf-8-sig') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            shutil.move(temp_file, config_file)
        except Exception as e:
            if os.path.exists(temp_file): os.remove(temp_file)
            return jsonify({"error": "Failed to write config"}), 500
            
        return jsonify({"success": True})

@app.route('/api/config/reset', methods=['POST'])
def reset_config():
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
            config['telegram_token'] = ""
            with open(config_file, 'w', encoding='utf-8-sig') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except: pass
    return jsonify({"success": True})

@app.route('/api/setup/pull_models', methods=['POST'])
def pull_models():
    # 백그라운드에서 모델 다운로드 프로세스 실행 (비동기로 실행되게 Popen 사용)
    import subprocess
    data = request.json
    model_name = data.get('model', 'nomic-embed-text')
    try:
        subprocess.Popen(['ollama', 'pull', model_name], creationflags=subprocess.CREATE_NO_WINDOW)
        return jsonify({"success": True, "message": f"{model_name} 다운로드 요청이 백그라운드에서 시작되었습니다."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

if __name__ == '__main__':
    print("🚀 Minos 웹 대시보드 서버 실행 중... (http://localhost:5000)")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
