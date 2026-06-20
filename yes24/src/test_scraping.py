"""
YES24 베스트셀러 도서 목록에서 가격, 평점, 리뷰 수의 HTML 구조를 정밀 분석하기 위한 테스트 모듈입니다.

이 모듈은 다음 기능을 수행합니다:
- 도서 가격 정보 태그 추출 및 구조 파악
- 도서 평점(별점) 및 리뷰 수 정보 태그 추출 및 구조 파악
"""

import requests
from bs4 import BeautifulSoup

url = "https://www.yes24.com/Product/Category/BestSeller"
params = {
    "categoryNumber": "001",
    "pageNumber": "1",
    "pageSize": "24"
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

res = requests.get(url, params=params, headers=headers)
soup = BeautifulSoup(res.text, "lxml")

items = soup.select("#yesBestList > li")
if not items:
    items = soup.select("ul.ycg_list > li")

if items:
    first_item = items[0]
    print("--- First Item Text (for reference) ---")
    print(repr(first_item.text.strip()))
    
    print("\n--- Price Information Area ---")
    price_area = first_item.select_one(".info_row.info_price") or first_item.select_one("[class*='price']")
    if price_area:
        print(price_area.prettify())
    else:
        print("No price area found")

    print("\n--- Rating & Review Area ---")
    rating_area = first_item.select_one(".info_row.info_rating") or first_item.select_one("[class*='rating']")
    if rating_area:
        print(rating_area.prettify())
    else:
        print("No rating area found")
else:
    print("No items found.")
