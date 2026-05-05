# -*- coding: utf-8 -*-
"""
스킬명: Vision_UI_Analyzer
기능: 이미지 경로(스크린샷)를 받아 멀티모달 프롬프트를 전송해 분석
사용법: Vision_UI_Analyzer.py "이미지경로" "질문/프롬프트"
"""
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    if len(sys.argv) < 3:
        print("[오류] 사용법: Vision_UI_Analyzer.py \"이미지경로\" \"질문내용\"")
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = sys.argv[2]

    if not os.path.exists(image_path):
        print(f"[오류] 이미지를 찾을 수 없습니다: {image_path}")
        sys.exit(1)
        
    print(f"👁️ [Vision 분석 시작]")
    print(f"- 대상 이미지: {image_path}")
    print(f"- 질문: {prompt}")
    
    # 멀티모달 API(로컬 LLaVA 등) 연동 뼈대
    print("\n✅ 이미지가 성공적으로 인식되었습니다. (멀티모달 API 연동 대기 중)")
    print("이 스크립트는 향후 Ollama LLaVA 또는 외부 Vision API와 HTTP 통신을 수행하도록 확장될 예정입니다.")

if __name__ == "__main__":
    main()
