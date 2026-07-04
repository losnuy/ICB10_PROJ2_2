"""
네이버 오픈 API 통합 키워드 상세 분석 페이지

사용자가 입력한 여러 검색어 중 대표 키워드를 하나 선택하여
해당 키워드에 대한 트렌드 추이, 블로그 리뷰, 카페 글 반응, 최신 뉴스 동향, 쇼핑 상품 분석 결과를
탭(Tab) 레이아웃 형태로 한 화면에 모아서 입체적으로 시각화 및 분석하는 기능을 제공합니다.
"""
# -*- coding: utf-8 -*-
import os
import re
import datetime
from collections import Counter
import pandas as pd
import plotly.express as px
import streamlit as st
from api_client import NaverApiClient

st.title("🔍 통합 키워드 상세 분석")
st.markdown("하나의 검색어를 바탕으로 네이버의 트렌드, 블로그, 카페, 뉴스, 쇼핑 데이터를 한눈에 모아보고 종합적으로 분석합니다.")

# 1. API Key 및 파라미터 로드
client_id = st.session_state.get("client_id") or os.environ.get("NAVER_CLIENT_ID", "")
client_secret = st.session_state.get("client_secret") or os.environ.get("NAVER_CLIENT_SECRET", "")
keywords = st.session_state.get("keywords", [])
start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")

if not client_id or not client_secret:
    st.warning("⚠️ 사이드바(왼쪽)에서 네이버 API Client ID와 Client Secret을 입력해 주세요.")
    st.stop()

if not keywords:
    st.info("💡 사이드바에서 분석할 검색어를 1개 이상 입력해 주세요.")
    st.stop()

# 2. 분석 검색어 선택
selected_keyword = st.selectbox(
    "상세 분석할 핵심 키워드 선택",
    options=keywords,
    index=0,
    help="선택한 키워드로 트렌드, 블로그, 카페, 뉴스, 쇼핑 결과를 종합 로드합니다."
)

# 기본 날짜 보정
if not start_date:
    start_date = datetime.date.today() - datetime.timedelta(days=90)
if not end_date:
    end_date = datetime.date.today()

# 3. 탭 구성
tab_trend, tab_blog, tab_cafe, tab_news, tab_shop = st.tabs([
    "📈 검색 트렌드 추이",
    "📝 블로그 리뷰 분석",
    "💬 카페 커뮤니티 반응",
    "📰 실시간 뉴스 동향",
    "🛒 쇼핑 상품 분석"
])

client = NaverApiClient(client_id, client_secret)

# 공통 정제 함수
def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', '', raw_html)
    clean = clean.replace("&quot;", '"').replace("&amp;", '&').replace("&lt;", '<').replace("&gt;", '>')
    return clean

