"""
이 모듈은 사람인 회계 채용 공고 데이터를 바탕으로 범주화 분석을 수행하는 스크립트입니다.

주요 기능:
- 데이터베이스(recruit.db) 연동 및 텍스트 데이터 로드
- 상세 요강 텍스트 파싱을 통한 경력/학력 범주 현황 분석
- 사전 정의된 자격증, 활용 툴, 세부 직무 실무 키워드의 빈도 카운팅 (Top 20 산출)
- 동일한 의미의 단어를 묶어주는 동의어(시소러스) 매핑 가이드 제안
- 결과를 터미널에 출력하고 'accounting_keywords.json' 파일로 저장
"""

import os
import re
import json
import sqlite3
from collections import Counter

# 경로 설정
DB_PATH = os.path.join("recruit", "data", "recruit.db")
OUTPUT_JSON_PATH = os.path.join("recruit", "accounting_keywords.json")


def load_texts():
    """
    recruit.db 에서 분석 대상 텍스트 데이터를 로드합니다.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB 파일이 존재하지 않습니다: {DB_PATH}")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 목록의 title 과 상세의 detail_content 를 연계하여 텍스트 분석
    cursor.execute("""
        SELECT l.title, d.detail_content 
        FROM recruit_list l
        LEFT JOIN recruit_detail d ON l.rec_idx = d.rec_idx
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def parse_metadata(rows):
    """
    경력 및 학력 요건을 파싱하여 범주별 빈도를 산출합니다.
    """
    exp_counter = Counter()
    edu_counter = Counter()
    
    for title, content in rows:
        text = str(title) + " " + str(content or "")
        
        # 1. 경력 파싱
        exp_val = "경력무관"
        if "경력무관" in text or "경력 무관" in text or "무관" in text:
            exp_val = "경력무관"
        elif "신입" in text and "경력" not in text:
            exp_val = "신입Only"
        else:
            match = re.search(r"경력\s*(?:(?:[0-9]~\s*)?([0-9]+)\s*년)", text)
            if match:
                exp_val = f"경력 {match.group(1)}년 이상"
            else:
                match2 = re.search(r"([0-9]+)\s*년\s*(?:이상|경력)", text)
                if match2:
                    exp_val = f"경력 {match2.group(1)}년 이상"
                elif "경력" in text:
                    exp_val = "경력(년수무관)"
                    
        exp_counter[exp_val] += 1
        
        # 2. 학력 파싱
        edu_val = "학력무관"
        if "고졸" in text or "고등학교" in text:
            edu_val = "고졸 이상"
        elif "전문대" in text or "초대졸" in text or "2년제" in text or "3년제" in text:
            edu_val = "전문대졸 이상"
        elif "대졸" in text or "4년제" in text or "학사" in text:
            edu_val = "대졸(4년) 이상"
        elif "석사" in text or "대학원" in text:
            edu_val = "석사 이상"
            
        edu_counter[edu_val] += 1

    return dict(exp_counter), dict(edu_counter)


def count_keywords(rows):
    """
    자격증, 활용 툴, 세부 직무 키워드를 정밀 집계합니다.
    """
    # 키워드 사전 정의
    cert_keywords = {
        "CPA (한국공인회계사)": r"CPA|공인회계사",
        "AICPA (미국공인회계사)": r"AICPA|USCPA|미국공인회계사",
        "CTA (세무사)": r"CTA|세무사",
        "CFA (재무분석사)": r"CFA",
        "전산세무 1급": r"전산세무\s*1급",
        "전산세무 2급": r"전산세무\s*2급",
        "전산회계 1급": r"전산회계\s*1급",
        "전산회계 2급": r"전산회계\s*2급",
        "재경관리사": r"재경관리사",
        "회계관리 1급": r"회계관리\s*1급",
        "회계관리 2급": r"회계관리\s*2급",
        "ERP정보관리사": r"ERP\s*정보관리사|ERP\s*회계"
    }
    
    tool_keywords = {
        "SAP ERP": r"SAP",
        "더존 (Smart A)": r"더존|Smart\s*A|스마트\s*A",
        "더존 (iU)": r"더존\s*iU|i-U|iU",
        "Excel (엑셀)": r"Excel|엑셀|스프레드시트",
        "일반 ERP": r"ERP",
        "영림원 ERP": r"영림원",
        "국세청 / 홈택스": r"국세청|홈택스|홈텍스",
        "세무나라 / 텍스온넷": r"세무나라|텍스온넷",
        "웹케시": r"웹케시|경리나라"
    }
    
    job_keywords = {
        "회계 결산": r"결산|재무제표 작성|월말결산|분기결산",
        "세무 신고": r"부가세\s*(?:신고)?|세무신고|부가세|원천세|종소세|법인세|세무\s*신고",
        "자금 관리": r"자금관리|자금집행|출납|자금계획|출납업무",
        "회계 감사 대응": r"회계감사|감사대응|외부감사|감사\s*대응",
        "전표 입력": r"전표|전표입력|전표\s*입력",
        "부가세 신고": r"부가세|부가가치세",
        "원천세 신고": r"원천세|원천징수",
        "법인세 조정": r"법인세|세무조정",
        "예산 관리": r"예산관리|예산수립",
        "원가 회계": r"원가|원가계산|원가관리",
        "4대 보험": r"4대\s*보험|사대보험|국민연금|건강보험",
        "급여 계산": r"급여|급여대장|급여계산",
        "매출/매입 관리": r"매출관리|매입관리|매출\s*매입",
        "외환 / 수출입": r"외환|수출입|송금|외화",
        "채권/채무 관리": r"채권|채무|미수금|미지급금",
        "내부 회계 관리": r"내부회계|내부통제|내부\s*통제",
        "어음/수표 관리": r"어음|수표"
    }

    cert_counts = Counter()
    tool_counts = Counter()
    job_counts = Counter()

    for title, content in rows:
        text = str(title) + " " + str(content or "")
        
        # 자격증 카운트
        for name, pattern in cert_keywords.items():
            if re.search(pattern, text, re.IGNORECASE):
                cert_counts[name] += 1
                
        # 툴 카운트
        for name, pattern in tool_keywords.items():
            if re.search(pattern, text, re.IGNORECASE):
                tool_counts[name] += 1
                
        # 직무 카운트
        for name, pattern in job_keywords.items():
            if re.search(pattern, text, re.IGNORECASE):
                job_counts[name] += 1

    # 최다 언급 순 정렬
    top_certs = cert_counts.most_common(20)
    top_tools = tool_counts.most_common(20)
    top_jobs = job_counts.most_common(20)
    
    return top_certs, top_tools, top_jobs


