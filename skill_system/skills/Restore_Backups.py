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