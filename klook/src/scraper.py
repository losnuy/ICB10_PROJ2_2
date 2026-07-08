"""
이 모듈은 Klook 검색 API를 활용하여 '대한민국' 검색어에 대한 상품 정보를 SQLite DB에 저장하는 스크래퍼입니다.

주요 기능:
- Klook 검색 API에 대해 페이징 처리를 하여 전체 수집을 수행합니다.
- API 서버 부하를 고려하여 요청 간 0.1초~1.0초 사이의 지연 시간(Sleep)을 적용합니다.
- HTTP 요청 에러 시 최대 3회까지 재시도하는 예외 처리를 수행합니다.
- 로우데이터(Raw Data)로부터 비즈니스 분석에 유용한 핵심 필드만을 추출 및 정제하여 정적 SQLite 테이블 스키마에 페이지 단위로 즉시 적재(Commit)합니다.
- 제품 상세 링크인 'deep_link' 정보를 필수로 포함하며, 리뷰 개수 등의 복잡한 문자열 정보를 숫자로 파싱하여 정형화된 형태로 저장합니다.
"""

import os
import re
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

def parse_review_count(review_text):
    """
    리뷰 텍스트(예: '50 reviews', '(12)')에서 숫자 부분만 추출하여 정수형으로 반환합니다.
    """
    if not review_text:
        return 0
    match = re.search(r'\d+', str(review_text))
    return int(match.group()) if match else 0

