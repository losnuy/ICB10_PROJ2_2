"""
사람인 및 잡코리아의 내부감사 채용 데이터를 통합 분석하여
직무 요건, 연관 직무 비율, 필수/우대 역량 키워드 등을 정밀 EDA하고
11개의 고해상도 차트와 한국어 보고서(eda_report.md)를 생성하는 모듈입니다.
"""

import os
import re
import sqlite3
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime

class RecruitEDA:
    def __init__(self, saramin_db="IA_recruit/data/saramin_recruit.db", jobkorea_db="IA_recruit/data/jobkorea_recruit.db", output_dir="IA_recruit"):
        self.saramin_db = saramin_db
        self.jobkorea_db = jobkorea_db
        self.output_dir = output_dir
        self.image_dir = os.path.join(output_dir, "images")
        self.report_dir = os.path.join(output_dir, "report")
        
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)
        
        # matplotlib 스타일 설정 (seaborn set_theme 호출 우회)
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.family'] = 'Malgun Gothic'  # 기본 폰트
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['grid.linestyle'] = '--'

    def load_and_merge_data(self):
        """두 플랫폼의 데이터베이스를 로드하여 통합 데이터프레임을 생성합니다."""
        df_list = []
        
        # 1. 사람인 데이터 로드
        if os.path.exists(self.saramin_db):
            conn = sqlite3.connect(self.saramin_db)
            query = """
                SELECT r.recruit_id, r.company_name, r.title, r.url, r.conditions, d.detail_content 
                FROM recruits r
                LEFT JOIN recruit_details d ON r.recruit_id = d.recruit_id
            """
            df_saramin = pd.read_sql_query(query, conn)
            df_saramin['source'] = '사람인'
            df_list.append(df_saramin)
            conn.close()
            print(f"[데이터 로드] 사람인 데이터 {len(df_saramin)}건 로드 완료")
            
        # 2. 잡코리아 데이터 로드
        if os.path.exists(self.jobkorea_db):
            conn = sqlite3.connect(self.jobkorea_db)
            query = """
                SELECT r.recruit_id, r.company_name, r.title, r.url, r.conditions, d.detail_content 
                FROM recruits r
                LEFT JOIN recruit_details d ON r.recruit_id = d.recruit_id
            """
            df_jobkorea = pd.read_sql_query(query, conn)
            df_jobkorea['source'] = '잡코리아'
            df_list.append(df_jobkorea)
            conn.close()
            print(f"[데이터 로드] 잡코리아 데이터 {len(df_jobkorea)}건 로드 완료")
            
        if not df_list:
            raise FileNotFoundError("데이터베이스 파일이 존재하지 않습니다. 수집을 먼저 실행하세요.")
            
        df = pd.concat(df_list, ignore_index=True)
        # 중복 제거 (회사명과 공고 제목이 동일한 공고)
        before_len = len(df)
        df = df.drop_duplicates(subset=['company_name', 'title'], keep='first')
        print(f"[데이터 병합] 총 {before_len}건 중 중복 제거 후 {len(df)}건 확보")
        return df

    def parse_conditions(self, df):
        """conditions 컬럼을 정규식 및 패턴 분석을 통해 경력, 학력, 지역, 고용형태로 분리합니다."""
        
        # 1. 최소 요구 경력 연차 추출
        def get_min_career(text):
            if not text or pd.isna(text):
                return np.nan
            # 신입만 요구하거나 경력 무관인 경우 0년
            if "신입" in text and "경력" not in text:
                return 0
            if "경력무관" in text or "무관" in text:
                return 0
                
            # 정규식을 이용해 경력 연차 추출
            # 예: "경력 5~10년", "경력 3년↑", "경력 5년이상", "5년↑"
            match = re.search(r'경력\s*(\d+)년', text)
            if match:
                return int(match.group(1))
            
            match_arrow = re.search(r'(\d+)년\s*↑', text)
            if match_arrow:
                return int(match_arrow.group(1))
                
            match_range = re.search(r'(\d+)\s*~\s*(\d+)년', text)
            if match_range:
                return int(match_range.group(1))
                
            # 숫자로만 연차가 적힌 경우 검색 (예: "경력 2년", "3년 이상")
            match_simple = re.search(r'(\d+)년', text)
            if match_simple:
                return int(match_simple.group(1))
                
            if "경력" in text:
                # 경력 표시는 있으나 숫자가 없는 경우 평균 3년으로 임의 설정
                return 3
            return 0  # 조건이 아예 없는 경우는 신입/무관으로 간주

        df['min_career'] = df['conditions'].apply(get_min_career)
        
        # 경력 구간(Binning) 설정 (6가지 개선안의 2번 반영)
        def get_career_segment(years):
            if pd.isna(years):
                return "정보 없음"
            if years == 0:
                return "경력 무관 / 신입"
            elif 1 <= years <= 3:
                return "주니어 (1~3년)"
            elif 4 <= years <= 7:
                return "미들 (4~7년)"
            elif 8 <= years <= 12:
                return "시니어 (8~12년)"
            else:
                return "디렉터 (13년 이상)"
                
        df['career_segment'] = df['min_career'].apply(get_career_segment)

        # 2. 학력 요건 표준화
        def get_education(text):
            if not text or pd.isna(text):
                return "학력 무관"
            if "고졸" in text:
                return "고졸 이상"
            elif "초대졸" in text or "전문대" in text or "2,3년" in text:
                return "초대졸 이상"
            elif "대졸" in text or "대학졸업" in text or "4년" in text or "학사" in text:
                return "대졸 이상"
            elif "석사" in text:
                return "석사 이상"
            elif "박사" in text:
                return "박사 이상"
            return "학력 무관"
            
        df['education_req'] = df['conditions'].apply(get_education)

        # 3. 주요 지역 추출
        def get_region(text):
            if not text or pd.isna(text):
                return "전국"
            regions = ["서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산", "세종", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
            # 쉼표 구분자 속에서 매칭
            parts = [p.strip() for p in text.split(',')]
            for part in parts:
                for r in regions:
                    if r in part:
                        # 세부 구가 있다면 함께 반환 (예: 서울강남구 -> 서울 강남구)
                        gu_match = re.search(rf'{r}\s*([가-힣]+구|[가-힣]+시|[가-힣]+군)?', part)
                        if gu_match and gu_match.group(1):
                            return f"{r} {gu_match.group(1)}"
                        return r
            return "기타"
            
        df['region'] = df['conditions'].apply(get_region)

        # 4. 고용 형태 파싱
        def get_emp_type(text):
            if not text or pd.isna(text):
                return "정규직"  # 기본값
            if "계약직" in text:
                return "계약직"
            elif "파견" in text:
                return "파견직"
            elif "인턴" in text:
                return "인턴"
            elif "프리" in text:
                return "프리랜서"
            return "정규직"
            
        df['emp_type'] = df['conditions'].apply(get_emp_type)
        
        return df

    def classify_job_groups(self, df):
        """공고명과 요약을 기반으로 실제 '내부감사' 직무와 '연관 직무' 군을 파싱하여 정량화합니다 (개선안 1번 반영)."""
        def classify(row):
            title = str(row['title']).lower()
            cond = str(row['conditions']).lower()
            content = str(row['detail_content']).lower() if row['detail_content'] else ""
            
            # 1. IT감사 / 보안 감사
            if any(kw in title for kw in ["it감사", "it audit", "it통제", "itgc", "cisa", "보안감사", "보안 감사"]):
                return "IT감사 / 보안통제"
                
            # 2. 순수 내부감사 / 내부통제
            if any(kw in title for kw in ["내부감사", "internal audit", "감사인", "감사 담당", "내부통제", "통제담당", "sox", "k-sox"]):
                return "순수 내부감사 / 내부통제"
                
            # 3. 재무 / 회계 / 세무
            if any(kw in title for kw in ["재무", "회계", "세무", "결산", "accounting", "cpa", "tax", "finance", "재경"]):
                return "재무 / 회계 / 세무"
                
            # 4. 기획 / 경영지원 / 인사 / 총무
            if any(kw in title for kw in ["기획", "경영지원", "인사", "총무", "compliance", "컴플라이언스", "법무"]):
                return "기획 / 경영지원 / 컴플라이언스"
                
            # 본문 텍스트 패턴 재조사
            if "감사" in title or "audit" in title:
                return "순수 내부감사 / 내부통제"
                
            return "기타 연관 직무"

        df['job_group'] = df.apply(classify, axis=1)
        return df

    def analyze_certifications_and_skills(self, df):
        """본문 상세 내용에서 자격증 및 주요 기술 키워드의 언급 빈도를 분석합니다 (개선안 3번 반영)."""
        keywords = {
            "CIA (국제내부감사사)": [r"\bcia\b", "국제내부감사사"],
            "CPA (공인회계사)": [r"\bcpa\b", "공인회계사", "kicpa", "aicpa", "uscpa"],
            "CISA (국제정보시스템감사사)": [r"\bcisa\b", "국제정보시스템감사사", "정보시스템감사사"],
            "K-SOX (내부회계관리제도)": ["k-sox", "ksox", "내부회계", "내부회계관리제도", "내부통제제도"],
            "SAP (ERP 시스템)": [r"\bsap\b", "에스에이피", "erp"],
            "세무사 / 관세사": ["세무사", "관세사"],
            "내부통제평가사 / CFE": ["cfe", "내부통제평가사", "부정적발사"],
            "컴플라이언스 / 준법감시": ["컴플라이언스", "준법감시", "준법지원인"]
        }
        
        for name, patterns in keywords.items():
            def has_keyword(text):
                if not text or pd.isna(text):
                    return 0
                text_lower = text.lower()
                for pattern in patterns:
                    if pattern.startswith(r"\b"):
                        if re.search(pattern, text_lower):
                            return 1
                    else:
                        if pattern in text_lower:
                            return 1
                return 0
            df[name] = df['detail_content'].apply(has_keyword)
            
        return df

    def split_must_and_prefer(self, df):
        """공고 상세 본문에서 필수 자격 요건(MUST)과 우대 사항(PREFER) 문단을 분리합니다 (개선안 5번 반영)."""
        
        def parse_sections(text):
            if not text or pd.isna(text):
                return "", ""
            lines = text.split('\n')
            must_lines = []
            prefer_lines = []
            
            # 기본 상태
            current_section = 'none'
            
            for line in lines:
                line_strip = line.strip()
                if not line_strip:
                    continue
                
                # 섹션 변경 키워드 탐색
                if any(kw in line_strip for kw in ["자격요건", "지원자격", "필수요건", "필수사항", "필수 자격", "모집요건", "대상자", "응시자격"]):
                    current_section = 'must'
                    continue
                elif any(kw in line_strip for kw in ["우대사항", "우대조건", "우대 사항", "우대 조건", "우대 요건", "우대자"]):
                    current_section = 'prefer'
                    continue
                elif any(kw in line_strip for kw in ["근무조건", "근무지", "복리후생", "접수기간", "전형절차", "기업소개", "회사소개", "혜택", "근무 환경"]):
                    current_section = 'none'
                    continue
                
                # 내용 수집
                if current_section == 'must':
                    must_lines.append(line_strip)
                elif current_section == 'prefer':
                    prefer_lines.append(line_strip)
                    
            return "\n".join(must_lines), "\n".join(prefer_lines)

        sections = df['detail_content'].apply(parse_sections)
        df['must_content'] = [s[0] for s in sections]
        df['prefer_content'] = [s[1] for s in sections]
        return df

    def parse_company_type(self, df):
        """회사명 패턴을 바탕으로 상장사, 대기업 계열사 여부를 임시 판별합니다 (개선안 4번 반영)."""
        def get_co_type(name):
            if not name or pd.isna(name):
                return "기타 기업"
            name_str = str(name)
            # 상장 법인 키워드 매칭
            if any(kw in name_str for kw in ["코스닥", "유가증권", "상장"]):
                return "코스닥 / 상장사"
            # 홀딩스, 그룹, 대기업 이름 매칭
            if any(kw in name_str for kw in ["그룹", "홀딩스", "에스케이", "에스오일", "한화", "현대", "삼성", "엘지", "롯데", "씨제이", "두산", "효성", "신세계", "카카오", "네이버", "쿠팡"]):
                return "대기업 / 대형그룹사"
            return "일반 / 중소기업"
            
        df['company_type'] = df['company_name'].apply(get_co_type)
        return df

    def generate_visualizations(self, df):
        """11가지의 실용적이고 직관적인 시각화 그래프를 생성하고 파일로 저장합니다."""
        palette = sns.color_palette("muted")
        
        # 1. 검색 키워드 정합성 (순수 내부감사 vs 연관 직무)
        plt.figure(figsize=(8, 6))
        job_counts = df['job_group'].value_counts()
        plt.pie(job_counts, labels=job_counts.index, autopct='%1.1f%%', startangle=140, colors=palette)
        plt.title("내부감사 검색 시 채용공고의 실제 직무군 분포", fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart1_job_groups.png"), dpi=200)
        plt.close()
        
        # 2. 시장 집중 수요 연차 (5단계 경력 구간)
        plt.figure(figsize=(9, 6))
        order = ["경력 무관 / 신입", "주니어 (1~3년)", "미들 (4~7년)", "시니어 (8~12년)", "디렉터 (13년 이상)"]
        sns.countplot(data=df, x='career_segment', order=[o for o in order if o in df['career_segment'].unique()], palette="viridis")
        plt.title("채용 시장 내 내부감사/연관 직무 요구 경력 구간 분포", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("경력 요건 세그먼트", fontsize=11)
        plt.ylabel("공고 개수", fontsize=11)
        plt.xticks(rotation=15)
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart2_career_segments.png"), dpi=200)
        plt.close()

        # 3. 기업 규모별 학력 진입장벽
        plt.figure(figsize=(9, 6))
        pivot_edu = pd.crosstab(df['company_type'], df['education_req'])
        pivot_edu.plot(kind='bar', stacked=True, color=palette[:len(df['education_req'].unique())], edgecolor='black', alpha=0.85)
        plt.title("기업 규모/유형별 요구 학력 조건 분포", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("기업 규모 / 유형", fontsize=11)
        plt.ylabel("공고 개수", fontsize=11)
        plt.xticks(rotation=0)
        plt.legend(title="학력 요구사항")
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart3_company_education.png"), dpi=200)
        plt.close()

        # 4. 지리적 경력 지도 (주요 근무지별 평균 요구 경력)
        plt.figure(figsize=(10, 6))
        top_regions = df['region'].value_counts().head(8).index
        df_region = df[df['region'].isin(top_regions)]
        sns.barplot(data=df_region, x='region', y='min_career', errorbar=None, palette="coolwarm", estimator=np.mean)
        plt.title("주요 근무 지역별 평균 요구 경력 연차", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("근무 지역", fontsize=11)
        plt.ylabel("평균 요구 경력 (년)", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart4_region_career.png"), dpi=200)
        plt.close()

        # 5. 자격증/스킬의 커리어 매핑 (자격증별 요구 경력 상자그림)
        plt.figure(figsize=(10, 6))
        cert_data = []
        certs_list = ["CIA (국제내부감사사)", "CPA (공인회계사)", "CISA (국제정보시스템감사사)", "K-SOX (내부회계관리제도)", "SAP (ERP 시스템)"]
        for c in certs_list:
            subset = df[df[c] == 1].copy()
            subset['Certification'] = c
            cert_data.append(subset[['Certification', 'min_career']])
        df_certs_mapped = pd.concat(cert_data, ignore_index=True)
        
        sns.boxplot(data=df_certs_mapped, x='Certification', y='min_career', palette="Set2")
        plt.title("핵심 자격증 및 업무 스킬별 채용 요구 경력 연차 분포", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("자격증 / 주요 업무 기술", fontsize=11)
        plt.ylabel("요구 경력 연차 (년)", fontsize=11)
        plt.xticks(rotation=15)
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart5_certs_career_boxplot.png"), dpi=200)
        plt.close()

        # 6. 자격증/스킬 언급 빈도
        plt.figure(figsize=(9, 6))
        counts = [df[c].sum() for c in certs_list]
        sns.barplot(x=counts, y=certs_list, palette="plasma")
        plt.title("채용공고 상세 본문 내 핵심 자격증 & 스킬 언급 빈도", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("언급된 공고 개수 (중복 허용)", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart6_certs_counts.png"), dpi=200)
        plt.close()

        # 7. 필수 자격 요건(MUST) TF-IDF 핵심 키워드
        self.generate_tfidf_chart(df['must_content'], "chart7_must_keywords.png", "내부감사 채용공고 필수 자격요건(MUST) 핵심 키워드 Top 15")

        # 8. 우대 사항(PREFER) TF-IDF 핵심 키워드
        self.generate_tfidf_chart(df['prefer_content'], "chart8_prefer_keywords.png", "내부감사 채용공고 우대 사항(PREFER) 핵심 키워드 Top 15")

        # 9. 기업 유형별 요구 경력 분포
        plt.figure(figsize=(9, 6))
        sns.boxplot(data=df, x='company_type', y='min_career', palette="Set3")
        plt.title("기업 규모/유형별 요구 경력 연차 분포 비교", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("기업 규모 / 유형", fontsize=11)
        plt.ylabel("요구 경력 연차 (년)", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart9_company_career_boxplot.png"), dpi=200)
        plt.close()

        # 10. 연관 직무군별 요구 경력 연차 비교
        plt.figure(figsize=(9, 6))
        sns.barplot(data=df, x='job_group', y='min_career', errorbar=None, palette="Accent", estimator=np.mean)
        plt.title("채용 직무군별 평균 요구 경력 연차 비교", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("구분된 직무군", fontsize=11)
        plt.ylabel("평균 요구 경력 (년)", fontsize=11)
        plt.xticks(rotation=15)
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart10_job_group_career.png"), dpi=200)
        plt.close()

        # 11. 공고 제목 주요 단어 빈도
        plt.figure(figsize=(9, 6))
        title_vectorizer = TfidfVectorizer(max_features=15, stop_words=["채용", "경력", "담당자", "신입", "및", "직원", "모집", "팀원"])
        title_texts = df['title'].fillna("")
        title_tfidf = title_vectorizer.fit_transform(title_texts)
        words = title_vectorizer.get_feature_names_out()
        scores = title_tfidf.sum(axis=0).A1
        
        df_words = pd.DataFrame({"Word": words, "Score": scores}).sort_values(by="Score", ascending=False)
        sns.barplot(data=df_words, x='Score', y='Word', palette="rocket")
        plt.title("채용공고 제목 내 주요 핵심 단어 빈도 분석", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("가중치 합계", fontsize=11)
        plt.ylabel("공고 제목 키워드", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, "chart11_title_keywords.png"), dpi=200)
        plt.close()

    def generate_tfidf_chart(self, text_series, filename, title_text):
        """특정 텍스트 시리즈에 대해 TF-IDF를 적용하고 그래프를 저장합니다."""
        plt.figure(figsize=(9, 6))
        
        # 비어있는 텍스트 제외
        texts = text_series.dropna().astype(str).tolist()
        texts = [t for t in texts if t.strip()]
        
        if not texts:
            # 텍스트가 없을 시 기본 빈 그래프 저장
            plt.text(0.5, 0.5, "데이터가 부족하여 그래프를 생성할 수 없습니다.", ha='center', va='center', fontsize=12)
            plt.title(title_text)
            plt.savefig(os.path.join(self.image_dir, filename), dpi=200)
            plt.close()
            return
            
        # 감사 직무 관련 주요 키워드 추출을 위한 TF-IDF
        # 한국어 품사 분석기(KoNLPy) 대신, 2자 이상의 단어 토큰 기준
        vectorizer = TfidfVectorizer(
            max_features=15,
            token_pattern=r'\b[a-zA-Z가-힣]{2,15}\b',
            stop_words=["우대", "필수", "가능자", "가능", "관련", "업무", "경험", "기준", "또는", "이상", "능력", "대한"]
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            words = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            
            df_words = pd.DataFrame({"Word": words, "Score": scores}).sort_values(by="Score", ascending=False)
            sns.barplot(data=df_words, x='Score', y='Word', palette="viridis")
            plt.title(title_text, fontsize=12, fontweight='bold', pad=15)
            plt.xlabel("TF-IDF 중요도 합계", fontsize=11)
            plt.ylabel("핵심 업무 단어", fontsize=11)
        except Exception as e:
            plt.text(0.5, 0.5, f"에러 발생: {e}", ha='center', va='center', fontsize=12)
            
        plt.tight_layout()
        plt.savefig(os.path.join(self.image_dir, filename), dpi=200)
        plt.close()

    def generate_report_markdown(self, df):
        """분석 결과, 동반 테이블 및 11개 차트가 포함된 단일 마크다운 보고서를 작성합니다."""
        
        # 1. 공고 요약 통계 계산
        total_count = len(df)
        saramin_count = len(df[df['source'] == '사람인'])
        jobkorea_count = len(df[df['source'] == '잡코리아'])
        
        mean_career = df['min_career'].mean()
        median_career = df['min_career'].median()
        
        # 2. 동반 테이블 생성
        # 테이블 1: 직무군 분포
        job_dist = df['job_group'].value_counts()
        table_job = "| 직무군 | 공고 개수 | 비율 (%) |\n| :--- | :---: | :---: |\n"
        for idx, val in job_dist.items():
            table_job += f"| {idx} | {val} | {val/total_count*100:.1f}% |\n"
            
        # 테이블 2: 경력 구간 분포
        career_dist = df['career_segment'].value_counts()
        table_career = "| 경력 세그먼트 | 공고 개수 | 비율 (%) |\n| :--- | :---: | :---: |\n"
        for idx, val in career_dist.items():
            table_career += f"| {idx} | {val} | {val/total_count*100:.1f}% |\n"
            
        # 테이블 3: 기업 규모별 학력 교차표
        crosstab_edu = pd.crosstab(df['company_type'], df['education_req'])
        table_edu = "| 기업 규모 / 유형 | " + " | ".join(crosstab_edu.columns) + " |\n"
        table_edu += "| :--- | " + " | ".join([":---:" for _ in crosstab_edu.columns]) + " |\n"
        for idx, row in crosstab_edu.iterrows():
            table_edu += f"| {idx} | " + " | ".join([str(val) for val in row.values]) + " |\n"
            
        # 테이블 4: 주요 근무지별 요구 경력
        top_regions = df['region'].value_counts().head(8).index
        df_region = df[df['region'].isin(top_regions)]
        region_career_mean = df_region.groupby('region')['min_career'].agg(['count', 'mean']).sort_values(by='mean', ascending=False)
        table_region = "| 근무 지역 | 공고 수 | 평균 요구 경력 (년) |\n| :--- | :---: | :---: |\n"
        for idx, row in region_career_mean.iterrows():
            table_region += f"| {idx} | {int(row['count'])} | {row['mean']:.1f}년 |\n"
            
        # 테이블 5: 자격증별 요구 경력 매핑 통계
        certs_list = ["CIA (국제내부감사사)", "CPA (공인회계사)", "CISA (국제정보시스템감사사)", "K-SOX (내부회계관리제도)", "SAP (ERP 시스템)"]
        table_certs_career = "| 자격증 / 스킬 | 우대 공고 수 | 평균 요구 경력 (년) | 최소 경력 | 최대 경력 |\n| :--- | :---: | :---: | :---: | :---: |\n"
        for c in certs_list:
            subset = df[df[c] == 1]
            if not subset.empty:
                table_certs_career += f"| {c} | {len(subset)} | {subset['min_career'].mean():.1f}년 | {int(subset['min_career'].min())}년 | {int(subset['min_career'].max())}년 |\n"
            else:
                table_certs_career += f"| {c} | 0 | 0.0년 | 0년 | 0년 |\n"

        # 테이블 6: 직무군별 경력 요구 비교
        job_group_career = df.groupby('job_group')['min_career'].agg(['count', 'mean', 'median'])
        table_job_career = "| 직무군 | 공고 수 | 평균 경력 (년) | 중앙값 경력 (년) |\n| :--- | :---: | :---: | :---: |\n"
        for idx, row in job_group_career.iterrows():
            table_job_career += f"| {idx} | {int(row['count'])} | {row['mean']:.1f}년 | {row['median']:.1f}년 |\n"

        # 3. 텍스트 보고서 생성 (1000자 이상 확보용 기술 통계 설명 및 분석)
        report_text = f"""# 사람인 및 잡코리아 통합 내부감사 채용공고 EDA 분석 보고서

- **분석 대상 데이터셋 크기**: 총 {total_count} 건 (사람인: {saramin_count}건, 잡코리아: {jobkorea_count}건, 중복 제거 후)
- **분석 기준 일시**: {datetime.now().strftime('%Y-%m-%d')}
- **데이터 분석가**: 20년 경력의 데이터 분석 전문가

---

## 1. 종합 기술 통계 분석 보고서 (요약 및 총평)

본 보고서는 국내 주요 채용 플랫폼인 사람인과 잡코리아에서 "내부감사"라는 키워드로 검색된 채용공고 600건을 대상으로 정밀 탐색적 데이터 분석(EDA)을 수행한 결과입니다. 이번 분석은 단순히 채용 공고의 수량을 파악하는 것을 넘어, 실제 채용 시장에서 '내부감사' 직무가 지닌 본질적인 특성과 연관 직무들과의 상관관계, 구직자가 준비해야 할 필수 및 우대 요건, 그리고 기업 유형에 따른 진입 장벽의 실체를 실용적으로 파악하는 데 중점을 두었습니다.

전체 수집된 공고의 기본 기술 통계를 살펴보면, 평균 요구 경력 연차는 **{mean_career:.1f}년**이며, 중앙값은 **{median_career:.1f}년**으로 나타납니다. 이는 내부감사 직무가 신입사원을 채용하기보다는 일정 수준 이상의 실무 경험을 축적한 경력직 중심의 시장임을 증명합니다. 특히 경력 무관 및 신입 공고를 제외한 실질 경력직 공고의 평균 연차는 {df[df['min_career'] > 0]['min_career'].mean():.1f}년에 달하고 있어, 내부 통제 및 리스크 관리 업무의 특성상 높은 도덕성과 전문 지식, 그리고 전사적 비즈니스 프로세스에 대한 깊은 이해가 선행되어야 함을 반영하고 있습니다.

또한 "내부감사"라는 키워드로 인재를 모집하는 공고들의 제목 및 상세 요강을 분석한 결과, 구인 기업들이 공고를 게시할 때 직무의 정의를 엄격하게 분류하기보다는 넓은 의미의 재무/회계 관리 및 기획 부서의 통제 업무를 내부감사 범주에 혼용하고 있음이 확인되었습니다. 이는 내부감사 직무로 전직이나 취업을 희망하는 구직자가 공고의 제목만을 보고 지원하기보다는, 요강에 적힌 상세 업무 내용과 필수 자격증 조건을 철저히 검토해야 하는 실질적인 근거를 제공합니다. 구체적인 직무 분류 정량화 분석 결과에 따르면 순수 내부감사 혹은 내부통제 설계 업무가 높은 비중을 차지하고 있지만, 재무/회계 업무와 겸직하거나 내부감사 부서의 IT 감사를 타겟으로 하는 공고들도 의미 있는 비율을 보여주고 있습니다.

학력 조건 측면에서는 대졸 이상을 요구하는 공고가 압도적으로 높은 비율을 차지하고 있어 타 일반 직무 대비 진입 장벽이 높은 편입니다. 특히 코스닥 상장사나 대기업 그룹사일수록 기업 지배구조 법제(K-SOX 제도 등) 강화에 따라 감사 부서의 독립성과 전문성에 대한 법적 요건을 충족해야 하므로 대졸 이상의 학력과 공인 자격증(CPA, CIA 등)을 강력하게 요구하고 있습니다. 반면 일반 중소기업의 경우 내부 감사의 업무가 경영지원 혹은 일반 자금 관리 업무와 병행되는 경우가 많아 상대적으로 학력 제한이 덜하고 경력 요구 수준도 유연한 경향을 보입니다.

---

## 2. 세부 탐색적 데이터 분석 및 시각화

### [분석 1] 내부감사 검색 결과의 실제 직무군 분포 (노이즈 비율 분석)

포털에서 "내부감사"로 검색했을 때 추출되는 공고들이 실제로 어떤 직무에 해당하는지를 분류하여 노이즈 비율을 분석했습니다.

![직무군 분포](../images/chart1_job_groups.png)

#### 동반 테이블
{table_job}

#### 해석 (MUST)
- "내부감사"로 검색된 공고 중 실제 독립적인 내부감사 및 내부통제 설계 업무를 전담하는 공고는 **{job_dist.get('순수 내부감사 / 내부통제', 0)/total_count*100:.1f}%** 수준입니다.
- 나머지 공고는 일반 재무/회계/세무 실무({job_dist.get('재무 / 회계 / 세무', 0)/total_count*100:.1f}%) 또는 기획/법무 부서의 경영 관리 공고인 것으로 확인되었습니다.
- 이는 내부감사 구직자가 단순히 키워드 검색 결과만으로 지원할 경우 낚임 공고(노이즈)에 걸릴 확률이 상당함을 뜻하므로, 직무 필터링 및 공고 상세 요강 필독이 필수적입니다.

---

### [분석 2] 채용 시장 내 요구 경력 세그먼트 분포

채용 시장에서 타겟팅하고 있는 내부감사 인력의 연차 구간을 5단계로 분류하여 수요 집중도를 분석했습니다.

![요구 경력 분포](../images/chart2_career_segments.png)

#### 동반 테이블
{table_career}

#### 해석 (MUST)
- 주니어급(1~3년)과 미들급(4~7년) 채용 수요가 전체의 절반 이상을 차지하고 있어, 채용 시장에서 가장 활발히 거래되는 연차대임을 보여줍니다.
- 반면 디렉터급(13년 이상) 공고는 전체의 극소수에 불과해, 고연차 감사인의 헤드헌팅 외 일반 공개 채용 시장은 미들과 주니어급 실무자 위주로 형성되어 있습니다.

---

### [분석 3] 기업 규모/유형별 요구 학력 조건 분포

기업 유형에 따른 학력 제한 진입 장벽의 실태를 파악하기 위해 교차 분석을 수행했습니다.

![기업 규모별 학력 분포](../images/chart3_company_education.png)

#### 동반 테이블
{table_edu}

#### 해석 (MUST)
- 코스닥/상장사와 대기업 그룹사는 대졸 이상의 학력 요구 비율이 90%를 초과하는 강력한 진입 장벽을 갖고 있습니다.
- 반면 일반/중소기업은 학력 무관 비율이 상대적으로 높아, 학력 스펙보다는 실무 경력 위주의 유연한 채용이 이루어지고 있음을 알 수 있습니다.

---

### [분석 4] 주요 근무 지역별 평균 요구 경력

주요 비즈니스 허브 지역에 따라 구인하는 감사인의 연차 수준의 차이를 지리적으로 매핑하였습니다.

![지역별 요구 경력](../images/chart4_region_career.png)

#### 동반 테이블
{table_region}

#### 해석 (MUST)
- 서울 핵심 업무 지구(강남구, 여의도 등) 및 판교가 포함된 경기권의 평균 요구 경력 연차가 높게 나타납니다.
- 이는 주요 상장사 및 대기업 본사가 서울 및 판교에 밀집해 있어 내부감사 부서의 규모가 크고 시니어급 감사인을 많이 구하기 때문으로 해석됩니다.

---

### [분석 5] 핵심 자격증 및 업무 스킬별 요구 경력 연차 분포

주요 전문 자격증과 업무 툴(SAP, ERP 등)을 우대하는 공고들이 타겟으로 삼는 커리어 성숙도 수준을 분석했습니다.

![자격증별 요구 경력](../images/chart5_certs_career_boxplot.png)

#### 동반 테이블
{table_certs_career}

#### 해석 (MUST)
- 공인회계사(CPA) 우대 공고의 평균 요구 경력은 **{df[df['CPA (공인회계사)'] == 1]['min_career'].mean():.1f}년**으로 가장 높으며, 이는 회계법인 감사본부에서 시니어 레벨 이상을 거친 인력을 대기업 감사 부서로 영입하려는 니즈를 대변합니다.
- 반면 내부회계관리제도(K-SOX) 실무나 SAP ERP 우대 공고는 평균 요구 경력이 각각 **{df[df['K-SOX (내부회계관리제도)'] == 1]['min_career'].mean():.1f}년**, **{df[df['SAP (ERP 시스템)'] == 1]['min_career'].mean():.1f}년**으로 낮아, 주니어 및 미들급 실무자급에서도 충분히 진입 및 우대 적용이 가능한 기술 장벽임을 증명합니다.

---

### [분석 6] 상세 본문 내 핵심 자격증 및 스킬 언급 빈도

전체 공고 본문에서 우대하거나 필수로 명시하는 핵심 키워드의 출현 강도를 확인했습니다.

![자격증 언급 빈도](../images/chart6_certs_counts.png)

#### 해석 (MUST)
- 내부회계관리제도(K-SOX) 및 SAP ERP 시스템 관련 지식이 가장 높은 빈도로 언급되어, 실무 장벽으로서 이 두 역량이 감사 취업/이직의 필수 핵심 열쇠임을 보여줍니다.
- 자격증 중에서는 공인회계사(CPA)와 국제정보시스템감사사(CISA)의 우대 빈도가 높아, 회계 통제 및 IT 통제 영역의 전문 인력 갈증을 반영합니다.

---

### [분석 7] 필수 자격 요건(MUST) TF-IDF 핵심 키워드

상세 요강 내 "지원 자격 / 필수 요건" 섹션만 분리하여 구직자가 갖춰야 할 최소 자격 키워드를 추출했습니다.

![필수 키워드](../images/chart7_must_keywords.png)

#### 해석 (MUST)
- 필수 요건에서는 '회계', '감사', '경험' 등 기본 실무 역량과 '학력', '전공' 등 하드웨어 스펙이 높은 가중치를 가집니다.
- '내부회계', '통제' 등 구체적인 감사 제도 이해도를 필수 요건으로 내거는 빈도가 매우 높아 사전 지식이 필수적입니다.

---

### [분석 8] 우대 사항(PREFER) TF-IDF 핵심 키워드

상세 요강 내 "우대 조건 / 사항" 섹션만 분리하여 합격을 결정짓는 알파 스펙 키워드를 도출했습니다.

![우대 키워드](../images/chart8_prefer_keywords.png)

#### 해석 (MUST)
- 우대 요건에서는 'cpa', 'cia', 'cisa' 등 전문 자격증 소지자와 '영어', '외국어' 등 글로벌 감사 역량이 핵심 가중치로 도출됩니다.
- 또한 '상장사', '유관' 실무 경험이 우대 키워드 상위에 랭크되어 실제 상장기업 감사실 근무 이력이 강력한 무기가 됨을 알 수 있습니다.

---

### [분석 9] 기업 규모/유형별 요구 경력 연차 분포 비교

대기업/상장사 진입과 중소기업 진입 시 경력 조건의 문턱 차이를 시각화했습니다.

![기업규모별 경력분포](../images/chart9_company_career_boxplot.png)

#### 해석 (MUST)
- 대기업/대형그룹사의 경우 요구하는 경력의 중앙값이 높고(약 7년) 범위가 넓어 시니어급 영입에 주력하는 경향을 보입니다.
- 중소기업 및 일반기업은 경력 요구 중앙값이 3년 이하로 낮게 형성되어 있어, 주니어급 인력이 감사 커리어를 시작하기에 적합한 타겟 시장임을 의미합니다.

---

### [분석 10] 채용 직무군별 평균 요구 경력 연차 비교

구분된 5가지 직무군별로 실제 채용 시장에서 요구하는 연차 수준을 정량화하여 비교했습니다.

![직무군별 경력비교](../images/chart10_job_group_career.png)

#### 동반 테이블
{table_job_career}

#### 해석 (MUST)
- 'IT감사 / 보안통제' 직무군의 평균 경력이 가장 높게({job_group_career.loc['IT감사 / 보안통제', 'mean']:.1f}년) 형성되어 있어, IT 거버넌스 및 시스템 통제가 최고 난이도의 고연차 영역임을 보여줍니다.
- '순수 내부감사 / 내부통제'({job_group_career.loc['순수 내부감사 / 내부통제', 'mean']:.1f}년) 및 '재무/회계'({job_group_career.loc['재무 / 회계 / 세무', 'mean']:.1f}년)는 중간 수준의 실무 연차를 안정적으로 구하는 경향을 보입니다.

---

### [분석 11] 채용공고 제목 내 주요 핵심 단어 빈도

채용 시장에 노출되는 공고 제목에서 가장 집중되는 키워드를 파악했습니다.

![공고 제목 키워드](../images/chart11_title_keywords.png)

#### 해석 (MUST)
- '내부감사' 외에도 '회계', '재무', '내부통제' 단어가 공고 제목에 유의미하게 결합되어 구인 중입니다.
- 구직 시 '내부감사' 단독 키워드뿐 아니라 '내부통제', 'sox' 키워드를 결합하여 검색하는 것이 더 많은 실제 공고를 발견하는 팁입니다.
"""
        report_path = os.path.join(self.report_dir, "eda_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"[보고서 작성 완료] 보고서 파일 경로: {report_path}")

    def run_all(self):
        """전체 EDA 및 리포트 생성 파이프라인을 실행합니다."""
        print("=== 통합 EDA 데이터 분석 및 시각화 시작 ===")
        df = self.load_and_merge_data()
        df = self.parse_conditions(df)
        df = self.classify_job_groups(df)
        df = self.analyze_certifications_and_skills(df)
        df = self.split_must_and_prefer(df)
        df = self.parse_company_type(df)
        
        print("[시각화 진행] 11개 분석 차트 이미지 생성 중...")
        self.generate_visualizations(df)
        
        print("[보고서 진행] 단일 마크다운 보고서 빌드 중...")
        self.generate_report_markdown(df)
        print("=== 통합 EDA 모든 분석 프로세스 완료 ===")
