"""
온라인 쇼핑객 구매 의도 예측을 위한 디시전 트리(Decision Tree) 머신러닝 페이지입니다.

주요 기능:
- 머신러닝 모델링의 전반적인 과정을 Mermaid 파이프라인으로 시각화
- 의사결정나무 모델의 하이퍼파라미터(Max Depth, Min Samples Split, Criterion, Test Size) 실시간 조절 및 인터랙티브 학습
- 5가지 분류 평가지표(정확도, 정밀도, 재현율, F1-Score, ROC-AUC) 산출 및 시각화 (Confusion Matrix, ROC 곡선, PR 곡선 등)
- 학습된 의사결정나무 모델의 피처 중요도(Feature Importance) 분석 및 Plotly 가로 막대 그래프 시각화
- 디시전 트리 구조 시각화 (Matplotlib plot_tree 및 export_text 텍스트 규칙 렌더링)
"""
import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree, export_text
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    roc_curve,
    precision_recall_curve
)

# 폰트 깨짐 방지를 위한 한글 지원 설정 (Matplotlib용)
# Windows 환경이므로 Malgun Gothic을 기본으로 사용
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 페이지 설정 (멀티페이지 앱의 개별 페이지이므로 단독 타이틀 설정 가능)
st.set_page_config(
    page_title="온라인 쇼핑객 구매 예측 머신러닝",
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

# Mermaid 텍스트를 HTML/JS로 렌더링하기 위한 헬퍼 함수
def draw_mermaid(mermaid_code: str, height: int = 400):
    """
    Mermaid 코드를 받아 HTML/JS로 렌더링하는 함수입니다.
    CDN에서 mermaid.esm.min.mjs를 로드하여 로컬 브라우저에서 직접 렌더링합니다.
    """
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                background-color: transparent;
                margin: 0;
                overflow: hidden;
            }}
            .mermaid {{
                display: flex;
                justify-content: center;
                align-items: center;
            }}
        </style>
    </head>
    <body>
        <pre class="mermaid">
            {mermaid_code}
        </pre>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ 
                startOnLoad: true, 
                theme: 'dark',
                themeVariables: {{
                    background: '#0e1117',
                    primaryColor: '#1e222b',
                    primaryTextColor: '#fafafa',
                    lineColor: '#00ffcc'
                }}
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=height, scrolling=True)


# 1. 데이터 로드 (캐싱 활용)
@st.cache_data
def load_ml_data():
    # 여러 상대 경로 후보군 탐색하여 안정적인 로드 보장
    paths = [
        "online-shoppers/data/online_shoppers_intention.csv",
        "data/online_shoppers_intention.csv",
        "../data/online_shoppers_intention.csv",
        "../../data/online_shoppers_intention.csv"
    ]
    
    file_path = None
    for p in paths:
        if os.path.exists(p):
            file_path = p
            break
            
    if file_path is None:
        raise FileNotFoundError("데이터셋 파일을 찾을 수 없습니다. 경로 설정을 확인하세요.")
        
    df = pd.read_csv(file_path)
    return df

try:
    df_raw = load_ml_data()
except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    st.stop()

# 소개 및 타이틀
st.title("🧠 Decision Tree 기반 구매 의도 예측 모델")
st.markdown("""
이 페이지에서는 온라인 쇼핑객의 방문 세션 데이터를 기반으로 실제 구매 완료 여부(`Revenue`)를 예측하는 **의사결정나무(Decision Tree) 분류 모델**을 구축하고 평가합니다.
오른쪽 사이드바를 통해 하이퍼파라미터를 유연하게 조정하여 최적의 모델 성능을 찾아보세요.
""")

# 2. 사이드바 하이퍼파라미터 컨트롤러 구성
st.sidebar.title("🛠️ 모델 하이퍼파라미터 설정")
st.sidebar.markdown("---")

max_depth = st.sidebar.slider(
    "🌳 최대 깊이 (Max Depth)",
    min_value=1,
    max_value=10,
    value=4,
    help="의사결정나무의 최대 깊이를 지정합니다. 너무 높으면 과적합(Overfitting)의 위험이 있습니다."
)

