import sys
import os
import matplotlib.pyplot as plt
import pandas as pd
from io import StringIO

def draw_chart(chart_type, title, data_str):
    try:
        # 데이터 파싱 (간단한 CSV 문자열을 DataFrame으로 변환)
        df = pd.read_csv(StringIO(data_str))
        
        plt.figure(figsize=(8, 6))
        # 한글 폰트 깨짐 방지 (윈도우 기본 폰트 맑은 고딕 사용)
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False
        
        # 차트 종류에 따른 시각화
        if chart_type == "bar":
            plt.bar(df.iloc[:, 0].astype(str), df.iloc[:, 1], color='skyblue')
        elif chart_type == "line":
            plt.plot(df.iloc[:, 0].astype(str), df.iloc[:, 1], marker='o', color='red')
        elif chart_type == "pie":
            plt.pie(df.iloc[:, 1], labels=df.iloc[:, 0].astype(str), autopct='%1.1f%%', startangle=90)
        else:
            print(f"[ERROR] 지원하지 않는 차트 형식입니다: {chart_type} (bar, line, pie 중 선택)")
            return
            
        plt.title(title)
        if chart_type != "pie":
            plt.xlabel(df.columns[0])
            plt.ylabel(df.columns[1])
        plt.tight_layout()
        
        # 엔진 루트 폴더에 이미지로 임시 저장
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        save_path = os.path.join(BASE_DIR, "output_chart.png")
        plt.savefig(save_path)
        plt.close()
        
        # 윈도우 기본 뷰어로 이미지를 비동기로 열기 (팝업)
        os.startfile(save_path)
        
        print(f"[OK] 데이터 시각화 성공! 차트가 노트북 화면에 즉시 팝업되었습니다. (파일: {save_path})")
    except Exception as e:
        print(f"[ERROR] 차트 생성 및 출력 중 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("사용법: python gui_output_engine.py [차트종류(bar/line/pie)] \"[차트제목]\" \"[CSV형식의_데이터_문자열]\"")
        print("데이터 예시: \"이름,점수\\n에이전트,90\\n자비스,80\"")
        sys.exit(1)
        
    draw_chart(sys.argv[1], sys.argv[2], sys.argv[3])
