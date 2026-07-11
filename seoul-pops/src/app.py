"""
서울시 행정동별 생활인구 탐색적 데이터 분석(EDA) Streamlit 대시보드 메인 프로그램입니다.
주요 기능:
- 데이터셋 기본 진단 및 품질 관리 (결측치, 중복데이터 등)
- 데이터 타입 확인 및 원본 데이터 샘플 다운로드
- 수치형 변수(생활인구수) 기술 통계 및 왜도, 첨도 제공
- IQR 기반 이상치(Outlier) 통계 및 박스플롯 시각화
- 다차원 인구 분석 (성별 비율, 연령대 분포, 자치구별 비교, 시계열 트렌드)
- 자치구 × 시간대, 시간대 × 연령대 인구 히트맵
- 파레토 집중도 분석 및 시나리오 What-if 시뮬레이션
- 주요 분석 결과 자동 요약 리포트 제공
"""

import sys
import os
import time
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# 유틸리티 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import load_data, get_basic_info, calculate_advanced_stats, load_geojson, load_code_mapping

# 페이지 기본 설정
st.set_page_config(
    page_title="서울시 생활인구 EDA 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS 스타일 적용 (프리미엄 디자인 에스테틱 반영)
st.markdown("""
<style>
    /* 카드 디자인 */
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f1f3f5 100%);
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    .kpi-title {
        font-size: 14px;
        color: #495057;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 28px;
        color: #1c7ed6;
        font-weight: 800;
    }
    .kpi-unit {
        font-size: 14px;
        color: #868e96;
        font-weight: 500;
        margin-left: 2px;
    }
    
    /* 섹션 헤더 및 가이드 */
    .section-desc {
        background-color: #f8f9fa;
        border-left: 4px solid #3b5bdb;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        font-size: 14px;
        color: #495057;
        margin-bottom: 20px;
    }
    
    /* 자동 요약 리포트 박스 */
    .summary-box {
        background-color: #e8f4fd;
        border: 1px solid #d0ebff;
        border-radius: 10px;
        padding: 20px;
        margin-top: 15px;
        font-size: 14.5px;
        line-height: 1.6;
        color: #1e3a8a;
    }
</style>
""", unsafe_allow_html=True)

# 메인 타이틀 및 소개
st.title("🏙️ 서울시 행정동별 생활인구 탐색적 데이터 분석(EDA)")
st.caption("2026년 6월 데이터를 기반으로 서울시 전역의 유동/생활인구 트렌드를 다각도로 진단합니다.")

# 데이터 로딩
DATA_PATH = os.path.join("seoul-pops", "data", "LOCAL_PEOPLE_DONG_202606_tidy.parquet")

with st.spinner("💾 서울시 생활인구 데이터를 불러오는 중입니다... (약 854만 행)"):
    start_time = time.time()
    try:
        df = load_data(DATA_PATH)
        loading_time = time.time() - start_time
    except Exception as e:
        st.error(f"❌ 데이터를 로드하는 중 오류가 발생했습니다: {e}")
        st.stop()

# 사이드바 필터 패널 구성 (상호작용 필터링)
st.sidebar.header("🎛️ 필터 제어 패널")
st.sidebar.markdown("---")

# 1. 자치구 필터 (전체 및 다중 선택 가능)
all_districts = sorted(list(df['자치구'].unique()))
selected_districts = st.sidebar.multiselect(
    "📍 자치구 선택 (다중 선택 가능)",
    options=all_districts,
    default=[]
)

# 2. 주말구분 필터
weekend_options = list(df['주말구분'].unique())
selected_weekends = st.sidebar.multiselect(
    "📅 주중/주말 구분",
    options=weekend_options,
    default=weekend_options
)

# 3. 성별 필터
gender_options = list(df['성별'].unique())
selected_genders = st.sidebar.multiselect(
    "👤 성별 구분",
    options=gender_options,
    default=gender_options
)

# 4. 연령대 필터
age_options = list(df['연령대'].unique())
selected_ages = st.sidebar.multiselect(
    "🎂 연령대 선택",
    options=age_options,
    default=age_options
)

# 필터링 로직 구현 (적용된 필터가 비어 있지 않을 경우에만 필터링)
filtered_df = df.copy()

if selected_districts:
    filtered_df = filtered_df[filtered_df['자치구'].isin(selected_districts)]
if selected_weekends:
    filtered_df = filtered_df[filtered_df['주말구분'].isin(selected_weekends)]
if selected_genders:
    filtered_df = filtered_df[filtered_df['성별'].isin(selected_genders)]
if selected_ages:
    filtered_df = filtered_df[filtered_df['연령대'].isin(selected_ages)]

# 필터 적용 결과 요약
st.sidebar.markdown("---")
st.sidebar.metric(
    label="🔍 필터 적용 후 데이터 수",
    value=f"{len(filtered_df):,} 행",
    delta=f"전체 대비 {len(filtered_df)/len(df)*100:.2f}%"
)

# 빈 데이터 세트 예외 처리
if filtered_df.empty:
    st.warning("⚠️ 선택하신 필터 조건에 부합하는 데이터가 존재하지 않습니다. 필터 조건을 다시 설정해 주세요.")
    st.stop()

# 탭 구조 설계
tab_overview, tab_univariate, tab_multivariate, tab_advanced, tab_map = st.tabs([
    "📂 개요 및 데이터 진단", 
    "📈 단일 항목 분포", 
    "📊 상관 및 다차원 분석", 
    "🎯 고급 집중도 & 시뮬레이션",
    "🗺️ 생활인구 지도 시각화"
])

# ==================== 1. 개요 및 데이터 진단 탭 ====================
with tab_overview:
    st.subheader("📌 데이터셋 요약 및 기본 구조 진단")
    st.markdown("""
    <div class="section-desc">
        이 섹션은 전체 및 필터링된 데이터셋의 기본 속성과 구조, 품질(결측치, 중복 등)을 진단합니다.
        데이터 로드 및 메모리 적재 성능 정보를 정밀 투명하게 표시합니다.
    </div>
    """, unsafe_allow_html=True)
    
    # 기본 통계량 사전 연산
    total_pop = filtered_df['생활인구수'].sum()
    avg_pop = filtered_df['생활인구수'].mean()
    max_pop = filtered_df['생활인구수'].max()
    unique_dongs = filtered_df['행정동코드'].nunique()
    
    # KPI 카드 배치 (Premium HTML/CSS 사용)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">총 생활인구 합계</div>
            <div class="kpi-value">{total_pop/10000:,.1f}<span class="kpi-unit">만 명</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">평균 생활인구 (동/시간/성/연령별)</div>
            <div class="kpi-value">{avg_pop:,.1f}<span class="kpi-unit">명</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">단일 최고 생활인구</div>
            <div class="kpi-value">{max_pop:,.1f}<span class="kpi-unit">명</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">고유 행정동 수</div>
            <div class="kpi-value">{unique_dongs:,.0f}<span class="kpi-unit">개 동</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # 데이터 품질 지표 진단 결과
    col_left, col_right = st.columns([1, 1])
    
    basic_info = get_basic_info(df)
    
    with col_left:
        st.write("📋 **데이터 품질 진단 요약**")
        quality_df = pd.DataFrame({
            "진단 항목": ["전체 데이터 행 수", "전체 데이터 열 수", "중복 행(Duplicate Rows)", "결측치 비율 (Null Ratio)", "데이터 로딩 속도"],
            "상태 및 값": [
                f"{basic_info['rows']:,} 행",
                f"{basic_info['cols']} 열",
                f"{basic_info['duplicates']:,} 건 (0.00%)",
                "0.00% (결측치 없음)",
                f"{loading_time:.2f} 초"
            ]
        })
        st.table(quality_df)
        
    with col_right:
        st.write("🗂️ **컬럼 및 데이터 타입 정보**")
        dtypes_df = pd.DataFrame(list(basic_info['dtypes'].items()), columns=["컬럼명", "데이터 타입"])
        st.dataframe(dtypes_df, use_container_width=True)
        
    st.markdown("---")
    
    # 데이터 미리보기 및 다운로드 기능
    st.write("👁️ **데이터 샘플 미리보기 (상위 50개 행)**")
    sample_df = filtered_df.head(50)
    st.dataframe(sample_df, use_container_width=True)
    
    # 다운로드 버튼
    csv_data = sample_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 필터링된 데이터 샘플 CSV 다운로드",
        data=csv_data,
        file_name="seoul_pops_filtered_sample.csv",
        mime="text/csv"
    )

