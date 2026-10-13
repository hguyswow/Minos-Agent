# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: voice_tts
# AGENT_SKILL_DESC: 텍스트를 음성으로 변환하여 스피커로 재생합니다. 한국어와 영어를 지원합니다.
# AGENT_SKILL_ARGS: text(str) - 읽어줄 텍스트, lang(str) - ko/en
# AGENT_SKILL_RETURNS: 음성 재생 완료 메시지
import sys
import os
import asyncio
import edge_tts

# Pygame 웰컴 메시지("Hello from the pygame community")를 봇이 읽고 당황하지 않도록 숨김 처리
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

async def speak_text(text):
    # 형님께서 지정하신 마이크로소프트 27세 여성톤 클라우드 Neural 보이스
    voice = "ko-KR-SunHiNeural"
    
    # 임시 오디오 파일 저장 경로 (프로젝트 최상단)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_file = os.path.join(BASE_DIR, "temp_tts_output.mp3")
    
    try:
        # 1. Edge-TTS를 이용하여 고음질 MP3 파일 생성 (속도 약간 증가 +10%)
        communicate = edge_tts.Communicate(text, voice, rate="+10%")
        await communicate.save(output_file)
        
        # 2. Pygame을 이용하여 백그라운드 오디오 재생
        pygame.mixer.init()
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()
        
        print(f"[OK] 고음질 SunHiNeural 보이스로 성공적으로 출력했습니다: '{text}'")
        
        # 3. 비동기 블로킹 방식을 사용하여 재생이 끝날 때까지 스크립트 대기
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # 4. 재생 완료 후 오디오 엔진 종료 및 임시 파일 청소
        pygame.mixer.quit()
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass
                
    except Exception as e:
        print(f"[ERROR] 음성 합성(TTS) 중 오류 발생 (인터넷 연결을 확인하세요): {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python voice_tts.py \"읽어줄 문장\"")
        sys.exit(1)
        
    # Windows 환경에서 asyncio.run() 중복 실행 시 발생하는 루프 오류 방지
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    text = " ".join(sys.argv[1:])
    asyncio.run(speak_text(text))
