"""
네이버 쇼핑 검색 API 데이터를 수집하여 상품 가격 분포(Box Plot), 브랜드 점유율(Pie Chart),
판매처 분포 등을 분석하고 시각화하는 페이지입니다.
"""
# -*- coding: utf-8 -*-
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from api_client import NaverApiClient

st.title("📦 쇼핑 상품 검색 및 가격 분석")

# 1. API Key 및 파라미터 로드
client_id = st.session_state.get("client_id") or os.environ.get("NAVER_CLIENT_ID", "")
client_secret = st.session_state.get("client_secret") or os.environ.get("NAVER_CLIENT_SECRET", "")
keywords = st.session_state.get("keywords", [])

if not client_id or not client_secret:
    st.warning("⚠️ 사이드바(왼쪽)에서 네이버 API Client ID와 Client Secret을 입력해 주세요.")
    st.stop()

if not keywords:
    st.info("💡 사이드바에서 분석할 검색어를 1개 이상 입력해 주세요.")
    st.stop()

# 2. 분석 대상 검색어 선택 및 조회 파라미터 설정
st.markdown("### ⚙️ 쇼핑 검색 설정")
col1, col2, col3 = st.columns(3)

with col1:
    # 여러 입력어 중 분석할 단일 키워드 선택
    selected_keyword = st.selectbox(
        "분석할 검색어 선택",
        options=keywords,
        index=0,
        help="사이드바에 입력한 검색어 중 분석할 대상 하나를 선택하세요."
    )

with col2:
    display_num = st.slider(
        "상품 수집 개수",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
        help="한 번에 가져올 상품의 개수를 설정합니다. (최대 100개)"
    )

with col3:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["sim", "date", "asc", "dsc"],
        format_func=lambda x: {
            "sim": "유사도순",
            "date": "날짜순",
            "asc": "가격 낮은순",
            "dsc": "가격 높은순"
        }[x],
        index=0,
        help="상품 검색 결과의 정렬 기준을 정의합니다."
    )

# 3. API 호출
client = NaverApiClient(client_id, client_secret)

with st.spinner(f"'{selected_keyword}' 상품 정보를 수집 중입니다..."):
    @st.cache_data(show_spinner=False)
    def fetch_shopping_search(c_id, c_secret, query, display, sort):
        api = NaverApiClient(c_id, c_secret)
        return api.search_shop(query, display=display, sort=sort)

    response_data = fetch_shopping_search(
        client_id, client_secret, selected_keyword, display_num, sort_option
    )

