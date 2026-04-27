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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
from memory_engine import MemoryEngine

sys.path.append(os.path.join(BASE_DIR, 'skill_system'))
from skill_registry import SkillRegistry

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
LLAMA_URL = 'http://127.0.0.1:11434/api/chat'

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
        except:
            pass
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
    except:
        pass

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
    '[에이전트 권한 부여]: 당신은 사용자의 윈도우 PC(CMD/PowerShell)를 직접 제어할 수 있는 손(Tool)을 가지고 있습니다. '
    '무언가 확인이 필요하거나, 스크립트를 실행하거나, 파일 시스템을 탐색해야 할 때 터미널 명령어를 실행할 수 있습니다. '
    '명령어를 실행하고 싶다면 반드시 답변 어딘가에 아래와 같이 정확한 태그로 명령어를 출력하세요:\n'
    '<CMD>dir C:\\</CMD>\n'
    '당신이 위 태그를 출력하면 즉시 시스템이 멈추고 실제 PC에서 명령어를 실행한 뒤, 그 결과를 당신에게 다시 입력해 줄 것입니다. '
    '그러면 당신은 그 결과를 읽고 최종적인 판단이나 답변을 이어나가면 됩니다. (한 번에 하나의 <CMD>만 사용하세요.)\n\n'
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
        "/backup - 현재까지의 모든 기억을 하드디스크 백업 폴더로 복사합니다.\n"
        "/clear - 단기 기억(문맥)을 포맷하여 새로운 대화를 시작합니다.\n"
        "/auto - 봇의 PC 명령어 전역 자동 실행 모드를 켜거나 끕니다. (위험/전체허용)\n"
        "/skills - [NEW] 개별 스킬별로 자동(Auto)/수동(Manual) 권한을 세밀하게 제어할 수 있는 버튼 대시보드를 엽니다.\n"
        "/memorymode - 기억 검색 엔진(키워드/임베딩)을 변경합니다."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import psutil
    chat_id = str(update.effective_chat.id)
    mem_data = memory.load_memory(chat_id)
    state = get_user_state(chat_id)
    working_count = len(mem_data.get("working_memory", [])) // 2 
    max_count = memory.max_working_memory // 2
    
    # 모델 및 컨텍스트 사이즈 추산
    current_model = "gemma4-e4b:q4km (로컬 Ollama)"
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

async def skill_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = str(query.message.chat.id)
    state = get_user_state(chat_id)
    
    if data.startswith("toggle_skill:"):
        skill_file = data.split(":", 1)[1]
        
        if 'auto_skills' not in state:
            state['auto_skills'] = set()
            
        if skill_file in state['auto_skills']:
            state['auto_skills'].remove(skill_file)
        else:
            state['auto_skills'].add(skill_file)
            
        save_user_settings()
            
        skills_dir = os.path.join(BASE_DIR, "skill_system", "skills")
        skill_files = [f for f in os.listdir(skills_dir) if f.endswith('.py') and f != "__init__.py"]
        
        keyboard = []
        for sf in skill_files:
            is_auto = sf in state['auto_skills']
            status_emoji = "🟢 AUTO" if is_auto else "🔴 MANUAL"
            btn = InlineKeyboardButton(f"{sf} [{status_emoji}]", callback_data=f"toggle_skill:{sf}")
            keyboard.append([btn])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.edit_message_reply_markup(reply_markup=reply_markup)
        except telegram.error.BadRequest:
            pass
            
    elif data.startswith("toggle_tentacle:"):
        import json
        tentacle_file = data.split(":", 1)[1]
        
        tentacles_dir = os.path.join(BASE_DIR, "tentacles")
        config_file = os.path.join(tentacles_dir, "data", "tentacle_config.json")
        
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except: pass
            
        # 토글
        current_state = config.get(tentacle_file, True)
        config[tentacle_file] = not current_state
        
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        tentacle_files = [f for f in os.listdir(tentacles_dir) if f.endswith('.py') and f not in ["__init__.py", "tentacle_daemon.py"]]
        
        keyboard = []
        for tf in tentacle_files:
            is_on = config.get(tf, True)
            status_emoji = "🟢 ON" if is_on else "🔴 OFF"
            btn = InlineKeyboardButton(f"{tf} [{status_emoji}]", callback_data=f"toggle_tentacle:{tf}")
            keyboard.append([btn])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.edit_message_reply_markup(reply_markup=reply_markup)
        except telegram.error.BadRequest:
            pass
            
    elif data == "btn_yes":
        cmd = state.get('pending_command')
        if not cmd:
            await query.message.reply_text("대기 중인 명령어가 없습니다.")
            return
        state['pending_command'] = None
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except: pass
        await execute_command_and_continue(cmd, update, context, chat_id)
        
    elif data == "btn_no":
        if not state.get('pending_command'):
            await query.message.reply_text("대기 중인 명령어가 없습니다.")
            return
        state['pending_command'] = None
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except: pass
        await query.message.reply_text("❌ 명령어 실행을 취소했습니다. 봇에게 취소 사실을 전달합니다.")
        memory.add_message(chat_id=chat_id, role="user", content="[시스템 알림]: 사용자가 해당 명령어 실행을 거부/취소했습니다. 다른 방법으로 해결하거나 답변을 마무리하세요.")
        await stream_llm_response(update, context, chat_id)

