# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: web_search
# AGENT_SKILL_DESC: 인터넷에서 정보를 검색합니다. 최신 뉴스, 날씨, 가격, 일반 지식 등 실시간 정보 조회에 사용합니다. 한국어 쿼리는 한국 사이트 우선 검색합니다.
# AGENT_SKILL_ARGS: query(str) - 검색할 키워드 또는 질문, max_results(int, 선택) - 최대 결과 수 (기본 7)
# AGENT_SKILL_RETURNS: 검색 결과 요약 (제목 + 핵심 내용 + 출처 링크)
import sys
import io
import re
import warnings

warnings.filterwarnings("ignore")

# 한글 깨짐 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.StringIO()

# ── 중국어 쓰레기 판별 ─────────────────────────────────
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

# ── 한국어 쿼리 판별 ──────────────────────────────────
def is_korean(q: str) -> bool:
    return bool(re.search(r'[\uAC00-\uD7A3]', q))

# ── DDG 검색 (핵심 엔진) ──────────────────────────────
def ddg_search(query: str, max_results: int = 10) -> list:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        return []

# ── 메인 검색 함수 ────────────────────────────────────
def search(query: str, max_results: int = 7) -> str:
    korean = is_korean(query)
    results = []

    if korean:
        # 전략 1: 나무위키/한국 사이트 힌트를 붙인 쿼리로 1차 검색
        hint_query = query + " 나무위키 OR 한국 OR 네이버"
        r1 = ddg_search(hint_query, max_results=10)
        good1 = [r for r in r1 if not is_junk(r)]

        # 전략 2: 원본 쿼리로 2차 검색 후 중국어 필터
        r2 = ddg_search(query, max_results=10)
        good2 = [r for r in r2 if not is_junk(r)]

        # 전략 3: 영문으로 변환해서 보완 (선택적)
        combined = good1 + [r for r in good2 if r.get('href','') not in {x.get('href','') for x in good1}]
        results = combined
    else:
        # 영문 쿼리는 그냥 DDG 직접 사용
        r = ddg_search(query, max_results=10)
        results = [x for x in r if not is_junk(x)]

    # 중복 제거 (href 기준)
    seen, unique = set(), []
    for r in results:
        key = r.get('href', '')[:70]
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    results = unique[:max_results]

    # 결과가 없으면 힌트 없는 원본 쿼리로 재시도
    if not results and korean:
        fallback = ddg_search(query, max_results=10)
        results = fallback[:max_results]

    if not results:
        return (
            f"[검색 결과 없음]\n"
            f"'{query}'에 대한 결과를 찾지 못했습니다.\n"
            f"⚠️ 검색 엔진 일시적 제한 가능성이 있습니다.\n"
            f"직접 검색: https://search.naver.com/search.naver?query={query.replace(' ','+')}"
        )

    lines = [f"[{query}] 검색 결과 (총 {len(results)}건):\n"]
    for i, res in enumerate(results, 1):
        title   = res.get('title', '제목 없음')[:70]
        body    = res.get('body',  '')[:200]
        href    = res.get('href',  '')
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
