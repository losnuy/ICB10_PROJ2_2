"""
네이버 API 대시보드 메인 엔트리포인트 파일입니다.
모듈을 import 할 때 자동 실행되지 않도록 모든 로직을 `main()` 함수 안에 넣고,
`if __name__ == '__main__':` 가드에서 `main()` 을 호출하도록 구조를 변경합니다.
"""

# -*- coding: utf-8 -*-
import os
import datetime
import streamlit as st

def load_env(env_path):
    """외부 라이브러리 없이 .env 파일을 파싱하여 환경 변수에 등록합니다."""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                os.environ[key] = val

def main():
    # 페이지 설정
    st.set_page_config(
        page_title="네이버 API 종합 분석 대시보드",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 기본 디렉터리 경로 계산
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pages_dir = os.path.join(current_dir, "pages")

    # .env 로드 (여러 후보 경로 탐색)
    env_candidates = [
        os.path.join(os.path.dirname(current_dir), ".env"),
        os.path.join(current_dir, ".env"),
        os.path.abspath(".env"),
        os.path.join(os.getcwd(), "naver-api-app", ".env")
    ]
    for path in env_candidates:
        if os.path.exists(path):
            load_env(path)
            break

    # 사이드바 타이틀
    st.sidebar.title("🔑 네이버 API 설정")

    # 환경 변수 및 세션 상태에서 API Key 로드
    env_client_id = os.environ.get("NAVER_CLIENT_ID", "")
    env_client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
    loaded_from_secrets = False
    if not env_client_id or not env_client_secret:
        try:
            if "NAVER_CLIENT_ID" in st.secrets:
                env_client_id = st.secrets["NAVER_CLIENT_ID"]
            if "NAVER_CLIENT_SECRET" in st.secrets:
                env_client_secret = st.secrets["NAVER_CLIENT_SECRET"]
            if env_client_id and env_client_secret:
                loaded_from_secrets = True
        except Exception:
            pass
    if "client_id" not in st.session_state:
        st.session_state["client_id"] = env_client_id
    if "client_secret" not in st.session_state:
        st.session_state["client_secret"] = env_client_secret

    # 1. API Key UI 구성
    if env_client_id and env_client_secret:
        if loaded_from_secrets:
            st.sidebar.success("✅ Streamlit Secrets에서 API 설정을 자동으로 로드했습니다.")
        else:
            st.sidebar.success("✅ `.env` 파일에서 API 설정을 자동으로 로드했습니다.")
        with st.sidebar.expander("🔑 API 키 수동 변경"):
            client_id_input = st.text_input(
                "Client ID",
                value=st.session_state["client_id"],
                type="password",
                help="네이버 개발자 센터에서 발급받은 Client ID를 입력하세요."
            )
            client_secret_input = st.text_input(
                "Client Secret",
                value=st.session_state["client_secret"],
                type="password",
                help="네이버 개발자 센터에서 발급받은 Client Secret을 입력하세요."
            )
            if client_id_input != st.session_state["client_id"] or client_secret_input != st.session_state["client_secret"]:
                st.session_state["client_id"] = client_id_input
                st.session_state["client_secret"] = client_secret_input
                st.rerun()
    else:
        st.sidebar.warning("⚠️ API 설정이 자동 로드되지 않았습니다. 수동으로 입력해 주세요.")
        client_id_input = st.sidebar.text_input(
            "Client ID",
            value=st.session_state.get("client_id", ""),
            type="password",
            help="네이버 개발자 센터에서 발급받은 Client ID를 입력하세요."
        )
        client_secret_input = st.sidebar.text_input(
            "Client Secret",
            value=st.session_state.get("client_secret", ""),
            type="password",
            help="네이버 개발자 센터에서 발급받은 Client Secret을 입력하세요."
        )
        if client_id_input != st.session_state.get("client_id", "") or client_secret_input != st.session_state.get("client_secret", ""):
            st.session_state["client_id"] = client_id_input
            st.session_state["client_secret"] = client_secret_input
            st.rerun()

    client_id = st.session_state.get("client_id", "")
    client_secret = st.session_state.get("client_secret", "")

    # 2. 공통 검색 파라미터 설정
    st.sidebar.markdown("---")
    st.sidebar.title("🔍 공통 분석 파라미터")
    keywords_input = st.sidebar.text_input(
        "검색어 (쉼표 ',' 로 구분)",
        value=st.session_state.get("keywords_raw", "캠핑,글램핑,차박"),
        help="분석할 키워드들을 쉼표로 구분하여 입력하세요. (최대 5개 권장)"
    )
    st.session_state["keywords_raw"] = keywords_input
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    st.session_state["keywords"] = keywords
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=90)
    start_date = st.sidebar.date_input(
        "시작일",
        value=st.session_state.get("start_date", default_start),
        max_value=today,
        help="조회 시작일을 선택하세요."
    )
    end_date = st.sidebar.date_input(
        "종료일",
        value=st.session_state.get("end_date", today),
        min_value=start_date,
        max_value=today,
        help="조회 종료일을 선택하세요."
    )
    st.session_state["start_date"] = start_date
    st.session_state["end_date"] = end_date
    if not client_id or not client_secret:
        st.sidebar.warning("⚠️ Client ID와 Secret을 입력해야 네이버 API 데이터를 로드할 수 있습니다.")

    # 3. 멀티 페이지 구성
    integrated_page = st.Page(os.path.join(pages_dir, "integrated_analysis.py"), title="🔍 통합 키워드 상세 분석", icon="🔎")
    trend_page = st.Page(os.path.join(pages_dir, "trend.py"), title="📈 통합 검색어 트렌드", icon="📊")
    shopping_trend_page = st.Page(os.path.join(pages_dir, "shopping_trend.py"), title="🛍️ 쇼핑 검색어 트렌드", icon="🛒")
    shopping_search_page = st.Page(os.path.join(pages_dir, "shopping_search.py"), title="📦 쇼핑 상품 분석", icon="🛒")
    blog_page = st.Page(os.path.join(pages_dir, "blog.py"), title="📝 블로그 검색 분석", icon="✍️")
    cafe_page = st.Page(os.path.join(pages_dir, "cafe.py"), title="💬 카페글 검색 분석", icon="☕")
    news_page = st.Page(os.path.join(pages_dir, "news.py"), title="📰 뉴스 검색 분석", icon="🗞️")
    pages_dict = {
        "종합 분석": [integrated_page],
        "트렌드 분석": [trend_page, shopping_trend_page],
        "개별 검색 분석": [shopping_search_page, blog_page, cafe_page, news_page]
    }
    pg = st.navigation(pages_dict)
    pg.run()

if __name__ == "__main__":
    main()
