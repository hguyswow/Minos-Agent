# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Skill_Scaffolder
# AGENT_SKILL_DESC: 새로운 스킬 파이썬 파일의 기본 템플릿을 생성합니다. 스킬 이름과 설명을 주면 뼈대 코드를 만들어줍니다.
# AGENT_SKILL_ARGS: skill_name(str) - 스킬 이름, description(str) - 스킬 기능 설명
# AGENT_SKILL_RETURNS: 생성된 스킬 파일 경로
"""
스킬명: Skill_Scaffolder
기능: 스킬 이름과 설명을 입력하면 표준 형식의 .py 스킬 뼈대와
      skills_index 등록 문구를 자동 생성합니다.
      알쫑이가 새 스킬을 스스로 계획하고 제안할 때의 핵심 도구입니다.
사용법:
  Skill_Scaffolder.py "스킬파일명(영문)" "스킬 기능 설명(한글)" ["인자설명(선택)"]
  예: Skill_Scaffolder.py "Stock_Checker" "특정 주식 티커의 현재가를 조회합니다" "\"티커심볼\""
"""
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(BASE_DIR, 'skill_system', 'skills')
INDEX_FILE = os.path.join(BASE_DIR, 'skill_system', 'skills_index.txt')

TEMPLATE = '''# -*- coding: utf-8 -*-
"""
스킬명: {skill_name}
기능: {description}
사용법: {skill_name}.py {args_desc}
생성일: {created_at}
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # TODO: 인자 파싱
    # args = sys.argv[1:]
    # if not args:
    #     print("[오류] 사용법: {skill_name}.py [인자]")
    #     sys.exit(1)

    print("[{skill_name}] 실행 시작...")

    try:
        # TODO: 핵심 로직 구현
        result = "구현 필요"
        print(f"[{skill_name}] 결과: {{result}}")

    except Exception as e:
        print(f"[{skill_name}] 오류 발생: {{e}}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

def main():
    if len(sys.argv) < 3:
        print("[오류] 사용법: Skill_Scaffolder.py \"스킬파일명\" \"기능설명\" [\"인자설명\"]")
        sys.exit(1)

    skill_name_raw = sys.argv[1].replace('.py', '').strip()
    description    = sys.argv[2]
    args_desc      = sys.argv[3] if len(sys.argv) > 3 else "[인자]"

    # 파일명 안전하게 정제
    skill_name = ''.join(c for c in skill_name_raw if c.isalnum() or c in ('_', '-'))
    if not skill_name:
        print("[오류] 유효한 스킬 이름을 입력하세요 (영문, 숫자, _ 만 허용)")
        sys.exit(1)

    skill_file = f"{skill_name}.py"
    skill_path = os.path.join(SKILLS_DIR, skill_file)

    if os.path.exists(skill_path):
        print(f"[경고] 동일한 이름의 스킬이 이미 존재합니다: {skill_file}")
        print("       기존 파일을 덮어쓰려면 직접 삭제 후 다시 실행하세요.")
        sys.exit(1)

    # 뼈대 파일 생성
    code = TEMPLATE.format(
        skill_name=skill_name,
        description=description,
        args_desc=args_desc,
        created_at=datetime.now().strftime('%Y-%m-%d')
    )
    with open(skill_path, 'w', encoding='utf-8') as f:
        f.write(code)

    # skills_index.txt 등록 문구 생성
    index_line = (
        f"- {skill_name}: {description} "
        f"(실행: <CMD>python {skill_path} {args_desc}</CMD>)"
    )

    print("=" * 60)
    print(f"[Skill_Scaffolder] 스킬 뼈대 생성 완료!")
    print(f"  파일: {skill_path}")
    print()
    print("[skills_index.txt 등록 문구]")
    print(f"  {index_line}")
    print()
    print("[다음 단계]")
    print(f"  1. {skill_path} 파일을 열어 TODO 부분에 핵심 로직을 구현하세요.")
    print(f"  2. 위 등록 문구를 skills_index.txt에 추가하세요.")
    print(f"  3. Skill_Tester.py \"{skill_file}\" 로 동작을 검증하세요.")
    print("=" * 60)

    # 선택적으로 index에 자동 추가
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            current = f.read()
        if skill_name not in current:
            with open(INDEX_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n{index_line}\n")
            print(f"[skills_index.txt] 자동 등록 완료!")
    except Exception as e:
        print(f"[경고] skills_index.txt 자동 등록 실패: {e}")
        print("       위 등록 문구를 수동으로 추가해 주세요.")

if __name__ == "__main__":
    main()
