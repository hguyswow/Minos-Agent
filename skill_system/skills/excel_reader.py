# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: excel_reader
# AGENT_SKILL_DESC: 엑셀(.xlsx, .xls) 또는 CSV 파일을 읽어 내용을 텍스트로 반환합니다.
# AGENT_SKILL_ARGS: file_path(str) - 읽을 파일 경로, sheet(str) - 시트명(선택)
# AGENT_SKILL_RETURNS: 파일 내용 (테이블 형식)
#
# excel_reader: 엑셀(.xlsx, .xls) 또는 CSV 파일 경로를 받아 내용을 요약하여 반환합니다.
# 사용 예: <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\excel_reader.py "C:\path\to\file.xlsx"</CMD>
#
import sys
import io
import warnings
warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os

def read_file(path: str, max_rows: int = 50) -> str:
    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == '.csv':
            import csv
            rows = []
            # 인코딩 자동 감지 (utf-8-sig → utf-8 → cp949 순)
            for enc in ['utf-8-sig', 'utf-8', 'cp949']:
                try:
                    with open(path, 'r', encoding=enc, newline='') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                    break
                except (UnicodeDecodeError, FileNotFoundError):
                    continue
            if not rows:
                return "[excel_reader] CSV를 읽을 수 없습니다. 인코딩을 확인하세요."
        elif ext in ['.xlsx', '.xls']:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
                ws = wb.active
                rows = []
                for row in ws.iter_rows(values_only=True):
                    rows.append([str(c) if c is not None else '' for c in row])
            except ImportError:
                return "[excel_reader] openpyxl이 설치되어 있지 않습니다. pip install openpyxl 을 실행하세요."
        else:
            return f"[excel_reader] 지원하지 않는 파일 형식입니다: {ext} (csv, xlsx, xls 만 지원)"

        if not rows:
            return "[excel_reader] 파일이 비어있습니다."

        total_rows = len(rows)
        display_rows = rows[:max_rows]

        output_lines = [f"[파일: {os.path.basename(path)}] 총 {total_rows}행"]
        output_lines.append(f"(최대 {max_rows}행 표시)\n")

        for i, row in enumerate(display_rows):
            output_lines.append(f"행{i+1}: {' | '.join(str(c) for c in row)}")

        if total_rows > max_rows:
            output_lines.append(f"\n...이하 {total_rows - max_rows}행 생략")

        return '\n'.join(output_lines)

    except FileNotFoundError:
        return f"[excel_reader] 파일을 찾을 수 없습니다: {path}"
    except Exception as e:
        return f"[excel_reader] 오류: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python excel_reader.py \"C:\\path\\to\\file.xlsx\"")
        sys.exit(1)
    result = read_file(sys.argv[1])
    print(result)
