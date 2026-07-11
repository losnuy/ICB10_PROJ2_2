"""
서울시 생활인구 대시보드의 성능 개선을 위해 Parquet 데이터를 기반으로
주요 통계 집계 테이블을 미리 생성하여 SQLite 데이터베이스에 이관 및 인덱싱하는 스크립트입니다.
"""

import os
import sys
import sqlite3
import time
import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis

# 터미널 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

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

def main():
    parquet_path = os.path.join("seoul-pops", "data", "LOCAL_PEOPLE_DONG_202606_tidy.parquet")
    db_path = os.path.join("seoul-pops", "data", "seoul_pops.db")
    
    print("Step 1. 대용량 Parquet 파일 로드 중...")
    start_time = time.time()
    df = pd.read_parquet(parquet_path)
    print(f"Parquet 로드 완료: {time.time() - start_time:.2f} 초 (Shape: {df.shape})")
    
    print("\nStep 2. 자치구 매핑 및 시간대/주말 파생변수 생성 중...")
    df['행정동코드_str'] = df['행정동코드'].astype(str)
    df['자치구코드'] = df['행정동코드_str'].str[:5]
    df['자치구'] = df['자치구코드'].map(DISTRICT_MAP).fillna('기타')
    df.drop(columns=['행정동코드_str', '자치구코드'], inplace=True)
    
    unique_dates = df['기준일ID'].unique()
    date_series = pd.to_datetime(unique_dates.astype(str), format='%Y%m%d')
    date_to_dayname = {d: dt.strftime('%Y-%m-%d (%a)') for d, dt in zip(unique_dates, date_series)}
    date_to_weekend = {d: '주말' if dt.dayofweek >= 5 else '주중' for d, dt in zip(unique_dates, date_series)}
    
    df['날짜포맷'] = df['기준일ID'].map(date_to_dayname)
    df['주말구분'] = df['기준일ID'].map(date_to_weekend)
    print("파생변수 합성 완료.")
    
    # SQLite 커넥션 설정
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"\n기존 DB 파일 제거 완료: {db_path}")
        
    conn = sqlite3.connect(db_path)
    
    # 1. basic_summary 테이블 저장
    print("\nStep 3. 기본 요약 정보 및 데이터 품질 진단 테이블 작성 중...")
    rows_count, cols_count = df.shape
    duplicates = int(df.duplicated().sum())
    
    summary_data = pd.DataFrame({
        "info_key": ["rows", "cols", "duplicates", "last_updated"],
        "info_value": [str(rows_count), str(cols_count), str(duplicates), time.strftime('%Y-%m-%d %H:%M:%S')]
    })
    summary_data.to_sql('basic_summary', conn, if_exists='replace', index=False)
    
    # 2. daily_pop_trend
    print("일자별 생활인구 합계 집계 중...")
    daily_trend = df.groupby('날짜포맷', observed=True)['생활인구수'].sum().reset_index()
    daily_trend.to_sql('daily_pop_trend', conn, if_exists='replace', index=False)
    
    # 3. hourly_pop_trend
    print("시간대별 평균 생활인구 집계 중...")
    hourly_trend = df.groupby('시간대구분')['생활인구수'].mean().reset_index()
    hourly_trend.to_sql('hourly_pop_trend', conn, if_exists='replace', index=False)
    
    # 4. gender_pop_dist
    print("성별 생활인구 비율 집계 중...")
    gender_dist = df.groupby('성별', observed=True)['생활인구수'].sum().reset_index()
    gender_dist.to_sql('gender_pop_dist', conn, if_exists='replace', index=False)
    
    # 5. age_pop_dist
    print("연령대별 생활인구 분포 집계 중...")
    age_dist = df.groupby('연령대', observed=True)['생활인구수'].sum().reset_index()
    age_dist.to_sql('age_pop_dist', conn, if_exists='replace', index=False)
    
    # 6. gender_age_pop_dist
    print("연령대 및 성별 생활인구 비교 집계 중...")
    gender_age_dist = df.groupby(['연령대', '성별'], observed=True)['생활인구수'].sum().reset_index()
    gender_age_dist.to_sql('gender_age_pop_dist', conn, if_exists='replace', index=False)
    
    # 7. dong_pop_ranking
    print("행정동별 평균 생활인구(랭킹용) 집계 중...")
    dong_ranking = df.groupby(['행정동코드', '자치구'], observed=True)['생활인구수'].mean().reset_index()
    dong_ranking.to_sql('dong_pop_ranking', conn, if_exists='replace', index=False)
    
    # 8. weekend_hourly_pop
    print("주중 vs 주말 시간대별 평균 인구 집계 중...")
    weekend_hourly = df.groupby(['주말구분', '시간대구분'], observed=True)['생활인구수'].mean().reset_index()
    weekend_hourly.to_sql('weekend_hourly_pop', conn, if_exists='replace', index=False)
    
    # 9. hourly_district_pop [자치구 지도 전용]
    print("지도용 시간대별 자치구 평균 생활인구 집계 중...")
    district_map_pop = df.groupby(['시간대구분', '자치구'], observed=True)['생활인구수'].mean().reset_index()
    district_map_pop.to_sql('hourly_district_pop', conn, if_exists='replace', index=False)
    
    # 10. hourly_dong_pop [행정동 지도 전용]
    print("지도용 시간대별 행정동 평균 생활인구 집계 중...")
    dong_map_pop = df.groupby(['시간대구분', '행정동코드'], observed=True)['생활인구수'].mean().reset_index()
    # 행정동코드를 문자열로 일관 변환하여 DB에 저장
    dong_map_pop['행정동코드'] = dong_map_pop['행정동코드'].astype(str)
    dong_map_pop.to_sql('hourly_dong_pop', conn, if_exists='replace', index=False)
    
    # 11. advanced_stats
    print("고급 통계량(왜도, 첨도, IQR, 이상치 등) 사전 연산 중...")
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
    
    stats_df = pd.DataFrame({
        "stat_key": [
            "mean", "median", "mode", "std", "cv", 
            "skewness", "kurtosis", "q1", "q3", "iqr", 
            "lower_bound", "upper_bound", "outlier_count", "outlier_ratio"
        ],
        "stat_value": [
            float(mean_val), float(median_val), float(mode_val), float(std_val), float(cv_val),
            float(skew_val), float(kurt_val), float(q1), float(q3), float(iqr),
            float(lower_bound), float(upper_bound), float(outlier_count), float(outlier_ratio)
        ]
    })
    stats_df.to_sql('advanced_stats', conn, if_exists='replace', index=False)
    
    # 인덱스 추가 생성하여 DB 쿼리 퍼포먼스 극대화
    print("\nStep 4. 데이터베이스 쿼리 인덱스 추가 및 최적화 중...")
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX idx_district_pop ON hourly_district_pop (시간대구분);")
    cursor.execute("CREATE INDEX idx_dong_pop ON hourly_dong_pop (시간대구분);")
    conn.commit()
    
    print("\n데이터베이스 빌드 완료!")
    print(f"생성된 SQLite 파일 크기: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
    conn.close()

if __name__ == '__main__':
    main()
