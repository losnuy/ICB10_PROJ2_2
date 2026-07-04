"""
네이버 뉴스 검색 API 데이터를 수집하여 언론사별 배포 도메인 점유율(Pie Chart),
일자별 보도량 추이(시계열), 그리고 뉴스 제목 및 요약 속 핵심 단어 빈도를 분석하는 페이지입니다.
"""
# -*- coding: utf-8 -*-
import os
import re
from collections import Counter
from urllib.parse import urlparse
import pandas as pd
import plotly.express as px
import streamlit as st
from api_client import NaverApiClient

st.title("📰 뉴스 검색 데이터 분석")

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

# 2. 뉴스 검색 설정 UI
st.markdown("### ⚙️ 뉴스 검색 설정")
col1, col2, col3 = st.columns(3)

with col1:
    selected_keyword = st.selectbox(
        "분석할 검색어 선택",
        options=keywords,
        index=0,
        key="news_kw_select",
        help="사이드바에 입력한 검색어 중 뉴스 분석 대상을 선택하세요."
    )

with col2:
    display_num = st.slider(
        "수집 뉴스 기사 수",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
        key="news_display_slider",
        help="가져올 뉴스 기사의 최대 개수입니다. (최대 100개)"
    )

with col3:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["sim", "date"],
        format_func=lambda x: {"sim": "정확도순 (유사도)", "date": "최신 뉴스순"}[x],
        index=0,
        key="news_sort_select",
        help="검색 결과 정렬 방식입니다."
    )

# 3. API 호출
client = NaverApiClient(client_id, client_secret)

with st.spinner(f"'{selected_keyword}' 관련 뉴스 데이터를 수집 중입니다..."):
    @st.cache_data(show_spinner=False)
    def fetch_news_search(c_id, c_secret, query, display, sort):
        api = NaverApiClient(c_id, c_secret)
        return api.search_news(query, display=display, sort=sort)

    response_data = fetch_news_search(
        client_id, client_secret, selected_keyword, display_num, sort_option
    )

