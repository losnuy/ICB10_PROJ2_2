"""
YES24 종합 베스트셀러 도서 목록을 수집하여 CSV 파일로 저장하는 스크래핑 모듈입니다.

주요 기능:
- 베스트셀러 전체 페이지(최대 5페이지)를 순회하며 책 정보 수집
- 수집 컬럼: 순위, 상품ID, 도서명, 상세링크, 저자, 출판사, 출판일, 할인율, 판매가, 정가, 판매지수, 평점, 리뷰수
- 데이터 정제: 콤마 제거 및 숫자 형변환 처리
- 최종 수집 데이터를 Pandas DataFrame으로 변환 후 CSV 파일로 저장
"""

import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

def clean_number(text):
    """
    텍스트에서 숫자만 추출하여 정수형으로 반환하는 헬퍼 함수입니다.
    """
    if not text:
        return 0
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else 0

def clean_float(text):
    """
    텍스트에서 실수를 추출하여 반환하는 헬퍼 함수입니다.
    """
    if not text:
        return 0.0
    cleaned = re.findall(r"\d+\.\d+|\d+", text)
    return float(cleaned[0]) if cleaned else 0.0

def scrape_yes24_bestsellers():
    """
    YES24 베스트셀러 목록을 수집하고 CSV로 저장하는 메인 함수입니다.
    """
    url = "https://www.yes24.com/Product/Category/BestSeller"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    collected_data = []
    
    # 베스트셀러는 일반적으로 최대 5페이지까지 제공됩니다.
    max_pages = 5
    
    for page in range(1, max_pages + 1):
        print(f"[정보] {page} 페이지 수집 중...")
        params = {
            "categoryNumber": "001",
            "pageNumber": page,
            "pageSize": "24"
        }
        
        try:
            res = requests.get(url, params=params, headers=headers)
            if res.status_code != 200:
                print(f"[경고] {page} 페이지를 가져오지 못했습니다. 상태 코드: {res.status_code}")
                break
                
            soup = BeautifulSoup(res.text, "lxml")
            items = soup.select("#yesBestList > li")
            if not items:
                items = soup.select("ul.ycg_list > li")
                
            if not items:
                print(f"[정보] {page} 페이지에 도서 데이터가 없습니다. 수집을 종료합니다.")
                break
                
            for item in items:
                # 1. 순위
                rank_elem = item.select_one("em.ico.rank")
                rank = clean_number(rank_elem.text) if rank_elem else 0
                
                # 2. 도서 ID
                goods_id = item.get("data-goods-no", "")
                
                # 3. 도서명
                title_elem = item.select_one("a.gd_name")
                title = title_elem.text.strip() if title_elem else ""
                
                # 4. 상세 링크
                link = ""
                if title_elem and title_elem.get("href"):
                    link = "https://www.yes24.com" + title_elem.get("href")
                
                # 5. 저자
                auth_elem = item.select_one(".info_pubGrp span.info_auth")
                author = auth_elem.text.strip() if auth_elem else ""
                
                # 6. 출판사
                pub_elem = item.select_one(".info_pubGrp span.info_pub")
                publisher = pub_elem.text.strip() if pub_elem else ""
                
                # 7. 출판일
                date_elem = item.select_one(".info_pubGrp span.info_date")
                publish_date = date_elem.text.strip() if date_elem else ""
                
                # 8. 할인율
                sale_elem = item.select_one(".info_price .txt_sale")
                discount_rate = sale_elem.text.strip() if sale_elem else "0%"
                
                # 9. 판매가
                sale_price_elem = item.select_one(".info_price strong.txt_num")
                sale_price = clean_number(sale_price_elem.text) if sale_price_elem else 0
                
                # 10. 정가
                orig_price_elem = item.select_one(".info_price span.txt_num.dash")
                original_price = clean_number(orig_price_elem.text) if orig_price_elem else sale_price
                
                # 11. 판매지수
                sales_index_elem = item.select_one(".info_rating span.saleNum")
                sales_index = clean_number(sales_index_elem.text) if sales_index_elem else 0
                
                # 12. 평점
                rating_elem = item.select_one(".info_rating span.rating_grade .yes_b")
                rating = clean_float(rating_elem.text) if rating_elem else 0.0
                
                # 13. 리뷰 개수
                review_elem = item.select_one(".info_rating span.rating_rvCount .txC_blue")
                review_count = clean_number(review_elem.text) if review_elem else 0
                
                # 수집 데이터 저장
                collected_data.append({
                    "순위": rank,
                    "도서ID": goods_id,
                    "도서명": title,
                    "상세링크": link,
                    "저자": author,
                    "출판사": publisher,
                    "출판일": publish_date,
                    "할인율": discount_rate,
                    "판매가": sale_price,
                    "정가": original_price,
                    "판매지수": sales_index,
                    "평점": rating,
                    "리뷰수": review_count
                })
            
            # 다음 페이지 요청 전 매너 딜레이 (1초)
            time.sleep(1.0)
            
        except Exception as e:
            print(f"[에러] {page} 페이지 수집 중 에러 발생: {e}")
            break
            
    if collected_data:
        # 데이터프레임 변환
        df = pd.DataFrame(collected_data)
        
        # 저장 디렉토리 확인 및 생성
        output_dir = os.path.join("yes24", "data")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "yes24_bestsellers.csv")
        # 엑셀 깨짐을 방지하기 위해 utf-8-sig 인코딩으로 저장
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"[성공] 총 {len(df)}개의 도서 정보를 성공적으로 수집하여 저장했습니다: {output_path}")
        return output_path
    else:
        print("[경고] 수집된 데이터가 없습니다.")
        return None

if __name__ == "__main__":
    scrape_yes24_bestsellers()
