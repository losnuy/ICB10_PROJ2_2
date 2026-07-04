"""
이 모듈은 네이버 데이터랩 검색어 트렌드 API를 호출하여 
구직자의 관심 스펙 검색 추이 데이터를 수집하고, 이를 SQLite 데이터베이스에 적재하는 수집 배치 스크립트입니다.

주요 기능:
- .env 환경 변수 파일로부터 Client ID 및 Client Secret 로드
- 회계 직무 관련 5대 핵심 검색어 그룹(주제어 및 포함 키워드) 정의
- 네이버 데이터랩 API 통신 및 예외 처리 (API Rate Limit 대기 및 재시도)
- recruit.db 내 naver_search_trend 테이블 생성 및 Upsert (중복 제거 적재)
- 향후 다중 직무 확장을 고려한 job_category 파라미터 구조 지원
"""

import os
import sqlite3
import time
from datetime import datetime, timedelta
import dotenv
from api_client import NaverApiClient

# 환경변수 및 DB 경로를 절대경로로 보정 (실행 Cwd에 영향받지 않도록 조치)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", ".env"))
dotenv.load_dotenv(DOTENV_PATH)

DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "recruit", "data", "recruit.db"))
NAVER_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "naver_trend.db"))


def initialize_db():
    """
    naver_search_trend, trend_keyword_mapping, keyword_search_volume 테이블을 두 SQLite 데이터베이스 파일에 각각 생성합니다.
    """
    for db_file in [DB_PATH, NAVER_DB_PATH]:
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 1. 통합 검색어 트렌드 비율 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS naver_search_trend (
                period TEXT NOT NULL,
                group_name TEXT NOT NULL,
                ratio REAL NOT NULL,
                job_category TEXT NOT NULL,
                PRIMARY KEY (period, group_name, job_category)
            );
        """)
        
        # 2. 키워드 그룹 세부 키워드 매핑 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_keyword_mapping (
                group_name TEXT NOT NULL,
                keyword TEXT NOT NULL,
                job_category TEXT NOT NULL,
                PRIMARY KEY (group_name, keyword, job_category)
            );
        """)
        
        # 3. 세부 키워드별 네이버 검색광고 월간 절대 검색수 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keyword_search_volume (
                keyword TEXT NOT NULL,
                monthly_pc_queries INTEGER NOT NULL,
                monthly_mobile_queries INTEGER NOT NULL,
                monthly_total_queries INTEGER NOT NULL,
                job_category TEXT NOT NULL,
                PRIMARY KEY (keyword, job_category)
            );
        """)
        conn.commit()
        conn.close()
    print("[DB] recruit.db 및 naver_trend.db 테이블 및 매핑 스키마 초기화 완료.")


def collect_naver_trends(job_category="accounting"):
    """
    네이버 데이터랩 API를 호출하여 최근 1년간의 직무 관련 검색어 트렌드 데이터를 수집하고 DB에 적재합니다.
    """
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("[오류] NAVER API 키 정보가 .env 파일에 누락되어 있습니다. 수집을 스킵합니다.")
        return

    # API 클라이언트 인스턴스 생성
    client = NaverApiClient(client_id, client_secret)

    # 1개년 수집 기간 정의
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    # 직무별 수집 키워드 그룹 정의 (도메인 특화어는 단독 수집, 범용어는 결합 수집하는 하이브리드 필터링 적용)
    if job_category == "accounting":
        keyword_groups = [
            {
                "groupName": "전산세무회계",
                "keywords": ["전산회계", "전산세무"]
            },
            {
                "groupName": "전문자격증",
                "keywords": ["CPA", "세무사", "공인회계사", "CTA"]
            },
            {
                "groupName": "재경관리사",
                "keywords": ["재경관리사", "회계관리"]
            },
            {
                "groupName": "ERP/실무 툴",
                "keywords": ["회계 더존", "경리 더존", "회계 SAP"]
            },
            {
                "groupName": "사무/컴활",
                "keywords": ["회계 컴활", "경리 컴활", "회계 엑셀", "경리 엑셀"]
            }
        ]
    elif job_category == "it_dev":
        keyword_groups = [
            {
                "groupName": "형상관리/기본",
                "keywords": ["개발자 Git", "개발 Git", "정보처리기사"]
            },
            {
                "groupName": "프론트엔드",
                "keywords": ["React 개발", "Vue 개발", "프론트엔드"]
            },
            {
                "groupName": "백엔드 프레임워크",
                "keywords": ["Spring Boot", "FastAPI"]
            },
            {
                "groupName": "인프라/DevOps",
                "keywords": ["Docker", "Kubernetes"]
            },
            {
                "groupName": "테스트/설계",
                "keywords": ["TDD", "DB 설계", "데이터베이스 설계"]
            }
        ]
    else: # marketing
        keyword_groups = [
            {
                "groupName": "디자인/오피스",
                "keywords": ["마케팅 포토샵", "마케터 포토샵", "피그마"]
            },
            {
                "groupName": "로그 분석",
                "keywords": ["Google Analytics", "GA4"]
            },
            {
                "groupName": "데이터 추출",
                "keywords": ["마케터 SQL", "마케팅 SQL"]
            },
            {
                "groupName": "광고/그로스",
                "keywords": ["퍼포먼스 마케팅", "그로스해킹"]
            },
            {
                "groupName": "검색 최적화",
                "keywords": ["SEO 마케팅", "검색엔진 최적화"]
            }
        ]

    print(f"[API] 네이버 데이터랩 트렌드 API 요청 중... (기간: {start_date} ~ {end_date}, 직무: {job_category})")
    
    # API 호출 (일별 데이터 수집)
    response_data = client.get_search_trend(
        start_date=start_date,
        end_date=end_date,
        time_unit="date",
        keyword_groups=keyword_groups
    )

    # 네이버 검색광고 API 기준의 키워드별 합리적인 월간 검색 조회수 모의 사전 정의 데이터
    mock_volumes = {
        # 회계 (Accounting)
        "전산회계": (12000, 38000), "전산세무": (8000, 24000),
        "CPA": (15000, 35000), "세무사": (11000, 29000), "공인회계사": (4000, 9000), "CTA": (3000, 7000),
        "재경관리사": (6000, 18000), "회계관리": (2000, 5000),
        "회계 더존": (120, 350), "경리 더존": (80, 240), "회계 SAP": (90, 280),
        "회계 컴활": (350, 1100), "경리 컴활": (240, 780), "회계 엑셀": (500, 1800), "경리 엑셀": (420, 1500),
        # IT / 개발 (IT Dev)
        "개발자 Git": (450, 980), "개발 Git": (620, 1200), "정보처리기사": (25000, 68000),
        "React 개발": (800, 1900), "Vue 개발": (350, 780), "프론트엔드": (4500, 12000),
        "Spring Boot": (8200, 14000), "FastAPI": (1800, 3200),
        "Docker": (9500, 15000), "Kubernetes": (4800, 6200),
        "TDD": (1100, 1900), "DB 설계": (380, 850), "데이터베이스 설계": (450, 920),
        # 마케팅 (Marketing)
        "마케팅 포토샵": (150, 480), "마케터 포토샵": (90, 280), "피그마": (18000, 38000),
        "Google Analytics": (7200, 11000), "GA4": (14000, 22000),
        "마케터 SQL": (250, 680), "마케팅 SQL": (320, 890),
        "퍼포먼스 마케팅": (2800, 6200), "그로스해킹": (1200, 2800),
        "SEO 마케팅": (450, 1100), "검색엔진 최적화": (950, 2100)
    }

    # 데이터 적재를 위한 DB 트랜잭션 수행 (두 DB에 동시 쓰기 진행)
    conns = [sqlite3.connect(DB_PATH), sqlite3.connect(NAVER_DB_PATH)]
    cursors = [conn.cursor() for conn in conns]
    
    # 1. 키워드 매핑 정보 및 월간 절대 검색수 선행 적재
    for group in keyword_groups:
        g_name = group["groupName"]
        for kw in group["keywords"]:
            pc, mob = mock_volumes.get(kw, (100, 300))
            tot = pc + mob
            for cursor in cursors:
                # 매핑 관계 적재
                cursor.execute("""
                    INSERT OR REPLACE INTO trend_keyword_mapping (group_name, keyword, job_category)
                    VALUES (?, ?, ?)
                """, (g_name, kw, job_category))
                
                # 절대 검색수 데이터 적재
                cursor.execute("""
                    INSERT OR REPLACE INTO keyword_search_volume (keyword, monthly_pc_queries, monthly_mobile_queries, monthly_total_queries, job_category)
                    VALUES (?, ?, ?, ?, ?)
                """, (kw, pc, mob, tot, job_category))

    # 2. 트렌드 비율 시계열 데이터 적재
    insert_count = 0
    results = response_data["results"]

    for group in results:
        group_name = group["title"]
        data_points = group["data"]
        
        for point in data_points:
            period = point["period"]
            ratio = float(point["ratio"])
            
            for cursor in cursors:
                cursor.execute("""
                    INSERT OR REPLACE INTO naver_search_trend (period, group_name, ratio, job_category)
                    VALUES (?, ?, ?, ?)
                """, (period, group_name, ratio, job_category))
            insert_count += 1

    for conn in conns:
        conn.commit()
        conn.close()
    
    print(f"[DB] {job_category} 직무 검색 트렌드 및 세부 매핑·절대수치 데이터 적재 완료 (총 {insert_count}건 이중 DB 적재 완료)")


if __name__ == "__main__":
    initialize_db()
    # 회계 직무 구직 관심 분석을 위해 오직 회계(accounting) 데이터만 수집 및 적재합니다.
    collect_naver_trends("accounting")
    print("=== 회계 직무 네이버 트렌드 데이터 수집 완료 ===")
