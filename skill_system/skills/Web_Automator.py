# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Web_Automator
# AGENT_SKILL_DESC: 실제 웹 브라우저(Playwright Chromium)로 URL에 접속하여 텍스트, 링크, 이미지를 스크래핑합니다. JS가 필요한 동적 사이트도 완전히 읽을 수 있습니다.
# AGENT_SKILL_ARGS: url(str) - 접속할 URL, action(str, 선택) - scrape/screenshot/click/type
# AGENT_SKILL_RETURNS: 페이지 텍스트, 링크 목록, 이미지 URL, 스크린샷 경로
"""
Web_Automator 스킬
==================
Playwright Chromium 기반 실제 브라우저 자동화.

지원 액션:
  scrape     : 텍스트 + 링크 + 이미지 스크래핑 (기본)
  screenshot : 페이지 스크린샷 저장
  search     : URL에 접속 후 키워드 검색

사용법:
  python Web_Automator.py "https://namu.wiki/w/라면" scrape
  python Web_Automator.py "https://namu.wiki/w/라면" screenshot
"""
import sys
import io
import os
import re
import warnings

warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.StringIO()

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '..', '..', 'logs', 'screenshots')

# ── 브라우저 컨텍스트 생성 헬퍼 ──────────────────────
def make_browser():
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
        ]
    )
    ctx = browser.new_context(
        locale='ko-KR',
        timezone_id='Asia/Seoul',
        viewport={'width': 1280, 'height': 900},
        user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    )
    page = ctx.new_page()
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko']});
    """)
    return p, browser, page

# ── 페이지 스크래핑 ───────────────────────────────────
def scrape_page(url: str, max_text: int = 2000, max_links: int = 10, max_images: int = 5) -> str:
    p, browser, page = make_browser()
    try:
        page.goto(url, timeout=20000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)

        # 텍스트 추출 (스크립트/스타일 제외)
        text = page.evaluate("""() => {
            const els = document.querySelectorAll('script, style, noscript, nav, footer, header');
            els.forEach(el => el.remove());
            return document.body ? document.body.innerText : '';
        }""")
        text = re.sub(r'\n{3,}', '\n\n', text).strip()[:max_text]

        # 링크 추출
        links_raw = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]'))
                .filter(a => a.href.startsWith('http'))
                .map(a => ({text: a.innerText.trim().substring(0, 60), href: a.href}))
                .filter(a => a.text.length > 2)
                .slice(0, 20);
        }""")
        links = links_raw[:max_links]

        # 이미지 추출
        imgs_raw = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img[src]'))
                .map(img => ({src: img.src, alt: img.alt || ''}))
                .filter(img => img.src.startsWith('http') && !img.src.includes('icon'))
                .slice(0, 10);
        }""")
        imgs = imgs_raw[:max_images]

        lines = [f"[{url}] 페이지 스크래핑 결과\n"]
        lines.append("=== 텍스트 ===")
        lines.append(text if text else "(텍스트 없음)")
        lines.append("")

        if links:
            lines.append(f"=== 링크 ({len(links)}개) ===")
            for lk in links:
                lines.append(f"  - {lk['text']} -> {lk['href']}")
            lines.append("")

        if imgs:
            lines.append(f"=== 이미지 ({len(imgs)}개) ===")
            for img in imgs:
                lines.append(f"  🖼  {img['src']}")
                if img['alt']:
                    lines.append(f"      ({img['alt'][:50]})")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"[오류] 페이지 스크래핑 실패: {e}"
    finally:
        browser.close()
        p.stop()

# ── 스크린샷 ──────────────────────────────────────────
def take_screenshot(url: str) -> str:
    p, browser, page = make_browser()
    try:
        page.goto(url, timeout=20000, wait_until='domcontentloaded')
        page.wait_for_timeout(1500)

        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        import time
        fname = f"screenshot_{int(time.time())}.png"
        fpath = os.path.join(SCREENSHOT_DIR, fname)
        page.screenshot(path=fpath, full_page=True)

        return f"[스크린샷 저장됨]\n경로: {fpath}\nURL: {url}"
    except Exception as e:
        return f"[오류] 스크린샷 실패: {e}"
    finally:
        browser.close()
        p.stop()

# ── 실행 진입점 ───────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("사용법: Web_Automator.py <URL> [액션: scrape|screenshot]")
        print("  예시: Web_Automator.py https://namu.wiki/w/라면 scrape")
        sys.exit(1)

    url    = sys.argv[1]
    action = sys.argv[2].lower() if len(sys.argv) > 2 else 'scrape'

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[오류] playwright 미설치.")
        print("  pip install playwright")
        print("  python -m playwright install chromium")
        sys.exit(1)

    if action == 'screenshot':
        print(take_screenshot(url))
    else:
        print(scrape_page(url))

if __name__ == '__main__':
    main()
