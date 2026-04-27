import threading
import queue
import re
import json
import os

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
            text, rate, volume = item
            try:
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

        # 스피치용 텍스트 클리닝 (태그 및 마크다운 제거)
        clean_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.DOTALL)
        clean_text = re.sub(r'[*_`~]', '', clean_text)
        if clean_text.strip():
            self.q.put((clean_text.strip(), rate, volume))

tts = TTSEngine()
