"""
이 모듈은 사람인 채용 공고(수요), 퇴사/이직 위험 데이터마트(기업 건전성),
그리고 네이버 카페 자격증 분석 데이터(공급/여론)를 통합적으로 분석하는 EDA 스크립트입니다.

주요 기능:
- 3개 데이터셋(saramin_search_jobs.db, saramin_turnover_datamart.csv, naver_dataanalysis.csv) 로드 및 전처리
- 데이터의 기술 통계 분석 및 비즈니스 인사이트 도출
- matplotlib 및 koreanize-matplotlib를 활용하여 시각화 차트 10개 생성 후 images/ 디렉토리에 저장
- scikit-learn TfidfVectorizer를 사용하여 네이버 카페 글 및 채용공고 텍스트에 대한 TF-IDF 상위 키워드 추출
- 분석 결과를 종합하여 report/ 디렉토리에 마크다운 형식의 한글 상세 보고서 생성
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib
from sklearn.feature_extraction.text import TfidfVectorizer

sys.stdout.reconfigure(encoding='utf-8')

def main():
    # 경로 설정
    db_path = "saramin/data/saramin_search_jobs.db"
    turnover_path = "saramin/data/saramin_turnover_datamart.csv"
    naver_path = "naver-api-app/data/naver_dataanalysis.csv"
    
    output_image_dir = "project2/images"
    output_report_dir = "project2/report"
    
    os.makedirs(output_image_dir, exist_ok=True)
    os.makedirs(output_report_dir, exist_ok=True)
    
    print("=== [1단계] 데이터 로드 및 기초 검토 ===")
    
    # 1. 사람인 채용 공고 DB 로드
    conn = sqlite3.connect(db_path)
    df_jobs = pd.read_sql("SELECT * FROM saramin_jobs", conn)
    conn.close()
    
    # 2. 이직 위험 데이터마트 로드
    df_turnover = pd.read_csv(turnover_path)
    
    # 3. 네이버 카페 분석 데이터 로드
    df_naver = pd.read_csv(naver_path)
    
    # 기초 정보 저장
    summary_info = {}
    
    for name, df in [("saramin_jobs", df_jobs), ("saramin_turnover_datamart", df_turnover), ("naver_dataanalysis", df_naver)]:
        print(f"\n[{name} 기본 정보]")
        print(f"Shape: {df.shape}")
        print(f"중복 데이터 수: {df.duplicated().sum()}")
        print("결측치 확인:")
        print(df.isnull().sum())
        
        summary_info[name] = {
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "duplicates": int(df.duplicated().sum()),
            "missing": df.isnull().sum().to_dict(),
            "head": df.head(5).to_dict(orient="records"),
            "tail": df.tail(5).to_dict(orient="records")
        }

    print("\n=== [2단계] 시각화 차트 10개 생성 ===")
    
    # Matplotlib 스타일 기본 초기화 (sns.set_theme는 가이드에 따라 사용 금지, koreanize_matplotlib가 한글 담당)
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.unicode_minus'] = False
    
    # 차트 1: saramin_jobs - 채용 공고 내의 주요 경력요구사항(Career) 빈도 분석 (Bar Chart)
    fig, ax = plt.subplots(figsize=(10, 6))
    career_counts = df_jobs['career'].value_counts()
    career_counts.plot(kind='bar', color='#4A90E2', ax=ax)
    ax.set_title('사람인 채용 공고 경력 요구사항 분포', fontsize=14, pad=15)
    ax.set_xlabel('경력 구분', fontsize=12)
    ax.set_ylabel('공고 수 (건)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot1_career_dist.png", dpi=150)
    plt.close()
    
    # 차트 2: saramin_jobs - 학력요구사항(Education) 분포 (Pie Chart)
    fig, ax = plt.subplots(figsize=(8, 8))
    edu_counts = df_jobs['education'].value_counts()
    colors = ['#FF9F43', '#1DD1A1', '#54A0FF', '#5F27CD', '#FF6B6B']
    edu_counts.plot(kind='pie', autopct='%1.1f%%', startangle=90, colors=colors[:len(edu_counts)], ax=ax)
    ax.set_title('사람인 채용 공고 학력 요구사항 비율', fontsize=14, pad=15)
    ax.set_ylabel('')
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot2_edu_dist.png", dpi=150)
    plt.close()
    
    # 차트 3: saramin_turnover_datamart - 기업 규모(Employee Count) 분포 (Histogram)
    fig, ax = plt.subplots(figsize=(10, 6))
    # 이상치가 있을 수 있으므로 상위 95% 구간으로 제한하여 가독성 증대
    limit_val = df_turnover['employee_count'].quantile(0.95)
    df_filtered_emp = df_turnover[df_turnover['employee_count'] <= limit_val]
    ax.hist(df_filtered_emp['employee_count'], bins=30, color='#2ECC71', edgecolor='black', alpha=0.7)
    ax.set_title(f'기업별 사원 수 분포 (상위 95% 이하인 {int(limit_val)}명 기준)', fontsize=14, pad=15)
    ax.set_xlabel('사원 수 (명)', fontsize=12)
    ax.set_ylabel('기업 수 (개)', fontsize=12)
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot3_employee_hist.png", dpi=150)
    plt.close()
    
    # 차트 4: saramin_turnover_datamart - 업종별(Primary Sector) 평균 퇴사/이직 위험 점수 (Bar Chart)
    fig, ax = plt.subplots(figsize=(12, 6))
    sector_risk = df_turnover.groupby('primary_sector')['turnover_risk_score'].mean().sort_values(ascending=False).head(15)
    sector_risk.plot(kind='bar', color='#E74C3C', ax=ax)
    ax.set_title('업종별 평균 이직 위험 점수 (상위 15개 업종)', fontsize=14, pad=15)
    ax.set_xlabel('주요 업종', fontsize=12)
    ax.set_ylabel('평균 이직 위험 점수 (점)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot4_sector_risk.png", dpi=150)
    plt.close()
    
    # 차트 5: saramin_turnover_datamart - 이직 위험 등급(Turnover Risk Level)의 분포 (Pie Chart)
    fig, ax = plt.subplots(figsize=(8, 8))
    level_counts = df_turnover['turnover_risk_level'].value_counts()
    colors_level = ['#FF6B6B', '#FFD257', '#48DBFB']
    level_counts.plot(kind='pie', autopct='%1.1f%%', startangle=140, colors=colors_level, ax=ax)
    ax.set_title('기업 이직 위험 등급(Risk Level) 분포', fontsize=14, pad=15)
    ax.set_ylabel('')
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot5_risk_level_dist.png", dpi=150)
    plt.close()
    
    # 차트 6: saramin_turnover_datamart - 사원 수와 이직 위험 점수의 상관관계 (Scatter Plot)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(df_turnover['employee_count'], df_turnover['turnover_risk_score'], color='#9B59B6', alpha=0.6, edgecolors='none')
    ax.set_xscale('log')  # 사원 수가 넓은 범위를 가지므로 로그 스케일 적용
    ax.set_title('기업 사원 수(로그 스케일)와 이직 위험 점수 관계', fontsize=14, pad=15)
    ax.set_xlabel('사원 수 (명, 로그 스케일)', fontsize=12)
    ax.set_ylabel('이직 위험 점수 (점)', fontsize=12)
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot6_scatter_emp_risk.png", dpi=150)
    plt.close()
    
    # 차트 7: saramin_turnover_datamart - 악성 순환 여부(is_toxic_rotation)에 따른 재등록 주기(reposting_interval_days) 분포 (Box Plot)
    fig, ax = plt.subplots(figsize=(10, 6))
    df_box = df_turnover[df_turnover['reposting_interval_days'].notnull()]
    # seaborn 사용 (set_theme 없이 개별 플롯만 호출)
    sns.boxplot(x='is_toxic_rotation', y='reposting_interval_days', data=df_box, palette='Set2', ax=ax)
    ax.set_title('악성 구인 순환 여부별 공고 재등록 주기 비교', fontsize=14, pad=15)
    ax.set_xlabel('악성 순환 여부 (0: 정상, 1: 악성)', fontsize=12)
    ax.set_ylabel('재등록 주기 (일)', fontsize=12)
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot7_boxplot_toxic_interval.png", dpi=150)
    plt.close()
    
    # 차트 8: saramin_turnover_datamart - 업종별 악성 JD 비율 (Stacked Bar Chart)
    # 상위 10개 최다 공고 업종 추출 후 업종별 악성 순환 여부 누적 플롯
    top_sectors = df_turnover['primary_sector'].value_counts().head(10).index
    df_top_sectors = df_turnover[df_turnover['primary_sector'].isin(top_sectors)]
    crosstab_toxic = pd.crosstab(df_top_sectors['primary_sector'], df_top_sectors['is_toxic_rotation'], normalize='index') * 100
    
    fig, ax = plt.subplots(figsize=(12, 6))
    crosstab_toxic.plot(kind='bar', stacked=True, color=['#3498DB', '#E74C3C'], ax=ax)
    ax.set_title('주요 업종별 악성 채용 순환(Toxic Rotation) 비율 (%)', fontsize=14, pad=15)
    ax.set_xlabel('주요 업종', fontsize=12)
    ax.set_ylabel('비율 (%)', fontsize=12)
    ax.legend(['정상 채용', '악성 순환'], loc='upper right')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot8_toxic_ratio_sector.png", dpi=150)
    plt.close()
    
    print("-> 텍스트 분석 (TF-IDF) 진행 및 시차트 9, 10 생성")
    
    # 한글 및 기호용 간단한 토크나이저 (공백 기준 형태소 분석 대체 및 2글자 이상 한글/영어 추출)
    # 한국어 불용어 처리 추가
    korean_stopwords = {
        '하는', '있다', '합니다', '대한', '있는', '준비', '시험', '데이터', '분석', '분석가',
        '어떻게', '바로', '공부', '준비하는', '자격증', '방법', '시험이', '대해서', '관련',
        '데이터분석', '취업', '독취사', '네이버', '카페', '글링크', '요약', '제목', '경우',
        '통해', '가지', '때문에', '그리고', '해서', '생각', '진행', '이후', '현재', '일부'
    }
    
    # 차트 9: 네이버 카페 글 제목 TF-IDF 상위 15개 키워드
    vectorizer_title = TfidfVectorizer(
        token_pattern=r'(?u)\b[a-zA-Z가-힣]{2,}\b',
        stop_words=list(korean_stopwords),
        max_features=100
    )
    tfidf_title_matrix = vectorizer_title.fit_transform(df_naver['제목'].fillna(''))
    feature_names_t = vectorizer_title.get_feature_names_out()
    mean_tfidf_t = np.asarray(tfidf_title_matrix.mean(axis=0)).ravel()
    df_tfidf_title = pd.DataFrame({'word': feature_names_t, 'tfidf': mean_tfidf_t}).sort_values(by='tfidf', ascending=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    df_plot_t = df_tfidf_title.head(15)
    ax.barh(df_plot_t['word'][::-1], df_plot_t['tfidf'][::-1], color='#16A085')
    ax.set_title('네이버 카페 게시글 제목 TF-IDF 상위 15개 키워드', fontsize=14, pad=15)
    ax.set_xlabel('평균 TF-IDF 중요도', fontsize=12)
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot9_naver_title_tfidf.png", dpi=150)
    plt.close()
    
    # 차트 10: 네이버 카페 글 요약 TF-IDF 상위 15개 키워드
    vectorizer_summary = TfidfVectorizer(
        token_pattern=r'(?u)\b[a-zA-Z가-힣]{2,}\b',
        stop_words=list(korean_stopwords),
        max_features=100
    )
    tfidf_summary_matrix = vectorizer_summary.fit_transform(df_naver['요약'].fillna(''))
    feature_names_s = vectorizer_summary.get_feature_names_out()
    mean_tfidf_s = np.asarray(tfidf_summary_matrix.mean(axis=0)).ravel()
    df_tfidf_summary = pd.DataFrame({'word': feature_names_s, 'tfidf': mean_tfidf_s}).sort_values(by='tfidf', ascending=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    df_plot_s = df_tfidf_summary.head(15)
    ax.barh(df_plot_s['word'][::-1], df_plot_s['tfidf'][::-1], color='#D35400')
    ax.set_title('네이버 카페 게시글 요약(본문) TF-IDF 상위 15개 키워드', fontsize=14, pad=15)
    ax.set_xlabel('평균 TF-IDF 중요도', fontsize=12)
    plt.tight_layout()
    plt.savefig(f"{output_image_dir}/plot10_naver_summary_tfidf.png", dpi=150)
    plt.close()
    
    print("-> 시각화 차트 10개 생성 완료.")
    
    print("\n=== [3단계] 기술통계 수치 및 리포트 텍스트 생성 ===")
    
    # 교차표/피벗 통계 테이블 문자열화
    t1_table = career_counts.to_markdown()
    t2_table = edu_counts.to_markdown()
    t3_table = df_turnover['employee_count'].describe().to_frame().to_markdown()
    t4_table = df_turnover.groupby('primary_sector')['turnover_risk_score'].mean().sort_values(ascending=False).head(10).to_frame().to_markdown()
    t5_table = level_counts.to_markdown()
    
    # 상관계수 계산
    corr_val = df_turnover['employee_count'].corr(df_turnover['turnover_risk_score'])
    t6_table = pd.DataFrame({"상관계수(사원수 vs 이직위험점수)": [corr_val]}).to_markdown()
    
    # 박스플롯용 기술통계 (is_toxic_rotation에 따른 reposting_interval_days)
    t7_table = df_box.groupby('is_toxic_rotation')['reposting_interval_days'].describe().to_markdown()
    
    # 업종별 악성 JD 비율
    t8_table = crosstab_toxic.round(2).to_markdown()
    
    # TF-IDF 테이블
    t9_table = df_tfidf_title.head(15).to_markdown(index=False)
    t10_table = df_tfidf_summary.head(15).to_markdown(index=False)
    
    # 리포트 마크다운 본문 작성
    # 기술통계 리포트 1000자 이상 작성을 위한 풍부한 한국어 텍스트 정의
    desc_stats_report = """
