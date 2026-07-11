"""
서울시 생활인구 대시보드를 위한 원본 Parquet 파일 로드 및 SQLite DB 집계 연동 하이브리드 캐시 모듈입니다.
주요 기능:
- load_raw_parquet: Parquet 원본 데이터셋 캐시 적재 및 기본 파생변수 생성
- load_db_table: SQLite DB의 사전 연산 집계 테이블 로드
- load_map_data_from_db: 지도 시각화용 시군구/읍면동 시간대별 평균 인구 쿼리
- get_basic_info: 원본 데이터셋 품질 진단 및 타입 명세 실시간 제공
- calculate_advanced_stats: 원본 생활인구수 컬럼 기반 기술 통계 및 IQR 이상치 계산
- load_geojson / load_code_mapping: 지리 경계 데이터 및 통계청-행안부 코드 바인딩 지원
"""

import os
import urllib.request
import urllib.parse
import json
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
from scipy.stats import skew, kurtosis

# 서울시 25개 자치구 코드 매핑 딕셔너리
DISTRICT_MAP = {
    '11110': '종로구',
    '11140': '중구',
    '11170': '용산구',
    '11200': '성동구',
    '11215': '광진구',
    '11230': '동대문구',
    '11260': '중랑구',
    '11290': '성북구',
    '11305': '강북구',
    '11320': '도봉구',
    '11350': '노원구',
    '11380': '은평구',
    '11410': '서대문구',
    '11440': '마포구',
    '11470': '양천구',
    '11500': '강서구',
    '11530': '구로구',
    '11545': '금천구',
    '11560': '영등포구',
    '11590': '동작구',
    '11620': '관악구',
    '11650': '서초구',
    '11680': '강남구',
    '11710': '송파구',
    '11740': '강동구'
}

@st.cache_data
def load_raw_parquet() -> pd.DataFrame:
    """
    Parquet 원본 데이터셋을 캐시 로드하고,
    자치구 매핑 및 날짜/주말 파생변수를 추가하여 반환합니다.
    """
    parquet_path = os.path.join("seoul-pops", "data", "LOCAL_PEOPLE_DONG_202606_tidy.parquet")
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"원본 Parquet 파일을 찾을 수 없습니다: {parquet_path}")
        
    df = pd.read_parquet(parquet_path)
    
    # 1. 자치구 매핑 생성
    df['행정동코드_str'] = df['행정동코드'].astype(str)
    df['자치구코드'] = df['행정동코드_str'].str[:5]
    df['자치구'] = df['자치구코드'].map(DISTRICT_MAP).fillna('기타').astype('category')
    df.drop(columns=['행정동코드_str', '자치구코드'], inplace=True)
    
    # 2. 날짜포맷 및 주말구분 파생변수 생성
    unique_dates = df['기준일ID'].unique()
    date_series = pd.to_datetime(unique_dates.astype(str), format='%Y%m%d')
    date_to_dayname = {d: dt.strftime('%Y-%m-%d (%a)') for d, dt in zip(unique_dates, date_series)}
    date_to_weekend = {d: '주말' if dt.dayofweek >= 5 else '주중' for d, dt in zip(unique_dates, date_series)}
    
    df['날짜포맷'] = df['기준일ID'].map(date_to_dayname).astype('category')
    df['주말구분'] = df['기준일ID'].map(date_to_weekend).astype('category')
    
    return df

