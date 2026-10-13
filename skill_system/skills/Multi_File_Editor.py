# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Multi_File_Editor
# AGENT_SKILL_DESC: 여러 파일을 한 번에 읽거나 수정합니다. 파일 목록과 변경 내용을 전달하면 일괄 처리합니다.
# AGENT_SKILL_ARGS: files(list) - 파일 경로 목록, action(str) - read/write/append
# AGENT_SKILL_RETURNS: 파일 처리 결과
"""
스킬명: Multi_File_Editor
기능: 특정 폴더/확장자에서 파일을 검색하여 일괄 찾기&바꾸기 수행
사용법: Multi_File_Editor.py "폴더경로" "찾을문자열" "바꿀문자열" [".py,.txt 등 확장자 필터(선택)"]
"""
import os
import sys

def main():
    if len(sys.argv) < 4:
        print("[오류] 사용법: Multi_File_Editor.py \"폴더경로\" \"찾을문자열\" \"바꿀문자열\" [\".py,.txt\"]")
        sys.exit(1)

    folder = sys.argv[1]
    find_str = sys.argv[2]
    replace_str = sys.argv[3]
    ext_filter_raw = sys.argv[4] if len(sys.argv) > 4 else ""
    ext_filter = [e.strip() for e in ext_filter_raw.split(",") if e.strip()] if ext_filter_raw else []

    if not os.path.isdir(folder):
        print(f"[오류] 폴더를 찾을 수 없습니다: {folder}")
        sys.exit(1)

    print(f"[Multi_File_Editor] 폴더: {folder}")
    print(f"[Multi_File_Editor] 찾기: '{find_str}' → 바꾸기: '{replace_str}'")
    if ext_filter:
        print(f"[Multi_File_Editor] 확장자 필터: {ext_filter}")
    print("-" * 50)

    modified_files = []
    skipped_files = []

    for root, dirs, files in os.walk(folder):
        # __pycache__ 등 불필요 폴더 제외
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules']]
        for fname in files:
            if ext_filter and not any(fname.endswith(ext) for ext in ext_filter):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if find_str in content:
                    new_content = content.replace(find_str, replace_str)
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    count = content.count(find_str)
                    modified_files.append((fpath, count))
                    print(f"  ✅ [{count}건 변경] {fpath}")
            except Exception as e:
                skipped_files.append((fpath, str(e)))

    print("-" * 50)
    print(f"✅ 총 {len(modified_files)}개 파일 수정 완료.")
    if skipped_files:
        print(f"⚠️ {len(skipped_files)}개 파일 처리 실패:")
        for fp, err in skipped_files:
            print(f"   - {fp}: {err}")

if __name__ == "__main__":
    main()