def init_db(db_path, table_name="klook_products"):
    """
    SQLite 데이터베이스를 연결하고 정형화된 스키마로 테이블을 생성합니다.
    기존에 동일한 이름의 테이블이 있다면 안전하게 처리합니다.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 정적 스키마 정의 (무료취소, 즉시확정, 로우 JSON 필드 추가)
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        activity_id INTEGER PRIMARY KEY,
        title TEXT,
        deep_link TEXT,
        category TEXT,
        city_name TEXT,
        sub_title TEXT,
        cover_url TEXT,
        location TEXT,
        rating REAL,
        review_count INTEGER,
        booked_count TEXT,
        selling_price TEXT,
        market_price TEXT,
        sold_out INTEGER,
        free_cancellation INTEGER,
        instant_confirmation INTEGER,
        raw_json TEXT
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()

def save_page_to_db(df, db_path, table_name="klook_products"):
    """
    파싱된 데이터프레임을 SQLite DB 테이블에 페이지 단위로 추가(Append) 적재합니다.
    정적 스키마에 일치하도록 INSERT OR REPLACE 구문을 활용하여 중복을 방지합니다.
    """
    conn = sqlite3.connect(db_path)
    try:
        cols = [
            "activity_id", "title", "deep_link", "category", "city_name", 
            "sub_title", "cover_url", "location", "rating", "review_count", 
            "booked_count", "selling_price", "market_price", "sold_out",
            "free_cancellation", "instant_confirmation", "raw_json"
        ]
        
        # 데이터프레임 컬럼 순서 맞추기 및 결측치 처리
        for col in cols:
            if col not in df.columns:
                df[col] = None
        
        df_to_save = df[cols]
        
        # SQL 질의를 사용해 INSERT OR REPLACE 실행 (중복 발생 시 자동 업데이트)
        cursor = conn.cursor()
        placeholders = ", ".join(["?"] * len(cols))
        query = f"INSERT OR REPLACE INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"
        
        data_tuples = [tuple(x) for x in df_to_save.to_numpy()]
        cursor.executemany(query, data_tuples)
        conn.commit()
    except Exception as e:
        print(f"[에러] DB 저장 중 에러 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

def scrape_klook_data():
    """
    Klook 검색 API를 순회하며 상품 데이터를 수집하고 파싱하여 SQLite DB에 실시간 저장하는 메인 함수입니다.
    """
    # HTTP 세션을 설정하여 재사용성을 극대화합니다.
    session = requests.Session()
    
    # 기본 검색 요청 URL 템플릿
    base_url = "https://www.klook.com/v1/cardinfocenterservicesrv/search/platform/complete_search_v3"
    query = "대한민국"
    
    # DB 저장 경로 설정
    db_dir = os.path.join("klook", "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "klook_products.db")
    table_name = "klook_products"
    
    # 깨끗한 데이터 수집을 위해 기존 DB 삭제
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"[정보] 기존 데이터베이스 파일을 삭제하고 새로 구성을 준비합니다: {db_path}")
        except Exception as e:
            print(f"[경고] 기존 데이터베이스 파일 삭제 실패: {e}")
            
    # 정적 스키마의 테이블 초기화
    init_db(db_path, table_name)
            
    page = 1
    max_retries = 3
    total_inserted = 0
    
    print("[정보] Klook 상품 데이터 정밀 파싱 수집을 시작합니다. (1~10페이지)")
    
    while page <= 10:
        # 페이지마다 Referer와 파라미터가 유동적으로 구성됩니다.
        location_val = "158,157,156,5031,8928,24975,28741,545,6166,6268,703649,703648,705582,6955,15088,701102,16467,707516,26374,7204,20296,28972,28785,8898,23546,30633,15378,16365,28742,10956,26961,10093,16560,25178,30570,7558,7741,11925,24865,25140,707332,8989,10706,11364,11745,13523,14446,15281,15603,16655,18214,18323,20392,22390,22675,23237,24520,24762,25060,26454,27895,29136,29872,30051,30265,30376,30466,31247,7030,705101,9079"
        referer_url = f"https://www.klook.com/ko/search/result/?query={urllib.parse.quote(query)}&search_scope=main_search&location={urllib.parse.quote(location_val)}&sort=most_relevant&tab_key=0&start={page}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Referer": referer_url,
            "Accept-Language": "ko_KR",
            "baggage": "sentry-environment=production,sentry-release=web_ssr-platform_20260623_7acde2fb,sentry-public_key=919ae3dd598137e1aa2a88c31e161bb3,sentry-trace_id=f58bdd1f067f452e9a7de0055c9a2c4f,sentry-transaction=SearchResult,sentry-sampled=false,sentry-sample_rand=0.5150356711438143,sentry-sample_rate=0",
            "cache-control": "no-cache",
            "sec-ch-device-memory": "16",
            "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-full-version-list": '"Google Chrome";v="149.0.7827.158", "Chromium";v="149.0.7827.158", "Not)A;Brand";v="24.0.0.0"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-platform": "desktop",
            "x-requested-with": "XMLHttpRequest",
            "x-klook-market": "global",
            "x-klook-user-residence": "10_KR",
            "x-klook-kepler-id": "2cdd3af6-1db0-4cdb-93c4-b276737adfe1",
            "x-klook-tint": '{"kepler":["253:861","669:3215","684:3546","694:3666","695:3674","706:3783","732:4304","741:4469","761:4623","768:4732","778:4887","779:4897","780:4904","787:4996","788:5005","818:5278","822:5363","851:5735","853:5740","854:5751","855:5752","871:5974","877:6067","885:6185","901:6288","910:6455","931:6736","933:6751","936:9309","948:7023","969:7423","970:7425","978:7536","980:7551","994:7879","1006:8210","1016:8314","1017:8338","1020:8414","1038:8663","1058:9017","1084:9630","1091:9724","1128:10287","1147:10834","1171:11684","1172:11691","1180:11872","1191:12047","1193:12099","1205:12358","1206:12362","1209:12385","1219:12858","1226:13132","1229:13466","1233:13338","1243:13403","1245:13481","1264:13863","1295:15296","1298:15429","1304:15491","1309:15662","1315:15687","1334:16011","1339:16217","1340:16222","1350:16662","1351:16664","1358:16742","1364:16919","1369:17000","1371:17010","1372:17052","1375:17136","1378:17204","1379:17207","1382:17315","1386:17615","1397:18048","1487:20706","1522:22730","1533:21689","1537:21796","1572:22732","1573:22735","1574:22738","1599:23643","1600:23647","1602:24273","1604:24849","1605:24270","1606:24267","1664:24744","1665:24751","1666:24760","1691:26210","1692:26200","1693:26203","1694:26859","1695:26856","1696:26853","1697:26193","1702:25542","1741:26400","1748:26626","1749:30652","1887:30172","1901:30291","1903:30331","1909:30461","1914:32288","1915:32292","1916:32296","1918:30619","1919:30623","1921:30870","1922:30755","1926:30897","1930:30926","1956:31533","1963:31519","1992:32257","2003:32588","2014:32761","2016:32825","2018:32881","2019:32887","2022:32948","2026:32987","2031:33250","2058:33418","2074:33686","2078:33785","2079:33788","2080:33790","2081:33794","2082:33833"]}'
        }
        
        params = {
            "location": location_val,
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
                
            # 1. 로우 데이터로부터 정의된 정적 스키마 필드 파싱
            activity_id = card_data.get("vertical_id")
            title = card_data.get("title")
            deep_link = card_data.get("deep_link")
            category = card_data.get("category")
            city_name = card_data.get("city_name")
            sub_title = card_data.get("sub_title")
            cover_url = card_data.get("cover_url")
            location = card_data.get("location")
            
            # 평점 및 예약 정보 추출
            review_obj = card_data.get("review_obj", {})
            rating = 0.0
            review_count = 0
            booked_count = ""
            if isinstance(review_obj, dict):
                rating = clean_float(review_obj.get("star"))
                review_count = parse_review_count(review_obj.get("count"))
                booked_count = review_obj.get("booked", "")
            
            # 가격 정보 추출
            price_obj = card_data.get("price", {})
            selling_price = ""
            market_price = ""
            if isinstance(price_obj, dict):
                selling_price = price_obj.get("selling_price", "")
                market_price = price_obj.get("market_price", "")
                
            # 품절 여부
            sold_out = 1 if card_data.get("sold_out") else 0
            
            # 신규: 무료 취소 및 즉시 확정 지능형 파싱 (general_tag 및 tags 병합 검출)
            free_cancellation = 0
            instant_confirmation = 0
            
            # 1) general_tag 리스트 검사
            general_tags = card_data.get("general_tag", [])
            if isinstance(general_tags, list):
                for tag in general_tags:
                    if isinstance(tag, dict):
                        tag_text = tag.get("text", "")
                        tag_key = tag.get("tagKey", "")
                        if "무료 취소" in tag_text or "무료취소" in tag_text or "free_cancel" in tag_key.lower():
                            free_cancellation = 1
                        if "즉시 확정" in tag_text or "즉시확정" in tag_text or "instant_confirm" in tag_key.lower():
                            instant_confirmation = 1
                            
            # 2) 혹시 모를 tags 리스트 검사 보완
            tags = card_data.get("tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    tag_name = tag.get("name", "") if isinstance(tag, dict) else str(tag)
                    if "무료 취소" in tag_name or "무료취소" in tag_name:
                        free_cancellation = 1
                    if "즉시 확정" in tag_name or "즉시확정" in tag_name:
                        instant_confirmation = 1
                        
            # 신규: 로우 JSON 저장
            raw_json = json.dumps(card_data, ensure_ascii=False)
            
            row_data = {
                "activity_id": activity_id,
                "title": title,
                "deep_link": deep_link,
                "category": category,
                "city_name": city_name,
                "sub_title": sub_title,
                "cover_url": cover_url,
                "location": location,
                "rating": rating,
                "review_count": review_count,
                "booked_count": booked_count,
                "selling_price": selling_price,
                "market_price": market_price,
                "sold_out": sold_out,
                "free_cancellation": free_cancellation,
                "instant_confirmation": instant_confirmation,
                "raw_json": raw_json
            }
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
            
            # 수집 완료 후 통계 요약 리포트 출력
            print("\n==================================================")
            print("                 KLOOK 수집 요약 리포트")
            print("==================================================")
            print(f"▶ 총 수집 상품 수        : {len(df_all)}개")
            free_cancel_cnt = df_all['free_cancellation'].sum()
            instant_conf_cnt = df_all['instant_confirmation'].sum()
            sold_out_cnt = df_all['sold_out'].sum()
            avg_rating = df_all['rating'].mean()
            
            print(f"▶ 무료 취소 가능 상품 수  : {free_cancel_cnt}개 ({free_cancel_cnt/len(df_all)*100:.1f}%)")
            print(f"▶ 즉시 확정 가능 상품 수  : {instant_conf_cnt}개 ({instant_conf_cnt/len(df_all)*100:.1f}%)")
            print(f"▶ 품절 상품 수            : {sold_out_cnt}개 ({sold_out_cnt/len(df_all)*100:.1f}%)")
            print(f"▶ 평균 평점              : {avg_rating:.2f} / 5.0")
            print("==================================================\n")
            
        except Exception as e:
            print(f"[경고] CSV 파일 저장 및 통계 리포트 생성 중 오류 발생: {e}")
            
    return db_path

if __name__ == "__main__":
    scrape_klook_data()