async def yes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    state = get_user_state(chat_id)
    cmd = state['pending_command']
    
    if not cmd:
        await update.message.reply_text("대기 중인 명령어가 없습니다.")
        return
        
    state['pending_command'] = None
    await execute_command_and_continue(cmd, update, context, chat_id)

async def no_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
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
    """실제 터미널 명령어를 실행하고 결과를 봇의 뇌에 주입한 뒤 다시 스트리밍을 호출합니다."""
    bot = context.bot if context else application.bot
    status_msg = await bot.send_message(chat_id=chat_id, text=f"⚡ 윈도우에서 터미널 명령어 실행 중...\n`{cmd}`", parse_mode='Markdown')
    
    try:
        # 명령어 윈도우 실행 (timeout 30초 설정)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if not output.strip():
            output = "(명령어가 성공적으로 실행되었으나 출력된 내용이 없습니다.)"
    except subprocess.TimeoutExpired:
        output = "[오류]: 명령어 실행 시간이 30초를 초과하여 강제 종료되었습니다."
    except Exception as e:
        output = f"[오류]: 명령어 실행 중 예외 발생: {str(e)}"
        
    # 너무 긴 출력은 자르기 (Ollama 컨텍스트 오버플로우 방지)
    if len(output) > 2000:
        output = output[:2000] + "\n... (출력이 너무 길어 생략됨)"
        
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=status_msg.message_id,
        text=f"✅ 실행 완료. 봇이 결과를 분석합니다..."
    )
    
    # 실행 결과를 user 롤로 기억에 주입
    memory.add_message(chat_id=chat_id, role="user", content=f"[터미널 명령어 실행 결과]\n명령어: {cmd}\n결과:\n{output}\n\n위 결과를 바탕으로 분석하거나 사용자에게 답변을 이어나가세요.")
    
    # 봇에게 다시 생각하도록 스트리밍 호출
    await stream_llm_response(update, context, chat_id, application=application)