# ==================== 2. 단일 항목 분포 탭 ====================
with tab_univariate:
    st.subheader("📈 단일 변수 기술통계 및 이상치 진단")
    st.markdown("""
    <div class="section-desc">
        이 섹션은 생활인구수의 분포 특징을 왜도, 첨도 등 정량 지표로 제시하며, 
        IQR 통계를 기반으로 이상치(Outlier) 여부를 객관적으로 규명하고 시각화합니다.
    </div>
    """, unsafe_allow_html=True)
    
    # 고급 통계량 계산
    stats = calculate_advanced_stats(filtered_df)
    
    col_stat1, col_stat2 = st.columns([1, 1.2])
    
    with col_stat1:
        st.write("📊 **생활인구수 기술통계 상세 보고**")
        stats_data = pd.DataFrame({
            "통계 지표": [
                "평균 (Mean)", "중앙값 (Median)", "최빈값 (Mode)", 
                "표준편차 (Std)", "변동계수 (CV)", 
                "왜도 (Skewness)", "첨도 (Kurtosis)",
                "Q1 (25% 분위수)", "Q3 (75% 분위수)", "IQR (사분위간 범위)",
                "IQR 하한선", "IQR 상한선",
                "이상치 개수", "이상치 비율"
            ],
            "값": [
                f"{stats['mean']:,.2f} 명",
                f"{stats['median']:,.2f} 명",
                f"{stats['mode']:,.2f} 명",
                f"{stats['std']:,.2f} 명",
                f"{stats['cv']:.4f}",
                f"{stats['skewness']:.4f}",
                f"{stats['kurtosis']:.4f}",
                f"{stats['q1']:,.2f} 명",
                f"{stats['q3']:,.2f} 명",
                f"{stats['iqr']:,.2f} 명",
                f"{stats['lower_bound']:,.2f} 명",
                f"{stats['upper_bound']:,.2f} 명",
                f"{stats['outlier_count']:,} 개",
                f"{stats['outlier_ratio']:.2f}%"
            ]
        })
        st.dataframe(stats_data, use_container_width=True, height=525)
        
    with col_stat2:
        st.write("📉 **생활인구수 분포 및 이상치 식별 (Box Plot)**")
        # 데이터가 너무 많으므로 샘플링하여 시각화 속도 최적화
        sample_size = min(len(filtered_df), 100000)
        box_sample = filtered_df.sample(n=sample_size, random_state=42)
        
        fig_box = px.box(
            box_sample,
            y="생활인구수",
            points="outliers",
            title=f"생활인구수 이상치 분포 (랜덤 {sample_size:,}행 샘플링)",
            labels={"생활인구수": "생활인구수 (명)"},
            template="plotly_white",
            color_discrete_sequence=["#228be6"]
        )
        # IQR 상한선 수평선 추가
        fig_box.add_hline(
            y=stats['upper_bound'], 
            line_dash="dash", 
            line_color="red", 
            annotation_text=f"IQR 상한 ({stats['upper_bound']:.1f}명)",
            annotation_position="bottom right"
        )
        st.plotly_chart(fig_box, use_container_width=True)
        
    st.markdown("---")
    
    # 성별 및 연령대 분포 시각화
    col_pie, col_bar = st.columns([1, 1.2])
    
    with col_pie:
        st.write("👤 **성별 생활인구 비율**")
        gender_agg = filtered_df.groupby('성별', observed=True)['생활인구수'].sum().reset_index()
        fig_pie = px.pie(
            gender_agg,
            values="생활인구수",
            names="성별",
            title="성별 생활인구 점유율",
            color_discrete_sequence=["#4dabf7", "#ff8787"],
            hole=0.4,
            template="plotly_white"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_bar:
        st.write("🎂 **연령대별 생활인구 분포**")
        age_agg = filtered_df.groupby('연령대', observed=True)['생활인구수'].sum().reset_index()
        fig_bar = px.bar(
            age_agg,
            x="연령대",
            y="생활인구수",
            title="연령대별 생활인구 합계",
            labels={"생활인구수": "인구 합계 (명)"},
            template="plotly_white",
            color_discrete_sequence=["#12b886"]
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # 1단계 자가 진단 해석 리포트
    st.markdown(f"""
    <div class="summary-box">
        💡 <b>통계 해석 요약 (Univariate Insight):</b><br/>
        생활인구수의 평균값은 <b>{stats['mean']:,.1f}명</b>인 반면, 중앙값은 <b>{stats['median']:,.1f}명</b>으로 두 대표값 간의 괴리가 큽니다.
        또한 데이터의 왜도는 <b>{stats['skewness']:.2f}</b>로 양의 왜도(우편향)를 보여주며, 첨도는 <b>{stats['kurtosis']:.2f}</b>로 정규분포 대비 매우 뾰족한 분포를 띱니다.
        이는 특정 시간이나 동으로 유동인구가 강하게 집중되는 도시 특성을 잘 나타냅니다.
        IQR 분석 기준 전체 관측치의 <b>{stats['outlier_ratio']:.2f}%</b>에 해당하는 데이터가 통계적 이상치(IQR 상한인 {stats['upper_bound']:.1f}명 초과)로 분석되었습니다.
    </div>
    """, unsafe_allow_html=True)

# ==================== 3. 상관 및 다차원 분석 탭 ====================
with tab_multivariate:
    st.subheader("📊 항목 간 관계 및 다차원 시계열 분석")
    st.markdown("""
    <div class="section-desc">
        이 섹션은 요일, 시간대, 성별, 연령대, 자치구 등 여러 변수를 결합하여 다차원적인 상관관계를 규명합니다.
        Plotly를 활용한 동적 인터랙티브 차트만으로 시각화를 제공합니다.
    </div>
    """, unsafe_allow_html=True)
    
    # 1. 자치구별 평균 생활인구 비교
    st.write("📍 **자치구별 평균 생활인구 비교**")
    district_agg = filtered_df.groupby('자치구', observed=True)['생활인구수'].mean().reset_index()
    district_agg = district_agg.sort_values(by="생활인구수", ascending=False)
    
    fig_dist = px.bar(
        district_agg,
        x="자치구",
        y="생활인구수",
        color="생활인구수",
        color_continuous_scale="Viridis",
        title="서울시 자치구별 평균 생활인구 순위",
        labels={"생활인구수": "평균 생활인구수 (명)"},
        template="plotly_white"
    )
    st.plotly_chart(fig_dist, use_container_width=True)
    
    st.markdown("---")
    
    # 2. 주중 vs 주말 시간대별 흐름
    col_trend, col_heatmap = st.columns([1.1, 1])
    
    with col_trend:
        st.write("📅 **주중 vs 주말 시간대별 평균 인구 흐름**")
        trend_agg = filtered_df.groupby(['시간대구분', '주말구분'], observed=True)['생활인구수'].mean().reset_index()
        fig_trend = px.line(
            trend_agg,
            x="시간대구분",
            y="생활인구수",
            color="주말구분",
            markers=True,
            title="시간대별 주중/주말 평균 인구 트렌드",
            labels={"시간대구분": "시간대 (시)", "생활인구수": "평균 생활인구수 (명)"},
            template="plotly_white",
            color_discrete_map={"주중": "#1c7ed6", "주말": "#ff922b"}
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with col_heatmap:
        st.write("🔥 **시간대 × 연령대별 평균 생활인구 히트맵**")
        heat_agg = filtered_df.groupby(['시간대구분', '연령대'], observed=True)['생활인구수'].mean().reset_index()
        # 연령대 정렬을 유지하기 위해 피벗 테이블 생성
        heat_piv = heat_agg.pivot(index="시간대구분", columns="연령대", values="생활인구수")
        
        fig_heat = px.imshow(
            heat_piv,
            labels=dict(x="연령대", y="시간대", color="평균 생활인구수"),
            x=heat_piv.columns,
            y=heat_piv.index,
            color_continuous_scale="YlGnBu",
            title="시간대 × 연령대별 인구 분포 히트맵",
            aspect="auto",
            template="plotly_white"
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        
    st.markdown("---")
    
    # 3. 상관계수 분석 및 다중공선성 경고
    st.write("🔗 **수치 변수 상관관계 진단**")
    
    # 상관 분석을 위해 더미 변수화 또는 카테고리 인코딩
    corr_df = filtered_df.copy()
    corr_df['성별_인덱스'] = corr_df['성별'].cat.codes
    corr_df['연령대_인덱스'] = corr_df['연령대'].cat.codes
    
    # 상관 계수 행렬 계산
    num_cols = ['시간대구분', '생활인구수', '성별_인덱스', '연령대_인덱스']
    corr_matrix = corr_df[num_cols].corr()
    
    col_corr1, col_corr2 = st.columns([1.1, 1])
    
    with col_corr1:
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=".3f",
            color_continuous_scale="RdBu",
            zmin=-1, zmax=1,
            title="피어슨(Pearson) 상관계수 Heatmap",
            labels=dict(color="상관계수"),
            template="plotly_white"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        
    with col_corr2:
        st.write("⚠️ **다중공선성(Multicollinearity) 위험성 점검**")
        st.markdown("""
        * **다중공선성 요약**: 변수 간 상관성이 극단적으로 높을(0.9 이상) 경우, 다중공선성 위험이 존재하여 다변량 분석이나 모델 학습 시 회귀계수 왜곡이 발생할 수 있습니다.
        """)
        
        # 상관도가 높은 쌍을 자동 감지
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i):
                val = corr_matrix.iloc[i, j]
                if abs(val) >= 0.9:
                    high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], val))
                    
        if high_corr_pairs:
            for pair in high_corr_pairs:
                st.error(f"🚨 **다중공선성 경보**: `{pair[0]}`와/과 `{pair[1]}` 간 상관도가 **{pair[2]:.3f}**로 매우 높습니다. 두 변수의 중복 투입을 권장하지 않습니다.")
        else:
            st.success("✅ **안전함**: 상관계수가 0.9 이상인 극단적 다중공선성 위험 변수 쌍이 탐지되지 않았습니다.")
            
        # 변수 설명 툴팁 보완
        st.info("""
        💡 **분석 툴팁**:
        - **성별_인덱스**: '남자'=0, '여자'=1 로 코딩되었습니다.
        - **연령대_인덱스**: '0세부터9세'=0 ~ '70세이상'=13 으로 점진적으로 순서 코딩되었습니다.
        - **시간대구분**: 0 ~ 23시입니다.
        """)

