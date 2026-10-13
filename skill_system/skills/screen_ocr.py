# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: screen_ocr
# AGENT_SKILL_DESC: 현재 화면(스크린샷)에서 텍스트를 OCR로 추출합니다. 복사 불가능한 화면의 텍스트를 읽을 때 유용합니다.
# AGENT_SKILL_ARGS: region(str) - 캡처 영역 (선택, 기본값: 전체 화면)
# AGENT_SKILL_RETURNS: 화면에서 인식된 텍스트
import sys
import pyautogui
import pytesseract

def capture_and_ocr():
    try:
        # 화면 캡처
        screenshot = pyautogui.screenshot()
        # OCR 수행 (한국어+영어)
        # 참고: Tesseract-OCR이 환경변수에 등록되어 있지 않다면 에러 발생
        text = pytesseract.image_to_string(screenshot, lang='kor+eng')
        
        print("[화면 캡처 및 OCR(글자 인식) 결과]\n")
        if text.strip():
            print(text)
        else:
            print("인식된 텍스트가 없습니다. 화면이 비어있거나 그림 위주일 수 있습니다.")
    except pytesseract.pytesseract.TesseractNotFoundError:
        print("[ERROR] Tesseract-OCR이 설치되어 있지 않거나 환경변수 PATH에 등록되지 않았습니다.")
        print("사용자에게 Tesseract-OCR 프로그램 설치를 요청하세요.")
    except Exception as e:
        print(f"OCR 실행 중 알 수 없는 오류 발생: {e}")

if __name__ == "__main__":
    capture_and_ocr()
