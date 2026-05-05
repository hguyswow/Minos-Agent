# -*- coding: utf-8 -*-
#
# web_fetch: URL을 받아 본문 텍스트만 깔끔하게 추출합니다. (HTML 태그 제거)
# 사용 예: <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\web_fetch.py "https://example.com"</CMD>
#
import sys
import io
import warnings
warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request
import re

def fetch_text(url: str, max_chars: int = 3000) -> str:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            # 인코딩 감지
            content_type = response.headers.get('Content-Type', '')
            if 'charset=euc-kr' in content_type.lower() or 'charset=ks_c' in content_type.lower():
                html = raw.decode('euc-kr', errors='replace')
            else:
                try:
                    html = raw.decode('utf-8')
                except UnicodeDecodeError:
                    html = raw.decode('euc-kr', errors='replace')

        # HTML 태그 제거
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'\s{2,}', '\n', text).strip()

        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n...(이하 {len(text)-max_chars}자 생략)"
        return text

    except Exception as e:
        return f"[web_fetch 오류] {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python web_fetch.py \"https://URL주소\"")
        sys.exit(1)
    url = sys.argv[1]
    result = fetch_text(url)
    print(f"[URL: {url}] 본문 추출 결과:\n")
    print(result)
