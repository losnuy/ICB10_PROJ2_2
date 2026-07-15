"""
온라인 쇼핑객 구매 의도(Online Shoppers Purchasing Intention) 데이터셋 분석을 위한 Streamlit 대시보드 모듈입니다.

주요 기능:
- 데이터 캐싱을 통한 CSV 파일 로드 및 필터링 기능
- 구매 여부(Revenue)에 따른 핵심 KPI 카드 표시
- 모든 수치형 및 범주형 변수의 Revenue별 분포 비교 시각화 (서브플롯 활용)
- 수치형 변수 기술 통계 및 범주형 변수 교차표(Crosstab) 테이블 요약
- 피어슨 상관계수 히트맵 및 Random Forest 기반 구매 중요도 분석
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestClassifier
import os

# 페이지 설정
st.set_page_config(
    page_title="온라인 쇼핑객 구매 의도 분석 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 다크/프리미엄 스타일 테마 적용을 위한 CSS
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1e222b;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #8a92a6;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2e3440;
        color: #00ffcc !important;
        font-weight: bold;
        border-bottom: 2px solid #00ffcc;
    }
</style>
""", unsafe_allow_html=True)

# 1. 데이터 로드 (캐싱 활용)
@st.cache_data
def load_data():
    # 상대 경로로 데이터 읽기
    file_path = "online-shoppers/data/online_shoppers_intention.csv"
    if not os.path.exists(file_path):
        # 만약 상대 경로에서 실패할 경우 대안 탐색
        file_path = "data/online_shoppers_intention.csv"
    
    df = pd.read_csv(file_path)
    # 데이터 전처리: 가독성을 위해 일부 변수 형식 변경
    df['Revenue_Str'] = df['Revenue'].map({True: '구매 완료 (True)', False: '구매 미완료 (False)'})
    df['Weekend_Str'] = df['Weekend'].map({True: '주말', False: '평일'})
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    st.stop()

# 2. 사이드바 필터 구성
st.sidebar.title("🔍 분석 필터 설정")
st.sidebar.markdown("---")

# 월 필터
months = sorted(df_raw['Month'].unique())
selected_months = st.sidebar.multiselect(
    "📅 분석 대상 월 (Month)",
    options=months,
    default=months,
    help="분석할 월을 선택하세요. 여러 개 선택 가능합니다."
)

# 방문자 유형 필터
visitor_types = df_raw['VisitorType'].unique()
selected_visitors = st.sidebar.multiselect(
    "👥 방문자 유형 (VisitorType)",
    options=visitor_types,
    default=visitor_types,
    help="방문자 유형을 선택하세요."
)

# 주말 여부 필터
weekend_options = ['전체', '주말', '평일']
selected_weekend = st.sidebar.selectbox(
    "🏖️ 주말 여부",
    options=weekend_options,
    index=0
)

# 데이터 필터링 적용
df = df_raw.copy()
if selected_months:
    df = df[df['Month'].isin(selected_months)]
if selected_visitors:
    df = df[df['VisitorType'].isin(selected_visitors)]
if selected_weekend != '전체':
    is_weekend = True if selected_weekend == '주말' else False
    df = df[df['Weekend'] == is_weekend]

# 데이터 건수 경고 (필터로 인해 데이터가 없는 경우)
if df.empty:
    st.warning("⚠️ 선택한 필터 조건에 부합하는 데이터가 없습니다. 필터를 조정해 주세요.")
    st.stop()

# 타이틀 및 대시보드 소개
st.title("🛍️ 온라인 쇼핑객 구매 의도 분석 대시보드")
st.markdown("쇼핑객의 세션 행동 데이터를 기반으로 구매 결정(`Revenue`)에 미치는 영향을 탐색합니다. "
            "의사결정나무(Decision Tree) 기반 머신러닝 예측 및 평가 모델은 사이드바의 **1_Machine_Learning** 페이지에서 확인할 수 있습니다.")

# 3. 핵심 KPI 카드 배치 (상단 영역)
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

total_sessions = len(df)
revenue_true = df['Revenue'].sum()
conversion_rate = (revenue_true / total_sessions * 100) if total_sessions > 0 else 0.0
avg_bounce = df['BounceRates'].mean() * 100
avg_page_value = df['PageValues'].mean()

with kpi_col1:
    st.metric(
        label="📊 총 세션 수 (Total Sessions)",
        value=f"{total_sessions:,}건",
        help="필터링된 조건 하에서의 총 방문 세션 수입니다."
    )

