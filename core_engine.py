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

# 설정
LLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"
memory = MemoryEngine(memory_dir=os.path.join(BASE_DIR, "memory_logs"), max_working_memory=30)
skills = SkillRegistry(system_dir=os.path.join(BASE_DIR, "skill_system"))

def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return "당신은 AI 어시스턴트입니다."

SYSTEM_PROMPT = load_system_prompt()

def get_dynamic_prompt(chat_id: str) -> str:
    """시스템 부하 상태와 스킬 목록을 주입한 동적 프롬프트를 생성합니다."""
    skills_index_text = skills.get_skills_index_text()
    
    mem_data = memory.load_memory(chat_id)
    working_count = len(mem_data.get("working_memory", [])) // 2 
    max_count = memory.max_working_memory // 2
    cpu_percent = psutil.cpu_percent()
    ram_percent = psutil.virtual_memory().percent
    
    self_awareness_prompt = (
        f"\n\n[당신의 현재 상태 (Self-Awareness)]\n"
        f"- 단기 기억 포화도: {working_count} / {max_count} (최대치 도달 시 오래된 기억부터 강제 유실됨)\n"
        f"- 구동 환경 부하: CPU {cpu_percent}%, RAM {ram_percent}%\n"
        f"* 지시사항: 당신은 매 턴마다 자신의 위 상태를 인지해야 합니다. 만약 단기 기억이 꽉 차가거나 시스템 부하가 높다면, 대답 시 먼저 사용자에게 '기억 정리가 필요하다'고 건의하십시오."
    )
    
    return SYSTEM_PROMPT + f"\n\n[장착한 스킬 목록]\n{skills_index_text}" + self_awareness_prompt

def generate_response_stream(chat_id: str, current_query: str = "", memory_mode: str = 'embedding'):
    """
    LLM에 요청을 보내고 스트리밍 응답을 Generator 형태로 반환합니다.
    yield (status, content) 형태로 반환하여 텔레그램과 대시보드가 범용적으로 사용할 수 있게 합니다.
    status: 'chunk', 'done', 'error'
    """
    dynamic_system_prompt = get_dynamic_prompt(chat_id)
    
    optimized_messages = memory.get_optimized_context(
        chat_id=chat_id, 
        base_system_prompt=dynamic_system_prompt,
        current_query=current_query,
        memory_mode=memory_mode
    )
    
    payload = {
        'model': 'gemma4-e4b:q4km',
        'messages': optimized_messages,
        'temperature': 0.7,
        'max_tokens': 4096,
        'stream': True
    }
    
    try:
        response = requests.post(LLAMA_URL, json=payload, stream=True, timeout=300)
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