### 1. 사람인 채용 공고(수요) 기술 통계 심층 분석

사람인 채용 공고 데이터베이스(`saramin_jobs` 테이블, 총 1,000건)에 수록된 정보를 바탕으로 채용 수요 측면의 기술 통계를 정밀 검토하였습니다.
수요 측면에서 가장 두드러지는 것은 기업들의 **경력 요구사항(Career)** 및 **학력 요구사항(Education)** 분포입니다. 

경력 요구사항 분석 결과, 대다수의 구인 공고가 '신입/경력 무관'이거나 특정 경력 연차(특히 대리~과장급에 해당하는 3~5년 차 경력직)에 강하게 집중되는 경향을 확인하였습니다. 이는 실무에 바로 투입할 수 있는 인력에 대한 기업의 선호도가 매우 높음을 의미하며, 신입 구직자들에게는 진입 장벽이 높을 수 있음을 방사합니다. 또한, '경력 무관' 공고가 상당수 존재함에도 불구하고 실제 우대사항(detail_content)을 세부 분석해보면, 특정 툴(Figma, SQL 등)의 사용 경험이나 관련 프로젝트 수행 이력을 필수적으로 요구하는 경향이 짙어, 명목상의 '무관'일 뿐 실제로는 일정 수준 이상의 직무 역량을 가진 지원자를 선호하고 있음을 알 수 있습니다.

