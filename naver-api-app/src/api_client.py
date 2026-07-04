"""
네이버 오픈 API(검색, 데이터랩 트렌드, 쇼핑인사이트 등)와의 통신을 전담하며
API 요청 및 예외 처리, 캐싱 처리를 지원하는 공통 API 클라이언트 모듈입니다.
"""
# -*- coding: utf-8 -*-
import requests
import json
import streamlit as st

class NaverApiClient:
    """
    네이버 오픈 API 호출을 관리하는 클라이언트 클래스
    """
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json"
        }

    def _post(self, url: str, payload: dict) -> dict:
        """
        POST 요청 공통 헬퍼 함수
        """
        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(payload), timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            st.error(f"네트워크 연결에 실패했습니다: {e}")
            return {}

    def _get(self, url: str, params: dict) -> dict:
        """
        GET 요청 공통 헬퍼 함수
        """
        # GET 요청의 경우 Content-Type 헤더가 없거나 다를 수 있으므로 별도 복사하여 사용
        get_headers = self.headers.copy()
        if "Content-Type" in get_headers:
            del get_headers["Content-Type"]
            
        try:
            response = requests.get(url, headers=get_headers, params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            st.error(f"네트워크 연결에 실패했습니다: {e}")
            return {}

    def _handle_response(self, response: requests.Response) -> dict:
        """
        응답 코드를 확인하고 에러 발생 시 알맞은 한국어 메시지를 출력합니다.
        """
        if response.status_code == 200:
            return response.json()
        
        status = response.status_code
        try:
            err_data = response.json()
            err_msg = err_data.get("errorMessage", response.text)
        except Exception:
            err_msg = response.text

        if status == 400:
            msg = f"잘못된 요청 파라미터입니다. (400 Bad Request)\n상세 내용: {err_msg}"
        elif status == 401:
            msg = "API 인증에 실패했습니다. 사이드바에 입력된 Client ID 및 Client Secret이 유효한지 확인해 주세요. (401 Unauthorized)"
        elif status == 403:
            msg = "API 권한이 없습니다. 네이버 개발자 센터에서 해당 API(데이터랩, 검색 등)가 애플리케이션 사용 API로 활성화되어 있는지 확인해 주세요. (403 Forbidden)"
        elif status == 429:
            msg = "API 일일 호출 한도를 초과했습니다. 내일 다시 시도해 주세요. (429 Too Many Requests)"
        elif status == 500:
            msg = f"네이버 서버 내부 에러가 발생했습니다. 잠시 후 다시 시도해 주세요. (500 Internal Server Error)\n상세 내용: {err_msg}"
        else:
            msg = f"에러가 발생했습니다. (HTTP {status})\n상세 내용: {err_msg}"
            
        st.error(msg)
        print(f"[API ERROR] {msg}")
        return {}

    def get_search_trend(self, start_date: str, end_date: str, time_unit: str, keyword_groups: list, device: str = None, gender: str = None, ages: list = None) -> dict:
        """
        통합 검색어 트렌드 조회
        """
        url = "https://openapi.naver.com/v1/datalab/search"
        payload = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": keyword_groups
        }
        if device:
            payload["device"] = device
        if gender:
            payload["gender"] = gender
        if ages:
            payload["ages"] = ages
            
        return self._post(url, payload)

    def get_shopping_trend(self, start_date: str, end_date: str, time_unit: str, category_id: str, keywords: list, device: str = None, gender: str = None, ages: list = None) -> dict:
        """
        쇼핑인사이트 카테고리 내 키워드 트렌드 조회
        """
        url = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
        payload = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": category_id,
            "keyword": keywords
        }
        if device:
            payload["device"] = device
        if gender:
            payload["gender"] = gender
        if ages:
            payload["ages"] = ages
            
        return self._post(url, payload)

    def search_shop(self, query: str, display: int = 20, start: int = 1, sort: str = "sim") -> dict:
        """
        쇼핑 검색결과 조회
        """
        url = "https://openapi.naver.com/v1/search/shop.json"
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }
        return self._get(url, params)

    def search_blog(self, query: str, display: int = 20, start: int = 1, sort: str = "sim") -> dict:
        """
        블로그 검색결과 조회
        """
        url = "https://openapi.naver.com/v1/search/blog.json"
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }
        return self._get(url, params)

    def search_cafe(self, query: str, display: int = 20, start: int = 1, sort: str = "sim") -> dict:
        """
        카페글 검색결과 조회
        """
        url = "https://openapi.naver.com/v1/search/cafearticle.json"
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }
        return self._get(url, params)

    def search_news(self, query: str, display: int = 20, start: int = 1, sort: str = "sim") -> dict:
        """
        뉴스 검색결과 조회
        """
        url = "https://openapi.naver.com/v1/search/news.json"
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }
        return self._get(url, params)