def get_synonym_suggestions():
    """
    동의어(시소러스) 처리 가이드를 정의합니다.
    """
    synonyms = [
        {"대표어": "더존", "동의어 목록": ["Smart A", "스마트A", "SmartA", "iU", "i-U", "더존 iU"]},
        {"대표어": "Excel", "동의어 목록": ["엑셀", "스프레드시트", "MS Office", "MS오피스"]},
        {"대표어": "SAP ERP", "동의어 목록": ["SAP", "S/4HANA", "SAP R3"]},
        {"대표어": "CPA", "동의어 목록": ["한국공인회계사", "공인회계사", "KICPA"]},
        {"대표어": "AICPA", "동의어 목록": ["USCPA", "미국공인회계사"]},
        {"대표어": "부가세", "동의어 목록": ["부가가치세", "부가세신고"]},
        {"대표어": "세무사", "동의어 목록": ["CTA", "세무대리인"]},
        {"대표어": "자금관리", "동의어 목록": ["출납", "자금집행", "시재관리"]},
        {"대표어": "감사대응", "동의어 목록": ["회계감사", "외부감사", "감사인대응"]},
        {"대표어": "법인세", "동의어 목록": ["세무조정", "법인세세무조정"]}
    ]
    return synonyms


def main():
    print("=== 회계 직무 데이터 범주화 프로세스 시작 ===")
    
    # 1. 데이터 로딩
    rows = load_texts()
    print(f"데이터베이스 로드 완료: 총 {len(rows)}건")
    
    # 2. 메타데이터 파싱 (경력, 학력)
    exp_data, edu_data = parse_metadata(rows)
    
    # 3. 키워드 분석
    certs, tools, jobs = count_keywords(rows)
    
    # 4. 동의어 가이드 구성
    synonyms = get_synonym_suggestions()
    
    # 5. 최종 데이터 구조화
    result_data = {
        "경력 범주 현황": exp_data,
        "학력 범주 현황": edu_data,
        "자격증 최다 언급 TOP 20": {k: v for k, v in certs},
        "활용 툴 최다 언급 TOP 20": {k: v for k, v in tools},
        "세부 직무 최다 언급 TOP 20": {k: v for k, v in jobs},
        "추천 동의어 처리 리스트": synonyms
    }
    
    # 6. JSON 파일로 저장
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)
    print(f"정제된 데이터 JSON 저장 완료: {OUTPUT_JSON_PATH}")

    # 7. 터미널 출력
    print("\n" + "="*50)
    print("[1] 경력 범주 현황 (값 - 빈도수)")
    print("="*50)
    for k, v in sorted(exp_data.items(), key=lambda x: x[1], reverse=True):
        print(f"- {k}: {v}건")
        
    print("\n" + "="*50)
    print("[2] 학력 범주 현황 (값 - 빈도수)")
    print("="*50)
    for k, v in sorted(edu_data.items(), key=lambda x: x[1], reverse=True):
        print(f"- {k}: {v}건")

    print("\n" + "="*50)
    print("[3] 자격증 최다 언급 TOP 20")
    print("="*50)
    for idx, (k, v) in enumerate(certs, 1):
        print(f"{idx:02d}. {k}: {v}건")

    print("\n" + "="*50)
    print("[4] 활용 툴 최다 언급 TOP 20")
    print("="*50)
    for idx, (k, v) in enumerate(tools, 1):
        print(f"{idx:02d}. {k}: {v}건")

    print("\n" + "="*50)
    print("[5] 세부 직무 최다 언급 TOP 20")
    print("="*50)
    for idx, (k, v) in enumerate(jobs, 1):
        print(f"{idx:02d}. {k}: {v}건")

    print("\n" + "="*50)
    print("[6] 추천 동의어 처리 리스트")
    print("="*50)
    for item in synonyms:
        print(f"- {item['대표어']} <- {', '.join(item['동의어 목록'])}")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