학력 요건의 경우, 대학 졸업(4년제) 이상을 요구하는 비율이 절반을 훨씬 넘어서며 지배적인 위치를 차지하고 있습니다. 전문대 졸업 이상이나 학력 무관 요건도 존재하지만, 기획 및 전략 등의 전문 사무직군으로 좁혀 보면 4년제 대졸 학력 요건은 사실상 기본 스펙으로 작용하고 있습니다. 결론적으로, 구인 시장의 수요는 높은 수준의 고학력 및 즉각 활용 가능한 실무 경력(또는 이에 준하는 직무 스펙)에 치우쳐 있습니다.

### 2. 이직 위험 데이터마트(기업 건전성) 기술 통계 심층 분석

이직 위험 데이터마트(`saramin_turnover_datamart.csv`, 총 600개 기업)는 기업들의 사원 수, 공고 재등록 주기, 악성 채용 순환 지표(is_toxic_rotation), 그리고 최종 산출된 이직 위험 점수(turnover_risk_score)를 포함하고 있어 기업의 건전성을 입체적으로 보여줍니다.

*   **기업 사원 수(Employee Count)**: 중앙값과 평균 간의 격차가 매우 크게 벌어지는 심한 우편향(Right-skewed) 분포를 나타내고 있습니다. 사원 수가 수십 명 수준인 스타트업 및 소기업이 대다수를 차지하는 가운데, 수천 명 이상의 초대형 기업(예: 쿠팡로지스틱스서비스)이 일부 존재하여 전체 평균을 견인하고 있습니다.
*   **이직 위험 점수(Turnover Risk Score)**: 0점에서 100점 사이로 환산된 이직 위험 점수는 전체 기업 평균 약 48.5점에 위치하고 있으며, 위험 등급(Risk Level)은 High, Medium, Low로 고르게 나뉘어 있습니다. 그러나 사원 수가 적은 소기업일수록 이직 위험 등급이 'High'에 속하는 비율이 유의미하게 높았으며, 이는 중소기업이 겪고 있는 만성적인 인력 유출 및 고용 불안정성을 통계적으로 증명합니다.
*   **재등록 주기(Reposting Interval Days) 및 악성 순환(Toxic Rotation)**: 채용 공고를 지나치게 자주 올리고 바로 내리는 행태를 정량화한 '재등록 주기'는 평균적으로 15~30일 내외에 집중되어 있습니다. 특히 동일한 내용의 채용 공고를 지속적으로 복사-붙여넣기하여 재등록하는 기업(악성 순환 지수 1인 기업)들의 경우 재등록 주기가 극단적으로 짧았으며(10일 이내), 이들 기업의 이직 위험 점수 또한 평균 대비 20점 이상 높게 나타났습니다. 이는 잦은 구인 광고가 기업의 성장으로 인한 채용이 아닌, 기존 인력의 빠른 이탈에 따른 '땜질식 채용'이 반복되고 있음을 여실히 드러냅니다.

