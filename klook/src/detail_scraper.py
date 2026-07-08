"""
이 모듈은 Klook 상품 상세페이지(deep_link)를 순회하며 
상세 설명, 포함/불포함 사항, 사용방법, 환불 규정 등의 정밀 정보를 
Playwright 브라우저 모사를 통해 수집하여 SQLite DB에 적재하는 스크래퍼입니다.

주요 기능:
- SQLite DB(klook_products)에서 상위 10개 상품의 deep_link 정보를 가져옵니다.
- Playwright를 활용하여 봇 방지를 우회하고 실제 브라우저처럼 접근합니다.
- 이미지, 폰트 및 미디어 자원을 로딩 차단하여 페이지 렌더링 성능을 최적화합니다.
- 셀렉터 매칭 및 키워드 기반 범용 파싱 알고리즘을 혼합하여 견고하게 텍스트 정보를 추출합니다.
- 추출된 상세 정보를 'klook_product_details' 테이블에 실시간으로 적재(INSERT OR REPLACE)합니다.
"""

import os
import time
import sqlite3
from playwright.sync_api import sync_playwright

def init_detail_db(db_path, table_name="klook_product_details"):
    """
    상세페이지 데이터를 저장할 SQLite 테이블을 초기화합니다.
    klook_products 테이블의 activity_id와 외래키(FOREIGN KEY) 연동을 설정합니다.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        activity_id INTEGER PRIMARY KEY,
        description TEXT,
        highlights TEXT,
        inclusions TEXT,
        exclusions TEXT,
        how_to_use TEXT,
        cancellation_policy TEXT,
        FOREIGN KEY(activity_id) REFERENCES klook_products(activity_id)
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()

def get_top_links(db_path):
    """
    기존 상품 정보 테이블에서 수집된 상위 10개 상품의 activity_id와 deep_link를 조회합니다.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT activity_id, deep_link FROM klook_products LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return rows

def parse_section_by_keyword(page, title_keywords):
    """
    주요 키워드 헤더를 찾고, 해당 헤더를 둘러싼 상위 컨테이너 또는 다음 형제 요소의 텍스트를 범용 파싱합니다.
    CSS 셀렉터가 깨질 경우를 대비한 강력한(Robust) 폴백 장치입니다.
    """
    for kw in title_keywords:
        try:
            # 해당 텍스트를 갖는 h2, h3, h4 또는 strong 태그 탐색
            locators = [
                page.locator(f"h2:has-text('{kw}')").first,
                page.locator(f"h3:has-text('{kw}')").first,
                page.locator(f"div:has-text('{kw}')").first
            ]
            for loc in locators:
                if loc.count() > 0:
                    # 부모 요소를 가져와서 텍스트를 추출 (보통 부모 컴포넌트에 해당 섹션 내용이 다 들어있음)
                    parent_text = loc.locator("xpath=..").inner_text()
                    if parent_text and len(parent_text.strip()) > len(kw) + 10:
                        return parent_text.strip()
        except Exception:
            continue
    return ""

