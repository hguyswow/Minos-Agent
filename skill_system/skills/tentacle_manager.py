import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TENTACLES_DIR = os.path.join(BASE_DIR, "tentacles")

def main():
    if len(sys.argv) < 2:
        print("사용법: python tentacle_manager.py [read/write] [파일명] [코드내용(write인경우)]")
        return

    action = sys.argv[1]
    
    if action == "read":
        if len(sys.argv) < 3:
            print("파일명을 입력하세요.")
            return
        filename = sys.argv[2]
        filepath = os.path.join(TENTACLES_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"오류: {filename} 파일을 찾을 수 없습니다.")
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
            
        print(f"--- {filename} 코드 시작 ---")
        print(code)
        print(f"--- {filename} 코드 끝 ---")
        
    elif action == "write":
        if len(sys.argv) < 4:
            print("파일명과 새로운 코드 내용을 모두 입력해야 합니다.")
            return
        filename = sys.argv[2]
        filepath = os.path.join(TENTACLES_DIR, filename)
        new_code = sys.argv[3]
        
        # 백업 생성
        if os.path.exists(filepath):
            backup_path = filepath + ".bak"
            import shutil
            shutil.copy2(filepath, backup_path)
            print(f"[안내] 기존 코드를 {filename}.bak 로 백업했습니다.")
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_code)
            
        # 에러 기록 즉시 삭제 (환상통 방지)
        error_file = os.path.join(TENTACLES_DIR, "logs", "tentacle_errors.json")
        if os.path.exists(error_file):
            try:
                import json
                with open(error_file, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
                if filename in errors:
                    del errors[filename]
                    with open(error_file, 'w', encoding='utf-8') as f:
                        json.dump(errors, f, indent=4, ensure_ascii=False)
            except Exception as e:
                pass
            
        print(f"[성공] {filename} 코드가 성공적으로 수정(배포)되었습니다. 다음 데몬 사이클에서 테스트됩니다.")
        
    else:
        print("알 수 없는 액션입니다. read 또는 write 를 사용하세요.")

if __name__ == "__main__":
    main()