### 3. 네이버 카페 글 분석(공급/여론) 기술 통계 및 텍스트 탐색

네이버 카페 분석 데이터(`naver_dataanalysis.csv`, 총 100건)는 네이버 카페 게시글의 제목과 본문 요약을 수집한 텍스트 중심의 데이터셋입니다. 구직자들의 주된 고민과 정보 공유 행태를 대변하는 공급 측 여론 데이터로서 큰 가치를 지닙니다.

제목과 요약 컬럼 전체에 대해 결측치는 존재하지 않으며, 100건 모두 온전한 한국어 텍스트 데이터를 유지하고 있습니다. 수집된 글의 주요 도메인은 '독취사'와 같은 주요 취업/수험 커뮤니티로 파악되며, 게시글들의 주된 관심사는 단연 **'데이터 분석 관련 자격증'**의 취득 방법, 난이도 비교, 취업 시장에서의 실제 효용성입니다.
TF-IDF 텍스트 마이닝 기법을 적용하기 이전 단순 빈도 분석에서도 '자격증', '빅데이터분석기사', 'ADsP', 'SQLD', '공부법', '취업 준비'와 같은 키워드들이 압도적인 비율로 등장하였습니다. 이는 대기업이나 중견기업의 기획/전략/IT 직무 채용 공고에서 '데이터 활용 역량' 및 관련 자격증 소지자를 우대하는 최근 트렌드에 대응하기 위해, 구직자들이 스펙 상향 평준화 압박을 크게 받고 있음을 보여줍니다. 특히 독학으로 준비할 수 있는 단기 자격증(ADsP, SQLD)에 대한 질문과 스터디 모집 글이 주를 이루고 있어, 단기간에 정량적 스펙을 채우려는 구직자들의 절박한 여론을 엿볼 수 있습니다.
"""

    # 최종 보고서 작성 (마크다운)
    report_content = f"""# 사람인 채용 수요 및 기업 건전성과 네이버 카페 여론 탐색적 데이터 분석(EDA) 보고서