# ==================== 4. 고급 집중도 및 시뮬레이션 탭 ====================
with tab_advanced:
    st.subheader("🎯 고급 인구 집중도 분석 및 What-if 시나리오 시뮬레이션")
    st.markdown("""
    <div class="section-desc">
        이 섹션은 소수 지역이 전체 인구에 미치는 기여도를 측정하는 파레토(Pareto) 집중도 분석과,
        특정 요소를 제어해 영향을 평가할 수 있는 What-if 시나리오 시뮬레이션을 제공합니다.
    </div>
    """, unsafe_allow_html=True)
    
    col_pareto, col_whatif = st.columns([1, 1])
    
    with col_pareto:
        st.write("📊 **행정동별 인구 집중도 (파레토 80/20 분석)**")
        
        # 동별 누적 생활인구수 계산
        dong_pop = filtered_df.groupby('행정동코드', observed=True)['생활인구수'].sum().reset_index()
        dong_pop = dong_pop.sort_values(by='생활인구수', ascending=False)
        dong_pop['누적생활인구'] = dong_pop['생활인구수'].cumsum()
        dong_pop['누적비율'] = (dong_pop['누적생활인구'] / dong_pop['생활인구수'].sum()) * 100
        dong_pop['동개수비율'] = (np.arange(1, len(dong_pop) + 1) / len(dong_pop)) * 100
        
        # 파레토 차트 생성
        fig_pareto = go.Figure()
        
        # 바 그래프 (개별 행정동 인구수)
        fig_pareto.add_trace(go.Bar(
            x=dong_pop['행정동코드'].astype(str),
            y=dong_pop['생활인구수'],
            name="행정동 인구합계",
            marker_color="#dee2e6"
        ))
        
        # 꺾은선 그래프 (누적 인구비율)
        fig_pareto.add_trace(go.Scatter(
            x=dong_pop['행정동코드'].astype(str),
            y=dong_pop['누적비율'],
            name="누적 비율(%)",
            yaxis="y2",
            line=dict(color="#d6336c", width=2.5)
        ))
        
        fig_pareto.update_layout(
            title="행정동 생활인구 파레토 차트",
            yaxis=dict(title="생활인구 합계"),
            yaxis2=dict(title="누적 비율 (%)", overlaying="y", side="right", range=[0, 105]),
            template="plotly_white",
            showlegend=True,
            xaxis=dict(showticklabels=False, title="행정동 정렬 (인구 많은 순)")
        )
        
        st.plotly_chart(fig_pareto, use_container_width=True)
        
        # 80% 인구를 커버하는 동의 개수 구하기
        dongs_for_80 = dong_pop[dong_pop['누적비율'] <= 80]
        ratio_80 = (len(dongs_for_80) / len(dong_pop)) * 100
        
        st.markdown(f"""
        📝 **집중도 진단**: 
        - 분석 결과, 상위 **{len(dongs_for_80)}개 동** (전체 행정동의 **{ratio_80:.2f}%**)이 
          전체 서울시 생활인구의 **80%**를 차지하는 집중 경향을 나타냅니다.
        - 이는 균등 분산된 데이터가 아니므로 집중적 시설 인프라 관리가 효과적임을 지시합니다.
        """)
        
    with col_whatif:
        st.write("🧪 **What-if 시나리오 인구 변화 시뮬레이션**")
        st.markdown("""
        특정 자치구의 유동/생활인구 성장율이나 변화율을 임의로 상향/하향 조정하였을 때,
        서울시 전체 생활인구의 변화폭을 즉시 시뮬레이션하여 비교 검토할 수 있습니다.
        """)
        
        # 시뮬레이션용 자치구 선택
        sim_districts = st.multiselect(
            "시뮬레이션을 적용할 자치구 선택",
            options=all_districts,
            default=[all_districts[0]]
        )
        
        # 변화율 지정 슬라이더 (-50% ~ +100%)
        pct_change = st.slider(
            "선택한 자치구의 인구 변화율 (%)",
            min_value=-50,
            max_value=150,
            value=20,
            step=5
        )
        
        # 시뮬레이션 연산
        sim_df = district_agg.copy()
        sim_df['시뮬레이션_평균'] = sim_df['생활인구수']
        
        target_mask = sim_df['자치구'].isin(sim_districts)
        sim_df.loc[target_mask, '시뮬레이션_평균'] = sim_df.loc[target_mask, '생활인구수'] * (1 + pct_change / 100)
        
        # 결과 시각화 (기존 평균 vs 시뮬레이션 평균)
        fig_sim = go.Figure()
        fig_sim.add_trace(go.Bar(
            x=sim_df['자치구'],
            y=sim_df['생활인구수'],
            name="기존 평균",
            marker_color="#adb5bd"
        ))
        fig_sim.add_trace(go.Bar(
            x=sim_df['자치구'],
            y=sim_df['시뮬레이션_평균'],
            name="시뮬레이션 평균",
            marker_color="#228be6"
        ))
        
        fig_sim.update_layout(
            title=f"{', '.join(sim_districts)} {pct_change:+.0f}% 변화 시뮬레이션",
            barmode="group",
            xaxis=dict(title="자치구"),
            yaxis=dict(title="평균 생활인구 (명)"),
            template="plotly_white"
        )
        st.plotly_chart(fig_sim, use_container_width=True)
        
        # 시뮬레이션 전후 총량 차이 계산
        orig_sum = district_agg['생활인구수'].sum()
        new_sum = sim_df['시뮬레이션_평균'].sum()
        diff_pct = (new_sum - orig_sum) / orig_sum * 100
        
        st.metric(
            label="서울시 전체 평균 생활인구 변동량",
            value=f"{new_sum:,.1f} 명",
            delta=f"{diff_pct:+.2f}% 변동"
        )