async def stream_llm_response(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: str, current_query: str = "", application=None):
    """Ollama API와 통신하여 텍스트를 실시간으로 받아오고 텔레그램에 출력하는 핵심 로직"""
    bot = context.bot if context else application.bot
    status_message = await bot.send_message(chat_id=chat_id, text='생각 중... 💭')
    
    import psutil
    
    # 시스템 프롬프트에 현재 스킬 목록 주입
    skills_index_text = skills.get_skills_index_text()
    
    # [자아 인식(Self-Awareness) 상태값 동적 생성]
    mem_data = memory.load_memory(chat_id)
    working_count = len(mem_data.get("working_memory", [])) // 2 
    max_count = memory.max_working_memory // 2
    cpu_percent = psutil.cpu_percent()
    ram_percent = psutil.virtual_memory().percent
    
    self_awareness_prompt = (
        f"\n\n[당신의 현재 상태 (Self-Awareness)]\n"
        f"- 단기 기억 포화도: {working_count} / {max_count} (최대치 도달 시 오래된 기억부터 강제 유실됨)\n"
        f"- 구동 환경 부하: CPU {cpu_percent}%, RAM {ram_percent}%\n"
        f"* 지시사항: 당신은 매 턴마다 자신의 위 상태를 인지해야 합니다. 만약 단기 기억이 꽉 차가거나 시스템 부하가 높다면, 대답 시 먼저 사용자(형님)에게 '기억이 한계에 달해 정리가 필요하다(/clear)'고 능동적으로 건의하거나 요약 모드로 전환하십시오."
    )
    
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
        'model': 'gemma4-e4b:q4km',
        'messages': optimized_messages,
        'temperature': 0.7,
        'max_tokens': 4096,
        'stream': True
    }
    
    reply_text = ""
    last_update_time = time.time()
    update_interval = 1.5 
    
    try:
        response = requests.post(LLAMA_URL, json=payload, stream=True, timeout=300)
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
                                        await bot.edit_message_text(
                                            chat_id=chat_id,
                                            message_id=status_message.message_id,
                                            text=reply_text + " ✍️"
                                        )
                                        last_update_time = current_time
                                    except telegram.error.BadRequest:
                                        pass
                    except json.JSONDecodeError:
                        continue

        # 스트리밍 종료 후 최종 텍스트 업데이트
        if reply_text.strip():
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message.message_id,
                    text=reply_text
                )
            except telegram.error.BadRequest:
                pass
            
            # 봇의 최종 답변 저장
            memory.add_message(chat_id=chat_id, role="assistant", content=reply_text)
            
            # --- [스킬 학습 처리부: <SAVE_SKILL> 태그 감지] ---
            skill_match = re.search(r'<SAVE_SKILL name="(.*?)" desc="(.*?)">(.*?)</SAVE_SKILL>', reply_text, re.IGNORECASE | re.DOTALL)
            if skill_match:
                skill_name = skill_match.group(1).strip()
                skill_desc = skill_match.group(2).strip()
                skill_code = skill_match.group(3).strip()
                
                # 스킬 저장 및 인덱스 업데이트
                sys_msg = skills.save_skill(skill_name, skill_desc, skill_code)
                await bot.send_message(chat_id=chat_id, text=f"✨ **새로운 스킬을 습득했습니다!**\n- 이름: {skill_name}\n- 기능: {skill_desc}", parse_mode='Markdown')
                
                # 봇의 기억에 성공 메시지 주입
                memory.add_message(chat_id=chat_id, role="user", content=sys_msg)
            
            # --- [에이전트 권한 처리부: <CMD> 태그 감지] ---
            cmd_match = re.search(r'<CMD>(.*?)</CMD>', reply_text, re.IGNORECASE | re.DOTALL)
            if cmd_match:
                extracted_cmd = cmd_match.group(1).strip()
                state = get_user_state(chat_id)
                
                # 개별 스킬 자동 권한 체크
                skill_auto_approved = False
                for auto_sf in state.get('auto_skills', set()):
                    if auto_sf in extracted_cmd:
                        skill_auto_approved = True
                        break
                
                if state['auto_mode'] or skill_auto_approved:
                    # 자동 실행 모드 또는 개별 스킬 자동 승인
                    if not state['auto_mode']:
                        await bot.send_message(chat_id=chat_id, text=f"⚡ (개별 스킬 권한에 의해 즉시 실행됩니다.)\n`{extracted_cmd}`", parse_mode='Markdown')
                    await execute_command_and_continue(extracted_cmd, update, context, chat_id, application=application)
                else:
                    # 수동 승인 모드
                    state['pending_command'] = extracted_cmd
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ 실행 허락", callback_data="btn_yes"),
                            InlineKeyboardButton("❌ 실행 거부", callback_data="btn_no")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"🛑 **명령어 실행 대기 중**\n알쫑이가 다음 윈도우 명령어를 실행하려고 합니다. 허락하시겠습니까?\n\n`{extracted_cmd}`",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
        else:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_message.message_id,
                text="❌ 응답을 생성하지 못했습니다."
            )
            
    except requests.exceptions.ConnectionError:
        await bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text='❌ 안내: 로컬 Ollama 서버(11434 포트)가 꺼져 있습니다.')
    except Exception as e:
        await bot.edit_message_text(chat_id=chat_id, message_id=status_message.message_id, text=f'❌ 통신 오류: {str(e)}')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_text = update.message.text
    
    # 사용자의 말을 기억에 추가
    memory.add_message(chat_id=chat_id, role="user", content=user_text)
    
    # 스트리밍 텍스트 생성
    await stream_llm_response(update, context, chat_id, current_query=user_text)

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
                            chat_ids = list(user_states.keys())
                            if chat_ids:
                                chat_id = chat_ids[-1] 
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
                        
                        chat_ids = list(user_states.keys())
                        if chat_ids:
                            chat_id = chat_ids[-1]
                            alert_msg = f"🚨 **[문어발 자가 치유 시스템 발동]**\n\n문어발 스크립트 `{filename}` 에서 에러가 감지되었습니다. 알쫑이가 디버깅을 시작합니다!\n\n에러 내용:\n`{err_log[:500]}...`"
                            await application.bot.send_message(chat_id=chat_id, text=alert_msg, parse_mode='Markdown')
                            
                            ai_prompt = f"[긴급 시스템 명령 - 자가 치유(Self-Healing) 발동]\n백그라운드에서 동작하는 당신의 보조 스크립트(문어발) '{filename}'에서 다음 에러가 발생했습니다:\n\n{err_log}\n\n당장 <CMD>python C:\\ai\\Antigravity_Memory_Engine\\skill_system\\skills\\tentacle_manager.py read \"{filename}\"</CMD> 를 실행하여 코드를 읽어오고, 원인을 분석한 뒤 수정한 코드를 다시 배포(write)하여 문제를 해결하십시오."
                            memory.add_message(chat_id=chat_id, role="user", content=ai_prompt)
                            await stream_llm_response(None, None, chat_id, application=application)
                            
        except Exception as e:
            print(f"Tentacle error watchdog error: {e}")
            
        await asyncio.sleep(60)

