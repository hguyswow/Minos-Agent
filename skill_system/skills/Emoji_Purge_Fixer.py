# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Emoji_Purge_Fixer
# AGENT_SKILL_DESC: 파이썬 소스 파일에서 이모지와 특수문자를 제거하거나 안전한 텍스트로 교체합니다. 인코딩 오류 방지용.
# AGENT_SKILL_ARGS: file_path(str) - 처리할 파이썬 파일 경로
# AGENT_SKILL_RETURNS: 처리 완료 메시지 및 수정된 항목 수
import sys
import os
import glob
import re

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

TARGET_DIR = r"C:\ai\Antigravity_Memory_Engine\tentacles"

EMOJI_MAP = {
    "\u2728": "[SPARKLES]",
    "\U0001F527": "[WRENCH]",
    "\U0001F4CA": "[CHART]",
    "\U0001F680": "[ROCKET]",
    "\u26A0\uFE0F": "[WARNING]",
    "\u26A0": "[WARNING]",
    "\u2705": "[CHECK]",
    "\u274C": "[X]",
    "\U0001F4B0": "[MONEY]",
    "\U0001F525": "[FIRE]",
    "\U0001F4E2": "[ALERT]",
    "\U0001F60A": "[SMILE]",
    "\U0001F60E": "[COOL]",
    "\U0001F44D": "[THUMBS_UP]",
    "\U0001F44E": "[THUMBS_DOWN]",
    "\U0001F4BB": "[COMPUTER]",
    "\U0001F504": "[LOOP]",
    "\U0001F4DD": "[MEMO]",
    "\U0001F3AF": "[TARGET]",
    "\U0001F4A1": "[IDEA]",
    "\U0001F680": "[ROCKET]",
    "\U0001F916": "[ROBOT]",
    "\U0001F4AC": "[SPEECH]",
    "\u2757": "[!]",
    "\u2753": "[?]",
    "\U0001F680": "[ROCKET]",
}

changed_files = 0
total_replacements = 0

for filepath in glob.glob(os.path.join(TARGET_DIR, "*.py")):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        original = content
        for emoji, text in EMOJI_MAP.items():
            if emoji in content:
                content = content.replace(emoji, text)
        
        # 남은 모든 이모지 강제 제거 (유니코드 범위)
        content = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U0000FE00-\U0000FE0F]', '', content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            changed_files += 1
            print(f"Fixed: {os.path.basename(filepath)}")
    except Exception as e:
        print(f"Error on {os.path.basename(filepath)}: {e}")

print(f"\nDone! {changed_files} files purged of emojis.")