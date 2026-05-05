# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: image_ocr_enhanced
# AGENT_SKILL_DESC: 이미지에서 텍스트를 추출합니다. 영수증 이미지는 금액을 자동 합산합니다. pytesseract + Pillow 필요.
# AGENT_SKILL_ARGS: image_path(str) - 이미지 파일 경로, mode(str) - "text"(기본) 또는 "receipt"(영수증 모드)
# AGENT_SKILL_RETURNS: 추출된 텍스트 및 영수증 모드 시 금액 합계
import sys
import os
import re

def check_dependencies():
    missing = []
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow (pip install Pillow)")
    try:
        import pytesseract
    except ImportError:
        missing.append("pytesseract (pip install pytesseract)")
    return missing

def extract_text(image_path: str) -> str:
    """이미지에서 텍스트 추출"""
    from PIL import Image
    import pytesseract

    # Tesseract 경로 (Windows 기본 설치 위치)
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break

    img = Image.open(image_path)
    # 한국어 + 영어 OCR
    text = pytesseract.image_to_string(img, lang="kor+eng")
    return text.strip()

def parse_receipt(text: str) -> dict:
    """영수증 텍스트에서 금액 파싱 및 합산"""
    # 숫자 패턴: 1,000 / 10000 / 1.000 형식
    price_pattern = re.compile(r'(\d{1,3}(?:[,\.]\d{3})+|\d{4,})')
    prices = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        matches = price_pattern.findall(line)
        for m in matches:
            val = int(m.replace(',', '').replace('.', ''))
            # 합리적인 금액 범위만 포함 (100원 ~ 1,000,000원)
            if 100 <= val <= 1_000_000:
                prices.append((line[:30], val))

    total = sum(v for _, v in prices)
    return {"items": prices, "total": total}

def run(image_path: str, mode: str = "text") -> str:
    missing = check_dependencies()
    if missing:
        return (
            "❌ 필요한 패키지가 없습니다:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\n또한 Tesseract OCR 엔진을 설치해야 합니다:\n"
            "  https://github.com/tesseract-ocr/tesseract/releases\n"
            "  (Windows 설치 파일 다운로드 후 기본 경로에 설치)"
        )

    if not os.path.exists(image_path):
        return f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}"

    valid_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    if os.path.splitext(image_path)[1].lower() not in valid_exts:
        return f"❌ 지원하지 않는 파일 형식입니다. 지원: {', '.join(valid_exts)}"

    try:
        text = extract_text(image_path)

        if not text:
            return "⚠️ 텍스트를 인식하지 못했습니다. 이미지 해상도를 높여서 다시 시도해보세요."

        if mode == "receipt":
            receipt = parse_receipt(text)
            items_str = "\n".join(
                f"  {line[:20]:20s}  {val:>8,}원"
                for line, val in receipt["items"][:15]
            )
            result = (
                f"🧾 영수증 OCR 결과\n\n"
                f"{'='*35}\n"
                f"📝 원본 텍스트:\n{text[:500]}\n\n"
                f"{'='*35}\n"
                f"💰 감지된 금액:\n{items_str if items_str else '  금액 없음'}\n\n"
                f"{'='*35}\n"
                f"💵 합계 추정: {receipt['total']:,}원\n"
                f"(자동 파싱이므로 실제 합계와 다를 수 있습니다)"
            )
        else:
            result = (
                f"🖼️ OCR 텍스트 추출 결과\n"
                f"파일: {os.path.basename(image_path)}\n"
                f"{'='*35}\n"
                f"{text[:2000]}"
            )
            if len(text) > 2000:
                result += f"\n\n... ({len(text)-2000}자 더 있음)"

        return result

    except Exception as e:
        return f"❌ OCR 처리 오류: {e}"

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("사용법: python image_ocr_enhanced.py <이미지경로> [text|receipt]")
        print("예시:  python image_ocr_enhanced.py receipt.jpg receipt")
        sys.exit(1)

    image_path = args[0]
    mode = args[1] if len(args) > 1 else "text"
    print(run(image_path, mode))
