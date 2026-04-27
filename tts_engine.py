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
    def __init__(self):
        self.q = queue.Queue()
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
                    # edge-tts 처리
                    async def play_edge():
                        # volume / rate 는 edge-tts 에서 지원하는 파라미터가 있지만 심플하게 voice만 우선 적용
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
                        try:
                            os.remove(temp_audio)
                        except: pass
                    
                    asyncio.run(play_edge())
                else:
                    # 기존 pyttsx3 처리
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
        if not pyttsx3:
            return
            
        current_config = get_bot_config()
        if not current_config.get("tts_enabled", False):
            return
            
        rate = current_config.get("tts_rate", 180)
        volume = float(current_config.get("tts_volume", 1.0))
        engine_type = current_config.get("tts_engine", "pyttsx3")
        voice = current_config.get("tts_voice", "ko-KR-SunHiNeural")

        # 스피치용 텍스트 클리닝 (태그 및 마크다운 제거)
        clean_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.DOTALL)
        clean_text = re.sub(r'[*_`~]', '', clean_text)
        if clean_text.strip():
            self.q.put((clean_text.strip(), rate, volume, engine_type, voice))

tts = TTSEngine()