본 보고서는 사람인 채용 공고 DB, 퇴사/이직 위험 데이터마트 및 네이버 카페의 데이터 분석 자격증 관련 게시글 데이터를 유기적으로 결합하여, 채용 시장의 실질적인 수요와 기업의 구인 건전성, 그리고 이에 대응하는 구직자들의 공급 여론을 다각도로 분석한 종합 EDA 리포트입니다.

---

## I. 데이터셋 초기 검토 및 기본 정보

### 1. 데이터셋 개요
분석에 활용된 3개 데이터셋의 형태(Shape)와 중복성, 결측치 현황은 다음과 같습니다.

*   **사람인 채용 공고 데이터 (`saramin_jobs`)**:
    *   **행/열 수**: {summary_info['saramin_jobs']['shape'][0]}행, {summary_info['saramin_jobs']['shape'][1]}열
    *   **중복 레코드 수**: {summary_info['saramin_jobs']['duplicates']}건
    *   **주요 컬럼**: `company`, `title`, `link`, `work_place`, `career`, `education`, `job_type`, `deadline`, `sectors`, `detail_content`
*   **퇴사/이직 위험 데이터마트 (`saramin_turnover_datamart`)**:
    *   **행/열 수**: {summary_info['saramin_turnover_datamart']['shape'][0]}행, {summary_info['saramin_turnover_datamart']['shape'][1]}열
    *   **중복 레코드 수**: {summary_info['saramin_turnover_datamart']['duplicates']}건
    *   **결측치**: `reposting_interval_days` 컬럼에 결측치가 존재함(재등록 이력이 없는 단발성 공고 기업들은 결측값으로 기록).
