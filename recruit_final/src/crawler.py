"""
이 모듈은 사람인(Saramin) 채용 사이트에서 채용공고 목록(1~35페이지) 및 상세페이지 데이터를 수집하고
SQLite 데이터베이스(recruit.db)에 적재하는 크롤러 프로그램입니다.
여러 직무 카테고리를 지원하며, 상세 내용이 수집되지 않는 공고(외부 링크, 이미지 등)는 목록에서도 제외하여
데이터 정합성을 1:1로 일치시킵니다. 최종적으로 정상 상세 데이터 1000건 수집을 목표로 합니다.

주요 기능:
- 일반 기업 채용 정보 필터링 및 헤드헌팅/파견대행 원천 제외 (company_cd 파라미터 활용)
- 요청 간 0.1~1.0초 랜덤 지연 시간을 적용하여 서버 부하 최소화
- 직무 카테고리(job_category) 컬럼을 추가하고 (rec_idx, job_category) 복합 PK 스키마 설계
- 상세페이지 수집 시 view-detail API 직접 호출 및 정형화 파싱
- 상세 본문 미취득 시 목록(recruit_list) 및 상세(recruit_detail) 테이블에서 실시간 제외(DELETE)
- 수집 성공 개수가 1000건에 도달하면 자동으로 크롤러 동작 조기 중단(break)
"""

import os
import re
import sys
import time
import random
import sqlite3
import json
import requests
from bs4 import BeautifulSoup

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