with kpi_col2:
    st.metric(
        label="🎯 구매 성공 수 (Revenue True)",
        value=f"{revenue_true:,}건",
        delta=f"비율: {conversion_rate:.2f}%",
        help="실제 구매가 이루어진 세션 수와 비율입니다."
    )

with kpi_col3:
    st.metric(
        label="📉 평균 이탈률 (Avg Bounce Rate)",
        value=f"{avg_bounce:.3f}%",
        help="방문자가 웹사이트 진입 후 즉시 이탈한 비율의 평균입니다."
    )

with kpi_col4:
    st.metric(
        label="💰 평균 페이지 가치 (Avg Page Value)",
        value=f"${avg_page_value:.2f}",
        help="세션 내 방문한 페이지들의 평균 가치 정보입니다. 구매 전환과 직결되는 핵심 지표입니다."
    )

st.markdown("---")

# 탭 구성
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📂 전체 개요 및 데이터 요약",
    "📈 수치형 변수 분석 (Numerical)",
    "📊 범주형 변수 분석 (Categorical)",
    "🧠 상관관계 & 중요도 분석",
    "🌪️ 퍼널 분석 (Funnel)"
])

# ----------------- Tab 1: 전체 개요 및 데이터 요약 -----------------
with tab1:
    st.header("📂 데이터셋 기본 정보 및 Target 분포")
    
    col_desc_1, col_desc_2 = st.columns([2, 3])
    
    with col_desc_1:
        st.subheader("📋 데이터 요약 통계 정보")
        st.write(f"**전체 행 수:** {df.shape[0]:,}개")
        st.write(f"**전체 열 수:** {df.shape[1]}개")
        
        # 결측치 확인
        null_counts = df.isnull().sum().sum()
        st.write(f"**결측치 개수:** {null_counts}개")
        
        # Target 변수 (Revenue) 빈도/비율 테이블
        revenue_counts = df['Revenue'].value_counts()
        revenue_probs = df['Revenue'].value_counts(normalize=True) * 100
        
        revenue_summary = pd.DataFrame({
            '빈도 (건수)': revenue_counts,
            '비율 (%)': revenue_probs
        })
        revenue_summary.index = revenue_summary.index.map({True: '구매 완료 (True)', False: '구매 미완료 (False)'})
        st.markdown("**Target 변수 (Revenue) 분포 테이블**")
        st.dataframe(revenue_summary.style.format({'비율 (%)': '{:.2f}%'}))
        
    with col_desc_2:
        st.subheader("🍩 Revenue 비율 시각화")
        fig_pie = px.pie(
            df, 
            names='Revenue_Str', 
            title='전체 세션 중 구매 전환 비율',
            color='Revenue_Str',
            color_discrete_map={'구매 완료 (True)': '#00ffcc', '구매 미완료 (False)': '#ff4b4b'},
            hole=0.4
        )
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa'
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("👀 데이터셋 샘플 미리보기 (상위 5개 행)")
    st.dataframe(df.head())


