# -*- coding: utf-8 -*-
"""
스킬명: Prompt_Editor
기능: 자신의 시스템 프롬프트(prompt.txt)를 읽거나 수정하여
      자신의 성격, 말투, 행동 지침을 스스로 조율합니다.
사용법:
  Prompt_Editor.py read                         — 현재 프롬프트 전체 출력
  Prompt_Editor.py append "추가할 내용"          — 프롬프트 끝에 내용 추가
  Prompt_Editor.py replace "찾을텍스트" "바꿀텍스트" — 특정 구절 수정
  Prompt_Editor.py restore                      — 백업에서 프롬프트 복원
"""
import os
import sys
import shutil
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROMPT_FILE = os.path.join(BASE_DIR, 'prompt.txt')
BACKUP_DIR  = os.path.join(BASE_DIR, 'state', 'prompt_backups')

def backup_prompt():
    """수정 전 자동 백업"""
    if not os.path.exists(PROMPT_FILE):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'prompt_{ts}.txt')
    shutil.copy2(PROMPT_FILE, backup_path)
    print(f"[백업 완료] {backup_path}")
    # 최신 5개 백업만 유지
    backups = sorted(os.listdir(BACKUP_DIR))
    for old in backups[:-5]:
        os.remove(os.path.join(BACKUP_DIR, old))

def main():
    if len(sys.argv) < 2:
        print("[오류] 사용법: Prompt_Editor.py [read/append/replace/restore] [인자...]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == 'read':
        if not os.path.exists(PROMPT_FILE):
            print("[오류] prompt.txt가 없습니다.")
            sys.exit(1)
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.splitlines()
        print(f"[Prompt_Editor] 현재 프롬프트 ({len(lines)}줄, {len(content)}자):")
        print("=" * 60)
        print(content)
        print("=" * 60)

    elif action == 'append':
        if len(sys.argv) < 3:
            print("[오류] 추가할 내용을 입력하세요.")
            sys.exit(1)
        append_text = sys.argv[2]
        backup_prompt()
        with open(PROMPT_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n\n# [자가 업데이트 {datetime.now().strftime('%Y-%m-%d %H:%M')}]\n{append_text}")
        print(f"[Prompt_Editor] 프롬프트에 내용 추가 완료:")
        print(f"  >>> {append_text[:100]}")

    elif action == 'replace':
        if len(sys.argv) < 4:
            print("[오류] 사용법: Prompt_Editor.py replace \"찾을텍스트\" \"바꿀텍스트\"")
            sys.exit(1)
        find_str = sys.argv[2]
        repl_str = sys.argv[3]
        if not os.path.exists(PROMPT_FILE):
            print("[오류] prompt.txt가 없습니다.")
            sys.exit(1)
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        if find_str not in content:
            print(f"[오류] 찾을 텍스트를 프롬프트에서 찾지 못했습니다: '{find_str}'")
            sys.exit(1)
        backup_prompt()
        new_content = content.replace(find_str, repl_str)
        with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[Prompt_Editor] 수정 완료:")
        print(f"  변경 전: {find_str[:60]}")
        print(f"  변경 후: {repl_str[:60]}")

    elif action == 'restore':
        if not os.path.exists(BACKUP_DIR):
            print("[오류] 백업 폴더가 없습니다.")
            sys.exit(1)
        backups = sorted(os.listdir(BACKUP_DIR))
        if not backups:
            print("[오류] 복원할 백업 파일이 없습니다.")
            sys.exit(1)
        latest = os.path.join(BACKUP_DIR, backups[-1])
        shutil.copy2(latest, PROMPT_FILE)
        print(f"[Prompt_Editor] 최신 백업으로 복원 완료: {backups[-1]}")

    else:
        print(f"[오류] 알 수 없는 명령: '{action}'")
        print("사용 가능: read, append, replace, restore")
        sys.exit(1)

if __name__ == "__main__":
    main()
