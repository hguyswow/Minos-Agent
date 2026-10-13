# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: clipboard_manager
# AGENT_SKILL_DESC: 클립보드 내용을 읽거나 새 텍스트를 클립보드에 복사합니다.
# AGENT_SKILL_ARGS: action(str) - read/write, text(str) - 복사할 텍스트(write 시)
# AGENT_SKILL_RETURNS: 현재 클립보드 내용 또는 복사 완료 메시지
import sys
import pyperclip

def manage_clipboard():
    if len(sys.argv) > 1:
        # Write to clipboard
        text_to_copy = " ".join(sys.argv[1:])
        pyperclip.copy(text_to_copy)
        print("클립보드에 텍스트가 성공적으로 복사되었습니다.")
    else:
        # Read from clipboard
        content = pyperclip.paste()
        if content and content.strip():
            print(f"[현재 클립보드에 복사된 내용]\n{content}")
        else:
            print("클립보드가 비어있거나 텍스트 형태가 아닙니다.")

if __name__ == "__main__":
    manage_clipboard()
