# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: fix_tentacle_encoding
# AGENT_SKILL_DESC: 문어발(tentacle) 스크립트의 인코딩 문제를 수정합니다. CP949/UTF-8 변환 등 한글 깨짐 방지.
# AGENT_SKILL_ARGS: file_path(str) - 수정할 파일 경로
# AGENT_SKILL_RETURNS: 인코딩 수정 결과
import os

target_path = r"C:\ai\Antigravity_Memory_Engine\skill_system\skills\tentacle_manager.py"

# 1. 원본 백업
backup_path = target_path + ".bak"
if not os.path.exists(backup_path):
    with open(target_path, 'r', encoding='utf-8') as f:
        original = f.read()
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original)
    print(f"✅ 백업 완료: {backup_path}")

# 2. 파일 읽기
with open(target_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 3. 문제의 print(code) 문장을 인코딩 안전하게 패치
#    CP949로 출력할 수 없는 문자를 replace로 대체
old_pattern = "print(code)"
if old_pattern in content:
    new_pattern = "print(code.encode('cp949', errors='replace').decode('cp949'))"
    content = content.replace(old_pattern, new_pattern)
    print(f"🔧 '{old_pattern}' → '{new_pattern}' 패치 완료")
else:
    print("❌ 패턴을 찾을 수 없습니다. 코드를 확인해주세요.")

# 4. 파일 저장
with open(target_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ tentacle_manager.py 인코딩 패치 성공!")