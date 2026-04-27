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
