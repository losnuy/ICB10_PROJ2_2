"""
이 스크립트는 서울 마포구 연남동(행정동코드: 11440660)의 생활인구 데이터만 추출하여
fg-data-profiling 도구를 사용해 인터랙티브 데이터 프로파일링 리포트(HTML)를 생성하는 스크립트입니다.
주요 기능:
- Parquet 데이터 로드 후 연남동 데이터(20,160행) 필터링
- matplotlib 폰트 맑은 고딕(Malgun Gothic) 몽키 패치 적용 (한글 깨짐 방지)
- yeonnam_profile.html 파일로 결과 리포트 저장
"""

import os
import sys
import pandas as pd
import numpy as np

# 터미널 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# Matplotlib 한글 폰트 설정 및 몽키 패치 (차트 내부 한글 깨짐 완전 방지)
import matplotlib
import matplotlib.pyplot as plt
import koreanize_matplotlib
import matplotlib.font_manager as fm
import contextlib

# 1. 폰트 매니저의 findfont를 가로채어 Arial/sans-serif 요청을 맑은 고딕으로 강제 리다이렉트
original_findfont = fm.FontManager.findfont

def custom_findfont(self, prop, *args, **kwargs):
    from matplotlib.font_manager import FontProperties
    if isinstance(prop, str):
        if any(x in prop for x in ['Arial', 'sans-serif', 'DejaVu Sans', 'Liberation Sans']):
            prop = 'Malgun Gothic'
    elif isinstance(prop, FontProperties):
        name = prop.get_name()
        if name in ['Arial', 'sans-serif', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans']:
            prop.set_family('Malgun Gothic')
            prop.set_name('Malgun Gothic')
    return original_findfont(self, prop, *args, **kwargs)

fm.FontManager.findfont = custom_findfont

# fg-data-profiling 임포트 (ydata_profiling 사용)
from ydata_profiling import ProfileReport
import data_profiling.visualisation.context as ctx

# 2. 스타일 컨텍스트 매니저 패치
original_manage_ctx = ctx.manage_matplotlib_context

@contextlib.contextmanager
def custom_manage_matplotlib_context():
    with original_manage_ctx():
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = ["Malgun Gothic", "sans-serif"]
        matplotlib.rcParams["axes.unicode_minus"] = False
        yield

ctx.manage_matplotlib_context = custom_manage_matplotlib_context

def main():
    print("=== 연남동 데이터 프로파일링 리포트 생성 시작 ===")
    
    parquet_path = 'seoul-pops/data/LOCAL_PEOPLE_DONG_202606_tidy.parquet'
    output_html_path = 'seoul-pops/report/yeonnam_profile.html'
    
    # 1. 데이터 로드 및 연남동 필터링
    if not os.path.exists(parquet_path):
        print(f"Error: 데이터셋 파일이 존재하지 않습니다: {parquet_path}", file=sys.stderr)
        sys.exit(1)
        
    print(f"1. 데이터 로딩 중: {parquet_path}")
    df = pd.read_parquet(parquet_path)
    
    # 연남동 행정동코드: '11440660' (마포구 연남동)
    yeonnam_code = '11440660'
    print(f"2. 연남동(코드: {yeonnam_code}) 데이터 필터링 중...")
    df_yeonnam = df[df['행정동코드'].astype(str) == yeonnam_code].copy()
    
    rows_count = len(df_yeonnam)
    print(f"필터링 완료: 총 {rows_count:,}개 행 추출")
    
    if rows_count == 0:
        print("Error: 연남동 코드로 필터링된 행이 없습니다. 데이터셋의 행정동코드를 다시 확인하세요.", file=sys.stderr)
        sys.exit(1)
        
    # 2. 프로파일링 수행
    print("3. 연남동 데이터 프로파일링 리포트 생성 중 (ydata-profiling)...")
    profile = ProfileReport(df_yeonnam, title="Mapo-gu Yeonnam-dong Population Profiling", explorative=True)
    
    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
    profile.to_file(output_html_path)
    
    print(f"4. 연남동 프로파일링 리포트 저장 완료: {output_html_path}")
    print("=== 연남동 프로파일링 작업 완료 ===")

if __name__ == '__main__':
    main()
