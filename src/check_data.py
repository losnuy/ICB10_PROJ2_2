"""
이 스크립트는 EDA 분석 대상 파일들의 초기 스키마와 데이터를 검토하기 위한 임시 스크립트입니다.
대상 파일:
- saramin/data/saramin_search_jobs.db
- saramin/data/saramin_turnover_datamart.csv
- naver-api-app/data/naver_dataanalysis.csv
"""

import sys
import pandas as pd
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

def check_db():
    print("=== saramin_search_jobs.db 검토 ===")
    conn = sqlite3.connect("saramin/data/saramin_search_jobs.db")
    # 테이블 목록 조회
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("테이블 목록:", tables)
    
    for table_name_tup in tables:
        table_name = table_name_tup[0]
        print(f"\n[테이블: {table_name}]")
        df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 5", conn)
        print("Columns:", df.columns.tolist())
        print(df.head(2))
        
        # 총 row 수 확인
        cursor.execute(f"SELECT count(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        print(f"총 행 수: {row_count}")
    conn.close()

def check_csv_turnover():
    print("\n=== saramin_turnover_datamart.csv 검토 ===")
    df = pd.read_csv("saramin/data/saramin_turnover_datamart.csv")
    print(f"Shape: {df.shape}")
    print("Columns:", df.columns.tolist())
    print(df.head(2))
    print("Info:")
    print(df.info())

def check_csv_naver():
    print("\n=== naver_dataanalysis.csv 검토 ===")
    df = pd.read_csv("naver-api-app/data/naver_dataanalysis.csv")
    print(f"Shape: {df.shape}")
    print("Columns:", df.columns.tolist())
    print(df.head(2))
    print("Info:")
    print(df.info())

if __name__ == "__main__":
    check_db()
    check_csv_turnover()
    check_csv_naver()
