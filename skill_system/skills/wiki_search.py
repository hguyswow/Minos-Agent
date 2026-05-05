import sys
import io
import requests

# 한글 깨짐 방지 (Windows 환경 시스템 인코딩 방어)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def wiki_search(query, max_results=3):
    try:
        url = "https://ko.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "utf8": "",
            "format": "json",
            "srlimit": max_results
        }
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        
        if not search_results:
            print(f"'{query}'에 대한 위키백과 검색 결과가 없습니다.")
            return
            
        print(f"[{query}] 위키백과 검색 결과 (Top {len(search_results)}):\n")
        
        for i, res in enumerate(search_results, 1):
            title = res.get('title', '제목 없음')
            snippet = res.get('snippet', '내용 없음')
            
            # HTML 태그 제거 (snippet에 포함된 <span class="searchmatch"> 등 제거)
            import re
            clean_snippet = re.sub(r'<[^>]+>', '', snippet)
            clean_snippet = clean_snippet.replace("&quot;", '"').replace("&amp;", "&")
            
            link = f"https://ko.wikipedia.org/wiki/{title.replace(' ', '_')}"
            
            print(f"{i}. {title}")
            print(f"   내용: {clean_snippet}...")
            print(f"   링크: {link}\n")
            
    except Exception as e:
        print(f"위키백과 검색 중 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python wiki_search.py \"검색어\"")
        sys.exit(1)
        
    query = " ".join(sys.argv[1:])
    wiki_search(query)