# ----------------- Tab 2: 수치형 변수 분석 -----------------
with tab2:
    st.header("📈 수치형 변수와 Revenue 비교 분석")
    st.markdown("수치형 변수들이 구매 완료 여부(`Revenue`)에 따라 어떻게 달라지는지 **박스플롯(Box Plot)**과 **히스토그램(Histogram)**을 병렬 시각화하여 확인하고, 하단의 상세 기술통계를 통해 비교합니다.")
    
    num_cols = [
        'Administrative', 'Administrative_Duration', 
        'Informational', 'Informational_Duration', 
        'ProductRelated', 'ProductRelated_Duration', 
        'BounceRates', 'ExitRates', 
        'PageValues', 'SpecialDay'
    ]
    
    st.subheader("🔍 변수별 상세 비교 분석 (Box Plot & Histogram + 기술통계)")
    st.markdown("분석하고자 하는 수치형 변수를 아래 드롭다운에서 선택해 주세요. 해당 변수의 분포와 기술통계가 함께 표시됩니다.")
    
    selected_num_col = st.selectbox("분석할 수치형 변수 선택:", options=num_cols)
    
    # 1행 2열로 박스플롯과 히스토그램 그리기
    fig_detail = make_subplots(
        rows=1, cols=2,
        subplot_titles=[f"[{selected_num_col}] Box Plot (분포 비교)", f"[{selected_num_col}] Histogram (빈도 분포 비교)"],
        horizontal_spacing=0.15
    )
    
    colors = {True: '#00ffcc', False: '#ff4b4b'}
    
    # Left: Box Plot (Revenue별로 분리)
    fig_detail.add_trace(
        go.Box(
            y=df[df['Revenue'] == True][selected_num_col],
            name="구매 완료 (True)",
            marker_color=colors[True],
            boxpoints='outliers',
            jitter=0.3
        ),
        row=1, col=1
    )
    fig_detail.add_trace(
        go.Box(
            y=df[df['Revenue'] == False][selected_num_col],
            name="구매 미완료 (False)",
            marker_color=colors[False],
            boxpoints='outliers',
            jitter=0.3
        ),
        row=1, col=1
    )
    
    # Right: Histogram (Revenue별로 오버레이)
    fig_detail.add_trace(
        go.Histogram(
            x=df[df['Revenue'] == True][selected_num_col],
            name="구매 완료 (True)",
            marker_color=colors[True],
            opacity=0.6,
            nbinsx=40
        ),
        row=1, col=2
    )
    fig_detail.add_trace(
        go.Histogram(
            x=df[df['Revenue'] == False][selected_num_col],
            name="구매 미완료 (False)",
            marker_color=colors[False],
            opacity=0.6,
            nbinsx=40
        ),
        row=1, col=2
    )
    
    fig_detail.update_layout(
        barmode='overlay',
        height=500,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#fafafa'
    )
    fig_detail.update_xaxes(showgrid=True, gridcolor='#2e3440')
    fig_detail.update_yaxes(showgrid=True, gridcolor='#2e3440')
    
    st.plotly_chart(fig_detail, use_container_width=True)
    
    # 기술통계 데이터프레임 생성 및 표시
    desc_df = df.groupby('Revenue')[selected_num_col].describe()
    desc_df.index = desc_df.index.map({True: '구매 완료 (True)', False: '구매 미완료 (False)'})
    
    counts = df.groupby('Revenue')[selected_num_col].count()
    pcts = (counts / len(df)) * 100
    
    desc_df.insert(0, '샘플 비율 (%)', pcts)
    desc_df.insert(0, '세션 빈도 (건수)', counts)
    
    st.markdown(f"##### 📋 '{selected_num_col}' 변수의 Revenue 그룹별 요약 기술통계")
    st.dataframe(desc_df.style.format({
        '샘플 비율 (%)': '{:.2f}%',
        'mean': '{:.3f}',
        'std': '{:.3f}',
        'min': '{:.3f}',
        '25%': '{:.3f}',
        '50%': '{:.3f}',
        '75%': '{:.3f}',
        'max': '{:.3f}'
    }))
    
    insights = {
        'Administrative': "관리 페이지 방문 횟수입니다. 구매 완료 고객이 대체로 관리 페이지 방문 횟수가 높은 편입니다.",
        'Administrative_Duration': "관리 페이지 체류 시간입니다. 체류 시간이 길수록 서비스 탐색 의도가 높은 것을 의미합니다.",
        'Informational': "정보 제공형 페이지(FAQ, 회사 소개 등) 방문 횟수입니다.",
        'Informational_Duration': "정보 제공형 페이지에서의 체류 시간입니다.",
        'ProductRelated': "상품 상세 정보 페이지 방문 횟수입니다. 구매 고객은 미구매 고객에 비해 확연히 많은 상품 페이지를 탐색합니다.",
        'ProductRelated_Duration': "상품 상세 정보 페이지에서의 누적 체류 시간입니다.",
        'BounceRates': "이탈률입니다. 첫 페이지 방문 후 즉시 나간 비율로, 구매 고객의 이탈률은 극히 낮은 수치를 보입니다.",
        'ExitRates': "종료율입니다. 세션 내 마지막으로 나간 페이지 비율로, 구매 고객 그룹은 이 수치가 낮게 유지됩니다.",
        'PageValues': "페이지 가치 점수입니다. 구매가 발생한 세션에서 방문한 페이지들에 부여되는 평균 점수로, **구매 예측에 가장 핵심적인 변수**입니다.",
        'SpecialDay': "특정 특별일(어머니날, 발렌타인데이 등)과의 인접도로, 구매 의도 상승 기간 분석에 유용합니다."
    }
    st.info(f"💡 **변수 설명 및 인사이트**: {insights.get(selected_num_col, '')}")

    st.markdown("---")
    st.subheader("📂 모든 수치형 변수 일괄 비교 (Expander 목록)")
    st.markdown("각각의 수치형 변수에 대한 히스토그램, 박스플롯, 기술통계를 접이식 목록을 통해 바로 확인해 볼 수 있습니다.")

    for col in num_cols:
        with st.expander(f"🔍 [{col}] 변수 상세 시각화 & 기술통계 요약"):
            fig_col = make_subplots(
                rows=1, cols=2,
                subplot_titles=["Box Plot", "Histogram"],
                horizontal_spacing=0.15
            )
            
            # Left: Box Plot
            fig_col.add_trace(
                go.Box(
                    y=df[df['Revenue'] == True][col],
                    name="구매 완료 (True)",
                    marker_color=colors[True],
                    boxpoints='outliers',
                    jitter=0.3
                ),
                row=1, col=1
            )
            fig_col.add_trace(
                go.Box(
                    y=df[df['Revenue'] == False][col],
                    name="구매 미완료 (False)",
                    marker_color=colors[False],
                    boxpoints='outliers',
                    jitter=0.3
                ),
                row=1, col=1
            )
            
            # Right: Histogram
            fig_col.add_trace(
                go.Histogram(
                    x=df[df['Revenue'] == True][col],
                    name="구매 완료 (True)",
                    marker_color=colors[True],
                    opacity=0.6,
                    nbinsx=30
                ),
                row=1, col=2
            )
            fig_col.add_trace(
                go.Histogram(
                    x=df[df['Revenue'] == False][col],
                    name="구매 미완료 (False)",
                    marker_color=colors[False],
                    opacity=0.6,
                    nbinsx=30
                ),
                row=1, col=2
            )
            
            fig_col.update_layout(
                barmode='overlay',
                height=350,
                showlegend=True,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#fafafa',
                margin=dict(l=20, r=20, t=40, b=20)
            )
            fig_col.update_xaxes(showgrid=True, gridcolor='#2e3440')
            fig_col.update_yaxes(showgrid=True, gridcolor='#2e3440')
            
            st.plotly_chart(fig_col, use_container_width=True)
            
            # 기술통계
            d_df = df.groupby('Revenue')[col].describe()
            d_df.index = d_df.index.map({True: '구매 완료 (True)', False: '구매 미완료 (False)'})
            
            cnts = df.groupby('Revenue')[col].count()
            pts = (cnts / len(df)) * 100
            
            d_df.insert(0, '샘플 비율 (%)', pts)
            d_df.insert(0, '세션 빈도 (건수)', cnts)
            
            st.dataframe(d_df.style.format({
                '샘플 비율 (%)': '{:.2f}%',
                'mean': '{:.3f}',
                'std': '{:.3f}',
                'min': '{:.3f}',
                '25%': '{:.3f}',
                '50%': '{:.3f}',
                '75%': '{:.3f}',
                'max': '{:.3f}'
            }))