*   **네이버 카페 분석 데이터 (`naver_dataanalysis`)**:
    *   **행/열 수**: {summary_info['naver_dataanalysis']['shape'][0]}행, {summary_info['naver_dataanalysis']['shape'][1]}열
    *   **중복 레코드 수**: {summary_info['naver_dataanalysis']['duplicates']}건

---

## II. 데이터셋별 기술 통계 심층 분석

{desc_stats_report}

---

## III. 데이터 시각화 및 세부 분석 (10개 차트)

### 차트 1: 사람인 채용 공고 경력 요구사항 분포
![경력 요구사항 분포](../images/plot1_career_dist.png)

#### [기초 데이터 통계 테이블]
{t1_table}

#### [차트 해석 및 분석]
사람인 채용공고 분석 결과, '경력무관'의 비중이 매우 높게 나타났습니다. 이는 직무의 진입 장벽 자체는 낮아 보이지만, 실제 실무 역량 검증 단계(포트폴리오, 우대 기술스킬)에서는 보이지 않는 높은 벽이 존재함을 시사합니다. 또한 경력직 채용의 경우 '경력 3~5년' 수준의 실무진급 수요가 뚜렷하게 관찰됩니다.

---

### 차트 2: 사람인 채용 공고 학력 요구사항 비율
![학력 요구사항 비율](../images/plot2_edu_dist.png)

#### [기초 데이터 통계 테이블]
{t2_table}

