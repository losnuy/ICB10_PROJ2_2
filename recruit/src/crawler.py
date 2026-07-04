"""
이 모듈은 사람인(Saramin) 사이트에서 회계 직무 관련 채용공고 목록(1~10페이지) 및 상세페이지 데이터를 수집하여 SQLite 데이터베이스에 저장하는 수집기입니다.

주요 기능:
- SQLite 데이터베이스 테이블 초기화 (Upsert를 지원하는 스키마 구성)
- HTTP 헤더 및 쿠키 설정을 이용한 실제 브라우저 모방 요청 전송
- 채용공고 목록 페이지 파싱 및 주요 메타데이터 추출 (기업명, 제목, 조건, 마감일 등)
- 채용공고 상세 페이지 HTML 본문 및 메타데이터 수집
- 수집 간 네트워크 부하 최소화를 위한 요청 지연 처리 (Random Delay)
- 수집 성공 여부를 요약하여 출력하는 리포팅
"""

import os
import re
import time
import random
import json
import sqlite3
from datetime import datetime
import urllib.parse
import requests
from bs4 import BeautifulSoup

# 설정 값 정의
DB_DIR = os.path.join("recruit", "data")
DB_PATH = os.path.join(DB_DIR, "recruit.db")
BASE_URL = "https://www.saramin.co.kr"
SEARCH_URL = "https://www.saramin.co.kr/zf_user/search"

# 브라우저 요청 모방을 위한 헤더 설정
# User-Agent와 Referer는 실제 환경과 유사하게 고정하고, 쿠키는 비로그인 시 사용 가능한 수준으로 기본 구성
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Referer": "https://www.saramin.co.kr/",
}

# recruit_prompt_v1.md 에서 추출한 예시 쿠키 설정
COOKIES = {
    "PCID": "17825374927795132397418",
    "_gcl_au": "1.1.1905928679.1782537501",
}


