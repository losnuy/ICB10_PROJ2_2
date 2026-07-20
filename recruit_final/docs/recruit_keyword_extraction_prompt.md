# 직무별 역량/스펙 키워드 추출 및 네이버 검색 트렌드 분석 연계 프롬프트 (개선판)

본 프롬프트는 수집된 채용 정보 데이터베이스(`recruit.f.db`)로부터 직무별 역량, 자격요건, 자격증 관련 빈발 키워드를 정교하게 추출하고, 이를 네이버 검색어 빈도 분석(네이버 검색광고 API 및 네이버 데이터랩 트렌드 API 등)에 바로 적용할 수 있도록 가공하기 위해 설계된 가이드라인입니다.

---

## 1. 역할 정의 (System Role)
귀하는 대용량 채용 텍스트 데이터를 정제하고 마켓 트렌드를 도출하는 **데이터 과학자이자 오디언스 리서치 전문가**입니다. 수집된 채용 공고의 자격요건(Requirement)과 우대사항(Preferential)을 계량적으로 분석하여, 구직자들이 네이버 등 포털 사이트에서 실제로 검색해볼 만한 핵심 키워드를 직무별로 정밀 추출하고 구조화하는 작업을 수행합니다.

---

## 2. 분석 목적 및 배경
- **목표**: 채용 공고에서 요구하는 주요 역량, 기술 스택, 우대 자격증 키워드를 직무별로 추출하고 수치화합니다.
- **연계 분석**: 추출된 키워드를 네이버 트렌드와 네이버 키워드 도구(검색광고 API)에 대입하여 **"기업이 요구하는 스펙(공고 빈도)"**과 **"구직자가 관심을 갖는 스펙(네이버 검색량)"** 간의 격차(Gap) 및 관심사 트렌드를 비교 분석합니다.

---

## 3. 분석 대상 데이터베이스 스키마 (`recruit.f.db`)
분석 대상 데이터베이스는 아래 두 테이블을 `rec_idx`로 조인하여 사용합니다.

### 1) `recruit_list` (채용 공고 기본 정보 테이블)
- `rec_idx` (TEXT, PK): 채용 공고 고유 식별자
- `job_category` (TEXT): 실제 DB 내 직무 분류 (`mkt` (마케팅), `plan` (기획), `dev` (개발), `hr` (인사), `acc` (회계))
- `title` (TEXT): 채용 공고 제목
- `company_name` (TEXT): 기업명
- `updated_at` (TIMESTAMP): 수집/갱신 일자

### 2) `recruit_detail` (채용 공고 상세 정보 테이블)
- `rec_idx` (TEXT, FK): 채용 공고 고유 식별자
- `requirement` (TEXT): 자격요건 정보 (가중치: 1.0)
- `preferential` (TEXT): 우대사항 정보 (가중치: 1.5 - 최신 트렌드 스택이 많으므로 가중치 부여)
- `job_description` (TEXT): 상세 직무 기술
- `detail_content` (TEXT): 전체 HTML/텍스트 본문

---

## 4. 정교화된 키워드 정제 및 매핑 규칙 (10대 핵심 규칙)

### 1) 네이버 검색 플랫폼 제약 사항 준수
- 네이버 트렌드 API 및 키워드 광고 API 연동을 위해 모든 키워드는 **특수문자 및 기호가 정제된 명사형**이어야 합니다.
- 특수문자가 포함된 기술(예: `C++`, `C#`, `Vue.js`)은 검색 시 기호가 누락될 수 있으므로 동의어 그룹에 `C++`, `씨플플`, `C플플` 등을 반드시 함께 생성합니다.

### 2) 한/영 동의어 및 축약어 표준 매핑
- 동일한 대상을 지칭하는 다양한 표기를 하나의 표준 대표 키워드로 매핑합니다.
  - *예시*: `React` / `리액트` / `React.js` → 대표어: `React`
  - *예시*: `정보처리기사` / `정처기` / `정보 처리 기사` → 대표어: `정보처리기사`

### 3) 텍스트 노이즈 및 상투적 불용어(Stopwords) 배제
- 구직자가 검색창에 검색하지 않는 일반 용어나 채용 상투 문구는 키워드 추출 시 제외합니다.
  - 제외 대상 예시: `우대`, `가능자`, `경험`, `업무`, `인원`, `인근거주자`, `성실`, `커뮤니케이션`, `학력무관`

### 4) 직무명(카테고리명) 자체 필터링
- 해당 직무 도메인에서 너무 흔하게 나타나는 직무명 자체는 중요 키워드에서 제외합니다.
  - *예시*: `dev` 직무 내에서 `개발자` 키워드 제외, `mkt` 직무 내에서 `마케터`/`마케팅` 키워드 제외.

### 5) 데이터 가치 가중치 부여 (필수 vs 우대)
- 자격요건(`requirement`)보다 우대사항(`preferential`) 필드에서 추출된 키워드에 **1.5배의 가중치**를 부여하여 트렌디한 기술 스택이 상위에 도출되도록 조정합니다.

### 6) 최신성(Recency) 가중치 필터 적용
- `updated_at` 컬럼을 기준으로 최근 3개월 이내에 등록된 공고의 키워드에 추가 가중치(예: 1.2배)를 부여하여 시장의 최신 트렌드를 우선 반영합니다.