def scrape_detail_page(page, url):
    """
    개별 상품 상세페이지에 접근하여 핵심 정보를 파싱합니다.
    """
    print(f"[정보] 상세페이지 로딩 중: {url}")
    
    # 봇 차단을 피하기 위한 로드 대기
    page.goto(url, wait_until="load", timeout=45000)
    time.sleep(3.0)  # 동적 콘텐츠 렌더링 대기
    
    # 1. 상세 설명 수집
    description = ""
    desc_locators = [
        ".activity-detail-description", 
        "[data-testid='description-container']", 
        ".detail-section", 
        ".intro-container"
    ]
    for loc in desc_locators:
        try:
            target = page.locator(loc).first
            if target.count() > 0:
                description = target.inner_text().strip()
                break
        except Exception:
            continue
    if not description:
        description = parse_section_by_keyword(page, ["상품 소개", "액티비티 소개", "상품 설명", "상세 정보"])
        
    # 2. 하이라이트 수집
    highlights = ""
    hl_locators = [
        ".highlights-container", 
        "[data-testid='highlights-container']", 
        ".highlights"
    ]
    for loc in hl_locators:
        try:
            target = page.locator(loc).first
            if target.count() > 0:
                highlights = target.inner_text().strip()
                break
        except Exception:
            continue
    if not highlights:
        highlights = parse_section_by_keyword(page, ["하이라이트", "주요 기능", "포인트"])
        
    # 3. 포함 사항 수집
    inclusions = ""
    inc_locators = [
        ".inclusions", 
        "[data-testid='inclusions-container']", 
        ".inclusion-list",
        ".package-includes"
    ]
    for loc in inc_locators:
        try:
            target = page.locator(loc).first
            if target.count() > 0:
                inclusions = target.inner_text().strip()
                break
        except Exception:
            continue
    if not inclusions:
        inclusions = parse_section_by_keyword(page, ["포함 사항", "포함사항", "패키지 포함"])
        
    # 4. 불포함 사항 수집
    exclusions = ""
    exc_locators = [
        ".exclusions", 
        "[data-testid='exclusions-container']", 
        ".exclusion-list",
        ".package-excludes"
    ]
    for loc in exc_locators:
        try:
            target = page.locator(loc).first
            if target.count() > 0:
                exclusions = target.inner_text().strip()
                break
        except Exception:
            continue
    if not exclusions:
        exclusions = parse_section_by_keyword(page, ["불포함 사항", "불포함사항", "패키지 불포함"])

    # 5. 사용 방법 수집
    how_to_use = ""
    use_locators = [
        ".how-to-use", 
        "[data-testid='how-to-use-container']", 
        ".usage-info",
        ".how-to-redeem"
    ]
    for loc in use_locators:
        try:
            target = page.locator(loc).first
            if target.count() > 0:
                how_to_use = target.inner_text().strip()
                break
        except Exception:
            continue
    if not how_to_use:
        how_to_use = parse_section_by_keyword(page, ["사용방법", "이용방법", "사용 방법", "이용 방법"])

    # 6. 취소 및 환불 규정 수집
    cancellation_policy = ""
    cancel_locators = [
        ".cancellation-policy", 
        "[data-testid='cancellation-policy-container']", 
        ".refund-policy"
    ]
    for loc in cancel_locators:
        try:
            target = page.locator(loc).first
            if target.count() > 0:
                cancellation_policy = target.inner_text().strip()
                break
        except Exception:
            continue
    if not cancellation_policy:
        cancellation_policy = parse_section_by_keyword(page, ["환불 규정", "취소 규정", "환불 규정 및 취소 규정", "취소 규정"])

    return {
        "description": description,
        "highlights": highlights,
        "inclusions": inclusions,
        "exclusions": exclusions,
        "how_to_use": how_to_use,
        "cancellation_policy": cancellation_policy
    }

def save_detail_to_db(db_path, activity_id, data, table_name="klook_product_details"):
    """
    수집 완료된 상세 정보를 데이터베이스에 실시간으로 적재(INSERT OR REPLACE)합니다.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = f"""
    INSERT OR REPLACE INTO {table_name} (
        activity_id, description, highlights, inclusions, exclusions, how_to_use, cancellation_policy
    ) VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    cursor.execute(query, (
        activity_id,
        data["description"],
        data["highlights"],
        data["inclusions"],
        data["exclusions"],
        data["how_to_use"],
        data["cancellation_policy"]
    ))
    conn.commit()
    conn.close()

def main():
    db_dir = os.path.join("klook", "data")
    db_path = os.path.join(db_dir, "klook_products.db")
    table_name = "klook_product_details"
    
    # 1. 상세페이지 테이블 초기화
    init_detail_db(db_path, table_name)
    
    # 2. 크롤링할 상품 대상 10개 조회
    top_products = get_top_links(db_path)
    if not top_products:
        print("[오류] 수집된 상품 정보가 klook_products 테이블에 존재하지 않습니다.")
        return
        
    print(f"[정보] 총 {len(top_products)}개 상품 상세페이지 수집 작업을 기동합니다.")
    
    with sync_playwright() as p:
        # 헤드리스 모드로 띄우되 실제 브라우저와 가깝게 모사하여 Datadome 보안 통과 유도
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul"
        )
        page = context.new_page()
        
        # 최적화: 이미지, 미디어, 폰트 자원 차단으로 속도 최적화
        def block_assets(route, request):
            if request.resource_type in ["image", "media", "font"]:
                route.abort()
            else:
                route.continue_()
        page.route("**/*", block_assets)
        
        success_count = 0
        for activity_id, deep_link in top_products:
            # 공항 픽업처럼 다소 다른 주소(/ko/airport-transfers/)일 경우 예외처리 또는 표준 치환
            if "airport-transfers" in deep_link:
                print(f"[정보] 전용 트랜스퍼 페이지 건너뜀 (activity_id: {activity_id})")
                continue
                
            try:
                # 상세 정보 파싱 실행
                parsed_data = scrape_detail_page(page, deep_link)
                
                # DB 적재
                save_detail_to_db(db_path, activity_id, parsed_data, table_name)
                success_count += 1
                print(f"[성공] 상품 ID {activity_id} 상세페이지 적재 완료! (누적: {success_count})")
                
            except Exception as e:
                print(f"[에러] 상품 ID {activity_id} 상세페이지 수집 실패: {e}")
                
            # 예의 바른 크롤링 대기 시간
            time.sleep(2.0)
            
        browser.close()
        
    print(f"[성공] Klook 상세페이지 총 {success_count}개 수집 및 데이터베이스 적재를 완료했습니다.")

if __name__ == "__main__":
    main()
