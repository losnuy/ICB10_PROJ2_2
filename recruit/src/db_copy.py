"""
이 모듈은 기존 recruit.db에서 recruit_list와 recruit_detail 테이블만 복사하여
새로운 recruit_subset.db 파일을 생성하는 기능을 수행합니다.
"""

import os
import sqlite3

def copy_recruit_tables():
    # 상대경로 지정
    src_db_path = "recruit/data/recruit.db"
    dest_db_path = "recruit/data/recruit_subset.db"
    
    print(f"원본 데이터베이스: {src_db_path}")
    print(f"대상 데이터베이스: {dest_db_path}")
    
    # 대상 파일이 이미 존재하면 삭제
    if os.path.exists(dest_db_path):
        os.remove(dest_db_path)
        print("기존에 존재하던 대상 데이터베이스 파일을 삭제했습니다.")
        
    # sqlite3 연결 (새 파일 생성)
    conn = sqlite3.connect(dest_db_path)
    cursor = conn.cursor()
    
    try:
        # 원본 데이터베이스 연결
        cursor.execute(f"ATTACH DATABASE '{src_db_path}' AS orig")
        
        # 복사 대상 테이블 목록
        target_tables = ["recruit_list", "recruit_detail"]
        
        for table in target_tables:
            print(f"테이블 복사 중: {table}")
            
            # 1. 테이블의 CREATE SQL 가져오기
            cursor.execute(f"SELECT sql FROM orig.sqlite_master WHERE type='table' AND name='{table}'")
            create_sql = cursor.fetchone()
            
            if create_sql and create_sql[0]:
                # 새 DB에 테이블 생성
                cursor.execute(create_sql[0])
                
                # 데이터 복사
                cursor.execute(f"INSERT INTO main.{table} SELECT * FROM orig.{table}")
                print(f"  - {table} 테이블 구조 및 데이터 복사 완료")
            else:
                print(f"  - 경고: 원본에서 {table} 테이블을 찾을 수 없습니다.")
                
            # 2. 관련 인덱스의 CREATE SQL 가져오기 및 생성
            cursor.execute(f"SELECT sql FROM orig.sqlite_master WHERE type='index' AND tbl_name='{table}' AND sql IS NOT NULL")
            indexes = cursor.fetchall()
            for idx_sql in indexes:
                if idx_sql[0]:
                    cursor.execute(idx_sql[0])
                    print(f"  - {table} 관련 인덱스 생성 완료")
                    
        conn.commit()
        print("모든 복사 작업이 성공적으로 완료되었습니다.")
        
        # 검증 출력
        print("\n=== 복사된 데이터베이스 검증 ===")
        for table in target_tables:
            cursor.execute(f"SELECT COUNT(*) FROM main.{table}")
            row_count = cursor.fetchone()[0]
            print(f"테이블: {table} | 행 개수: {row_count}")
            
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        conn.rollback()
    finally:
        # DB 연결 해제
        try:
            cursor.execute("DETACH DATABASE orig")
        except sqlite3.OperationalError:
            pass
        conn.close()

if __name__ == "__main__":
    copy_recruit_tables()
