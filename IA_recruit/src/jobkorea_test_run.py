"""
잡코리아 채용공고 수집 스크립트 실행 및 1페이지 단위 1차 검증 테스트 엔트리포인트 파일입니다.
동작 흐름:
1. 1페이지를 먼저 수집하여 정상 수집 여부를 1차 검증합니다.
2. 성공 시, 2~10페이지까지의 잡코리아 공고 목록을 수집합니다.
3. 수집된 잡코리아 공고 목록을 순회하며 상세페이지(main 태그) 정보를 수집합니다.
4. 모든 작업이 완료되면 최종 마크다운 리포트를 생성합니다.
"""

import sys
import os
import time
import random
# 부모 디렉토리를 path에 추가하여 scraper 모듈 로드 가능하도록 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.jobkorea_scraper import JobKoreaScraper

def main():
    print("=== 잡코리아 내부감사 채용공고 수집 프로세스 시작 ===")
    scraper = JobKoreaScraper()
    
    # 1. 1페이지 테스트 수집
    print("\n--- [단계 1] 1페이지 테스트 수집 및 검증 ---")
    page1_count = scraper.crawl_list(page=1)
    
    if page1_count > 0:
        print(f"[검증 성공] 1페이지에서 {page1_count}개의 공고를 수집하였습니다.")
    else:
        print("[검증 실패] 1페이지 수집 건수가 0개입니다. 프로세스를 중단합니다.")
        return

    # 대기 후 다음 작업 진행
    time.sleep(random.uniform(1.0, 2.0))
    
    # 2. 2~10페이지 수집
    print("\n--- [단계 2] 2~10페이지 공고 목록 수집 ---")
    total_list_count = page1_count
    for page in range(2, 11):
        count = scraper.crawl_list(page=page)
        total_list_count += count
        time.sleep(random.uniform(0.5, 1.5))
        
    print(f"[목록 수집 완료] 총 {total_list_count}개의 공고 목록이 수집/갱신되었습니다.")

    # 3. 상세페이지 수집
    print("\n--- [단계 3] 상세페이지 내용 수집 ---")
    total_detail_count = scraper.crawl_all_details()
    print(f"[상세 수집 완료] 총 {total_detail_count}개의 상세페이지 정보가 수집/갱신되었습니다.")

    # 4. 리포트 생성
    print("\n--- [단계 4] 요약 리포트 생성 ---")
    scraper.generate_report()
    
    print("\n=== 모든 수집 프로세스가 성공적으로 완료되었습니다! ===")

if __name__ == "__main__":
    main()
