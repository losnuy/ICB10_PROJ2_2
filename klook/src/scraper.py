"""
이 모듈은 Klook 검색 API를 활용하여 '대한민국' 검색어에 대한 상품 정보를 SQLite DB에 저장하는 스크래퍼입니다.

주요 기능:
- Klook 검색 API에 대해 페이징 처리를 하여 전체 수집을 수행합니다.
- API 서버 부하를 고려하되 요청 간 0.1초~1.0초 사이의 지연 시간(Sleep)을 적용합니다.
- HTTP 요청 에러 시 최대 3회까지 재시도하는 예외 처리를 수행합니다.
- 매 페이지 크롤링 완료 시점에 수집된 데이터를 SQLite DB에 즉시 적재(Commit)합니다.
- 수집된 모든 칼럼을 유실 없이 반영하기 위해 SQLite 테이블 스키마를 동적으로 확장(ALTER TABLE)하는 동기화 로직을 포함합니다.
- 제품 상세 링크인 'deep_link' 정보를 필수로 포함하여 저장합니다.
"""

import os
import time
import json
import random
import sqlite3
import urllib.parse
import requests
import pandas as pd

def clean_float(value):
    """
    평점 등 실수값을 파싱하여 float 형태로 반환합니다.
    """
    if value is None:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0

