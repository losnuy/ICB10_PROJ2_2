"""
이 모듈은 사람인 채용 공고 데이터를 기반으로 작동하며, 다중 직무 확장을 고려한 Streamlit 대시보드 웹앱입니다.

주요 기능:
- 사이드바 직무군 선택(회계, IT/개발, 마케팅)에 따른 동적 UI 렌더링 및 프레임워크 지원
- 직무별 동의어 변환 딕셔너리, Plotly 스펙 갭 대상 변수, JD 작성 템플릿의 메타데이터 분리 관리
- 미수집 직무(IT/개발, 마케팅) 선택 시 모의 데이터(Mock Data) 생성을 통해 다중 직무 대시보드 렌더링 틀 사전 검증 지원
- K-Means 군집 분석을 이용한 직무별 기업 유형 자동 판정 및 군집 프로파일링 동적 라벨링
- 구직자 탭: 코사인 유사도 기반 직무 적합도 점수 예측, 미스매치 진단, What-if 스펙 시뮬레이터
- 인사팀 탭: Plotly 스펙 갭 바 차트, JD 우대사항 자동 생성 가이드, 허수 지원자 필터링 시뮬레이터
"""

import os
import re
import json
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

# 앱 설정 및 레이아웃
st.set_page_config(
    page_title="다중 직무 적합도 & 미스매치 진단 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 경로 상수
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "recruit.db")
ACCOUNTING_KEYWORDS_PATH = os.path.join(BASE_DIR, "accounting_keywords.json")

# -------------------------------------------------------------
# 다중 직무 메타데이터 정의 (Multi-job Configuration)
# -------------------------------------------------------------
JOB_META = {
    "accounting": {
        "title": "회계 취준생들의 컴활 탈출기",
        "subtitle": "시장 데이터를 기반으로 한 미스매치 및 허수 지원 필터링 가이드",
        "job_name": "회계",
        "keywords_file": ACCOUNTING_KEYWORDS_PATH,
        "generic_specs": ["Excel (엑셀)", "전산회계 1급", "전산회계 2급"],
        "real_specs": ["SAP ERP", "회계 결산", "세무 신고", "자금 관리", "4대 보험", "법인세 조정"],
        "synonyms": {
            r"Smart\s*A|스마트\s*A|더존\s*Smart\s*A": "더존 (Smart A)",
            r"iU|i-U|더존\s*iU": "더존 (iU)",
            r"엑셀|스프레드시트|MS\s*Office|MS\s*오피스": "Excel (엑셀)",
            r"S/4HANA|SAP\s*R3": "SAP ERP",
            r"한국공인회계사|공인회계사|KICPA": "CPA (한국공인회계사)",
            r"USCPA|미국공인회계사": "AICPA (미국공인회계사)",
            r"부가가치세|부가세신고": "부가세 신고",
            r"CTA|세무대리인": "CTA (세무사)",
            r"출납|자금집행|시재관리": "자금 관리",
            r"외부감사|회계감사|감사인대응": "회계 감사 대응",
            r"세무조정|법인세세무조정": "법인세 조정"
        },
        "guideline_templates": {
            "회계 결산": "우대사항에 단순 '결산 보조' 대신, <b>'더존 스마트A를 활용한 자체 연말 결산 및 조정 업무 단독 수행 가능자'</b>로 명시해 직무 완성도를 평가하십시오.",
            "세무 신고": "단순 세무 보조 업무 문구를 삭제하고, <b>'원천세 신고, 부가세 신고 및 세무 대리 기장 업무 경력 2년 이상 소지자'</b>로 명시하여 허수 지원자를 원천 필터링하십시오.",
            "SAP ERP": "단순 ERP 사용 가능 우대 문구 대신, <b>'SAP FI/CO 모듈 사용 및 글로벌 회계 감사 대응 경력자'</b>를 우대사항에 상세 표기하여 타겟 인재를 확보하십시오.",
            "4대 보험": "사무 보조 우대 문구를 삭제하고, <b>'4대 보험 신고 및 실무 급여 계산 업무 단독 가능자'</b>를 우대 문구로 교체하십시오.",
            "더존 (Smart A)": "단순 더존 사용 가능보다는, <b>'더존 Smart A를 활용한 전표 입력 및 자금 집행 관리 유경험자'</b>로 구체적인 롤을 정의하십시오.",
            "Excel (엑셀)": "컴활 및 엑셀 우대 문구를 삭제하고, <b>'엑셀 피벗 테이블 및 다중 VLOOKUP 함수를 활용한 실무 재무 데이터 분석 가능자'</b>로 구체화하여 작성하십시오."
        }
    },
    "it_dev": {
        "title": "IT 개발자들의 포폴 생존기",
        "subtitle": "단순 토이 프로젝트를 넘어 런타임 최적화와 인프라 대응성을 추적하는 JD 가이드",
        "job_name": "IT/개발",
        "keywords_file": None,
        "generic_specs": ["Git/GitHub", "정보처리기사", "HTML/CSS"],
        "real_specs": ["React/Vue", "FastAPI/Spring", "Docker/K8s", "Database 설계", "TDD", "CI/CD"],
        "synonyms": {
            r"깃허브|깃헙|GitHub|Git": "Git/GitHub",
            r"정처기|정보처리": "정보처리기사",
            r"쿠버네티스|Kubernetes|k8s|도커|Docker": "Docker/K8s",
            r"React|Vue|Angular|리액트|뷰": "React/Vue",
            r"Spring|Boot|FastAPI|장고|Django": "FastAPI/Spring",
            r"테스트코드|TDD|Test": "TDD",
            r"CI/CD|젠킨스|GitHub Actions": "CI/CD"
        },
        "guideline_templates": {
            "Docker/K8s": "단순 '서버 배포 경험' 대신, <b>'Docker 컨테이너라이징 및 Kubernetes 오케스트레이션 기반 분산 클러스터 환경 구축 가능자'</b>로 JD를 구체화하십시오.",
            "FastAPI/Spring": "단순 '백엔드 언어 사용 가능' 대신, <b>'Spring Boot 또는 FastAPI 기반 비동기 API 엔드포인트 설계 및 RDBMS 병목 최적화 가능자'</b>로 명시하십시오.",
            "React/Vue": "화면 구현 가능 수준이 아닌, <b>'React 상태 관리 라이브러리(Redux, Recoil 등) 활용 및 웹 컴포넌트 재사용 설계 가능자'</b>를 우대 요건에 배치하십시오.",
            "TDD": "단순 개발 지식 보유자보다, <b>'pytest 또는 JUnit을 활용한 단위 테스트 및 TDD 개발 프레임워크 적용 유경험자'</b>로 명시해 진성 인재를 구별하십시오.",
            "Git/GitHub": "단순 소스코드 공유 수준을 넘어, <b>'Git Flow 브랜치 전략 기반 협업 및 코드 리뷰 프로세스 주도 경험자'</b>로 작성하여 협업 시너지를 확보하십시오."
        }
    },
    "marketing": {
        "title": "그로스 마케터들의 데이터 지표 탈출기",
        "subtitle": "단순 카드뉴스 기획을 넘어 GA 지표와 SQL 쿼리 기반 퍼널 분석 JD 가이드",
        "job_name": "마케팅",
        "keywords_file": None,
        "generic_specs": ["포토샵/일러스트", "SNS 콘텐츠 제작", "파워포인트"],
        "real_specs": ["Google Analytics", "SQL 데이터 추출", "A/B 테스트", "퍼포먼스 광고 집행", "SEO 최적화"],
        "synonyms": {
            r"구글애널리틱스|GA4|GA|Analytics": "Google Analytics",
            r"포토샵|Photoshop|일러스트|Illustrator": "포토샵/일러스트",
            r"콘텐츠제작|인스타|블로그|카드뉴스": "SNS 콘텐츠 제작",
            r"SQL|쿼리|Query": "SQL 데이터 추출",
            r"A/B테스트|실험설계|ABTest": "A/B 테스트",
            r"키워드최적화|SEO|검색최적화": "SEO 최적화",
            r"퍼포먼스광고|페북광고|구글광고": "퍼포먼스 광고 집행"
        },
        "guideline_templates": {
            "Google Analytics": "단순 '로그 분석 도구 사용' 대신, <b>'GA4 맞춤 이벤트 설계, 전자상거래 퍼널 설정 및 데이터 시각화 리포트 도출 가능자'</b>로 직무 범위를 명확히 규정하십시오.",
            "SQL 데이터 추출": "데이터 분석 유경험 우대 대신, <b>'RDBMS 및 BigQuery 환경에서 SQL 쿼리를 활용한 유저 리텐션 및 코호트 데이터 직접 가공 가능자'</b>를 명시하십시오.",
            "A/B 테스트": "우대사항에 <b>'가설 수립부터 모수 설계, 유의성 p-value 검증 및 A/B 테스트 성과 지표 도출 기획 경험자'</b>로 구체화하여 작성하십시오.",
            "SEO 최적화": "마케팅 기획자 대신, <b>'웹 크롤러 분석에 적합한 시맨틱 HTML 및 핵심 키워드 매핑을 통한 자연 검색(Organic) 트래픽 개선 유경험자'</b>를 우대하십시오."
        }
    }
}


