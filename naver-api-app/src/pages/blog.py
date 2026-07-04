"""
네이버 블로그 검색 API 데이터를 수집하여 일자별 작성 추이(시계열),
주요 발행 블로거 순위, 그리고 제목 및 요약 내용의 단어 빈도 분석(TF)을 시각화하는 페이지입니다.
"""
# -*- coding: utf-8 -*-
import os
import re
from collections import Counter
import pandas as pd
import plotly.express as px
import streamlit as st
from api_client import NaverApiClient

st.title("📝 블로그 검색 데이터 분석")

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

# 2. 상세 조회 설정 UI
st.markdown("### ⚙️ 블로그 검색 설정")
col1, col2, col3 = st.columns(3)

with col1:
    selected_keyword = st.selectbox(
        "분석할 검색어 선택",
        options=keywords,
        index=0,
        key="blog_kw_select",
        help="사이드바에 입력한 검색어 중 블로그 분석 대상을 선택하세요."
    )

with col2:
    display_num = st.slider(
        "수집 포스트 수",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
        key="blog_display_slider",
        help="가져올 블로그 포스트의 최대 개수입니다. (최대 100개)"
    )

with col3:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["sim", "date"],
        format_func=lambda x: {"sim": "정확도순 (유사도)", "date": "최신 작성일순"}[x],
        index=0,
        key="blog_sort_select",
        help="검색 결과 정렬 방식입니다."
    )

# 3. API 호출
client = NaverApiClient(client_id, client_secret)

with st.spinner(f"'{selected_keyword}' 관련 블로그 데이터를 수집 중입니다..."):
    @st.cache_data(show_spinner=False)
    def fetch_blog_search(c_id, c_secret, query, display, sort):
        api = NaverApiClient(c_id, c_secret)
        return api.search_blog(query, display=display, sort=sort)

    response_data = fetch_blog_search(
        client_id, client_secret, selected_keyword, display_num, sort_option
    )

# 4. 데이터 가공
if response_data and "items" in response_data:
    items = response_data["items"]
    
    if items:
        records = []
        for item in items:
            # HTML 태그 제거 및 엔티티 코드 정제
            clean_title = re.sub(r'<[^>]+>', '', item["title"])
            clean_title = clean_title.replace("&quot;", '"').replace("&amp;", '&').replace("&lt;", '<').replace("&gt;", '>')
            
            clean_desc = re.sub(r'<[^>]+>', '', item["description"])
            clean_desc = clean_desc.replace("&quot;", '"').replace("&amp;", '&').replace("&lt;", '<').replace("&gt;", '>')
            
            # 날짜 변환 (YYYYMMDD -> YYYY-MM-DD)
            raw_date = item["postdate"]
            try:
                date_obj = pd.to_datetime(raw_date, format="%Y%m%d")
            except Exception:
                date_obj = pd.NaT
                
            records.append({
                "작성일": date_obj,
                "제목": clean_title,
                "요약": clean_desc,
                "블로그명": item["bloggername"],
                "포스트 링크": item["link"],
                "블로그 주소": item["bloggerlink"]
            })
            
        df = pd.DataFrame(records)
        
        # 5. 시계열 분석 (작성 추이)
        st.markdown("### 📅 블로그 포스트 작성 추이")
        df_valid_date = df[df["작성일"].notna()]
        
        if not df_valid_date.empty:
            date_counts = df_valid_date["작성일"].value_counts().reset_index()
            date_counts.columns = ["작성일", "작성건수"]
            date_counts = date_counts.sort_values("작성일")
            
            fig_date = px.line(
                date_counts,
                x="작성일",
                y="작성건수",
                title="날짜별 블로그 작성 포스팅 수 트렌드",
                labels={"작성건수": "발행 건수", "작성일": "날짜"},
                template="plotly_white",
                markers=True
            )
            st.plotly_chart(fig_date, use_container_width=True)
        else:
            st.info("작성일 데이터를 파싱할 수 없습니다.")
            
        # 6. 블로거 및 텍스트 키워드 분석
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("#### 🏆 다빈도 발행 블로그 (Top 10)")
            blog_counts = df["블로그명"].value_counts().reset_index()
            blog_counts.columns = ["블로그명", "발행수"]
            
            fig_blog = px.bar(
                blog_counts.head(10),
                x="발행수",
                y="블로그명",
                orientation="h",
                title="가장 많이 발행한 블로그 순위",
                labels={"발행수": "글 개수", "블로그명": "블로그 이름"},
                template="plotly_white"
            )
            fig_blog.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_blog, use_container_width=True)
            
        with col_chart2:
            st.markdown("#### 🔤 본문 단어 빈도 분석 (Top 15)")
            # 제목과 요약 결합 텍스트 분석
            combined_text = " ".join(df["제목"] + " " + df["요약"])
            words = re.findall(r'[ㄱ-ㅎㅏ-ㅣ가-힣]+', combined_text)
            
            # 간단한 한국어 조사 및 불용어 제거
            stopwords = {
                '그리고', '하지만', '그러나', '그래서', '을', '를', '이', '가', '은', '는', 
                '에', '에서', '로', '으로', '과', '와', '하고', '하고있는', '등', '및', '의', 
                '입니다', '있는', '하는', '한다', '한', '할', '수', '것', '그', '이것', '저것',
                '때', '더', '등등', '통해', '대한', '위해', '대한', '많은', '가장', '매우', '요'
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
                    title="자주 등장한 주요 키워드",
                    labels={"빈도수": "등장 횟수", "단어": "핵심 키워드"},
                    template="plotly_white",
                    color="빈도수",
                    color_continuous_scale="Viridis"
                )
                fig_word.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_word, use_container_width=True)
            else:
                st.caption("충분한 한국어 단어를 추출하지 못했습니다.")
                
        # 7. 검색 결과 상세 테이블 표출
        st.markdown("### 📋 수집 블로그 상세 목록")
        df_display = df.copy()
        # 시각용 날짜 포맷팅
        df_display["작성일"] = df_display["작성일"].dt.strftime("%Y-%m-%d")
        
        st.dataframe(
            df_display,
            column_config={
                "작성일": st.column_config.TextColumn("작성일", width="small"),
                "제목": st.column_config.TextColumn("제목", width="medium"),
                "요약": st.column_config.TextColumn("본문 요약", width="large"),
                "블로그명": st.column_config.TextColumn("블로그 이름", width="small"),
                "포스트 링크": st.column_config.LinkColumn("포스트 링크", width="small"),
                "블로그 주소": st.column_config.LinkColumn("블로그 주소", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 다운로드
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 블로그 수집 데이터 CSV 다운로드",
            data=csv,
            file_name=f"naver_blog_{selected_keyword}.csv",
            mime="text/csv"
        )
        
    else:
        st.warning("⚠️ 검색 결과가 존재하지 않습니다.")
else:
    st.info("데이터를 로드하지 못했습니다. API 키 정보가 맞는지 다시 확인해 주세요.")