min_samples_split = st.sidebar.slider(
    "🌱 분할 최소 샘플 수 (Min Samples Split)",
    min_value=2,
    max_value=100,
    value=20,
    step=2,
    help="자식 노드로 분할되기 위해 필요한 최소한의 샘플 수입니다."
)

criterion = st.sidebar.selectbox(
    "📊 불순도 기준 (Criterion)",
    options=["gini", "entropy", "log_loss"],
    index=0,
    help="노드 분할의 품질을 측정할 기준을 선택합니다."
)

test_size = st.sidebar.slider(
    "📐 검증 데이터 비율 (Test Size)",
    min_value=0.1,
    max_value=0.5,
    value=0.2,
    step=0.05,
    help="학습용 모델의 성능 검증을 위해 분할할 검증 데이터셋의 비율을 지정합니다."
)

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 모델 성능 개선 옵션")
use_oversampling = st.sidebar.toggle(
    "오버샘플링 (Recall 개선)",
    value=True,
    help="학습 데이터셋의 구매(True) 클래스를 오버샘플링하여 Recall(재현율)을 획기적으로 개선합니다. 오직 학습(Train) 데이터에만 적용됩니다."
)

# 3. 데이터 전처리 파이프라인
# 범주형 변수를 모델이 인식할 수 있도록 원-핫 인코딩(One-Hot Encoding)을 적용합니다.
with st.spinner("데이터 전처리 중..."):
    # 타겟 및 독립변수 분리
    X = df_raw.copy()
    y = X['Revenue'].astype(int)
    
    # 모델 입력에 사용하지 않을 파생/결과 컬럼 제거
    if 'Revenue_Str' in X.columns:
        X = X.drop(columns=['Revenue_Str'])
    if 'Weekend_Str' in X.columns:
        X = X.drop(columns=['Weekend_Str'])
        
    X = X.drop(columns=['Revenue'])
    
    # Weekend 불리언 값을 정수형(0/1)으로 인코딩
    if 'Weekend' in X.columns:
        X['Weekend'] = X['Weekend'].astype(int)
        
    # 문자형 범주형 변수(Month, VisitorType) 원-핫 인코딩 적용
    categorical_cols = ['Month', 'VisitorType']
    X = pd.get_dummies(X, columns=categorical_cols, drop_first=True)
    
    # 원-핫 인코딩으로 생겨난 bool 타입을 int(0/1)로 형변환
    X = X.astype(float)

# 4. 데이터셋 분할 및 모델 학습
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=test_size, random_state=42, stratify=y
)

# 학습 데이터셋 오버샘플링 적용 여부 결정 (오버샘플링은 Train에만 적용하여 데이터 누수를 방지합니다)
if use_oversampling:
    df_train = pd.concat([X_train, y_train], axis=1)
    df_majority = df_train[df_train['Revenue'] == 0]
    df_minority = df_train[df_train['Revenue'] == 1]
    
    # 소수 클래스 무작위 복제 오버샘플링 (다수 클래스 수에 일치시킴)
    df_minority_oversampled = df_minority.sample(len(df_majority), replace=True, random_state=42)
    df_oversampled = pd.concat([df_majority, df_minority_oversampled])
    
    X_train_model = df_oversampled.drop(columns=['Revenue'])
    y_train_model = df_oversampled['Revenue']
else:
    X_train_model = X_train.copy()
    y_train_model = y_train.copy()

dt_model = DecisionTreeClassifier(
    max_depth=max_depth,
    min_samples_split=min_samples_split,
    criterion=criterion,
    random_state=42
)
dt_model.fit(X_train_model, y_train_model)

# 예측 수행 (Test 검증용 및 Train 학습 성능 둘 다 수행)
y_pred = dt_model.predict(X_test)
y_prob = dt_model.predict_proba(X_test)[:, 1]

y_pred_train = dt_model.predict(X_train_model)
y_prob_train = dt_model.predict_proba(X_train_model)[:, 1]

# 5. 평가지표 산출 (5가지 필수) - Test 성능
acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred, zero_division=0)
rec = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_prob)

# Train 성능 (과적합 진단용)
acc_train = accuracy_score(y_train_model, y_pred_train)
prec_train = precision_score(y_train_model, y_pred_train, zero_division=0)
rec_train = recall_score(y_train_model, y_pred_train)
f1_train = f1_score(y_train_model, y_pred_train)
roc_auc_train = roc_auc_score(y_train_model, y_prob_train)

