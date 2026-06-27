"""
이 모듈은 scrapling 라이브러리를 사용하여 trip.com에서 특정 호텔의 전체 리뷰 데이터를 수집하고
이를 SQLite 데이터베이스에 저장하는 스크립트입니다.

주요 기능:
- trip.com 호텔 리뷰 API를 호출하여 데이터 페이징 수집
- 첫 번째 페이지를 수집 및 검증한 후, 전체 리뷰 수집 진행
- 수집된 리뷰 데이터(작성자, 작성일자, 별점, 내용, 번역 내용 등)를 SQLite DB에 저장
"""

import os
import time
import random
import sqlite3
import json
from scrapling import Fetcher

# 대상 URL 및 헤더 설정
API_URL = "https://kr.trip.com/restapi/soa2/34308/getHotelCommentInfo"

HEADERS = {
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "w-payload-source": "1.0.9@102!Nudtz1KLhCAbOX4SO6An9PKnG2KLOSqZOlbn+6FaG6OaKSbpKET2OSVbOrK2+ET5+rApbbbpOSknKr42+rG2KlqIbEVbKtb5+rbSOEb2KE4p+rKpOr4nKrq/K5bpOSqL+rk/OSKZKrVpQlVROShDKFO3GVd3hbb=",
    "x-ctx-country": "KR",
    "x-ctx-currency": "KRW",
    "x-ctx-locale": "ko-KR",
    "x-ctx-ubt-pageid": "10320668147",
    "x-ctx-ubt-pvid": "7",
    "x-ctx-ubt-sid": "9",
    "x-ctx-ubt-vid": "1754985737191.9877n1SlbHlt",
    "x-ctx-user-recognize": "NON_EU",
    "x-ctx-wclient-req": "0af33fe7acb74bcfe9f82cf404544b46",
    "content-type": "application/json"
}

# DB 및 데이터 저장 경로 설정 (상대경로 적용)
DB_PATH = "trip_com/data/trip_reviews.db"

def get_payload(page_index, page_size=10):
    """
    지정된 페이지 인덱스와 페이지 크기에 맞는 요청 페이로드를 생성합니다.
    """
    return {
        "hotelId": 58635410,
        "commentFilterOptions": {
            "pageIndex": page_index,
            "pageSize": page_size,
            "repeatComment": 1
        },
        "sceneTypes": ["CommentList"],
        "head": {
            "platform": "PC",
            "cver": "0",
            "cid": "1754985737191.9877n1SlbHlt",
            "bu": "IBU",
            "group": "trip",
            "aid": "",
            "sid": "",
            "ouid": "",
            "locale": "ko-KR",
            "timezone": "9",
            "currency": "KRW",
            "pageId": "10320668147",
            "vid": "1754985737191.9877n1SlbHlt",
            "guid": "",
            "isSSR": False
        }
    }

def init_db():
    """
    SQLite 데이터베이스 및 테이블을 초기화합니다.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY,
            username TEXT,
            create_date TEXT,
            room_name TEXT,
            rating INTEGER,
            content TEXT,
            translated_content TEXT,
            travel_type TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_reviews_to_db(reviews):
    """
    리뷰 데이터 리스트를 SQLite DB에 저장(UPSERT)합니다.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted_count = 0
    for review in reviews:
        try:
            cursor.execute("""
                INSERT INTO reviews (id, username, create_date, room_name, rating, content, translated_content, travel_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username=excluded.username,
                    create_date=excluded.create_date,
                    room_name=excluded.room_name,
                    rating=excluded.rating,
                    content=excluded.content,
                    translated_content=excluded.translated_content,
                    travel_type=excluded.travel_type
            """, (
                review.get("id"),
                review.get("username"),
                review.get("create_date"),
                review.get("room_name"),
                review.get("rating"),
                review.get("content"),
                review.get("translated_content"),
                review.get("travel_type")
            ))
            inserted_count += 1
        except Exception as e:
            print(f"리뷰 ID {review.get('id')} 저장 중 오류 발생: {e}")
            
    conn.commit()
    conn.close()
    return inserted_count

def parse_comment_data(comment_list):
    """
    API 응답에서 수집할 필드들만 추출하여 정제된 리스트로 변환합니다.
    """
    parsed_reviews = []
    for item in comment_list:
        parsed_reviews.append({
            "id": item.get("id"),
            "username": item.get("userInfo", {}).get("nickName"),
            "create_date": item.get("createDate"),
            "room_name": item.get("roomName"),
            "rating": item.get("rating"),
            "content": item.get("content"),
            "translated_content": item.get("translatedContent"),
            "travel_type": item.get("travelTypeText")
        })
    return parsed_reviews

