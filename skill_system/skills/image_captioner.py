# -*- coding: utf-8 -*-
#
# image_captioner: 이미지 파일 경로를 받아 Ollama의 비전 모델(gemma4-e4b 또는 llava)로 이미지 내용을 설명합니다.
# 사용 예: <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\image_captioner.py "C:\path\to\image.jpg"</CMD>
#
import sys
import io
import warnings
warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import base64
import json
import urllib.request

# Ollama에서 비전을 지원하는 모델 (우선순위 순)
VISION_MODELS = ["gemma4-e4b:q4km", "llava", "moondream"]

def describe_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        return f"[image_captioner] 파일을 찾을 수 없습니다: {image_path}"

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
        return f"[image_captioner] 지원하지 않는 이미지 형식입니다: {ext}"

    try:
        with open(image_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        return f"[image_captioner] 이미지 로드 실패: {e}"

    # 사용 가능한 모델 확인
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as res:
            tags = json.loads(res.read().decode('utf-8'))
        available = [m['name'] for m in tags.get('models', [])]
    except:
        available = []

    selected_model = None
    for m in VISION_MODELS:
        if any(m in a for a in available):
            selected_model = next(a for a in available if m in a)
            break

    if not selected_model:
        return f"[image_captioner] 비전 모델을 찾을 수 없습니다. Ollama에서 llava 또는 gemma4 모델을 pull 하세요."

    payload = json.dumps({
        "model": selected_model,
        "prompt": "이 이미지에서 보이는 것을 한국어로 상세하게 설명해 주세요. 텍스트가 있다면 읽어주세요.",
        "images": [img_b64],
        "stream": False
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=60) as res:
            result = json.loads(res.read().decode('utf-8'))
        return f"[이미지 설명 - 모델: {selected_model}]\n{result.get('response', '결과 없음')}"
    except Exception as e:
        return f"[image_captioner] Ollama 비전 API 오류: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python image_captioner.py \"C:\\path\\to\\image.jpg\"")
        sys.exit(1)
    result = describe_image(sys.argv[1])
    print(result)
