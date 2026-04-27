import sys
import os
import py_compile
import subprocess

def validate_code(filepath):
    if not os.path.exists(filepath):
        print(f"❌ 오류: 지정된 파이썬 파일을 찾을 수 없습니다. 경로를 확인하세요. ({filepath})")
        return
        
    print(f"[{os.path.basename(filepath)} 코드 검증 리포트]\n")
    
    # 1. Syntax Check (문법 검사)
    print("[STEP 1] 문법(Syntax) 검사 (py_compile)")
    try:
        py_compile.compile(filepath, doraise=True)
        print("[OK] 문법 검사 통과: 치명적인 구문 오류(Syntax Error)가 없습니다.\n")
    except py_compile.PyCompileError as e:
        print("[ERROR] 치명적 문법 오류(Syntax Error) 발견!")
        print(str(e))
        print("\n이 스크립트는 실행조차 불가능한 상태입니다. 문법부터 수정해야 합니다.")
        return # Syntax 에러가 있으면 Linting은 무의미하므로 즉시 종료
        
    # 2. Pylint Analysis (정적 분석)
    print("[STEP 2] 논리, 최적화 및 스타일 분석 (Pylint)")
    try:
        # pylint 실행 (오류가 있어도 스크립트가 죽지 않도록 캡처)
        result = subprocess.run(
            ['pylint', filepath, '--output-format=text', '--reports=n'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8' # 윈도우 환경 한글 깨짐 방지
        )
        
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip()
            
        if "Your code has been rated at 10.00/10" in output:
             print("[OK] Pylint 검사 통과: 코드 퀄리티가 매우 우수합니다(10.00/10점)!\n")
             return
             
        # 긴 출력 방지 (최대 3000자 제한)
        print("[WARN] 코드 개선점(Warning/Refactoring) 발견:")
        print(output[:3000])
        
        if len(output) > 3000:
            print("\n... (결과가 너무 길어 3000자에서 잘렸습니다.)")
            
    except FileNotFoundError:
        print("[ERROR] 'pylint' 모듈이 설치되어 있지 않거나 환경변수 PATH에 없습니다. ('pip install pylint' 필요)")
    except Exception as e:
        print(f"분석 중 알 수 없는 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python code_validator.py \"파이썬파일_절대경로\"")
        sys.exit(1)
    validate_code(sys.argv[1])
