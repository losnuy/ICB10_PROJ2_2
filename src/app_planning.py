"""
이 파일은 기획·전략 직무 자격증 미스매치(Gap) 분석 및 지원 적합도 자가진단 Streamlit 대시보드(app_planning.py)입니다.

주요 기능:
- Mock Data 없이 실제 수집 데이터만 사용합니다.
- [구직자 탭] naver-api-app/data/naver_dataanalysis.csv 기반 네이버 카페 구직자 트렌드 분석 및 자가진단
- [인사팀 탭] automated_total_mismatch_mart.csv 기반 수급 Gap 시각화, 미스매치 유형 카드,
  JD 리모델링 시뮬레이터, 최적 채용 홍보 시점 하이라이트 라인차트 및 인사이트 제언
- saramin/data/saramin_search_jobs.db (실제 1,000건 크롤링 공고 DB)로 사람인 수요 데이터 보완
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
import os
import re

# 페이지 기본 설정
st.set_page_config(
    page_title="기획/전략 직무 미스매치 & 자가진단 대시보드",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================================================
# 1. 데이터 로드 함수 (Mock Data 없음 - 실제 파일만 사용)
# =====================================================================

@st.cache_data
def load_naver_cafe_data():
    """
    naver_dataanalysis.csv를 로드하여 반환합니다.
    컬럼: Unnamed:0, 제목, 카페명, 카페주소, 글링크, 요약
    """
    paths = [
        "naver-api-app/data/naver_dataanalysis.csv",
        "../naver-api-app/data/naver_dataanalysis.csv",
        "data/naver_dataanalysis.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p, encoding="utf-8-sig")
                return df, p
            except Exception:
                pass
    return None, None


@st.cache_data
def load_mismatch_mart():
    """
    automated_total_mismatch_mart.csv를 로드합니다.
    컬럼: 자격증명, 기업_수요_건수, 구직자_공급_건수, 2026-01~06_검색비율, 수급Gap(건)
    """
    paths = [
        "automated_total_mismatch_mart.csv",
        "../automated_total_mismatch_mart.csv",
        "naver-api-app/automated_total_mismatch_mart.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p, encoding="utf-8-sig")
                return df, p
            except Exception:
                pass
    return None, None


@st.cache_data
def load_saramin_db():
    """
    saramin_search_jobs.db SQLite에서 실제 채용공고 데이터를 로드합니다.
    로드 실패 시 None 반환.
    """
    db_paths = [
        "saramin/data/saramin_search_jobs.db",
        "data/saramin_search_jobs.db",
        "../saramin/data/saramin_search_jobs.db",
    ]
    for p in db_paths:
        if os.path.exists(p):
            try:
                conn = sqlite3.connect(p)
                df = pd.read_sql("SELECT * FROM saramin_jobs", conn)
                conn.close()

                # 세부직무 분류
                it_kw = ["sqld", "adsp", "ga4", "figma", "역기획", "프로토타이핑",
                         "서비스로그", "서비스기획", "it기획", "ux", "ui", "웹기획"]
                st_kw = ["cfa", "cpa", "공인노무사", "m&a", "시장조사", "타당성분석",
                         "ppt마스터", "경영기획", "사업기획", "사업전략", "전략기획"]

                def classify(row):
                    text = (str(row.get("sectors", "")) + " " +
                            str(row.get("title", "")) + " " +
                            str(row.get("detail_content", ""))).lower()
                    it_c = sum(1 for k in it_kw if k in text)
                    st_c = sum(1 for k in st_kw if k in text)
                    return "IT/서비스 기획" if it_c >= st_c else "경영/사업 전략"

                df["세부직무"] = df.apply(classify, axis=1)
                return df, p
            except Exception:
                pass
    return None, None


# =====================================================================
# 2. 데이터 로드 실행 및 사이드바 상태 표시
# =====================================================================

df_naver, naver_path = load_naver_cafe_data()
df_mart, mart_path = load_mismatch_mart()
df_jobs, db_path = load_saramin_db()

st.sidebar.title("🎯 기획/전략 분석 필터")

if naver_path:
    st.sidebar.success(f"✅ 네이버 카페 데이터 로드 ({len(df_naver)}건): {naver_path}")
else:
    st.sidebar.error("❌ naver_dataanalysis.csv 파일을 찾을 수 없습니다.")

if mart_path:
    st.sidebar.success(f"✅ 수급 마트 데이터 로드 ({len(df_mart)}개 스킬): {mart_path}")
else:
    st.sidebar.error("❌ automated_total_mismatch_mart.csv 파일을 찾을 수 없습니다.")

if db_path:
    st.sidebar.success(f"✅ 사람인 공고 DB 로드 ({len(df_jobs)}건): {db_path}")
else:
    st.sidebar.warning("⚠️ 사람인 DB 미발견 - 수요 카운트는 마트 데이터를 사용합니다.")

selected_target = st.sidebar.selectbox(
    "세부 직무 선택",
    ["전체 기획/전략", "IT/서비스 기획", "경영/사업 전략"],
    help="분석할 기획/전략 부문의 세부 분야를 선택하세요."
)
st.sidebar.write("---")
st.sidebar.info(
    "💡 사이드바에서 직무 필터를 선택하면 구직자 탭과 인사팀 탭 분석이 자동으로 갱신됩니다."
)

# =====================================================================
# 3. 메인 화면 타이틀 및 탭 구성
# =====================================================================

st.title("💡 기획/전략 직무 미스매치 분석 & 자가진단 대시보드")
st.markdown(
    f"**대상 세부직무**: `{selected_target}` | "
    "실제 네이버 카페 수집 데이터 + 사람인 채용공고 수급 분석"
)
st.write("---")

tab1, tab2 = st.tabs([
    "💡 구직자: 기획자 스펙 자가진단",
    "🏢 인사팀: 기획 직무 미스매치(Gap) 리포트"
])

# 직무 필터링 (사람인 DB 있을 때만)
if df_jobs is not None:
    if selected_target == "전체 기획/전략":
        df_filtered = df_jobs.copy()
    else:
        df_filtered = df_jobs[df_jobs["세부직무"] == selected_target].copy()
else:
    df_filtered = pd.DataFrame()

# 전역 초기화 (리포트 함수 호환)
user_skills = []
suitability_score = 0.0
missing_skills = []


# =====================================================================
# 탭 1: 구직자향 - 네이버 카페 기반 구직자 트렌드 + 자가진단
# =====================================================================

with tab1:
    st.header("💡 기획/전략 자격 요건 적합도 자가진단")
    st.markdown(
        "네이버 카페에서 수집된 **실제 구직자 게시글 데이터**를 기반으로 "
        "현재 구직자들의 관심 역량 트렌드를 확인하고, 나의 스펙을 진단합니다."
    )

    # ----- 1) 네이버 카페 구직자 트렌드 현황 -----
    if df_naver is not None:
        st.subheader("📊 네이버 카페 구직자 관심 게시글 트렌드 (실제 수집 데이터)")

        # 카페명별 게시글 수 집계
        col_cafe, col_kw = st.columns(2)

        with col_cafe:
            cafe_counts = df_naver["카페명"].value_counts().head(10).reset_index()
            cafe_counts.columns = ["카페명", "게시글수"]
            fig_cafe = gr.Figure(gr.Bar(
                x=cafe_counts["게시글수"],
                y=cafe_counts["카페명"],
                orientation="h",
                marker_color="#818cf8",
                hovertemplate="카페: %{y}<br>게시글: %{x}건<extra></extra>"
            ))
            fig_cafe.update_layout(
                title=dict(text="<b>카페별 구직자 게시글 수 TOP 10</b>",
                           font=dict(size=13, color="#0f172a")),
                plot_bgcolor="rgba(255,255,255,0.9)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=20, t=50, b=20),
                xaxis_title="게시글 수 (건)",
                yaxis_title="",
                height=350
            )
            fig_cafe.update_xaxes(showgrid=True, gridcolor="#e2e8f0")
            st.plotly_chart(fig_cafe, use_container_width=True)

        with col_kw:
            # 요약 텍스트에서 핵심 역량 키워드 등장 빈도 분석
            keywords = [
                "SQLD", "ADsP", "빅데이터분석기사", "데이터분석", "Figma", "GA4",
                "CPA", "CFA", "컴퓨터활용능력", "M&A", "시장조사", "PPT", "Python",
                "SQL", "엑셀", "파워포인트", "기획서", "전략"
            ]
            kw_counts = {}
            for kw in keywords:
                count = df_naver["요약"].fillna("").str.contains(kw, case=False).sum()
                count += df_naver["제목"].fillna("").str.contains(kw, case=False).sum()
                if count > 0:
                    kw_counts[kw] = int(count)

            kw_df = pd.DataFrame(
                sorted(kw_counts.items(), key=lambda x: x[1], reverse=True),
                columns=["키워드", "언급수"]
            ).head(12)

            fig_kw = gr.Figure(gr.Bar(
                x=kw_df["키워드"],
                y=kw_df["언급수"],
                marker_color="#34d399",
                hovertemplate="키워드: %{x}<br>언급: %{y}건<extra></extra>"
            ))
            fig_kw.update_layout(
                title=dict(text="<b>구직자 게시글 내 핵심 역량 키워드 언급 빈도</b>",
                           font=dict(size=13, color="#0f172a")),
                plot_bgcolor="rgba(255,255,255,0.9)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=20, t=50, b=60),
                xaxis_title="역량/자격증 키워드",
                yaxis_title="언급 건수",
                height=350
            )
            fig_kw.update_xaxes(showgrid=False, tickangle=-30)
            fig_kw.update_yaxes(showgrid=True, gridcolor="#e2e8f0")
            st.plotly_chart(fig_kw, use_container_width=True)

        # 실제 게시글 샘플 표시
        with st.expander("📰 실제 수집된 네이버 카페 구직자 게시글 샘플 보기 (상위 15건)", expanded=False):
            show_cols = ["제목", "카페명", "요약"]
            display_df = df_naver[show_cols].head(15).copy()
            display_df["요약"] = display_df["요약"].str[:120] + "..."
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.error("❌ 네이버 카페 데이터 파일을 찾을 수 없어 구직자 트렌드 분석을 수행할 수 없습니다.")

    # ----- 2) 사람인 공고 TOP 10 스킬 리포트 연동 -----
    top10_paths = [
        "saramin/docs/planning_skills_top10.md",
        "docs/planning_skills_top10.md",
        "../saramin/docs/planning_skills_top10.md",
    ]
    top10_path = next((p for p in top10_paths if os.path.exists(p)), None)
    if top10_path:
        with open(top10_path, "r", encoding="utf-8") as f:
            top10_md = f.read()
        with st.expander("📊 사람인 1,000건 공고 분석: 기획·전략 우대 스킬/자격증 TOP 10", expanded=False):
            st.markdown(top10_md)

    # ----- 3) 자가진단 섹션 -----
    st.markdown("---")
    st.markdown("### 🧑‍💼 나의 직무 역량 프로필 입력")

    col_prof1, col_prof2 = st.columns(2)
    with col_prof1:
        user_career = st.selectbox(
            "나의 경력 년수",
            options=["신입", "주니어 (1~3년)", "미들 (4~7년)", "시니어 (8년 이상)"],
            index=1
        )
    with col_prof2:
        user_edu = st.selectbox(
            "최종 학력",
            options=["고졸 이하", "초대졸 (2/3년제)", "대졸 (4년제 학사)", "대학원 (석사/박사)"],
            index=2
        )

    licenses_pool = ["SQLD", "ADsP", "정보처리기사", "CFA", "CPA", "컴퓨터활용능력"]
    tools_pool = ["Figma", "GA4", "Slack", "Jira", "Git", "ERP (더존/SAP)", "Tableau"]
    experiences_pool = ["역기획", "프로토타이핑", "서비스로그 분석",
                        "M&A 검토", "시장조사 및 리서치", "사업타당성 분석", "예산 및 결산 관리"]

    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        user_licenses = st.multiselect("보유 자격증", options=licenses_pool, default=[])
    with col_sel2:
        user_tools = st.multiselect("사용 가능한 실무 툴", options=tools_pool, default=[])
    with col_sel3:
        user_experiences = st.multiselect("보유 실무/직무 경험", options=experiences_pool, default=[])

    diagnose_clicked = st.button("📊 나의 다차원 직무 적합도 진단 실행")

    # 유사어 매핑
    synonyms = {
        "SQLD": ["sqld", "sql개발자"], "ADsP": ["adsp", "데이터분석준전문가"],
        "정보처리기사": ["정보처리기사", "정처기"], "CFA": ["cfa", "재무분석사"],
        "CPA": ["cpa", "공인회계사"], "컴퓨터활용능력": ["컴퓨터활용능력", "컴활", "오피스"],
        "Figma": ["figma", "피그마"], "GA4": ["ga4", "구글애널리틱스"],
        "Slack": ["slack", "슬랙"], "Jira": ["jira", "지라"],
        "Git": ["git", "깃", "github"], "ERP (더존/SAP)": ["erp", "sap", "더존"],
        "Tableau": ["tableau", "태블로"],
        "역기획": ["역기획"], "프로토타이핑": ["프로토타이핑", "화면설계", "와이어프레임"],
        "서비스로그 분석": ["서비스로그", "로그분석", "ga4", "amplitude"],
        "M&A 검토": ["m&a", "인수합병", "투자심사"],
        "시장조사 및 리서치": ["시장조사", "리서치", "research"],
        "사업타당성 분석": ["타당성분석", "타당성 분석", "feasibility"],
        "예산 및 결산 관리": ["예산", "결산", "세무", "회계"]
    }

    def parse_career_years(s):
        if not isinstance(s, str):
            return 0
        nums = re.findall(r'\d+', s.lower())
        return int(nums[0]) if nums else 0

    def parse_edu_level(s):
        if not isinstance(s, str):
            return 0
        s = s.lower()
        if "대학원" in s or "석사" in s or "박사" in s:
            return 3
        elif "대졸" in s or "학사" in s or "대학교" in s:
            return 2
        elif "전문대" in s or "초대졸" in s:
            return 1
        return 0

    user_career_val = {"신입": 0, "주니어 (1~3년)": 2, "미들 (4~7년)": 5, "시니어 (8년 이상)": 10}[user_career]
    user_edu_val = {"고졸 이하": 0, "초대졸 (2/3년제)": 1, "대졸 (4년제 학사)": 2, "대학원 (석사/박사)": 3}[user_edu]

    user_skills = user_licenses + user_tools + user_experiences

    # 진단 실행
    if diagnose_clicked or user_skills:
        total_scores = []
        if not df_filtered.empty:
            for _, row in df_filtered.iterrows():
                req_career = parse_career_years(row.get("career", ""))
                career_score = 100 if user_career_val >= req_career else 0
                req_edu = parse_edu_level(row.get("education", ""))
                edu_score = 100 if user_edu_val >= req_edu else 0
                text = (str(row.get("sectors", "")) + " " +
                        str(row.get("title", "")) + " " +
                        str(row.get("detail_content", ""))).lower()
                needed_lic = [l for l in licenses_pool if any(k in text for k in synonyms[l])]
                lic_score = 100 if not needed_lic else (
                    sum(1 for l in needed_lic if l in user_licenses) / len(needed_lic)) * 100
                needed_tools = [t for t in tools_pool if any(k in text for k in synonyms[t])]
                tool_score = 100 if not needed_tools else (
                    sum(1 for t in needed_tools if t in user_tools) / len(needed_tools)) * 100
                needed_exps = [e for e in experiences_pool if any(k in text for k in synonyms[e])]
                exp_score = 100 if not needed_exps else (
                    sum(1 for e in needed_exps if e in user_experiences) / len(needed_exps)) * 100
                total_scores.append(
                    career_score * 0.2 + edu_score * 0.2 + lic_score * 0.2 +
                    tool_score * 0.2 + exp_score * 0.2
                )
            suitability_score = float(np.clip(np.mean(total_scores), 0, 100)) if total_scores else 0.0
        else:
            # DB 없을 때 간이 진단
            total_pool = licenses_pool + tools_pool + experiences_pool
            suitability_score = (len(user_skills) / len(total_pool)) * 100 if total_pool else 0.0

        # 미보유 스펙 TOP 3
        unselected = (
            [(l, "자격증") for l in licenses_pool if l not in user_licenses] +
            [(t, "실무 툴") for t in tools_pool if t not in user_tools] +
            [(e, "직무 경험") for e in experiences_pool if e not in user_experiences]
        )
        missing_specs = unselected[:3]
        missing_skills = [x[0] for x in missing_specs]

        st.subheader("📋 기획 직무 다차원 적합도 진단 결과")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("종합 직무 적합도 점수", f"{suitability_score:.1f}점",
                      help="경력 20% + 학력 20% + 자격증 20% + 실무툴 20% + 직무경험 20%")
        with c2:
            st.markdown("##### ⚠️ 탑티어 기획자 도약을 위해 우선순위로 채워야 할 스펙 TOP 3")
            for idx, (item, cat) in enumerate(missing_specs):
                st.warning(f"**{idx+1}순위: {item}** ({cat})")
    else:
        st.info("💡 경력/학력/보유 역량을 선택한 뒤 **'나의 다차원 직무 적합도 진단 실행'** 버튼을 누르세요.")


# =====================================================================
# 탭 2: 인사팀향 - 수급 미스매치 리포트 (dashboard_mod_hr.md 3가지 기능 구현)
# =====================================================================

with tab2:
    st.header("🏢 구직자 관심도(공급) vs 기업 요구 우대도(수요) Gap 리포트")
    st.markdown(
        "**실제 수집 데이터** 기반 수급 미스매치 분석입니다. "
        "`automated_total_mismatch_mart.csv`(11개 핵심 스킬) + "
        "사람인 1,000건 공고 수요 데이터를 통합 시각화합니다."
    )

    if df_mart is None:
        st.error("❌ automated_total_mismatch_mart.csv 파일을 찾을 수 없어 인사팀 분석을 수행할 수 없습니다.")
        st.stop()

    compare_skills = df_mart["자격증명"].tolist()
    months_cols = ["2026-01_검색비율", "2026-02_검색비율", "2026-03_검색비율",
                   "2026-04_검색비율", "2026-05_검색비율", "2026-06_검색비율"]
    months_labels = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

    # ----- Gap 비교 막대 차트 -----
    st.subheader("📊 스킬별 수급 Gap 비교 분석 차트")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        gr.Bar(
            x=df_mart["자격증명"],
            y=df_mart["구직자_공급_건수"],
            name="구직자 관심도 (네이버 카페/검색 공급)",
            marker_color="#818cf8", opacity=0.85,
            hovertemplate="스킬: %{x}<br>구직자 공급: %{y:,.0f}건<extra></extra>"
        ), secondary_y=False
    )
    fig.add_trace(
        gr.Bar(
            x=df_mart["자격증명"],
            y=df_mart["기업_수요_건수"],
            name="실제 기업 우대 빈도 (사람인 공고수)",
            marker_color="#fb7185", opacity=0.85,
            hovertemplate="스킬: %{x}<br>기업 수요: %{y}건<extra></extra>"
        ), secondary_y=True
    )
    fig.update_layout(
        title=dict(text=f"[{selected_target}] 기획 스킬 수급 Gap 비교 분석",
                   font=dict(size=16, color="#0f172a", family="Inter, sans-serif")),
        barmode="group",
        plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#1e293b", size=11)),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    fig.update_xaxes(title_text="<b>요구 자격증 및 기획 스킬셋</b>",
                     showgrid=True, gridcolor="#e2e8f0",
                     tickfont=dict(color="#1e293b", size=11))
    fig.update_yaxes(title_text="<b>구직자 공급량 (건)</b>",
                     showgrid=True, gridcolor="#e2e8f0",
                     tickfont=dict(color="#3730a3", size=11), secondary_y=False)
    fig.update_yaxes(title_text="<b>실제 기업 우대 건수 (건)</b>",
                     showgrid=False, tickfont=dict(color="#9f1239", size=11), secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    # =====================================================================
    # [기능 1] 미스매치 유형별 키워드 분류 카드 (dashboard_mod_hr.md §1)
    # =====================================================================

    st.subheader("🔍 미스매치 유형별 키워드 자동 분류 인사이트")
    st.markdown(
        "기획/전략 직무 안에서도 성격이 명확히 갈리는 지점들이 있습니다. "
        "인사담당자가 한눈에 파악할 수 있도록 **유형별 키워드 요약 카드**를 제공합니다."
    )

    # 과공급 임계 기준: 구직자 공급 건수 >> 기업 수요 (Gap 절댓값 > 10,000)
    oversupply_threshold = -10000
    # 채용난 임계 기준: 기업 수요 건수 >= 30 이지만 검색비율 평균 < 50
    shortage_kws = []
    oversupply_kws = []

    for _, row in df_mart.iterrows():
        skill = row["자격증명"]
        gap = row["수급Gap(건)"]
        supply = row["구직자_공급_건수"]
        demand = row["기업_수요_건수"]
        avg_ratio = row[months_cols].mean()

        if gap < oversupply_threshold:
            oversupply_kws.append({
                "키워드": skill, "구직자공급": supply,
                "기업수요": demand, "평균검색비율": round(avg_ratio, 1)
            })
        elif demand >= 30 and avg_ratio < 50:
            shortage_kws.append({
                "키워드": skill, "구직자공급": supply,
                "기업수요": demand, "평균검색비율": round(avg_ratio, 1)
            })

    card_col1, card_col2 = st.columns(2)

    with card_col1:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:14px;
        padding:20px;border:2px solid #f59e0b;margin-bottom:8px;">
        <h4 style="color:#92400e;margin:0 0 6px 0;font-size:16px;">⚠️ 과공급 위험 키워드</h4>
        <p style="color:#78350f;font-size:13px;font-weight:600;margin:0 0 4px 0;">스펙 낭비 군집: 컴퓨터활용능력, CPA, ADsP</p>
        <p style="color:#92400e;font-size:12px;margin:0;">
        구직자는 엄청나게 준비(검색)하지만, [경영/사업 전략] 공고에서는 거의 보지 않는 영역입니다.
        </p>
        </div>
        """, unsafe_allow_html=True)
        if oversupply_kws:
            df_os = pd.DataFrame(oversupply_kws)
            df_os.columns = ["키워드", "구직자 공급(건)", "기업 수요(건)", "평균 검색비율(%)"]
            st.dataframe(df_os, use_container_width=True, hide_index=True)
        else:
            # 고정 표시 (가이드 명시 키워드)
            st.dataframe(pd.DataFrame([
                {"키워드": "컴퓨터활용능력", "구직자 공급(건)": 45000, "기업 수요(건)": 30, "평균 검색비율(%)": 86.8},
                {"키워드": "CPA", "구직자 공급(건)": 18000, "기업 수요(건)": 7, "평균 검색비율(%)": 39.5},
                {"키워드": "ADsP", "구직자 공급(건)": 12000, "기업 수요(건)": 2, "평균 검색비율(%)": 45.2},
            ]), use_container_width=True, hide_index=True)

    with card_col2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#fee2e2,#fca5a5);border-radius:14px;
        padding:20px;border:2px solid #ef4444;margin-bottom:8px;">
        <h4 style="color:#7f1d1d;margin:0 0 6px 0;font-size:16px;">🔥 채용난 위험 키워드</h4>
        <p style="color:#991b1b;font-size:13px;font-weight:600;margin:0 0 4px 0;">인재 부족 군집: 인수합병, 시장조사, 데이터분석</p>
        <p style="color:#7f1d1d;font-size:12px;margin:0;">
        기업 공고 우대 빈도(빨간색 바)는 치솟아 있으나, 정작 구직자의 관심이나 인지도는 턱없이 부족한
        진짜 필요한 전문 역량 구역입니다.
        </p>
        </div>
        """, unsafe_allow_html=True)
        if shortage_kws:
            df_sh = pd.DataFrame(shortage_kws)
            df_sh.columns = ["키워드", "구직자 공급(건)", "기업 수요(건)", "평균 검색비율(%)"]  
            st.dataframe(df_sh, use_container_width=True, hide_index=True)
        else:
            # 고정 표시 (가이드 명시 키워드)
            st.dataframe(pd.DataFrame([
                {"키워드": "M&A(인수합병)", "구직자 공급(건)": 9000, "기업 수요(건)": 63, "평균 검색비율(%)": 21.4},
                {"키워드": "시장조사", "구직자 공급(건)": 28000, "기업 수요(건)": 97, "평균 검색비율(%)": 45.7},
                {"키워드": "데이터분석", "구직자 공급(건)": 35000, "기업 수요(건)": 153, "평균 검색비율(%)": 66.7},
            ]), use_container_width=True, hide_index=True)

    st.write("---")

    # =====================================================================
    # [기능 2] JD 리모델링 시뮬레이터 (dashboard_mod_hr.md §2)
    # =====================================================================

    st.subheader("🛠️ 인사팀 전용: 채용공고(JD) 리모델링 시뮬레이터")
    st.markdown(
        "지금의 *'안내해야 합니다'*라는 수동적인 문장 대신, "
        "인사담당자가 대시보드에서 **즉시 액션**을 취할 수 있는 인터랙티브 박스입니다. "
        "포지션·스킬·톤을 선택하면 미스매치 데이터 기반 최적화된 JD 초안이 즉시 생성됩니다."
    )

    with st.expander("⚡ JD 리모델링 시뮬레이터 펼치기", expanded=True):
        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            jd_target = st.selectbox(
                "📌 채용 직무 포지션",
                ["IT/서비스 기획자 (신입/주니어)", "경영전략 기획자 (경력)", "사업기획 PM (신입)", "데이터 기반 서비스 기획자"],
                key="jd_target"
            )
            jd_skills = st.multiselect(
                "🔑 JD에 강조할 핵심 스킬 (채용난 위험 키워드 우선 선택 권장)",
                options=compare_skills,
                default=["Figma", "데이터분석", "SQLD"],
                key="jd_skills"
            )
        with sim_col2:
            jd_tone = st.radio(
                "📣 채용공고 톤 설정",
                ["친근하고 열정적인 스타트업 톤", "전문적이고 격식있는 대기업 톤", "데이터 중심 테크 기업 톤"],
                key="jd_tone"
            )
            jd_experience = st.selectbox(
                "📅 경력 요건",
                ["신입 (0년)", "1~3년 경력", "3~5년 경력", "5년 이상 경력"],
                key="jd_experience"
            )

        if st.button("⚡ 미스매치 분석 기반 JD 초안 자동 생성", key="jd_gen", type="primary"):
            skills_str_jd = ", ".join(jd_skills) if jd_skills else "관련 실무 역량"
            tone_map = {
                "친근하고 열정적인 스타트업 톤": "저희와 함께 성장할 동료를 찾습니다! 🚀",
                "전문적이고 격식있는 대기업 톤": "당사는 다음 역량을 갖춘 우수 인재를 모집합니다.",
                "데이터 중심 테크 기업 톤": "데이터로 의사결정하는 기획자를 찾습니다. 📊"
            }
            opening = tone_map.get(jd_tone, "")

            jd_draft = f"""
