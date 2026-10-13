# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: pdf_reader
# AGENT_SKILL_DESC: PDF 파일을 읽어 텍스트를 추출하고 내용 요약을 반환합니다. pdfplumber 패키지 필요.
# AGENT_SKILL_ARGS: file_path(str) - PDF 파일의 절대 경로, pages(str) - 읽을 페이지 범위 (예: "1-3", 기본값: "all")
# AGENT_SKILL_RETURNS: 추출된 텍스트 및 문서 정보
import sys
import os

def check_dependency():
    try:
        import pdfplumber
        return True, pdfplumber
    except ImportError:
        return False, None

def read_pdf(file_path: str, pages: str = "all") -> str:
    ok, pdfplumber = check_dependency()
    if not ok:
        return (
            "❌ pdfplumber 패키지가 없습니다.\n"
            "설치 명령: pip install pdfplumber\n"
            "또는 대시보드에서 Dependency_Manager 스킬로 설치 요청하세요."
        )

    if not os.path.exists(file_path):
        return f"❌ 파일을 찾을 수 없습니다: {file_path}"

    if not file_path.lower().endswith('.pdf'):
        return f"❌ PDF 파일이 아닙니다: {file_path}"

    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)

            # 페이지 범위 파싱
            if pages == "all":
                page_indices = list(range(total_pages))
            elif "-" in pages:
                start, end = pages.split("-")
                page_indices = list(range(int(start)-1, min(int(end), total_pages)))
            else:
                page_indices = [int(pages) - 1]

            extracted = []
            for i in page_indices:
                if 0 <= i < total_pages:
                    text = pdf.pages[i].extract_text()
                    if text:
                        extracted.append(f"--- 페이지 {i+1} ---\n{text.strip()}")

            full_text = "\n\n".join(extracted)
            word_count = len(full_text.replace("\n", " ").split())

            result = (
                f"📄 PDF 분석 완료: {os.path.basename(file_path)}\n"
                f"📑 전체 페이지: {total_pages}페이지\n"
                f"📖 추출된 페이지: {len(page_indices)}페이지\n"
                f"📝 단어 수: 약 {word_count:,}개\n\n"
                f"{'='*40}\n"
                f"{full_text[:3000]}"
            )
            if len(full_text) > 3000:
                result += f"\n\n... (이하 {len(full_text)-3000}자 생략. 특정 페이지를 지정하면 더 볼 수 있습니다.)"
            return result

    except Exception as e:
        return f"❌ PDF 읽기 오류: {e}"

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("사용법: python pdf_reader.py <파일경로> [페이지범위]")
        print("예시:  python pdf_reader.py C:/documents/report.pdf 1-5")
        sys.exit(1)

    file_path = args[0]
    pages = args[1] if len(args) > 1 else "all"
    print(read_pdf(file_path, pages))
