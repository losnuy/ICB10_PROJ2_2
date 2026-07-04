"""
네이버 데이터랩 쇼핑인사이트 키워드 클릭 트렌드 API 데이터를 수집 및 시각화하고,
선택한 쇼핑 카테고리 내에서 키워드별 쇼핑 선호 추이를 비교 및 분석하는 페이지입니다.
"""
# -*- coding: utf-8 -*-
import os
import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from api_client import NaverApiClient

st.title("🛒 쇼핑 검색어 트렌드 분석 (쇼핑인사이트)")

# 1. API Key 및 파라미터 로드
client_id = st.session_state.get("client_id") or os.environ.get("NAVER_CLIENT_ID", "")
client_secret = st.session_state.get("client_secret") or os.environ.get("NAVER_CLIENT_SECRET", "")
keywords = st.session_state.get("keywords", [])
start_date = st.session_state.get("start_date", None)
end_date = st.session_state.get("end_date", None)

if not client_id or not client_secret:
    st.warning("⚠️ 사이드바(왼쪽)에서 네이버 API Client ID와 Client Secret을 입력해 주세요.")
    st.stop()

if not keywords:
    st.info("💡 사이드바에서 분석할 검색어를 1개 이상 입력해 주세요. (예: 텐트,타프,침낭)")
    st.stop()

# 2. 쇼핑 카테고리 설정 및 필터 UI 구성
st.markdown("### ⚙️ 쇼핑 카테고리 및 필터")

# 네이버 쇼핑 주요 대분류 카테고리 ID 정의
categories = {
    "패션의류 (50000000)": "50000000",
    "패션잡화 (50000001)": "50000001",
    "화장품/미용 (50000002)": "50000002",
    "디지털/가전 (50000003)": "50000003",
    "가구/인테리어 (50000004)": "50000004",
    "출산/육아 (50000005)": "50000005",
    "식품 (50000006)": "50000006",
    "스포츠/레저 (50000007)": "50000007",
    "생활/건강 (50000008)": "50000008",
    "여가/생활편의 (50000009)": "50000009",
    "면세점 (50000010)": "50000010",
    "도서 (50005542)": "50005542"
}

col1, col2, col3 = st.columns(3)

with col1:
    # "도서 (50005542)" 카테고리를 기본 선택(active)으로 지정
    default_index = list(categories.keys()).index("도서 (50005542)")
    selected_cat_name = st.selectbox(
        "쇼핑 대분류 카테고리",
        options=list(categories.keys()),
        index=default_index,
        help="조회하고자 하는 쇼핑 분야를 선택하세요."
    )
    category_id = categories[selected_cat_name]

with col2:
    time_unit = st.selectbox(
        "구간 단위",
        options=["date", "week", "month"],
        format_func=lambda x: {"date": "일간", "week": "주간", "month": "월간"}[x],
        index=0,
        help="데이터 집계 기준을 선택합니다."
    )

with col3:
    device = st.selectbox(
        "기기 유형",
        options=[None, "pc", "mo"],
        format_func=lambda x: {None: "전체", "pc": "PC", "mo": "모바일"}[x],
        index=0,
        help="검색 기기 기준 필터입니다."
    )

col4, col5 = st.columns(2)
with col4:
    gender = st.selectbox(
        "사용자 성별 필터",
        options=[None, "m", "f"],
        format_func=lambda x: {None: "전체", "m": "남성", "f": "여성"}[x],
        index=0,
        help="쇼핑 고객의 성별 필터입니다."
    )
with col5:
    ages = st.multiselect(
        "사용자 연령대 필터 (다중 선택 가능)",
        options=["10", "20", "30", "40", "50", "60"],
        default=[],
        format_func=lambda x: f"{x}대",
        help="쇼핑 고객의 연령대를 필터링합니다. 선택하지 않으면 전 연령대를 조회합니다."
    )

# 연령대 필터가 비어 있으면 None으로 처리
ages_param = ages if ages else None

# 날짜 변환
start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

# 3. API 요청 파라미터 빌드 및 호출
client = NaverApiClient(client_id, client_secret)

# keyword 파라미터 구조화 (name과 param 설정)
keyword_param = [{"name": kw, "param": [kw]} for kw in keywords]

