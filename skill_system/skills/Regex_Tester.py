# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Regex_Tester
# AGENT_SKILL_DESC: 정규식 패턴을 테스트합니다. 패턴과 테스트 문자열을 주면 매칭 결과를 반환합니다.
# AGENT_SKILL_ARGS: pattern(str) - 정규식 패턴, text(str) - 테스트할 문자열
# AGENT_SKILL_RETURNS: 매칭 결과 및 캡처 그룹
"""
스킬명: Regex_Tester
기능: 정규식 패턴과 대상 문자열을 받아 매칭 결과 및 그룹을 상세 출력
"""
import re
import sys
import json

def main():
    if len(sys.argv) < 3:
        print("[오류] 사용법: Regex_Tester.py \"패턴\" \"대상문자열\"")
        sys.exit(1)

    pattern_str = sys.argv[1]
    target_str = sys.argv[2]
    flag_arg = sys.argv[3] if len(sys.argv) > 3 else ""

    flags = 0
    if 'i' in flag_arg: flags |= re.IGNORECASE
    if 'm' in flag_arg: flags |= re.MULTILINE
    if 's' in flag_arg: flags |= re.DOTALL

    print(f"[Regex_Tester] 패턴: {pattern_str}")
    print(f"[Regex_Tester] 대상: {target_str}")
    print("-" * 50)

    try:
        compiled = re.compile(pattern_str, flags)
    except re.error as e:
        print(f"[오류] 유효하지 않은 정규식 패턴입니다: {e}")
        sys.exit(1)

    # 전체 매칭 확인
    full_match = compiled.fullmatch(target_str)
    if full_match:
        print(f"✅ 전체 매칭(fullmatch) 성공!")
        print(f"   매칭 값: {full_match.group()}")
        if full_match.groups():
            for i, g in enumerate(full_match.groups(), 1):
                print(f"   그룹 {i}: {g}")
    else:
        print("ℹ️ 전체 매칭(fullmatch): 없음")

    # 부분 매칭 확인
    matches = list(compiled.finditer(target_str))
    print(f"\n🔍 findall 매칭 결과: {len(matches)}건")
    for idx, m in enumerate(matches, 1):
        print(f"  [{idx}] 위치 {m.start()}~{m.end()}: '{m.group()}'")
        if m.groups():
            for i, g in enumerate(m.groups(), 1):
                print(f"       그룹 {i}: {g}")

    # 치환 미리보기
    if matches:
        replaced = compiled.sub("[MATCH]", target_str)
        print(f"\n🔄 sub() 치환 미리보기: {replaced}")

if __name__ == "__main__":
    main()