# 평가지표 데이터프레임 (Test 기준)
metrics_summary = pd.DataFrame({
    "평가지표 (Metrics)": ["정확도 (Accuracy)", "정밀도 (Precision)", "재현율 (Recall)", "F1-Score", "ROC-AUC"],
    "성능 수치 (Score)": [acc, prec, rec, f1, roc_auc]
})

# 과적합 분석용 데이터프레임 (Train vs Test 비교)
compare_df = pd.DataFrame({
    "평가지표 (Metrics)": ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"] * 2,
    "데이터셋 (Dataset)": ["학습용 (Train)"] * 5 + ["검증용 (Test)"] * 5,
    "성능 수치 (Score)": [
        acc_train, prec_train, rec_train, f1_train, roc_auc_train,
        acc, prec, rec, f1, roc_auc
    ]
})

# 레이아웃 탭 구성
tab_proc, tab_eval, tab_tree = st.tabs([
    "⛓️ 머신러닝 프로세스 과정",
    "📈 모델 성능 평가 및 시각화",
    "🌳 디시전 트리 구조 및 피처 중요도"
])

# ----------------- Tab 1: 머신러닝 프로세스 과정 -----------------
with tab_proc:
    st.header("⛓️ 머신러닝 파이프라인 프로세스 흐름")
    st.markdown("의사결정나무 모델의 데이터 처리 및 학습 절차를 시각적으로 도식화한 흐름도입니다.")
    
    # Mermaid 시각화
    mermaid_code = """
    graph TD
        A[Original Data: online_shoppers_intention.csv] --> B[Data Preprocessing]
        B --> B1[타겟 변수 Revenue 분리 및 int형 변환]
        B --> B2[불리언 변수 Weekend int형 변환]
        B --> B3[범주형 변수 Month, VisitorType 원-핫 인코딩]
        B3 --> C[Data Splitting: Train/Test]
        C --> D[Decision Tree Classifier 학습]
        D --> E[모델 예측: 클래스 예측 및 확률 예측]
        E --> F[성능 검증: 5대 평가지표 분석]
        F --> F1[Accuracy / Precision / Recall / F1-Score / ROC-AUC]
        E --> G[구조 및 특징 분석]
        G --> G1[Feature Importance 분석]
        G --> G2[Tree Node 분할 조건 시각화]
    """
    draw_mermaid(mermaid_code, height=450)
    
    st.subheader("데이터셋 및 분할 정보 요약")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 전체 데이터 수", f"{len(df_raw):,} 건")
    with col2:
        st.metric("📈 학습용 데이터(Train)", f"{len(X_train):,} 건")
    with col3:
        st.metric("🧪 검증용 데이터(Test)", f"{len(X_test):,} 건")

