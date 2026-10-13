# -*- coding: utf-8 -*-
"""
browser_search.py
=================
Playwright Chromium 기반 실제 브라우저 검색 모듈.
- 네이버 검색 (한국어 쿼리) : JS 완전 렌더링, 텍스트 + 이미지 스크래핑
- 자동 헤드리스 모드로 동작 (화면 없이 백그라운드 실행)
- 다른 PC에서도 `playwright install chromium` 실행 후 사용 가능

사용법:
    python browser_search.py "검색어"
    python browser_search.py "검색어" --images   # 이미지 URL도 포함
    python browser_search.py "검색어" --screenshot  # 스크린샷 저장
"""
import sys
import io
import os
import re
import json
import warnings
import argparse

warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.StringIO()

# ── Playwright 가용 여부 확인 ─────────────────────────
def check_playwright() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False

# ── 네이버 브라우저 검색 ──────────────────────────────
def naver_browser_search(query: str, max_results: int = 7,
                          with_images: bool = False,
                          screenshot_path: str = None) -> dict:
    """
    Playwright Chromium으로 네이버 검색을 수행합니다.
    Returns: {"results": [...], "images": [...], "screenshot": path_or_None}
    """
    from playwright.sync_api import sync_playwright
    import urllib.parse

    results = []
    images  = []
    shot    = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/124.0.0.0 Safari/537.36',
            ]
        )
        ctx = browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            viewport={'width': 1280, 'height': 900},
        )
        page = ctx.new_page()

        # 봇 감지 우회: navigator.webdriver 속성 제거
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US']});
        """)

        try:
            url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}&where=web"
            page.goto(url, timeout=15000, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)  # JS 렌더링 대기

            # 스크린샷 저장 (옵션)
            if screenshot_path:
                os.makedirs(os.path.dirname(screenshot_path) or '.', exist_ok=True)
                page.screenshot(path=screenshot_path, full_page=False)
                shot = screenshot_path

            # ── 텍스트 결과 파싱 ──────────────────────
            # 네이버 웹 검색 결과 셀렉터 (2024~2025 기준)
            selectors = [
                '.total_wrap .bx',       # 일반 웹 결과
                '.sp_nkeyword .bx',      # 키워드 블록
                'li.bx',                 # 리스트 결과
                '.api_subject_bx',       # API 결과
                '[class*="news_area"]',  # 뉴스 결과
            ]

            raw_items = []
            for sel in selectors:
                items = page.query_selector_all(sel)
                if items:
                    raw_items.extend(items)
                if len(raw_items) >= max_results * 2:
                    break

            seen_titles = set()
            for item in raw_items:
                try:
                    # 제목
                    title_el = (item.query_selector('.title_area a') or
                                item.query_selector('.link_tit') or
                                item.query_selector('a.title') or
                                item.query_selector('h3 a') or
                                item.query_selector('a[href^="http"]'))

                    title = title_el.inner_text().strip() if title_el else ''
                    href  = title_el.get_attribute('href') if title_el else ''

                    # 설명
                    desc_el = (item.query_selector('.dsc_area') or
                               item.query_selector('.total_dsc') or
                               item.query_selector('.desc') or
                               item.query_selector('.api_txt_lines') or
                               item.query_selector('[class*="desc"]') or
                               item.query_selector('[class*="summary"]') or
                               item.query_selector('[class*="contents"]'))
                    # 설명이 없으면 item 전체 텍스트 일부 사용
                    if desc_el:
                        desc = desc_el.inner_text().strip()[:200]
                    else:
                        full_text = item.inner_text().strip()
                        # 제목 이후 텍스트만 사용
                        desc = full_text.replace(title, '').strip()[:200]

                    if not title or len(title) < 3 or title in seen_titles:
                        continue
                    if not href or 'javascript:' in href:
                        continue

                    seen_titles.add(title)
                    results.append({'title': title, 'body': desc, 'href': href})
                    if len(results) >= max_results:
                        break
                except Exception:
                    continue

            # 결과가 부족하면 전체 텍스트에서 링크 추출 (Fallback)
            if len(results) < 3:
                anchors = page.query_selector_all('#main_pack a[href^="http"]')
                for a in anchors:
                    try:
                        text = a.inner_text().strip()
                        href = a.get_attribute('href')
                        if len(text) > 5 and text not in seen_titles and href:
                            seen_titles.add(text)
                            results.append({'title': text, 'body': '', 'href': href})
                        if len(results) >= max_results:
                            break
                    except Exception:
                        continue

            # ── 이미지 결과 파싱 (옵션) ───────────────
            if with_images:
                img_url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}&where=image"
                page.goto(img_url, timeout=10000, wait_until='domcontentloaded')
                page.wait_for_timeout(1500)

                img_els = page.query_selector_all('img[src^="http"]')
                for img in img_els:
                    src = img.get_attribute('src') or ''
                    alt = img.get_attribute('alt') or ''
                    if src and 'naver' in src and src not in images:
                        images.append({'url': src, 'alt': alt})
                    if len(images) >= 5:
                        break

        except Exception as e:
            results.append({'title': f'[오류] {e}', 'body': '', 'href': ''})
        finally:
            browser.close()

    return {'results': results, 'images': images, 'screenshot': shot}


# ── 결과 포맷팅 ───────────────────────────────────────
def format_results(query: str, data: dict) -> str:
    results   = data.get('results', [])
    images    = data.get('images', [])
    shot      = data.get('screenshot')

    if not results:
        return (f"[브라우저 검색 결과 없음]\n'{query}'에 대한 결과를 찾지 못했습니다.")

    lines = [f"[브라우저 검색] '{query}' 결과 (총 {len(results)}건):\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.get('title','')[:70]}")
        if r.get('body'):
            lines.append(f"   📄 {r['body'][:180]}")
        if r.get('href'):
            lines.append(f"   🔗 {r['href'][:100]}")
        lines.append('')

    if images:
        lines.append(f"[이미지 결과 {len(images)}건]")
        for img in images:
            lines.append(f"  🖼  {img.get('url','')[:120]}")
            if img.get('alt'):
                lines.append(f"      alt: {img['alt'][:60]}")
        lines.append('')

    if shot:
        lines.append(f"[스크린샷 저장됨] {shot}")

    return "\n".join(lines)


# ── CLI 진입점 ────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Playwright 브라우저 검색')
    parser.add_argument('query', nargs='+', help='검색어')
    parser.add_argument('--images', action='store_true', help='이미지 결과 포함')
    parser.add_argument('--screenshot', type=str, default=None,
                        help='스크린샷 저장 경로 (예: logs/search_shot.png)')
    parser.add_argument('--max', type=int, default=7, help='최대 결과 수')
    args = parser.parse_args()

    query = ' '.join(args.query)

    if not check_playwright():
        print("[오류] playwright 패키지가 없습니다.")
        print("  pip install playwright")
        print("  python -m playwright install chromium")
        sys.exit(1)

    data = naver_browser_search(
        query,
        max_results=args.max,
        with_images=args.images,
        screenshot_path=args.screenshot
    )
    print(format_results(query, data))


if __name__ == '__main__':
    main()
