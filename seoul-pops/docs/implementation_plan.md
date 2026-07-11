# 서울시 생활인구 대시보드 - Parquet 원본 및 SQLite 집계 하이브리드 아키텍처 수립 계획

사용자의 추가 지침에 따라, 대시보드의 데이터 저장 및 쿼리 구조를 **"가공 및 집계 데이터는 SQLite DB에서 신속 조회"**하고, **"원본 수준의 지표 분석 및 진단은 Parquet 원천 데이터에서 직접 연산"**하는 하이브리드 형태로 구성하기 위한 계획입니다.

## 🛠️ 1. 하이브리드 데이터 흐름 설계

1. **Parquet 원본 데이터 연산 영역 (원천 데이터 보존 및 분석)**:
   - **대상 분석**: 📂 개요 및 데이터 진단 탭(행 수, 열 수, 결측치 진단, 원본 샘플 미리보기), 📈 단일 항목 분포 탭(왜도, 첨도, IQR 및 이상치 Box Plot).
   - **연동 방식**: `utils.py`에 `@st.cache_data`가 적용된 `load_raw_parquet()` 함수를 복원하여 대용량 Parquet 원본 파일(`LOCAL_PEOPLE_DONG_202606_tidy.parquet`)을 그대로 메모리에 로드하고, 실시간 기술통계량을 연산합니다.
   
2. **SQLite DB 집계 데이터 연산 영역 (가공 데이터 성능 최적화)**:
   - **대상 분석**: 📊 상관 및 다차원 분석 탭(요일별/시간대별/성별/연령별 비교), 🗺️ 생활인구 지도 시각화 탭(시간대별 자치구/행정동 평균 생활인구 공간 시각화).
   - **연동 방식**: 원본 Parquet 전체를 리드하여 그룹바이를 매번 수행하는 오버헤드를 막기 위해, 시간대별/지역별로 이미 가공·집계된 SQLite 테이블(`hourly_district_pop`, `hourly_dong_pop` 등)에서 필요한 정보만 필터링하여 지연 없이 빠르게 렌더링합니다.

---

## 🛠️ 제안된 변경 사항

### [MODIFY] [utils.py](file:///c:/workspace/ICB10_22222/seoul-pops/src/utils.py)
- `load_raw_parquet` 캐시 함수를 구현하여 원본 Parquet 데이터셋을 파생변수 포함 상태로 로드합니다.
- DB에서 기본 정보 및 고급 통계를 불러오던 `get_basic_info_from_db`, `get_advanced_stats_from_db` 함수를 폐지하고, 로드된 원본 데이터프레임을 인자로 받아 실시간 계산 후 반환하는 `get_basic_info(df)` 및 `calculate_advanced_stats(df)` 형태로 복원합니다.

### [MODIFY] [app.py](file:///c:/workspace/ICB10_22222/seoul-pops/src/app.py)
- 대시보드 로딩 시 `load_raw_parquet()` 로 원본 데이터를 로딩하여 1, 2번 탭(품질 요약 및 기술통계 연산)에 직접 바인딩합니다.
- 3, 4, 5번 탭은 기존과 동일하게 SQLite 사전 컴파일 테이블(`daily_pop_trend`, `hourly_district_pop` 등)을 연계해 지도 슬라이더와 시계열 차트의 빠른 전환 성능을 유지합니다.

---

## 🔍 검증 계획
1. 개요 및 분포 탭의 모든 텍스트 요약과 통계 지표가 원본 Parquet 계산과 정확하게 매핑되는지 검증합니다.
2. 개요 탭 하단에 원본 생활인구 Parquet 샘플 데이터(head 10개 행)가 정상적으로 표시되는지 확인합니다.
3. 지도 시각화 탭이 SQLite 사전 집계 쿼리를 통해 속도 저하 없이 매끄럽게 연동되는지 최종 교차 점검합니다.