@st.cache_data
def load_db_table(table_name: str) -> pd.DataFrame:
    """
    SQLite 데이터베이스에서 사전 연산된 통계 집계 테이블을 캐시 로드합니다.
    """
    db_path = os.path.join("seoul-pops", "data", "seoul_pops.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"데이터베이스 파일이 존재하지 않습니다: {db_path}")
        
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    
    # 카테고리 데이터타입 자동 복원
    category_cols = ['성별', '연령대', '자치구', '날짜포맷', '주말구분']
    for col in category_cols:
        if col in df.columns:
            df[col] = df[col].astype('category')
            
    return df

@st.cache_data
def load_map_data_from_db(unit: str, hour: int) -> pd.DataFrame:
    """
    지도 시각화용 시간대별 자치구 혹은 행정동 평균 생활인구 데이터를 SQLite DB에서 직접 쿼리하여 반환합니다.
    """
    db_path = os.path.join("seoul-pops", "data", "seoul_pops.db")
    table_name = "hourly_district_pop" if unit == "자치구별 (구별)" else "hourly_dong_pop"
    
    conn = sqlite3.connect(db_path)
    query = f"SELECT * FROM {table_name} WHERE 시간대구분 = ?"
    df = pd.read_sql(query, conn, params=[hour])
    conn.close()
    
    if unit == "자치구별 (구별)":
        df['자치구'] = df['자치구'].astype('category')
    else:
        df['행정동코드'] = df['행정동코드'].astype(str)
        
    return df

@st.cache_data
def load_geojson(unit: str) -> dict:
    """
    지정한 시각화 단위("자치구별 (구별)" 또는 "행정동별 (동별)")에 따라
    southkorea/southkorea-maps 깃허브 저장소의 전국 GeoJSON 파일을 로드하고,
    서울시(코드 '11'로 시작) 행정구역 피처만 필터링하여 반환합니다.
    """
    if unit == "자치구별 (구별)":
        url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_municipalities_geo_simple.json"
    else:
        url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_submunicipalities_geo_simple.json"
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            geojson_data = json.loads(response.read().decode('utf-8'))
            
        # 서울시 피처만 필터링 (code 속성이 '11'로 시작)
        seoul_features = []
        for feature in geojson_data['features']:
            code = feature['properties'].get('code', '')
            if code.startswith('11'):
                seoul_features.append(feature)
                
        geojson_data['features'] = seoul_features
        return geojson_data
    except Exception as e:
        raise RuntimeError(f"GeoJSON 데이터를 다운로드하고 필터링하는 중 오류가 발생했습니다: {e}")

@st.cache_data
def load_code_mapping() -> dict:
    """
    행안부 행정표준코드(8자리)와 통계구역 분류코드(통계청 7자리) 간의 1:1 매핑 딕셔너리를 빌드합니다.
    """
    base_url = "https://raw.githubusercontent.com/raqoon886/Local_HangJeongDong/master/"
    filename = "hangjeongdong_서울특별시.geojson"
    encoded_filename = urllib.parse.quote(filename)
    url = base_url + encoded_filename
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        mapping = {}
        for feature in data['features']:
            props = feature['properties']
            adm_cd = props.get('adm_cd', '')     # 통계청 7자리
            adm_cd2 = props.get('adm_cd2', '')   # 행안부 10자리
            if adm_cd and adm_cd2:
                mapping[str(adm_cd2[:8])] = str(adm_cd)
        return mapping
    except Exception as e:
        raise RuntimeError(f"행정동 코드 매핑 테이블을 다운로드 및 빌드하는 중 오류가 발생했습니다: {e}")

def get_basic_info(df: pd.DataFrame) -> dict:
    """
    원본 데이터프레임의 행/열 수, 중복 데이터 수, 결측치 등을 실시간 진단합니다.
    """
    rows_count, cols_count = df.shape
    duplicates = df.duplicated().sum()
    null_counts = df.isnull().sum().to_dict()
    dtypes_dict = {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
    
    return {
        "rows": rows_count,
        "cols": cols_count,
        "duplicates": duplicates,
        "null_counts": null_counts,
        "dtypes": dtypes_dict
    }

def calculate_advanced_stats(df: pd.DataFrame) -> dict:
    """
    원본 생활인구수 컬럼에 대해 기술통계량 및 IQR 기준 이상치를 실시간 계산합니다.
    """
    series = df['생활인구수'].astype(float)
    
    mean_val = series.mean()
    median_val = series.median()
    mode_val = series.mode()[0] if not series.mode().empty else np.nan
    std_val = series.std()
    cv_val = std_val / mean_val if mean_val != 0 else np.nan
    
    skew_val = skew(series)
    kurt_val = kurtosis(series)
    
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    outliers = series[(series < lower_bound) | (series > upper_bound)]
    outlier_count = len(outliers)
    outlier_ratio = outlier_count / len(series) * 100
    
    return {
        "mean": mean_val,
        "median": median_val,
        "mode": mode_val,
        "std": std_val,
        "cv": cv_val,
        "skewness": skew_val,
        "kurtosis": kurt_val,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "outlier_count": outlier_count,
        "outlier_ratio": outlier_ratio
    }
