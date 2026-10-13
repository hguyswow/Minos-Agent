# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: web_search
# AGENT_SKILL_DESC: 인터넷에서 정보를 검색합니다. 한국어 쿼리는 실제 브라우저(Playwright)로 네이버를 검색하여 정확한 한국어 결과를 반환합니다.
# AGENT_SKILL_ARGS: query(str) - 검색할 키워드 또는 질문
# AGENT_SKILL_RETURNS: 검색 결과 요약 (제목 + 핵심 내용 + 출처 링크)
import sys
import io
import re
import os
import warnings

warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.StringIO()

# ── 한국어 쿼리 판별 ──────────────────────────────────
def is_korean(q: str) -> bool:
    return bool(re.search(r'[\uAC00-\uD7A3]', q))

# ── Playwright 가용 여부 확인 ─────────────────────────
def playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False

# ── 브라우저 검색 (한국어 전용) ───────────────────────
def browser_search_ko(query: str, max_results: int = 7) -> list:
    """browser_search.py 모듈을 import하여 Playwright 네이버 검색 수행"""
    try:
        # 같은 skills 폴더 내 browser_search 모듈 import
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        if skill_dir not in sys.path:
            sys.path.insert(0, skill_dir)
        from browser_search import naver_browser_search
        data = naver_browser_search(query, max_results=max_results)
        return data.get('results', [])
    except Exception:
        return []

# ── 중국어 쓰레기 판별 ────────────────────────────────
CHINESE_DOMAINS = re.compile(
    r'(zhihu\.com|baidu\.com|taobao|weibo|163\.com|sohu\.com|bilibili|csdn\.net'
    r'|\.cn/|zhidao\.baidu|wenku\.baidu|tieba\.baidu)'
)
def is_junk(res: dict) -> bool:
    href  = res.get('href', '')
    title = res.get('title', '')
    body  = res.get('body', '')
    if CHINESE_DOMAINS.search(href):
        return True
    text = title + body
    chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
    if len(text) > 20 and chinese / len(text) > 0.25:
        return True
    return False

# ── DDG 검색 (영문/폴백) ──────────────────────────────
def ddg_search(query: str, max_results: int = 10) -> list:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []

# ── 메인 검색 함수 ────────────────────────────────────
def search(query: str, max_results: int = 7) -> str:
    korean = is_korean(query)
    results = []

    if korean:
        # 1순위: Playwright 브라우저 실제 검색 (가용 시)
        if playwright_available():
            results = browser_search_ko(query, max_results=max_results)

        # 폴백: DDG + 한국어 힌트 + 중국어 필터
        if len(results) < 3:
            hint_query = query + " 나무위키 OR 한국 OR 네이버"
            r1 = ddg_search(hint_query, max_results=10)
            good1 = [r for r in r1 if not is_junk(r)]
            r2 = ddg_search(query, max_results=10)
            good2 = [r for r in r2 if not is_junk(r)]
            ddg_combined = good1 + [r for r in good2
                                    if r.get('href','') not in {x.get('href','') for x in good1}]
            # 기존 결과와 합치기 (중복 제거)
            existing_hrefs = {r.get('href','') for r in results}
            results += [r for r in ddg_combined if r.get('href','') not in existing_hrefs]

        engine_label = "네이버 브라우저" if playwright_available() else "DDG"
    else:
        # 영문 쿼리: DDG 직접 사용
        r = ddg_search(query, max_results=10)
        results = [x for x in r if not is_junk(x)]
        engine_label = "DDG"

    # 중복 + 개수 정리
    seen, unique = set(), []
    for r in results:
        key = r.get('href', '')[:70]
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    results = unique[:max_results]

    if not results:
        naver_url = f"https://search.naver.com/search.naver?query={query.replace(' ', '+')}"
        return (
            f"[검색 결과 없음]\n"
            f"'{query}'에 대한 결과를 찾지 못했습니다.\n"
            f"직접 검색: {naver_url}"
        )

    lines = [f"[{engine_label} 검색] '{query}' 결과 (총 {len(results)}건):\n"]
    for i, res in enumerate(results, 1):
        title = res.get('title', '제목 없음')[:70]
        body  = res.get('body',  '')[:200]
        href  = res.get('href',  '')
        lines.append(f"{i}. {title}")
        if body:
            lines.append(f"   📄 {body}")
        if href:
            lines.append(f"   🔗 {href}")
        lines.append('')

    return "\n".join(lines)

# ── 실행 진입점 ───────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python web_search.py \"검색어\"")
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    print(search(query))
