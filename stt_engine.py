import os
import io
import speech_recognition as sr

def transcribe_audio_google(wav_file_path):
    """
    구글 Web Speech API를 사용하여 음성을 텍스트로 변환
    """
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_file_path) as source:
            audio_data = recognizer.record(source)
            # 한국어 인식
            text = recognizer.recognize_google(audio_data, language='ko-KR')
            return text
    except sr.UnknownValueError:
        return "" # 음성을 인식하지 못한 경우
    except sr.RequestError as e:
        print(f"STT Error (Google): {e}")
        return f"[STT 오류: 구글 서버에 연결할 수 없습니다 - {e}]"
    except Exception as e:
        print(f"STT Error: {e}")
        return f"[STT 오류: {e}]"

# 전역 Whisper 모델 캐시 (최초 1회만 로드하기 위함)
_whisper_model = None

def transcribe_audio_whisper(wav_file_path):
    """
    로컬 faster-whisper 모델을 사용하여 음성을 텍스트로 변환
    """
    global _whisper_model
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return "[STT 오류: faster-whisper 모듈이 설치되지 않았습니다. 대시보드 환경설정에서 모델을 Google로 변경하거나 pip install faster-whisper를 실행하세요.]"
        
    try:
        if _whisper_model is None:
            print("🚀 로컬 Whisper 모델 로딩 중... (최초 1회만 실행됨)")
            # CPU 모드로 실행 (GPU가 VRAM 문제로 터지는 것을 방지, 필요시 device="cuda" 변경)
            # compute_type="int8" 로 하여 메모리 점유율을 줄입니다.
            _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            
        segments, info = _whisper_model.transcribe(wav_file_path, language="ko", beam_size=5)
        text = " ".join([segment.text for segment in segments])
        return text.strip()
    except Exception as e:
        print(f"STT Error (Whisper): {e}")
        return f"[STT 오류: 로컬 Whisper 인식 실패 - {e}]"

def convert_to_wav(input_file_path, output_file_path):
    """
    Telegram의 OGG 파일 등 임의의 오디오를 pydub와 imageio_ffmpeg를 이용해 WAV로 변환
    """
    try:
        from pydub import AudioSegment
        import imageio_ffmpeg
        
        # imageio_ffmpeg가 제공하는 바이너리 경로를 pydub에 주입
        AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
        
        audio = AudioSegment.from_file(input_file_path)
        audio.export(output_file_path, format="wav")
        return True
    except Exception as e:
        print(f"Audio Conversion Error: {e}")
        return False

def process_audio(audio_file_path, engine="google"):
    """
    통합 오디오 처리 함수. 
    1. WAV 파일로 변환 (필요시)
    2. 지정된 STT 엔진으로 변환
    3. 텍스트 리턴
    """
    import tempfile
    
    # 텔레그램이나 웹마이크 파일은 ogg, webm, wav 등 다양함. 
    # 무조건 wav로 변환하여 처리.
    fd, temp_wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    
    try:
        success = convert_to_wav(audio_file_path, temp_wav)
        if not success:
            return "[STT 오류: 오디오 파일을 변환할 수 없습니다. FFmpeg 문제가 발생했을 수 있습니다.]"
            
        if engine.lower() == "whisper":
            return transcribe_audio_whisper(temp_wav)
        else:
            return transcribe_audio_google(temp_wav)
            
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except:
                pass
