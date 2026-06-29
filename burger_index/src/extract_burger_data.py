"""
이 모듈은 전국 소상공인시장진흥공단 상가정보 데이터에서 4대 버거 브랜드의 매장 데이터를 추출하는 기능을 담당합니다.

주요 기능:
- 지정된 데이터 디렉토리에서 전국 17개 시도의 상가정보 CSV 파일 목록 로드
- 각 CSV 파일에서 상호명 컬럼을 대상으로 정규식을 사용해 버거킹, 맥도날드, KFC, 롯데리아(영문명 포함) 검색 및 필터링
- 필터링된 데이터를 하나로 병합하여 burger.csv 파일로 저장
"""

import os
import glob
import re
import pandas as pd

def main():
    # 데이터 폴더 경로 및 결과 저장 경로 정의 (워크스페이스 상대 경로 사용)
    data_dir = os.path.join("burger_index", "data")
    output_path = os.path.join("burger_index", "data", "burger.csv")
    
    # 4대 버거 브랜드 매칭을 위한 정규식 패턴 정의 (한글 및 영문, 대소문자 무관)
    # 버거킹 (Burger King), 맥도날드 (McDonald's, McDonalds), KFC (케이에프씨), 롯데리아 (Lotteria)
    pattern = r"버거킹|burger\s*king|맥도날드|mcdonald|kfc|케이에프씨|롯데리아|lotteria"
    
    # 데이터 디렉토리에서 시도별 csv 파일 검색
    csv_files = glob.glob(os.path.join(data_dir, "소상공인시장진흥공단_상가(상권)정보_*.csv"))
    
    if not csv_files:
        print("대상 CSV 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
        return

    print(f"총 {len(csv_files)}개의 시도별 CSV 파일을 처리합니다.")
    
    filtered_dfs = []
    
    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        print(f"파일 처리 중: {file_name} ...")
        
        try:
            # 대용량 파일이므로 로딩 시 데이터 타입 추론 경고를 방지하기 위해 low_memory=False 설정
            # 인코딩은 파일 열람 방법 가이드에 따라 utf-8 사용
            df = pd.read_csv(file_path, encoding="utf-8", low_memory=False)
            
            # '상호명' 컬럼이 존재하는지 확인
            if "상호명" not in df.columns:
                print(f"경고: {file_name} 파일에 '상호명' 컬럼이 존재하지 않습니다. 건너뜁니다.")
                continue
                
            # 정규식을 이용해 브랜드명 필터링 (대소문자 구분 없음, 결측치 제외)
            mask = df["상호명"].str.contains(pattern, flags=re.IGNORECASE, na=False)
            df_filtered = df[mask]
            
            if not df_filtered.empty:
                print(f"  -> {len(df_filtered)}건 추출 완료")
                filtered_dfs.append(df_filtered)
            else:
                print("  -> 추출된 데이터 없음")
                
        except Exception as e:
            print(f"오류 발생 ({file_name}): {e}")

    # 추출된 데이터가 있는 경우 병합하여 파일로 저장
    if filtered_dfs:
        merged_df = pd.concat(filtered_dfs, ignore_index=True)
        print(f"\n필터링 완료. 전체 추출 데이터 건수: {len(merged_df)}건")
        
        # 출력 폴더 생성 (이미 존재하지만 방어 코드 추가)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 엑셀에서 열 때 깨지지 않도록 utf-8-sig 인코딩 사용
        merged_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"성공적으로 데이터를 병합하여 '{output_path}'에 저장했습니다.")
    else:
        print("\n추출된 버거 브랜드 데이터가 없습니다. 파일 생성을 취소합니다.")

if __name__ == "__main__":
    main()