# --- 탭 1: 검색 트렌드 추이 ---
with tab_trend:
    st.subheader("📊 네이버 검색어 트렌드 분석")
    with st.spinner("트렌드 데이터를 불러오는 중..."):
        # 단일 키워드 그룹으로 구성하여 전달
        kw_group = [{"groupName": selected_keyword, "keywords": [selected_keyword]}]
        
        @st.cache_data(show_spinner=False)
        def fetch_trend(c_id, c_secret, s_dt, e_dt, kw):
            api = NaverApiClient(c_id, c_secret)
            return api.get_search_trend(
                start_date=s_dt.strftime("%Y-%m-%d"),
                end_date=e_dt.strftime("%Y-%m-%d"),
                time_unit="date",
                keyword_groups=kw
            )
            
        trend_response = fetch_trend(client_id, client_secret, start_date, end_date, kw_group)
        
    if trend_response and "results" in trend_response and trend_response["results"]:
        result_data = trend_response["results"][0]["data"]
        if result_data:
            df_trend = pd.DataFrame(result_data)
            df_trend["period"] = pd.to_datetime(df_trend["period"])
            
            fig = px.line(
                df_trend,
                x="period",
                y="ratio",
                title=f"'{selected_keyword}' 검색 트렌드 추이 (기간 내 상대 수치)",
                labels={"ratio": "검색 상대지수 (최대 100)", "period": "기간"},
                template="plotly_white",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 요약 지표
            max_ratio = df_trend["ratio"].max()
            max_date = df_trend.loc[df_trend["ratio"].idxmax(), "period"].strftime("%Y-%m-%d")
            avg_ratio = df_trend["ratio"].mean()
            
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("최고 검색 관심도 지수", f"{max_ratio:.1f} ({max_date})")
            col_m2.metric("평균 검색 관심도 지수", f"{avg_ratio:.1f}")
        else:
            st.info("해당 기간 동안의 트렌드 데이터가 없습니다.")
    else:
        st.error("트렌드 데이터를 로드할 수 없거나 API 설정이 올바르지 않습니다.")

# --- 탭 2: 블로그 리뷰 분석 ---
with tab_blog:
    st.subheader("📝 블로그 반응 분석")
    with st.spinner("블로그 포스트 수집 중..."):
        @st.cache_data(show_spinner=False)
        def fetch_blog(c_id, c_secret, query):
            api = NaverApiClient(c_id, c_secret)
            return api.search_blog(query, display=30, sort="sim")
            
        blog_response = fetch_blog(client_id, client_secret, selected_keyword)
        
    if blog_response and "items" in blog_response and blog_response["items"]:
        blog_items = blog_response["items"]
        records = []
        for item in blog_items:
            try:
                p_date = pd.to_datetime(item["postdate"], format="%Y%m%d").strftime("%Y-%m-%d")
            except:
                p_date = item["postdate"]
            records.append({
                "작성일": p_date,
                "제목": clean_html(item["title"]),
                "요약": clean_html(item["description"]),
                "블로그명": item["bloggername"],
                "링크": item["link"]
            })
        df_blog = pd.DataFrame(records)
        
        # 간단한 텍스트 단어 분석
        combined_text = " ".join(df_blog["제목"] + " " + df_blog["요약"])
        words = re.findall(r'[ㄱ-ㅎㅏ-ㅣ가-힣]+', combined_text)
        stopwords = {'을', '를', '이', '가', '은', '는', '에', '에서', '로', '으로', '과', '와', '하고', '의', '입니다', '있는', '하는', '한다', '한', '할', '수', '것', '그', '때', '더', '등등'}
        filtered_words = [w for w in words if len(w) > 1 and w not in stopwords]
        word_counts = Counter(filtered_words).most_common(10)
        
        col_b1, col_b2 = st.columns([1, 2])
        with col_b1:
            st.markdown("**주요 등장 단어**")
            if word_counts:
                word_df = pd.DataFrame(word_counts, columns=["단어", "빈도"])
                fig_b = px.bar(word_df, x="빈도", y="단어", orientation="h", template="plotly_white", color="빈도")
                fig_b.update_layout(yaxis={'categoryorder': 'total ascending'}, height=300)
                st.plotly_chart(fig_b, use_container_width=True)
            else:
                st.caption("충분한 단어가 추출되지 않았습니다.")
        with col_b2:
            st.markdown("**최신 주요 블로그 목록**")
            st.dataframe(
                df_blog,
                column_config={
                    "작성일": st.column_config.TextColumn("작성일", width="small"),
                    "제목": st.column_config.TextColumn("제목", width="medium"),
                    "요약": st.column_config.TextColumn("본문 요약", width="large"),
                    "블로그명": st.column_config.TextColumn("블로그", width="small"),
                    "링크": st.column_config.LinkColumn("링크", width="small")
                },
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("블로그 검색 결과가 없습니다.")

# --- 탭 3: 카페 커뮤니티 반응 ---
with tab_cafe:
    st.subheader("💬 카페 커뮤니티 반응 분석")
    with st.spinner("카페 포스트 수집 중..."):
        @st.cache_data(show_spinner=False)
        def fetch_cafe(c_id, c_secret, query):
            api = NaverApiClient(c_id, c_secret)
            return api.search_cafe(query, display=30, sort="sim")
            
        cafe_response = fetch_cafe(client_id, client_secret, selected_keyword)
        
    if cafe_response and "items" in cafe_response and cafe_response["items"]:
        cafe_items = cafe_response["items"]
        records = []
        for item in cafe_items:
            records.append({
                "제목": clean_html(item["title"]),
                "요약": clean_html(item["description"]),
                "카페명": item["cafename"],
                "링크": item["link"]
            })
        df_cafe = pd.DataFrame(records)
        
        st.markdown("**카페글 반응 목록**")
        st.dataframe(
            df_cafe,
            column_config={
                "제목": st.column_config.TextColumn("제목", width="medium"),
                "요약": st.column_config.TextColumn("본문 요약", width="large"),
                "카페명": st.column_config.TextColumn("카페 이름", width="small"),
                "링크": st.column_config.LinkColumn("링크", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("카페 검색 결과가 없습니다.")

# --- 탭 4: 실시간 뉴스 동향 ---
with tab_news:
    st.subheader("📰 실시간 뉴스 동향")
    with st.spinner("뉴스 데이터 수집 중..."):
        @st.cache_data(show_spinner=False)
        def fetch_news(c_id, c_secret, query):
            api = NaverApiClient(c_id, c_secret)
            return api.search_news(query, display=30, sort="sim")
            
        news_response = fetch_news(client_id, client_secret, selected_keyword)
        
    if news_response and "items" in news_response and news_response["items"]:
        news_items = news_response["items"]
        records = []
        for item in news_items:
            # 날짜 정제
            raw_date = item["pubDate"]
            try:
                p_date = pd.to_datetime(raw_date).strftime("%Y-%m-%d %H:%M")
            except:
                p_date = raw_date
            records.append({
                "발행시각": p_date,
                "제목": clean_html(item["title"]),
                "요약": clean_html(item["description"]),
                "링크": item["link"]
            })
        df_news = pd.DataFrame(records)
        
        st.markdown("**관련 주요 뉴스**")
        st.dataframe(
            df_news,
            column_config={
                "발행시각": st.column_config.TextColumn("발행시각", width="small"),
                "제목": st.column_config.TextColumn("제목", width="medium"),
                "요약": st.column_config.TextColumn("기사 요약", width="large"),
                "링크": st.column_config.LinkColumn("기사 링크", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("뉴스 검색 결과가 없습니다.")

# --- 탭 5: 쇼핑 상품 분석 ---
with tab_shop:
    st.subheader("🛒 쇼핑 상품 분석")
    with st.spinner("쇼핑 상품 데이터 수집 중..."):
        @st.cache_data(show_spinner=False)
        def fetch_shop(c_id, c_secret, query):
            api = NaverApiClient(c_id, c_secret)
            return api.search_shop(query, display=30, sort="sim")
            
        shop_response = fetch_shop(client_id, client_secret, selected_keyword)
        
    if shop_response and "items" in shop_response and shop_response["items"]:
        shop_items = shop_response["items"]
        records = []
        for item in shop_items:
            records.append({
                "상품명": clean_html(item["title"]),
                "최저가(원)": int(item["lprice"]) if item["lprice"].isdigit() else 0,
                "브랜드": item.get("brand", ""),
                "제조사": item.get("maker", ""),
                "쇼핑몰": item["mallName"],
                "링크": item["link"]
            })
        df_shop = pd.DataFrame(records)
        
        col_s1, col_s2 = st.columns([1, 2])
        
        with col_s1:
            st.markdown("**평균 가격 정보**")
            valid_prices = df_shop[df_shop["최저가(원)"] > 0]
            if not valid_prices.empty:
                avg_price = valid_prices["최저가(원)"].mean()
                min_price = valid_prices["최저가(원)"].min()
                max_price = valid_prices["최저가(원)"].max()
                
                st.metric("수집 상품 평균가", f"{int(avg_price):,} 원")
                st.metric("수집 상품 최저가", f"{int(min_price):,} 원")
                st.metric("수집 상품 최고가", f"{int(max_price):,} 원")
            else:
                st.caption("가격 정보를 분석할 수 없습니다.")
                
        with col_s2:
            st.markdown("**인기 쇼핑몰 비중 (Top 5)**")
            mall_counts = df_shop["쇼핑몰"].value_counts().reset_index()
            mall_counts.columns = ["쇼핑몰", "상품수"]
            fig_s = px.pie(mall_counts.head(5), values="상품수", names="쇼핑몰", template="plotly_white", hole=0.3)
            fig_s.update_layout(height=250)
            st.plotly_chart(fig_s, use_container_width=True)
            
        st.markdown("**추천 상품 목록**")
        st.dataframe(
            df_shop,
            column_config={
                "상품명": st.column_config.TextColumn("상품명", width="medium"),
                "최저가(원)": st.column_config.NumberColumn("최저가(원)", format="%d 원", width="small"),
                "브랜드": st.column_config.TextColumn("브랜드", width="small"),
                "쇼핑몰": st.column_config.TextColumn("쇼핑몰", width="small"),
                "링크": st.column_config.LinkColumn("구매 링크", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("쇼핑 상품 검색 결과가 없습니다.")
