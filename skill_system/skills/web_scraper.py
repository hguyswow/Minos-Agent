import sys
import io
import requests
from bs4 import BeautifulSoup

# 한글 깨짐 방지 (Windows 환경 시스템 인코딩 방어)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def scrape_web(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 스크립트, 스타일, 네비게이션 바 등 불필요한 태그 제거
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.extract()
            
        text = soup.get_text(separator='\n')
        # 공백 정리
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        print(f"[{url} 페이지 본문 추출 결과]\n")
        print(text[:5000]) # 토큰 절약을 위해 5000자로 제한
        if len(text) > 5000:
            print("\n... (길이 제한으로 생략됨)")
            
    except Exception as e:
        print(f"웹 스크래핑 오류: 해당 웹페이지를 읽어오지 못했습니다. ({e})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python web_scraper.py \"웹주소(URL)\"")
        sys.exit(1)
    scrape_web(sys.argv[1])
