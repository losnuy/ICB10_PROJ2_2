"""
이 모듈은 SQLite 데이터베이스에 수집된 trip.com 리뷰 데이터를 
사용자가 바로 열람할 수 있도록 Excel(.xlsx) 및 CSV 형식으로 변환하여 내보내는 스크립트입니다.

주요 기능:
- SQLite DB(trip_reviews.db)에서 수집된 리뷰 데이터 조회
- pandas 라이브러리를 활용해 DataFrame으로 변환
- 데이터를 CSV 및 Excel 형식으로 변환하여 trip_com/report 폴더에 저장
"""

import os
import sqlite3
import pandas as pd

# DB 및 내보낼 파일 경로 설정 (상대경로 적용)
DB_PATH = "trip_com/data/trip_reviews.db"
EXPORT_DIR = "trip_com/report"
CSV_PATH = os.path.join(EXPORT_DIR, "trip_reviews.csv")
EXCEL_PATH = os.path.join(EXPORT_DIR, "trip_reviews.xlsx")

def main():
    import sys
    # 윈도우 인코딩 에러 방지
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    if not os.path.exists(DB_PATH):
        print(f"오류: 데이터베이스 파일({DB_PATH})이 존재하지 않습니다. 먼저 수집을 완료해 주세요.")
        return

    print("SQLite DB에서 데이터를 읽어오는 중...")
    try:
        # DB 연결 및 데이터 조회
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM reviews ORDER BY create_date DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            print("데이터베이스에 저장된 리뷰가 없습니다.")
            return

        print(f"조회 성공: 총 {len(df)}개의 리뷰 데이터를 로드했습니다.")

        # 내보낼 폴더 생성
        os.makedirs(EXPORT_DIR, exist_ok=True)

        # 1. CSV 형식으로 내보내기 (UTF-8-BOM 인코딩으로 저장하여 엑셀에서 바로 열 때 한글 깨짐 방지)
        print("CSV 파일로 내보내는 중...")
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"CSV 파일 저장 완료: {CSV_PATH}")

        # 2. Excel 형식으로 내보내기
        print("Excel 파일로 내보내는 중...")
        try:
            df.to_excel(EXCEL_PATH, index=False)
            print(f"Excel 파일 저장 완료: {EXCEL_PATH}")
        except ModuleNotFoundError:
            print("\n[알림] openpyxl 패키지가 설치되지 않아 Excel(.xlsx) 내보내기를 건너뜁니다.")
            print("Excel 형식으로도 변환하려면 'uv pip install openpyxl'을 실행한 후 다시 시도해 주세요.")
            print("하지만 생성된 CSV 파일(utf-8-sig) 역시 엑셀에서 바로 정상적으로 열람하실 수 있습니다.")
            
    except Exception as e:
        print(f"데이터 변환 및 내보내기 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
