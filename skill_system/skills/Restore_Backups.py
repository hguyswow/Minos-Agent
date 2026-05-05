# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Restore_Backups
# AGENT_SKILL_DESC: 백업된 파일을 원래 위치로 복원합니다. 파일 수정 실수 등 긴급 상황에서 롤백할 때 사용합니다.
# AGENT_SKILL_ARGS: file_path(str) - 복원할 파일 경로
# AGENT_SKILL_RETURNS: 복원 성공/실패 메시지
import shutil
import os

base_dir = r"C:\ai\Antigravity_Memory_Engine\tentacles"

bak_files = [
    "stock_tiger_tentacle.py",
    "morning_brief_tentacle.py",
]

restored = []
failed = []

for f in bak_files:
    src = os.path.join(base_dir, f + ".bak")
    dst = os.path.join(base_dir, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        restored.append(f)
        print(f"[OK] 복원 완료: {f}")
    else:
        failed.append(f)
        print(f"[FAIL] 백업 없음: {f}")

print(f"\n복원 완료: {len(restored)}개")
print(f"복원 실패: {len(failed)}개")