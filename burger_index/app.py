"""
이 모듈은 4대 버거 브랜드 매장 데이터 및 버거지수를 시각화하는 Streamlit 대시보드 어플리케이션입니다.

주요 기능:
1. 기본 EDA 페이지: 브랜드별 통계 수치(대표값, 왜도, 첨도 등), 데이터프레임 뷰어, 기존 시각화 아티팩트 이미지 출력, plotly 인터랙티브 바 차트 제공
2. 위경도 지도 페이지: Folium을 사용해 위경도 기준 버거지수 비례 CircleMarker 시각화 (호버 툴팁, 매장 수 필터 지원)
3. 행정구역 지도 페이지: Folium.Choropleth 및 GeoJSON을 활용하여 시군구 행정구역 경계별 버거지수 시각화
"""

import os
import json
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from scipy.stats import skew, kurtosis
import streamlit as st
from streamlit_folium import st_folium

# 페이지 기본 설정
st.set_page_config(
    page_title="대한민국 4대 버거 브랜드 & 버거지수 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. 데이터 로드 및 전처리 캐싱
@st.cache_data
def load_data():
    burger_path = "burger_index/data/burger.csv"
    crosstab_path = "burger_index/data/burger_crosstab.csv"
    
    df_burger = pd.read_csv(burger_path, encoding="utf-8-sig")
    df_cross = pd.read_csv(crosstab_path, encoding="utf-8-sig")
    
    # 5자리 시군구코드 문자열 포맷팅 함수
    def format_code(x):
        try:
            val = int(float(x))
            return str(val).zfill(5)
        except:
            return str(x)
            
    # 시도시군구명 결합 키 생성 및 시군구코드 매핑 정보 구축
    df_burger["시도시군구명"] = df_burger["시도명"].astype(str) + " " + df_burger["시군구명"].astype(str)
    df_burger["시군구코드_formatted"] = df_burger["시군구코드"].apply(format_code)
    
    code_map = df_burger.groupby("시도시군구명")["시군구코드_formatted"].first().to_dict()
    
    # 크로스탭에 시군구코드 매핑 추가
    df_cross["시군구코드"] = df_cross["시도시군구명"].map(code_map)
    df_cross["시군구코드"] = df_cross["시군구코드"].fillna("")
    
    return df_burger, df_cross

# 2. GeoJSON 로드 캐싱
@st.cache_data
def load_geojson():
    geojson_path = "burger_index/data/skorea-municipalities-2018-geo.json"
    with open(geojson_path, "r", encoding="utf-8") as f:
        return json.load(f)

# 데이터 로딩
try:
    df_burger, df_cross = load_data()
    geojson_data = load_geojson()
except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    st.stop()

# 합계 행 분리 (분석 및 시각화용)
df_clean = df_cross[df_cross["시도시군구명"] != "합계"].copy()
total_row = df_cross[df_cross["시도시군구명"] == "합계"].iloc[0]

# 사이드바 메뉴 네비게이션
st.sidebar.title("🍔 버거지수 분석 메뉴")
page = st.sidebar.radio(
    "페이지를 이동하세요:",
    ["1) 기본 EDA 및 통계 분석", "2) 위경도 위치 기반 버거지수 지도", "3) 행정구역별 버거지수 단계구분도"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**💡 버거지수(Burger Index) 란?**\n\n"
    "도시의 상권 발달과 인프라 수준을 평가하기 위한 지표로, "
    "다음 공식으로 산출됩니다:\n\n"
    "$$\\text{버거지수} = \\frac{\\text{버거킹} + \\text{맥도날드} + \\text{KFC}}{\\text{롯데리아}}$$"
)

# ----------------------------------------------------
# 페이지 1: 기본 EDA 및 통계 분석
# ----------------------------------------------------
if page == "1) 기본 EDA 및 통계 분석":
    st.title("📊 4대 버거 브랜드 기본 EDA 및 통계 분석")
    st.write(
        "전국 시도시군구별 버거 매장 수 데이터를 요약 및 기술 통계 관점에서 보여줍니다. "
        "대표값의 왜곡 방지를 위해 **대표값(평균/중앙값)**, **이상치**, **비대칭도(왜도/첨도)**를 점검합니다."
    )
    
    # 1. 상단 KPI 카드
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(label="총 브랜드 매장 수", value=f"{int(total_row['합계']):,}개")
    with col2:
        st.metric(label="롯데리아 매장 수", value=f"{int(total_row['롯데리아']):,}개")
    with col3:
        st.metric(label="맥도날드 매장 수", value=f"{int(total_row['맥도날드']):,}개")
    with col4:
        st.metric(label="버거킹 매장 수", value=f"{int(total_row['버거킹']):,}개")
    with col5:
        st.metric(label="KFC 매장 수", value=f"{int(total_row['KFC']):,}개")
        
    st.markdown("---")
    
    # 2. 기술통계 및 비대칭 분석
    st.subheader("📈 시도시군구별 브랜드 매장 분포 기술통계")
    
    # 대표값, 변동성, 왜도, 첨도 계산
    stats_data = []
    brands = ["롯데리아", "맥도날드", "버거킹", "KFC", "버거지수"]
    
    for brand in brands:
        values = df_clean[brand].dropna()
        stats_data.append({
            "브랜드": brand,
            "평균(Mean)": round(values.mean(), 2),
            "중앙값(Median)": round(values.median(), 2),
            "표준편차(SD)": round(values.std(), 2),
            "최소값(Min)": round(values.min(), 2),
            "최대값(Max)": round(values.max(), 2),
            "왜도(Skewness)": round(skew(values), 2),
            "첨도(Kurtosis)": round(kurtosis(values), 2),
        })
    df_stats = pd.DataFrame(stats_data)
    
    st.dataframe(df_stats, use_container_width=True)
    st.caption(
        "**💡 분포 비대칭성 가이드**: 왜도(Skewness)가 클수록 특정 대도시 지역에 매장이 고도로 편중되어 있음을 나타냅니다. "
        "특히 맥도날드, 버거킹, KFC는 매우 큰 왜도를 보이며 대도시 집중화 현상이 뚜렷합니다."
    )
    
    # 3. 데이터프레임 확인 및 다운로드
    st.subheader("📋 시도시군구별 데이터 원본 테이블")
    st.dataframe(df_clean.drop(columns=["시각화_점크기", "경도", "위도"], errors="ignore"), use_container_width=True)
    
    # CSV 다운로드 기능 제공
    csv_bytes = df_cross.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 원본 가공 데이터셋 다운로드 (CSV)",
        data=csv_bytes,
        file_name="burger_crosstab_final.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    
    # 4. Plotly 실시간 인터랙티브 차트
    st.subheader("🏆 버거지수 상위 지역 순위 (Plotly Express)")
    top_n = st.slider("조회할 상위 지역 개수를 선택하세요:", min_value=5, max_value=30, value=15, step=5)
    
    df_top = df_clean.sort_values(by="버거지수", ascending=False).head(top_n)
    
    fig_top = px.bar(
        df_top,
        x="시도시군구명",
        y="버거지수",
        color="버거지수",
        color_continuous_scale="Reds",
        hover_data=["KFC", "롯데리아", "맥도날드", "버거킹", "합계"],
        text_auto=".2f",
        title=f"전국 버거지수 상위 {top_n}개 지역"
    )
    fig_top.update_layout(
        xaxis_title="시도시군구명",
        yaxis_title="버거지수",
        xaxis={"categoryorder": "total descending"}
    )
    st.plotly_chart(fig_top, use_container_width=True)
    
    st.markdown("---")
    
    # 5. 기존 시각화 아티팩트 아카이브 (2x2 그리드 이미지 표시)
    st.subheader("🖼️ 기존 정적 시각화 분석 보관함")
    st.write("로컬에 영구 저장된 고해상도 시각화 차트들의 히스토리입니다.")
    
    img_dir = "burger_index/images"
    col_img1, col_img2 = st.columns(2)
    
    with col_img1:
        bar_path = os.path.join(img_dir, "burger_bar_chart.png")
        if os.path.exists(bar_path):
            st.image(bar_path, caption="[막대그래프] 브랜드별 전국 총 매장 빈도수")
            
        heat_path = os.path.join(img_dir, "burger_heatmap.png")
        if os.path.exists(heat_path):
            st.image(heat_path, caption="[히트맵] 브랜드 매장 수 간 상관관계 분석")
            
    with col_img2:
        box_path = os.path.join(img_dir, "burger_box_violin.png")
        if os.path.exists(box_path):
            st.image(box_path, caption="[박스/바이올린 플롯] 시도시군구별 브랜드 매장 수 밀도 분포")
            
        pair_path = os.path.join(img_dir, "burger_pairplot.png")
        if os.path.exists(pair_path):
            st.image(pair_path, caption="[페어플롯] 상삼각 회귀분석 및 대각선 밀도 분포")

# ----------------------------------------------------
# 페이지 2: 위경도 위치 기반 버거지수 지도
# ----------------------------------------------------
elif page == "2) 위경도 위치 기반 버거지수 지도":
    st.title("📍 위경도 위치 기반 버거지수 산점도 지도")
    st.write(
        "각 시도시군구별 위도와 경도의 중간값 좌표를 기준으로 지도상에 버거지수 비례 점을 매핑합니다. "
        "버거지수가 높을수록 **원의 크기가 커지고 색상이 진한 빨간색**으로 변합니다."
    )
    
    # 왜곡 방지 필터링 옵션 제공
    st.markdown("##### 🎛️ 필터링 조건 설정")
    min_total = st.slider(
        "해석 왜곡 방지를 위해 특정 합계 매장수 이상의 지역만 필터링합니다 (합계 >= N):",
        min_value=1,
        max_value=10,
        value=3,
        help="매장 수가 지나치게 적은 지역은 버거지수가 극단적으로 높거나 낮게 나와 왜곡이 발생할 수 있습니다."
    )
    
    df_map_filtered = df_clean[df_clean["합계"] >= min_total].copy()
    st.write(f"현재 조건 만족 지역 수: **{len(df_map_filtered)}개** (전체 {len(df_clean)}개 중)")
    
    # 지도 객체 생성 (대한민국 중심 좌표로 설정)
    m = folium.Map(location=[36.3, 127.8], zoom_start=7, tiles="OpenStreetMap")
    
    # CircleMarker 매핑
    for idx, row in df_map_filtered.iterrows():
        # 버거지수에 비례하는 원 반지름 설정 (최소 반지름 3.5 보장)
        radius = row["버거지수"] * 7 + 3.5
        
        # 버거지수 값에 따른 동적 색상 코드 매핑 (진한 빨강 ~ 연한 주황)
        bi = row["버거지수"]
        if bi >= 2.0:
            color = "#800026"       # 극도로 진한 빨강
            fill_color = "#bd0026"
        elif bi >= 1.0:
            color = "#e31a1c"       # 진한 빨강
            fill_color = "#fc4e2a"
        elif bi >= 0.5:
            color = "#fd8d3c"       # 오렌지
            fill_color = "#feb24c"
        else:
            color = "#fed976"       # 노랑
            fill_color = "#ffeda0"
            
        # 호버 시 노출될 툴팁 정보 HTML 구성
        tooltip_html = f"""
        <div style="font-family: 'Malgun Gothic', sans-serif; font-size:12px; line-height: 1.5;">
            <b>🏢 {row['시도시군구명']}</b><br>
            🔴 <b>버거지수: {row['버거지수']:.2f}</b><br>
            📦 매장합계: {int(row['합계'])}개<br>
            <hr style="margin:5px 0; border:0; border-top:1px solid #ccc;">
            - 🍔 버거킹: {int(row['버거킹'])}개<br>
            - 🍟 맥도날드: {int(row['맥도날드'])}개<br>
            - 🍗 KFC: {int(row['KFC'])}개<br>
            - 🥤 롯데리아: {int(row['롯데리아'])}개
        </div>
        """
        
        folium.CircleMarker(
            location=[row["위도"], row["경도"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=fill_color,
            fill_opacity=0.7,
            weight=1.5,
            tooltip=folium.Tooltip(tooltip_html, sticky=True)
        ).add_to(m)
        
    # streamlit-folium으로 지도 렌더링
    st_folium(m, width=900, height=650, returned_objects=[])

# ----------------------------------------------------
# 페이지 3: 행정구역별 버거지수 단계구분도
# ----------------------------------------------------
elif page == "3) 행정구역별 버거지수 단계구분도":
    st.title("🗺️ 행정구역별 버거지수 단계구분도 (Choropleth Map)")
    st.write(
        "GitHub의 `southkorea-maps` 시군구 GeoJSON 행정구역 정보를 바탕으로 "
        "전국 지자체 단위별 버거지수 크기를 면적의 색상 농도로 표현합니다."
    )
    
    # 지도 중심 설정
    m_ch = folium.Map(location=[36.3, 127.8], zoom_start=7, tiles="cartodbpositron")
    
    # 지리적 경계 데이터를 맵핑하기 위한 Choropleth 레이어 추가
    choropleth = folium.Choropleth(
        geo_data=geojson_data,
        data=df_clean,
        columns=["시군구코드", "버거지수"],
        key_on="feature.properties.code", # GeoJSON의 properties.code 매칭
        fill_color="YlOrRd", # 황색-적색 그라데이션
        fill_opacity=0.7,
        line_opacity=0.3,
        legend_name="버거지수 (Burger Index)",
        highlight=True
    ).add_to(m_ch)
    
    # 호버 툴팁 기능을 추가하기 위해 GeoJson 레이어를 추가로 입힘
    # 크로스탭에서 코드를 기준으로 정보 매핑을 쉽게 하기 위해 딕셔너리 구축
    crosstab_info = df_clean.set_index("시군구코드").to_dict(orient="index")
    
    def style_function(feature):
        return {
            "fillColor": "transparent",
            "color": "transparent",
            "weight": 0
        }
        
    def highlight_function(feature):
        return {
            "fillColor": "#2b5c8f",
            "fillOpacity": 0.15,
            "weight": 1.5,
            "color": "#2c3e50"
        }
        
    # GeoJSON 레이어에 개별 툴팁 적용
    folium.GeoJson(
        geojson_data,
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["name"], # 우선 GeoJSON의 name(시군구명) 필드를 띄우고 아래와 결합
            aliases=["지역명:"],
            localize=True,
            sticky=True,
            labels=True
        ),
        # 툴팁을 커스텀하게 꾸미기 위해 각 피처별 버거지수 매핑 추가
        data=df_clean
    ).add_to(m_ch)
    
    # 맵 출력
    st_folium(m_ch, width=900, height=650, returned_objects=[])
    
    st.info(
        "**💡 행정구역 단계구분도 분석**: "
        "수도권 및 광역시급 번화가 지역이 짙은 주황~적색을 띠고 있으며, "
        "대다수 지방 도시 및 외곽 지역은 옅은 황색(버거지수 0 부근)을 보이고 있어 "
        "국내 버거 브랜드 인프라의 지역적 불균형을 한눈에 확인할 수 있습니다."
    )