def init_db():
    """
    데이터베이스 연결을 수행하고 필요한 테이블을 생성합니다.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 채용공고 목록 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruit_list (
            rec_idx TEXT PRIMARY KEY,
            company_name TEXT,
            title TEXT,
            link TEXT,
            conditions TEXT,
            job_sector TEXT,
            deadlines TEXT,
            raw_json TEXT,
            updated_at TEXT
        )
    """)

    # 2. 채용공고 상세정보 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruit_detail (
            rec_idx TEXT PRIMARY KEY,
            detail_html TEXT,
            detail_content TEXT,
            raw_json TEXT,
            updated_at TEXT,
            FOREIGN KEY (rec_idx) REFERENCES recruit_list(rec_idx)
        )
    """)

    conn.commit()
    conn.close()
    print(f"데이터베이스 초기화 완료: {DB_PATH}")


def parse_rec_idx(link):
    """
    공고 상세 링크 URL 에서 rec_idx 값을 파싱해 반환합니다.
    """
    parsed = urllib.parse.urlparse(link)
    params = urllib.parse.parse_qs(parsed.query)
    if "rec_idx" in params:
        return params["rec_idx"][0]
    
    # 정규식 패턴 매칭 시도
    match = re.search(r"rec_idx=(\d+)", link)
    if match:
        return match.group(1)
    return None


def upsert_recruit_list(conn, item):
    """
    수집한 채용공고 목록 요소를 recruit_list 테이블에 Upsert 합니다.
    """
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_json_str = json.dumps(item, ensure_ascii=False)

    cursor.execute("""
        INSERT INTO recruit_list (rec_idx, company_name, title, link, conditions, job_sector, deadlines, raw_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(rec_idx) DO UPDATE SET
            company_name=excluded.company_name,
            title=excluded.title,
            link=excluded.link,
            conditions=excluded.conditions,
            job_sector=excluded.job_sector,
            deadlines=excluded.deadlines,
            raw_json=excluded.raw_json,
            updated_at=excluded.updated_at
    """, (
        item["rec_idx"],
        item["company_name"],
        item["title"],
        item["link"],
        item["conditions"],
        item["job_sector"],
        item["deadlines"],
        raw_json_str,
        now_str
    ))
    conn.commit()


def upsert_recruit_detail(conn, rec_idx, html_content, detail_content, raw_data):
    """
    수집한 상세 정보를 recruit_detail 테이블에 Upsert 합니다.
    """
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_json_str = json.dumps(raw_data, ensure_ascii=False)

    cursor.execute("""
        INSERT INTO recruit_detail (rec_idx, detail_html, detail_content, raw_json, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(rec_idx) DO UPDATE SET
            detail_html=excluded.detail_html,
            detail_content=excluded.detail_content,
            raw_json=excluded.raw_json,
            updated_at=excluded.updated_at
    """, (
        rec_idx,
        html_content,
        detail_content,
        raw_json_str,
        now_str
    ))
    conn.commit()


def sleep_random():
    """
    요청 간에 0.1 ~ 1.0초 사이의 임의의 지연 시간을 적용하여 네트워크 부하를 줄입니다.
    """
    delay = random.uniform(0.1, 1.0)
    time.sleep(delay)


def crawl_recruit_list(page):
    """
    특정 페이지의 사람인 회계 채용 공고 목록을 수집하고 파싱합니다.
    """
    params = {
        "searchType": "search",
        "searchword": "회계",
        "company_cd": "0,1,2,3,4,5,6,7,9,10",
        "cat_kewd": "2197",
        "panel_type": "",
        "search_optional_item": "y",
        "search_done": "y",
        "panel_count": "y",
        "preview": "y",
        "recruitPage": str(page),
        "recruitPageCount": "40" # 한 페이지당 수집 기본 수
    }

    try:
        response = requests.get(SEARCH_URL, headers=HEADERS, cookies=COOKIES, params=params, timeout=10)
        if response.status_code != 200:
            print(f"Error: 목록 페이지 {page} 호출 실패 (Status: {response.status_code})")
            return []

        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".item_recruit")
        
        parsed_items = []
        for item in items:
            try:
                # 1. 기업명 추출
                corp_elem = item.select_one(".corp_name a")
                company_name = corp_elem.get_text(strip=True) if corp_elem else ""
                
                # 2. 공고 제목 및 링크 추출
                tit_elem = item.select_one(".job_tit a")
                if not tit_elem:
                    continue
                title = tit_elem.get_text(strip=True)
                link = tit_elem.get("href", "")
                if link and not link.startswith("http"):
                    link = BASE_URL + link
                
                # 3. 공고 ID(rec_idx) 추출
                rec_idx = parse_rec_idx(link)
                if not rec_idx:
                    # 속성에서 직접 가져오기 시도
                    rec_idx = item.get("rec-idx") or item.get("id")
                if not rec_idx:
                    continue
                
                # 4. 채용 조건 추출
                cond_elems = item.select(".job_conditions span")
                conditions = " | ".join([c.get_text(strip=True) for c in cond_elems])
                
                # 5. 직무 분야 키워드 추출
                sector_elem = item.select_one(".job_sector")
                job_sector = sector_elem.get_text(" | ", strip=True) if sector_elem else ""
                
                # 6. 마감일/등록일 추출
                date_elem = item.select_one(".job_date")
                deadlines = date_elem.get_text(strip=True) if date_elem else ""

                parsed_items.append({
                    "rec_idx": rec_idx,
                    "company_name": company_name,
                    "title": title,
                    "link": link,
                    "conditions": conditions,
                    "job_sector": job_sector,
                    "deadlines": deadlines
                })
            except Exception as e:
                print(f"아이템 파싱 예외 발생: {e}")
                continue

        return parsed_items
    except Exception as e:
        print(f"목록 수집 예외 발생 (페이지 {page}): {e}")
        return []


def crawl_recruit_detail(link, rec_idx=None):
    """
    공고 상세 링크에서 rec_idx를 추출하여 실제 본문 요강 전용 URL(view-detail)로 요청을 전송하고,
    상세페이지의 실제 본문 내용(HTML)과 순수 본문 텍스트를 수집합니다.
    """
    if not rec_idx:
        rec_idx = parse_rec_idx(link)
    
    if not rec_idx:
        return None, "", {}
        
    detail_url = f"https://www.saramin.co.kr/zf_user/jobs/relay/view-detail?rec_idx={rec_idx}"
    
    try:
        response = requests.get(detail_url, headers=HEADERS, cookies=COOKIES, timeout=10)
        if response.status_code != 200:
            return None, "", {}
        
        soup = BeautifulSoup(response.text, "html.parser")
        user_content = soup.select_one(".user_content")
        
        meta_info = {}
        if user_content:
            detail_content = user_content.get_text("\n", strip=True)
            detail_html = str(user_content)
            meta_info["has_user_content"] = True
            meta_info["summary_snippet"] = detail_content[:200].replace("\n", " ")
        else:
            detail_content = soup.get_text("\n", strip=True)
            detail_html = response.text
            
        return detail_html, detail_content, meta_info
    except Exception as e:
        print(f"상세 수집 예외 발생 ({detail_url}): {e}")
        return None, "", {}



def main():
    """
    전체 수집 파이프라인을 실행합니다.
    """
    print("=== 사람인 채용공고 수집 프로세스 시작 ===")
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1단계: 목록 수집 (1 ~ 40페이지 혹은 1000건 확보 시까지)
    list_success_count = 0
    collected_ids = []
    
    print("\n[1단계] 채용공고 목록 수집을 시작합니다. (최대 40페이지)")
    for page in range(1, 41):
        # 현재 DB에 저장된 총 목록 수 확인
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM recruit_list")
        current_total = cursor.fetchone()[0]
        
        # if current_total >= 1000:
        #     print(f"   [완료] 목표 건수(1000건) 도달 완료 (현재 DB 목록: {current_total}건). 목록 수집을 종료합니다.")
        #     break
            
        print(f"-> {page} 페이지 수집 중... (현재 DB 목록: {current_total}건)")
        items = crawl_recruit_list(page)
        
        if not items:
            print(f"   [주의] {page} 페이지에서 수집된 채용공고가 없거나 오류가 발생했습니다.")
            continue
            
        for item in items:
            try:
                upsert_recruit_list(conn, item)
                collected_ids.append(item["rec_idx"])
                list_success_count += 1
            except Exception as db_err:
                print(f"DB 저장 오류: {db_err}")
                
        print(f"   {page} 페이지 완료: {len(items)}건 처리 완료.")
        sleep_random()

    # 최종 DB 목록 수 재확인
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recruit_list")
    final_list_count = cursor.fetchone()[0]
    print(f"\n[1단계 완료] 현재 DB에 저장된 누적 목록: {final_list_count}건")
    
    # 2단계: 상세페이지 수집
    # DB에서 목록에는 존재하나 상세 테이블에 없는(신규 추가된) 공고만 조회
    cursor.execute("""
        SELECT r.rec_idx, r.link, r.title, r.company_name
        FROM recruit_list r
        LEFT JOIN recruit_detail d ON r.rec_idx = d.rec_idx
        WHERE d.rec_idx IS NULL
    """)
    targets = cursor.fetchall()
    total_targets = len(targets)
    
    print(f"\n[2단계] 신규 채용공고 상세 정보 수집을 시작합니다. (수집 대상: {total_targets}개 공고)")
    
    detail_success_count = 0
    for idx, (rec_idx, link, title, company_name) in enumerate(targets, 1):
        print(f"-> [{idx}/{total_targets}] 공고 ID: {rec_idx} ({company_name} - {title[:15]}...) 상세 수집 중...")
        
        html_content, detail_content, meta_info = crawl_recruit_detail(link, rec_idx)
        if html_content:
            try:
                upsert_recruit_detail(conn, rec_idx, html_content, detail_content, meta_info)
                detail_success_count += 1
            except Exception as db_err:
                print(f"상세 DB 저장 오류: {db_err}")
        else:
            print(f"   [주의] 상세 수집 실패: {link}")
            
        sleep_random()

    # 최종 상세 수집 개수 확인
    cursor.execute("SELECT COUNT(*) FROM recruit_detail")
    final_detail_count = cursor.fetchone()[0]
    conn.close()
    
    # 3단계: 최종 리포트 출력
    print("\n" + "="*40)
    print("=== 수집 프로세스 최종 결과 리포트 ===")
    print("="*40)
    print(f"수집 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"DB 누적 목록 수 (recruit_list): {final_list_count}건")
    print(f"DB 누적 상세 수 (recruit_detail): {final_detail_count}건")
    print(f"금번 신규 상세페이지 Upsert 성공 건수: {detail_success_count}건 / {total_targets}건")
    print(f"데이터베이스 저장 경로: {DB_PATH}")
    print("="*40)


if __name__ == "__main__":
    main()
