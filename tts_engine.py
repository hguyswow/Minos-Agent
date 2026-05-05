# -*- coding: utf-8 -*-
import threading
import queue
import re
import json
import os
import asyncio
import tempfile

try:
    import edge_tts
    import pygame
    pygame.mixer.init()
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    import pythoncom
except ImportError:
    pyttsx3 = None
    pythoncom = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_bot_config():
    config_file = os.path.join(BASE_DIR, "state", "bot_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except: pass
    return {}

class TTSEngine:
    def __init__(self, skip_symbols: bool = False):
        self.q = queue.Queue()
        self._skip_symbols = skip_symbols
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        
    def _worker(self):
        if not pyttsx3: return
        if pythoncom:
            pythoncom.CoInitialize()
        engine = pyttsx3.init()
        while True:
            item = self.q.get()
            if item is None:
                break
            text, rate, volume, engine_type, voice = item
            try:
                if engine_type == "edge" and EDGE_TTS_AVAILABLE:
                    async def play_edge():
                        communicate = edge_tts.Communicate(text, voice)
                        fd, temp_audio = tempfile.mkstemp(suffix=".mp3")
                        os.close(fd)
                        await communicate.save(temp_audio)
                        
                        pygame.mixer.music.load(temp_audio)
                        pygame.mixer.music.set_volume(volume)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                        pygame.mixer.music.unload()
                        try: os.remove(temp_audio)
                        except: pass
                    
                    asyncio.run(play_edge())
                elif engine_type == "google" and GTTS_AVAILABLE:
                    def play_google():
                        tts_google = gTTS(text=text, lang='ko', slow=(rate < 150))
                        fd, temp_audio = tempfile.mkstemp(suffix=".mp3")
                        os.close(fd)
                        tts_google.save(temp_audio)
                        
                        pygame.mixer.music.load(temp_audio)
                        pygame.mixer.music.set_volume(volume)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                        pygame.mixer.music.unload()
                        try: os.remove(temp_audio)
                        except: pass
                    
                    play_google()
                else:
                    if not pyttsx3: raise Exception("pyttsx3 not installed")
                    engine.setProperty('rate', rate)
                    engine.setProperty('volume', volume)
                    engine.say(text)
                    engine.runAndWait()
            except Exception as e:
                print(f"TTS Error: {e}")
            finally:
                self.q.task_done()

    def speak(self, text):
        if not pyttsx3: return
            
        current_config = get_bot_config()
        if not current_config.get("tts_enabled", False): return
            
        rate = current_config.get("tts_rate", 180)
        volume = float(current_config.get("tts_volume", 1.0))
        engine_type = current_config.get("tts_engine", "pyttsx3")
        voice = current_config.get("tts_voice", "ko-KR-SunHiNeural")
        
        # 기호/이모지 스킵 옵션 갱신
        self._skip_symbols = current_config.get("tts_skip_symbols", False)

        # 스피치용 텍스트 클리닝
        clean_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.DOTALL)
        clean_text = re.sub(r'#+\s*', '', clean_text)   # ## 헤딩 제거 (샘플시인 포함)
        clean_text = re.sub(r'[*_`~]', '', clean_text)
        
        if self._skip_symbols:
            # 이모지 제거
            clean_text = re.sub(r'[\U0001F600-\U0001F64F]', '', clean_text)
            clean_text = re.sub(r'[\U0001F300-\U0001F5FF]', '', clean_text)
            # 괄호 제거
            clean_text = re.sub(r'[\(\[\{][^\)\]\}]*[\)\]\}]', '', clean_text)
            
        if clean_text.strip():
            self.q.put((clean_text.strip(), rate, volume, engine_type, voice))

    def stop(self):
        """현재 재생 중인 음성을 중단하고 대기 중인 큐를 비움"""
        try:
            pygame.mixer.music.stop()
            while not self.q.empty():
                try:
                    self.q.get_nowait()
                    self.q.task_done()
                except: break
        except Exception as e:
            print(f"TTS Stop Error: {e}")

# 전역 인스턴스 생성
config = get_bot_config()
tts = TTSEngine(skip_symbols=config.get('tts_skip_symbols', False))

def generate_tts_file(text, config):
    """지정된 텍스트와 설정으로 오디오 파일을 생성하고 해당 경로를 반환합니다. 호출자가 직접 삭제해야 합니다."""
    clean_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.DOTALL)
    clean_text = re.sub(r'#+\s*', '', clean_text)   # ## 헤딩 제거 (샘플시인 포함)
    clean_text = re.sub(r'[*_`~]', '', clean_text)
    if config.get("tts_skip_symbols", False):
        clean_text = re.sub(r'[\U0001F600-\U0001F64F]', '', clean_text)
        clean_text = re.sub(r'[\U0001F300-\U0001F5FF]', '', clean_text)
        clean_text = re.sub(r'[\(\[\{][^\)\]\}]*[\)\]\}]', '', clean_text)
        
    clean_text = clean_text.strip()
    if not clean_text: return None

    engine_type = config.get("tts_engine", "pyttsx3")
    voice = config.get("tts_voice", "ko-KR-SunHiNeural")
    rate = config.get("tts_rate", 180)
    
    fd, temp_audio = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    
    try:
        if engine_type == "edge" and EDGE_TTS_AVAILABLE:
            async def gen_edge():
                communicate = edge_tts.Communicate(clean_text, voice)
                await communicate.save(temp_audio)
            asyncio.run(gen_edge())
        elif engine_type == "google" and GTTS_AVAILABLE:
            tts_google = gTTS(text=clean_text, lang='ko', slow=(rate < 150))
            tts_google.save(temp_audio)
        else:
            # 기본 pyttsx3는 파일 저장이 까다로우므로 google로 폴백
            if GTTS_AVAILABLE:
                tts_google = gTTS(text=clean_text, lang='ko')
                tts_google.save(temp_audio)
            else:
                return None
        return temp_audio
    except Exception as e:
        print(f"TTS 파일 생성 실패: {e}")
        try: os.remove(temp_audio)
        except: pass
        return None