def save_page_to_db(df, db_path, table_name="klook_products"):
    """
    데이터프레임을 SQLite DB 테이블에 페이지 단위로 적재합니다.
    DB 테이블 스키마에 존재하지 않는 컬럼이 발견되면 동적으로 추가합니다.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 테이블 존재 여부 확인
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            # 최초 적재 시 테이블 생성 및 데이터 적재
            df.to_sql(table_name, conn, index=False, if_exists="fail")
        else:
            # 기존 테이블의 컬럼 정보 조회
            cursor.execute(f"PRAGMA table_info({table_name});")
            db_cols = [row[1] for row in cursor.fetchall()]
            
            # 데이터프레임에만 존재하고 DB 테이블에는 없는 새 컬럼이 있으면 ALTER TABLE로 추가
            for col in df.columns:
                if col not in db_cols:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN [{col}] TEXT;")
            
            # 변경된 스키마 정보 재조회
            cursor.execute(f"PRAGMA table_info({table_name});")
            updated_db_cols = [row[1] for row in cursor.fetchall()]
            
            # DB에는 있지만 현재 데이터프레임에는 없는 컬럼은 None으로 보완
            for col in updated_db_cols:
                if col not in df.columns:
                    df[col] = None
            
            # 컬럼 순서를 DB 컬럼 구조와 일치시킨 후 적재
            df_reordered = df[updated_db_cols]
            df_reordered.to_sql(table_name, conn, index=False, if_exists="append")
            
        conn.commit()
    except Exception as e:
        print(f"[에러] DB 저장 중 에러 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

def scrape_klook_data():
    """
    Klook 검색 API를 순회하며 상품 데이터를 수집하여 SQLite DB에 페이지 단위로 실시간 저장하는 메인 함수입니다.
    """
    # 봇 차단을 우회하기 위해 HTTP 세션을 설정하고 헤더를 주입합니다.
    session = requests.Session()
    
    # 기본 검색 요청 URL 템플릿
    base_url = "https://www.klook.com/v1/cardinfocenterservicesrv/search/platform/complete_search_v3"
    
    # 검색 검색어: 대한민국 (URL 인코딩: %EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD)
    query = "대한민국"
    
    # DB 저장 경로 설정
    db_dir = os.path.join("klook", "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "klook_products.db")
    table_name = "klook_products"
    
    # 기존 DB가 있다면 백업하거나 제거하여 깨끗한 데이터 수집을 유도 (사용자 명시적 DB 수집 요구 대응)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"[정보] 기존 데이터베이스 파일을 삭제하고 새로 수집을 시작합니다: {db_path}")
        except Exception as e:
            print(f"[경고] 기존 데이터베이스 파일 삭제 실패: {e}")
            
    page = 1
    max_retries = 3
    total_inserted = 0
    
    print("[정보] Klook 상품 데이터 SQLite 수집을 시작합니다. (페이지 단위 실시간 커밋 및 0.1~1초 지연 적용)")
    
    while True:
        # 페이지마다 Referer와 파라미터가 유동적으로 변하므로 요청 전에 구성합니다.
        referer_url = f"https://www.klook.com/ko/search/result/?query={urllib.parse.quote(query)}&search_scope=main_search&sort=most_relevant&tab_key=0&start={page}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Referer": referer_url,
            "x-platform": "desktop",
            "x-requested-with": "XMLHttpRequest",
            "x-klook-market": "global",
            "x-klook-user-residence": "10_KR"
        }
        
        params = {
            "sort": "most_relevant",
            "tab_key": "0",
            "start": str(page),
            "query": query,
            "size": "15",
            "search_scope": "main_search",
            "k_lang": "ko_KR",
            "k_currency": "KRW"
        }
        
        success = False
        for retry in range(max_retries):
            try:
                res = session.get(base_url, headers=headers, params=params, timeout=15)
                if res.status_code == 200:
                    response_json = res.json()
                    if response_json.get("success"):
                        success = True
                        break
                    else:
                        print(f"[경고] API 응답 success 필드가 False입니다. (시도 {retry + 1}/{max_retries})")
                else:
                    print(f"[경고] HTTP 상태 코드 에러: {res.status_code} (시도 {retry + 1}/{max_retries})")
            except Exception as e:
                print(f"[에러] HTTP 요청 에러 발생: {e} (시도 {retry + 1}/{max_retries})")
            
            # 재시도 전 대기 시간 증가
            time.sleep(2.0 * (retry + 1))
            
        if not success:
            print(f"[에러] {page} 페이지 수집 실패. 재시도 횟수를 초과하여 스크래핑을 중단합니다.")
            break
            
        # 데이터 파싱
        result_data = response_json.get("result", {})
        search_result = result_data.get("search_result", {})
        cards = search_result.get("cards", [])
        total_count = search_result.get("total", 0)
        
        if not cards:
            print(f"[정보] {page} 페이지에서 수집된 상품이 없습니다. 수집을 완료합니다.")
            break
            
        page_cards = []
        for card in cards:
            card_data = card.get("data")
            if not card_data:
                continue
                
            # 1. card_data의 모든 키-값 쌍을 수집
            row_data = {}
            for key, val in card_data.items():
                if isinstance(val, (dict, list)):
                    # 중첩된 dict나 list는 유실 방지를 위해 JSON 문자열로 직렬화하여 저장
                    row_data[key] = json.dumps(val, ensure_ascii=False)
                else:
                    row_data[key] = val
            
            # 2. 주요 파생 필드를 별도의 단일 칼럼으로 추가로 추출하여 덧붙입니다. (제품 링크 deep_link가 정상 저장되는지 확인)
            price_obj = card_data.get("price", {})
            row_data["derived_selling_price"] = price_obj.get("selling_price", "") if isinstance(price_obj, dict) else ""
            row_data["derived_market_price"] = price_obj.get("market_price", "") if isinstance(price_obj, dict) else ""
            
            review_obj = card_data.get("review_obj", {})
            if isinstance(review_obj, dict):
                row_data["derived_rating"] = clean_float(review_obj.get("star"))
                row_data["derived_review_count"] = review_obj.get("count", "")
                row_data["derived_booked_count"] = review_obj.get("booked", "")
            else:
                row_data["derived_rating"] = 0.0
                row_data["derived_review_count"] = ""
                row_data["derived_booked_count"] = ""
                
            page_cards.append(row_data)
            
        # 페이지 단위로 수집된 데이터를 즉시 DB에 적재 및 Commit
        if page_cards:
            df_page = pd.DataFrame(page_cards)
            save_page_to_db(df_page, db_path, table_name)
            total_inserted += len(page_cards)
            print(f"[정보] {page} 페이지 {len(page_cards)}개 상품 SQLite 적재 완료 (누적: {total_inserted} / 전체 예측: {total_count})")
            
        # 다음 페이지로 이동
        page += 1
        
        # 페이지별 0.1~1초 지연 설정
        delay = random.uniform(0.1, 1.0)
        time.sleep(delay)
        
    print(f"[성공] 총 {total_inserted}개의 상품 정보를 SQLite DB에 페이지 단위로 적재 성공했습니다: {db_path}")
    
    # SQLite DB 데이터를 읽어 CSV 파일로도 저장 (동시 저장 요구사항 반영)
    if total_inserted > 0:
        try:
            conn = sqlite3.connect(db_path)
            df_all = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
            
            csv_path = os.path.join(db_dir, "klook_search_results.csv")
            df_all.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"[성공] 수집 완료된 데이터를 CSV 파일로도 저장했습니다: {csv_path}")
        except Exception as e:
            print(f"[경고] CSV 파일 동시 저장 중 오류 발생: {e}")
            
    return db_path

if __name__ == "__main__":
    scrape_klook_data()


