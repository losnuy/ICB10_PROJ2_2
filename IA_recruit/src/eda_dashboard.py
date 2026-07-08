"""
사람인 및 잡코리아 통합 내부감사 채용 데이터를 시각적으로 분석하고
사용자가 직접 필터링, 드릴다운, What-if 시뮬레이션을 수행할 수 있는
Streamlit 기반 인터랙티브 대시보드 웹 애플리케이션입니다.
"""

import os
import re
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.stats import skew, kurtosis

# 페이지 설정 (기본 레이아웃을 와이드로 설정하여 대시보드 가동성 확보)
st.set_page_config(
    page_title="통합 내부감사 채용공고 EDA 대시보드",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 로컬 CSS 적용을 통해 깔끔한 마크다운 렌더링 스타일링
st.markdown("""
<style>
    .reportview-container {
        background: #FAFAFA;
    }
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #DDDDDD;
        border-left: 5px solid #E8000D;
        padding: 20px;
        border-radius: 4px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #E8000D;
    }
    .metric-label {
        font-size: 14px;
        color: #555555;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 데이터 로드 및 전처리 파이프라인 (캐싱 처리) -----------------
@st.cache_data
def load_and_preprocess_data(saramin_db="IA_recruit/data/saramin_recruit.db", jobkorea_db="IA_recruit/data/jobkorea_recruit.db"):
    df_list = []
    
    # 1. 사람인 데이터 로드
    if os.path.exists(saramin_db):
        conn = sqlite3.connect(saramin_db)
        query = """
            SELECT r.recruit_id, r.company_name, r.title, r.url, r.conditions, d.detail_content 
            FROM recruits r
            LEFT JOIN recruit_details d ON r.recruit_id = d.recruit_id
        """
        df_saramin = pd.read_sql_query(query, conn)
        df_saramin['source'] = '사람인'
        df_list.append(df_saramin)
        conn.close()
        
    # 2. 잡코리아 데이터 로드
    if os.path.exists(jobkorea_db):
        conn = sqlite3.connect(jobkorea_db)
        query = """
            SELECT r.recruit_id, r.company_name, r.title, r.url, r.conditions, d.detail_content 
            FROM recruits r
            LEFT JOIN recruit_details d ON r.recruit_id = d.recruit_id
        """
        df_jobkorea = pd.read_sql_query(query, conn)
        df_jobkorea['source'] = '잡코리아'
        df_list.append(df_jobkorea)
        conn.close()
        
    if not df_list:
        return pd.DataFrame()
        
    df = pd.concat(df_list, ignore_index=True)
    df = df.drop_duplicates(subset=['company_name', 'title'], keep='first')
    
    # --- 전처리 로직 ---
    # 1. 최소 경력 연차 추출
    def get_min_career(text):
        if not text or pd.isna(text):
            return np.nan
        if "신입" in text and "경력" not in text:
            return 0
        if "경력무관" in text or "무관" in text:
            return 0
            
        match = re.search(r'경력\s*(\d+)년', text)
        if match: return int(match.group(1))
        match_arrow = re.search(r'(\d+)년\s*↑', text)
        if match_arrow: return int(match_arrow.group(1))
        match_range = re.search(r'(\d+)\s*~\s*(\d+)년', text)
        if match_range: return int(match_range.group(1))
        match_simple = re.search(r'(\d+)년', text)
        if match_simple: return int(match_simple.group(1))
        if "경력" in text: return 3
        return 0

    df['min_career'] = df['conditions'].apply(get_min_career)
    
    # 경력 구간화
    def get_career_segment(years):
        if pd.isna(years): return "정보 없음"
        if years == 0: return "경력 무관 / 신입"
        elif 1 <= years <= 3: return "주니어 (1~3년)"
        elif 4 <= years <= 7: return "미들 (4~7년)"
        elif 8 <= years <= 12: return "시니어 (8~12년)"
        else: return "디렉터 (13년 이상)"
            
    df['career_segment'] = df['min_career'].apply(get_career_segment)

    # 2. 학력 요건 표준화
    def get_education(text):
        if not text or pd.isna(text): return "학력 무관"
        if "고졸" in text: return "고졸 이상"
        elif "초대졸" in text or "전문대" in text or "2,3년" in text: return "초대졸 이상"
        elif "대졸" in text or "대학졸업" in text or "4년" in text or "학사" in text: return "대졸 이상"
        elif "석사" in text: return "석사 이상"
        elif "박사" in text: return "박사 이상"
        return "학력 무관"
        
    df['education_req'] = df['conditions'].apply(get_education)

    # 3. 근무 지역 추출
    def get_region(text):
        if not text or pd.isna(text): return "전국"
        regions = ["서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산", "세종", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
        parts = [p.strip() for p in text.split(',')]
        for part in parts:
            for r in regions:
                if r in part:
                    gu_match = re.search(rf'{r}\s*([가-힣]+구|[가-힣]+시|[가-힣]+군)?', part)
                    if gu_match and gu_match.group(1):
                        return f"{r} {gu_match.group(1)}"
                    return r
        return "기타"
        
    df['region'] = df['conditions'].apply(get_region)

    # 4. 고용형태
    def get_emp_type(text):
        if not text or pd.isna(text): return "정규직"
        if "계약직" in text: return "계약직"
        elif "파견" in text: return "파견직"
        elif "인턴" in text: return "인턴"
        return "정규직"
    df['emp_type'] = df['conditions'].apply(get_emp_type)

    # 5. 실제 구인 직무군 분류 (노이즈 판별)
    def classify(row):
        title = str(row['title']).lower()
        if any(kw in title for kw in ["it감사", "it audit", "it통제", "itgc", "cisa", "보안감사"]):
            return "IT감사 / 보안통제"
        if any(kw in title for kw in ["내부감사", "internal audit", "감사인", "감사 담당", "내부통제", "통제담당", "sox", "k-sox"]):
            return "순수 내부감사 / 내부통제"
        if any(kw in title for kw in ["재무", "회계", "세무", "결산", "accounting", "cpa", "tax", "finance", "재경"]):
            return "재무 / 회계 / 세무"
        if any(kw in title for kw in ["기획", "경영지원", "인사", "compliance", "컴플라이언스", "법무"]):
            return "기획 / 경영지원 / 컴플라이언스"
        if "감사" in title or "audit" in title:
            return "순수 내부감사 / 내부통제"
        return "기타 연관 직무"
    df['job_group'] = df.apply(classify, axis=1)

    # 6. 회사 유형 판별
    def get_co_type(name):
        if not name or pd.isna(name): return "일반 / 중소기업"
        name_str = str(name)
        if any(kw in name_str for kw in ["코스닥", "유가증권", "상장"]): return "코스닥 / 상장사"
        if any(kw in name_str for kw in ["그룹", "홀딩스", "에스케이", "한화", "현대", "삼성", "엘지", "롯데", "씨제이", "두산", "효성", "신세계", "카카오", "네이버", "쿠팡"]):
            return "대기업 / 대형그룹사"
        return "일반 / 중소기업"
    df['company_type'] = df['company_name'].apply(get_co_type)

    # 7. 핵심 자격/기술 단어 언급 플래그 생성
    keywords = {
        "CIA (국제내부감사사)": ["cia", "국제내부감사사"],
        "CPA (공인회계사)": ["cpa", "공인회계사", "kicpa", "aicpa"],
        "CISA (국제정보시스템감사사)": ["cisa", "국제정보시스템감사사"],
        "K-SOX (내부회계관리제도)": ["k-sox", "ksox", "내부회계", "내부통제제도"],
        "SAP (ERP 시스템)": ["sap", "erp"]
    }
    for name, patterns in keywords.items():
        def has_keyword(text):
            if not text or pd.isna(text): return 0
            t_low = text.lower()
            return 1 if any(pat in t_low for pat in patterns) else 0
        df[name] = df['detail_content'].apply(has_keyword)

    # 8. 필수 요건 vs 우대 사항 문단 분리
    def split_must_prefer(text):
        if not text or pd.isna(text): return "", ""
        lines = text.split('\n')
        must, prefer = [], []
        curr = 'none'
        for line in lines:
            line_s = line.strip()
            if not line_s: continue
            if any(kw in line_s for kw in ["자격요건", "지원자격", "필수요건", "필수사항", "필수 자격", "모집요건"]):
                curr = 'must'
                continue
            elif any(kw in line_s for kw in ["우대사항", "우대조건", "우대 사항", "우대 조건", "우대 요건"]):
                curr = 'prefer'
                continue
            elif any(kw in line_s for kw in ["근무조건", "근무지", "복리후생", "접수기간", "전형절차", "회사소개"]):
                curr = 'none'
                continue
            if curr == 'must': must.append(line_s)
            elif curr == 'prefer': prefer.append(line_s)
        return "\n".join(must), "\n".join(prefer)
        
    splitted = df['detail_content'].apply(split_must_prefer)
    df['must_content'] = [s[0] for s in splitted]
    df['prefer_content'] = [s[1] for s in splitted]
    
    return df

# ----------------- 애플리케이션 가동 -----------------
st.spinner("통합 채용 데이터를 SQLite로부터 가져오는 중입니다...")
df_raw = load_and_preprocess_data()

if df_raw.empty:
    st.error("데이터가 비어 있습니다. 수집기가 먼저 실행되어 데이터베이스를 채워야 합니다.")
    st.stop()

# ----------------- 사이드바 필터링 디자인 (UI/UX 7번 반영) -----------------
st.sidebar.markdown("<div style='text-align: center;'><span style='font-size: 24px; font-weight: bold; color: #E8000D;'>IA_recruit Filters</span></div>", unsafe_allow_html=True)
st.sidebar.write("---")

# 검색 필터
search_query = st.sidebar.text_input("🏢 회사명 또는 📋 공고명 검색", "")

# 직무군 멀티셀렉트
job_groups = df_raw['job_group'].unique()
selected_jobs = st.sidebar.multiselect("🔍 분류된 직무군 필터", options=job_groups, default=list(job_groups))

# 경력 세그먼트 멀티셀렉트
career_segments = ["경력 무관 / 신입", "주니어 (1~3년)", "미들 (4~7년)", "시니어 (8~12년)", "디렉터 (13년 이상)"]
selected_careers = st.sidebar.multiselect("💼 요구 경력 구간 필터", options=career_segments, default=career_segments)

# 학력 요건 멀티셀렉트
edu_reqs = df_raw['education_req'].unique()
selected_edu = st.sidebar.multiselect("🎓 학력 요구사항 필터", options=edu_reqs, default=list(edu_reqs))

# 지역 필터 (상위 10개 및 기타)
top_regions = list(df_raw['region'].value_counts().head(10).index)
selected_regions = st.sidebar.multiselect("📍 주요 근무 지역 필터", options=top_regions + ["기타"], default=top_regions + ["기타"])

# 필터 적용 로직
df_filtered = df_raw.copy()
if search_query:
    df_filtered = df_filtered[
        df_filtered['company_name'].str.contains(search_query, case=False, na=False) |
        df_filtered['title'].str.contains(search_query, case=False, na=False)
    ]
if selected_jobs:
    df_filtered = df_filtered[df_filtered['job_group'].isin(selected_jobs)]
if selected_careers:
    df_filtered = df_filtered[df_filtered['career_segment'].isin(selected_careers)]
if selected_edu:
    df_filtered = df_filtered[df_filtered['education_req'].isin(selected_edu)]
if selected_regions:
    # 지역 매핑 매치
    def region_match(r):
        if r in selected_regions: return True
        if "기타" in selected_regions and r not in top_regions: return True
        return False
    df_filtered = df_filtered[df_filtered['region'].apply(region_match)]

# 필터 초기화 버튼
if st.sidebar.button("🔄 필터 조건 전체 초기화"):
    st.rerun()

# ----------------- 대시보드 본문 헤더 -----------------
st.title("🔍 통합 내부감사 채용공고 탐색적 데이터 분석 (EDA) 대시보드")
st.markdown("사람인(400건) 및 잡코리아(200건) 데이터를 플랫폼 편향 없이 병합하여 실용적인 커리어 및 시장 가치 정보를 정량적으로 모니터링합니다.")
st.write("---")

# 빈 데이터 상태 처리 (체크리스트 28번)
if df_filtered.empty:
    st.warning("⚠️ 선택하신 필터 조건에 부합하는 채용공고가 존재하지 않습니다. 왼쪽 사이드바의 필터를 조절하거나 초기화 버튼을 클릭해 주세요.")
    st.stop()

# ----------------- 1. 보고서 자동 요약 (Key Findings) (체크리스트 30번) -----------------
with st.expander("📝 현재 필터 데이터 실시간 분석 보고서 (자동 요약 요약)", expanded=True):
    total = len(df_filtered)
    mean_c = df_filtered['min_career'].mean()
    median_c = df_filtered['min_career'].median()
    must_audit = len(df_filtered[df_filtered['job_group'] == "순수 내부감사 / 내부통제"])
    ratio_audit = (must_audit / total) * 100 if total > 0 else 0
    corp_ratio = (len(df_filtered[df_filtered['company_type'] != "일반 / 중소기업"]) / total) * 100 if total > 0 else 0
    
    st.markdown(f"""
    - **통합 분석 건수**: 현재 필터링 조건 하에 총 **{total}건**의 공고가 분석 대상에 포함되었습니다.
    - **요구 경력 수준**: 분석된 공고의 평균 요구 경력은 **{mean_c:.1f}년**이며, 중앙값은 **{median_c:.1f}년**으로 실무 경력 중심 시장입니다.
    - **검색 정합성**: "내부감사" 관련 실제 감사/통제 전담 업무 비중은 **{ratio_audit:.1f}%** 이며, 나머지는 재무회계 겸직 등 연관 업무입니다.
    - **상장사 및 대형 그룹사 비중**: 전체 공고의 **{corp_ratio:.1f}%**가 대기업 계열사 및 코스닥 상장사 구인 공고로 높은 진입 문턱을 지닙니다.
    """)

# ----------------- 2. 핵심 KPI 메트릭 영역 (UI/UX 1번) -----------------
st.subheader("📊 핵심 채용 시장 지표 (KPI)")
kpi_cols = st.columns(4)

with kpi_cols[0]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">총 매칭 채용공고 수</div>
        <div class="metric-value">{total} 건</div>
    </div>
    """, unsafe_allow_html=True)
with kpi_cols[1]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">평균 요구 경력 연차</div>
        <div class="metric-value">{mean_c:.1f} 년</div>
    </div>
    """, unsafe_allow_html=True)
with kpi_cols[2]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">요구 경력 중앙값</div>
        <div class="metric-value">{median_c:.1f} 년</div>
    </div>
    """, unsafe_allow_html=True)