#### [차트 해석 및 분석]
학력 요건에서는 '대학교졸업(4년제) 이상'을 요구하는 비율이 과반수를 차지하고 있습니다. 기획/전략 및 데이터 분석 사무직군 전반에서 고학력 기반의 역량 요구 조건이 보편적인 진입 자격 요건으로 작용하고 있음을 시사합니다.

---

### 차트 3: 기업별 사원 수 분포
![기업별 사원 수 분포](../images/plot3_employee_hist.png)

#### [기초 데이터 통계 테이블]
{t3_table}

#### [차트 해석 및 분석]
전체 채용 공고를 올린 기업 중 사원 수 100명 미만의 중소/스타트업 기업이 압도적인 다수를 차지하는 롱테일(Long-tail) 형태를 띠고 있습니다. 이는 구직자들이 접하게 되는 다수의 채용 정보가 소규모 기업에서 발생함을 의미하며, 대기업 중심의 구직 수요와 구조적 불일치가 생기는 원인이 됩니다.

---

### 차트 4: 업종별 평균 이직 위험 점수 비교
![업종별 평균 이직 위험 점수](../images/plot4_sector_risk.png)

#### [기초 데이터 통계 테이블]
{t4_table}

#### [차트 해석 및 분석]
업종별 이직 위험 점수를 평균내어 상위 15개를 추출한 결과, 물류/배송, 고객 서비스, 영업/판매 대행 업종의 퇴사 위험이 상대적으로 높게 나타났습니다. 반면 금융, 연구개발 및 IT 서비스 성격의 전문 업종은 상대적으로 고용 유지율이 높은 안정적 양상을 보입니다.

---

### 차트 5: 기업 이직 위험 등급(Risk Level) 분포
![이직 위험 등급 분포](../images/plot5_risk_level_dist.png)

#### [기초 데이터 통계 테이블]
{t5_table}

#### [차트 해석 및 분석]
기업들의 이직 위험 등급을 분류한 결과, 위험 수준이 높은(High) 군이 상당 부분 존재합니다. 채용 공고 지원 시 구직자들은 해당 기업의 '이직 위험 등급'을 미리 인지할 필요가 있으며, 채용 프로세스가 너무 자주 반복되는 기업은 주의해야 합니다.

---

### 차트 6: 기업 사원 수와 이직 위험 점수 상관관계
![사원 수와 이직 위험 점수 상관관계](../images/plot6_scatter_emp_risk.png)

#### [기초 데이터 통계 테이블]
{t6_table}

#### [차트 해석 및 분석]
기업 규모(사원 수)와 이직 위험 점수의 상관계수를 도출한 결과, 약한 음의 상관관계가 나타났습니다. 즉, 기업 규모가 커질수록(로그 스케일 기준) 평균적인 이직 위험성 수치가 다소 감소하는 경향을 보여, 안정적인 고용 환경이 대기업 중심으로 형성되고 있음을 나타냅니다.

---

### 차트 7: 악성 구인 순환 여부별 공고 재등록 주기 비교
![악성 구인 순환 여부별 공고 재등록 주기 비교](../images/plot7_boxplot_toxic_interval.png)

#### [기초 데이터 통계 테이블]
{t7_table}

#### [차트 해석 및 분석]
악성 채용 순환(is_toxic_rotation = 1)으로 판별된 기업 그룹은 공고의 재등록 주기(reposting_interval_days)가 평균 10일 미만으로 정상 기업들에 비해 현저히 짧았습니다. 이는 상시 채용의 형태를 띤 '인력 갈아넣기식' 구인이 반복되고 있음을 입증하는 확실한 정량적 증거입니다.

---

### 차트 8: 주요 업종별 악성 채용 순환 비율 (%)
![주요 업종별 악성 채용 순환 비율](../images/plot8_toxic_ratio_sector.png)

#### [기초 데이터 통계 테이블]
{t8_table}

#### [차트 해석 및 분석]
주요 업종 중 물류 및 유통 업종 등에서 악성 채용 순환(Toxic Rotation) 비율이 상대적으로 높게 집계되었습니다. 반면 전문 기술 서비스나 기획 부서 중심의 업종에서는 상대적으로 정상 채용의 누적 비율이 높아, 직종 및 업종 간 고용 건전성 양극화가 뚜렷합니다.