# ----------------- Tab 2: 모델 성능 평가 및 시각화 -----------------
with tab_eval:
    st.header("📈 모델 성능 평가 지표 (5가지)")
    st.markdown("모델의 예측 정확성과 실질 성능을 대변하는 5대 분류 평가지표를 상세 비교합니다.")
    
    # 상단 KPI 메트릭 카드
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    m_col1.metric("📊 정확도 (Accuracy)", f"{acc * 100:.2f}%", help="전체 예측 중 올바르게 분류한 비율")
    m_col2.metric("🎯 정밀도 (Precision)", f"{prec * 100:.2f}%", help="구매할 것으로 예측한 세션 중 실제 구매한 비율")
    m_col3.metric("📢 재현율 (Recall)", f"{rec * 100:.2f}%", help="실제 구매한 고객 중 모델이 잡아낸 비율")
    m_col4.metric("⚖️ F1-Score", f"{f1 * 100:.2f}%", help="정밀도와 재현율의 조화 평균값")
    m_col5.metric("📈 ROC-AUC", f"{roc_auc:.4f}", help="분류기의 변별력 지수 (1에 가까울수록 성능 우수)")
    
    st.markdown("---")
    st.subheader("🔍 학습용 (Train) vs 검증용 (Test) 성능 교차 비교 및 과적합 자가진단")
    st.markdown("모델이 학습 세트에 과도하게 쏠려서 일반화 능력이 상실되었는지(Overfitting), 혹은 학습 자체가 부족한지(Underfitting) 실시간으로 진단합니다.")
    
    col_diag_1, col_diag_2 = st.columns([1, 1])
    
    with col_diag_1:
        st.markdown("#### 🔬 모델 적합도 실시간 진단 피드백")
        
        # F1-Score 격차 및 Accuracy 격차 계산
        f1_gap = f1_train - f1
        acc_gap = acc_train - acc
        
        if acc_train < 0.75:
            st.error(f"### ⚠️ 과소적합 (Underfitting) 상태 감지\n\n"
                     f"**진단 수치:** 학습용 정확도: `{acc_train*100:.2f}%` / 검증용 정확도: `{acc*100:.2f}%`\n\n"
                     "현재 모델은 학습용과 검증용 데이터셋 모두에서 비즈니스 기준치(75%) 이하의 현저히 낮은 분류 성능을 보여주고 있습니다. "
                     "의사결정나무 모델이 데이터의 패턴을 학습하기에 지나치게 단순한 구조로 설계되었습니다.\n\n"
                     "**💡 개선을 위한 비즈니스/개발 액션:**\n"
                     "- 사이드바 설정에서 **최대 깊이 (Max Depth)**를 점진적으로 늘려 트리의 표현력을 키우세요.\n"
                     "- **분할 최소 샘플 수 (Min Samples Split)** 파라미터를 낮게(예: 10 이하) 설정하여 분기를 더 세분화하도록 허용하세요.")
        elif f1_gap > 0.08:
            st.warning(f"### ⚠️ 과적합 (Overfitting) 상태 경고\n\n"
                       f"**진단 수치:** 학습용 F1: `{f1_train*100:.2f}%` / 검증용 F1: `{f1*100:.2f}%` (격차: `{f1_gap*100:.2f}%`)\n\n"
                       "학습용 점수가 검증용 점수보다 비정상적으로 높으며, 두 스코어의 격차가 일반화 임계치(8%)를 크게 초과하였습니다. "
                       "모델이 학습용 데이터셋에만 편향되어, 새로운 고객 데이터(Test set)에 대해 예측 오류를 양산할 가능성이 큽니다.\n\n"
                       "**💡 개선을 위한 비즈니스/개발 액션:**\n"
                       "- 사이드바 설정에서 **최대 깊이 (Max Depth)**를 줄여(예: 4 이하) 트리의 일반화력을 강화하세요.\n"
                       "- **분할 최소 샘플 수 (Min Samples Split)**를 30~50 이상으로 높여 너무 자잘하고 세세한 노드 분할을 억제하세요.")
        else:
            st.success(f"### ✅ 안정적인 최적 학습 (Optimal Fitting) 달성\n\n"
                       f"**진단 수치:** 학습용 F1: `{f1_train*100:.2f}%` / 검증용 F1: `{f1*100:.2f}%` (격차: `{f1_gap*100:.2f}%`)\n\n"
                       "두 데이터셋 간의 점수 편차가 매우 좁은 편(8% 이내)으로 안정적입니다. 모델이 훈련용 데이터의 특이적 노이즈를 제어하고, "
                       "새로운 환경에 대한 합리적인 추론 능력을 훌륭히 유지하고 있습니다. 현재 하이퍼파라미터 조합을 비즈니스 추론에 사용하는 것이 안전합니다.")
                       
    with col_diag_2:
        st.markdown("#### 📊 Train vs Test 주요 평가지표 비교 차트")
        fig_compare = px.bar(
            compare_df,
            x="성능 수치 (Score)",
            y="평가지표 (Metrics)",
            color="데이터셋 (Dataset)",
            barmode="group",
            orientation='h',
            text_auto=".3f",
            color_discrete_map={"학습용 (Train)": "#0099ff", "검증용 (Test)": "#00ffcc"},
            range_x=[0, 1.05]
        )
        fig_compare.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            height=320,
            margin=dict(l=20, r=20, t=10, b=20)
        )
        st.plotly_chart(fig_compare, use_container_width=True)
        st.caption("학습용 대비 검증용 데이터셋의 스코어 격차가 적어야 안정적인 모델입니다.")

    st.markdown("---")
    
    # 시각화 영역: 1행 2열 레이아웃
    vis_col1, vis_col2 = st.columns(2)
    
    with vis_col1:
        st.subheader("🏁 혼동 행렬 (Confusion Matrix)")
        cm = confusion_matrix(y_test, y_pred)
        
        # Plotly Heatmap을 활용한 고급스러운 혼동행렬 렌더링
        fig_cm = px.imshow(
            cm,
            x=["미구매 예측 (False)", "구매 예측 (True)"],
            y=["실제 미구매 (False)", "실제 구매 (True)"],
            text_auto=True,
            color_continuous_scale="BuGn",
            labels=dict(x="예측 결과", y="실제 정답", color="빈도 수")
        )
        fig_cm.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            height=380,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_cm, use_container_width=True)
        st.caption("혼동 행렬은 모델의 예측 성공(TP, TN)과 오류(FP, FN) 유형을 한눈에 대조해 줍니다.")

    with vis_col2:
        st.subheader("📊 5대 평가지표 종합 점수")
        
        # 평가지표 스코어 막대그래프 시각화
        fig_bar = px.bar(
            metrics_summary,
            x="성능 수치 (Score)",
            y="평가지표 (Metrics)",
            orientation='h',
            text_auto='.3f',
            color="성능 수치 (Score)",
            color_continuous_scale="Tealgrn",
            range_x=[0, 1.05]
        )
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            height=380,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("평가지표들이 100%(또는 1.0)에 가까울수록 예측 모델의 질이 우수함을 의미합니다.")
        
    st.markdown("---")
    
    # ROC Curve & PR Curve 2차 시각화 영역
    curve_col1, curve_col2 = st.columns(2)
    
    with curve_col1:
        st.subheader("📈 ROC 곡선 (ROC Curve)")
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        
        fig_roc = go.Figure()
        # 무작위 예측 기준선
        fig_roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', line=dict(dash='dash', color='gray'), name='Random (AUC = 0.5)'))
        # 모델 ROC 곡선
        fig_roc.add_trace(go.Scatter(x=fpr, y=tpr, mode='lines', line=dict(color='#00ffcc', width=3), name=f'Decision Tree (AUC = {roc_auc:.4f})'))
        
        fig_roc.update_layout(
            xaxis_title="FPR (1 - Specificity)",
            yaxis_title="TPR (Recall / Sensitivity)",
            xaxis=dict(range=[-0.01, 1.01]),
            yaxis=dict(range=[-0.01, 1.01]),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            height=400,
            legend=dict(x=0.55, y=0.1, bgcolor='rgba(30, 30, 30, 0.6)')
        )
        fig_roc.update_xaxes(showgrid=True, gridcolor='#2e3440')
        fig_roc.update_yaxes(showgrid=True, gridcolor='#2e3440')
        st.plotly_chart(fig_roc, use_container_width=True)
        st.caption("FPR(거짓 양성 비율) 대비 TPR(참 양성 비율)의 궤적을 그리며, 곡선 밑면적(AUC)이 넓을수록 우수합니다.")
        
    with curve_col2:
        st.subheader("🎯 정밀도-재현율 곡선 (Precision-Recall Curve)")
        prec_val, rec_val, _ = precision_recall_curve(y_test, y_prob)
        
        fig_pr = go.Figure()
        # 모델 PR 곡선
        fig_pr.add_trace(go.Scatter(x=rec_val, y=prec_val, mode='lines', line=dict(color='#ff4b4b', width=3), name='Precision-Recall Curve'))
        
        fig_pr.update_layout(
            xaxis_title="Recall (재현율)",
            yaxis_title="Precision (정밀도)",
            xaxis=dict(range=[-0.01, 1.01]),
            yaxis=dict(range=[-0.01, 1.01]),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            height=400
        )
        fig_pr.update_xaxes(showgrid=True, gridcolor='#2e3440')
        fig_pr.update_yaxes(showgrid=True, gridcolor='#2e3440')
        st.plotly_chart(fig_pr, use_container_width=True)
        st.caption("데이터의 불균형이 있을 때 유용한 지표로, 재현율이 높아짐에 따른 정밀도의 트레이드오프 변화를 관찰합니다.")