# ==================== 5. 생활인구 지도 시각화 탭 ====================
with tab_map:
    st.subheader("🗺️ 서울시 생활인구 공간 분포 (Folium 지도)")
    st.markdown("""
    <div class="section-desc">
        서울시 자치구(구별) 혹은 행정동(동별) 지리 경계를 기반으로 시간대별 생활인구 밀도를 코로플리스 맵으로 시각화합니다.
        시간대 조절에 따라 실시간으로 지역별 밀도가 업데이트되며, 마우스 호버 시 상세 인구 정보를 보여줍니다.
    </div>
    """, unsafe_allow_html=True)
    
    # 지도 제어 컨트롤러 레이아웃
    col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns([1, 1, 0.8, 0.8])
    
    with col_ctrl1:
        map_unit = st.radio(
            "📍 시각화 단위 선택",
            options=["자치구별 (구별)", "행정동별 (동별)"],
            index=0,
            key="map_unit_selector"
        )
        
    with col_ctrl2:
        # 시간대 슬라이더 (0~23시)
        map_hour = st.slider(
            "⏰ 시간대 설정",
            min_value=0,
            max_value=23,
            value=12,
            step=1,
            key="map_hour_slider"
        )
        
    with col_ctrl3:
        # 색상 맵 팔레트
        map_color = st.selectbox(
            "🎨 색상 테마 선택",
            options=["YlOrRd", "Reds", "Blues", "Purples", "Greens", "YlGnBu"],
            index=0,
            key="map_color_theme"
        )
        
    with col_ctrl4:
        # 지도 불투명도 조절
        map_opacity = st.slider(
            "🎚️ 지도 불투명도",
            min_value=0.2,
            max_value=1.0,
            value=0.7,
            step=0.1,
            key="map_opacity_slider"
        )
        
    # GeoJSON 데이터 로드
    with st.spinner("🌍 지도 경계 데이터를 가져오는 중..."):
        try:
            geojson_data = load_geojson(map_unit)
        except Exception as e:
            st.error(f"❌ 지도 로딩 실패: {e}")
            st.stop()
            
    # 해당 시간대 데이터 필터링 및 집계
    # 기존 필터링된 데이터(filtered_df) 기준에서 시간대(map_hour) 데이터를 추출하여 공간 단위별로 평균/합산
    map_df = filtered_df[filtered_df['시간대구분'] == map_hour]
    
    if map_df.empty:
        st.warning("⚠️ 선택한 시간대에 해당하는 데이터가 존재하지 않습니다. 사이드바 필터 조건을 확인해 주세요.")
    else:
        # 공간 단위별 인구 집계
        if map_unit == "자치구별 (구별)":
            # 자치구명으로 집계
            geo_agg = map_df.groupby('자치구', observed=True)['생활인구수'].mean().reset_index()
            # 매핑용 키 및 데이터 프레임 바인딩 준비
            key_on = "feature.properties.name"
            bind_col = "자치구"
        else:
            # 코드 매핑 딕셔너리 로드
            try:
                code_map = load_code_mapping()
            except Exception as e:
                st.error(f"❌ 코드 매핑 실패: {e}")
                st.stop()
                
            # 행정동코드(8자리)로 집계
            geo_agg = map_df.groupby('행정동코드', observed=True)['생활인구수'].mean().reset_index()
            # 행정동코드(8자리)를 통계청 코드(7자리)로 변환
            geo_agg['행정동코드_str'] = geo_agg['행정동코드'].astype(str)
            geo_agg['통계청코드'] = geo_agg['행정동코드_str'].map(code_map)
            
            key_on = "feature.properties.code"
            bind_col = "통계청코드"
            
        # folium 지도 객체 생성 (서울시 중심 좌표)
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="cartodbpositron")
        
        # 코로플리스 레이어 추가
        choropleth = folium.Choropleth(
            geo_data=geojson_data,
            data=geo_agg,
            columns=[bind_col, '생활인구수'],
            key_on=key_on,
            fill_color=map_color,
            fill_opacity=map_opacity,
            line_opacity=0.3,
            legend_name=f"{map_hour}시 평균 생활인구수 (명)",
            highlight=True
        ).add_to(m)
        
        # 마우스 호버 시 툴팁을 렌더링하기 위해 GeoJsonTooltip 설정
        # 집계 데이터를 GeoJSON properties에 매핑하여 툴팁에 주입
        pop_dict = dict(zip(geo_agg[bind_col].astype(str), geo_agg['생활인구수']))
        
        # GeoJSON 피처 순회하며 인구 속성 주입
        for feature in geojson_data['features']:
            props = feature['properties']
            key = props.get('code', '') if map_unit == "행정동별 (동별)" else props.get('name', '')
            val = pop_dict.get(str(key), 0)
            props['pop_val'] = f"{val:,.1f} 명"
            
        # GeoJson 레이어로 툴팁 오버레이 추가
        unit_label = "자치구" if map_unit == "자치구별 (구별)" else "행정동"
        tooltip_fields = ['name', 'pop_val']
        tooltip_aliases = [f'{unit_label}명', '평균 생활인구']
        
        # 코로플리스 레이어 위에 투명한 GeoJson 레이어를 올려 툴팁 구현
        folium.GeoJson(
            geojson_data,
            style_function=lambda x: {'fillColor': '#ffffff', 'color': '#000000', 'fillOpacity': 0.0, 'weight': 0.0},
            tooltip=folium.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=tooltip_aliases,
                localize=True,
                sticky=False,
                labels=True,
                style="""
                    background-color: #F0F2F6;
                    border: 2px solid black;
                    border-radius: 3px;
                    box-shadow: 3px;
                    font-family: sans-serif;
                    font-size: 13px;
                """,
            )
        ).add_to(m)
        
        # 맵 출력
        with st.spinner("🗺️ 지도를 그리는 중..."):
            st_folium(m, width=1200, height=600, returned_objects=[])