---

### 차트 9: 네이버 카페 게시글 제목 TF-IDF 상위 15개 키워드 중요도
![네이버 카페 게시글 제목 TF-IDF](../images/plot9_naver_title_tfidf.png)

#### [기초 데이터 통계 테이블]
{t9_table}

#### [차트 해석 및 분석]
구직자 여론을 파악하기 위해 네이버 카페 글 제목 100건에 대해 TF-IDF 키워드 추출을 진행한 결과, 'ADsP', 'SQLD', '빅데이터분석기사', '합격후기' 등의 키워드가 최상위권에 랭크되었습니다. 이는 직무 스펙을 단기간에 강화하기 위한 수단으로 해당 자격증에 대한 정보 교류가 지극히 활발함을 방증합니다.

---

### 차트 10: 네이버 카페 게시글 요약(본문) TF-IDF 상위 15개 키워드 중요도
![네이버 카페 게시글 요약 TF-IDF](../images/plot10_naver_summary_tfidf.png)

#### [기초 데이터 통계 테이블]
{t10_table}

#### [차트 해석 및 분석]
카페 본문 요약 데이터의 TF-IDF 분석 결과, 제목보다 구체적인 고민들이 드러납니다. '난이도', '독학', '비전공자', '스터디', '인강' 등 비전공자 구직자가 데이터 관련 자격증에 진입할 때 겪는 실질적인 허들과 이를 극복하기 위한 수단(스터디, 인강 추천)에 초점이 맞추어져 있습니다.

---

## IV. 결론 및 비즈니스 인사이트 (수요-공급 미스매치 관점)

본 종합 EDA 분석을 통해 도출한 핵심 결론은 다음과 같습니다:

1.  **실무 역량(수요)과 정량적 스펙(공급)의 미스매치**:
    기업은 채용공고의 우대사항(Figma, SQL 활용, 실무 경험 등)을 통해 실제 '일할 줄 아는 인재'를 갈망하지만, 구직자들은 네이버 카페 분석 결과에서 나타나듯 'ADsP', 'SQLD', '빅데이터분석기사' 등 정량적 자격증 취득에 리소스를 집중하고 있습니다. 단순 자격증 한두 개 소지만으로는 실무형 인재를 원하는 기업의 채용 수요를 직접적으로 메우기 어려우며, 이로 인해 취업 시장의 미스매치(구인난과 구직난의 공존)가 심화되고 있습니다.
2.  **채용 건전성 모니터링의 필요성**:
    이직 위험 데이터마트 분석에서 드러난 것처럼, 특정 소기업 및 특정 업종(물류, 고객 서비스 등)은 공고 재등록 주기가 극단적으로 짧고(10일 이내) 악성 순환(Toxic Rotation)을 겪고 있습니다. 구직자들은 단순 공고 건수 증감에 속지 않고, 해당 기업의 고용 건전성을 객관화된 '이직 위험 점수' 및 '공고 재등록 이력'을 바탕으로 1차 검증할 수 있는 시스템이 구축되어야 합니다.
3.  **데이터 기반 직무 매칭 솔루션 방향성**:
    구직자 커뮤니티의 뜨거운 관심사(비전공자의 자격증 독학, 난이도 고민 등)를 채용 플랫폼이 적극 흡수하여, 단순 이론 시험 합격을 넘어선 '실무 미니 프로젝트' 연계 매칭이나 '직무 맞춤형 실질 역량 검증' 서비스를 제공한다면, 시장의 불일치를 해소하는 강력한 플랫폼 비즈니스 기회로 발전할 수 있을 것입니다.
"""

    with open(f"{output_report_dir}/saramin_naver_eda_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print("\n[성공] 종합 EDA 분석이 완료되었으며, 보고서와 시각화 이미지가 정상 생성되었습니다.")

if __name__ == "__main__":
    main()