# ----------------- Tab 3: 범주형 변수 분석 -----------------
with tab3:
    st.header("📊 범주형 변수와 Revenue 비교 분석")
    st.markdown("범주형 변수의 각 항목별 세션 규모(**빈도**)와 각 항목 내에서의 구매 전환 비율(**100% Stacked 비율**)을 1행 2열 서브플롯으로 비교 분석합니다.")
    
    cat_cols = ['Month', 'VisitorType', 'Weekend_Str', 'OperatingSystems', 'Browser', 'Region', 'TrafficType']
    
    st.subheader("🔍 변수별 상세 비교 분석 (빈도 막대 & 100% 비율 막대 + 교차분석)")
    st.markdown("분석하고자 하는 범주형 변수를 아래 드롭다운에서 선택해 주세요. 해당 변수의 빈도 분포와 Revenue 비율 분포가 서브플롯으로 표시됩니다.")
    
    selected_cat_col = st.selectbox("분석할 범주형 변수 선택:", options=cat_cols)
    
    # 1행 2열 서브플롯 구성 (좌: 빈도, 우: 100% 비율)
    fig_cat_detail = make_subplots(
        rows=1, cols=2,
        subplot_titles=[f"[{selected_cat_col}] 세션 빈도 (건수)", f"[{selected_cat_col}] 구매 전환 비율 (100% Stacked)"],
        horizontal_spacing=0.15
    )
    
    colors_cat = {'구매 완료 (True)': '#00ffcc', '구매 미완료 (False)': '#ff4b4b'}
    
    # 1. 좌측 그래프: 일반 Grouped Bar (절대 빈도)
    freq_df = df.groupby([selected_cat_col, 'Revenue_Str']).size().reset_index(name='Count')
    
    for rev_status in ['구매 완료 (True)', '구매 미완료 (False)']:
        sub_df = freq_df[freq_df['Revenue_Str'] == rev_status]
        fig_cat_detail.add_trace(
            go.Bar(
                x=sub_df[selected_cat_col],
                y=sub_df['Count'],
                name=rev_status,
                marker_color='#00ffcc' if '구매 완료' in rev_status else '#ff4b4b',
                showlegend=True
            ),
            row=1, col=1
        )
        
    # 2. 우측 그래프: 100% Stacked Bar (상대 비율, 높이를 동일하게 비교)
    ct = pd.crosstab(df[selected_cat_col], df['Revenue_Str'], normalize='index') * 100
    
    if '구매 미완료 (False)' in ct.columns:
        fig_cat_detail.add_trace(
            go.Bar(
                x=ct.index,
                y=ct['구매 미완료 (False)'],
                name='구매 미완료 (비율)',
                marker_color='#ff4b4b',
                showlegend=False
            ),
            row=1, col=2
        )
    if '구매 완료 (True)' in ct.columns:
        fig_cat_detail.add_trace(
            go.Bar(
                x=ct.index,
                y=ct['구매 완료 (True)'],
                name='구매 완료 (비율)',
                marker_color='#00ffcc',
                showlegend=False
            ),
            row=1, col=2
        )
        
    fig_cat_detail.update_layout(
        barmode='stack',
        height=500,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#fafafa'
    )
    fig_cat_detail.update_xaxes(type='category', showgrid=True, gridcolor='#2e3440')
    fig_cat_detail.update_yaxes(showgrid=True, gridcolor='#2e3440')
    
    st.plotly_chart(fig_cat_detail, use_container_width=True)
    
    # 교차표 계산 및 출력
    cross_tab = pd.crosstab(df[selected_cat_col], df['Revenue'], margins=True, margins_name='전체 합계')
    
    # 전환율(구매 완료 비율) 계산
    conversion_rates = []
    for idx_val in cross_tab.index:
        t_val = cross_tab.loc[idx_val, True]
        total_val = cross_tab.loc[idx_val, '전체 합계']
        rate = (t_val / total_val * 100) if total_val > 0 else 0.0
        conversion_rates.append(rate)
        
    cross_tab['구매 전환율 (%)'] = conversion_rates
    cross_tab.columns = ['구매 미완료 (False) 빈도', '구매 완료 (True) 빈도', '총 세션 수', '구매 전환율 (%)']
    
    st.markdown(f"##### 📋 '{selected_cat_col}' 변수의 Revenue 교차 분석 테이블")
    st.dataframe(cross_tab.style.format({
        '구매 미완료 (False) 빈도': '{:,}',
        '구매 완료 (True) 빈도': '{:,}',
        '총 세션 수': '{:,}',
        '구매 전환율 (%)': '{:.2f}%'
    }))
    
    cat_insights = {
        'Month': "대체로 11월(Nov), 5월(May) 등에 세션 방문이 많으며, 특히 11월은 높은 구매 전환율을 보이는 경향이 있습니다.",
        'VisitorType': "신규 방문자(New_Visitor)는 재방문자(Returning_Visitor)에 비해 상대적으로 구매 전환율이 높은 트렌드를 보입니다.",
        'Weekend_Str': "주말 여부에 따른 전환율 편차는 미미한 편이나, 주말 세션 수가 평일 대비 일별 분포에서 어떻게 작용하는지 확인할 수 있습니다.",
        'OperatingSystems': "특정 OS 환경을 사용하는 사용자층의 세션 수 및 구매 비율을 나타냅니다.",
        'Browser': "방문자가 사용하는 브라우저 종류에 따른 전환율 정보입니다.",
        'Region': "사용자 접속 지역에 따른 구매 의도 차이를 보여줍니다.",
        'TrafficType': "유입 경로(트래픽 소스 유형)별로 구매 의사가 있는 사용자의 비율이 유의미하게 다를 수 있음을 시사합니다."
    }
    st.info(f"💡 **변수 설명 및 인사이트**: {cat_insights.get(selected_cat_col, '')}")

    st.markdown("---")
    st.subheader("📂 모든 범주형 변수 일괄 비교 (Expander 목록)")
    st.markdown("각각의 범주형 변수에 대해 [빈도 막대]와 [높이가 일치된 100% 비율 막대] 서브플롯, 그리고 하단의 교차 분석표를 바로 확인해 볼 수 있습니다.")

    for col in cat_cols:
        with st.expander(f"🔍 [{col}] 변수 상세 시각화 & 교차 통계 요약"):
            fig_col = make_subplots(
                rows=1, cols=2,
                subplot_titles=["세션 빈도 (건수)", "구매 전환 비율 (100% Stacked)"],
                horizontal_spacing=0.15
            )
            
            # Left: Freq Grouped Bar
            freq_col_df = df.groupby([col, 'Revenue_Str']).size().reset_index(name='Count')
            for rev_status in ['구매 완료 (True)', '구매 미완료 (False)']:
                sub_col_df = freq_col_df[freq_col_df['Revenue_Str'] == rev_status]
                fig_col.add_trace(
                    go.Bar(
                        x=sub_col_df[col],
                        y=sub_col_df['Count'],
                        name=rev_status,
                        marker_color='#00ffcc' if '구매 완료' in rev_status else '#ff4b4b',
                        showlegend=False
                    ),
                    row=1, col=1
                )
                
            # Right: 100% Stacked Bar
            ct_col = pd.crosstab(df[col], df['Revenue_Str'], normalize='index') * 100
            if '구매 미완료 (False)' in ct_col.columns:
                fig_col.add_trace(
                    go.Bar(
                        x=ct_col.index,
                        y=ct_col['구매 미완료 (False)'],
                        name='구매 미완료',
                        marker_color='#ff4b4b',
                        showlegend=False
                    ),
                    row=1, col=2
                )
            if '구매 완료 (True)' in ct_col.columns:
                fig_col.add_trace(
                    go.Bar(
                        x=ct_col.index,
                        y=ct_col['구매 완료 (True)'],
                        name='구매 완료',
                        marker_color='#00ffcc',
                        showlegend=False
                    ),
                    row=1, col=2
                )
                
            fig_col.update_layout(
                barmode='stack',
                height=350,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#fafafa',
                margin=dict(l=20, r=20, t=40, b=20)
            )
            fig_col.update_xaxes(type='category', showgrid=True, gridcolor='#2e3440')
            fig_col.update_yaxes(showgrid=True, gridcolor='#2e3440')
            
            st.plotly_chart(fig_col, use_container_width=True)
            
            # Crosstab
            c_tab = pd.crosstab(df[col], df['Revenue'], margins=True, margins_name='전체 합계')
            c_rates = []
            for idx_val in c_tab.index:
                t_val = c_tab.loc[idx_val, True]
                total_val = c_tab.loc[idx_val, '전체 합계']
                rate = (t_val / total_val * 100) if total_val > 0 else 0.0
                c_rates.append(rate)
            c_tab['구매 전환율 (%)'] = c_rates
            c_tab.columns = ['구매 미완료 (False) 빈도', '구매 완료 (True) 빈도', '총 세션 수', '구매 전환율 (%)']
            
            st.dataframe(c_tab.style.format({
                '구매 미완료 (False) 빈도': '{:,}',
                '구매 완료 (True) 빈도': '{:,}',
                '총 세션 수': '{:,}',
                '구매 전환율 (%)': '{:.2f}%'
            }))