async def tentacle_signal_checker(application):
    import asyncio
    import json
    import os
    
    signal_file_path = os.path.join(BASE_DIR, "tentacles", "logs", "tentacle_signals.json")
    reported_signals = {}
    
    while True:
        try:
            if os.path.exists(signal_file_path):
                with open(signal_file_path, 'r', encoding='utf-8') as f:
                    signals = json.load(f)
                    
                for filename, sig_info in signals.items():
                    sig_time = sig_info.get("timestamp")
                    sig_message = sig_info.get("message", "")
                    
                    if reported_signals.get(filename) != sig_time:
                        reported_signals[filename] = sig_time
                        
                        chat_ids = list(user_states.keys())
                        if chat_ids:
                            chat_id = chat_ids[-1]
                            
                            ai_prompt = f"[긴급 시스템 명령 - 자율신경계(문어발) 신호 수신]\n백그라운드에서 동작하는 당신의 보조 스크립트(문어발) '{filename}'에서 다음 유용한 정보를 수집하여 보고했습니다:\n\n{sig_message}\n\n사용자에게 이 정보를 기반으로 아침 인사나 주식 알림 등 친절하고 간결한 선톡 브리핑을 즉시 작성하여 보내십시오."
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
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('backup', backup_command))
    application.add_handler(CommandHandler('clear', clear_memory))
    
    # 에이전트용 특수 핸들러
    application.add_handler(CommandHandler('auto', auto_toggle))
    application.add_handler(CommandHandler('yes', yes_command))
    application.add_handler(CommandHandler('no', no_command))
    application.add_handler(CommandHandler('memorymode', memorymode_command))
    application.add_handler(CommandHandler('skills', skills_command))
    application.add_handler(CommandHandler('tentacles', tentacles_command))
    application.add_handler(CallbackQueryHandler(skill_callback_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print('준비 완료! (에이전트 루프 및 기억 엔진 가동 중...)')
    application.run_polling()

if __name__ == '__main__':
    main()
