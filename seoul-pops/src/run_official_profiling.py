"""
이 스크립트는 fg-data-profiling 도구를 사용하여 데이터 프로파일링을 실행하는 공식 스크립트입니다.
주요 기능:
- eda_report.md 파일 내의 마크다운 테이블(상/하위 5행)을 파싱하여 데이터프레임으로 변환
- 실제 원본 데이터셋(Parquet)에서 50,000행의 랜덤 샘플을 추출하여 데이터프레임 생성
- fg-data-profiling(data_profiling)의 ProfileReport를 활용해 두 대상의 프로파일링 리포트(HTML) 생성
- 생성 완료 시 로컬 HTTP 서버 주소로 브라우저 오픈 유도
"""

import os
import sys
import pandas as pd
import numpy as np

# 터미널 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# Matplotlib 한글 폰트 설정
import matplotlib.pyplot as plt
import koreanize_matplotlib
plt.rc('font', family='Malgun Gothic')

# fg-data-profiling 임포트 (ydata_profiling 사용)
from ydata_profiling import ProfileReport

# 런타임 몽키 패치 (차트 내부 한글 깨짐 완전 방지)
import contextlib
import data_profiling.visualisation.context as ctx
import matplotlib
import matplotlib.font_manager as fm

# 1. 폰트 매니저의 findfont를 가로채어 Arial 요청을 맑은 고딕으로 강제 리다이렉트
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

def parse_markdown_tables(filepath):
    """
    마크다운 파일에서 표(Table) 형식을 찾아 Pandas DataFrame 리스트로 파싱합니다.
    """
    if not os.path.exists(filepath):
        print(f"Error: 파일이 존재하지 않습니다: {filepath}", file=sys.stderr)
        return []
        
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    tables = []
    current_table = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            # 마크다운 표 구분선(|---|) 제외
            if '---' in line:
                continue
            cols = [c.strip() for c in line.split('|')[1:-1]]
            current_table.append(cols)
        else:
            if current_table:
                tables.append(current_table)
                current_table = []
    if current_table:
        tables.append(current_table)
        
    dfs = []
    for t in tables:
        if len(t) > 1:
            headers = t[0]
            rows = t[1:]
            df_temp = pd.DataFrame(rows, columns=headers)
            dfs.append(df_temp)
    return dfs

def main():
    print("=== fg-data-profiling 공식 프로파일링 프로세스 시작 ===")
    
    md_path = 'seoul-pops/report/eda_report.md'
    parquet_path = 'seoul-pops/data/LOCAL_PEOPLE_DONG_202606_tidy.parquet'
    
    report_dir = 'seoul-pops/report'
    os.makedirs(report_dir, exist_ok=True)
    
    # ----------------- 1. eda_report.md 내 테이블 프로파일링 -----------------
    print(f"\n1. 마크다운 보고서 테이블 파싱 중: {md_path}")
    parsed_dfs = parse_markdown_tables(md_path)
    
    if not parsed_dfs:
        print("Warning: 파싱된 마크다운 테이블이 없습니다.")
        df_md = pd.DataFrame()
    else:
        # 추출된 상위 5행, 하위 5행 테이블 합치기
        print(f"파싱 완료: {len(parsed_dfs)}개의 테이블 발견. 병합 수행 중...")
        df_md = pd.concat(parsed_dfs, ignore_index=True)
        
        # 타입 전처리
        if '시간대구분' in df_md.columns:
            df_md['시간대구분'] = pd.to_numeric(df_md['시간대구분'], errors='coerce')
        if '생활인구수' in df_md.columns:
            df_md['생활인구수'] = pd.to_numeric(df_md['생활인구수'], errors='coerce')
            
        print("파싱된 데이터프레임 프리뷰:")
        print(df_md.head())
        
        # fg-data-profiling 리포트 생성
        print("마크다운 데이터 프로파일링 리포트 생성 중...")
        profile_md = ProfileReport(df_md, title="Markdown Report Table Profiling", explorative=True)
        output_md_html = os.path.join(report_dir, 'eda_report_profile.html')
        profile_md.to_file(output_md_html)
        print(f"저장 완료: {output_md_html}")

    # ----------------- 2. 원본 parquet 데이터셋 프로파일링 (샘플) -----------------
    print(f"\n2. 원본 데이터셋 프로파일링 중 (50,000행 샘플링): {parquet_path}")
    if os.path.exists(parquet_path):
        df_raw = pd.read_parquet(parquet_path)
        
        # 850만 행 전체는 시간이 매우 오래 걸리므로 50,000행 무작위 샘플링
        df_sample = df_raw.sample(n=min(50000, len(df_raw)), random_state=42)
        
        print("데이터셋 샘플 프로파일링 리포트 생성 중...")
        profile_dataset = ProfileReport(df_sample, title="Seoul Population Dataset Profiling (50k Sample)", explorative=True)
        output_ds_html = os.path.join(report_dir, 'dataset_profile.html')
        profile_dataset.to_file(output_ds_html)
        print(f"저장 완료: {output_ds_html}")
    else:
        print(f"Error: 원본 Parquet 파일이 존재하지 않습니다: {parquet_path}", file=sys.stderr)
        
    print("\n=== fg-data-profiling 완료 ===")

if __name__ == '__main__':
    main()