# 4. 데이터 가공
if response_data and "items" in response_data:
    items = response_data["items"]
    
    if items:
        records = []
        for item in items:
            # HTML 태그 제거 및 텍스트 엔티티 정제
            clean_title = re.sub(r'<[^>]+>', '', item["title"])
            clean_title = clean_title.replace("&quot;", '"').replace("&amp;", '&').replace("&lt;", '<').replace("&gt;", '>')
            
            clean_desc = re.sub(r'<[^>]+>', '', item["description"])
            clean_desc = clean_desc.replace("&quot;", '"').replace("&amp;", '&').replace("&lt;", '<').replace("&gt;", '>')
            
            # 발간 일자 파싱 (예: Mon, 24 Aug 2020 16:30:00 +0900)
            raw_date = item["pubDate"]
            try:
                date_obj = pd.to_datetime(raw_date)
            except Exception:
                date_obj = pd.NaT
                
            # 언론사 도메인 추출 (originallink가 있을 경우 도메인을 분석하여 언론사 분류 보조)
            orig_link = item["originallink"]
            domain = ""
            if orig_link:
                try:
                    parsed_url = urlparse(orig_link)
                    domain = parsed_url.netloc.replace("www.", "")
                except Exception:
                    domain = "기타"
            else:
                domain = "네이버뉴스 직접 제공"
                
            records.append({
                "보도일": date_obj,
                "제목": clean_title,
                "요약": clean_desc,
                "언론사 도메인": domain if domain else "기타",
                "원문 링크": orig_link,
                "네이버 뉴스 링크": item["link"]
            })
            
        df = pd.DataFrame(records)
        
        # 5. 시계열 분석 (뉴스 발행 트렌드)
        st.markdown("### 📅 뉴스 보도량 추이")
        df_valid_date = df[df["보도일"].notna()]
        
        if not df_valid_date.empty:
            # 보도 기사를 날짜 단위(일자별)로 묶어 건수 산출
            df_valid_date["보도일자"] = df_valid_date["보도일"].dt.date
            date_counts = df_valid_date["보도일자"].value_counts().reset_index()
            date_counts.columns = ["보도일자", "보도건수"]
            date_counts = date_counts.sort_values("보도일자")
            
            fig_date = px.line(
                date_counts,
                x="보도일자",
                y="보도건수",
                title="일자별 뉴스 보도량 추이",
                labels={"보도건수": "뉴스 기사 수", "보도일자": "날짜"},
                template="plotly_white",
                markers=True
            )
            st.plotly_chart(fig_date, use_container_width=True)
        else:
            st.info("보도시간 데이터를 분석할 수 없습니다.")
            
        # 6. 언론사 및 텍스트 단어 분석
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("#### 🏆 주요 언론사 도메인 점유율 (Top 10)")
            domain_counts = df["언론사 도메인"].value_counts().reset_index()
            domain_counts.columns = ["도메인", "기사수"]
            
            fig_domain = px.pie(
                domain_counts.head(10),
                values="기사수",
                names="도메인",
                title="상위 10개 보도 도메인 비율",
                template="plotly_white",
                hole=0.4
            )
            fig_domain.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_domain, use_container_width=True)
            
        with col_chart2:
            st.markdown("#### 🔤 뉴스 제목/본문 단어 빈도 분석 (Top 15)")
            combined_text = " ".join(df["제목"] + " " + df["요약"])
            words = re.findall(r'[ㄱ-ㅎㅏ-ㅣ가-힣]+', combined_text)
            
            stopwords = {
                '그리고', '하지만', '그러나', '그래서', '을', '를', '이', '가', '은', '는', 
                '에', '에서', '로', '으로', '과', '와', '하고', '하고있는', '등', '및', '의', 
                '입니다', '있는', '하는', '한다', '한', '할', '수', '것', '그', '이것', '저것',
                '때', '더', '등등', '통해', '대한', '위해', '많은', '가장', '매우', '뉴스', '기사', '기자'
            }
            filtered_words = [w for w in words if len(w) > 1 and w not in stopwords]
            word_counts = Counter(filtered_words).most_common(15)
            
            if word_counts:
                word_df = pd.DataFrame(word_counts, columns=["단어", "빈도수"])
                fig_word = px.bar(
                    word_df,
                    x="빈도수",
                    y="단어",
                    orientation="h",
                    title="뉴스 주요 핵심 키워드",
                    labels={"빈도수": "보도 횟수", "단어": "핵심 키워드"},
                    template="plotly_white",
                    color="빈도수",
                    color_continuous_scale="Temps"
                )
                fig_word.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_word, use_container_width=True)
            else:
                st.caption("텍스트 분석 결과가 충분치 않습니다.")
                
        # 7. 기사 리스트
        st.markdown("### 📋 수집 뉴스 상세 목록")
        df_display = df.copy()
        if not df_display["보도일"].isna().all():
            df_display["보도일"] = df_display["보도일"].dt.strftime("%Y-%m-%d %H:%M")
            
        st.dataframe(
            df_display,
            column_config={
                "보도일": st.column_config.TextColumn("보도 일시", width="small"),
                "제목": st.column_config.TextColumn("뉴스 제목", width="medium"),
                "요약": st.column_config.TextColumn("요약 내용", width="large"),
                "언론사 도메인": st.column_config.TextColumn("언론사 도메인", width="small"),
                "원문 링크": st.column_config.LinkColumn("원문 링크", width="small"),
                "네이버 뉴스 링크": st.column_config.LinkColumn("네이버 뉴스 링크", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 다운로드
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 뉴스 수집 데이터 CSV 다운로드",
            data=csv,
            file_name=f"naver_news_{selected_keyword}.csv",
            mime="text/csv"
        )
        
    else:
        st.warning("⚠️ 검색 결과가 존재하지 않습니다.")
else:
    st.info("데이터를 로드하지 못했습니다. API 설정을 확인하세요.")
