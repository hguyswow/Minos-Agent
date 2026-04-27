import sys
import os
import datetime

# 엔진 폴더 최상단에 todo_list.txt 저장
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TODO_FILE = os.path.join(BASE_DIR, "todo_list.txt")

def read_todos():
    if not os.path.exists(TODO_FILE):
        print("현재 기록된 메모나 할 일이 없습니다.")
        return
        
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if content.strip():
            print("[나의 로컬 메모장 / 할 일 목록]\n")
            print(content)
        else:
            print("현재 기록된 메모나 할 일이 없습니다.")

def add_todo(note):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(TODO_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now_str}] {note}\n")
    print("메모가 성공적으로 기록되었습니다. (나중에 읽으려면 명령어 인자 없이 스크립트를 실행하세요.)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 인자가 있으면 쓰기 모드
        note = " ".join(sys.argv[1:])
        add_todo(note)
    else:
        # 인자가 없으면 읽기 모드
        read_todos()