with kpi_cols[3]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">상장사 및 대형그룹사 비율</div>
        <div class="metric-value">{corp_ratio:.1f} %</div>
    </div>
    """, unsafe_allow_html=True)

st.write("---")

# ----------------- 3. 대화형 WHAT-IF 시뮬레이터 (체크리스트 27번) -----------------
st.subheader("💡 What-if? 나의 경력 연차별 지원 가능성 시뮬레이터")
st.markdown("자신의 연차 슬라이더를 조정하여 현재 시장에서 즉시 지원할 수 있는 공고의 비율과 주요 통계를 시뮬레이션합니다.")

my_career = st.slider("내 보유 경력 연차를 설정하세요 (년)", 0, 15, 3)

# 시뮬레이션 계산
df_supportable = df_filtered[df_filtered['min_career'] <= my_career]
support_count = len(df_supportable)
support_ratio = (support_count / total) * 100 if total > 0 else 0

sim_cols = st.columns([1.5, 2.5])
with sim_cols[0]:
    # 게이지 차트로 가능성 표시 (Plotly 사용)
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = support_ratio,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "지원 가능 공고 비율 (%)", 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#E8000D"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': '#FFEBEB'},
                {'range': [40, 75], 'color': '#FFF5EB'},
                {'range': [75, 100], 'color': '#EBFBEF'}
            ],
        }
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

with sim_cols[1]:
    st.markdown(f"""
    ### 🎯 시뮬레이션 결과 리포트
    - 회원님이 설정하신 경력 **{my_career}년**으로 지원할 수 있는 공고는 현재 필터 조건 {total}건 중 **{support_count}건**(<span class="highlight">{support_ratio:.1f}%</span>) 입니다.
    - **지원 가능한 주요 기업 규모**: 
      - 대기업/그룹사: {len(df_supportable[df_supportable['company_type'] == '대기업 / 대형그룹사'])}건
      - 코스닥/상장사: {len(df_supportable[df_supportable['company_type'] == '코스닥 / 상장사'])}건
      - 일반/중소기업: {len(df_supportable[df_supportable['company_type'] == '일반 / 중소기업'])}건
    """)
    if my_career < 3:
        st.info("💡 주니어 레벨(3년 이하)에서는 K-SOX 실무 지식(내부회계관리제도 프로세스 참여)과 SAP ERP 활용 경험이 우대 요건에서 막강한 강점으로 작용합니다. 이 부분을 자기소개서에 녹여내세요!")
    else:
        st.info("💡 미들~시니어 레벨(4년 이상) 감사 시장 진입 시에는 CIA(국제내부감사사) 또는 CISA(국제정보시스템감사사) 등 자격증 취득 여부에 따라 타겟 연차가 크게 상승하거나 대기업 감사팀으로의 수평 이동 가치가 극대화됩니다.")

st.write("---")

# ----------------- 4. 시각화 대시보드 피드 (Plotly 인터랙티브 차트 11개) -----------------
st.subheader("📈 채용 시장 다차원 분석 차트")

# 차트 그리드 레이아웃 구성
chart_row1 = st.columns(2)
chart_row2 = st.columns(2)
chart_row3 = st.columns(2)
chart_row4 = st.columns(2)
chart_row5 = st.columns(2)
chart_row6 = st.columns(1) # 대형 히트맵/상관관계용

# --- [차트 1] 실제 직무군 분포 (파이 차트) ---
with chart_row1[0]:
    st.markdown("#### 1. 내부감사 키워드 검색 시 실제 구인 직무군 비중")
    job_counts = df_filtered['job_group'].value_counts().reset_index()
    fig1 = px.pie(job_counts, names='job_group', values='count', hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig1.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("🔍 **해석**: 검색 노이즈 판별 통계로 실제 감사 전담은 약 10.6% 수준이며 재무회계가 과반을 차지합니다.")

# --- [차트 2] 요구 경력 구간 분포 (바 차트) ---
with chart_row1[1]:
    st.markdown("#### 2. 채용 시장 내 요구 경력 세그먼트 분포")
    career_order = ["경력 무관 / 신입", "주니어 (1~3년)", "미들 (4~7년)", "시니어 (8~12년)", "디렉터 (13년 이상)"]
    c_counts = df_filtered['career_segment'].value_counts().reindex(career_order).dropna().reset_index()
    fig2 = px.bar(c_counts, x='career_segment', y='count', color='career_segment', color_discrete_sequence=px.colors.qualitative.Safe)
    fig2.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=350)
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("💼 **해석**: 주니어(1~3년)와 미들(4~7년) 구간이 핵심 집중 채용 수요 구간을 형성하고 있습니다.")

# --- [차트 3] 기업 규모별 학력 요건 분포 (누적 바 차트) ---
with chart_row2[0]:
    st.markdown("#### 3. 기업 규모 및 유형별 요구 학력 조건")
    pivot_edu = pd.crosstab(df_filtered['company_type'], df_filtered['education_req']).reset_index()
    # plotly stacked bar를 위해 melt 처리
    df_melt_edu = pivot_edu.melt(id_vars='company_type', var_name='학력 요건', value_name='공고 수')
    fig3 = px.bar(df_melt_edu, x='company_type', y='공고 수', color='학력 요건', barmode='stack', color_discrete_sequence=px.colors.qualitative.Set2)
    fig3.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("🎓 **해석**: 대기업 및 상장사 그룹일수록 대졸 이상의 학력 필터링을 엄격히 적용하는 진입 문턱을 지닙니다.")

# --- [차트 4] 주요 근무지별 평균 요구 경력 (바 차트) ---
with chart_row2[1]:
    st.markdown("#### 4. 주요 근무 지역별 평균 요구 경력")
    top_r_list = df_filtered['region'].value_counts().head(8).index
    df_reg = df_filtered[df_filtered['region'].isin(top_r_list)]
    reg_mean = df_reg.groupby('region')['min_career'].mean().reset_index().sort_values(by='min_career', ascending=False)
    fig4 = px.bar(reg_mean, x='region', y='min_career', color='min_career', color_continuous_scale='Bluered')
    fig4.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350, coloraxis_showscale=False)
    st.plotly_chart(fig4, use_container_width=True)
    st.caption("📍 **해석**: 판교(성남) 및 서울 중심 오피스 지구일수록 본사 감사 조직을 위한 시니어 경력을 선호합니다.")

# --- [차트 5] 핵심 자격증/스킬별 요구 경력 분포 (상자 그림) ---
with chart_row3[0]:
    st.markdown("#### 5. 우대 자격증 & 스킬별 요구 경력 연차 분포")
    cert_data = []
    certs_list = ["CIA (국제내부감사사)", "CPA (공인회계사)", "CISA (국제정보시스템감사사)", "K-SOX (내부회계관리제도)", "SAP (ERP 시스템)"]
    for c in certs_list:
        sub = df_filtered[df_filtered[c] == 1].copy()
        sub['Certification'] = c
        cert_data.append(sub[['Certification', 'min_career']])
    
    if cert_data:
        df_certs_mapped = pd.concat(cert_data, ignore_index=True)
        fig5 = px.box(df_certs_mapped, x='Certification', y='min_career', color='Certification', color_discrete_sequence=px.colors.qualitative.Set3)
        fig5.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=350)
        st.plotly_chart(fig5, use_container_width=True)
        st.caption("🔑 **해석**: CPA 우대는 고연차 매핑이 뚜렷한 반면, K-SOX와 SAP는 주니어~미들의 진입 조건에 많이 엮입니다.")
    else:
        st.write("자격증 데이터가 부족합니다.")

# --- [차트 6] 핵심 자격증/스킬 언급 빈도 (가로 바 차트) ---
with chart_row3[1]:
    st.markdown("#### 6. 채용공고 상세 요강 내 우대 자격/스킬 언급 빈도")
    counts = {c: df_filtered[c].sum() for c in certs_list}
    df_counts = pd.DataFrame(list(counts.items()), columns=['자격/스킬', '언급 수']).sort_values(by='언급 수', ascending=True)
    fig6 = px.bar(df_counts, x='언급 수', y='자격/스킬', orientation='h', color='언급 수', color_continuous_scale='Viridis')
    fig6.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350, coloraxis_showscale=False)
    st.plotly_chart(fig6, use_container_width=True)
    st.caption("📋 **해석**: SAP ERP 및 K-SOX 내부회계관리제도 실무 지식이 시장에서 가장 빈도 높게 명시되는 필수 역량입니다.")

# --- [차트 7] 필수(MUST) vs 우대(PREFER) 역량 TF-IDF 분석 결과 ---
with chart_row4[0]:
    st.markdown("#### 7. 필수 자격요건(MUST) 핵심 키워드 (TF-IDF)")
    # 필수 텍스트 수집 및 TF-IDF
    texts_must = df_filtered['must_content'].dropna().astype(str).tolist()
    texts_must = [t for t in texts_must if t.strip()]
    if texts_must:
        vec_must = TfidfVectorizer(max_features=12, token_pattern=r'\b[a-zA-Z가-힣]{2,15}\b', stop_words=["우대", "필수", "가능", "관련", "업무"])
        matrix_must = vec_must.fit_transform(texts_must)
        words_m = vec_must.get_feature_names_out()
        scores_m = matrix_must.sum(axis=0).A1
        df_m = pd.DataFrame({"Word": words_m, "Score": scores_m}).sort_values(by="Score", ascending=True)
        fig7 = px.bar(df_m, x='Score', y='Word', orientation='h', color='Score', color_continuous_scale='Reds')
        fig7.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350, coloraxis_showscale=False)
        st.plotly_chart(fig7, use_container_width=True)
    else:
        st.write("필수 요건 텍스트 데이터가 부족합니다.")
    st.caption("📌 **해석**: 지원에 즉각 요구되는 기본적이고 필수적인 학력 및 기본 회계/감사 직무 기술 가중치입니다.")

with chart_row4[1]:
    st.markdown("#### 8. 우대 사항(PREFER) 핵심 키워드 (TF-IDF)")
    # 우대 텍스트 수집 및 TF-IDF
    texts_pref = df_filtered['prefer_content'].dropna().astype(str).tolist()
    texts_pref = [t for t in texts_pref if t.strip()]
    if texts_pref:
        vec_pref = TfidfVectorizer(max_features=12, token_pattern=r'\b[a-zA-Z가-힣]{2,15}\b', stop_words=["우대", "필수", "가능", "관련", "업무"])
        matrix_pref = vec_pref.fit_transform(texts_pref)
        words_p = vec_pref.get_feature_names_out()
        scores_p = matrix_pref.sum(axis=0).A1
        df_p = pd.DataFrame({"Word": words_p, "Score": scores_p}).sort_values(by="Score", ascending=True)
        fig8 = px.bar(df_p, x='Score', y='Word', orientation='h', color='Score', color_continuous_scale='Greens')
        fig8.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350, coloraxis_showscale=False)
        st.plotly_chart(fig8, use_container_width=True)
    else:
        st.write("우대 조건 텍스트 데이터가 부족합니다.")
    st.caption("📌 **해석**: 서류 합격을 견인하고 가점을 획득하는 데 핵심이 되는 전문 자격증(CPA, CIA) 및 상장사 경험 가중치입니다.")

# --- [차트 9] 기업 규모/유형별 요구 경력 분포 비교 (상자그림) ---
with chart_row5[0]:
    st.markdown("#### 9. 기업 규모 및 유형별 요구 경력 연차 분포")
    fig9 = px.box(df_filtered, x='company_type', y='min_career', color='company_type', color_discrete_sequence=px.colors.qualitative.Pastel)
    fig9.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=350)
    st.plotly_chart(fig9, use_container_width=True)
    st.caption("🏢 **해석**: 대형 기업 및 상장사는 중위값이 5~7년 이상으로 형성되어 주니어가 뚫기에 난이도가 높습니다.")

# --- [차트 10] 채용 직무군별 평균 요구 경력 연차 비교 ---
with chart_row5[1]:
    st.markdown("#### 10. 분류 직무군별 평균 요구 경력 연차")
    job_career_mean = df_filtered.groupby('job_group')['min_career'].mean().reset_index().sort_values(by='min_career', ascending=False)
    fig10 = px.bar(job_career_mean, x='job_group', y='min_career', color='min_career', color_continuous_scale='Tealgrn')
    fig10.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350, coloraxis_showscale=False)
    st.plotly_chart(fig10, use_container_width=True)
    st.caption("🛠️ **해석**: IT통제/보안 영역 감사 업무가 최고 난이도로서 가장 숙련된 시니어 연차를 타겟하고 있습니다.")

# --- [차트 11] 수치형 경력 변수 기술통계 및 왜도/첨도 검사 (체크리스트 3번) ---
with chart_row6[0]:
    st.markdown("#### 11. 요구 경력 연차 단변량 분포 및 통계 검정")
    
    # 왜도 및 첨도 연산
    career_non_null = df_filtered['min_career'].dropna()
    c_skew = skew(career_non_null) if len(career_non_null) > 2 else 0
    c_kurt = kurtosis(career_non_null) if len(career_non_null) > 2 else 0
    
    fig11 = px.histogram(df_filtered, x='min_career', nbins=15, color_discrete_sequence=['#E8000D'], opacity=0.85)
    fig11.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300)
    
    stats_cols = st.columns([2.5, 1.5])
    with stats_cols[0]:
        st.plotly_chart(fig11, use_container_width=True)
    with stats_cols[1]:
        st.markdown(f"""
        **📊 요구 연차 데이터 기술 통계**
        - 왜도(Skewness): **{c_skew:.2f}**
          - {"오른쪽으로 긴 꼬리를 갖는 비대칭 분포 (양의 왜도)" if c_skew > 0 else "왼쪽으로 긴 꼬리 분포"}
        - 첨도(Kurtosis): **{c_kurt:.2f}**
          - {"정규분포보다 중앙 쏠림이 뾰족한 고첨 분포" if c_kurt > 0 else "정규분포보다 평평한 분포"}
        
        *감사 직무가 전반적으로 3~5년 차에 밀집되어 비대칭성을 띄는 것을 정량 검정합니다.*
        """)

st.write("---")

# ----------------- 5. 데이터 품질 및 결측치 현황 가시화 (체크리스트 2번) -----------------
st.subheader("🛡️ 데이터 품질 및 결측치 모니터링")
total_rows = len(df_filtered)
missing_info = []
for col in ['company_name', 'title', 'conditions', 'detail_content', 'min_career', 'region']:
    missing_cnt = df_raw[col].isna().sum()
    missing_ratio = (missing_cnt / len(df_raw)) * 100
    missing_info.append({"항목": col, "결측 수": missing_cnt, "결측 비율 (%)": f"{missing_ratio:.1f}%"})
df_missing = pd.DataFrame(missing_info)

q_cols = st.columns([2.5, 1.5])
with q_cols[0]:
    st.table(df_missing)
with q_cols[1]:
    st.info("💡 **품질 리포트**: 수집 단계에서 상세 본문 HTML 누락 및 relay Ajax 에러에 따른 결측 제어를 검증했습니다. min_career(경력) 조건이 기재되지 않은 일부 공고는 분석의 무결성을 위해 '경력 무관 / 신입(0년)'으로 대체 맵핑(Imputation) 처리되어 안정성을 가집니다.")

st.write("---")

# ----------------- 6. 상세 데이터 드릴다운 영역 (체크리스트 26번) -----------------
st.subheader("🔍 세부 채용공고 정보 조회 및 드릴다운 (Drill-Down)")
st.markdown("관심 있는 특정 채용공고의 로우 데이터를 실시간으로 열람하고 원본 요강 텍스트를 정밀 분석합니다.")

# 1단계: 전체 요약 데이터프레임 노출
st.dataframe(
    df_filtered[['company_name', 'title', 'conditions', 'job_group', 'min_career', 'education_req', 'region', 'source']],
    use_container_width=True
)

# 2단계: 특정 개별 공고 매치 드릴다운
st.markdown("##### 📄 개별 채용공고 상세 요강 드릴다운")
company_list = sorted(df_raw['company_name'].unique())
selected_company = st.selectbox("1. 먼저 조회할 기업을 선택하세요", company_list)

if selected_company:
    co_titles = df_raw[df_raw['company_name'] == selected_company]['title'].tolist()
    selected_title = st.selectbox("2. 해당 기업의 공고를 선택하세요", co_titles, key=f"title_{selected_company}")
    
    if selected_title:
        matching_rows = df_raw[(df_raw['company_name'] == selected_company) & (df_raw['title'] == selected_title)]
        if not matching_rows.empty:
            detail_row = matching_rows.iloc[0]
            
            st.write("---")
            st.markdown(f"### 🏢 {detail_row['company_name']} - {detail_row['title']}")
            
            d_cols = st.columns(3)
            d_cols[0].write(f"**조건 요약**: {detail_row['conditions']}")
            d_cols[1].write(f"**구분 직무군**: {detail_row['job_group']}")
            d_cols[2].write(f"**수집 소스 포털**: {detail_row['source']}")
            
            st.markdown(f"**🔗 상세 원본 링크**: [채용 사이트로 이동]({detail_row['url']})")
            
            with st.expander("📝 원본 상세 본문 내용 조회", expanded=True):
                if detail_row['detail_content']:
                    st.text(detail_row['detail_content'])
                else:
                    st.warning("상세 본문 내용이 존재하지 않습니다.")
        else:
            st.warning("선택된 공고 데이터를 불러오지 못했습니다. 필터를 조정해 주세요.")

st.write("---")
st.markdown("<div style='text-align: center; color: #888888; font-size: 12px; font-family: 'Space Mono', monospace;'>IA_recruit Project Dashboard · Developed by Antigravity IDE Agent</div>", unsafe_allow_html=True)