# ----------------- Tab 4: 상관관계 및 중요도 분석 -----------------
with tab4:
    st.header("🧠 다변량 분석 및 머신러닝 기반 특징 중요도")
    
    st.subheader("🔗 수치형 변수 상관관계 분석 (Pearson Correlation)")
    
    # 수치형 변수 상관계수 행렬 구하기
    corr_matrix = df[num_cols].corr()
    
    # 히트맵 그리기
    fig_corr = px.imshow(
        corr_matrix,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu",
        range_color=[-1, 1],
        title="수치형 변수 간 상관계수 히트맵"
    )
    fig_corr.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#fafafa',
        height=600
    )
    st.plotly_chart(fig_corr, use_container_width=True)
    
    # 다중공선성 정보 안내
    st.markdown("""
    > ⚠️ **상관관계 주요 탐색 포인트**:
    > - `BounceRates`(이탈률)와 `ExitRates`(종료율)는 **0.91** 수준의 매우 강한 양의 상관관계를 가집니다. 분석 및 예측 모델 개발 시 다중공선성(Multicollinearity)에 유의해야 합니다.
    > - `ProductRelated`와 `ProductRelated_Duration` 역시 강한 상관관계(약 0.86)를 가집니다. 상품 상세 페이지를 많이 볼수록 해당 페이지에서의 누적 체류 시간이 비례해서 늘어나기 때문입니다.
    """)
    
    st.markdown("---")
    st.subheader("🔑 Random Forest 기반 특징 중요도 (Feature Importance)")
    st.markdown("기계학습 모델(Random Forest Classifier)을 이용해 어떤 변수가 고객의 실제 구매 완료(`Revenue`) 결정에 가장 크게 기여하는지 평가합니다.")
    
    with st.spinner("특징 중요도를 분석 중입니다..."):
        # 모델 데이터 준비
        X = df_raw.copy()
        y = X['Revenue'].astype(int)
        
        # 모델 학습용 수치형 변수 선택
        features_num = num_cols.copy()
        X_model = X[features_num].copy()
        X_model['Weekend'] = X['Weekend'].astype(int)
        
        rf = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
        rf.fit(X_model, y)
        
        importances = rf.feature_importances_
        feature_names = X_model.columns
        
        importance_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importances
        }).sort_values('Importance', ascending=True)
        
        # 중요도 시각화 (Plotly)
        fig_imp = px.bar(
            importance_df,
            x='Importance',
            y='Feature',
            orientation='h',
            title='Random Forest Feature Importance (구매 영향도)',
            color='Importance',
            color_continuous_scale='Viridis'
        )
        fig_imp.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            height=500
        )
        st.plotly_chart(fig_imp, use_container_width=True)
        
        st.markdown("""
        > 💡 **중요도 해석**:
        > - **`PageValues`**가 압도적으로 높은 기여도를 보여줍니다. 이는 사용자가 거쳐간 페이지들의 가치 점수가 높은 세션일수록 실제 구매 결정으로 강하게 이어진다는 것을 실증합니다.
        > - 뒤이어 `ProductRelated_Duration` 및 `ExitRates` 등이 중요한 행동 지표로 작용합니다.
        """)