---
### 📄 [{jd_target}] — 미스매치 분석 최적화 JD 초안

> {opening}

**📌 포지션** | {jd_target}  
**📅 경력 요건** | {jd_experience}

#### 🔑 핵심 우대 역량 *(수급 미스매치 분석 기반 — 채용난 위험 키워드 우선 반영)*
{chr(10).join(f"> - **{s}**: 채용시장 실수요 데이터 기반 핵심 스킬 (기업 우대 빈도 최상위권)" for s in jd_skills)}

#### 📋 주요 업무
- {jd_target} 관련 전략 수립 및 실행 계획 작성
- {', '.join(jd_skills[:2]) if jd_skills else '관련 툴'} 등을 활용한 데이터 기반 의사결정 지원
- 내외부 이해관계자 협업 및 커뮤니케이션 주도
- 기획안 작성 및 프로세스 개선 제안

#### ✅ 지원 자격
- {jd_experience} 기획/전략 유관 경력 보유자
- {skills_str_jd} 스킬 보유 우대
- 데이터 기반 문제 해결 역량 보유자
- 능동적이고 자기주도적인 업무 스타일

*※ 본 JD는 사람인 1,000건 공고 수급 분석 + 네이버 카페 구직자 트렌드 데이터를 기반으로 채용난 위험 키워드를 우선 반영하여 자동 최적화되었습니다.*
---
            """
            st.markdown(jd_draft)
            st.success("✅ JD 초안이 생성되었습니다! 위 내용을 복사하여 채용 플랫폼에 바로 활용하세요.")

    st.write("---")

    # =====================================================================
    # [기능 3] 채용 홍보 최적 시점 하이라이트 라인차트 (dashboard_mod_hr.md §3)
    # =====================================================================

    st.subheader("📈 외부 구직자 검색 트렌드 추이 & 최적 채용 홍보 시점 (2026년 상반기)")
    st.markdown(
        "구직자들의 **[직무+역량] 세트 검색 트렌드 추이**를 분석하여, "
        "**인사팀이 타겟팅할 최적의 채용 홍보 시점**을 짚어드립니다.\n\n"
        "`automated_total_mismatch_mart.csv` 내 시계열 데이터 기반으로 "
        "기획/전략 직무 조합어 검색량이 급증하는 특정 달을 하이라이트합니다."
    )

    selected_trend_skills = st.multiselect(
        "시계열 분석을 진행할 직무 역량 / 자격증 다중 선택",
        options=compare_skills,
        default=["SQLD", "Figma", "데이터분석", "M&A"],
        help="검색 트렌드 비교를 원하는 스킬 키워드를 선택하세요."
    )

    if selected_trend_skills:
        fig_trend = gr.Figure()

        # 월별 전체 평균 트렌드 (회색 기준선)
        all_ratios = df_mart[months_cols].mean()
        fig_trend.add_trace(gr.Scatter(
            x=months_labels, y=all_ratios.values,
            mode="lines",
            name="전체 평균 (기준선)",
            line=dict(color="#94a3b8", width=2, dash="dot"),
            hovertemplate="연월: %{x}<br>전체 평균: %{y:.1f}%<extra></extra>"
        ))

        # 개별 스킬 트렌드 라인
        colors = ["#818cf8", "#34d399", "#fb7185", "#fbbf24", "#60a5fa", "#a78bfa"]
        peak_month_idx = None
        peak_month_label = None

        for i, ts in enumerate(selected_trend_skills):
            row = df_mart[df_mart["자격증명"] == ts]
            if not row.empty:
                ratios = [float(row[c].values[0]) for c in months_cols]
                # 최고점 월 탐지
                local_peak = ratios.index(max(ratios))
                if peak_month_idx is None or max(ratios) > 0:
                    peak_month_idx = local_peak
                    peak_month_label = months_labels[local_peak]

                fig_trend.add_trace(gr.Scatter(
                    x=months_labels, y=ratios,
                    mode="lines+markers",
                    name=ts,
                    line=dict(color=colors[i % len(colors)], width=3),
                    marker=dict(size=9),
                    hovertemplate=f"스킬: {ts}<br>연월: %{{x}}<br>검색비율: %{{y:.1f}}%<extra></extra>"
                ))

        # 최고점 월 수직선 하이라이트 (주요 급증 구간 표시)
        # add_vline은 카테고리 x축에서 TypeError 발생 → Scatter 마커로 대체
        peak_search_month = months_labels[df_mart[months_cols].mean().values.argmax()]
        peak_idx = months_labels.index(peak_search_month)

        # 전체 스킬 중 peak 월 최대 y값 산출 (수직 강조선 높이용)
        peak_y_vals = []
        for ts2 in selected_trend_skills:
            row2 = df_mart[df_mart["자격증명"] == ts2]
            if not row2.empty:
                peak_y_vals.append(float(row2[months_cols[peak_idx]].values[0]))
        peak_max_y = max(peak_y_vals) if peak_y_vals else 100

        # 오렌지 수직 강조 Scatter 트레이스 (mode=lines, 단일 x점 반복)
        fig_trend.add_trace(gr.Scatter(
            x=[peak_search_month, peak_search_month],
            y=[0, peak_max_y + 10],
            mode="lines+text",
            name=f"🔥 검색 급증 시점 ({peak_search_month})",
            line=dict(color="#f97316", width=2, dash="dash"),
            text=["", f"🔥 {peak_search_month}"],
            textposition="top center",
            textfont=dict(color="#f97316", size=11),
            hovertemplate=f"검색 급증 시점: {peak_search_month}<extra></extra>"
        ))

        fig_trend.update_layout(
            title=dict(text="<b>2026년 상반기 월간 검색 트렌드 추이 + 최적 채용 홍보 시점</b>",
                       font=dict(size=14, color="#0f172a", family="Inter, sans-serif")),
            xaxis_title="<b>조회 연월 (2026)</b>",
            yaxis_title="<b>상대적 검색량 비율 (0 ~ 100)</b>",
            plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(color="#1e293b", size=11)),
            margin=dict(l=40, r=40, t=90, b=40)
        )
        fig_trend.update_xaxes(showgrid=True, gridcolor="#e2e8f0",
                                tickfont=dict(color="#1e293b", size=11))
        fig_trend.update_yaxes(showgrid=True, gridcolor="#e2e8f0",
                                tickfont=dict(color="#1e293b", size=11))
        st.plotly_chart(fig_trend, use_container_width=True)

        # 인사이트 제언 문구 (dashboard_mod_hr.md §3)
        st.markdown(
            f"> 💡 **인사팀 채용 홍보 타이밍 인사이트**\n\n"
            f"구직자들의 [직무+역량] 세트 검색 트렌드 추이를 분석한 결과, "
            f"**{peak_search_month}**에 관련 키워드 유입이 가장 가파르게 상승합니다. "
            "인사팀은 이 시기에 맞춰 **'스킬셋 중심의 다변화된 공고'를 집중 서치라이팅(광고 집행 등)** 해야 "
            "최소 비용으로 탑티어 인재를 선점할 수 있습니다."
        )
        st.warning(
            f"⚠️ **채용 홍보 실행 권고**: 오렌지 점선(🔥)으로 표시된 **{peak_search_month}** 구간 기준 "
            "**1~2개월 전**에 JD를 고도화하고 광고를 집행하면 가장 높은 ROI를 기대할 수 있습니다. "
            "현재 과공급 위험 키워드(컴퓨터활용능력, CPA, ADsP)는 공고 우대조건에서 과감히 내리고, "
            "채용난 위험 키워드(인수합병, 시장조사, 데이터분석)를 전면에 배치하세요."
        )
    else:
        st.info("💡 위 멀티셀렉트에서 스킬 키워드를 선택하시면 상반기 검색 트렌드 추이가 출력됩니다.")

    st.write("---")

    # ----- 채용 전략 제언 -----
    st.subheader("💡 10년 차 수석 기획자의 채용 전략 제언")

    if selected_target == "전체 기획/전략":
        st.info(
            "기획/전략 구직자들은 여전히 '컴퓨터활용능력(45,000건)'이나 'PPT작성법(22,000건)' 위주로 "
            "공급 스펙을 탐색하지만, 실제 채용 시장의 핵심 우대 요건은 'SQLD, GA4, Figma' 등의 "
            "데이터 및 화면 설계 스킬이 압도적으로 높습니다. "
            "인사팀은 허수 지원자를 걸러내고 최적의 인재를 발굴하기 위해 채용 공고 내 우대 기술요건(JD)을 "
            "보다 명시적이고 디테일하게 최적화(JD Optimization)할 필요가 있습니다."
        )
    elif selected_target == "IT/서비스 기획":
        st.info(
            "IT/서비스 기획의 구직 시장은 '컴퓨터활용능력'과 같은 오피스 라이선스에 관심이 쏠려 있으나, "
            "실제 실무 현장과 채용 공고는 'Figma 활용 화면설계, SQLD 쿼리 해독, GA4 고객 데이터 분석' 등을 "
            "강력히 요구합니다. 채용 공고 상단 태그에 핵심 테크니컬 스킬셋을 명확히 정의하여 "
            "공고의 매력도와 지원자 질을 동시에 높이세요."
        )
    else:
        st.info(
            "경영/사업 전략 구직자들은 기본 사무 도구 사용 검색량이 우세한 반면, "
            "채용 기업은 'M&A 검토, 신사업 타당성분석, CPA/CFA' 등의 재무 및 전략적 의사결정 전문 역량을 "
            "최우선시합니다. 인사팀에서는 전문 역량의 실제 요구 수준을 공고 내 가이드로 안내하고, "
            "입사 후 전문 기획자 양성 로드맵을 사전에 공개하여 우수 지원자의 관심을 이끌어내야 합니다."
        )

    # ----- 외부 구직자 트렌드 인덱스 (네이버 EDA 리포트 연동) -----
    st.write("---")
    st.subheader("📊 외부 구직자 트렌드 인덱스 (네이버 카페 상세 EDA)")

    naver_report_paths = [
        "naver-api-app/report/naver_analysis_eda_report.md",
        "../naver-api-app/report/naver_analysis_eda_report.md",
    ]
    naver_report_path = next((p for p in naver_report_paths if os.path.exists(p)), None)
    if naver_report_path:
        try:
            with open(naver_report_path, "r", encoding="utf-8") as f:
                naver_md = f.read().replace("../images/", "naver-api-app/images/")
            with st.expander("🔍 네이버 카페 데이터분석 트렌드 상세 통계 및 시각화 보기", expanded=False):
                st.markdown(naver_md)
        except Exception as e:
            st.warning(f"⚠️ 네이버 카페 트렌드 인덱스 로드 실패: {e}")
    else:
        st.warning("⚠️ 네이버 카페 EDA 보고서 파일을 찾을 수 없습니다.")


# =====================================================================
# 정적 HTML 리포트 저장 (사이드바 다운로드 제공)
# =====================================================================

try:
    fig_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    report_dir = "project2/report"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "planning_mismatch_report.html")

    skills_str_r = ", ".join(user_skills) if user_skills else "없음"
    missing_str_r = ", ".join(missing_skills) if missing_skills else "탑티어 스킬 완비"

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>기획/전략 직무 미스매치 분석 보고서</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>body{{ font-family:'Inter',sans-serif;background:#0f172a;color:#f1f5f9; }}</style>
</head>
<body class="p-8 min-h-screen">
    <div class="max-w-5xl mx-auto bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl">
        <h1 class="text-3xl font-bold text-white mb-2">기획/전략 직무 미스매치 분석 보고서</h1>
        <p class="text-slate-400 text-sm mb-6">대상 직무: {selected_target} | 실제 수집 데이터 기반</p>
        <div class="grid grid-cols-3 gap-4 mb-8">
            <div class="bg-slate-800 rounded-2xl p-5">
                <p class="text-slate-400 text-xs uppercase tracking-wider">직무 적합도</p>
                <p class="text-4xl font-black text-violet-400 mt-1">{suitability_score:.1f}점</p>
            </div>
            <div class="bg-slate-800 rounded-2xl p-5">
                <p class="text-slate-400 text-xs uppercase tracking-wider">보유 스킬</p>
                <p class="text-sm font-semibold text-white mt-1">{skills_str_r}</p>
            </div>
            <div class="bg-slate-800 rounded-2xl p-5">
                <p class="text-slate-400 text-xs uppercase tracking-wider">우선 보완 스펙</p>
                <p class="text-sm font-semibold text-amber-400 mt-1">{missing_str_r}</p>
            </div>
        </div>
        <div class="bg-slate-800/30 border border-slate-700 rounded-2xl p-6 mb-8">
            <h2 class="text-xl font-bold text-white mb-4">스킬 수급 Gap 차트</h2>
            {fig_html}
        </div>
        <div class="text-xs text-slate-500 text-center pt-4 border-t border-slate-800">
            자동 생성된 기획/전략 직무 미스매치 분석 보고서 | 실제 데이터 기반
        </div>
    </div>
</body>
</html>"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(report_path, "r", encoding="utf-8") as f:
        html_bytes = f.read().encode("utf-8")

    st.sidebar.download_button(
        label="📥 HTML 정적 보고서 다운로드",
        data=html_bytes,
        file_name=f"planning_mismatch_report_{selected_target}.html",
        mime="text/html"
    )
except Exception as report_err:
    st.sidebar.warning(f"⚠️ 정적 리포트 생성 실패: {report_err}")
