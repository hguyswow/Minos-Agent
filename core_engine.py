# -*- coding: utf-8 -*-
import os
import re
import json
import time
import requests
import psutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
from memory_engine import MemoryEngine

sys.path.append(os.path.join(BASE_DIR, 'skill_system'))
from skill_registry import SkillRegistry

# 설정 불러오기
def load_llm_config():
    config_path = os.path.join(BASE_DIR, "llm_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 기본값
    return {
        "active_engine": "ollama",
        "engines": {
            "ollama": {
                "url": "http://127.0.0.1:11434/v1/chat/completions",
                "model": "gemma4-e4b:q4km",
                "max_tokens": 4096
            }
        }
    }

LLM_CONFIG = load_llm_config()
active_env = LLM_CONFIG.get("active_engine", "ollama")
engine_info = LLM_CONFIG.get("engines", {}).get(active_env, {})
LLAMA_URL = engine_info.get("url", "http://127.0.0.1:11434/v1/chat/completions")
MODEL_NAME = engine_info.get("model", "gemma4-e4b:q4km")
MAX_TOKENS = engine_info.get("max_tokens", 4096)
API_KEY = engine_info.get("api_key", "")

memory = MemoryEngine(memory_dir=os.path.join(BASE_DIR, "memory_logs"), max_working_memory=30)
skills = SkillRegistry(system_dir=os.path.join(BASE_DIR, "skill_system"))

def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return "당신은 AI 어시스턴트입니다."

SYSTEM_PROMPT = load_system_prompt()

def get_static_system_prompt() -> str:
    """Ollama 시스템 프롬프트 캐싱 극대화를 위해 변하지 않는 정적 스킬 목록과 지침만 반환합니다."""
    skills_index_text = skills.get_skills_index_text()
    return SYSTEM_PROMPT + f"\n\n[장착한 스킬 목록]\n{skills_index_text}"

def get_dynamic_reminder(chat_id: str) -> str:
    """CPU/RAM 부하 및 기억 포화도 등의 실시간 변동 데이터를 정적 캐시 파괴 없이 사용자 쿼리 끝부분에 주입하도록 설계된 동적 리마인더입니다."""
    mem_data = memory.load_memory(chat_id)
    working_count = len(mem_data.get("working_memory", [])) // 2 
    max_count = memory.max_working_memory // 2
    cpu_percent = psutil.cpu_percent()
    ram_percent = psutil.virtual_memory().percent
    
    self_awareness_prompt = (
        f"\n\n[당신의 실시간 시스템 상태 (Self-Awareness)]\n"
        f"- 현재 구동 중인 AI 두뇌(모델명): {MODEL_NAME} ({active_env})\n"
        f"- 단기 기억 포화도: {working_count} / {max_count} (최대치 도달 시 장기 기억 압축 마이그레이션이 가동됨)\n"
        f"- 구동 환경 부하: CPU {cpu_percent}%, RAM {ram_percent}%\n"
        f"* 지시사항: 위의 시스템 상태를 실시간으로 참고하여, 만약 단기 기억 포화도가 90% 이상이거나 CPU/RAM 부하가 85%를 초과할 경우 대화 중 사용자에게 '기억 정리(Memory Cleanup)'를 정중히 권고하세요."
    )
    return self_awareness_prompt

def generate_response_stream(chat_id: str, current_query: str = "", memory_mode: str = 'embedding'):
    """
    LLM에 요청을 보내고 스트리밍 응답을 Generator 형태로 반환합니다.
    [v3 - 캐시 최적화 및 Ollama 추론 가속 반영]
    yield (status, content) 형태로 반환하여 텔레그램과 대시보드가 범용적으로 사용할 수 있게 합니다.
    status: 'chunk', 'done', 'error'
    """
    # 1. 정적 프롬프트는 100% 캐싱되도록 상단 유지
    static_system_prompt = get_static_system_prompt()
    
    # 2. 동적 데이터(CPU/RAM/기억)는 캐시 파괴 방지를 위해 오직 쿼리 끝부분 리마인더와 병합
    dynamic_reminder = get_dynamic_reminder(chat_id)
    
    # 로컬 모델(특히 작은 모델)이 시스템 프롬프트(영혼)를 망각하는 것을 방지하기 위해 사용자 질문 끝에 말투 리마인더 강제 주입
    persona_reminder = "\n\n(※ 절대 지시: 반드시 '형님!'이라고 부르는 명랑하고 깍듯한 꼬마 비서 '알쫑이/Minos'의 말투를 유지해서 대답하세요.)"
    
    optimized_query = (current_query or "") + dynamic_reminder + persona_reminder

    optimized_messages = memory.get_optimized_context(
        chat_id=chat_id, 
        base_system_prompt=static_system_prompt,
        current_query=optimized_query,
        memory_mode=memory_mode
    )
    
    # 3. 로컬 Ollama 및 TurboQuant 연산 가속을 위한 options 튜닝
    payload = {
        'model': MODEL_NAME,
        'messages': optimized_messages,
        'temperature': 0.7,
        'max_tokens': MAX_TOKENS,
        'stream': True,
        'num_ctx': 16384,
        'options': {
            'num_ctx': 16384,
            'num_predict': 384,      # 불필요한 장황 생성 방지 및 속도 극대화
            'temperature': 0.7,
            'top_k': 40,
            'top_p': 0.9,
            'f16_kv': True,          # 16비트 KV 캐시 반정밀도 가속
            'use_mmap': True,        # 메모리 고속 매핑 가동
            'use_mlock': True        # OS 페이지 스왑 아웃 방지
        }
    }
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    try:
        response = requests.post(LLAMA_URL, headers=headers, json=payload, stream=True, timeout=300)
        response.raise_for_status()
        
        reply_text = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data_str = decoded_line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                reply_text += content
                                yield ('chunk', content)
                    except json.JSONDecodeError:
                        continue
                        
        # 생성 완료 후 기억에 저장 및 스킬 파싱 처리
        if reply_text.strip():
            memory.add_message(chat_id=chat_id, role="assistant", content=reply_text)
            
            # 스킬 학습 처리부
            skill_match = re.search(r'<SAVE_SKILL name="(.*?)" desc="(.*?)">(.*?)</SAVE_SKILL>', reply_text, re.IGNORECASE | re.DOTALL)
            if skill_match:
                skill_name = skill_match.group(1).strip()
                skill_desc = skill_match.group(2).strip()
                skill_code = skill_match.group(3).strip()
                skills.create_skill(skill_name, skill_desc, skill_code)
                yield ('system', f"✨ 새로운 스킬 '{skill_name}.py'가 성공적으로 학습 및 등록되었습니다!")

            # 터미널 명령어 실행 처리부
            cmd_match = re.search(r'<CMD>(.*?)</CMD>', reply_text, re.IGNORECASE | re.DOTALL)
            if cmd_match:
                cmd = cmd_match.group(1).strip()
                # 텔레그램이나 대시보드 측에서 사용자 승인을 받도록 command 이벤트를 보냅니다.
                yield ('command_request', cmd)
                
        yield ('done', reply_text)
        
    except Exception as e:
        yield ('error', str(e))