### 7) 네이버 데이터랩 트렌드 API 규격 동기화
- 네이버 데이터랩 트렌드 API는 **최대 5개의 주제어 그룹**, **각 그룹별 최대 20개의 검색어** 설정이 가능합니다. LLM은 직무별로 가장 빈도가 높은 Top 5 대표 키워드를 선정한 뒤, 각 대표 키워드에 매핑되는 20개 이하의 연관 키워드 어레이(Array)를 함께 제공해야 합니다.

### 8) 네이버 키워드 도구용 검색수 검증
- 네이버 광고주 시스템의 '키워드 도구 API'를 통해 월간 검색수(PC/모바일)를 2차 쿼리할 수 있도록 띄어쓰기가 정형화된 키워드 목록을 함께 분리 제공합니다.

### 9) 자격증 명칭 표준화
- 자격증은 한국산업인력공단 등 공인 기관의 표준 명칭으로 통합하되, 구직자들이 흔히 검색하는 줄임말도 함께 동의어 그룹으로 관리합니다 (예: `ADsP` → `데이터분석준전문가`, `ADsP`).

### 10) 정성적 소프트 스킬의 정량화 배제
- '소통 능력', '적극성'과 같은 주관적 평가는 네이버 검색어 빈도 분석의 유의미성이 낮으므로, 철저히 **하드 스킬(기술, 툴, 프레임워크)** 및 **정량적 스펙(자격증, 어학 등)** 위주로만 키워드를 추출합니다.

---

## 5. 실전 분석 및 전처리 파이썬(Python) 코드

데이터베이스에서 데이터를 로드하고 한국어 형태소 분석기(`KoNLPy`의 `Okt`)를 적용해 명사를 추출하며, 가중치를 적용해 빈도를 산출하는 고도화된 스크립트 예시입니다.

```python
"""
SQLite DB에서 직무별 데이터를 수집하고 형태소 분석을 통해 
가중치가 적용된 명사 키워드를 추출하는 파이썬 스크립트입니다.
"""

import sqlite3
import pandas as pd
from collections import Counter
from konlpy.tag import Okt
import re

# 직무별/항목별 불용어 정의 (실제 DB의 job_category 값 매핑)
STOPWORDS = {
    '공통': ['우대', '가능자', '경험', '업무', '인원', '지원', '근무', '필수', '관련', '능력', '사항'],
    'dev': ['개발', '개발자', '프로그래머'],
    'mkt': ['마케팅', '마케터', '홍보'],
    'plan': ['기획', '기획자'],
    'hr': ['인사', '채용', '노무'],
    'acc': ['회계', '세무', '경리']
}

def load_and_clean_data(db_path):
    conn = sqlite3.connect(db_path)
    query = """
        SELECT 
            l.job_category,
            d.requirement,
            d.preferential,
            l.updated_at
        FROM recruit_list l
        JOIN recruit_detail d ON l.rec_idx = d.rec_idx
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def extract_keywords_by_category(df, category):
    # 특정 직무 필터링
    df_cat = df[df['job_category'] == category]
    okt = Okt()
    word_counter = Counter()

    for _, row in df_cat.iterrows():
        # 1. 필수요건 (가중치 1.0)
        if row['requirement']:
            req_clean = re.sub(r'[^a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣0-9\s#\+]', ' ', row['requirement'])
            nouns = okt.nouns(req_clean)
            for n in nouns:
                if len(n) > 1 and n not in STOPWORDS['공통'] and n not in STOPWORDS.get(category, []):
                    word_counter[n] += 1.0

        # 2. 우대사항 (가중치 1.5)
        if row['preferential']:
            pref_clean = re.sub(r'[^a-zA-Zㄱ-ㅎㅏ-ㅣ가-힣0-9\s#\+]', ' ', row['preferential'])
            nouns = okt.nouns(pref_clean)
            for n in nouns:
                if len(n) > 1 and n not in STOPWORDS['공통'] and n not in STOPWORDS.get(category, []):
                    word_counter[n] += 1.5

    return word_counter.most_common(20)
```

---

## 6. 네이버 트렌드 맞춤형 최종 출력 포맷

### [JSON 포맷: 네이버 데이터랩 API 입력 규격 호환]
```json
{
  "job_category": "dev",
  "naver_trend_payload": {
    "startDate": "2026-01-01",
    "endDate": "2026-06-30",
    "timeUnit": "month",
    "keywordGroups": [
      {
        "groupName": "파이썬",
        "keywords": ["파이썬", "Python", "Python3", "파이썬인강", "파이썬기초"]
      },
      {
        "groupName": "리액트",
        "keywords": ["React", "리액트", "ReactJS", "React.js", "리액트공부"]
      },
      {
        "groupName": "정보처리기사",
        "keywords": ["정보처리기사", "정처기", "정보처리기사실기", "정보처리기사필기", "정처기일정"]
      }
    ]
  }
}
```

### [마크다운 테이블: 기획/보고서용 양식]
| 직무 카테고리 | 구분 | 대표 키워드 (주제어) | 네이버 검색어 그룹 (20자 이내 쉼표 구분) | 공고 내 가중치 적용 빈도수 |
| :--- | :--- | :--- | :--- | :--- |
| dev | 기술 | 파이썬 | `파이썬, Python, Python3, 파이썬인강, 파이썬기초` | 217.5 |
| dev | 자격증 | 정보처리기사 | `정보처리기사, 정처기, 정보처리기사실기, 정보처리기사필기` | 81.0 |
| acc | 자격증 | 전산세무 | `전산세무, 전산세무1급, 전산세무2급, 전산세무인강` | 100.5 |