# ----------------- Tab 3: 디시전 트리 구조 및 피처 중요도 -----------------
with tab_tree:
    st.header("🌳 디시전 트리 구조 & 피처 중요도")
    st.markdown("모델이 의사결정을 내린 변수들의 중요성과 실제 노드 분기 프로세스를 분석합니다.")
    
    # 1. 피처 중요도 시각화
    st.subheader("🔑 피처 중요도 (Feature Importance)")
    
    importances = dt_model.feature_importances_
    features = X.columns
    
    importance_df = pd.DataFrame({
        "Feature": features,
        "Importance": importances
    }).sort_values(by="Importance", ascending=True)
    
    # 0보다 큰 피처 중요도를 가진 변수들만 하이라이트 가능
    fig_importance = px.bar(
        importance_df,
        x="Importance",
        y="Feature",
        orientation="h",
        color="Importance",
        color_continuous_scale="Plotly3",
        title="디시전 트리 분류 피처 기여도"
    )
    fig_importance.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#fafafa',
        height=500
    )
    st.plotly_chart(fig_importance, use_container_width=True)
    
    # 변수 해석 안내
    st.info("""
    💡 **피처 중요도 분석**:
    - 의사결정나무 모델에서도 **`PageValues`**가 가장 핵심적인 분할 기준 피처로 작용함을 볼 수 있습니다.
    - 그 외에도 `ProductRelated_Duration`, `ExitRates` 등 웹 탐색 여정 관련 행동 패턴 수치형 변수들이 상위 기여도를 형성하고 있습니다.
    """)
    
    st.markdown("---")
    
    # 2. 디시전 트리 시각화
    st.subheader("🌳 의사결정나무 시각화 (Decision Tree Structure)")
    st.markdown("설정된 최대 깊이에 따른 실제 노드의 조건과 클래스 결정 과정을 확인합니다. "
                "마우스 드래그를 통해 트리를 이동하고, 휠 스크롤을 이용해 **확대/축소(Zoom)**하여 상세 노드 글씨를 선명하게 조회할 수 있습니다.")
    
    # export_graphviz를 사용해 DOT 포맷 데이터 생성
    from sklearn.tree import export_graphviz
    
    # Windows 환경의 한글 깨짐 방지를 위해 Malgun Gothic 폰트 지정 및 클래스명 매핑
    dot_data = export_graphviz(
        dt_model,
        out_file=None,
        feature_names=list(X.columns),
        class_names=["미구매 (False)", "구매 (True)"],
        filled=True,
        rounded=True,
        special_characters=True,
        fontname="Malgun Gothic"
    )
    
    # Streamlit Graphviz 컴포넌트를 이용해 반응형 SVG 렌더링
    st.graphviz_chart(dot_data, use_container_width=True)
    
    st.markdown("---")
    
    # 3. 디시전 트리 텍스트 규칙 (export_text)
    st.subheader("📝 텍스트 기반 의사결정 규칙 (Decision Rules)")
    st.markdown("분기별 노드 기준을 명확한 IF-THEN 형식의 텍스트로 조회합니다.")
    
    tree_rules = export_text(dt_model, feature_names=list(X.columns))
    st.code(tree_rules, language="text")

    st.markdown("---")
    st.subheader("🎯 비즈니스 인사이트 & 실행 가능한 액션 플랜 (Action Plan)")
    st.markdown("""
### 1. 핵심 인사이트: 구매 전환의 마스터 키, '페이지 가치 (PageValues)'
의사결정나무 모델 및 Random Forest 등 예측 모델 전체에서 공통적으로 구매 예측에 가장 막대한 기여를 하는 피처는 **PageValues**입니다. 페이지 가치 점수는 구매가 성사된 세션 내에서 사용자가 거쳐간 웹페이지들에 부여되는 평균적인 점수입니다. 
의사결정나무의 첫 분기(Root Node) 조건인 **`PageValues <= 1.109`**에 주목할 필요가 있습니다.
- **페이지 가치가 1.1점 이하인 다수의 방문 세션(약 80% 이상)**은 상품을 조회하더라도 최종 구매를 완료하지 않고 미구매 상태로 이탈할 확률이 극단적으로 높습니다.
- 반면, **페이지 가치 점수가 1.1점을 초과하는 세션**은 고부가가치 콘텐츠 페이지를 방문함으로써 매우 높은 확률로 구매 결정을 성사시킵니다.
따라서 쇼핑몰의 총 매출을 끌어올리기 위해서는 '단순히 트래픽을 모으는 것'보다 '유입된 사용자가 페이지 가치가 높은 고효율 페이지(베스트셀러, 상세 리뷰, 한정 혜택 딜 등)로 유도하는 내비게이션 최적화'가 최우선 과제입니다.

### 2. 비즈니스 성장을 위한 실질적 액션 플랜
**[Action 1] 고가치 페이지 랜딩 유도 및 개인화 경로 최적화 (Target: PageValues)**
- **초기 노출 강화**: 메인 홈 화면이나 첫 방문 광고 랜딩 페이지에서 사용자가 3회 이내의 클릭 안에 실시간 기획전 또는 평점이 우수한 상위 1% 구매 후기 요약 페이지로 랜딩할 수 있도록 사용자의 이동 동선을 직관적으로 재설계합니다.
- **결제 의도 이탈 방지**: 페이지 가치 점수가 상승(PageValues > 0)했음에도 구매를 완료하지 않고 세션을 이탈하려는 조짐이 보이는 사용자 그룹(예: 장바구니 추가 후 결제창 정체 고객)을 타겟으로 실시간 리타게팅 팝업이나 이탈 후 30분 이내에 카카오 알림톡(개인화 할인 혜택, 품절 임박 안내)을 발송하여 구매 욕구를 리마인드합니다.

**[Action 2] 상품 탐색 경험 다양화 및 머무는 시간 증대 (Target: ProductRelated_Duration)**
- **체류 시간 확장**: 피처 중요도 분석에서 주요 행동 지표로 포착된 상품 상세 관련 페이지 체류 시간(`ProductRelated_Duration`)을 늘려야 합니다. 
- 이를 위해 상세 페이지 상단에 실제 고객이 올린 숏폼 영상 리뷰나 3D 상품 뷰어 기능을 배치하고, 연관 상품을 제안하는 스마트 추천 인공지능(AI) 구좌를 하단에 구성하여 페이지의 스크롤을 끝까지 내리며 탐색할 수 있도록 유도합니다.

**[Action 3] 종료 허들 진단 및 결제 직전 이탈률 케어 (Target: ExitRates / BounceRates)**
- **종료 예상 지점 방어**: 이탈률과 종료율을 낮추기 위해, 사용자의 마우스 궤적이 브라우저 상단이나 탭 종료 버튼 부근으로 향할 때 '이탈 감지 혜이징 트리거'를 작동시켜 즉시 할인 가능한 '첫 구매 전용 시크릿 쿠폰' 또는 '무료 배송 혜택 쿠폰' 팝업을 노출하여 마지막 결제 허들을 허물어줍니다.

### 3. 디시전트리 룰 기반 고객 세그먼트 마케팅 전략
- **세그먼트 A (PageValues > 23.61 - 초고가치 세션)**: 구매 확률이 매우 강력한 핵심 고객군입니다. 이들에게는 추가적인 혜택 할인 제안보다는, 복잡한 인증 절차나 결제 방식의 불편함(간편 결제 미지원 등)으로 인한 낙오가 없도록 결제 UX를 극도로 직관화하고 '원클릭 간편결제' 및 '무료 반품' 서비스를 우선 노출하여 이탈 없이 성공적으로 주문이 마감되도록 유도합니다.
- **세그먼트 B (PageValues <= 1.109 이나 Month = November - 시즌 유입 세션)**: 11월(Month_Nov)은 블랙프라이데이 및 연말 이벤트 등으로 대규모 특별 프로모션이 집중되는 시기입니다. 이 시기에는 탐색 깊이가 얕고 페이지 가치가 낮게 기록되더라도 일시적인 이벤트 혜택에 마음이 움직이기 쉬운 쇼핑객이 많으므로, 첫 랜딩 화면에 메가 세일 타이머 배너와 한정 수량 실시간 재고 현황을 카운트다운 형태로 전면 강조하여 즉각적인 충동 구매 전환을 촉진해야 합니다.
""")
