# -*- coding: utf-8 -*-
"""
adsp test CSV 데이터 탐색을 수행하는 스크립트입니다.
카페명 빈도, 텍스트 내 주요 키워드 및 간접 회차 정보 등을 분석합니다.
"""

import pandas as pd
import re
import sys
from collections import Counter

# 표준 출력 인코딩을 UTF-8로 설정하여 한글 깨짐 방지
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 파일 경로
file_path = "project2/data/2026-07-15T13-11_adsp test.csv"

# 데이터 로드
try:
    df = pd.read_csv(file_path)
    print(f"데이터 로드 성공. 행 개수: {len(df)}, 컬럼 목록: {df.columns.tolist()}")
except Exception as e:
    print(f"데이터 로드 실패: {e}")
    exit(1)

# 1. 카페별 언급 빈도수 분석
print("\n[1] 카페별 언급 빈도 Top 10")
cafe_counts = df['카페명'].value_counts()
for name, cnt in cafe_counts.head(10).items():
    print(f"- {name}: {cnt}건")

# 2. 제목 및 요약 내 숫자/회차/연도 등 시계열 단서 추출
print("\n[2] 제목 및 요약 내 회차(회) 및 연도(년) 언급 패턴")
text_combined = " ".join(df['제목'].fillna('') + " " + df['요약'].fillna(''))
rounds = re.findall(r'\d+회', text_combined)
years = re.findall(r'20\d{2}년', text_combined)

print(f"- 언급된 시험 회차 빈도: {Counter(rounds)}")
print(f"- 언급된 연도 빈도: {Counter(years)}")

# 3. 준비 기간(주, 달, 일) 관련 언급 분석
print("\n[3] 구직자 체감 준비 기간 언급")
study_periods = []
# 2주, 3주, 한 달, 3일, 7일 등 패턴 탐지
patterns = [r'\d+주', r'\d+일', r'한\s*달', r'두\s*달']
found_periods = []
for p in patterns:
    found_periods.extend(re.findall(p, text_combined))
print(f"- 준비 기간 관련 언급 빈도: {Counter(found_periods)}")

# 4. 주요 주제 키워드(난이도, 인강, 비전공자 등) 언급 분석
print("\n[4] 주요 관심 주제어 분석")
keywords = ["난이도", "비전공자", "노베이스", "독학", "인강", "합격후기", "시험일정", "접수"]
kw_counts = {}
for kw in keywords:
    kw_counts[kw] = text_combined.count(kw)
for kw, cnt in sorted(kw_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"- {kw}: {cnt}회 언급")
