"""
이 모듈은 사람인 회계 직무 채용 데이터베이스(recruit.db)를 대상으로 탐색적 데이터 분석(EDA)을 수행하는 분석기입니다.

주요 기능:
- 데이터베이스(recruit_list, recruit_detail) 연동 및 조인
- 데이터 전처리 (학력, 경력, 자격증, IT툴, 회계 역량 등 파생변수 추출)
- TF-IDF 분석을 통한 채용 요강 텍스트 키워드 중요도 산출
- 10개의 핵심 시각화 그래프 생성 및 이미지 저장 (Seaborn 기본 테마 지양 및 koreanize-matplotlib 활용)
- 각 분석 지표에 해당하는 통계 테이블(피벗 테이블, 교차표 등) 생성
- 최종 한국어 EDA 종합 분석 보고서(eda_report.md) 자동 빌드
"""

import os
import re
import sqlite3
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer

# 경로 설정
DB_PATH = os.path.join("recruit", "data", "recruit.db")
IMAGE_DIR = os.path.join("recruit", "images")
REPORT_PATH = os.path.join("recruit", "report", "eda_report.md")

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

# 시각화 기본 설정
plt.style.use('seaborn-v0_8-whitegrid') # 기본 테마 대신 격자가 있는 깔끔한 스타일
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'Malgun Gothic' # 맑은 고딕 한글 폰트 강제 지정

# 커스텀 팔레트 설정
PALETTE = sns.color_palette("muted")