def fetch_page(fetcher, page_index):
    """
    특정 페이지의 리뷰 데이터를 수집하고 파싱하여 반환합니다.
    """
    payload = get_payload(page_index)
    try:
        response = fetcher.post(API_URL, headers=HEADERS, json=payload)
        if response.status != 200:
            print(f"[페이지 {page_index}] 요청 실패. HTTP 상태 코드: {response.status}")
            return None
            
        data = response.json()
        if not data or "data" not in data:
            print(f"[페이지 {page_index}] 응답에 데이터가 존재하지 않습니다.")
            return None
            
        res_data = data["data"]
        total_count = res_data.get("totalCount", 0)
        
        # groupList 안에서 commentList를 가진 항목 찾기
        comment_list = []
        group_list = res_data.get("groupList", [])
        for group in group_list:
            if "commentList" in group and group["commentList"]:
                comment_list.extend(group["commentList"])
                
        parsed_reviews = parse_comment_data(comment_list)
        return {
            "reviews": parsed_reviews,
            "total_count": total_count
        }
    except Exception as e:
        print(f"[페이지 {page_index}] 수집 중 예외 발생: {e}")
        return None

def main():
    import sys
    # 윈도우 환경에서 다국어(일본어, 중국어 등) 터미널 출력 시 인코딩 에러 방지
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # reconfigure가 지원되지 않는 구버전 파이썬 대비
        pass

    print("SQLite 데이터베이스를 초기화합니다...")
    init_db()
    
    fetcher = Fetcher()
    
    # 1 단계: 첫 페이지 수집 및 검증
    print("1단계: 첫 페이지 수집 검증을 시작합니다...")
    first_page_data = fetch_page(fetcher, page_index=1)
    
    if not first_page_data or not first_page_data["reviews"]:
        print("첫 페이지 수집 검증에 실패했습니다. 데이터를 가져올 수 없습니다.")
        return
        
    reviews = first_page_data["reviews"]
    total_count = first_page_data["total_count"]
    
    print(f"첫 페이지 수집 성공! (가져온 리뷰 수: {len(reviews)} / 전체 리뷰 수: {total_count})")
    
    # 첫 페이지 데이터 검증용 출력
    print("\n--- 첫 페이지 수집 데이터 검증 ---")
    test_review = reviews[0]
    print(f"리뷰 ID: {test_review['id']}")
    print(f"작성자: {test_review['username']}")
    print(f"작성일자: {test_review['create_date']}")
    print(f"평점: {test_review['rating']}")
    print(f"객실 타입: {test_review['room_name']}")
    print(f"리뷰 내용 일부: {test_review['content'][:100] if test_review['content'] else '없음'}")
    print(f"번역 내용 일부: {test_review['translated_content'][:100] if test_review['translated_content'] else '없음'}")
    print("---------------------------------\n")
    
    # 데이터가 정상적으로 채워져 있는지 체크
    if not test_review['content'] or test_review['rating'] is None:
        print("경고: 필수 데이터(리뷰 내용 또는 평점)가 누락되었습니다. 수집을 중단합니다.")
        return
        
    print("첫 페이지 데이터 검증이 정상적으로 통과되었습니다. DB에 저장 후 전체 수집을 진행합니다.")
    save_reviews_to_db(reviews)
    
    # 2 단계: 전체 리뷰 수집 진행
    page_size = 10
    import math
    total_pages = math.ceil(total_count / page_size)
    print(f"전체 수집 대상 페이지 수: {total_pages} (2페이지부터 {total_pages}페이지까지 순차 수집)")
    
    collected_total = len(reviews)
    
    for page in range(2, total_pages + 1):
        # 봇 차단 방지를 위한 랜덤 지연시간 설정 (1초 ~ 3초)
        delay = random.uniform(1.0, 3.0)
        print(f"대기 중... ({delay:.2f}초)")
        time.sleep(delay)
        
        print(f"페이지 {page}/{total_pages} 수집 요청 중...")
        page_data = fetch_page(fetcher, page)
        
        if page_data and page_data["reviews"]:
            page_reviews = page_data["reviews"]
            saved_count = save_reviews_to_db(page_reviews)
            collected_total += len(page_reviews)
            print(f"페이지 {page} 수집 완료: {len(page_reviews)}개 수집 (누적 {collected_total}/{total_count})")
        else:
            print(f"페이지 {page} 수집 실패 또는 데이터 없음. 다음 페이지로 진행합니다.")
            
    print(f"\n모든 작업이 완료되었습니다. 총 {collected_total}개의 리뷰가 수집/업데이트되어 DB에 저장되었습니다.")

if __name__ == "__main__":
    main()