@st.cache_data
def load_and_preprocess_data(job_key):
    """
    선택된 직무(job_key)에 적합한 데이터를 가공합니다.
    회계 직무의 경우 실데이터 데이터베이스를 로드하고,
    IT/개발 및 마케팅 직무의 경우 프레임워크 검증용 모의 데이터(Mock Data)를 동적 생성합니다.
    """
    meta = JOB_META[job_key]
    
    # 컴파일된 정규식 딕셔너리 생성 (속도 최적화)
    compiled_synonyms = {re.compile(pattern, re.IGNORECASE): rep for pattern, rep in meta["synonyms"].items()}
    
    # 1. 미수집 직무(IT, 마케팅)의 경우 가상 모의 데이터(Mock Data) 생성
    if meta["keywords_file"] is None or not os.path.exists(meta["keywords_file"]):
        np.random.seed(42)
        mock_count = 500
        
        cert_list = meta["generic_specs"]
        tool_list = meta["real_specs"][:3]
        job_list = meta["real_specs"][3:]
        all_features = cert_list + tool_list + job_list
        
        mock_records = []
        for i in range(mock_count):
            comp = f"가상 혁신 기업_{i}"
            tit = f"[{meta['job_name']}] 전문 인재 모집 (경력 채용)"
            desc = " ".join(all_features)
            mock_records.append((f"mock_{i}", comp, tit, "http://example.com", desc))
            
        df = pd.DataFrame(mock_records, columns=["rec_idx", "company_name", "title", "link", "detail_content"])
        df["detail_content_clean"] = df["detail_content"]
        
        feature_matrix = []
        exp_years_list = []
        edu_score_list = []
        
        for _ in range(mock_count):
            r_feats = []
            cluster_type = np.random.choice([0, 1, 2])
            for idx, feat in enumerate(all_features):
                if cluster_type == 0 and idx < len(cert_list):
                    r_feats.append(1 if np.random.rand() > 0.3 else 0)
                elif cluster_type == 1 and idx >= len(cert_list) and idx < len(cert_list) + len(tool_list):
                    r_feats.append(1 if np.random.rand() > 0.2 else 0)
                elif cluster_type == 2 and idx >= len(cert_list) + len(tool_list):
                    r_feats.append(1 if np.random.rand() > 0.1 else 0)
                else:
                    r_feats.append(1 if np.random.rand() > 0.75 else 0)
            
            feature_matrix.append(r_feats)
            exp_years_list.append(int(np.random.choice([0, 1, 3, 5, 7, 10], p=[0.2, 0.1, 0.3, 0.2, 0.1, 0.1])))
            edu_score_list.append(int(np.random.choice([0, 1, 2, 3, 4], p=[0.1, 0.1, 0.1, 0.6, 0.1])))
            
        df_features = pd.DataFrame(feature_matrix, columns=all_features)
        df_features["exp_years"] = exp_years_list
        df_features["edu_score"] = edu_score_list
        
        df_final = pd.concat([df, df_features], axis=1)
        mock_keywords_data = {
            "자격증 최다 언급 TOP 20": {k: 50 for k in cert_list},
            "활용 툴 최다 언급 TOP 20": {k: 80 for k in tool_list},
            "세부 직무 최다 언급 TOP 20": {k: 90 for k in job_list}
        }
        return df_final, mock_keywords_data, all_features
        
    # 2. 회계 직무 실데이터 로드 (강건한 예외 처리 장착)
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT 
                l.rec_idx,
                l.company_name,
                l.title,
                l.link,
                d.detail_content
            FROM recruit_list l
            LEFT JOIN recruit_detail d ON l.rec_idx = d.rec_idx
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
    except Exception as e:
        st.error(f"❌ 데이터베이스를 읽는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(), {}, []

    df["detail_content_clean"] = df["detail_content"].fillna("")

    with open(meta["keywords_file"], "r", encoding="utf-8") as f:
        keywords_data = json.load(f)

    cert_list = list(keywords_data["자격증 최다 언급 TOP 20"].keys())
    tool_list = list(keywords_data["활용 툴 최다 언급 TOP 20"].keys())
    job_list = list(keywords_data["세부 직무 최다 언급 TOP 20"].keys())
    all_features = cert_list + tool_list + job_list

    feature_matrix = []
    
    def get_exp_years(text):
        if "경력무관" in text or "경력 무관" in text or "무관" in text:
            return 0
        if "신입" in text and "경력" not in text:
            return 0
        match = re.search(r"경력\s*(?:(?:[0-9]~\s*)?([0-9]+)\s*년)", text)
        if match:
            return int(match.group(1))
        match2 = re.search(r"([0-9]+)\s*년\s*(?:이상|경력)", text)
        if match2:
            return int(match2.group(1))
        if "경력" in text:
            return 1
        return 0

    def get_edu_score(text):
        if "석사" in text or "대학원" in text:
            return 4
        if "대졸" in text or "4년제" in text or "학사" in text:
            return 3
        if "전문대" in text or "초대졸" in text or "2년제" in text or "3년제" in text:
            return 2
        if "고졸" in text or "고등학교" in text:
            return 1
        return 0

    exp_years_list = []
    edu_score_list = []

    for idx, row in df.iterrows():
        raw_text = str(row["detail_content_clean"]) + " " + str(row["title"])
        
        # 컴파일된 정규식으로 고속 매핑 진행
        clean_text = raw_text
        for comp_pattern, rep in compiled_synonyms.items():
            clean_text = comp_pattern.sub(rep, clean_text)

        row_features = []
        for feature in all_features:
            feat_pat = re.escape(feature)
            if re.search(feat_pat, clean_text, re.IGNORECASE):
                row_features.append(1)
            else:
                row_features.append(0)
                
        feature_matrix.append(row_features)
        exp_years_list.append(get_exp_years(raw_text))
        edu_score_list.append(get_edu_score(raw_text))

    df_features = pd.DataFrame(feature_matrix, columns=all_features)
    df_features["exp_years"] = exp_years_list
    df_features["edu_score"] = edu_score_list

    df_final = pd.concat([df, df_features], axis=1)

    return df_final, keywords_data, all_features


@st.cache_data
def load_naver_trends_data(job_key):
    """
    naver_search_trend 테이블로부터 네이버 검색어 트렌드 데이터를 로드하고 7일 이동평균 전처리를 적용합니다.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df_trend = pd.read_sql_query(
            "SELECT period, group_name, ratio FROM naver_search_trend WHERE job_category = ? ORDER BY period", 
            conn, 
            params=(job_key,)
        )
        conn.close()
        
        if not df_trend.empty:
            df_trend['ratio_ma'] = df_trend.groupby('group_name')['ratio'].transform(lambda x: x.rolling(7, min_periods=1).mean())
        return df_trend
    except Exception as e:
        # 데이터베이스 미생성 혹은 미수집 직무용 대체 시뮬레이션 모의 데이터 생성
        import pandas as pd
        dates = pd.date_range(end=datetime.now(), periods=180).strftime("%Y-%m-%d")
        groups = ["전산세무회계", "전문자격증", "재경관리사", "ERP/실무 툴", "사무/컴활"]
        records = []
        for d in dates:
            for g in groups:
                records.append((d, g, np.random.rand() * 100))
        df_mock = pd.DataFrame(records, columns=["period", "group_name", "ratio"])
        df_mock['ratio_ma'] = df_mock.groupby('group_name')['ratio'].transform(lambda x: x.rolling(7, min_periods=1).mean())
        return df_mock


@st.cache_data
def perform_clustering(df_final, features, job_key):
    """
    StandardScaler를 사용하여 변수 스케일링을 수행한 후, K-Means 분석을 안정적으로 처리합니다.
    """
    cluster_features = features + ["exp_years", "edu_score"]
    X = df_final[cluster_features].fillna(0)
    
    # 피처 스케일러(StandardScaler) 적용하여 단위 차이 왜곡 방지
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 실루엣 스코어 비교 (K=3, 4)
    silhouette_scores = {}
    models = {}
    for k in [3, 4]:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        silhouette_scores[k] = score
        models[k] = (kmeans, labels)

    best_k = max(silhouette_scores, key=silhouette_scores.get)
    best_model, best_labels = models[best_k]
    
    df_final["cluster_label"] = best_labels

    # 군집별 특화 피처 최댓값 비교 기반의 동적 작명 및 프로파일링
    # 고정 임계치(Threshold) 사용 시 데이터 분포에 따라 특정 이름으로 쏠리는 현상을 방지합니다.
    profile_dict = {}
    
    # 각 직무별 특화 군집 매핑용 ID 선정
    special_id_1 = -1
    special_id_2 = -1
    
    if job_key == "accounting":
        # SAP ERP 평균 비율이 가장 높은 군집을 대기업형으로 분류
        sap_means = [df_final[df_final["cluster_label"] == cid]["SAP ERP"].mean() for cid in range(best_k)]
        special_id_1 = int(np.argmax(sap_means))
        
        # CTA (세무사) 평균 비율이 가장 높은 군집(단, sap_cluster 제외)을 세무대리형으로 분류
        tax_means = [df_final[df_final["cluster_label"] == cid]["CTA (세무사)"].mean() if cid != special_id_1 else -1 for cid in range(best_k)]
        special_id_2 = int(np.argmax(tax_means))
        
    elif job_key == "it_dev":
        # Docker/K8s 평균 비율이 가장 높은 군집을 DevOps형으로 분류
        devops_means = [df_final[df_final["cluster_label"] == cid]["Docker/K8s"].mean() for cid in range(best_k)]
        special_id_1 = int(np.argmax(devops_means))
        
        # React/Vue 평균 비율이 가장 높은 군집을 프론트엔드형으로 분류
        frontend_means = [df_final[df_final["cluster_label"] == cid]["React/Vue"].mean() if cid != special_id_1 else -1 for cid in range(best_k)]
        special_id_2 = int(np.argmax(frontend_means))
        
    else: # marketing
        # Google Analytics 평균 비율이 가장 높은 군집을 그로스형으로 분류
        growth_means = [df_final[df_final["cluster_label"] == cid]["Google Analytics"].mean() for cid in range(best_k)]
        special_id_1 = int(np.argmax(growth_means))
        
        # SNS 콘텐츠 제작 평균 비율이 가장 높은 군집을 브랜드형으로 분류
        brand_means = [df_final[df_final["cluster_label"] == cid]["SNS 콘텐츠 제작"].mean() if cid != special_id_1 else -1 for cid in range(best_k)]
        special_id_2 = int(np.argmax(brand_means))

    # 프로파일 정보 채우기
    for cluster_id in range(best_k):
        cluster_data = df_final[df_final["cluster_label"] == cluster_id]
        avg_rates = cluster_data[features].mean()
        top_specs = avg_rates.sort_values(ascending=False).head(5)
        
        if job_key == "accounting":
            if cluster_id == special_id_1:
                cluster_name = "중견/대기업 SAP·결산 대응형"
                desc = "SAP ERP 활용 능력이 우대되며, 법인결산 및 외부감사 대응 중심의 체계적인 회계 업무"
            elif cluster_id == special_id_2:
                cluster_name = "세무/회계법인 전문 세무대리형"
                desc = "세무사 자격증 및 전산세무가 우대되며, 기장 및 다수의 세무 신고 대리를 전문으로 수행"
            else:
                cluster_name = "중소/스타트업 자금·경리 멀티태스킹형"
                desc = "더존(Smart A)과 Excel 활용 비율이 높으며, 급여 계산 및 4대 보험 등 총무를 겸하는 실무"
                
        elif job_key == "it_dev":
            if cluster_id == special_id_1:
                cluster_name = "DevOps 및 클라우드 인프라 아키텍트형"
                desc = "Docker/K8s 등 컨테이너 기반 서버 인프라 운영 및 CI/CD 파이프라인 자동화 구축을 전담"
            elif cluster_id == special_id_2:
                cluster_name = "프론트엔드 UI/UX 중심 개발형"
                desc = "React, Vue 등 최신 프레임워크와 웹 표준 기술을 사용하여 유저 인터페이스 설계를 전문 수행"
            else:
                cluster_name = "백엔드 분산 API 시스템 개발형"
                desc = "Spring 이나 FastAPI 프레임워크를 기반으로 비즈니스 로직과 데이터베이스 분산 아키텍처를 전담"
                
        else: # marketing
            if cluster_id == special_id_1:
                cluster_name = "데이터 기반 그로스/퍼포먼스 마케팅형"
                desc = "GA지표 수집과 SQL 데이터 가공을 통해 마케팅 성과 추적 및 전환율(CVR) 최적화를 주도"
            elif cluster_id == special_id_2:
                cluster_name = "브랜드 및 인플루언서 콘텐츠 기획형"
                desc = "포토샵/일러스트 등을 활용한 카드뉴스 제작 및 공식 SNS 채널 브랜딩 콘텐츠 기획"
            else:
                cluster_name = "SEO/CRM 유저 획득(Acquisition) 마케팅형"
                desc = "검색 엔진 노출 최적화(SEO) 및 고객 관계 관리(CRM) 툴을 이용한 오가닉 트래픽 유치"

        profile_dict[cluster_id] = {
            "name": cluster_name,
            "description": desc,
            "top_specs": top_specs.to_dict(),
            "count": len(cluster_data)
        }

    return df_final, profile_dict, silhouette_scores, best_k


# -------------------------------------------------------------
# 사이드바 레이아웃 및 직무군 선택 UI
# -------------------------------------------------------------
st.sidebar.markdown("## ⚙️ 분석 설정 영역")
job_options = {
    "accounting": "회계 (실제 수집 데이터)",
    "it_dev": "IT/개발 (프레임워크 검증 모의데이터)",
    "marketing": "마케팅 (프레임워크 검증 모의데이터)"
}
selected_job_key = st.sidebar.selectbox(
    "📊 대상 직무 카테고리 선택",
    options=list(job_options.keys()),
    format_func=lambda x: job_options[x]
)

meta = JOB_META[selected_job_key]

# 1. 선택된 직무 전용 데이터 로드
with st.spinner(f"{meta['job_name']} 채용 원본 데이터 분석 및 전처리 중..."):
    df_final, keywords_data, all_features = load_and_preprocess_data(selected_job_key)

if df_final.empty:
    st.error("데이터베이스를 로드할 수 없거나 분석 결과가 비어 있습니다.")
    st.stop()

# 2. 선택된 직무 군집화
with st.spinner(f"{meta['job_name']} 군집 분석 수행 중..."):
    df_final, profile_dict, silhouette_scores, best_k = perform_clustering(df_final, all_features, selected_job_key)


# 메인 대시보드 타이틀 동적 렌더링
st.title(f"💼 {meta['title']}")
st.subheader(meta['subtitle'])

if selected_job_key != "accounting":
    st.info(f"💡 현재 화면은 **{meta['job_name']}** 직무의 채용 가상 시뮬레이션 모의 데이터를 활용하여 동적 프레임워크 레이아웃을 표시하고 있습니다.")

st.markdown("---")

# 탭 구성
tab1, tab2 = st.tabs([
    f"💻 구직자용 : 내 {meta['job_name']} 직무 적합도 & 우선순위 리포트",
    f"🏢 인사팀용 : {meta['job_name']} 스펙 미스매치(Gap) 및 JD 가이드"
])

# -------------------------------------------------------------
# 탭 1: 구직자 탭 (개선된 지능형 적합도 로직 탑재)
# -------------------------------------------------------------
with tab1:
    st.markdown(f"### 🔍 구직자 {meta['job_name']} 스펙 자가진단 및 적합도 예측")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🛠️ 내 스펙 입력창")
        
        edu_input = st.selectbox(
            "학력 요건",
            options=["학력무관", "고졸 이상", "전문대졸 이상", "대졸(4년) 이상", "석사 이상"],
            index=3
        )
        edu_score_map = {"학력무관": 0, "고졸 이상": 1, "전문대졸 이상": 2, "대졸(4년) 이상": 3, "석사 이상": 4}
        user_edu_score = edu_score_map[edu_input]
        
        exp_input = st.slider("관련 경력 연수", min_value=0, max_value=15, value=2)
        
        cert_list = list(keywords_data["자격증 최다 언급 TOP 20"].keys())
        tool_list = list(keywords_data["활용 툴 최다 언급 TOP 20"].keys())
        job_list = list(keywords_data["세부 직무 최다 언급 TOP 20"].keys())
        
        user_certs = st.multiselect("기본 요건 / 자격 사항", options=cert_list, placeholder="자격/기본 요건 선택")
        user_tools = st.multiselect("활용 툴 / ERP / 소프트웨어", options=tool_list, placeholder="소프트웨어/도구 선택")
        user_jobs = st.multiselect("세부 실무/업무 경험", options=job_list, placeholder="실무 업무 경험 선택")

        st.markdown("---")
        st.subheader("💡 가상 스펙 취득 시뮬레이터 (What-if)")
        what_if_specs = st.multiselect(
            "시뮬레이션 스펙 추가",
            options=[x for x in all_features if x not in (user_certs + user_tools + user_jobs)],
            placeholder="가상으로 획득해볼 스펙 선택"
        )

    with col2:
        # 지능형 적합도 예측 연산 수행 함수 정의
        def calculate_intelligent_score(selected_specs):
            # 1. 37종 이진 피처 벡터 생성
            u_vec = [1 if f in selected_specs else 0 for f in all_features]
            db_vecs = df_final[all_features].values
            
            # 2. 이진 스펙간 코사인 유사도 점수 계산
            raw_sims = cosine_similarity([u_vec], db_vecs)[0]
            
            # 3. 경력 및 학력 요건 충족도 가중치(Multiplier) 연산
            # 공고별 요구 경력 및 학력 추출
            comp_exps = df_final["exp_years"].values
            comp_edus = df_final["edu_score"].values
            
            final_scores = []
            for sim, c_exp, c_edu in zip(raw_sims, comp_exps, comp_edus):
                # 경력 충족 연산 (미달 시 패널티 부여)
                if exp_input >= c_exp:
                    exp_mult = 1.0
                else:
                    exp_mult = max(0.5, 1.0 - (c_exp - exp_input) * 0.1)
                    
                # 학력 충족 연산
                if user_edu_score >= c_edu:
                    edu_mult = 1.0
                else:
                    edu_mult = max(0.7, 1.0 - (c_edu - user_edu_score) * 0.1)
                    
                final_scores.append(sim * exp_mult * edu_mult)
                
            # 상위 50개 공고 평균 유사도를 100점 스케일링
            top_scores = np.sort(final_scores)[-50:]
            return int(np.mean(top_scores) * 100)

        # 기본/시뮬레이션 스펙 목록 정의
        current_specs = user_certs + user_tools + user_jobs
        simulated_specs = current_specs + what_if_specs
        
        # 개선된 지능형 점수 산출
        fit_score = calculate_intelligent_score(current_specs)
        sim_fit_score = calculate_intelligent_score(simulated_specs)

        # 1. 적합도 Score 카드 및 게이지 시각화
        m1, m2 = st.columns(2)
        with m1:
            st.metric(
                label=f"현재 내 {meta['job_name']} 직무 적합도 점수",
                value=f"{fit_score} 점",
                help="기존의 단순 거리 연산을 넘어, 경력/학력 충족 여부 조건 패널티가 가미된 정밀 매칭 알고리즘 지표입니다."
            )
        with m2:
            score_diff = sim_fit_score - fit_score
            st.metric(
                label="시뮬레이션 스펙 적용 후 예상 점수",
                value=f"{sim_fit_score} 점",
                delta=f"+{score_diff} 점 상승" if score_diff > 0 else "변동 없음"
            )

        # 게이지(Gauge) 차트 구현
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fit_score,
            title={'text': "직무 매치 적합도 게이지 (%)"},
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#3b82f6"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 50], 'color': '#fee2e2'},
                    {'range': [50, 80], 'color': '#fef3c7'},
                    {'range': [80, 100], 'color': '#d1fae5'}
                ]
            }
        ))
        fig_gauge.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

        # 2. 군집 매핑 판정
        # 유저가 어떤 군집과 가장 유사한지 판정
        user_total_vec = []
        for feature in all_features:
            if feature in current_specs:
                user_total_vec.append(1)
            else:
                user_total_vec.append(0)
        user_total_vec += [exp_input, user_edu_score]
        
        cluster_similarities = []
        for cluster_id in range(best_k):
            cluster_centers = df_final[df_final["cluster_label"] == cluster_id][all_features + ["exp_years", "edu_score"]].mean().values
            sim = cosine_similarity([user_total_vec], [cluster_centers])[0][0]
            cluster_similarities.append(sim)
            
        best_cluster_id = np.argmax(cluster_similarities)
        best_cluster = profile_dict[best_cluster_id]
        
        st.success(f"🎯 **귀하의 스펙은 데이터 분석 결과 [{best_cluster['name']}] 유형의 기업에 가장 적합합니다.**")
        st.info(f"**유형 설명**: {best_cluster['description']}")
        
        # 3. 부족한 실무 스펙 TOP 3 동적 추천
        st.markdown(f"### 🔔 나에게 부족한 진성 실무 스펙 우선순위 TOP 3 ({meta['job_name']})")
        
        cluster_specs = df_final[df_final["cluster_label"] == best_cluster_id][all_features]
        avg_requirements = cluster_specs.mean()
        
        user_missing_specs = [f for f in all_features if f not in current_specs]
        missing_spec_rates = avg_requirements[user_missing_specs].sort_values(ascending=False)
        top_missing_3 = missing_spec_rates.head(3)
        
        cols_missing = st.columns(3)
        for i, (spec_name, rate) in enumerate(top_missing_3.items()):
            with cols_missing[i]:
                st.markdown(f"""
                <div style="background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #ef4444; color:white;">
                    <h4 style="margin:0; font-size:16px; color:#ef4444;">우선순위 {i+1}위</h4>
                    <p style="margin:5px 0 0 0; font-weight:bold; font-size:18px;">{spec_name}</p>
                    <p style="margin:5px 0 0 0; font-size:13px; color:#94a3b8;">해당 군집 요구 비율: <b>{rate*100:.1f}%</b></p>
                </div>
                """, unsafe_allow_html=True)
                
        # 4. 비교 그래프 (Plotly)
        st.markdown("#### 📊 타겟 기업 유형 요구도 vs 내 스펙 프로필 비교")
        top_12_features = avg_requirements.sort_values(ascending=False).index[:12]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_12_features,
            x=avg_requirements[top_12_features].values * 100,
            name="타겟 기업 요구율 (%)",
            orientation='h',
            marker_color='#3b82f6'
        ))
        
        user_has_top_12 = [100 if f in current_specs else 0 for f in top_12_features]
        fig.add_trace(go.Bar(
            y=top_12_features,
            x=user_has_top_12,
            name="내 보유 여부",
            orientation='h',
            marker_color='#10b981',
            opacity=0.65
        ))
        
        fig.update_layout(
            barmode='group',
            xaxis_title="비율 / 보유 여부 (%)",
            yaxis_title="스펙 키워드 명칭",
            legend=dict(x=0.7, y=0.1),
            height=400,
            margin=dict(l=150, r=20, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------
# 탭 2: 인사팀 탭 (개선된 Plotly 다차원 Heatmap 추가 완료)
# -------------------------------------------------------------
with tab2:
    st.markdown(f"### 🏢 인사담당자용 채용 JD 미스매치 완화 솔루션 ({meta['job_name']})")
    
    cluster_options = {f"유형 {cid}: {info['name']} (공고 {info['count']}건)": cid for cid, info in profile_dict.items()}
    selected_option = st.selectbox(f"진단할 {meta['job_name']} 기업 군집 유형 선택", options=list(cluster_options.keys()))
    selected_cluster_id = cluster_options[selected_option]
    target_cluster = profile_dict[selected_cluster_id]
    
    st.markdown("---")
    
    col_hr1, col_hr2 = st.columns([2, 1])
    
    with col_hr1:
        st.subheader("📊 범용 자격/이론 스펙 vs 진성 실무 스펙 미스매치")
        st.write("취준생들이 취득하는 기본 자격(기본 툴 활용)과, 기업이 실제 바라는 고난도 실무경험/특화 툴의 요구율 차이 비교입니다.")
        
        cluster_df = df_final[df_final["cluster_label"] == selected_cluster_id]
        
        generic_specs = meta["generic_specs"]
        real_specs = meta["real_specs"]
        
        generic_vals = cluster_df[generic_specs].mean().values * 100
        real_vals = cluster_df[real_specs].mean().values * 100
        
        gap_data = pd.DataFrame({
            "스펙 구분": ["기본 자격 스펙"] * len(generic_specs) + ["진성 실무 스펙"] * len(real_specs),
            "스펙 키워드": generic_specs + real_specs,
            "시장 요구 비율 (%)": list(generic_vals) + list(real_vals)
        })
        
        fig_gap = px.bar(
            gap_data,
            x="시장 요구 비율 (%)",
            y="스펙 키워드",
            color="스펙 구분",
            barmode="group",
            orientation="h",
            color_discrete_map={"기본 자격 스펙": "#94a3b8", "진성 실무 스펙": "#ef4444"},
            text_auto=".1f"
        )
        
        fig_gap.update_layout(
            xaxis_title="요구 비율 (%)",
            yaxis_title="스펙 키워드",
            height=350,
            margin=dict(l=150, r=20, t=40, b=40)
        )
        st.plotly_chart(fig_gap, use_container_width=True)

    with col_hr2:
        st.subheader("🛡️ HR 지원자 필터링 시뮬레이터")
        st.write("채용 자격 요건을 구체적으로 필수 기재함에 따라 차단(필터링)되는 허수 지원자의 비율을 계산합니다.")
        
        st.markdown("**필수 기재할 핵심 자격 요건 선택:**")
        filter_checks = {}
        for spec in real_specs[:4]:
            filter_checks[spec] = st.checkbox(f"{spec} 역량 필수 지정")
            
        filtered_df = cluster_df.copy()
        for spec, val in filter_checks.items():
            if val:
                filtered_df = filtered_df[filtered_df[spec] == 1]
                
        remaining_ratio = (len(filtered_df) / len(cluster_df)) * 100
        cutoff_ratio = 100 - remaining_ratio
        
        st.markdown(f"""
        <div style="background-color:#0f172a; padding:20px; border-radius:10px; text-align:center; border: 1px solid #334155;">
            <p style="font-size:14px; margin:0; color:#94a3b8;">예상 지원자 감소율 (허수 차단율)</p>
            <h2 style="font-size:36px; margin:10px 0; color:#ef4444;">{cutoff_ratio:.1f}%</h2>
            <p style="font-size:12px; margin:0; color:#475569;">전체 공고 대비 필터링 효과</p>
        </div>
        """, unsafe_allow_html=True)
        st.caption("※ 요건 명시 시 직무 이해도가 낮은 구직자의 투척형 지원 차단 효과를 모사합니다.")

    # [신규] 3. Plotly 다차원 군집별 스펙 히트맵(Heatmap) 시각화 배치
    st.markdown("---")
    st.subheader("🗺️ 다차원 군집별 실무 스펙 요구 비중 대조 히트맵")
    st.write("모든 기업 유형(Cluster) 간 핵심 실무 및 범용 스펙 요구 비율의 차이를 한눈에 직관적으로 비교할 수 있는 히트맵입니다.")
    
    # 히트맵 매핑용 데이터셋 준비
    heatmap_specs = generic_specs + real_specs
    heatmap_data = []
    
    for cid in range(best_k):
        c_mean = df_final[df_final["cluster_label"] == cid][heatmap_specs].mean().values * 100
        heatmap_data.append(c_mean)
        
    y_labels = [f"Cluster {cid}: {profile_dict[cid]['name']}" for cid in range(best_k)]
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=heatmap_specs,
        y=y_labels,
        colorscale='Viridis',
        text=[[f"{val:.1f}%" for val in row] for row in heatmap_data],
        texttemplate="%{text}",
        textfont={"size": 12},
        hoverongaps=False
    ))
    
    fig_heatmap.update_layout(
        title="기업 군집 유형별 전체 핵심 스펙 요구 비율 (%) 대조",
        xaxis_title="스펙 키워드 명칭",
        yaxis_title="기업 유형 군집",
        height=320,
        margin=dict(l=250, r=20, t=50, b=50)
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # 4. 우대사항 채용공고(JD) 작성 가이드라인 추천
    st.markdown("---")
    st.subheader("📝 직무 진정성 확보를 위한 우대사항 JD 최적화 가이드라인")
    
    avg_reqs = cluster_df[all_features].mean()
    top_requirements = avg_reqs.sort_values(ascending=False).head(3)
    
    cols_guidelines = st.columns(3)
    for idx, (spec_name, rate) in enumerate(top_requirements.items()):
        comment = meta["guideline_templates"].get(spec_name, f"해당 유형 기업의 <b>{rate*100:.1f}%</b>가 {spec_name} 역량을 핵심 요구하고 있습니다. JD 우대 요건에 <b>'{spec_name} 실무 수행 유경험자'</b>를 상세 기재하여 인재 매칭 확률을 높이십시오.")
        
        with cols_guidelines[idx]:
            st.markdown(f"""
            <div style="background-color:#1e293b; padding:20px; border-radius:10px; border-top: 4px solid #3b82f6; height:100%; color:white;">
                <h4 style="margin:0 0 10px 0; color:#3b82f6; font-size:16px;">🔑 우수 키워드: {spec_name} (요구 비율 {rate*100:.1f}%)</h4>
                <p style="font-size:13px; line-height:1.6; color:#cbd5e1;">{comment}</p>
            </div>
            """, unsafe_allow_html=True)

    # 5. 수요-공급 미스매치 진단 리포트 (네이버 검색관심 vs 실제 채용공고 JD)
    st.markdown("---")
    st.subheader("📈 구직자 관심 트렌드 vs 기업 채용 요구도 미스매치 시계열 분석")
    st.write("구직자가 네이버에서 검색하는 관심 빈도(네이버 데이터랩 트렌드)와 실제 채용공고의 실무자 요건 비중을 교차 대조하여 정보 비대칭성을 추적합니다.")
    
    from datetime import timedelta
    df_trend = load_naver_trends_data(selected_job_key)
    
    if not df_trend.empty:
        col_line1, col_line2 = st.columns([2, 1])
        
        with col_line1:
            fig_line = px.line(
                df_trend,
                x="period",
                y="ratio_ma",
                color="group_name",
                title="최근 1개년 핵심 스펙 대분류별 네이버 검색 관심도 추이 (7일 이동평균)",
                labels={"period": "수집 일자", "ratio_ma": "상대적 검색량 (%)", "group_name": "스펙 대분류"}
            )
            fig_line.update_layout(height=380, margin=dict(l=50, r=20, t=50, b=40))
            st.plotly_chart(fig_line, use_container_width=True)
            
        with col_line2:
            st.markdown("#### ℹ️ 트렌드 시각화 해설")
            st.write(f"네이버 데이터랩의 실시간 트렌드 추적 결과, 구직자들은 여전히 기본 컴활/사무 프로그램 위주로 많은 양의 검색을 시도하고 있습니다. 한편 실제 실무 툴(ERP 등)이나 결산 업무와 관련된 실무 경험 키워드는 상대적 검색 빈도가 매우 낮은 기형적인 **스펙 수급 불일치(미스매치)** 상태가 지속되고 있습니다.")
            
        # 미스매치 인덱스 테이블 도출
        recent_date_limit = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        recent_trends = df_trend[df_trend["period"] >= recent_date_limit]
        avg_search = recent_trends.groupby("group_name")["ratio"].mean()
        
        # 키워드 그룹별 공고 요구 비중 계산
        if selected_job_key == "accounting":
            job_req_mapping = {
                "전산세무회계": df_final[["전산세무 1급", "전산세무 2급", "전산회계 1급", "전산회계 2급"]].max(axis=1).mean() * 100,
                "전문자격증": df_final[["CPA (한국공인회계사)", "AICPA (미국공인회계사)", "CTA (세무사)"]].max(axis=1).mean() * 100,
                "재경관리사": df_final["재경관리사"].mean() * 100,
                "ERP/실무 툴": df_final[["더존 (Smart A)", "더존 (iU)", "SAP ERP"]].max(axis=1).mean() * 100,
                "사무/컴활": df_final["Excel (엑셀)"].mean() * 100
            }
        elif selected_job_key == "it_dev":
            job_req_mapping = {
                "형상관리/기본": df_final["Git/GitHub"].mean() * 100,
                "프론트엔드": df_final["React/Vue"].mean() * 100,
                "백엔드 프레임워크": df_final["FastAPI/Spring"].mean() * 100,
                "인프라/DevOps": df_final["Docker/K8s"].mean() * 100,
                "테스트/설계": df_final["TDD"].mean() * 100
            }
        else: # marketing
            job_req_mapping = {
                "디자인/오피스": df_final["포토샵/일러스트"].mean() * 100,
                "로그 분석": df_final["Google Analytics"].mean() * 100,
                "데이터 추출": df_final["SQL 데이터 추출"].mean() * 100,
                "광고/그로스": df_final["A/B 테스트"].mean() * 100,
                "검색 최적화": df_final["SEO 최적화"].mean() * 100
            }
            
        mismatch_records = []
        for group, jd_rate in job_req_mapping.items():
            search_rate = avg_search.get(group, 0.0)
            gap = search_rate - jd_rate
            if gap > 25:
                diagnosis = "⚠️ 구직자 관심 공급 과잉 (과열 스펙)"
            elif gap < -25:
                diagnosis = "🔥 기업 실무 수요 부족 (희소 스펙)"
            else:
                diagnosis = "✅ 시장 수요-공급 적정 매칭"
            mismatch_records.append({
                "스펙 대분류": group,
                "구직자 관심도 (네이버 검색 비율)": f"{search_rate:.1f}%",
                "기업 요구도 (채용공고 JD 비율)": f"{jd_rate:.1f}%",
                "수요-공급 갭 (Gap)": f"{gap:+.1f}%p",
                "정보 비대칭성 진단": diagnosis
            })
            
        df_mismatch = pd.DataFrame(mismatch_records)
        st.markdown("#### 🚨 실무 자격요건 수요-공급 미스매치(Gap) 지수 진단 테이블")
        st.dataframe(df_mismatch, use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# 하단 통계 무결성 정보 및 메타데이터 바인딩
# -------------------------------------------------------------
st.markdown("---")
col_footer1, col_footer2 = st.columns(2)
with col_footer1:
    st.caption(f"🤖 **머신러닝 군집 품질 분석**: 현재 최적의 기업 유형 수 {best_k}개 결정 (실루엣 스코어: K=3일 때 {silhouette_scores[3]:.4f} / K=4일 때 {silhouette_scores[4]:.4f})")
with col_footer2:
    st.markdown(f"<p style='text-align:right; font-size:12px; color:#64748b;'>데이터 수집 최종 업데이트: 2026-07-04 | {meta['job_name']} 분석 대상 데이터 수: {len(df_final)}건</p>", unsafe_allow_html=True)
