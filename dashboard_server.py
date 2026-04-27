import os
import json
import psutil
from flask import Flask, render_template, request, Response, jsonify
from core_engine import generate_response_stream
from memory_engine import MemoryEngine
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
    except:
        pass

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

@app.route('/api/status')
def get_status():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    gpu_percent = "--"
    vram_percent = "--"
    if GPUtil:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_percent = f"{gpus[0].load * 100:.1f}"
            vram_percent = f"{(gpus[0].memoryUsed / gpus[0].memoryTotal) * 100:.1f}"
            
    # 문어발 상태
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
                
    # 에러 로그
    errors = {}
    error_file = os.path.join(tentacles_dir, "logs", "tentacle_errors.json")
    if os.path.exists(error_file):
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except: pass

    # 스킬(자동 승인) 상태
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

    return jsonify({
        "cpu": cpu,
        "ram": ram,
        "gpu": gpu_percent,
        "vram": vram_percent,
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
    file_type = request.args.get('type') # 'skill' or 'tentacle'
    file_name = request.args.get('name')
    
    if not file_name or '..' in file_name or '/' in file_name or '\\' in file_name:
        return jsonify({"error": "Invalid file name"}), 400
        
    target_dir = os.path.join(BASE_DIR, "skill_system", "skills") if file_type == 'skill' else os.path.join(BASE_DIR, "tentacles")
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
        
    target_dir = os.path.join(BASE_DIR, "skill_system", "skills") if file_type == 'skill' else os.path.join(BASE_DIR, "tentacles")
    file_path = os.path.join(target_dir, file_name)
    
    if not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File not found"})
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return jsonify({"success": True})

@app.route('/api/memory')
def get_memory():
    chat_id = get_main_chat_id()
    mem_data = memory.load_memory(chat_id)
    return jsonify(mem_data.get("working_memory", []))

@app.route('/api/chat', methods=['POST'])
def chat():
    chat_id = get_main_chat_id()
    data = request.json
    user_message = data.get('message', '')
    
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
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout + result.stderr
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
            
    return Response(stream_rejection(), mimetype='text/event-stream')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    if request.method == 'GET':
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except: pass
        return jsonify(config)
        
    elif request.method == 'POST':
        data = request.json
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except: pass
            
        config['telegram_token'] = data.get('telegram_token', config.get('telegram_token', ''))
        if 'tts_enabled' in data: config['tts_enabled'] = data['tts_enabled']
        if 'tts_volume' in data: config['tts_volume'] = float(data['tts_volume'])
        if 'tts_rate' in data: config['tts_rate'] = int(data['tts_rate'])
        if 'stt_engine' in data: config['stt_engine'] = data['stt_engine']
        if 'tg_voice_enabled' in data: config['tg_voice_enabled'] = data['tg_voice_enabled']
        
        with open(config_file, 'w', encoding='utf-8-sig') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
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
