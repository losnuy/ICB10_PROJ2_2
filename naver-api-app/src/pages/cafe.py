"""
네이버 카페글 검색 API 데이터를 수집하여 주요 정보가 작성된 카페명 분포(Top 카페)와
본문 내 빈번히 사용된 핵심 어휘(단어 빈도)를 분석하고 시각화하는 페이지입니다.
"""
# -*- coding: utf-8 -*-
import os
import re
from collections import Counter
import pandas as pd
import plotly.express as px
import streamlit as st
from api_client import NaverApiClient

st.title("💬 카페글 검색 데이터 분석")

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

# 2. 카페 검색 설정 UI
st.markdown("### ⚙️ 카페 검색 설정")
col1, col2, col3 = st.columns(3)

with col1:
    selected_keyword = st.selectbox(
        "분석할 검색어 선택",
        options=keywords,
        index=0,
        key="cafe_kw_select",
        help="사이드바에 입력한 검색어 중 카페 분석 대상을 선택하세요."
    )

with col2:
    display_num = st.slider(
        "수집 글 수",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
        key="cafe_display_slider",
        help="가져올 카페글의 최대 개수입니다. (최대 100개)"
    )

with col3:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["sim", "date"],
        format_func=lambda x: {"sim": "정확도순 (유사도)", "date": "최신 작성일순"}[x],
        index=0,
        key="cafe_sort_select",
        help="검색 결과 정렬 방식입니다."
    )

# 3. API 호출
client = NaverApiClient(client_id, client_secret)

with st.spinner(f"'{selected_keyword}' 관련 카페글 데이터를 수집 중입니다..."):
    @st.cache_data(show_spinner=False)
    def fetch_cafe_search(c_id, c_secret, query, display, sort):
        api = NaverApiClient(c_id, c_secret)
        return api.search_cafe(query, display=display, sort=sort)

    response_data = fetch_cafe_search(
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
            
            records.append({
                "제목": clean_title,
                "요약": clean_desc,
                "카페명": item["cafename"],
                "글 링크": item["link"],
                "카페 주소": item["cafeurl"]
            })
            
        df = pd.DataFrame(records)
        
        # 5. 시각화 (Plotly)
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("#### 🏆 다빈도 활성화 카페 (Top 10)")
            cafe_counts = df["카페명"].value_counts().reset_index()
            cafe_counts.columns = ["카페명", "작성글수"]
            
            fig_cafe = px.bar(
                cafe_counts.head(10),
                x="작성글수",
                y="카페명",
                orientation="h",
                title="글이 가장 많이 등록된 카페 순위",
                labels={"작성글수": "등록 건수", "카페명": "카페 이름"},
                template="plotly_white"
            )
            fig_cafe.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_cafe, use_container_width=True)
            
        with col_chart2:
            st.markdown("#### 🔤 카페글 단어 빈도 분석 (Top 15)")
            combined_text = " ".join(df["제목"] + " " + df["요약"])
            words = re.findall(r'[ㄱ-ㅎㅏ-ㅣ가-힣]+', combined_text)
            
            stopwords = {
                '그리고', '하지만', '그러나', '그래서', '을', '를', '이', '가', '은', '는', 
                '에', '에서', '로', '으로', '과', '와', '하고', '하고있는', '등', '및', '의', 
                '입니다', '있는', '하는', '한다', '한', '할', '수', '것', '그', '이것', '저것',
                '때', '더', '등등', '통해', '대한', '위해', '많은', '가장', '매우', '카페', '글'
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
                    color_continuous_scale="Cividis"
                )
                fig_word.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_word, use_container_width=True)
            else:
                st.caption("텍스트 분석 결과가 충분치 않습니다.")
                
        # 6. 결과 목록 테이블
        st.markdown("### 📋 수집 카페글 상세 목록")
        st.dataframe(
            df,
            column_config={
                "카페명": st.column_config.TextColumn("카페 이름", width="small"),
                "제목": st.column_config.TextColumn("제목", width="medium"),
                "요약": st.column_config.TextColumn("본문 요약", width="large"),
                "글 링크": st.column_config.LinkColumn("글 링크", width="small"),
                "카페 주소": st.column_config.LinkColumn("카페 주소", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 다운로드
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 카페글 수집 데이터 CSV 다운로드",
            data=csv,
            file_name=f"naver_cafe_{selected_keyword}.csv",
            mime="text/csv"
        )
        
    else:
        st.warning("⚠️ 검색 결과가 존재하지 않습니다.")
else:
    st.info("데이터를 로드하지 못했습니다. API 설정을 확인하세요.")
