# 서울시 생활인구 대시보드 - southkorea-maps GeoJSON 전환 및 매핑 계획

사용자 요청에 따라 서울시 지도 시각화에 적용할 지리 정보(GeoJSON) 데이터를 **`southkorea/southkorea-maps`** 저장소의 파일로 전환하고, 8자리 행안부 행정동코드와 7자리 통계청 코드 간의 불일치를 완벽하게 해소하기 위한 업데이트 계획입니다.

## 🗺️ 지리 정보(GeoJSON) 및 매핑 데이터 수립

1. **지리 경계 데이터 (southkorea/southkorea-maps)**:
   - **자치구별 (구별) GeoJSON**: `https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_municipalities_geo_simple.json`
     - 서울시 자치구 피처(code 속성이 `'11'`로 시작하는 25개 구)만 필터링하여 시각화에 반영합니다.
   - **행정동별 (동별) GeoJSON**: `https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_submunicipalities_geo_simple.json`
     - 서울시 행정동 피처(code 속성이 `'11'`로 시작하는 423개 동)만 필터링하여 시각화에 반영합니다.

2. **코드 매핑 사전 빌드 (통계청 7자리 ↔ 행안부 8자리)**:
   - `southkorea-maps` 의 행정동 GeoJSON은 properties에 7자리 통계청 코드(`code`)만 포함하고 있어, 대시보드 데이터의 8자리 행안부 행정동코드와 다이렉트 매핑율이 11% 수준으로 매우 낮습니다.
   - 이를 해결하기 위해, 검증 완료된 `raqoon886/Local_HangJeongDong` 저장소의 `hangjeongdong_서울특별시.geojson` 속성 데이터( properties의 `adm_cd`와 `adm_cd2` 정보)를 활용하여 **행안부 8자리 코드와 통계청 7자리 코드를 1:1로 정확하게 연결하는 매핑 사전을 메모리 상에 캐시 빌드**합니다.
   - 데이터프레임의 8자리 코드를 이 사전에 매핑하여 통계청 7자리로 일괄 변환 후, `southkorea-maps` GeoJSON의 `'code'` 속성과 100% 완벽하게 바인딩합니다.

## 🛠️ 제안된 변경 사항

### 소스 코드
#### [MODIFY] [utils.py](file:///c:/workspace/ICB10_22222/seoul-pops/src/utils.py)
- `load_geojson` 함수를 수정하여 `southkorea/southkorea-maps` 의 전국 GeoJSON 중 서울특별시 피처만 필터링하여 반환하도록 변경합니다.
- `load_code_mapping` 함수를 새로이 추가하여 행정 표준 코드 매핑 딕셔너리를 캐싱 빌드하는 기능을 구현합니다.

#### [MODIFY] [app.py](file:///c:/workspace/ICB10_22222/seoul-pops/src/app.py)
- `load_code_mapping`으로 가져온 딕셔너리를 사용하여 행정동 공간 집계 데이터프레임의 코드를 통계청 7자리로 변환하는 단계를 연동합니다.
- `southkorea-maps` 읍면동 피처의 `code` 속성과 데이터프레임을 바인딩하여 Folium 코로플리스 지도를 렌더링합니다.

---

## 🔍 검증 계획
1. 대시보드 구동 후 지도 시각화 탭에서 서울시 자치구별 및 행정동별 지도가 누락이나 에러 없이 완전히 채워져 렌더링되는지 확인합니다.
2. 검증 결과를 캡처하여 `seoul-pops/docs` 폴더에 최종 배포합니다.
