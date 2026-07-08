# -*- coding: utf-8 -*-
"""
서울시 행정동별 생활인구 데이터를 처리하는 스크립트입니다.
ZIP 파일에서 직접 CSV 데이터를 로드한 뒤 Tidy Data(깔끔한 데이터) 형태로 변환하고,
기준일ID와 행정동코드를 카테고리 형태로 변경한 뒤, 기술통계를 바탕으로 수치형 데이터를 최적화(Downcasting)합니다.
최종적으로 분석 연산으로 유도 가능한 '총생활인구수' 컬럼을 데이터프레임에서 완전히 제외하여 최적화 효율을 극대화합니다.
"""

import os
import sys
import io
import pandas as pd
import numpy as np

# 터미널 한글 깨짐 방지를 위해 출력 인코딩을 UTF-8로 설정
sys.stdout.reconfigure(encoding='utf-8')

def main():
    zip_path = 'seoul-pops/data/LOCAL_PEOPLE_DONG_202606.zip'
    parquet_path = 'seoul-pops/data/LOCAL_PEOPLE_DONG_202606_tidy.parquet'
    
    print("Step 1. ZIP 파일에서 데이터 로드 중...")
    df_raw = pd.read_csv(zip_path, index_col=False, encoding='utf-8-sig')
    
    print("\n--- 원본 데이터 상위 5개 행 ---")
    print(df_raw.head(5))
    
    print("\nStep 2. 원본 데이터프레임 info() 캡처 중...")
    buffer_raw = io.StringIO()
    df_raw.info(buf=buffer_raw, show_counts=False)
    info_raw = buffer_raw.getvalue()
    print(info_raw)
    
    # 원본 info 정보 저장
    os.makedirs('seoul-pops/report', exist_ok=True)
    with open('seoul-pops/report/info_raw.txt', 'w', encoding='utf-8') as f:
        f.write(info_raw)
        
    print("\nStep 3. Tidy-data 형태로 데이터 변환 (Melt) 중...")
    id_vars = ['기준일ID', '시간대구분', '행정동코드', '총생활인구수']
    value_vars = [col for col in df_raw.columns if col not in id_vars]
    
    df_tidy = df_raw.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name='성별_연령대_구분',
        value_name='생활인구수'
    )
    
    print("Step 4. 성별 및 연령대 별도 컬럼으로 분리 추출 중...")
    df_tidy['성별'] = df_tidy['성별_연령대_구분'].str[:2]
    df_tidy['연령대'] = df_tidy['성별_연령대_구분'].str[2:-5]
    
    # 불필요해진 기존 구분 컬럼 및 분석으로 계산 가능한 '총생활인구수' 제거 (사용자 요청 반영)
    df_tidy.drop(columns=['성별_연령대_구분', '총생활인구수'], inplace=True)
    
    print("Step 5. 기술 통계 확인 및 분석 중...")
    # 임시 변환하여 기술 통계 수집
    df_tidy['기준일ID'] = df_tidy['기준일ID'].astype(str)
    df_tidy['행정동코드'] = df_tidy['행정동코드'].astype(str)
    desc_numeric = df_tidy[['시간대구분', '생활인구수']].describe()
    desc_categorical = df_tidy[['기준일ID', '행정동코드', '성별', '연령대']].describe(include='all')
    
    # 기술 통계 결과를 텍스트 파일로 저장
    with open('seoul-pops/report/descriptive_statistics.txt', 'w', encoding='utf-8') as f:
        f.write("=== 수치형 데이터 기술 통계 ===\n")
        f.write(desc_numeric.to_string())
        f.write("\n\n=== 범주형 데이터 기술 통계 ===\n")
        f.write(desc_categorical.to_string())
        
    print("\nStep 6. 기술통계 기반 데이터 타입 최적화 및 컬럼 정렬 중...")
    # 사용자 요구 순서 및 타입 지정
    df_tidy['기준일ID'] = df_tidy['기준일ID'].astype('category')
    df_tidy['시간대구분'] = df_tidy['시간대구분'].astype(np.int8)
    df_tidy['행정동코드'] = df_tidy['행정동코드'].astype('category')
    df_tidy['생활인구수'] = df_tidy['생활인구수'].astype(np.float32)
    df_tidy['성별'] = df_tidy['성별'].astype('category')
    df_tidy['연령대'] = df_tidy['연령대'].astype('category')
    
    # [사용자 요청 반영] '총생활인구수'를 제외한 컬럼 정렬
    col_order = ['기준일ID', '시간대구분', '행정동코드', '생활인구수', '성별', '연령대']
    df_tidy = df_tidy[col_order]
    
    print("\n--- Tidy Data (최적화 완료) 상위 5개 행 ---")
    print(df_tidy.head(5))
    
    print("\nStep 7. Parquet 형태로 압축 저장 중...")
    df_tidy.to_parquet(parquet_path, engine='pyarrow', index=False)
    print(f"Parquet 저장 완료: {parquet_path}")
    
    print("\nStep 8. 저장한 Parquet 데이터를 다시 불러오는 중...")
    df_parquet = pd.read_parquet(parquet_path)
    
    print("\nStep 9. 최종 Parquet 데이터프레임 info() 결과 (Non-Null 정보 제외):")
    buffer_parquet = io.StringIO()
    df_parquet.info(buf=buffer_parquet, show_counts=False)
    info_parquet = buffer_parquet.getvalue()
    print(info_parquet)
    
    # 캡처된 Parquet info 정보를 저장
    with open('seoul-pops/report/info_parquet.txt', 'w', encoding='utf-8') as f:
        f.write(info_parquet)
        
    print("\n데이터 최적화 및 처리 작업이 완료되었습니다!")

if __name__ == '__main__':
    main()