class SaraminCrawler:
    def __init__(self, db_path=None):
        # 디폴트 DB 파일명을 recruit.db로 설정
        if db_path is None:
            self.db_path = r'c:\workspace\ICB10_22222\recruit_final\data\recruit.db'
        else:
            self.db_path = db_path
            
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.session = requests.Session()
        # recruit_prompt_hr.md의 헤더 정보를 적용
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,de-DE;q=0.6,de;q=0.5",
            "connection": "keep-alive",
            "host": "www.saramin.co.kr",
            "referer": "https://www.saramin.co.kr/zf_user/search?cat_kewd=2198&company_cd=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7&exc_keyword=%EA%B3%B5%EA%B0%9C%EC%B1%84%EC%9A%A9%2C%EB%B6%80%EB%AC%B8%EB%B3%84&panel_type=&search_optional_item=y&search_done=y&panel_count=y&preview=y",
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"19.0.0"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        }
        
        # recruit_prompt_hr.md의 쿠키 데이터 적용
        cookies_dict = {
            "PCID": "17825374927795132397418",
            "_gcl_au": "1.1.1905928679.1782537501",
            "ab180ClientId": "32189bf7-9760-483b-92b4-69c4936e47d1",
            "PHPSESSID": "hq7bg9o0d308pbmqumgf4k45r2va3lkhjko2q97j2prh7n1bi4",
            "_gid": "GA1.3.2097125026.1783948745",
            "RSRVID": "web8|alTpT|alTlu"
        }
        requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies_dict)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 다중 직무 누적을 위해 (rec_idx, job_category) 복합 PK 구조로 변경
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruit_list (
            rec_idx TEXT,
            job_category TEXT,
            company_name TEXT,
            title TEXT,
            link TEXT,
            conditions TEXT,
            job_sector TEXT,
            deadlines TEXT,
            company_type TEXT,
            raw_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (rec_idx, job_category)
        );
        """)
        
        # 상세페이지 본문 테이블 (상세 내용은 rec_idx 단위로 고유하므로 rec_idx를 PK로 사용)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruit_detail (
            rec_idx TEXT PRIMARY KEY,
            detail_content TEXT,
            requirement TEXT,
            preferential TEXT,
            job_description TEXT,
            raw_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(rec_idx) REFERENCES recruit_list(rec_idx)
        );
        """)
        
        conn.commit()
        conn.close()

    def _random_delay(self):
        # 0.1~1.0초 사이의 랜덤 지연
        delay = random.uniform(0.1, 1.0)
        time.sleep(delay)

    def scrape_list(self, job_category='hr', company_type='regular', max_pages=10):
        print(f"\n>>> 목록 수집 시작 (직무 카테고리: {job_category}, 유형: {company_type}, 페이지 수: {max_pages})")
        
        # 직무 카테고리별 cat_kewd 및 exc_keyword 맵핑 고도화
        job_config = {
            'hr': {'cat_kewd': '2198', 'exc_keyword': '공개채용,부문'},
            'dev': {'cat_kewd': '84,87', 'exc_keyword': '공개채용,부문'},
            'acc': {'cat_kewd': '2197', 'exc_keyword': '공개채용,부문'},
            'mkt': {'cat_kewd': '1412', 'exc_keyword': '공개채용,부문,대규모'},  # 마케팅 신규 추가
            'plan': {'cat_kewd': '1633', 'exc_keyword': '공개채용,부문,대규모'}  # 기획 신규 추가
        }
        config = job_config.get(job_category, {'cat_kewd': '2198', 'exc_keyword': '공개채용,부문'})
        cat_kewd = config['cat_kewd']
        exc_keyword = config['exc_keyword']
        
        company_cd_map = {
            'regular': '0,1,2,3,4,5,6,7', # 일반기업 필터링
            'dispatch': '9',
            'headhunting': '10'
        }
        company_cd = company_cd_map.get(company_type, '0,1,2,3,4,5,6,7')
        base_url = "https://www.saramin.co.kr/zf_user/search"
        scraped_items = []
        
        for page in range(1, max_pages + 1):
            print(f"  페이지 {page}/{max_pages} 수집 중...")
            params = {
                "cat_kewd": cat_kewd,
                "company_cd": company_cd,
                "exc_keyword": exc_keyword,
                "panel_type": "",
                "search_optional_item": "y",
                "search_done": "y",
                "panel_count": "y",
                "preview": "y",
                "recruitPage": str(page),
                "recruitSort": "relation",
                "recruitPageCount": "40",
                "inner_com_type": "",
                "searchword": "",
                "show_applied": "",
                "quick_apply": "",
                "except_read": "",
                "ai_head_hunting": "",
                "mainSearch": "n"
            }
            
            try:
                response = self.session.get(base_url, headers=self.headers, params=params, timeout=10)
                if response.status_code != 200:
                    print(f"    [오류] 페이지 {page} 응답 코드: {response.status_code}")
                    break
                    
                soup = BeautifulSoup(response.text, 'lxml')
                items = soup.select('div.item_recruit')
                
                if not items:
                    print("    더 이상 채용 공고가 존재하지 않습니다.")
                    break
                    
                for item in items:
                    rec_idx = item.get('value', '').strip()
                    if not rec_idx:
                        continue
                        
                    corp_a = item.select_one('div.area_corp strong.corp_name a')
                    company_name = corp_a.text.strip() if corp_a else "Unknown"
                    
                    tit_a = item.select_one('div.area_job h2.job_tit a')
                    title = tit_a.text.strip() if tit_a else "No Title"
                    link_href = tit_a.get('href', '') if tit_a else ""
                    full_link = f"https://www.saramin.co.kr{link_href}" if link_href.startswith('/') else link_href
                    
                    conds = [c.text.strip() for c in item.select('div.area_job div.job_condition span')]
                    conditions = " | ".join(conds)
                    
                    sector_spans = [s.text.strip() for s in item.select('div.area_job div.job_sector a')]
                    job_sector = " | ".join(sector_spans)
                    
                    date_span = item.select_one('div.area_job div.job_date span.date')
                    deadlines = date_span.text.strip() if date_span else ""
                    
                    raw_data = {
                        "rec_idx": rec_idx,
                        "job_category": job_category,
                        "company_name": company_name,
                        "title": title,
                        "link": full_link,
                        "conditions": conditions,
                        "job_sector": job_sector,
                        "deadlines": deadlines
                    }
                    
                    scraped_items.append((
                        rec_idx,
                        job_category,
                        company_name,
                        title,
                        full_link,
                        conditions,
                        job_sector,
                        deadlines,
                        company_type,
                        json.dumps(raw_data, ensure_ascii=False)
                    ))
                    
                self._random_delay()
                
            except Exception as e:
                print(f"    [오류] 페이지 {page} 크롤링 중 예외 발생: {e}")
                break
                
        print(f"<<< 목록 수집 완료 (총 {len(scraped_items)}건 발견)")
        return scraped_items

    def save_list_to_db(self, items):
        if not items:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        inserted_count = 0
        for item in items:
            cursor.execute("""
            INSERT OR REPLACE INTO recruit_list (
                rec_idx, job_category, company_name, title, link, conditions, job_sector, deadlines, company_type, raw_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, item)
            inserted_count += cursor.rowcount
            
        conn.commit()
        conn.close()
        print(f"  -> SQLite DB 적재 완료 (총 {len(items)}건 중 {inserted_count}건 반영/업데이트)")

    def parse_job_detail_text(self, detail_text):
        """
        정규표현식을 활용하여 상세 본문에서 자격요건, 우대사항, 담당업무를 분리 파싱합니다.
        """
        patterns = {
            "job_description": r'(?:주요\s*업무|담당\s*업무|주요\s*사항|업무\s*내용|하는\s*일|직무\s*내용|직무\s*소개|모집\s*분야|역할|Role|Responsibilit)',
            "requirement": r'(?:자격\s*요건|지원\s*자격|지원\s*요건|필수\s*사항|필수\s*조건|지원\s*조건|대상자|Requirements)',
            "preferential": r'(?:우대\s*사항|우대\s*조건|우대\s*요건|우대|Preferred)'
        }
        
        matches = []
        for section, pat in patterns.items():
            for m in re.finditer(pat, detail_text, re.IGNORECASE):
                matches.append((m.start(), section))
                
        matches.sort()
        
        sections_data = {
            "job_description": "",
            "requirement": "",
            "preferential": ""
        }
        
        if not matches:
            sections_data["requirement"] = detail_text
            return sections_data
            
        for i, (start_idx, section) in enumerate(matches):
            end_idx = matches[i+1][0] if i + 1 < len(matches) else len(detail_text)
            extracted_text = detail_text[start_idx:end_idx].strip()
            
            if sections_data[section]:
                sections_data[section] += "\n\n" + extracted_text
            else:
                sections_data[section] = extracted_text
                
        return sections_data

    def scrape_and_save_details(self, job_category=None, force_all=False):
        """
        상세페이지 정보를 수집하여 저장합니다. job_category가 지정되면 해당 직무에 속한 대상만 수집합니다.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 다른 직무에 이미 상세페이지가 적재 완료된 중복 공고는 현재 직무 목록에서 원천 배제(스킵)
        if job_category:
            cursor.execute("""
                DELETE FROM recruit_list 
                WHERE job_category = ? 
                  AND rec_idx IN (
                      SELECT l.rec_idx 
                      FROM recruit_list l 
                      JOIN recruit_detail d ON l.rec_idx = d.rec_idx 
                      WHERE l.job_category != ?
                  )
            """, (job_category, job_category))
            conn.commit()
        
        query = """
        SELECT rl.rec_idx, rl.link, rl.job_category
        FROM recruit_list rl
        LEFT JOIN recruit_detail rd ON rl.rec_idx = rd.rec_idx
        """
        params = []
        
        conditions = []
        if not force_all:
            conditions.append("rd.rec_idx IS NULL")
        if job_category:
            conditions.append("rl.job_category = ?")
            params.append(job_category)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        cursor.execute(query, params)
        targets = cursor.fetchall()
        conn.close()
        
        # 상세페이지의 중복 rec_idx 제거 (목록에서는 job_category별 중복이 있을 수 있으나 상세페이지는 한 번만 수집)
        unique_targets = {}
        for rec_idx, link, job_cat in targets:
            unique_targets[rec_idx] = (link, job_cat)
            
        if not unique_targets:
            print("\n>>> 추가로 수집할 공고 상세페이지 정보가 없습니다.")
            return
            
        print(f"\n>>> 상세페이지 수집 시작 (대상: {len(unique_targets)}건, 강제 갱신 모드: {force_all})")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        success_count = 0
        for idx, (rec_idx, (link, job_cat)) in enumerate(unique_targets.items()):
            # 수집 중 루프 내에서 목표한 1000건에 도달했는지 확인
            cursor.execute("""
                SELECT COUNT(*) 
                FROM recruit_detail rd 
                JOIN recruit_list rl ON rd.rec_idx = rl.rec_idx 
                WHERE rl.job_category = ?
            """, (job_cat,))
            current_count = cursor.fetchone()[0]
            if current_count >= 1000:
                print(f"\n>>> [목표 달성] 정상 상세 데이터 1000건에 도달했습니다. (현재: {current_count}건)")
                print(">>> 상세페이지 수집을 종료합니다.")
                break
                
            print(f"  [{idx+1}/{len(unique_targets)}] 상세 수집 중 (rec_idx: {rec_idx}, 누적 성공: {current_count}건)...")
            
            detail_content = ""
            detail_html = ""
            detail_url = f"https://www.saramin.co.kr/zf_user/jobs/relay/view-detail?rec_idx={rec_idx}"
            
            try:
                response = self.session.get(detail_url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    user_content_div = soup.select_one('div.user_content')
                    
                    if user_content_div:
                        detail_content = user_content_div.text.strip()
                        detail_html = str(user_content_div)
                    else:
                        detail_content = soup.get_text('\n').strip()
                        detail_html = response.text
                        
            except Exception as e:
                print(f"    [오류] 상세페이지({detail_url}) 요청 중 예외 발생: {e}")
                
            if not detail_content:
                print(f"    [경고] 본문 텍스트를 추출하지 못했습니다. (rec_idx: {rec_idx}) -> 목록 및 상세에서 제외 처리")
                # 텍스트 추출에 실패한 공고는 recruit_list에서 즉시 삭제하여 1:1 정합성을 맞춤
                cursor.execute("DELETE FROM recruit_list WHERE rec_idx = ? AND job_category = ?", (rec_idx, job_cat))
                cursor.execute("DELETE FROM recruit_detail WHERE rec_idx = ?", (rec_idx,))
                conn.commit()
            else:
                cleaned_content = re.sub(r'\n{3,}', '\n\n', detail_content).strip()
                parsed_sections = self.parse_job_detail_text(cleaned_content)
                raw_json_data = {
                    "rec_idx": rec_idx,
                    "has_user_content": True,
                    "summary_snippet": cleaned_content[:200]
                }
                
                cursor.execute("""
                INSERT OR REPLACE INTO recruit_detail (
                    rec_idx, detail_content, requirement, preferential, job_description, raw_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    rec_idx,
                    cleaned_content,
                    parsed_sections["requirement"],
                    parsed_sections["preferential"],
                    parsed_sections["job_description"],
                    json.dumps(raw_json_data, ensure_ascii=False)
                ))
                conn.commit()
                success_count += 1
                
            self._random_delay()
            
        # 상세 수집 완료 후, 상세 정보가 수집되지 않은(시도되지 않았거나 실패한) 공고를 목록 테이블에서 최종 삭제하여 1:1 정합성 보장
        cursor = conn.cursor()
        if job_category:
            cursor.execute("""
                DELETE FROM recruit_list 
                WHERE job_category = ? 
                  AND rec_idx NOT IN (SELECT rec_idx FROM recruit_detail);
            """, (job_category,))
        else:
            cursor.execute("""
                DELETE FROM recruit_list 
                WHERE rec_idx NOT IN (SELECT rec_idx FROM recruit_detail);
            """)
        conn.commit()
        conn.close()
        print(f"<<< 상세페이지 수집 루프 완료 (이번 세션 반영: {success_count}건)")

    def print_summary_report(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM recruit_list;")
        total_list = cursor.fetchone()[0]
        
        cursor.execute("SELECT job_category, COUNT(*) FROM recruit_list GROUP BY job_category;")
        category_counts = cursor.fetchall()
        
        cursor.execute("SELECT company_type, COUNT(*) FROM recruit_list GROUP BY company_type;")
        type_counts = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM recruit_detail;")
        total_detail = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN requirement != '' AND requirement IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN preferential != '' AND preferential IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN job_description != '' AND job_description IS NOT NULL THEN 1 ELSE 0 END)
            FROM recruit_detail;
        """)
        parsed_stats = cursor.fetchone()
        
        conn.close()
        
        print("\n" + "="*50)
        print("          [ 사람인 채용공고 수집 결과 리포트 ]")
        print("="*50)
        print(f"  * 대상 DB 파일 경로: {self.db_path}")
        print(f"  * 수집된 전체 공고 목록 수: {total_list}건")
        
        print("  * 직무 카테고리별 공고 수:")
        for job_cat, cnt in category_counts:
            cat_kor = {"hr": "인사/HR", "dev": "개발", "acc": "회계/재무", "mkt": "마케팅", "plan": "기획"}.get(job_cat, job_cat)
            print(f"    - {cat_kor}: {cnt}건")
            
        print("  * 채용 유형별 공고 수:")
        for c_type, cnt in type_counts:
            type_kor = {"regular": "일반", "dispatch": "파견/대행", "headhunting": "헤드헌팅"}.get(c_type, c_type)
            print(f"    - {type_kor}: {cnt}건")
            
        print(f"  * 상세 내용 수집 및 파싱 완료 수: {total_detail}건")
        if parsed_stats:
            req_cnt, pref_cnt, job_cnt = parsed_stats
            print(f"    - 자격요건 추출 성공 건수: {req_cnt or 0}건")
            print(f"    - 우대사항 추출 성공 건수: {pref_cnt or 0}건")
            print(f"    - 담당업무 추출 성공 건수: {job_cnt or 0}건")
        print("="*50 + "\n")

if __name__ == '__main__':
    # 명령행 인자로 job_category를 받음 (기본값: 'hr')
    job_cat = 'hr'
    if len(sys.argv) > 1:
        job_cat = sys.argv[1].strip().lower()
        if job_cat not in ['hr', 'dev', 'acc', 'mkt', 'plan']:
            print(f"[오류] 지원하지 않는 직무 카테고리입니다: {job_cat} (지원: hr, dev, acc, mkt, plan)")
            sys.exit(1)
            
    crawler = SaraminCrawler()
    
    # 데이터 일치성 보장 및 1000건 재적재를 위해, 수집 시작 전 기존 실행 카테고리 데이터 초기화
    conn = sqlite3.connect(crawler.db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recruit_list WHERE job_category = ?;", (job_cat,))
    cursor.execute("DELETE FROM recruit_detail WHERE rec_idx NOT IN (SELECT rec_idx FROM recruit_list);")
    conn.commit()
    conn.close()
    
    cat_kor = {"hr": "인사/HR", "dev": "개발", "acc": "회계/재무", "mkt": "마케팅", "plan": "기획"}.get(job_cat, job_cat)
    print(f"\n>>> 기존 '{cat_kor}' 직무 관련 데이터를 깨끗하게 초기화했습니다. (1000건 재수집 시작)")
    
    # 1. 목록 수집 및 저장 (목표 1000건 달성을 위해 페이지 범위를 35페이지로 확대)
    items = crawler.scrape_list(job_category=job_cat, company_type='regular', max_pages=35)
    crawler.save_list_to_db(items)
    
    # 2. 상세페이지 view-detail 기반 재수집 및 파싱 업데이트 (성공한 것만 남기고 실패는 삭제)
    crawler.scrape_and_save_details(job_category=job_cat, force_all=True)
    
    # 3. 결과 리포트 출력
    crawler.print_summary_report()
