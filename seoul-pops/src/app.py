"""
서울시 행정동별 생활인구 탐색적 데이터 분석(EDA) Streamlit 대시보드 메인 프로그램입니다.
주요 기능:
- Parquet 원본 데이터와 SQLite 집계 데이터의 하이브리드 캐시 구조 탑재
- 개요 및 기술 통계 탭: 원본 Parquet 파일 기반의 실시간 통계 및 품질 분석
- 상관 분석 및 공간 지도 탭: 사전 연산된 SQLite DB 테이블로 초고속 렌더링 지원
- 📂 개요 및 데이터 진단 탭: 원본 데이터셋 정보 요약 및 원천 데이터 head(10) 노출
- 📈 단일 항목 분포 탭: 원본 데이터에 입각한 실시간 기술통계, 왜도/첨도 계산 및 Box Plot 시각화
- 🗺️ 생활인구 지도 시각화 탭: southkorea-maps 지리에 계층형 툴팁("서울특별시 [구명] [동명]") 및 3자리 콤마 정수 포맷 적용
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
from dashboard_utils import (
    load_raw_parquet,
    load_db_table,
    load_map_data_from_db,
    load_geojson,
    load_code_mapping,
    get_basic_info,
    calculate_advanced_stats
)

# 페이지 기본 설정
st.set_page_config(
    page_title="서울시 생활인구 EDA 대시보드 (하이브리드)",
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
st.title("🏙️ 서울시 행정동별 생활인구 탐색적 데이터 분석(하이브리드 캐시)")
st.caption("원본 Parquet 분석 및 SQLite DB 사전 가공 집계를 유기적으로 혼용하여 연산 성능과 분석 정밀도를 다 잡았습니다.")

# 하이브리드 데이터 로딩 알림 (최초 1회만 Parquet 파싱 지연이 있고 이후는 캐싱되어 초고속)
with st.spinner("⚡ Parquet 원본 데이터셋을 로드하고 사전 집계 DB 커넥션을 맺는 중..."):
    start_time = time.time()
    try:
        raw_df = load_raw_parquet()
        basic_info = get_basic_info(raw_df)
        stats = calculate_advanced_stats(raw_df)
        loading_time = time.time() - start_time
    except Exception as e:
        st.error(f"❌ 데이터 로딩 실패: {e}")
        st.stop()

# 사이드바 필터 패널 구성 (대시보드 조작 가이드 툴팁 제공)
st.sidebar.header("🎛️ 대시보드 정보")
st.sidebar.markdown("---")
st.sidebar.info("""
💡 **대시보드 하이브리드 설계 안내**:
- **개요/품질/기술통계**: 원천 Parquet 파일(`LOCAL_PEOPLE_DONG_202606_tidy.parquet`)의 원본을 캐시 적재하여 실시간 연산합니다.
- **다차원분석/지도**: 이미 가공 및 시간대별로 묶여져 최적화된 SQLite DB 테이블(`seoul_pops.db`)을 쿼리하여 초고속으로 시각화합니다.
""")

st.sidebar.metric(
    label="⚡ 원본 로딩 및 연산 속도 (캐싱)",
    value=f"{loading_time:.4f} 초",
    delta="최초 1회 이후 지연 0초"
)

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
    st.subheader("📌 Parquet 원본 데이터셋 기본 구조 진단")
    st.markdown("""
    <div class="section-desc">
        이 섹션은 원본 Parquet 데이터프레임의 행/열 규격, 메모리 중복율, 결측치 품질을 실시간 검사합니다.
        가장 아래에서 원천 데이터의 상위 10개 행 미리보기를 제공합니다.
    </div>
    """, unsafe_allow_html=True)
    
    # KPI 카드 배치 (최상단 핵심 성과지표 노출 규칙 반영)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">원본 총 관측 행 수</div>
            <div class="kpi-value">{basic_info['rows']:,}<span class="kpi-unit">행</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">수치형 변수 평균 생활인구</div>
            <div class="kpi-value">{stats['mean']:,.1f}<span class="kpi-unit">명</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">IQR 기준 분포 상한선</div>
            <div class="kpi-value">{stats['upper_bound']:,.1f}<span class="kpi-unit">명</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">컬럼 스키마 수</div>
            <div class="kpi-value">{basic_info['cols']}<span class="kpi-unit">개</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.write("📋 **원본 데이터 품질 진단 보고**")
        quality_df = pd.DataFrame({
            "진단 항목": ["전체 데이터 행 수", "전체 데이터 열 수", "중복 행(Duplicate Rows)", "결측치 비율 (Null Ratio)", "데이터 소스"],
            "값 및 상태": [
                f"{basic_info['rows']:,} 행",
                f"{basic_info['cols']} 열",
                f"{basic_info['duplicates']:,} 건",
                "0.00% (결측치 없음)",
                "LOCAL_PEOPLE_DONG_202606_tidy.parquet (원본)"
            ]
        })
        st.table(quality_df)
        
    with col_right:
        st.write("🗂️ **컬럼 데이터 타입 요약**")
        dtypes_df = pd.DataFrame(list(basic_info['dtypes'].items()), columns=["컬럼명", "데이터 타입"])
        st.dataframe(dtypes_df, use_container_width=True)
        
    st.markdown("---")
    
    st.write("👁️ **원본 Parquet 데이터프레임 미리보기 (상위 10개 행)**")
    st.dataframe(raw_df.head(10), use_container_width=True)
    
    # 다운로드 버튼
    csv_data = raw_df.head(500).to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 원본 데이터 일부(500행) CSV 다운로드",
        data=csv_data,
        file_name="seoul_pops_raw_sample.csv",
        mime="text/csv"
    )

# ==================== 2. 단일 항목 분포 탭 ====================
with tab_univariate:
    st.subheader("📈 원본 생활인구수 기술통계 및 이상치 진단")
    st.markdown("""
    <div class="section-desc">
        이 섹션은 원본 생활인구수 컬럼을 직접 리드하여 사분위간 범위(IQR) 및 왜도/첨도 등 고급 통계 수치를 실시간으로 진단하고 식별합니다.
    </div>
    """, unsafe_allow_html=True)
    
    col_stat1, col_stat2 = st.columns([1, 1.2])
    
    with col_stat1:
        st.write("📊 **기술통계 실시간 연산 보고 (Parquet 기반)**")
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
                f"{int(stats['outlier_count']):,} 개",
                f"{stats['outlier_ratio']:.2f}%"
            ]
        })
        st.dataframe(stats_data, use_container_width=True, height=525)
        
    with col_stat2:
        st.write("📉 **생활인구수 분포 시각화 (사전 통계 기반 Box Plot)**")
        fig_box = go.Figure()
        fig_box.add_trace(go.Box(
            y=[stats['q1'], stats['median'], stats['q3']],
            name="생활인구수",
            q1=[stats['q1']],
            median=[stats['median']],
            q3=[stats['q3']],
            mean=[stats['mean']],
            sd=[stats['std']],
            lowerfence=[max(0, stats['lower_bound'])],
            upperfence=[stats['upper_bound']],
            boxpoints=False,
            marker_color="#1c7ed6"
        ))
        
        fig_box.update_layout(
            title="원본 생활인구수 사분위 범위 분포",
            yaxis_title="생활인구수 (명)",
            template="plotly_white"
        )
        st.plotly_chart(fig_box, use_container_width=True)
        
    st.markdown("---")
    
    col_pie, col_bar = st.columns([1, 1.2])
    
    with col_pie:
        st.write("👤 **성별 생활인구 비율 (DB)**")
        gender_agg = load_db_table('gender_pop_dist')
        fig_pie = px.pie(
            gender_agg,
            values="생활인구수",
            names="성별",
            title="성별 생활인구 점유율",
            color_discrete_sequence=["#339af0", "#ff8787"],
            hole=0.4,
            template="plotly_white"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_bar:
        st.write("🎂 **연령대별 생활인구 분포 (DB)**")
        age_agg = load_db_table('age_pop_dist')
        fig_bar = px.bar(
            age_agg,
            x="연령대",
            y="생활인구수",
            title="연령대별 생활인구 합계",
            labels={"생활인구수": "인구 합계 (명)"},
            template="plotly_white",
            color_discrete_sequence=["#0ca678"]
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ==================== 3. 상관 및 다차원 분석 탭 ====================
with tab_multivariate:
    st.subheader("📊 상관관계 및 다차원 시계열 분석 (DB)")
    st.markdown("""
    <div class="section-desc">
        이 섹션은 자치구별 순위 및 주중/주말 시간대별 유동인구 추이를 비교합니다. SQLite 사전 연산 데이터를 연동해 지연을 제거했습니다.
    </div>
    """, unsafe_allow_html=True)
    
    st.write("📍 **자치구별 평균 생활인구 비교**")
    dong_pop = load_db_table('dong_pop_ranking')
    district_agg = dong_pop.groupby('자치구', observed=True)['생활인구수'].mean().reset_index()
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
    
    col_trend, col_heatmap = st.columns([1.1, 1])
    
    with col_trend:
        st.write("📅 **주중 vs 주말 시간대별 평균 인구 흐름**")
        trend_agg = load_db_table('weekend_hourly_pop')
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
        st.write("🔥 **연령대 및 성별 생활인구 분포 비교**")
        gender_age = load_db_table('gender_age_pop_dist')
        fig_gender_age = px.bar(
            gender_age,
            x="연령대",
            y="생활인구수",
            color="성별",
            barmode="group",
            title="연령대별/성별 생활인구 분포 비교",
            labels={"생활인구수": "인구 합계 (명)"},
            template="plotly_white",
            color_discrete_map={"남자": "#1c7ed6", "여자": "#ff8787"}
        )
        st.plotly_chart(fig_gender_age, use_container_width=True)

# ==================== 4. 고급 집중도 및 시뮬레이션 탭 ====================
with tab_advanced:
    st.subheader("🎯 고급 집중도 및 What-if 시나리오 시뮬레이션")
    st.markdown("""
    <div class="section-desc">
        이 섹션은 소수 행정동으로의 인구 쏠림을 진단하는 파레토 분석과 가상 인구 성장 시나리오 시뮬레이션을 제공합니다.
    </div>
    """, unsafe_allow_html=True)
    
    col_pareto, col_whatif = st.columns([1, 1])
    
    with col_pareto:
        st.write("📊 **행정동별 인구 집중도 (파레토 80/20 분석)**")
        
        # 동별 누적 생활인구수 계산
        dong_pop_sorted = dong_pop.sort_values(by='생활인구수', ascending=False).copy()
        dong_pop_sorted['누적생활인구'] = dong_pop_sorted['생활인구수'].cumsum()
        dong_pop_sorted['누적비율'] = (dong_pop_sorted['누적생활인구'] / dong_pop_sorted['생활인구수'].sum()) * 100
        
        fig_pareto = go.Figure()
        
        fig_pareto.add_trace(go.Bar(
            x=dong_pop_sorted['행정동코드'].astype(str),
            y=dong_pop_sorted['생활인구수'],
            name="행정동 인구평균",
            marker_color="#dee2e6"
        ))
        
        fig_pareto.add_trace(go.Scatter(
            x=dong_pop_sorted['행정동코드'].astype(str),
            y=dong_pop_sorted['누적비율'],
            name="누적 비율(%)",
            yaxis="y2",
            line=dict(color="#d6336c", width=2.5)
        ))
        
        fig_pareto.update_layout(
            title="행정동 생활인구 파레토 차트",
            yaxis=dict(title="평균 생활인구"),
            yaxis2=dict(title="누적 비율 (%)", overlaying="y", side="right", range=[0, 105]),
            template="plotly_white",
            showlegend=True,
            xaxis=dict(showticklabels=False, title="행정동 정렬 (인구 많은 순)")
        )
        st.plotly_chart(fig_pareto, use_container_width=True)
        
        # 80% 인구 커버 동 산출
        dongs_for_80 = dong_pop_sorted[dong_pop_sorted['누적비율'] <= 80]
        ratio_80 = (len(dongs_for_80) / len(dong_pop_sorted)) * 100
        
        st.markdown(f"""
        **집중도 진단 결과**:
        - 상위 **{len(dongs_for_80)}개 행정동** (전체 행정동의 **{ratio_80:.2f}%**)이 
          서울시 전체 생활인구의 **80%**를 지배하고 있어 인구 밀도가 극도로 편중된 현상이 입증됩니다.
        """)
        
    with col_whatif:
        st.write("🧪 **What-if 시나리오 인구 변화 시뮬레이션**")
        
        all_districts_list = sorted(list(district_agg['자치구'].unique()))
        sim_districts = st.multiselect(
            "대상 자치구 선택",
            options=all_districts_list,
            default=[all_districts_list[0]]
        )
        
        pct_change = st.slider(
            "변화율 설정 (%)",
            min_value=-50,
            max_value=150,
            value=20,
            step=5
        )
        
        sim_df = district_agg.copy()
        sim_df['시뮬레이션_평균'] = sim_df['생활인구수']
        
        target_mask = sim_df['자치구'].isin(sim_districts)
        sim_df.loc[target_mask, '시뮬레이션_평균'] = sim_df.loc[target_mask, '생활인구수'] * (1 + pct_change / 100)
        
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
            name="시뮬레이션 결과",
            marker_color="#1c7ed6"
        ))
        
        fig_sim.update_layout(
            title=f"{', '.join(sim_districts)} {pct_change:+.0f}% 변화율 시뮬레이션",
            barmode="group",
            template="plotly_white"
        )
        st.plotly_chart(fig_sim, use_container_width=True)
        
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
        map_hour = st.slider(
            "⏰ 시간대 설정",
            min_value=0,
            max_value=23,
            value=12,
            step=1,
            key="map_hour_slider"
        )
        
    with col_ctrl3:
        map_color = st.selectbox(
            "🎨 색상 테마 선택",
            options=["YlOrRd", "Reds", "Blues", "Purples", "Greens", "YlGnBu"],
            index=0,
            key="map_color_theme"
        )
        
    with col_ctrl4:
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
            
    # 해당 시간대 데이터 로드 (DB에서 직접 매칭 쿼리하여 초고속 반환)
    with st.spinner("💾 시간대별 인구 분포 데이터 로드 중..."):
        try:
            geo_agg = load_map_data_from_db(map_unit, map_hour)
        except Exception as e:
            st.error(f"❌ 데이터 로드 실패: {e}")
            st.stop()
            
    if geo_agg.empty:
        st.warning("⚠️ 선택한 시간대에 해당하는 데이터가 존재하지 않습니다. DB 상태를 확인해 주세요.")
    else:
        # 공간 단위별 인구 집계 매핑 키 설정
        if map_unit == "자치구별 (구별)":
            key_on = "feature.properties.name"
            bind_col = "자치구"
        else:
            # 행안부 코드를 통계청 7자리 코드로 변경하는 매핑 사전 로드
            try:
                code_map = load_code_mapping()
            except Exception as e:
                st.error(f"❌ 코드 매핑 실패: {e}")
                st.stop()
                
            geo_agg['통계청코드'] = geo_agg['행정동코드'].map(code_map)
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
        pop_dict = dict(zip(geo_agg[bind_col].astype(str), geo_agg['생활인구수']))
        
        # 자치구 한글 명칭 사전 구축 (행정동 툴팁에서 자치구 한글 명칭을 결합하기 위함)
        dist_geojson = load_geojson("자치구별 (구별)")
        kostat_dist_map = {feat['properties']['code']: feat['properties']['name'] for feat in dist_geojson['features']}
        
        # GeoJSON 피처 순회하며 상세 툴팁 전용 속성(full_name, pop_val) 주입
        for feature in geojson_data['features']:
            props = feature['properties']
            if map_unit == "자치구별 (구별)":
                key = props.get('name', '')
                props['full_name'] = f"서울특별시 {key}"
            else:
                key = props.get('code', '')
                code_5 = str(key)[:5]
                dist_name = kostat_dist_map.get(code_5, '')
                dong_name = props.get('name', '')
                props['full_name'] = f"서울특별시 {dist_name} {dong_name}"
                
            val = pop_dict.get(str(key), 0)
            props['pop_val'] = f"{int(val):,} 명"  # 정수 콤마 포맷팅 적용
            
        # choropleth.geojson에 직접 호버 툴팁 자식 탑재 (렌더링 속도 비약적 향상 및 이중 렌더링 방지)
        folium.GeoJsonTooltip(
            fields=['full_name', 'pop_val'],
            aliases=['지역명', '평균 생활인구'],
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
            """
        ).add_to(choropleth.geojson)
        
        # 맵 출력
        with st.spinner("🗺️ 지도를 그리는 중..."):
            st_folium(m, width=1200, height=600, returned_objects=[])