# 4. 데이터 정제 및 분석
if response_data and "items" in response_data:
    items = response_data["items"]
    
    if items:
        records = []
        for item in items:
            # HTML 태그 제거용 처리 (상품명에 <b> 태그 등이 포함되어 있을 수 있음)
            clean_title = item["title"].replace("<b>", "").replace("</b>", "")
            
            records.append({
                "이미지": item["image"],
                "상품명": clean_title,
                "최저가": int(item["lprice"]) if item["lprice"] else 0,
                "브랜드": item["brand"] if item["brand"] else "미지정",
                "판매처": item["mallName"] if item["mallName"] else "기타",
                "카테고리": f"{item['category1']} > {item['category2']}",
                "링크": item["link"]
            })
            
        df = pd.DataFrame(records)
        
        # 5. 핵심 가격 통계 (IQR 이상치 탐지 포함)
        prices = df["최저가"][df["최저가"] > 0]
        
        if not prices.empty:
            mean_price = prices.mean()
            median_price = prices.median()
            min_price = prices.min()
            max_price = prices.max()
            
            # IQR 분석
            q1 = prices.quantile(0.25)
            q3 = prices.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = prices[(prices < lower_bound) | (prices > upper_bound)]
            
            st.markdown("### 💰 상품 가격 통계 분석")
            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
            with kpi_col1:
                st.metric("최저 가격", f"{int(min_price):,}원")
            with kpi_col2:
                st.metric("최고 가격", f"{int(max_price):,}원")
            with kpi_col3:
                st.metric("평균 가격", f"{int(mean_price):,}원")
            with kpi_col4:
                st.metric("중앙 가격(Median)", f"{int(median_price):,}원")
                
            # 통계 해석 설명 요약
            st.info(
                f"💡 수집된 {len(df)}개 상품의 평균가 대비 중앙값 비율은 {(median_price/mean_price)*100:.1f}% 입니다. "
                f"가격의 50%는 {int(q1):,}원 ~ {int(q3):,}원 사이에 분포하며, "
                f"통계적 극단값(이상치)에 속하는 상품은 총 {len(outliers)}개 식별되었습니다."
            )
            
            # 가격 분포 시각화 (Plotly)
            st.markdown("#### 📊 가격 분포 차트 (Box Plot & Histogram)")
            fig_col1, fig_col2 = st.columns(2)
            
            with fig_col1:
                fig_box = px.box(
                    df,
                    y="최저가",
                    title="가격 분포 범위 및 이상치 확인 (Box Plot)",
                    labels={"최저가": "가격 (원)"},
                    points="all",
                    template="plotly_white"
                )
                st.plotly_chart(fig_box, use_container_width=True)
                
            with fig_col2:
                fig_hist = px.histogram(
                    df,
                    x="최저가",
                    nbins=20,
                    title="가격 구간별 상품 빈도 (Histogram)",
                    labels={"최저가": "가격 (원)", "count": "상품 수"},
                    template="plotly_white"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
        
        # 6. 브랜드 및 판매처 점유율 분석
        st.markdown("### 📊 브랜드 및 판매처 점유율")
        fig_col3, fig_col4 = st.columns(2)
        
        with fig_col3:
            # 상위 10개 브랜드 점유율
            brand_counts = df["브랜드"].value_counts().reset_index()
            brand_counts.columns = ["브랜드", "상품수"]
            fig_brand = px.pie(
                brand_counts.head(10),
                values="상품수",
                names="브랜드",
                title="상위 10개 브랜드 점유율",
                hole=0.4,
                template="plotly_white"
            )
            fig_brand.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_brand, use_container_width=True)
            
        with fig_col4:
            # 판매처 분포
            mall_counts = df["판매처"].value_counts().reset_index()
            mall_counts.columns = ["판매처", "상품수"]
            fig_mall = px.bar(
                mall_counts.head(10),
                x="상품수",
                y="판매처",
                orientation="h",
                title="상위 10개 판매처(쇼핑몰) 분포",
                labels={"상품수": "상품 수", "판매처": "쇼핑몰"},
                template="plotly_white"
            )
            fig_mall.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_mall, use_container_width=True)
            
        # 7. 수집 상품 리스트
        st.markdown("### 📋 수집 상품 상세 목록")
        
        # 렌더링용 구성
        st.dataframe(
            df,
            column_config={
                "이미지": st.column_config.ImageColumn("이미지", width="medium"),
                "상품명": st.column_config.TextColumn("상품명", width="large"),
                "최저가": st.column_config.NumberColumn("최저가 (원)", format="%d원", width="small"),
                "브랜드": st.column_config.TextColumn("브랜드", width="small"),
                "판매처": st.column_config.TextColumn("판매처", width="small"),
                "카테고리": st.column_config.TextColumn("카테고리", width="medium"),
                "링크": st.column_config.LinkColumn("링크", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 데이터 다운로드
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 수집 상품 데이터 CSV 다운로드",
            data=csv,
            file_name=f"naver_shopping_{selected_keyword}.csv",
            mime="text/csv"
        )
        
    else:
        st.warning("⚠️ 검색 결과가 존재하지 않습니다.")
else:
    st.info("데이터를 로드하지 못했습니다. API 정보를 확인해 주십시오.")
