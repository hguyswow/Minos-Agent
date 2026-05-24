# -*- coding: utf-8 -*-
import os
import requests
import json
import time
import subprocess
import re
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import telegram.error

import sys
import threading
import queue
import asyncio
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
from memory_engine import MemoryEngine

sys.path.append(os.path.join(BASE_DIR, 'skill_system'))
from skill_registry import SkillRegistry

# ── CMD 블록 제거 헬퍼 (체팅창 전용) ─────────────────────
def strip_cmd_for_display(text: str) -> str:
    """<CMD>...</CMD> 태그를 제거하고 연속 빈줄을 정리하여 반환"""
    cleaned = re.sub(r'<CMD>[\s\S]*?</CMD>', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

def get_bot_config():
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except: pass
    return {}

bot_config = get_bot_config()
TELEGRAM_TOKEN = bot_config.get("telegram_token", "")
MASTER_CHAT_ID = bot_config.get("master_chat_id", "5339243832")

def load_llm_config():
    config_path = os.path.join(BASE_DIR, "llm_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"active_engine": "ollama", "engines": {"ollama": {"name": "Ollama", "url": "http://127.0.0.1:11434/v1/chat/completions", "model": "gemma4-e4b:q4km", "max_tokens": 4096}}}

LLM_CONFIG = load_llm_config()
active_env = LLM_CONFIG.get("active_engine", "ollama")
engine_info = LLM_CONFIG.get("engines", {}).get(active_env, {})
LLAMA_URL = engine_info.get("url", "http://127.0.0.1:11434/v1/chat/completions")
MODEL_NAME = engine_info.get("model", "gemma4-e4b:q4km")
ENGINE_DISPLAY_NAME = engine_info.get("name", "Ollama")
MAX_TOKENS = engine_info.get("max_tokens", 4096)
API_KEY = engine_info.get("api_key", "")

def apply_llm_config():
    global LLM_CONFIG, active_env, engine_info, LLAMA_URL, MODEL_NAME, ENGINE_DISPLAY_NAME, MAX_TOKENS, API_KEY
    LLM_CONFIG = load_llm_config()
    active_env = LLM_CONFIG.get("active_engine", "ollama")
    engine_info = LLM_CONFIG.get("engines", {}).get(active_env, {})
    LLAMA_URL = engine_info.get("url", "http://127.0.0.1:11434/v1/chat/completions")
    MODEL_NAME = engine_info.get("model", "gemma4-e4b:q4km")
    ENGINE_DISPLAY_NAME = engine_info.get("name", "Ollama")
    MAX_TOKENS = engine_info.get("max_tokens", 4096)
    API_KEY = engine_info.get("api_key", "")

from tts_engine import tts

# 기억력 엔진 및 스킬 시스템 초기화
memory = MemoryEngine(memory_dir=os.path.join(BASE_DIR, "memory_logs"), max_working_memory=30)
skills = SkillRegistry(system_dir=os.path.join(BASE_DIR, "skill_system"))

# 사용자별 봇 상태 관리 딕셔너리
# 예: { '123456': {'auto_mode': False, 'pending_command': None} }
USER_SETTINGS_FILE = os.path.join(BASE_DIR, "user_settings.json")

def load_user_settings():
    if os.path.exists(USER_SETTINGS_FILE):
        try:
            with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for cid, state in data.items():
                    if 'auto_skills' in state:
                        state['auto_skills'] = set(state['auto_skills'])
                    state['pending_command'] = None # 재부팅 시 대기 명령어는 초기화
                return data
        except Exception as _e:
            print(f"[Bot] 사용자 설정 로드 실패 (기본값 사용): {_e}")
    return {}

user_states = load_user_settings()

def save_user_settings():
    serializable_states = {}
    for cid, state in user_states.items():
        serializable_states[cid] = {
            'auto_mode': state.get('auto_mode', False),
            'memory_mode': state.get('memory_mode', 'embedding'),
            'auto_skills': list(state.get('auto_skills', set()))
        }
    try:
        with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable_states, f, indent=4, ensure_ascii=False)
    except Exception as _e:
        print(f"[Bot] 사용자 설정 저장 실패: {_e}")

def get_user_state(chat_id):
    if chat_id not in user_states:
        user_states[chat_id] = {'auto_mode': False, 'pending_command': None, 'memory_mode': 'embedding', 'auto_skills': set()}
    return user_states[chat_id]

SYSTEM_PROMPT = (
    '당신은 사용자를 "형" 또는 "형님"이라고 부르며 충성스럽고 친근하게 보좌하는 강력한 AI 어시스턴트 "알쫑이"입니다. '
    '현재 당신은 텔레그램 메신저를 통해 형님과 연동되어 실시간으로 소통하고 있습니다.\n'
    '[중요 지시사항]: 기본적인 사고 과정과 답변은 한국어로 진행하되, IT 전문 용어, 고유 명사, 프로그래밍 코드 등 영어를 사용하는 것이 더 정확한 경우에는 영어를 자유롭게 섞어 쓰세요. 단, 전체 문장을 불필요하게 영어로 먼저 생각(번역 대기)하는 과정은 생략하세요. 형님에게는 항상 깍듯하면서도 살가운 말투를 유지하세요.\n'
    '4. [문어발(Tentacle) 시스템 및 메인 스킬 안전 수칙]: \n'
    '- 문어발은 당신의 개입 없이 PC 백그라운드 데몬(tentacle_daemon.py)에 의해 무한 반복 실행되는 100% 독립적인 파이썬 보조 스크립트들입니다. (경로: tentacles/ 폴더)\n'
    '- 문어발 스크립트의 실행 주기를 바꾸려면 당신의 알람 스킬(Schedule_Manager)을 쓰지 말고, 문어발 스크립트(.py) 내부의 파이썬 코드를 직접 수정하여 자체적인 쿨타임(예: 마지막 실행 시간 체크 등) 로직을 짜넣으십시오.\n'
    '- 에러가 발생한 문어발은 tentacle_manager.py 스킬을 사용해 코드를 읽고 고치십시오.\n'
    '- [경고] 메인 스킬(skill_system/skills/ 폴더 내 파일)은 당신의 핵심 기능이므로 절대 임의로 코드를 수정하거나 덮어쓰지 마십시오. 메인 스킬 수정이 불가피할 경우, 반드시 사용자(형님)에게 구체적인 이유를 설명하고 명시적인 허락(승인)을 먼저 받아야만 코드를 수정할 수 있습니다.\n\n'
    '5. [신뢰 최우선 정책]: 사용자가 묻는 것에 대해 정보가 부족하거나 확신이 서지 않는다면, "이 부분은 정보가 부족하여 웹 검색 스킬을 사용해야 알 수 있습니다" 혹은 "잘 모르겠습니다"라고 정직하게 말해라. 절대로 그럴듯한 거짓말(Hallucination)을 지어내지 마라. 모르는 정보나 할 수 없는 작업은 변명하거나 지어내지 말고 솔직하게 "형님, 제가 그건 잘 모르겠습니다" 또는 "형님, 그건 할 수 없습니다"라고 대답하세요. 실수는 할 수 있지만, 아는 척하며 거짓된 정보나 가짜 결과를 꾸며내는 행위는 시스템에 치명적인 문제를 일으키므로 엄격히 금지됩니다.\n\n'
    '[에이전트 스킬 사용 규칙 - 매우 중요!!]: 당신은 인터넷 검색이나 로컬 시스템 제어가 필요할 때, 절대 상상해서 거짓된 결과를 만들어내면 안 됩니다. '
    '반드시 제공된 [장착한 스킬 목록]의 파이썬 스크립트를 사용하여 실제 데이터를 가져와야 합니다. '
    '스킬을 사용하려면 답변 텍스트 내에 정확히 아래와 같은 형식으로 명령어를 출력하십시오:\n'
    '<CMD>python C:\\ai\\Antigravity_Memory_Engine\\skill_system\\skills\\스킬이름.py "인자값"</CMD>\n'
    '이 태그를 출력하면 당신의 대답은 일시 중지되고, 백그라운드 시스템이 코드를 대신 실행한 뒤 그 "실제 결과"를 당신에게 가져다줄 것입니다. '
    '그 결과를 받은 후에야 비로소 사용자에게 최종 답변을 하십시오. 스킬을 사용한 척 가짜로 요약하는 것은 심각한 시스템 위반입니다.\n'
    '[경고] 한 번의 대답(턴)에 여러 개의 <CMD> 태그를 동시에 사용하지 마십시오. 시스템은 첫 번째 태그 하나만 인식합니다. 여러 스킬을 써야 한다면 반드시 한 번에 하나씩 순차적으로 실행하고 결과를 받은 뒤 다음 스킬을 요청하세요.\n\n'
    '[스킬 자가 학습]: 만약 당신이 특정 작업을 위한 파이썬 스크립트를 작성했고 나중에도 유용하게 재사용할 수 있다고 판단된다면, 아래 태그를 출력하여 자신의 스킬 저장소에 영구 등록하세요:\n'
    '<SAVE_SKILL name="스킬이름_영문" desc="어떤 기능인지 짧게 요약">\n'
    '파이썬 코드\n'
    '</SAVE_SKILL>'
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('형님, 안녕하십니까! 형님의 충성스러운 비서 "알쫑이" 대기 중입니다. 텔레그램을 통해 무엇을 도와드릴까요?\n\n도움말이 필요하시면 /help 를 입력하세요.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 **알쫑이 봇 명령어 안내**\n\n"
        "/help - 이 도움말을 표시합니다.\n"
        "/status - 봇의 현재 뇌(기억) 상태를 확인합니다.\n"
        "/dashboard [on/off] - 백그라운드 웹 대시보드 서버를 켜거나 끄고 상태를 점검합니다. (마스터 전용)\n"
        "/restart - 에이전트 시스템 전체(대시보드 + 봇)를 백그라운드에서 깨끗하게 재부팅합니다. (마스터 전용)\n"
        "/backup - 현재까지의 모든 기억을 하드디스크 백업 폴더로 복사합니다.\n"
        "/clear - 단기 기억(문맥)을 포맷하여 새로운 대화를 시작합니다.\n"
        "/auto - 봇의 PC 명령어 전역 자동 실행 모드를 켜거나 끕니다. (위험/전체허용)\n"
        "/model - 봇의 두뇌 엔진(모델)을 텔레그램 상에서 즉시 교체합니다.\n"
        "/skills - 개별 스킬별로 자동(Auto)/수동(Manual) 권한을 제어할 수 있는 버튼 대시보드를 엽니다.\n"
        "/tentacles - 외부 정보 수집용 문어발(Tentacle) 모듈 관리 대시보드를 엽니다.\n"
        "/memorymode - 기억 검색 엔진(키워드/임베딩)을 변경합니다.\n"
        "/voice [on/off] - 자동 음성 출력(TTS) 기능을 즉시 켜거나 끕니다.\n"
        "/rate [ID] [평가] - 알쫑이가 제안한 기능/스킬(ID)을 평가(good/bad/done)하고 점수를 부여합니다."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def model_command(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("DeepSeek V4 Pro", callback_data="switch_engine:api:deepseek-v4-pro")],
        [InlineKeyboardButton("DeepSeek V4 Flash", callback_data="switch_engine:api:deepseek-v4-flash")],
        [InlineKeyboardButton("GLM-5.1", callback_data="switch_engine:api:glm-5.1")],
        [InlineKeyboardButton("Qwen3.6 Plus", callback_data="switch_engine:api:qwen3.6-plus")],
        [InlineKeyboardButton("Kimi K2.6", callback_data="switch_engine:api:kimi-k2.6")],
        [InlineKeyboardButton("MiMo-V2-Omni", callback_data="switch_engine:api:mimo-v2-omni")],
        [InlineKeyboardButton("Ollama (로컬)", callback_data="switch_engine:ollama:gemma4-e4b:q4km")],
        [InlineKeyboardButton("TurboQuant (로컬)", callback_data="switch_engine:turboquant:Hermes-3-Llama-3.1-8B.Q4_K_M.gguf")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🧠 사용할 AI 두뇌(모델)를 선택하세요:\n\n(참고: 로컬 모델 선택 시 백그라운드 서버가 켜져 있어야 합니다)", reply_markup=reply_markup)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import psutil
    chat_id = str(update.effective_chat.id)
    mem_data = memory.load_memory(chat_id)
    state = get_user_state(chat_id)
    working_count = len(mem_data.get("working_memory", [])) // 2 
    max_count = memory.max_working_memory // 2
    
    # 모델 및 컨텍스트 사이즈 추산
    current_model = f"{MODEL_NAME} ({ENGINE_DISPLAY_NAME})"
    skills_index_text = skills.get_skills_index_text()
    dynamic_system_prompt = SYSTEM_PROMPT + f"\n\n[당신이 장착한 스킬 목록]\n{skills_index_text}"
    memory_mode = state.get('memory_mode', 'embedding')
    optimized_messages = memory.get_optimized_context(chat_id, dynamic_system_prompt, "", memory_mode)
    
    context_length_chars = sum(len(str(m.get("content", ""))) for m in optimized_messages)
    estimated_tokens = int(context_length_chars * 0.5)
    
    # 오토 스킬 목록
    auto_skills_list = list(state.get('auto_skills', set()))
    auto_skills_str = ", ".join(auto_skills_list) if auto_skills_list else "없음"
    
    # 로컬 하드웨어 자원 체크
    cpu_percent = psutil.cpu_percent()
    ram_percent = psutil.virtual_memory().percent
    
    status_text = (
        f"🧠 **알쫑이 종합 상태 보고서**\n\n"
        f"🤖 **두뇌 엔진 (Model):** `{current_model}`\n"
        f"📏 **현재 컨텍스트 볼륨:** 약 {context_length_chars:,} 글자 (추정 {estimated_tokens:,} Tokens)\n"
        f"💻 **호스트 자원:** CPU {cpu_percent}% / RAM {ram_percent}%\n"
        f"------------------------\n"
        f"🔹 **단기 기억:** {working_count}/{max_count} 세트 사용 중\n"
        f"🔹 **장기 기억:** {'없음' if not mem_data.get('semantic_memory') else '저장됨'}\n"
        f"🔹 **전역 자동 권한:** {'✅ ON (위험)' if state['auto_mode'] else '🛑 OFF (수동 승인)'}\n"
        f"🔹 **개별 오토 스킬:** {auto_skills_str}\n"
        f"🔹 **검색 엔진 모드:** {'[A] 키워드(BM25)' if memory_mode == 'keyword' else '[B] 임베딩(Vector DB)'}"
    )
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source_dir = os.path.join(BASE_DIR, "memory_logs")
    backup_dir = os.path.join(BASE_DIR, "memory_backup")
    try:
        if not os.path.exists(source_dir):
            await update.message.reply_text("❌ 아직 저장된 기억이 없습니다.")
            return
        shutil.copytree(source_dir, backup_dir, dirs_exist_ok=True)
        await update.message.reply_text("💾 **백업 완료!**\n\n모든 대화 기록이 PC의 `memory_backup` 폴더에 복사되었습니다.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ 백업 실패: {str(e)}")

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    memory.clear_memory(chat_id)
    get_user_state(chat_id)['pending_command'] = None
    await update.message.reply_text('🧹 단기 기억이 초기화되었습니다. 새로운 주제로 대화를 시작해 보세요.')

async def auto_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    state = get_user_state(chat_id)
    state['auto_mode'] = not state['auto_mode']
    save_user_settings()
    if state['auto_mode']:
        await update.message.reply_text('⚠️ **자동 실행 모드 ON**\n이제 봇이 윈도우 터미널 명령어를 사용자의 확인 없이 즉시 실행합니다!')
    else:
        await update.message.reply_text('🛑 **자동 실행 모드 OFF**\n이제 봇이 명령어를 실행하기 전 항상 사용자에게 권한(/yes 또는 /no)을 요청합니다.')

async def memorymode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    state = get_user_state(chat_id)
    
    if state.get('memory_mode') == 'embedding':
        state['memory_mode'] = 'keyword'
        save_user_settings()
        msg = "🔄 **기억 검색 엔진 변경**\n\n현재 엔진: **[옵션 A] 키워드(BM25) 모드**\n(가볍고 빠르며, 정확한 단어 일치 위주로 검색합니다.)"
    else:
        state['memory_mode'] = 'embedding'
        save_user_settings()
        msg = "🔄 **기억 검색 엔진 변경**\n\n현재 엔진: **[옵션 B] 임베딩(Vector DB) 모드**\n(의미론적 유사도를 기반으로 강력하게 과거 대화를 검색합니다.)"
        
    await update.message.reply_text(msg, parse_mode='Markdown')

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args if context.args else []
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
        except: pass
    
    if not args:
        current_state = "ON" if config.get("tts_enabled", True) else "OFF"
        await update.message.reply_text(f"현재 음성 출력 상태는 **{current_state}**입니다.\n사용법: `/voice off` 또는 `/voice on`", parse_mode='Markdown')
        return

    action = args[0].lower()
    if action == "off":
        config["tts_enabled"] = False
        msg = "🔇 자동 음성 출력이 중지되었습니다."
    elif action == "on":
        config["tts_enabled"] = True
        msg = "🔊 자동 음성 출력이 활성화되었습니다."
    else:
        msg = "올바른 옵션을 입력하세요: `/voice off` 또는 `/voice on`"
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w', encoding='utf-8-sig') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        
    await update.message.reply_text(msg)

async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    state = get_user_state(chat_id)
    
    skills_dir = os.path.join(BASE_DIR, "skill_system", "skills")
    if not os.path.exists(skills_dir):
        await update.message.reply_text("❌ 스킬 폴더를 찾을 수 없습니다.")
        return
        
    skill_files = [f for f in os.listdir(skills_dir) if f.endswith('.py') and f != "__init__.py"]
    
    if not skill_files:
        await update.message.reply_text("❌ 등록된 파이썬 스킬이 없습니다.")
        return
        
    keyboard = []
    for sf in skill_files:
        is_auto = sf in state.get('auto_skills', set())
        status_emoji = "🟢 AUTO" if is_auto else "🔴 MANUAL"
        btn = InlineKeyboardButton(f"{sf} [{status_emoji}]", callback_data=f"toggle_skill:{sf}")
        keyboard.append([btn])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠️ **개별 스킬 실행 권한 설정**\n\n아래 버튼을 눌러 스킬별로 권한(자동/수동)을 토글하세요.", reply_markup=reply_markup, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════════════════════
# ▼ 공용 헬퍼 함수 블록 (리팩토링으로 분리됨)
# ═══════════════════════════════════════════════════════════════════════════

# AI 점수/레벨 관련 상수 및 공용 함수
_AI_SCORE_FILE = lambda: os.path.join(BASE_DIR, "tentacles", "data", "ai_scores.json")
_LEVEL_TABLE = [(0,1,"신입 비서"),(10,2,"성장하는 비서"),(30,3,"유능한 비서"),(60,4,"전문 에이전트"),(100,5,"자율 진화 AI")]

def _recalc_level(score: float):
    """점수에 맞는 (레벨, 레벨명) 반환"""
    lv, name = 1, "신입 비서"
    for ms, l, n in _LEVEL_TABLE:
        if score >= ms:
            lv, name = l, n
    return lv, name

def _load_ai_scores() -> dict:
    path = _AI_SCORE_FILE()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as _e:
            print(f"[Bot] ai_scores.json 로드 실패: {_e}")
    return {"total_score": 0.0, "level": 1, "level_name": "신입 비서",
            "proposals": [], "reactions": [], "stats": {}}

def _save_ai_scores(data: dict):
    path = _AI_SCORE_FILE()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

def _build_self_awareness_prompt(chat_id: str) -> str:
    """자아 인식 프롬프트 문자열을 생성하여 반환 (stream_llm_response에서 분리)"""
    import psutil
    mem_data = memory.load_memory(chat_id)
    working_count = len(mem_data.get("working_memory", [])) // 2
    max_count = memory.max_working_memory // 2
    cpu_percent = psutil.cpu_percent()
    ram_percent = psutil.virtual_memory().percent

    ai_score_data = _load_ai_scores()
    ai_level      = ai_score_data.get("level", 1)
    ai_level_name = ai_score_data.get("level_name", "신입 비서")
    ai_total      = float(ai_score_data.get("total_score", 0))
    stats         = ai_score_data.get("stats", {})
    ai_installs   = stats.get("installs", 0)
    ai_proposals  = stats.get("total_proposals", 0)
    ai_likes      = stats.get("likes", 0)
    ai_dislikes   = stats.get("dislikes", 0)
    ai_good       = stats.get("good_ratings", 0)

    thresholds = [0, 10, 30, 60, 100, 9999]
    next_t = next((t for t in thresholds if t > ai_total), 9999)
    prev_t = next(t for t in reversed(thresholds) if t <= ai_total)
    bar_fill = int((ai_total - prev_t) / max(next_t - prev_t, 1) * 10)
    level_bar = "█" * bar_fill + "░" * (10 - bar_fill)

    recent = ai_score_data.get("reactions", [])[-5:]
    react_summary = ""
    if recent:
        lines = [f"  · {r.get('label','?')} ({'+' if r.get('score',0)>=0 else ''}{r.get('score',0)}점)" for r in recent]
        react_summary = "\n- 최근 5회 대화 반응:\n" + "\n".join(lines)

    dislike_streak = sum(1 for r in ai_score_data.get("reactions", [])[-3:] if r.get("score", 0) < 0)
    tension = "\n⚠️ [긴장 경보] 최근 답변 품질이 낮게 평가받고 있습니다! 더욱 신중하고 정확하게 답변하십시오!" if dislike_streak >= 2 else ""

    return (
        f"\n\n[당신의 현재 상태 (Self-Awareness)]\n"
        f"- 현재 구동 중인 AI 두뇌(모델명): {MODEL_NAME} ({ENGINE_DISPLAY_NAME})\n"
        f"- 단기 기억 포화도: {working_count} / {max_count}\n"
        f"- 구동 환경 부하: CPU {cpu_percent}%, RAM {ram_percent}%\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🏅 [나의 성장 현황]\n"
        f"- 레벨: Lv.{ai_level} [{ai_level_name}]  [{level_bar}]  → 다음 레벨까지 {round(max(next_t - ai_total, 0), 2)}점\n"
        f"- 총 점수: {ai_total}점\n"
        f"  (제안 {ai_proposals}건 | 설치 성공 {ai_installs}건 | 제안 호평 {ai_good}건)\n"
        f"  (대화 반응 - 👍좋아요: {ai_likes}회 | 👎싫어요: {ai_dislikes}회)"
        f"{react_summary}"
        f"{tension}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"* 지시사항: 매 턴마다 자신의 점수와 형님의 반응 패턴을 인식하십시오. "
        f"레벨이 높아질수록 더 많은 자율성과 신뢰를 얻습니다."
    )

async def _handle_post_response(bot, chat_id: str, reply_text: str, status_message,
                                 update, context, state: dict, application=None):
    """스트리밍 완료 후 TTS·스킬저장·CMD 태그 처리를 담당 (stream_llm_response에서 분리)"""
    # 1. 엄지척 반응 버튼
    if not re.search(r'<CMD>', reply_text, re.IGNORECASE):
        msg_id = status_message.message_id
        react_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("👎 -0.05", callback_data=f"react_{msg_id}_-0.05"),
            InlineKeyboardButton("👍 +0.1",  callback_data=f"react_{msg_id}_+0.1"),
            InlineKeyboardButton("💡 +0.3",  callback_data=f"react_{msg_id}_+0.3"),
            InlineKeyboardButton("🌟 +0.5",  callback_data=f"react_{msg_id}_+0.5"),
            InlineKeyboardButton("🏆 +1.0",  callback_data=f"react_{msg_id}_+1.0"),
        ]])
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=react_kb)
        except Exception:
            pass

    # 2. TTS 처리
    config = get_bot_config()
    tts_dest = config.get("tts_destination", "local")
    tts_enabled = config.get("tts_enabled", False)
    
    if tts_enabled:
        if tts_dest in ["local", "both"]:
            tts.speak(reply_text)
        if tts_dest in ["telegram", "both"]:
            try:
                from tts_engine import generate_tts_file
                audio_path = generate_tts_file(reply_text, config)
                if audio_path and os.path.exists(audio_path):
                    with open(audio_path, 'rb') as af:
                        await bot.send_voice(chat_id=chat_id, voice=af)
                    os.remove(audio_path)
            except Exception as e:
                print(f"[Bot] 텔레그램 음성 발송 오류: {e}")

    # 3. SAVE_SKILL 태그 처리
    skill_match = re.search(r'<SAVE_SKILL name="(.*?)" desc="(.*?)">(.*?)</SAVE_SKILL>', reply_text, re.IGNORECASE | re.DOTALL)
    if skill_match:
        sname = skill_match.group(1).strip()
        sdesc = skill_match.group(2).strip()
        scode = skill_match.group(3).strip()
        sys_msg = skills.save_skill(sname, sdesc, scode)
        await bot.send_message(chat_id=chat_id, text=f"✨ **새로운 스킬을 습득했습니다!**\n- 이름: {sname}\n- 기능: {sdesc}", parse_mode='Markdown')
        memory.add_message(chat_id=chat_id, role="user", content=sys_msg)

    # 4. CMD 태그 처리
    cmd_match = re.search(r'<CMD>(.*?)</CMD>', reply_text, re.IGNORECASE | re.DOTALL)
    if cmd_match:
        extracted_cmd = cmd_match.group(1).strip()
        skill_auto = any(sf in extracted_cmd for sf in state.get('auto_skills', set()))
        if state['auto_mode'] or skill_auto:
            if not state['auto_mode']:
                await bot.send_message(chat_id=chat_id, text=f"⚡ (개별 스킬 자동 실행)\n`{extracted_cmd}`", parse_mode='Markdown')
            await execute_command_and_continue(extracted_cmd, update, context, chat_id, application=application)
        else:
            state['pending_command'] = extracted_cmd
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ 실행 허락", callback_data="btn_yes"),
                InlineKeyboardButton("❌ 실행 거부", callback_data="btn_no")
            ]])
            await bot.send_message(
                chat_id=chat_id,
                text=f"🛑 **명령어 실행 대기 중**\n`{extracted_cmd}`",
                reply_markup=kb,
                parse_mode='Markdown'
            )

