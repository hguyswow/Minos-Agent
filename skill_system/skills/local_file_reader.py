# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: local_file_reader
# AGENT_SKILL_DESC: 로컬 파일 시스템의 파일을 읽어 내용을 반환합니다. 텍스트, JSON, 마크다운 등 다양한 형식 지원.
# AGENT_SKILL_ARGS: file_path(str) - 읽을 파일의 절대 경로
# AGENT_SKILL_RETURNS: 파일 내용 (텍스트)
import sys
import os

def read_file(filepath):
    if not os.path.exists(filepath):
        print(f"오류: 파일을 찾을 수 없습니다. 경로를 확인하세요. ({filepath})")
        return
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(5000) # 메모리 오버플로우 방지 최대 5000자
            print(f"[{os.path.basename(filepath)} 문서 내용 (최대 5000자)]")
            print(content)
            if len(content) == 5000:
                print("\n... (길이 제한으로 생략됨)")
    except UnicodeDecodeError:
        print("오류: 텍스트 파일이 아니거나 인코딩이 맞지 않습니다. (UTF-8 필요)")
    except Exception as e:
        print(f"파일 읽기 오류: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python local_file_reader.py \"파일절대경로\"")
        sys.exit(1)
    read_file(sys.argv[1])