# ----------------- Tab 5: 퍼널 분석 (Funnel) -----------------
with tab5:
    st.header("🌪️ 쇼핑객 구매 여정 퍼널(Funnel) 분석")
    st.markdown("전체 방문 세션부터 상품 탐색, 관심 등록(고가치 페이지 방문), 그리고 최종 구매에 이르기까지의 핵심 단계별 전환과 이탈 현황을 분석합니다.")
    
    # 1. 퍼널 데이터 정의 및 계산
    # Step 1: 전체 방문 세션 (All Sessions)
    s1_cnt = len(df)
    
    # Step 2: 상품 상세 정보 탐색 세션 (Product Views - ProductRelated > 0)
    s2_cnt = len(df[df['ProductRelated'] > 0])
    
    # Step 3: 결제 관심/장바구니 추가 의심 세션 (Cart / Checkout Intent - PageValues > 0)
    s3_cnt = len(df[df['PageValues'] > 0])
    
    # Step 4: 최종 구매 완료 세션 (Purchase Completed - Revenue == True)
    s4_cnt = len(df[df['Revenue'] == True])
    
    # 데이터프레임 구축
    funnel_data = pd.DataFrame({
        '단계 (Stage)': [
            '1. 사이트 유입 (All Sessions)', 
            '2. 상품 탐색 (Product Views)', 
            '3. 결제 관심/장바구니 진입 (Cart/Checkout Intent)', 
            '4. 최종 구매 완료 (Purchase Completed)'
        ],
        '세션 수 (Users)': [s1_cnt, s2_cnt, s3_cnt, s4_cnt]
    })
    
    # 퍼널 계산 지표 보완
    total_sessions_val = funnel_data.loc[0, '세션 수 (Users)']
    
    # 전환율 및 이탈률 연산
    pct_first = [] # 첫 단계 대비 비율
    pct_prev = []  # 이전 단계 대비 비율 (전환율)
    drop_rates = [] # 이전 단계 대비 이탈률
    
    for i in range(len(funnel_data)):
        current_users = funnel_data.loc[i, '세션 수 (Users)']
        
        # 첫 단계 대비 비율
        pct_first.append((current_users / total_sessions_val * 100) if total_sessions_val > 0 else 0.0)
        
        # 이전 단계 대비 비율 및 이탈률
        if i == 0:
            pct_prev.append(100.0)
            drop_rates.append(0.0)
        else:
            prev_users = funnel_data.loc[i-1, '세션 수 (Users)']
            conversion = (current_users / prev_users * 100) if prev_users > 0 else 0.0
            pct_prev.append(conversion)
            drop_rates.append(100.0 - conversion)
            
    funnel_data['첫 단계 대비 비율 (%)'] = pct_first
    funnel_data['이전 단계 대비 전환율 (%)'] = pct_prev
    funnel_data['단계별 이탈률 (%)'] = drop_rates
    
    # 레이아웃 구성 (좌측: 퍼널 차트, 우측: 퍼널 지표 표)
    funnel_col1, funnel_col2 = st.columns([3, 2])
    
    with funnel_col1:
        st.subheader("🌪️ 구매 여정 퍼널 차트")
        # Plotly Funnel Chart 그리기
        fig_funnel = px.funnel(
            funnel_data,
            x='세션 수 (Users)',
            y='단계 (Stage)',
            title='온라인 쇼핑몰 세션 구매 전환 깔때기',
            color_discrete_sequence=['#00ffcc']
        )
        fig_funnel.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            height=450
        )
        st.plotly_chart(fig_funnel, use_container_width=True)
        
    with funnel_col2:
        st.subheader("📊 단계별 퍼널 통계 테이블")
        st.dataframe(
            funnel_data.style.format({
                '세션 수 (Users)': '{:,}건',
                '첫 단계 대비 비율 (%)': '{:.2f}%',
                '이전 단계 대비 전환율 (%)': '{:.2f}%',
                '단계별 이탈률 (%)': '{:.2f}%'
            }),
            height=250
        )
        
        # 이탈 경고 및 주의사항 표시
        max_drop_idx = funnel_data['단계별 이탈률 (%)'].idxmax()
        max_drop_stage = funnel_data.loc[max_drop_idx, '단계 (Stage)']
        max_drop_val = funnel_data.loc[max_drop_idx, '단계별 이탈률 (%)']
        
        st.warning(
            f"🚨 **가장 큰 이탈 지점:**\n"
            f"'{max_drop_stage}' 단계에서 **{max_drop_val:.2f}%**의 가장 높은 이탈률이 포착되었습니다. "
            f"이 구간의 사용자 행동 로그를 정밀 분석하고 개선할 필요가 있습니다."
        )

    st.markdown("---")
    st.subheader("💡 쇼핑객 구매 여정(Funnel) 상세 과정 설명 및 인사이트")
    
    # 4단계 퍼널 단계별 설명 텍스트
    st.markdown(f"""
    온라인 쇼핑몰 구매 여정은 다음과 같이 4가지 주요 이정표로 구분됩니다:
    
    1. **1단계: 사이트 유입 (All Sessions)**
       - 쇼핑몰에 접속한 전체 방문 세션입니다. 유입량은 분석 필터에 지정한 조건에 따라 변동됩니다.
       
    2. **2단계: 상품 탐색 (Product Views)**
       - 전체 방문객 중 **상품 상세 페이지(`ProductRelated`)를 1회 이상 조회한 세션**입니다.
       - 일반적으로 유입 세션의 95% 이상이 이 단계에 도달하여, 사이트 진입 후 대다수가 상품을 확인하는 양상을 보입니다. 
       - 만약 이 단계에서의 이탈률이 비정상적으로 높다면, 광고 유입 페이지(Landing Page) 매칭 실패 또는 초기 상품 노출 실패를 의심해야 합니다.
       
    3. **3단계: 결제 관심/장바구니 진입 (Cart/Checkout Intent)**
       - 상품 정보 확인 수준을 넘어, **실제 장바구니에 상품을 담거나 주문서 작성 등으로 페이지 가치(`PageValues > 0`)가 잡힌 고가치 관심 세션**입니다.
       - **핵심 이탈 지점:** 상품 탐색 단계에서 장바구니 진입 단계 사이에서 **대규모 이탈**이 흔히 발생합니다. (보통 70% 이상의 사용자가 이탈)
       - 구매 유도를 위한 장바구니 추가 유도 UI, 실시간 혜택 배너 노출, 리뷰 신뢰도 보완 등의 최적화 작업이 필요한 핵심 관문입니다.
       
    4. **4단계: 최종 구매 완료 (Purchase Completed)**
       - 실제 구매 결제에 성공하여 `Revenue`가 **True**로 전환된 최종 성과 세션입니다.
       - 장바구니/결제 시도(3단계)에 도달한 사용자들의 최종 결제 완료(4단계) 전환율은 상당히 높게 나타납니다. (대체로 70~80% 내외)
       - 이 최종 관문에서 이탈하는 고객은 주로 **'복잡한 결제 프로세스'**, **'추가 배송비 부담'**, **'할인 수단 적용 불가'** 등의 이유로 결제를 포기하므로, 간편 결제수단 도입 및 장바구니 리타게팅 이메일/알림톡 발송 등의 개선책이 유효합니다.
    """)