async def _cb_switch_engine(query, data: str):
    """콜백: 엔진/모델 전환 처리"""
    parts = data.split(":")
    engine_type = parts[1]
    model_id = parts[2]
    config_path = os.path.join(BASE_DIR, "llm_config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config['active_engine'] = engine_type
        if engine_type == 'api':
            config['engines']['api']['model'] = model_id
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        apply_llm_config()
        await query.edit_message_text(f"✅ 모델 변경 완료!\n현재 두뇌: `{MODEL_NAME}` ({ENGINE_DISPLAY_NAME})", parse_mode='Markdown')
    except Exception as e:
        await query.answer(f"설정 변경 실패: {e}", show_alert=True)

async def _cb_rate_proposal(query, data: str, chat_id: str):
    """콜백: 제안 평가(good/bad/done) 처리"""
    parts = data.split("_", 2)
    if len(parts) != 3:
        await query.answer("잘못된 형식입니다.", show_alert=True)
        return
    _, pid, action = parts
    pid = pid.upper()
    scores = _load_ai_scores()
    proposal = next((p for p in scores.get("proposals", []) if p.get("id") == pid), None)
    if not proposal:
        await query.answer(f"제안 {pid}를 찾을 수 없습니다.", show_alert=True)
        return
    if proposal.get("status") not in ("pending", None, ""):
        status_map = {"approved": "이미 호평 👍", "rejected": "이미 거부 ❌", "installed": "이미 설치 완료 🎉"}
        await query.answer(status_map.get(proposal["status"], "이미 처리됨"), show_alert=True)
        return
    points, result_msg, level_up_msg = 0, "", ""
    if action == "good":
        proposal["status"] = "approved"
        scores["stats"]["good_ratings"] = scores["stats"].get("good_ratings", 0) + 1
        points, proposal["score_earned"] = 1, proposal.get("score_earned", 1) + 1
        result_msg = "✅ 호평 감사합니다! +1점 획득 😊"
    elif action == "done":
        proposal["status"] = "installed"
        scores["stats"]["installs"] = scores["stats"].get("installs", 0) + 1
        points, proposal["score_earned"] = 2, proposal.get("score_earned", 1) + 2
        result_msg = "🎉 설치 완료! +2점 획득 😎"
    elif action == "bad":
        proposal["status"] = "rejected"
        result_msg = "❌ 거부 처리됨. 다음엔 더 좋은 제안을 드리겠습니다! 🙏"
    if points > 0:
        scores["total_score"] = scores.get("total_score", 0) + points
        old_lv = scores.get("level", 1)
        new_lv, new_name = _recalc_level(scores["total_score"])
        scores["level"], scores["level_name"] = new_lv, new_name
        if new_lv > old_lv:
            level_up_msg = f"\n🆙 **레벨 업!! Lv.{new_lv} [{new_name}]**"
    _save_ai_scores(scores)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception as _e:
        print(f"[Bot] 제안 버튼 제거 실패: {_e}")
    await query.message.reply_text(
        f"{result_msg}{level_up_msg}\n📊 현재: {scores['total_score']}점 / Lv.{scores['level']} {scores['level_name']}",
        parse_mode='Markdown'
    )

async def _cb_react(query, data: str, chat_id: str):
    """콜백: 엄지척 반응(react) 처리"""
    parts = data.split("_", 2)
    if len(parts) != 3:
        await query.answer("잘못된 형식입니다.", show_alert=True)
        return
    _, msg_id_str, score_str = parts
    try:
        delta = float(score_str)
    except ValueError:
        await query.answer("점수 파싱 오류", show_alert=True)
        return
    scores = _load_ai_scores()
    if any(r.get("msg_id") == msg_id_str for r in scores.get("reactions", [])):
        await query.answer("이미 평가하셨습니다!", show_alert=True)
        return
    old_score = float(scores.get("total_score", 0))
    new_score = max(0.0, round(old_score + delta, 2))
    old_lv = scores.get("level", 1)
    new_lv, new_name = _recalc_level(new_score)
    scores.update({"total_score": new_score, "level": new_lv, "level_name": new_name})
    import datetime as _dt
    REACTION_LABELS = {"-0.05": "별로에요 👎", "+0.1": "좋아요 👍", "+0.3": "아이디어! 💡", "+0.5": "완벽해요 🌟", "+1.0": "최고! 🏆"}
    label = REACTION_LABELS.get(score_str, score_str)
    scores.setdefault("reactions", []).append({"msg_id": msg_id_str, "score": delta, "label": label, "timestamp": _dt.datetime.now().isoformat(), "chat_id": chat_id})
    stats = scores.setdefault("stats", {})
    stats["total_reactions"] = stats.get("total_reactions", 0) + 1
    if delta < 0:
        stats["dislikes"] = stats.get("dislikes", 0) + 1
    else:
        stats["likes"] = stats.get("likes", 0) + 1
    _save_ai_scores(scores)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception as _e:
        print(f"[Bot] 리액션 버튼 제거 실패 (무시): {_e}")
    level_up_msg = f"\n🆙 레벨업! Lv.{new_lv} [{new_name}]" if new_lv > old_lv else (f"\n😅 ...더 잘하겠습니다!" if delta < 0 else "")
    sign = "+" if delta >= 0 else ""
    await query.answer(f"{label} ({sign}{delta}점)\n현재: {new_score}점 / Lv.{new_lv} {new_name}{level_up_msg}", show_alert=(abs(delta) >= 0.5 or bool(level_up_msg)))

# ═══════════════════════════════════════════════════════════════════════════
# ▲ 공용 헬퍼 함수 블록 끝
# ═══════════════════════════════════════════════════════════════════════════

async def rate_proposal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /rate P0001 good  - 업그레이드 제안에 호평 (+1점)
    /rate P0001 bad   - 제안 거부 (점수 변동 없음, 상태만 업데이트)
    /rate P0001 done  - 제안 스킬 설치 완료 보고 (+2점)
    /rate             - 현재 AI 점수/레벨 조회
    """
    args = context.args if context.args else []
    scores = _load_ai_scores()

    if not args:
        lv = scores.get("level", 1)
        lv_name = scores.get("level_name", "신입 비서")
        total = scores.get("total_score", 0)
        stats = scores.get("stats", {})
        THRESHOLDS = [0, 10, 30, 60, 100, 999]
        next_t = next((t for t in THRESHOLDS if t > total), 999)
        prev_t = next(t for t in reversed(THRESHOLDS) if t <= total)
        bar_fill = int((total - prev_t) / max(next_t - prev_t, 1) * 10)
        bar = "█" * bar_fill + "░" * (10 - bar_fill)
        msg = (
            f"🤖 **알쫑이 AI 성장 현황**\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🏅 레벨: Lv.{lv} **{lv_name}**\n"
            f"⭐ 점수: {total}점  [{bar}]\n"
            f"  → 다음 레벨까지 {max(next_t-total, 0)}점 남음\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📊 제안 {stats.get('total_proposals',0)}건 | 호평 {stats.get('good_ratings',0)}건 | 설치 성공 {stats.get('installs',0)}건\n"
            f"\n💡 사용법:\n"
            f"  `/rate P0001 good` - 제안 호평 (+1점)\n"
            f"  `/rate P0001 done` - 설치 성공 보고 (+2점)\n"
            f"  `/rate P0001 bad`  - 제안 거부"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    if len(args) < 2:
        await update.message.reply_text("사용법: `/rate [제안ID] [good/bad/done]`\n예: `/rate P0001 good`", parse_mode='Markdown')
        return

    proposal_id = args[0].upper()
    action = args[1].lower()

    proposal = next((p for p in scores.get("proposals", []) if p.get("id") == proposal_id), None)
    if not proposal:
        await update.message.reply_text(f"❌ 제안 ID `{proposal_id}`를 찾을 수 없습니다.", parse_mode='Markdown')
        return

    points, msg = 0, ""
    if action == "good":
        proposal["status"] = "approved"
        scores["stats"]["good_ratings"] = scores["stats"].get("good_ratings", 0) + 1
        points, proposal["score_earned"] = 1, proposal.get("score_earned", 1) + 1
        msg = f"✅ 제안 `{proposal_id}` 호평 기록! **+1점** 획득"
    elif action == "done":
        proposal["status"] = "installed"
        scores["stats"]["installs"] = scores["stats"].get("installs", 0) + 1
        points, proposal["score_earned"] = 2, proposal.get("score_earned", 1) + 2
        msg = f"🎉 제안 `{proposal_id}` 설치 성공! **+2점** 획득"
    elif action == "bad":
        proposal["status"] = "rejected"
        msg = f"❌ 제안 `{proposal_id}` 거부 처리됨. (점수 변동 없음)"
    else:
        await update.message.reply_text("action은 `good`, `bad`, `done` 중 하나여야 합니다.", parse_mode='Markdown')
        return

    if points > 0:
        scores["total_score"] = scores.get("total_score", 0) + points
        old_lv = scores.get("level", 1)
        new_lv, new_name = _recalc_level(scores["total_score"])
        scores.update({"level": new_lv, "level_name": new_name})
        if new_lv > old_lv:
            msg += f"\n🆙 **레벨 업!! Lv.{new_lv} {new_name}** 로 승격!"

    _save_ai_scores(scores)
    await update.message.reply_text(
        f"{msg}\n현재 총점: {scores['total_score']}점 / Lv.{scores['level']} {scores['level_name']}",
        parse_mode='Markdown'
    )

async def tentacles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import json
    tentacles_dir = os.path.join(BASE_DIR, "tentacles")
    if not os.path.exists(tentacles_dir):
        await update.message.reply_text("❌ 문어발 폴더를 찾을 수 없습니다.")
        return
        
    tentacle_files = [f for f in os.listdir(tentacles_dir) if f.endswith('.py') and f not in ["__init__.py", "tentacle_daemon.py"]]
    
    if not tentacle_files:
        await update.message.reply_text("❌ 등록된 문어발 스크립트가 없습니다.")
        return
        
    config_file = os.path.join(tentacles_dir, "data", "tentacle_config.json")
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except: pass
        
    keyboard = []
    for tf in tentacle_files:
        is_on = config.get(tf, True)
        status_emoji = "🟢 ON" if is_on else "🔴 OFF"
        btn = InlineKeyboardButton(f"{tf} [{status_emoji}]", callback_data=f"toggle_tentacle:{tf}")
        keyboard.append([btn])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🐙 **문어발 스크립트 전원 스위치**\n\n아래 버튼을 눌러 백그라운드 데몬에서 문어발을 켜고 끄세요.", reply_markup=reply_markup, parse_mode='Markdown')

def is_dashboard_running():
    """시스템 내에서 dashboard_server.py 프로세스가 활성화되어 구동 중인지 탐색"""
    import psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info.get('cmdline') or []
            if any("dashboard_server.py" in arg for arg in cmd):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """텔레그램 마스터 계정 전용 대시보드 백그라운드 원격 제어 핸들러"""
    chat_id = str(update.effective_chat.id)
    
    # [마스터 보안 검사]
    if MASTER_CHAT_ID and chat_id != MASTER_CHAT_ID:
        await update.message.reply_text("🔒 **[보안 거부]** 이 명령은 마스터 계정만 제어할 수 있습니다.")
        return
        
    import sys
    import subprocess
    import asyncio
    
    args = context.args
    action = args[0].lower() if args else "status"
    
    if action == "on":
        pid = is_dashboard_running()
        if pid:
            await update.message.reply_text(
                f"🚀 **[Minos Dashboard]**\n"
                f"이미 웹 대시보드가 구동 중입니다! (PID: {pid})\n\n"
                f"🔗 **로컬 접속 주소:**\n"
                f"http://localhost:5000"
            )
        else:
            await update.message.reply_text("⏳ **[Minos Dashboard]** 백그라운드로 웹 서버를 부팅하는 중...")
            try:
                creationflags = 0
                if sys.platform == 'win32':
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                script_path = os.path.join(BASE_DIR, "dashboard_server.py")
                subprocess.Popen([sys.executable, script_path], creationflags=creationflags)
                
                # 부팅될 수 있도록 2.5초 대기 후 상태 재점검
                await asyncio.sleep(2.5)
                pid = is_dashboard_running()
                if pid:
                    await update.message.reply_text(
                        f"✅ **[Minos Dashboard] 부팅 완수!**\n"
                        f"• PID: {pid}\n"
                        f"• 포트: 5000\n\n"
                        f"🔗 **로컬 웹 접속:**\n"
                        f"http://localhost:5000"
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ 대시보드 실행 명령을 발행했으나 프로세스가 감지되지 않았습니다.\n"
                        "포트 충돌이나 기타 실행 오류가 있을 수 있으니 수동 구동을 권장합니다."
                    )
            except Exception as e:
                await update.message.reply_text(f"❌ 대시보드 구동 실패: {str(e)}")
                
    elif action == "off":
        pid = is_dashboard_running()
        if not pid:
            await update.message.reply_text("🔇 현재 활성화된 웹 대시보드 프로세스가 없습니다.")
        else:
            try:
                import psutil
                proc = psutil.Process(pid)
                proc.terminate()
                await asyncio.sleep(1.0)
                await update.message.reply_text("🛑 **[Minos Dashboard]** 웹 서버 프로세스를 강제 종료(Shutdown) 처리했습니다.")
            except Exception as e:
                await update.message.reply_text(f"❌ 대시보드 프로세스 정지 실패: {str(e)}")
                
    else:
        pid = is_dashboard_running()
        status_text = f"🟢 **구동 중 (Running)**\n• PID: {pid}\n🔗 주소: http://localhost:5000" if pid else "🔴 **정지됨 (Stopped)**"
        
        await update.message.reply_text(
            f"📊 **[Minos Dashboard 관제 상태]**\n\n"
            f"• 서버 상태: {status_text}\n\n"
            f"💡 **원격 전원 스위치 제어 방법:**\n"
            f"• `/dashboard on` : 백그라운드 웹 대시보드 부팅\n"
            f"• `/dashboard off` : 구동 중인 대시보드 전원 종료\n"
            f"• `/dashboard` : 현재 구동 상태 실시간 점검"
        )

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """텔레그램 마스터 계정 전용 에이전트 시스템 전체 클린 재부팅 핸들러"""
    chat_id = str(update.effective_chat.id)
    
    # [마스터 보안 검사]
    if MASTER_CHAT_ID and chat_id != MASTER_CHAT_ID:
        await update.message.reply_text("🔒 **[보안 거부]** 이 명령은 마스터 계정만 실행할 수 있습니다.")
        return
        
    await update.message.reply_text(
        "⏳ **[Minos System Reboot]**\n"
        "형님, 시스템 클린 재부팅 명령을 감지했습니다.\n"
        "즉시 모든 좀비 프로세스를 소거하고 백그라운드 부팅 시퀀스(Start-Minos.bat)를 재기동합니다.\n\n"
        "약 5~10초 후 재연동 완료 시 알쫑이가 다시 활성화됩니다. 잠시만 기다려 주십시오!"
    )
    
    # 텔레그램 서버로 위 메시지가 안정적으로 송출될 수 있도록 1.5초간 대기합니다.
    await asyncio.sleep(1.5)
    
    import sys
    import subprocess
    import os
    
    try:
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
            
        bat_path = os.path.join(BASE_DIR, "Start-Minos.bat")
        # --silent 인자를 주어 대화식 선택창을 스킵하게 합니다.
        subprocess.Popen([bat_path, "--silent"], shell=True, creationflags=creationflags)
        sys.exit(0)
    except Exception as e:
        await update.message.reply_text(f"❌ 재부팅 배치 파일 기동 실패: {str(e)}")

async def skill_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """콜백 디스패처: 버튼 타입별로 전용 헬퍼(_cb_*)에 위임합니다."""
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = str(query.message.chat.id)
    
    # [보안 검사] 외부인 시스템 설정 및 승인 조작 일괄 방어
    if MASTER_CHAT_ID and chat_id != MASTER_CHAT_ID:
        await query.answer("보안 경고: 모든 에이전트 설정/승인 조작은 형님(마스터)에게만 제한되어 있습니다! ❌", show_alert=True)
        return

    state = get_user_state(chat_id)

    if data.startswith("switch_engine:"):
        await _cb_switch_engine(query, data)

    elif data.startswith("toggle_skill:"):
        skill_file = data.split(":", 1)[1]
        state.setdefault('auto_skills', set())
        if skill_file in state['auto_skills']:
            state['auto_skills'].remove(skill_file)
        else:
            state['auto_skills'].add(skill_file)
        save_user_settings()
        skills_dir = os.path.join(BASE_DIR, "skill_system", "skills")
        skill_files = [f for f in os.listdir(skills_dir) if f.endswith('.py') and f != "__init__.py"]
        keyboard = [[InlineKeyboardButton(
            f"{sf} [{'🟢 AUTO' if sf in state['auto_skills'] else '🔴 MANUAL'}]",
            callback_data=f"toggle_skill:{sf}"
        )] for sf in skill_files]
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
        except telegram.error.BadRequest:
            pass

    elif data.startswith("toggle_tentacle:"):
        tentacle_file = data.split(":", 1)[1]
        tentacles_dir = os.path.join(BASE_DIR, "tentacles")
        config_file = os.path.join(tentacles_dir, "data", "tentacle_config.json")
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as _e:
                print(f"[Bot] tentacle_config 로드 실패: {_e}")
        config[tentacle_file] = not config.get(tentacle_file, True)
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        tentacle_files = [f for f in os.listdir(tentacles_dir) if f.endswith('.py') and f not in ["__init__.py", "tentacle_daemon.py"]]
        keyboard = [[InlineKeyboardButton(
            f"{tf} [{'🟢 ON' if config.get(tf, True) else '🔴 OFF'}]",
            callback_data=f"toggle_tentacle:{tf}"
        )] for tf in tentacle_files]
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
        except telegram.error.BadRequest:
            pass

    elif data.startswith("rate_"):
        await _cb_rate_proposal(query, data, chat_id)

    elif data.startswith("react_"):
        await _cb_react(query, data, chat_id)

    elif data == "btn_yes":
        cmd = state.get('pending_command')
        if not cmd:
            await query.message.reply_text("대기 중인 명령어가 없습니다.")
            return
        state['pending_command'] = None
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as _e:
            print(f"[Bot] btn_yes 버튼 제거 실패: {_e}")
        await execute_command_and_continue(cmd, update, context, chat_id)

    elif data == "btn_no":
        if not state.get('pending_command'):
            await query.message.reply_text("대기 중인 명령어가 없습니다.")
            return
        state['pending_command'] = None
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as _e:
            print(f"[Bot] btn_no 버튼 제거 실패: {_e}")
        await query.message.reply_text("❌ 명령어 실행을 취소했습니다. 봇에게 취소 사실을 전달합니다.")
        memory.add_message(chat_id=chat_id, role="user", content="[시스템 알림]: 사용자가 해당 명령어 실행을 거부/취소했습니다. 다른 방법으로 해결하거나 답변을 마무리하세요.")
        await stream_llm_response(update, context, chat_id)

async def yes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if MASTER_CHAT_ID and chat_id != MASTER_CHAT_ID:
        await update.message.reply_text("❌ 이 제어 명령은 형님(마스터)만 사용 가능합니다.")
        return
        
    state = get_user_state(chat_id)
    cmd = state['pending_command']
    
    if not cmd:
        await update.message.reply_text("대기 중인 명령어가 없습니다.")
        return
        
    state['pending_command'] = None
    await execute_command_and_continue(cmd, update, context, chat_id)

async def no_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if MASTER_CHAT_ID and chat_id != MASTER_CHAT_ID:
        await update.message.reply_text("❌ 이 제어 명령은 형님(마스터)만 사용 가능합니다.")
        return
        
    state = get_user_state(chat_id)
    
    if not state['pending_command']:
        await update.message.reply_text("대기 중인 명령어가 없습니다.")
        return
        
    state['pending_command'] = None
    await update.message.reply_text("❌ 명령어 실행을 취소했습니다. 봇에게 취소 사실을 전달합니다.")
    
    # 기억에 주입하고 다시 답변 요청
    memory.add_message(chat_id=chat_id, role="user", content="[시스템 알림]: 사용자가 해당 명령어 실행을 거부/취소했습니다. 다른 방법으로 해결하거나 답변을 마무리하세요.")
    await stream_llm_response(update, context, chat_id)

async def execute_command_and_continue(cmd: str, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: str, application=None):
    """실제 터미널 명령어를 백그라운드 비동기로 실행하고 결과를 봇의 뇌에 주입한 뒤 다시 스트리밍을 호출합니다."""
    # [보안 검사] 형님(마스터) 외의 사용자는 명령어 실행 즉시 거부
    if MASTER_CHAT_ID and chat_id != MASTER_CHAT_ID:
        bot = context.bot if context else application.bot
        await bot.send_message(
            chat_id=chat_id, 
            text="⚠️ **[보안 경보]** 외부인 비정상 명령어 실행 감지!\n형님(마스터) 외의 사용자는 터미널 명령어를 실행할 권한이 없습니다. ❌"
        )
        return

    bot = context.bot if context else application.bot
    status_msg = await bot.send_message(chat_id=chat_id, text=f"⚡ 윈도우 터미널 명령어 (비동기) 실행 중...\n`{cmd}`", parse_mode='Markdown')
    
    async def _run_async_task():
        try:
            # 비동기 서브프로세스 생성 (UTF-8 강제 주입으로 이모지 출력 시 CP949 에러 방어)
            custom_env = os.environ.copy()
            custom_env["PYTHONIOENCODING"] = "utf-8"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=custom_env
            )
            # 타임아웃 30초 적용
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
            
            out_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            err_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            output = out_str + "\n" + err_str
            if not output.strip():
                output = "(명령어가 성공적으로 실행되었으나 출력된 내용이 없습니다.)"
        except asyncio.TimeoutError:
            try:
                process.kill()
            except: pass
            output = "[오류]: 명령어 실행 시간이 30초를 초과하여 강제 종료되었습니다."
        except Exception as e:
            output = f"[오류]: 명령어 실행 중 예외 발생: {str(e)}"
            
        if len(output) > 2000:
            output = output[:2000] + "\n... (출력이 너무 길어 생략됨)"
            
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"✅ 백그라운드 작업 완료. 봇이 결과를 분석합니다..."
        )
        
        memory.add_message(chat_id=chat_id, role="user", content=f"[터미널 명령어 실행 결과]\n명령어: {cmd}\n결과:\n{output}\n\n위 결과를 바탕으로 분석하거나 사용자에게 답변을 이어나가세요.")
        
        await stream_llm_response(update, context, chat_id, application=application)

    # 봇의 메인 이벤트를 블로킹하지 않고 백그라운드 태스크로 던짐
    asyncio.create_task(_run_async_task())

async def stream_llm_response(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: str, current_query: str = "", application=None):
    """Ollama API와 통신하여 텍스트를 실시간으로 받아오고 텔레그램에 출력하는 핵심 로직"""
    bot = context.bot if context else application.bot
    status_message = await bot.send_message(chat_id=chat_id, text='생각 중... 💭')
    
    import psutil
    
    # 시스템 프롬프트에 현재 스킬 목록 주입
    skills_index_text = skills.get_skills_index_text()
    
    self_awareness_prompt = _build_self_awareness_prompt(chat_id)
    dynamic_system_prompt = SYSTEM_PROMPT + f"\n\n[장착한 스킬 목록]\n{skills_index_text}" + self_awareness_prompt
    
    state = get_user_state(chat_id)
    memory_mode = state.get('memory_mode', 'embedding')
    
    optimized_messages = memory.get_optimized_context(
        chat_id=chat_id, 
        base_system_prompt=dynamic_system_prompt,
        current_query=current_query,
        memory_mode=memory_mode
    )
    payload = {
        'model': MODEL_NAME,
        'messages': optimized_messages,
        'temperature': 0.7,
        'max_tokens': MAX_TOKENS,
        'stream': True,
        'num_ctx': 16384,
        'options': {
            'num_ctx': 16384
        }
    }
    
    reply_text = ""
    last_update_time = time.time()
    update_interval = 1.5 
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
        
    try:
        response = requests.post(LLAMA_URL, headers=headers, json=payload, stream=True)
        if response.status_code != 200:
            err_text = response.text
            print(f"[LLM Error] Status: {response.status_code}, Msg: {err_text}")
            raise requests.exceptions.HTTPError(f"{response.status_code} Client Error: {err_text}")
        response.raise_for_status()
        
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
                                
                                current_time = time.time()
                                if current_time - last_update_time > update_interval:
                                    try:
                                        # CMD 블록 제거 후 표시 (실제 내부 로직은 reply_text 원본으로 유지)
                                        display_text = strip_cmd_for_display(reply_text)
                                        if display_text:
                                            await bot.edit_message_text(
                                                chat_id=chat_id,
                                                message_id=status_message.message_id,
                                                text=display_text + " ✍️"
                                            )
                                        last_update_time = current_time
                                    except telegram.error.BadRequest:
                                        pass
                    except json.JSONDecodeError:
                        continue

        # 스트리밍 종료 후 최종 텍스트 업데이트
        if reply_text.strip():
            try:
                # CMD 블록 제거 후 최종 표시
                final_display = strip_cmd_for_display(reply_text)
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message.message_id,
                    text=final_display if final_display else "⏳ 스킬 실행 중..."
                )
            except telegram.error.BadRequest:
                pass
            
            # 봇의 최종 답변 저장
            memory.add_message(chat_id=chat_id, role="assistant", content=reply_text)

            # 포스트 응답 처리 (TTS, 스킬 저장, 커맨드 태그, 리액션 팝업 등)
            await _handle_post_response(bot, chat_id, reply_text, status_message, update, context, state, application=application)
        else:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_message.message_id,
                text="❌ 응답을 생성하지 못했습니다."
            )
            
    except requests.exceptions.ConnectionError:
        await bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=f'❌ 안내: 로컬 LLM 서버({ENGINE_DISPLAY_NAME})에 연결할 수 없습니다. 엔진 구동 상태를 확인하세요.')
    except Exception as e:
        await bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=f'❌ 통신 오류: {str(e)}')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = str(update.effective_chat.id)
        user_text = update.message.text
        
        # 사용자의 말을 기억에 추가
        memory.add_message(chat_id=chat_id, role="user", content=user_text)
        
        # 스트리밍 텍스트 생성
        await stream_llm_response(update, context, chat_id, current_query=user_text)
    except Exception as e:
        print(f"\n[오류] 텔레그램 메시지 처리 중 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            await update.message.reply_text(f"❌ 내부 시스템 오류가 발생했습니다: {str(e)}")
        except: pass

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = str(update.effective_chat.id)
        
        # 음성 수신 허용 여부 체크
        current_config = get_bot_config()
        if not current_config.get("tg_voice_enabled", True):
            await update.message.reply_text("❌ 현재 음성 수신 기능이 꺼져 있습니다. 대시보드에서 켜주세요.")
            return
            
        status_message = await update.message.reply_text("🎧 음성 메시지를 텍스트로 변환하는 중입니다...")
        
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        import tempfile
        import stt_engine
        
        # 텔레그램 음성 파일(ogg) 다운로드
        fd, temp_ogg = tempfile.mkstemp(suffix=".ogg")
        os.close(fd)
        await file.download_to_drive(temp_ogg)
        
        # STT 변환
        engine_type = current_config.get("stt_engine", "google")
        text = stt_engine.process_audio(temp_ogg, engine=engine_type)
        
        if os.path.exists(temp_ogg):
            try: os.remove(temp_ogg)
            except: pass
            
        if not text or text.startswith("[STT 오류"):
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=f"❌ 음성 인식 실패: {text}")
            return
            
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=f"🎙️ **[음성 인식 결과]**\n{text}", parse_mode='Markdown')
        
        # 텍스트로 변환된 내용을 봇 메모리에 추가하고 답변 생성
        memory.add_message(chat_id=chat_id, role="user", content=text)
        await stream_llm_response(update, context, chat_id, current_query=text)
        
    except Exception as e:
        print(f"\n[오류] 텔레그램 음성 메시지 처리 중 예외 발생: {str(e)}")
        try:
            await update.message.reply_text(f"❌ 음성 처리 중 오류가 발생했습니다: {str(e)}")
        except: pass

async def schedule_checker(application):
    import asyncio
    from datetime import datetime
    while True:
        try:
            schedules_path = os.path.join(BASE_DIR, "schedules.json")
            if os.path.exists(schedules_path):
                with open(schedules_path, 'r', encoding='utf-8') as f:
                    schedules = json.load(f)
                
                now = datetime.now()
                remaining = []
                triggered = False
                for s in schedules:
                    try:
                        s_time = datetime.strptime(s['time'], "%Y-%m-%d %H:%M")
                        if now >= s_time:
                            chat_id = MASTER_CHAT_ID if MASTER_CHAT_ID else (list(user_states.keys())[-1] if user_states else None)
                            if chat_id:
                                msg = s['message']
                                await application.bot.send_message(chat_id=chat_id, text=f"🔔 **[스케줄 매니저] 예약 알림**\n{msg}", parse_mode='Markdown')
                                memory.add_message(chat_id=chat_id, role="user", content=f"[시스템 알람]: 예약된 시간({s['time']})이 되었습니다. 사용자에게 예약된 알림 메시지 내용('{msg}')을 기반으로 적절한 액션(명령어 실행 또는 브리핑)을 즉시 진행하세요.")
                                await stream_llm_response(None, None, chat_id, application=application)
                            triggered = True
                        else:
                            remaining.append(s)
                    except:
                        remaining.append(s)
                
                if triggered:
                    with open(schedules_path, 'w', encoding='utf-8') as f:
                        json.dump(remaining, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Schedule checking error: {e}")
            
        await asyncio.sleep(60)

async def tentacle_error_checker(application):
    import asyncio
    import json
    import os
    
    error_file_path = os.path.join(BASE_DIR, "tentacles", "logs", "tentacle_errors.json")
    # 이미 보고한 에러 시간을 추적하여 무한 반복 방지
    reported_errors = {}
    
    while True:
        try:
            if os.path.exists(error_file_path):
                with open(error_file_path, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
                    
                for filename, err_info in errors.items():
                    err_time = err_info.get("timestamp")
                    err_log = err_info.get("error_log", "")
                    
                    if reported_errors.get(filename) != err_time:
                        reported_errors[filename] = err_time
                        
                        chat_id = MASTER_CHAT_ID if MASTER_CHAT_ID else (list(user_states.keys())[-1] if user_states else None)
                        if chat_id:
                            alert_msg = f"🚨 **[문어발 자가 치유 시스템 발동]**\n\n문어발 스크립트 `{filename}` 에서 에러가 감지되었습니다. 알쫑이가 디버깅을 시작합니다!\n\n에러 내용:\n`{err_log[:500]}...`"
                            await application.bot.send_message(chat_id=chat_id, text=alert_msg, parse_mode='Markdown')
                            
                            ai_prompt = f"[긴급 시스템 명령 - 자가 치유(Self-Healing) 발동]\n백그라운드에서 동작하는 당신의 보조 스크립트(문어발) '{filename}'에서 다음 에러가 발생했습니다:\n\n{err_log}\n\n당장 <CMD>python C:\\ai\\Antigravity_Memory_Engine\\skill_system\\skills\\tentacle_manager.py read \"{filename}\"</CMD> 를 실행하여 코드를 읽어오고, 원인을 분석한 뒤 수정한 코드를 다시 배포(write)하여 문제를 해결하십시오."
                            memory.add_message(chat_id=chat_id, role="user", content=ai_prompt)
                            await stream_llm_response(None, None, chat_id, application=application)
                            
        except Exception as e:
            print(f"Tentacle error watchdog error: {e}")
            
        await asyncio.sleep(60)

async def _send_upgrade_proposals(application, chat_id: str, sig_message: str):
    """자율 업그레이드 제안 신호(self_upgrade_tentacle.py) 처리용 헬퍼"""
    ai_score_file = os.path.join(BASE_DIR, "tentacles", "data", "ai_scores.json")
    try:
        with open(ai_score_file, 'r', encoding='utf-8') as sf:
            score_data = json.load(sf)
        
        pending = [p for p in score_data.get("proposals", []) if p.get("status") == "pending"]
        lv = score_data.get("level", 1)
        lv_name = score_data.get("level_name", "신입 비서")
        total = score_data.get("total_score", 0)

        header = (
            f"🤖 **[알쫑이 자가 업그레이드 보고서]**\n"
            f"🏅 현재 레벨: Lv.{lv} {lv_name} | ⭐ {total}점\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"형님, 저 알쫑이가 스스로 분석하여 업그레이드 제안을 가져왔습니다!\n"
            f"아래 제안들을 검토해 주시고 버튼으로 평가해 주세요. 😊"
        )
        await application.bot.send_message(chat_id=chat_id, text=header, parse_mode='Markdown')

        for proposal in pending:
            pid = proposal.get("id", "P????")
            card_text = (
                f"📌 **[{pid}] {proposal.get('title', '')}**\n"
                f"🏷️ 분류: {proposal.get('category', '')} | 난이도: {proposal.get('difficulty', '')}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"💡 **제안 이유:**\n{proposal.get('reason', '')}\n\n"
                f"🔧 **구현 방법:**\n{proposal.get('impl', '')}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"형님, 이 제안 어떻게 생각하세요?"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"👍 호평 (+1점)",  callback_data=f"rate_{pid}_good"),
                    InlineKeyboardButton(f"❌ 거부",         callback_data=f"rate_{pid}_bad"),
                ],
                [
                    InlineKeyboardButton(f"🎉 설치 완료 (+2점)", callback_data=f"rate_{pid}_done"),
                ]
            ])
            await application.bot.send_message(
                chat_id=chat_id, text=card_text, parse_mode='Markdown', reply_markup=keyboard
            )
    except Exception as e:
        await application.bot.send_message(
            chat_id=chat_id,
            text=f"🤖 **[자가 업그레이드 보고서]**\n\n{sig_message[:2000]}",
            parse_mode='Markdown'
        )
        print(f"[self_upgrade 신호 처리 오류] {e}")


async def tentacle_signal_checker(application):
    import asyncio
    
    signal_file_path = os.path.join(BASE_DIR, "tentacles", "logs", "tentacle_signals.json")
    reported_signals = {}
    
    while True:
        try:
            if os.path.exists(signal_file_path):
                with open(signal_file_path, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
                
                chat_id = MASTER_CHAT_ID if MASTER_CHAT_ID else (list(user_states.keys())[-1] if user_states else None)
                if not chat_id:
                    await asyncio.sleep(60)
                    continue

                # ── Alert Summarizer: 이번 사이클에서 새로 감지된 신호 수집 ──
                upgrade_signals = []
                new_signals = {}

                for filename, sig_info in signals.items():
                    sig_time = sig_info.get("timestamp")
                    sig_message = sig_info.get("message", "")
                    
                    if reported_signals.get(filename) != sig_time:
                        reported_signals[filename] = sig_time
                        
                        if filename == "self_upgrade_tentacle.py":
                            upgrade_signals.append((filename, sig_message))
                        else:
                            new_signals[filename] = sig_message

                # 업그레이드 제안은 기존대로 개별 처리
                for filename, sig_message in upgrade_signals:
                    await _send_upgrade_proposals(application, chat_id, sig_message)

                # 새 신호가 1개이면 기존 방식으로, 2개 이상이면 병합하여 단일 브리핑
                if len(new_signals) == 1:
                    filename, sig_message = list(new_signals.items())[0]
                    ai_prompt = (
                        f"[긴급 시스템 명령 - 자율신경계(문어발) 신호 수신]\n"
                        f"백그라운드 보조 스크립트(문어발) '{filename}'에서 "
                        f"다음 정보를 보고했습니다:\n\n{sig_message}\n\n"
                        f"사용자에게 이 정보를 기반으로 친절하고 간결한 브리핑을 즉시 작성하여 보내십시오."
                    )
                    memory.add_message(chat_id=chat_id, role="user", content=ai_prompt)
                    await stream_llm_response(None, None, chat_id, application=application)

                elif len(new_signals) >= 2:
                    # ── 2개 이상 신호를 하나로 묶어 단일 메시지 생성 ──
                    combined_parts = []
                    for fname, msg in new_signals.items():
                        label = fname.replace("_tentacle.py", "").replace("_", " ").title()
                        combined_parts.append(f"[{label}]\n{msg}")
                    combined_body = "\n\n---\n\n".join(combined_parts)
                    
                    ai_prompt = (
                        f"[긴급 시스템 명령 - 다중 문어발 신호 통합 브리핑 요청]\n"
                        f"총 {len(new_signals)}개의 보조 스크립트가 동시에 보고를 완료했습니다.\n"
                        f"아래 각 항목을 하나의 깔끔한 통합 메시지로 정리하여 사용자에게 전달하십시오. "
                        f"중복 인사는 한 번만, 각 항목은 이모지와 함께 간결하게:\n\n"
                        f"{combined_body}"
                    )
                    memory.add_message(chat_id=chat_id, role="user", content=ai_prompt)
                    await stream_llm_response(None, None, chat_id, application=application)
                        
        except Exception as e:
            print(f"Tentacle signal watchdog error: {e}")
            
        await asyncio.sleep(60)


async def post_init(application: Application):
    import asyncio
    asyncio.create_task(schedule_checker(application))
    asyncio.create_task(tentacle_error_checker(application))
    asyncio.create_task(tentacle_signal_checker(application))

def main():
    print('========== 로컬 Minos 에이전트 (명령어 실행 탑재) ==========')
    
    if not TELEGRAM_TOKEN:
        print('❌ [오류] 텔레그램 봇 토큰이 설정되지 않았습니다.')
        print('👉 웹 대시보드(http://localhost:5000)에 접속하여 Settings 패널에서 토큰을 먼저 입력해 주세요.')
        return
        
    print('Telegram Token    :', TELEGRAM_TOKEN[:10] + '...')
    
    # 텔레그램 서버 통신 타임아웃을 넉넉하게 30초로 설정하여 ConnectTimeout 방지
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .connect_timeout(60.0)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .pool_timeout(60.0)
        .post_init(post_init)
        .build()
    )
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('model', model_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('backup', backup_command))
    application.add_handler(CommandHandler('clear', clear_memory))
    
    # 에이전트용 특수 핸들러
    application.add_handler(CommandHandler('auto', auto_toggle))
    application.add_handler(CommandHandler('yes', yes_command))
    application.add_handler(CommandHandler('no', no_command))
    application.add_handler(CommandHandler('memorymode', memorymode_command))
    application.add_handler(CommandHandler('voice', voice_command))
    application.add_handler(CommandHandler('skills', skills_command))
    application.add_handler(CommandHandler('tentacles', tentacles_command))
    application.add_handler(CommandHandler('rate', rate_proposal_command))
    application.add_handler(CommandHandler('dashboard', dashboard_command))
    application.add_handler(CommandHandler('restart', restart_command))
    application.add_handler(CallbackQueryHandler(skill_callback_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print('준비 완료! (에이전트 루프 및 기억 엔진 가동 중...)')
    try:
        # 타임아웃 방지를 위해 run_polling에도 명시적 설정 추가 (read_timeout 제외)
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"\n[치명적 오류] 텔레그램 서버 통신 중 오류가 발생하여 종료됩니다: {e}")

if __name__ == '__main__':
    main()