with st.spinner("네이버 쇼핑인사이트 데이터를 조회 중입니다..."):
    @st.cache_data(show_spinner=False)
    def fetch_shopping_trend_data(c_id, c_secret, start, end, unit, cat, kws, dev, gen, age_list):
        api = NaverApiClient(c_id, c_secret)
        return api.get_shopping_trend(start, end, unit, cat, kws, dev, gen, age_list)

    data = fetch_shopping_trend_data(
        client_id, client_secret, start_date_str, end_date_str,
        time_unit, category_id, keyword_param, device, gender, ages_param
    )

# 4. 결과 시각화 및 분석
if data and "results" in data:
    records = []
    for result in data["results"]:
        title = result["title"]
        data_points = result.get("data", [])
        for dp in data_points:
            records.append({
                "날짜": pd.to_datetime(dp["period"]),
                "키워드": title,
                "클릭비율": float(dp["ratio"])
            })
            
    if records:
        df = pd.DataFrame(records)
        
        # 5. Plotly 시각화
        st.markdown("### 📊 카테고리 내 키워드별 클릭 트렌드")
        st.caption(f"※ **{selected_cat_name}** 분야 내에서 설정한 검색어들 간 상대적인 클릭 횟수 비율 추이입니다.")
        
        fig = px.line(
            df,
            x="날짜",
            y="클릭비율",
            color="키워드",
            title=f"쇼핑 트렌드 추이 ({start_date_str} ~ {end_date_str})",
            labels={"클릭비율": "상대 클릭 비율 (%)", "날짜": "기간"},
            template="plotly_white"
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        
        # 6. 통계 요약 및 분석 가치 향상 (Item Analysis)
        st.markdown("### 📋 쇼핑 트렌드 통계 요약")
        
        summary_data = []
        for kw in keywords:
            kw_df = df[df["키워드"] == kw]
            if not kw_df.empty:
                mean_val = kw_df["클릭비율"].mean()
                median_val = kw_df["클릭비율"].median()
                max_row = kw_df.loc[kw_df["클릭비율"].idxmax()]
                max_val = max_row["클릭비율"]
                max_date = max_row["날짜"].strftime("%Y-%m-%d")
                std_val = kw_df["클릭비율"].std()
                cv_val = (std_val / mean_val) if mean_val > 0 else 0
                
                summary_data.append({
                    "쇼핑 키워드": kw,
                    "평균 클릭 비율": f"{mean_val:.2f}%",
                    "중앙값 클릭 비율": f"{median_val:.2f}%",
                    "최대 클릭 비율": f"{max_val:.2f}% ({max_date})",
                    "변동성 (CV)": f"{cv_val:.3f}"
                })
                
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            # 카드형 KPI 표출
            st.markdown("#### 💡 주요 쇼핑 인사이트")
            cols = st.columns(len(keywords))
            for i, kw in enumerate(keywords):
                kw_df = df[df["키워드"] == kw]
                if not kw_df.empty:
                    mean_val = kw_df["클릭비율"].mean()
                    max_val = kw_df["클릭비율"].max()
                    with cols[i]:
                        st.metric(
                            label=f"🛍️ {kw} 평균 클릭",
                            value=f"{mean_val:.2f}%",
                            delta=f"최대 {max_val:.1f}%"
                        )
                        
        # 데이터 원본 및 다운로드
        with st.expander("📂 원본 데이터 보기"):
            df_pivot = df.pivot(index="날짜", columns="키워드", values="클릭비율").reset_index()
            df_pivot["날짜"] = df_pivot["날짜"].dt.strftime("%Y-%m-%d")
            st.dataframe(df_pivot, use_container_width=True, hide_index=True)
            
            csv = df_pivot.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 CSV 데이터 다운로드",
                data=csv,
                file_name=f"naver_shopping_trend_{category_id}_{start_date_str}_{end_date_str}.csv",
                mime="text/csv"
            )
            
    else:
        st.warning("⚠️ 선택하신 조건과 기간에 대한 쇼핑 트렌드 클릭 데이터가 존재하지 않습니다.")
else:
    st.info("데이터를 로드하지 못했습니다. API 설정 또는 카테고리 ID가 맞는지 확인해 주세요.")
