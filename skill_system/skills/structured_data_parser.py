import sys
import os
import pandas as pd

def parse_data(filepath):
    if not os.path.exists(filepath):
        print(f"오류: 파일을 찾을 수 없습니다. 경로를 확인하세요. ({filepath})")
        return
        
    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        if ext == '.csv':
            df = pd.read_csv(filepath)
        elif ext in ['.xls', '.xlsx']:
            df = pd.read_excel(filepath)
        elif ext == '.json':
            df = pd.read_json(filepath)
        else:
            print(f"지원하지 않는 데이터 포맷입니다: {ext} (지원: .csv, .xlsx, .json)")
            return
            
        print(f"[{os.path.basename(filepath)} 구조화 데이터 분석 결과]\n")
        print(f"[INFO] 데이터 차원 (행/열): {df.shape[0]} 행 x {df.shape[1]} 열")
        print(f"[INFO] 컬럼 목록: {', '.join(map(str, df.columns))}\n")
        
        print("[데이터 미리보기 (Top 10 행)]")
        # 데이터프레임을 LLM이 읽기 쉬운 Markdown 표 포맷으로 변환하여 출력
        print(df.head(10).to_markdown(index=False))
        
        if df.shape[0] > 10:
            print(f"\n... (전체 {df.shape[0]}행 중 10행만 표시됨)")
            
    except Exception as e:
        print(f"데이터 파일 분석 중 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python structured_data_parser.py \"데이터파일_절대경로\"")
        sys.exit(1)
    parse_data(sys.argv[1])