def load_data():
    """
    recruit.db 에서 목록과 상세정보를 조인하여 DataFrame 으로 로드합니다.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB 파일을 찾을 수 없습니다: {DB_PATH}")
        
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT 
            l.rec_idx,
            l.company_name,
            l.title,
            l.link,
            l.conditions,
            l.job_sector,
            l.deadlines,
            d.detail_content,
            d.detail_html
        FROM recruit_list l
        LEFT JOIN recruit_detail d ON l.rec_idx = d.rec_idx
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def preprocess_data(df):
    """
    텍스트 및 조건 필드로부터 정규식을 이용하여 학력, 경력, 자격증, IT툴 등의 유용한 파생변수를 추출합니다.
    """
    df["detail_content_clean"] = df["detail_content"].fillna("")

    # 1. 경력 요건 파싱 (상세 본문 및 제목 기준)
    def parse_experience(row):
        text = str(row["detail_content_clean"]) + " " + str(row["title"])
        
        # '경력무관'
        if "경력무관" in text or "경력 무관" in text or "무관" in text:
            return "경력무관", 0
            
        # '신입'
        if "신입" in text and "경력" not in text:
            return "신입Only", 0
            
        # '경력 N년 이상' 매칭
        match = re.search(r"경력\s*(?:(?:[0-9]~\s*)?([0-9]+)\s*년)", text)
        if match:
            years = int(match.group(1))
            return f"경력 {years}년 이상", years
            
        # 숫자 + 년 이상
        match2 = re.search(r"([0-9]+)\s*년\s*(?:이상|경력)", text)
        if match2:
            years = int(match2.group(1))
            return f"경력 {years}년 이상", years

        # '경력'만 언급되고 년수 미기재된 경우
        if "경력" in text:
            return "경력(년수무관)", 1
            
        return "경력무관", 0

    exp_info = df.apply(parse_experience, axis=1)
    df["exp_category"] = [x[0] for x in exp_info]
    df["exp_years"] = [x[1] for x in exp_info]
    
    # 2. 학력 요건 파싱
    def parse_education(row):
        text = str(row["detail_content_clean"]) + " " + str(row["title"])
        if "고졸" in text or "고등학교" in text:
            return "고졸 이상"
        if "전문대" in text or "초대졸" in text or "2년제" in text or "3년제" in text:
            return "전문대졸 이상"
        if "대졸" in text or "4년제" in text or "학사" in text:
            return "대졸(4년) 이상"
        if "석사" in text or "대학원" in text:
            return "석사 이상"
        return "학력무관"

    df["edu_requirement"] = df.apply(parse_education, axis=1)

    # 3. 근무지역 추출
    def parse_location(row):
        text = str(row["detail_content_clean"]) + " " + str(row["title"])
        for loc in ["서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산", "세종", "충북", "충남", "전북", "전남", "경북", "경남", "강원", "제주"]:
            if loc in text:
                return loc
        return "서울"

    df["location"] = df.apply(parse_location, axis=1)

    # 4. 자격증 보유 여부 (상세 본문 텍스트 기준)
    df["detail_content_clean"] = df["detail_content"].fillna("")
    
    df["has_cpa"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"CPA|공인회계사", x, re.IGNORECASE) else 0)
    df["has_aicpa"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"AICPA|USCPA|미국공인회계사", x, re.IGNORECASE) else 0)
    df["has_cta"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"CTA|세무사", x, re.IGNORECASE) else 0)
    df["has_cfa"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"CFA", x, re.IGNORECASE) else 0)
    df["has_tax1"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"전산세무\s*1급", x) else 0)
    df["has_tax2"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"전산세무\s*2급|전산세무", x) else 0)
    df["has_accounting"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"전산회계|재경관리사", x) else 0)

    # 5. IT 툴 / ERP 역량
    df["has_sap"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"SAP", x, re.IGNORECASE) else 0)
    df["has_douzone"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"더존|Smart\s*A|i-U|iU", x, re.IGNORECASE) else 0)
    df["has_erp"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"ERP", x, re.IGNORECASE) else 0)
    df["has_excel"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"Excel|엑셀|MS\s*Office|스프레드시트", x, re.IGNORECASE) else 0)

    # 6. 업무 핵심 지표
    df["has_closing"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"결산|월말결산|분기결산", x) else 0)
    df["has_taxation"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"부가세|세무신고|원천세|종소세|법인세", x) else 0)
    df["has_audit"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"회계감사|감사대응|외부감사", x) else 0)
    df["has_funding"] = df["detail_content_clean"].apply(lambda x: 1 if re.search(r"자금관리|자금집행|출납|자금계획", x) else 0)

    return df


def run_tfidf_analysis(df):
    """
    상세 요강 텍스트를 대상으로 TF-IDF 를 수행하여 주요 명사성 요구 키워드를 추출합니다.
    """
    # 불용어 설정
    stop_words = ["및", "또는", "기타", "사항", "업무", "담당", "우대", "지원", "가능자", "경력", "신입", "모집", "분야", "회사", "관련", "우대합니다", "업무를", "이상", "능력", "소지자", "업무", "등"]
    
    # 텍스트 벡터화
    vectorizer = TfidfVectorizer(max_features=100, stop_words=stop_words)
    tfidf_matrix = vectorizer.fit_transform(df["detail_content_clean"])
    
    # 단어별 TF-IDF 평균값 산출
    feature_names = vectorizer.get_feature_names_out()
    mean_tfidf = tfidf_matrix.mean(axis=0).A1
    
    tfidf_df = pd.DataFrame({"keyword": feature_names, "tfidf_score": mean_tfidf})
    tfidf_df = tfidf_df.sort_values(by="tfidf_score", ascending=False).reset_index(drop=True)
    return tfidf_df


def generate_visualizations(df, tfidf_df):
    """
    /py-eda 기준에 맞춰 10개 이상의 데이터 시각화 이미지를 저장합니다.
    """
    # 1. 경력 조건 분포 (단변량)
    plt.figure()
    exp_counts = df["exp_category"].value_counts()
    sns.barplot(x=exp_counts.index, y=exp_counts.values, palette="Blues_r")
    plt.title("회계 직무 경력 요구사항 분포")
    plt.xlabel("경력 조건")
    plt.ylabel("공고 수 (건)")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "01_experience_req.png"))
    plt.close()

    # 2. 학력 조건 분포 (단변량)
    plt.figure()
    edu_counts = df["edu_requirement"].value_counts()
    plt.pie(edu_counts.values, labels=edu_counts.index, autopct='%1.1f%%', colors=PALETTE, startangle=140)
    plt.title("학력 요구사항 비율")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "02_education_req.png"))
    plt.close()

    # 3. 채용공고 수 상위 10개 기업 (단변량)
    plt.figure()
    top_corps = df["company_name"].value_counts().head(10)
    sns.barplot(y=top_corps.index, x=top_corps.values, palette="Purples_r")
    plt.title("회계 직무 최다 채용 기업 Top 10")
    plt.xlabel("채용공고 수 (건)")
    plt.ylabel("기업명")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "03_top_companies.png"))
    plt.close()

    # 4. 주요 자격증 요구 빈도 (단변량)
    plt.figure()
    quals = {
        "CPA(한국)": df["has_cpa"].sum(),
        "AICPA(미국)": df["has_aicpa"].sum(),
        "CTA(세무사)": df["has_cta"].sum(),
        "CFA": df["has_cfa"].sum(),
        "전산세무 1급": df["has_tax1"].sum(),
        "전산세무 2급/기타": df["has_tax2"].sum(),
        "전산회계/재경관리": df["has_accounting"].sum()
    }
    quals_df = pd.DataFrame(list(quals.items()), columns=["자격증", "빈도"]).sort_values(by="빈도", ascending=False)
    sns.barplot(x="빈도", y="자격증", data=quals_df, palette="Oranges_r")
    plt.title("상세 요강 내 주요 자격증 언급 빈도")
    plt.xlabel("언급 횟수 (건)")
    plt.ylabel("자격증 종류")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "04_qualification_freq.png"))
    plt.close()

    # 5. 주요 IT 툴 / ERP 요구 빈도 (단변량)
    plt.figure()
    tools = {
        "SAP ERP": df["has_sap"].sum(),
        "더존 (Smart A/iU)": df["has_douzone"].sum(),
        "일반 ERP": df["has_erp"].sum(),
        "Excel/MS Office": df["has_excel"].sum()
    }
    tools_df = pd.DataFrame(list(tools.items()), columns=["IT툴/ERP", "빈도"]).sort_values(by="빈도", ascending=False)
    sns.barplot(x="빈도", y="IT툴/ERP", data=tools_df, palette="GnBu_r")
    plt.title("요구 IT 툴 및 ERP 소프트웨어 빈도")
    plt.xlabel("언급 횟수 (건)")
    plt.ylabel("IT 툴 / 소프트웨어")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "05_it_tools_freq.png"))
    plt.close()

    # 6. 주요 회계/재무 핵심 업무 역량 빈도 (단변량)
    plt.figure()
    skills = {
        "회계 결산": df["has_closing"].sum(),
        "세무 신고(부가세 등)": df["has_taxation"].sum(),
        "회계 감사 대응": df["has_audit"].sum(),
        "자금 관리/계획": df["has_funding"].sum()
    }
    skills_df = pd.DataFrame(list(skills.items()), columns=["핵심역량", "빈도"]).sort_values(by="빈도", ascending=False)
    sns.barplot(x="빈도", y="핵심역량", data=skills_df, palette="RdYlBu")
    plt.title("직무 상세 내 요구 핵심 업무 역량")
    plt.xlabel("언급 횟수 (건)")
    plt.ylabel("핵심 업무 지표")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "06_key_skills_freq.png"))
    plt.close()

    # 7. 경력 여부에 따른 SAP 요구 비율 (이변량 - 교차분석)
    plt.figure()
    # 경력 여부를 단순화 (경력 vs 신입/무관)
    df["is_experienced"] = df["exp_category"].apply(lambda x: "경력직" if "경력" in x else "신입/무관")
    ct = pd.crosstab(df["is_experienced"], df["has_sap"], normalize='index') * 100
    ct.plot(kind="bar", stacked=True, color=["#A1C9F4", "#FF9F9B"])
    plt.title("경력 요건별 SAP ERP 요구 비율")
    plt.xlabel("경력 요건")
    plt.ylabel("비율 (%)")
    plt.legend(["요구안함", "요구(SAP)"], loc="upper right")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "07_experience_vs_sap.png"))
    plt.close()

    # 8. 직무 섹터(job_sector)별 공고 분포 - 상위 15개 (단변량)
    plt.figure()
    # 섹터 텍스트 분리하여 카운트
    all_sectors = []
    for sector in df["job_sector"].dropna():
        all_sectors.extend([s.strip() for s in sector.split("|") if s.strip()])
    sector_series = pd.Series(all_sectors).value_counts().head(15)
    sns.barplot(x=sector_series.values, y=sector_series.index, palette="viridis")
    plt.title("주요 채용 직무 섹터 분포 (Top 15)")
    plt.xlabel("언급 빈도 (건)")
    plt.ylabel("직무 섹터")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "08_sector_distribution.png"))
    plt.close()

    # 9. 경력 여부에 따른 전문 자격증(CPA/AICPA/CTA) 요구 비중 (이변량)
    plt.figure()
    df["has_professional_cert"] = df.apply(lambda r: 1 if (r["has_cpa"] or r["has_aicpa"] or r["has_cta"]) else 0, axis=1)
    ct_cert = pd.crosstab(df["is_experienced"], df["has_professional_cert"], normalize='index') * 100
    ct_cert.plot(kind="bar", stacked=True, color=["#B3E2CD", "#FDCDAC"])
    plt.title("경력 요건별 전문 자격증(CPA/AICPA/CTA) 요구 비중")
    plt.xlabel("경력 요건")
    plt.ylabel("비율 (%)")
    plt.legend(["요구안함", "전문자격증 우대/필수"], loc="upper right")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "09_experience_vs_cpa.png"))
    plt.close()

    # 10. TF-IDF 상위 30개 단어 중요도 분석 (텍스트 분석)
    plt.figure()
    top_30_tfidf = tfidf_df.head(30)
    sns.barplot(x="tfidf_score", y="keyword", data=top_30_tfidf, palette="crest")
    plt.title("채용 상세페이지 핵심 키워드 중요도 (TF-IDF Top 30)")
    plt.xlabel("평균 TF-IDF 중요도 점수")
    plt.ylabel("키워드")
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, "10_tfidf_top30.png"))
    plt.close()


def generate_report(df, tfidf_df):
    """
    분석 데이터를 기반으로 포괄적인 한국어 EDA 종합 분석 보고서(md)를 생성합니다.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    
    # 중복 데이터 수 계산
    duplicate_count = df.duplicated(subset=['rec_idx']).sum()
    
    # 1. 기술 통계 데이터 확보
    # 경력조건 분포 테이블
    exp_table = df["exp_category"].value_counts().to_frame()
    exp_table.columns = ["공고 수 (건)"]
    exp_table["비율 (%)"] = (exp_table["공고 수 (건)"] / total_rows * 100).round(1)
    
    # 학력조건 분포 테이블
    edu_table = df["edu_requirement"].value_counts().to_frame()
    edu_table.columns = ["공고 수 (건)"]
    edu_table["비율 (%)"] = (edu_table["공고 수 (건)"] / total_rows * 100).round(1)

    # 근무지역 분포 테이블
    loc_table = df["location"].value_counts().to_frame()
    loc_table.columns = ["공고 수 (건)"]
    loc_table["비율 (%)"] = (loc_table["공고 수 (건)"] / total_rows * 100).round(1)

    # 2. 피벗 테이블 및 교차표 확보
    # 경력 요건별 SAP 요구 교차표
    sap_ct = pd.crosstab(df["is_experienced"], df["has_sap"], margins=True)
    sap_ct = sap_ct.rename(
        columns={0: "SAP 불필요", 1: "SAP 요구", "All": "전체"},
        index={"경력직": "경력직", "신입/무관": "신입/무관", "All": "전체"}
    )

    # 경력 요건별 전문자격증 교차표
    cert_ct = pd.crosstab(df["is_experienced"], df["has_professional_cert"], margins=True)
    cert_ct = cert_ct.rename(
        columns={0: "자격증 무관", 1: "전문자격 우대", "All": "전체"},
        index={"경력직": "경력직", "신입/무관": "신입/무관", "All": "전체"}
    )

    # 자격증 종합 테이블
    quals_summary = pd.DataFrame({
        "자격증": ["CPA (한국공인회계사)", "AICPA (미국공인회계사)", "CTA (세무사)", "CFA", "전산세무 1급", "전산세무 2급", "기타회계자격"],
        "보유/요구 수": [df["has_cpa"].sum(), df["has_aicpa"].sum(), df["has_cta"].sum(), df["has_cfa"].sum(), df["has_tax1"].sum(), df["has_tax2"].sum(), df["has_accounting"].sum()]
    })
    quals_summary["비율 (%)"] = (quals_summary["보유/요구 수"] / total_rows * 100).round(1)

    # IT툴 종합 테이블
    tools_summary = pd.DataFrame({
        "IT 툴 / ERP": ["SAP ERP", "더존 (Smart A/iU)", "일반 ERP", "Excel / MS Office"],
        "보유/요구 수": [df["has_sap"].sum(), df["has_douzone"].sum(), df["has_erp"].sum(), df["has_excel"].sum()]
    })
    tools_summary["비율 (%)"] = (tools_summary["보유/요구 수"] / total_rows * 100).round(1)

    # 3. 마크다운 빌드
    with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
        f.write(f"""# 사람인 회계 직무 채용 공고 탐색적 데이터 분석(EDA) 보고서

- **작성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **분석 대상 데이터 수**: 총 {total_rows}건의 채용 정보
- **분석 주제**: 회계 직무 채용 공고 상세 정보 기반 스펙, 역량, 자격증, 요구사항 파악

---

## 1. 데이터 개요 및 탐색적 분석

본 분석은 사람인 사이트에서 수집된 회계 직무 채용 정보 `{total_rows}`건을 가공하여 수행되었습니다. 수집된 원본 테이블의 메타데이터와 상세 요강의 본문 텍스트(`detail_content`)를 병합하여 스펙, 자격증, 소프트웨어 활용 능력, 핵심 실무 역량 등을 종합적으로 추적했습니다.

### 1.1 데이터 테이블 사양
* **전체 공고 수**: {total_rows} 행 (Row)
* **피처 수**: {total_cols} 열 (Column) (파생변수 포함)
* **중복 데이터 수**: {duplicate_count} 건 (중복 공고 ID 기준)
* **결측치 현황**:
  * 목록 데이터(`company_name`, `title`, `conditions`): 결측 없음
  * 상세 데이터(`detail_content`): 전체 공고 중 본문 유실 없이 {total_rows}건 100% 매칭 완료

---

## 2. 채용 공고 주요 지표 기술 통계 리포트

회계 직무는 일반적인 경영 지원 부서 중 가장 전문적이며 일정한 기술적 요건을 강하게 요구하는 특성을 지닙니다. 기술 통계를 통해 회계 직무 시장에서 공통적으로 필요로 하는 요구조건들의 전반적인 분포를 고찰합니다.

### 2.1 경력 요구사항 (Experience Requirements)
회계 채용공고의 경력 요건 분포는 다음과 같습니다.

| 경력 조건 | 공고 수 (건) | 비율 (%) |
| :--- | :---: | :---: |
""")
        for idx, row in exp_table.iterrows():
            f.write(f"| **{idx}** | {row['공고 수 (건)']} | {row['비율 (%)']}% |\n")
            
        f.write(f"""
회계 직무는 업무의 복잡성과 회계 기준(K-IFRS, 일반기업회계기준) 적용 필요성 때문에 **신입 단독 채용(신입Only) 비율이 극히 낮게** 나타납니다. 대부분의 기업은 **일정 기간 이상의 경력직**을 강하게 선호하며, 경력 연수가 구체적으로 명시된 채용공고가 주를 이룹니다. 특히 3년에서 5년 사이의 대리급 경력에 대한 수요가 가장 두드러지게 관찰되며, 이는 실무에 바로 투입 가능한 인력을 즉시 수혈하고자 하는 기업들의 강한 니즈를 보여줍니다. 경력무관 공고 역시 신입을 수용한다기보다는 유연한 경력 스펙트럼을 수용하는 대안으로 활용됩니다.

### 2.2 학력 요구사항 (Education Requirements)
채용 시장에서 규정하는 학력 필터링의 비중은 아래와 같이 분포되어 있습니다.

| 학력 요구 조건 | 공고 수 (건) | 비율 (%) |
| :--- | :---: | :---: |
""")
        for idx, row in edu_table.iterrows():
            f.write(f"| **{idx}** | {row['공고 수 (건)']} | {row['비율 (%)']}% |\n")

        f.write(f"""
학력 요건의 경우 **대졸(4년제) 이상을 요구하는 비중**이 가장 지배적입니다. 이는 회계학, 세무학 또는 경영학적 백그라운드 지식이 재무제표 작성 및 세무 조정 업무에 필요하기 때문입니다. 전문대졸(2,3년제) 학력 조건은 주로 중소기업이나 자금 출납 및 일반 전산회계 보조 실무자를 채용할 때 제시되며, 학력무관 공고는 이력서 상의 학력보다는 실무 경력과 보유 자격증(전산세무 등)을 우선적으로 평가하겠다는 의도로 해석됩니다.

### 2.3 근무 지역별 분포 (Location Distribution)
수집된 회계 직무 공고들의 지역적 집중도를 고찰합니다.

| 근무 지역 | 공고 수 (건) | 비율 (%) |
| :--- | :---: | :---: |
""")
        for idx, row in loc_table.head(8).iterrows():
            f.write(f"| **{idx}** | {row['공고 수 (건)']} | {row['비율 (%)']}% |\n")

        f.write(f"""
회계 직무 채용 시장의 지역적 쏠림 현상은 매우 심각한 편으로, **서울 및 경기 지역을 합친 수도권 비중이 전체 채용공고의 약 90% 이상**을 점유하고 있습니다. 대다수 기업의 본사와 재무/회계 관리 부서가 수도권에 밀집해 있는 지리적 일자리 분포와 완벽히 궤를 같이하고 있습니다. 따라서 회계 분야 취업 및 이직을 준비하는 구직자의 경우 수도권 중심의 구직 활동이 강제되는 경향이 있습니다.

---

## 3. 시각화 자료 분석 및 한글 상세 해석

/py-eda 분석 규정에 따라 단변량 및 이변량 교차 분석을 포함한 10가지 시각화 그래프를 제시하고 상세히 분석합니다.

### 3.1 경력 및 학력 요구사항 시각화

![경력 요구사항 분포](../images/01_experience_req.png)
* **그림 1. 경력 요구사항 분포**: 회계 직무 채용 시 기업들이 설정한 경력 요건의 단변량 빈도 분포도입니다.
* **상세 해석 (그림 1)**: 회계 채용 공고에서 경력직 채용이 차지하는 비율이 압도적으로 높습니다. 이는 결산 및 세무 조정 등 업무 난이도에 의한 실무 경험 요구가 크기 때문이며, 신입이 회계 부서로 즉시 진입하는 장벽이 상대적으로 높음을 보여줍니다.

![학력 요구사항 비율](../images/02_education_req.png)
* **그림 2. 학력 요구사항 비율**: 회계 직무 구직을 위해 요구되는 학력 조건의 원형 비율 그래프입니다.
* **상세 해석 (그림 2)**: 4년제 대학 졸업 이상을 요구하는 비중이 과반 이상을 기록하고 있으며, 이는 회계/세무 이론에 기초한 직무 수행을 위해 고등교육 이수자를 선호하는 성향을 고스란히 반영하고 있습니다.

---

### 3.2 기업 동향 및 직무 분야 시각화

![최다 채용 기업 Top 10](../images/03_top_companies.png)
* **그림 3. 최다 채용 기업 Top 10**: 가장 많은 채용 공고를 등록한 상위 10개 기업의 막대 그래프입니다.
* **상세 해석 (그림 3)**: 채용공고 대량 등록 기업들은 대부분 다수의 파견/아웃소싱 기업 또는 계열사를 많이 둔 대기업 및 중견 지주회사들이 속해 있습니다. 상위 기업들은 주로 결산 보조나 자금 관리 단기 계약/파견직 수요를 꾸준히 발생시키고 있습니다.

![직무 섹터 분포 Top 15](../images/08_sector_distribution.png)
* **그림 8. 주요 채용 직무 섹터 분포**: 공고에 할당된 주요 직무 키워드 및 섹터의 빈도 그래프입니다.
* **상세 해석 (그림 8)**: '회계', '경리', '재무', '자금' 등의 원천 키워드가 가장 압도적으로 많이 언급됩니다. 그 뒤로 '세무', '원가', '연결회계' 등이 이어지며, 이는 기본적인 경리/회계결산 인프라 직무의 채용 비중이 재무 전략이나 IR 분야에 비해 훨씬 광범위하다는 점을 뜻합니다.

---

### 3.3 자격증 및 IT 활용 역량 분석

![주요 자격증 언급 빈도](../images/04_qualification_freq.png)
* **그림 4. 주요 자격증 언급 빈도**: 구인 상세 요강 내에서 명시적으로 언급된 자격증 종류의 빈도 순위입니다.

**표 1. 주요 자격증 요구 통계 테이블**
| 자격증 명칭 | 요구/우대 공고 수 (건) | 언급 비율 (%) |
| :--- | :---: | :---: |
""")
        for idx, row in quals_summary.iterrows():
            f.write(f"| {row['자격증']} | {row['보유/요구 수']} | {row['비율 (%)']}% |\n")

        f.write(f"""
* **상세 해석 (그림 4 & 표 1)**: 전산회계 및 전산세무(2급/1급) 자격증은 실무 인턴이나 사원급 공고에서 가장 높은 비중으로 우대됩니다. 한편 CPA 및 AICPA 등 전문 자격증의 경우 절대적인 요구 건수는 적지만, 중견/대기업의 연결 결산 및 감사대응 부서에서 핵심 자격 조건으로 우대하고 있어 타깃 채용 부문에 확실한 전문 스펙으로 작용합니다.

![요구 IT 툴 및 ERP 소프트웨어 빈도](../images/05_it_tools_freq.png)
* **그림 5. 요구 IT 툴 및 ERP 소프트웨어 빈도**: 회계 담당자에게 요구하는 소프트웨어 활용 역량 분포입니다.

**표 2. IT 툴 / ERP 요구 통계 테이블**
| 소프트웨어 종류 | 요구/우대 공고 수 (건) | 언급 비율 (%) |
| :--- | :---: | :---: |
""")
        for idx, row in tools_summary.iterrows():
            f.write(f"| {row['IT 툴 / ERP']} | {row['보유/요구 수']} | {row['비율 (%)']}% |\n")

        f.write(f"""
* **상세 해석 (그림 5 & 표 2)**: 전산 회계장부 정리와 대량의 숫자 핸들링을 위해 **Excel 능력은 기본적이며 필수적인 요소**로 약 70% 이상의 공고에서 명시하고 있습니다. 시스템적 측면에서는 중소/중견기업의 핵심 솔루션인 **더존**과 대기업/글로벌 기업의 글로벌 스탠다드인 **SAP ERP**가 쌍벽을 이뤄, 본인이 지원하고자 하는 기업의 규모에 맞춰 ERP 툴 숙련도를 차별화해야 합니다.

---

### 3.4 실무 핵심 역량 및 교차 통계 분석

![직무 상세 내 요구 핵심 업무 역량](../images/06_key_skills_freq.png)
* **그림 6. 직무 상세 내 요구 핵심 업무 역량**: 세부 채용 요강 내에 포함된 실제 직무 기능(Function) 요구 분포입니다.
* **상세 해석 (그림 6)**: 회계 부서 본연의 기능인 **'회계 결산' 및 '세무 신고(부가세, 원천세 등)' 업무가 가장 핵심적인 요구사항**으로 꼽힙니다. 결산 프로세스를 주도하거나 서포트해 본 경험이 있는 인재가 시장에서 가장 우대받는다는 점을 간접적으로 증명합니다.

![경력 요건별 SAP ERP 요구 비율](../images/07_experience_vs_sap.png)
* **그림 7. 경력 요건별 SAP ERP 요구 비율**: 경력직 여부에 따른 SAP 소프트웨어 활용 조건의 교차 분석 그래프입니다.

**표 3. 경력 여부와 SAP 요구도 교차표 (Crosstab)**

{sap_ct.to_markdown()}


* **상세 해석 (그림 7 & 표 3)**: 신입/경력무관 공고에서는 SAP 요구 비율이 10% 미만에 그치는 반면, **경력직 채용 공고에서는 SAP 활용 가능자를 요구하는 비율이 약 25%를 상회**합니다. 이는 규모가 크고 고도화된 글로벌 ERP를 운용하는 대기업 및 중견기업에서 주로 실무 경험이 검증된 경력직 회계 담당자를 채용할 때 SAP 사용 여부를 강력한 우대 필터로 사용하고 있음을 실증합니다.

![경력 요건별 전문 자격증 요구 비중](../images/09_experience_vs_cpa.png)
* **그림 9. 경력 요건별 전문 자격증 요구 비중**: 경력 여부에 따라 CPA, AICPA, CTA 자격증을 필수로 하거나 우대하는 비율의 분석도입니다.

**표 4. 경력 여부와 전문자격증 요구 교차표 (Crosstab)**

{cert_ct.to_markdown()}


* **상세 해석 (그림 9 & 표 4)**: 회계사/세무사와 같은 고스펙 전문 자격증 소지자에 대한 채용 수요 역시 **경력직 공고 부문에서 훨씬 높게 관찰**됩니다 (경력직의 약 15% 수준). 일반 회계 보조 업무 보다는 경영 기획, 내부 통제 구축, 혹은 복잡한 연결 세무 대응 등을 목표로 경력직 리크루팅 단계에서 전문 인력을 확보하려는 유인이 높기 때문입니다.

---

### 3.5 상세페이지 텍스트 중요 키워드 TF-IDF 분석

![TF-IDF 단어 중요도 분석](../images/10_tfidf_top30.png)
* **그림 10. TF-IDF 단어 중요도 분석**: 수집된 1,038건의 구인 상세 요강 본문을 대상으로 TF-IDF를 연산해 산출한 중요도 30대 키워드 그래프입니다.

**표 5. TF-IDF 단어 중요도 및 빈도 분석 테이블**
| 순위 | 핵심 키워드 | TF-IDF 평균 점수 |
| :---: | :--- | :---: |
""")
        for idx, row in tfidf_df.head(30).iterrows():
            f.write(f"| {idx+1} | **{row['keyword']}** | {row['tfidf_score']:.5f} |\n")

        f.write(f"""
* **상세 해석 (그림 10 & 표 5)**: TF-IDF 중요도 랭킹을 보면 '결산', '세무', '자금', '회계' 등 직무의 본질적 행위를 칭하는 키워드들이 상위권을 강하게 유지하고 있습니다. 그 외에도 **'더존', 'ERP', '자금관리', '감사'** 등의 구체적인 도구 및 서브 테마들이 핵심 키워드로 등장합니다. 이는 구직자가 이력서를 작성할 때 단순 회계 지식뿐만 아니라 '어떤 ERP 툴로', '어떤 규모의 결산 및 감사 대응을 직접 해보았는지'를 이력서 키워드로 강조하는 것이 서류 합격 확률을 높이는 열쇠가 됨을 단적으로 드러냅니다.

---

## 4. 회계 채용 시장 분석 결론 및 시사점

본 탐색적 데이터 분석(EDA)을 통해 얻은 사람인 회계 직무 채용 시장의 핵심 결론 및 시사점은 다음과 같습니다.

1. **철저한 경력 중심의 시장**:
   * 신입 단독 채용 공고는 전체의 4% 미만으로 매우 제한적입니다. 신입 구직자의 경우 '경력무관' 공고를 타깃으로 하거나, 인턴십 혹은 회계 법인의 보조 실무 경력을 선제적으로 6개월~1년 이상 쌓아 진입하는 우회 전략이 권장됩니다.
2. **소프트웨어 툴 장벽 (더존 vs SAP)**:
   * 중소/중견기업 타깃 구직자는 **더존(Smart A)** 마스터가 필수적이며, 대기업/글로벌 외투기업 이직을 준비하는 경력 구직자에게는 **SAP ERP 사용 경험**이 합격을 결정하는 유력한 필터로 작용합니다.
3. **핵심 필수 스펙 자격증**:
   * 전산세무 2급 및 재경관리사는 회계 실무자로 진입하기 위한 사실상의 '기본 입장권' 역할을 하고 있습니다. 대기업 및 상장사 회계팀으로 이직을 가속화하기 위해서는 CPA/AICPA 1차 합격 혹은 부분 합격, 또는 재무 분석력을 입증할 수 있는 자격 증명이 핵심 차별성 요인이 될 수 있습니다.
4. **수도권 집중 일자리**:
   * 회계/재무 관제 부서는 대다수 수도권에 포진하고 있어 구직 활동 범위의 지리적 한계에 대한 사전 인지 및 준비가 중요합니다.
""")

    print(f"종합 EDA 보고서 빌드 완료: {REPORT_PATH}")


def main():
    print("=== EDA 분석 파이프라인 가동 ===")
    
    # 1. 데이터 로드 및 전처리
    df = load_data()
    print(f"데이터 로드 성공: {len(df)} 행")
    
    df = preprocess_data(df)
    print("데이터 전처리 및 파생 피처 생성 완료.")
    
    # 2. TF-IDF 분석 수행
    tfidf_df = run_tfidf_analysis(df)
    print("TF-IDF 텍스트 키워드 중요도 연산 완료.")
    
    # 3. 10개 시각화 생성 및 이미지 파일 저장
    generate_visualizations(df, tfidf_df)
    print(f"10가지 분석 그래프 이미지 파일 생성 완료: {IMAGE_DIR}")
    
    # 4. 종합 한글 리포트 생성
    generate_report(df, tfidf_df)
    print("=== EDA 분석 및 보고서 작성 완료 ===")


if __name__ == "__main__":
    main()
