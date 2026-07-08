"""
통합 채용 데이터 EDA 데이터 분석 및 마크다운 보고서 생성을 실행하는 엔트리포인트 스크립트입니다.
"""
import sys
import os

# 모듈 로드를 위해 부모 디렉토리를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.eda_analysis import RecruitEDA

def main():
    try:
        analyzer = RecruitEDA()
        analyzer.run_all()
    except Exception as e:
        print(f"[실행 오류] EDA 수행 중 에러 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
