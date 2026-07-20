"""
네이버 API 자격증/어학 키워드 주간 통합 데이터 수집 파이프라인
===================================================================
[스펙 기준: project2/docs/api_automation_prompt.md]

주요 기능:
1. keyword_extraction_report_v2.md 파일에서 직무별 자격증 및 어학 스펙 키워드 자동 파싱
2. 지표 ① (주간 카페 언급량): 네이버 카페글 검색 API를 통해 키워드 단독 검색 후 취업 카페 필터링 및 주차별 누적 집계
3. 지표 ② (주간 검색 트렌드): [키워드 + "채용"], [키워드 + "스펙"] 등 구직 목적 행동어 조합으로 네이버 데이터랩 API 주간 트렌드 수집
4. 두 지표를 주차 시작일(Date) 및 키워드 기준으로 매핑 후 최종 취업관심도 지수(cafe_weekly_count * trend_ratio) 계산
5. project2/data/integrated/naver_weekly_insights.json 경로에 저장
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import re
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# 표준 출력 UTF-8 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# .env 로드
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path)

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# 동적 기간 설정 (시작일 2026-01-01, 종료일 어제 날짜)
TODAY = datetime.now()
YESTERDAY = TODAY - timedelta(days=1)
START_DATE = "2026-01-01"
END_DATE = YESTERDAY.strftime("%Y-%m-%d")

# 취업 카페명 목록 (필터링용)
TARGET_CAFES = ["독취사", "스펙업", "공준모", "취업대학교", "아웃캠퍼스", "취업", "스펙", "독금사", "공기업"]

def get_monday_of_week(date_str: str) -> str:
    """주어진 날짜 문자열(YYYY-MM-DD 또는 YYYYMMDD)이 속한 주의 월요일 날짜를 반환합니다."""
    date_str = date_str.replace("-", "")
    dt = datetime.strptime(date_str, "%Y%m%d")
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")

def parse_keywords_from_markdown(md_path: Path) -> dict:
    """
    keyword_extraction_report_v2.md 파일에서 직무별 자격증 및 어학 스펙 키워드 리스트를 자동 파싱합니다.
    """
    if not md_path.exists():
        print(f"  ⚠️  키워드 리포트 파일을 찾을 수 없습니다: {md_path}")
        return {}
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 직무 섹션 분할 (백틱과 괄호 정규식 수정)
    job_sections = re.split(r'### \d+\)\s+(.+?)\s*직무\s*\(\x60([^\x60\)]+)\x60\)', content)
    
    results = {}
    if len(job_sections) > 1:
        for i in range(1, len(job_sections), 3):
            job_name = job_sections[i].strip()
            job_code = job_sections[i+1].strip()
            job_body = job_sections[i+2]
            
            # 자격증 및 어학 스펙 섹션 검색 (\n\s*--- 전방 탐색 적용하여 구분선 충돌 방지)
            cert_section = re.search(r'#### \[자격증 및 어학 스펙 [^\]]+\](.*?)(?=###|\Z|\n\s*---)', job_body, re.DOTALL)
            if cert_section:
                table_content = cert_section.group(1)
                keywords = []
                for line in table_content.split('\n'):
                    if '|' in line and not line.strip().startswith('| :---'):
                        parts = [p.strip() for p in line.split('|')]
                        # 순위가 숫자인지 확인하여 테이블 내용 행 필터링
                        if len(parts) >= 5 and parts[1].isdigit():
                            rep_kw = parts[2].replace('\x60', '').strip()
                            synonyms = [s.strip() for s in parts[3].replace('\x60', '').split(',') if s.strip()]
                            keywords.append((rep_kw, synonyms))
                results[f"{job_name}({job_code})"] = keywords
    return results

def fetch_cafe_weekly_count(keyword: str) -> dict:
    """
    네이버 카페글 검색 API를 호출하여 자격증 키워드 단독 검색 결과를 주간(Weekly)으로 집계합니다.
    """
    encoded_q = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={encoded_q}&display=100&sort=date"
    
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    req.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
    
    weekly_counts = {}
    try:
        response = urllib.request.urlopen(req, timeout=10)
        result = json.loads(response.read().decode("utf-8"))
        for item in result.get("items", []):
            cafename = item.get("cafename", "")
            # 취업 관련 카페 필터링
            if any(cafe in cafename for cafe in TARGET_CAFES):
                pub_raw = item.get("postdate", "")
                if len(pub_raw) == 8:
                    monday_str = get_monday_of_week(pub_raw)
                    if START_DATE <= monday_str <= END_DATE:
                        weekly_counts[monday_str] = weekly_counts.get(monday_str, 0) + 1
    except Exception as e:
        print(f"    ⚠️ 카페 API 오류 [{keyword}]: {e}")
    return weekly_counts

def fetch_datalab_weekly_trend(job_name: str, keyword: str, synonyms: list) -> list:
    """
    네이버 데이터랩 API를 활용하여 구직 목적 행동어 조합 검색어 트렌드를 수집합니다.
    조합어 예시: ["컴활 채용", "컴활 스펙", "컴활 취업", "컴퓨터활용능력 채용"] 등
    """
    url = "https://openapi.naver.com/v1/datalab/search"
    
    # 검색어 조합어 자동 생성 (K + " 채용", K + " 스펙", K + " 취업" 등)
    # 데이터랩은 그룹당 키워드 5개까지 지원하므로, 대표 키워드와 핵심 동의어로 구성
    base_terms = [keyword] + synonyms[:2]
    search_terms = []
    for term in base_terms:
        search_terms.append(f"{term} 채용")
        search_terms.append(f"{term} 스펙")
        search_terms.append(f"{term} 취업")
    
    # 중복 제거 및 5개 제한
    search_terms = list(dict.fromkeys(search_terms))[:5]
    
    keyword_groups = [{"groupName": keyword, "keywords": search_terms}]
    
    payload = {
        "startDate": START_DATE,
        "endDate": END_DATE,
        "timeUnit": "week",  # 주간 단위 수집
        "keywordGroups": keyword_groups
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    req.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
    req.add_header("Content-Type", "application/json")
    
    try:
        response = urllib.request.urlopen(req, data=body, timeout=10)
        result = json.loads(response.read().decode("utf-8"))
        records = []
        for row in result.get("results", [{}])[0].get("data", []):
            records.append({
                "date": row["period"],  # 주차 시작일 (월요일)
                "job": job_name,
                "keyword": keyword,
                "trend_ratio": row["ratio"]
            })
        return records
    except Exception as e:
        print(f"    ⚠️ 데이터랩 API 오류 [{keyword}]: {e}")
        return []

def generate_mock_weekly_data(keyword_map: dict) -> list:
    """API 키 미지정 시 검증을 위한 목업 주간 데이터를 생성합니다."""
    import random
    random.seed(42)
    
    dates = pd.date_range(START_DATE, END_DATE, freq="W-MON").strftime("%Y-%m-%d").tolist()
    records = []
    
    for job, kws in keyword_map.items():
        for keyword, _ in kws:
            # 주간 카페 언급량 목업 (자주 검색되는 어학 등은 더 높은 가치 부여)
            base_cafe = random.randint(1, 15) if keyword in ["토익", "영어회화", "오픽", "컴퓨터활용능력"] else random.randint(0, 3)
            for date in dates:
                cafe_val = max(0, base_cafe + random.randint(-2, 5))
                trend_val = round(random.uniform(2, 95), 4)
                records.append({
                    "date": date,
                    "job": job,
                    "keyword": keyword,
                    "cafe_weekly_count": cafe_val,
                    "trend_ratio": trend_val,
                    "employment_interest_index": round(cafe_val * trend_val, 4)
                })
    return records

def main():
    md_path = Path("project2/report/keyword_extraction_report_v2.md")
    print("[1단계] 키워드 목록 자동 파싱 시작...")
    keyword_map = parse_keywords_from_markdown(md_path)
    
    if not keyword_map:
        print("❌ 키워드 목록을 파싱하지 못했습니다. 프로그램을 종료합니다.")
        return
    
    total_jobs = len(keyword_map)
    total_kws = sum(len(v) for v in keyword_map.values())
    print(f"✅ 파싱 완료: 총 {total_jobs}개 직무, {total_kws}개 자격증/어학 키워드 추출 성공")
    
    # API 키 유효성 사전 검사
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("=================================================================")
        print("❌ [.env API 키 미설정]")
        print("   - 네이버 API 키가 확인되지 않아 목업(Mock) 주간 데이터를 생성합니다.")
        print("=================================================================")
        records = generate_mock_weekly_data(keyword_map)
        is_mock = True
    else:
        is_mock = False
        print("\n[2단계] 네이버 API 실시간 데이터 수집 시작...")
        
        # 고유 키워드 목록 생성 (카페 검색 중복 제거용)
        all_unique_kws = list({kw for kws in keyword_map.values() for kw, _ in kws})
        cafe_weekly_lookup = {}  # (keyword, date) -> count
        
        # 지표 ① 수집
        print(f"▶ 지표 ① (주간 카페 유입량) 수집 중... (고유 키워드 {len(all_unique_kws)}개)")
        for idx, keyword in enumerate(all_unique_kws, 1):
            print(f"  [{idx}/{len(all_unique_kws)}] 카페 키워드 검색: '{keyword}'", end=" ", flush=True)
            weekly_counts = fetch_cafe_weekly_count(keyword)
            for date_str, count in weekly_counts.items():
                cafe_weekly_lookup[(keyword, date_str)] = count
            total_cnt = sum(weekly_counts.values())
            print(f"✅ (누적 {total_cnt}건)")
            time.sleep(0.5)
            
        # 지표 ② 수집 및 병합
        print(f"\n▶ 지표 ② (주간 검색 트렌드) 수집 및 병합 중...")
        records = []
        cur_idx = 0
        for job, kws in keyword_map.items():
            print(f"  직무: {job}")
            for keyword, synonyms in kws:
                cur_idx += 1
                print(f"    [{cur_idx}/{total_kws}] 트렌드 조합어 검색: '{keyword}'", end=" ", flush=True)
                trend_records = fetch_datalab_weekly_trend(job, keyword, synonyms)
                
                # 병합 및 지수 계산
                for rec in trend_records:
                    date_val = rec["date"]
                    # 지표 ① 매핑
                    cafe_count = cafe_weekly_lookup.get((keyword, date_val), 0)
                    rec["cafe_weekly_count"] = cafe_count
                    # 파생 변수 계산: 최종 취업관심도 지수 = 카페 유입량 * 검색 트렌드
                    rec["employment_interest_index"] = round(cafe_count * rec["trend_ratio"], 4)
                    records.append(rec)
                
                print(f"✅ (트렌드 {len(trend_records)}주차 수집)")
                time.sleep(0.5)

    # DataFrame 변환 후 컬럼 정렬
    df = pd.DataFrame(records)
    if not df.empty:
        df = df[["date", "job", "keyword", "cafe_weekly_count", "trend_ratio", "employment_interest_index"]]
    
    # JSON 파일 저장 (orient='records')
    save_dir = Path("project2/data/integrated")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / "naver_weekly_insights.json"
    
    result_list = df.to_dict(orient="records")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=2)
        
    print("\n=================================================================")
    print(f"📦 {'[MOCK] ' if is_mock else ''}주간 시계열 데이터 저장 완료!")
    print(f"  파일 경로 : {save_path}")
    print(f"  레코드 수  : {len(result_list):,}건")
    print(f"  수집 기간  : {START_DATE} ~ {END_DATE}")
    print(f"  컬럼 구조  : {list(df.columns)}")
    print("=================================================================")
    print("\n[최근 데이터 샘플 (마지막 5행)]")
    print(df.tail(5).to_string(index=False))

if __name__ == "__main__":
    main()
