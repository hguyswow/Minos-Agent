import sys
from duckduckgo_search import DDGS

def search(query, max_results=5):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if not results:
                print(f"'{query}'에 대한 검색 결과가 없습니다.")
                return
            
            print(f"[{query}] 검색 결과 (Top {len(results)}):\n")
            for i, res in enumerate(results, 1):
                print(f"{i}. {res.get('title', '제목 없음')}")
                print(f"   내용: {res.get('body', '내용 없음')}")
                print(f"   링크: {res.get('href', '링크 없음')}\n")
    except Exception as e:
        print(f"웹 검색 중 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python web_search.py \"검색어\"")
        sys.exit(1)
        
    # 명령어 인자를 모두 합쳐서 검색어로 사용
    query = " ".join(sys.argv[1:])
    search(query)
