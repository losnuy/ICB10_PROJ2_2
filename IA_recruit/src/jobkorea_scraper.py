"""
잡코리아(JobKorea) 채용공고 데이터를 수집하여 SQLite 데이터베이스에 저장하는 스크립트입니다.
주요 기능:
- "내부감사" 검색 키워드 기반 1~10페이지 채용공고 목록 수집 (Next.js RPC 데이터 파싱)
- 각 채용공고의 상세페이지(GI_Read) main 태그 본문 텍스트 및 HTML 수집
- 별도의 SQLite 데이터베이스(jobkorea_recruit.db)에 UPSERT 방식으로 데이터 중복 제거 및 적재
- 수집 통계 및 결과를 마크다운 리포트로 자동 출력
"""

import os
import re
import time
import random
import sqlite3
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class JobKoreaScraper:
    def __init__(self, db_path="IA_recruit/data/jobkorea_recruit.db"):
        self.db_path = db_path
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,de-DE;q=0.6,de;q=0.5",
            "cache-control": "max-age=0",
            "referer": "https://www.jobkorea.co.kr/",
            "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        }
        self._init_db()

    def _init_db(self):
        """데이터베이스 및 테이블이 존재하지 않는 경우 생성합니다."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. 공고 요약 정보 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recruits (
                recruit_id TEXT PRIMARY KEY,
                company_name TEXT,
                title TEXT,
                url TEXT,
                conditions TEXT,
                raw_json TEXT,
                updated_at TEXT
            )
        """)
        
        # 2. 공고 상세 내용 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recruit_details (
                recruit_id TEXT PRIMARY KEY,
                detail_content TEXT,
                detail_html TEXT,
                updated_at TEXT,
                FOREIGN KEY (recruit_id) REFERENCES recruits (recruit_id)
            )
        """)
        
        conn.commit()
        conn.close()

    def _extract_jobs_from_html(self, html):
        """
        Next.js RPC 데이터(self.__next_f.push 블록)를 분석하여
        JOB_LIST 쿼리 데이터에 포함된 채용공고 리스트를 파싱하여 리턴합니다.
        """
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")
        
        # self.__next_f.push 데이터를 모아서 결합
        next_f_data = []
        for sc in scripts:
            sc_text = sc.string if sc.string else ""
            if "self.__next_f.push" in sc_text:
                matches = re.findall(r'self\.__next_f\.push\(\[(.*)\]\)', sc_text, re.DOTALL)
                for m in matches:
                    first_comma = m.find(",")
                    if first_comma != -1:
                        raw_str = m[first_comma+1:].strip()
                        try:
                            parsed_list = json.loads("[" + m + "]")
                            if len(parsed_list) >= 2:
                                next_f_data.append(parsed_list[1])
                        except:
                            str_match = re.match(r'^["\'`](.*)["\'`]$', raw_str, re.DOTALL)
                            if str_match:
                                next_f_data.append(str_match.group(1))
                            else:
                                next_f_data.append(raw_str)
                                
        combined_text = "\n".join(next_f_data)
        
        # 'JOB_LIST' 쿼리 캐시 객체 파싱
        # "queries" 단어가 들어있는 대형 JSON 문자열 추출
        pos = 0
        jobs = []
        
        while True:
            pos = combined_text.find('"queries"', pos)
            if pos == -1:
                break
                
            # 중괄호 밸런스 맞춰서 JSON 블록 추출
            json_start = -1
            for i in range(pos, 0, -1):
                if combined_text[i] == '{':
                    json_start = i
                    break
                    
            if json_start != -1:
                bracket_count = 0
                json_end = -1
                for i in range(json_start, len(combined_text)):
                    if combined_text[i] == '{':
                        bracket_count += 1
                    elif combined_text[i] == '}':
                        bracket_count -= 1
                        if bracket_count == 0:
                            json_end = i + 1
                            break
                
                if json_end != -1:
                    json_str = combined_text[json_start:json_end]
                    try:
                        data = json.loads(json_str)
                        queries = data.get("queries", [])
                        for q in queries:
                            q_key = q.get("queryKey")
                            if isinstance(q_key, list) and len(q_key) > 0 and q_key[0] == "JOB_LIST":
                                state = q.get("state", {})
                                q_data = state.get("data", {})
                                content = q_data.get("content", [])
                                if content:
                                    jobs.extend(content)
                    except:
                        pass
                    pos = json_end
                else:
                    pos += 9
            else:
                pos += 9
                
        return jobs

    def crawl_list(self, page=1):
        """
        특정 페이지의 잡코리아 채용공고 목록을 수집하여 DB에 저장합니다.
        """
        print(f"[목록 수집] 잡코리아 {page}페이지 요청 중...")
        url = "https://www.jobkorea.co.kr/Search/"
        params = {
            "stext": "내부감사",
            "tabType": "recruit",
            "Page_No": str(page)
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                print(f"[에러] 목록 요청 실패 (상태 코드: {response.status_code})")
                return 0

            # RPC 데이터를 파싱하여 채용공고 추출
            jobs = self._extract_jobs_from_html(response.text)
            print(f"[목록 수집] {page}페이지에서 {len(jobs)}개의 공고 추출 성공")
            
            if not jobs:
                return 0
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            success_count = 0
            for job in jobs:
                try:
                    recruit_id = str(job.get("id"))
                    if not recruit_id:
                        continue
                        
                    company_name = job.get("companyName", job.get("postingCompanyName", ""))
                    title = job.get("title", "")
                    url_full = f"https://www.jobkorea.co.kr/Recruit/GI_Read/{recruit_id}"
                    
                    # 채용 조건 가공 (분류, 경력, 학력 등)
                    classification = job.get("jobClassificationOrIndustry", "")
                    career = job.get("careerRange", "")
                    if career == 100:
                        career_str = "경력무관"
                    elif career:
                        career_str = f"경력 {career}년↑"
                    else:
                        career_str = ""
                        
                    conditions_parts = [c.strip() for c in classification.split(",") if c.strip()]
                    if career_str:
                        conditions_parts.append(career_str)
                    conditions = ", ".join(conditions_parts)
                    
                    # 원본 데이터를 JSON 형태로 패키징
                    raw_json = json.dumps(job, ensure_ascii=False)
                    
                    # DB UPSERT 적재
                    cursor.execute("""
                        INSERT INTO recruits (recruit_id, company_name, title, url, conditions, raw_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                        ON CONFLICT(recruit_id) DO UPDATE SET
                            company_name=excluded.company_name,
                            title=excluded.title,
                            url=excluded.url,
                            conditions=excluded.conditions,
                            raw_json=excluded.raw_json,
                            updated_at=datetime('now', 'localtime')
                    """, (recruit_id, company_name, title, url_full, conditions, raw_json))
                    
                    success_count += 1
                except Exception as e:
                    print(f"[오류] 개별 항목 파싱 실패: {e}")
                    
            conn.commit()
            conn.close()
            return success_count
            
        except Exception as e:
            print(f"[에러] 목록 페이지 {page} 수집 중 예외 발생: {e}")
            return 0

    def crawl_detail(self, recruit_id):
        """
        특정 공고 ID의 잡코리아 상세페이지(main 태그)를 호출하여 DB에 적재합니다.
        """
        url = f"https://www.jobkorea.co.kr/Recruit/GI_Read/{recruit_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                print(f"[에러] 상세페이지 요청 실패 (ID: {recruit_id}, 상태 코드: {response.status_code})")
                return False
                
            soup = BeautifulSoup(response.text, 'html.parser')
            main_el = soup.select_one('main')
            
            if main_el:
                detail_content = main_el.get_text('\n', strip=True)
                detail_html = str(main_el)
            else:
                detail_content = soup.get_text('\n', strip=True)
                detail_html = response.text
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # DB UPSERT 적재
            cursor.execute("""
                INSERT INTO recruit_details (recruit_id, detail_content, detail_html, updated_at)
                VALUES (?, ?, ?, datetime('now', 'localtime'))
                ON CONFLICT(recruit_id) DO UPDATE SET
                    detail_content=excluded.detail_content,
                    detail_html=excluded.detail_html,
                    updated_at=datetime('now', 'localtime')
            """, (recruit_id, detail_content, detail_html))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[에러] 상세페이지(ID: {recruit_id}) 수집 중 예외 발생: {e}")
            return False

    def crawl_all_details(self):
        """
        DB에 등록된 모든 공고 목록 중 상세 내용이 아직 없는 항목들을 순회하며 수집합니다.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 목록에 있지만 상세 테이블에 없는 recruit_id 조회
        cursor.execute("""
            SELECT r.recruit_id, r.company_name, r.title 
            FROM recruits r
            LEFT JOIN recruit_details d ON r.recruit_id = d.recruit_id
            WHERE d.recruit_id IS NULL
        """)
        targets = cursor.fetchall()
        conn.close()
        
        total_targets = len(targets)
        print(f"[상세 수집] 총 {total_targets}개의 신규 상세페이지 수집 대상 발견")
        
        success_count = 0
        for idx, (recruit_id, company, title) in enumerate(targets, 1):
            print(f"[상세 수집] ({idx}/{total_targets}) {company} - {title[:20]}... 수집 중")
            success = self.crawl_detail(recruit_id)
            if success:
                success_count += 1
            
            # 0.1초 ~ 1.0초 랜덤 지연을 적용해 네트워크 및 서버 부담 경감
            time.sleep(random.uniform(0.1, 1.0))
            
        print(f"[상세 수집 완료] 총 {total_targets}개 중 {success_count}개 수집 성공")
        return success_count

    def generate_report(self, report_path="IA_recruit/report/jobkorea_scraping_report.md"):
        """
        DB 통계 및 수집 완료 결과를 마크다운 파일로 생성합니다.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 총 목록 수
        cursor.execute("SELECT COUNT(*) FROM recruits")
        total_recruits = cursor.fetchone()[0]
        
        # 총 상세 페이지 수
        cursor.execute("SELECT COUNT(*) FROM recruit_details")
        total_details = cursor.fetchone()[0]
        
        # 최근 저장된 5개 샘플
        cursor.execute("""
            SELECT r.company_name, r.title, r.conditions, r.updated_at 
            FROM recruits r
            ORDER BY r.updated_at DESC
            LIMIT 5
        """)
        samples = cursor.fetchall()
        conn.close()
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        report_content = f"""# 잡코리아 채용공고 수집 결과 보고서

- **수집 대상 키워드**: 내부감사
- **수집 실행 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **데이터베이스 경로**: `{self.db_path}`

## 1. 수집 요약 통계

| 항목 | 수집 건수 |
| :--- | :--- |
| **채용공고 요약 목록 (recruits)** | {total_recruits} 건 |
| **채용공고 세부 상세 (recruit_details)** | {total_details} 건 |

## 2. 최근 수집/업데이트된 공고 샘플 (최대 5개)

| 기업명 | 채용공고 제목 | 채용 조건 | 수집 시각 |
| :--- | :--- | :--- | :--- |
"""
        for company, title, cond, updated in samples:
            title_clean = title.replace('|', '\\|')
            cond_clean = cond.replace('|', '\\|')
            report_content += f"| {company} | {title_clean} | {cond_clean} | {updated} |\n"
            
        report_content += """
## 3. 데이터베이스 테이블 구조

### recruits (채용공고 목록)
- `recruit_id` (TEXT, PK): 잡코리아 채용공고 ID (`id`)
- `company_name` (TEXT): 기업명
- `title` (TEXT): 채용공고 제목
- `url` (TEXT): 상세페이지 URL
- `conditions` (TEXT): 요약 채용조건
- `raw_json` (TEXT): 수집된 JSON 원본 데이터
- `updated_at` (TEXT): 최종 업데이트 일시

### recruit_details (채용공고 상세내용)
- `recruit_id` (TEXT, PK): 잡코리아 채용공고 ID (recruits 테이블 참조)
- `detail_content` (TEXT): 본문 텍스트 내용
- `detail_html` (TEXT): 본문 HTML 원본
- `updated_at` (TEXT): 최종 업데이트 일시
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"[리포트 생성 완료] 리포트 파일 경로: {report_path}")
