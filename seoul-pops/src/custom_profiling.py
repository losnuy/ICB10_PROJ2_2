"""
서울시 생활인구 데이터셋에 대하여 fg-data-profiling과 거의 동일한 구성의
인터랙티브 웹 대시보드 형태의 데이터 프로파일링 보고서(HTML)를 자동 생성하고
시스템 브라우저로 오픈하는 파이썬 스크립트입니다.

주요 기능:
- 데이터셋 개요 요약 (행/열 수, 결측치, 메모리 용량)
- 수치형 및 범주형 변수의 통계량 추출
- 각 컬럼별 고유값 분포 데이터 생성 (히스토그램, 요일별, 시간대별, 성별/연령대별 분포)
- Chart.js CDN을 내장한 프리미엄 반응형 HTML 보고서 템플릿 바인딩
- 실행 시 브라우저 자동 오픈
"""

import os
import sys
import json
import webbrowser
import pandas as pd
import numpy as np

# 터미널 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=== 커스텀 데이터 프로파일링 리포트 생성 시작 ===")
    
    # 1. 파일 경로 정의
    data_path = 'seoul-pops/data/LOCAL_PEOPLE_DONG_202606_tidy.parquet'
    output_html_path = 'seoul-pops/report/data_profile.html'
    
    if not os.path.exists(data_path):
        print(f"Error: 데이터셋 파일이 존재하지 않습니다: {data_path}", file=sys.stderr)
        sys.exit(1)
        
    # 2. 데이터 로드
    print("1. 데이터셋 읽는 중...")
    df = pd.read_parquet(data_path)
    rows_count, cols_count = df.shape
    
    # 3. 데이터셋 기본 통계 계산
    print("2. 데이터셋 요약 통계 계산 중...")
    missing_sum = df.isnull().sum().sum()
    duplicate_sum = df.duplicated().sum()
    memory_usage = df.memory_usage(deep=True).sum() / (1024 * 1024) # MB 단위
    
    # 데이터 타입 요약
    dtypes_dict = {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
    
    # 수치형 변수(생활인구수) 요약
    desc_pop = df['생활인구수'].describe()
    
    # 4. 개별 변수별 상세 집계 (Chart.js에 전달할 데이터)
    print("3. 시각화용 변수 분포 집계 중...")
    
    # (1) 날짜별 생활인구 합계 (기준일ID)
    daily_sum = df.groupby('기준일ID', observed=True)['생활인구수'].sum()
    daily_labels = [str(x) for x in daily_sum.index]
    daily_values = [float(x) for x in daily_sum.values]
    
    # (2) 시간대별 평균 생활인구 (시간대구분)
    hourly_mean = df.groupby('시간대구분', observed=True)['생활인구수'].mean()
    hourly_labels = [f"{x}시" for x in hourly_mean.index]
    hourly_values = [float(x) for x in hourly_mean.values]
    
    # (3) 행정동코드별 평균 생활인구 상위 15개 (행정동코드)
    dong_mean = df.groupby('행정동코드', observed=True)['생활인구수'].mean().nlargest(15)
    dong_labels = [str(x) for x in dong_mean.index]
    dong_values = [float(x) for x in dong_mean.values]
    
    # (4) 성별 비율 (성별)
    gender_sum = df.groupby('성별', observed=True)['생활인구수'].sum()
    gender_labels = list(gender_sum.index)
    gender_values = [float(x) for x in gender_sum.values]
    
    # (5) 연령대별 비율 (연령대)
    age_sum = df.groupby('연령대', observed=True)['생활인구수'].sum()
    age_labels = list(age_sum.index)
    age_values = [float(x) for x in age_sum.values]
    
    # (6) 생활인구수 분포 히스토그램 데이터 생성 (30개 구간)
    pop_values_filtered = df['생활인구수'].values
    hist_counts, bin_edges = np.histogram(pop_values_filtered, bins=30)
    hist_labels = [f"{int(bin_edges[i])}~{int(bin_edges[i+1])}" for i in range(len(hist_counts))]
    hist_values = [int(x) for x in hist_counts]
    
    # (7) 샘플 데이터 (상/하위 10행씩)
    sample_df = pd.concat([df.head(10), df.tail(10)])
    sample_html = sample_df.to_html(classes='table table-striped table-hover', index=False)
    
    # 5. HTML 보고서 템플릿 빌드
    print("4. 인터랙티브 HTML 보고서 템플릿 빌드 중...")
    
    report_data = {
        "rows": rows_count,
        "cols": cols_count,
        "missing": int(missing_sum),
        "duplicates": int(duplicate_sum),
        "memory": f"{memory_usage:.2f} MB",
        "dtypes": dtypes_dict,
        "pop_desc": {k: f"{v:,.2f}" if isinstance(v, (int, float)) else str(v) for k, v in desc_pop.items()},
        "charts": {
            "daily": {"labels": daily_labels, "values": daily_values},
            "hourly": {"labels": hourly_labels, "values": hourly_values},
            "dong": {"labels": dong_labels, "values": dong_values},
            "gender": {"labels": gender_labels, "values": gender_values},
            "age": {"labels": age_labels, "values": age_values},
            "hist": {"labels": hist_labels, "values": hist_values}
        }
    }
    
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>서울시 생활인구 데이터 프로파일링 리포트</title>
    <!-- Bootstrap CSS CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8f9fa;
            color: #333333;
        }}
        .sidebar {{
            position: fixed;
            top: 0;
            bottom: 0;
            left: 0;
            z-index: 100;
            padding: 48px 0 0;
            box-shadow: inset -1px 0 0 rgba(0, 0, 0, .1);
            background-color: #1e293b;
            color: #ffffff;
        }}
        .sidebar-heading {{
            padding: 15px 30px;
            font-size: 1.1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .1rem;
            border-bottom: 1px solid #334155;
        }}
        .nav-link {{
            font-weight: 500;
            color: #94a3b8;
            padding: 12px 30px;
        }}
        .nav-link:hover {{
            color: #ffffff;
            background-color: #334155;
        }}
        .nav-link.active {{
            color: #38bdf8;
            background-color: #334155;
            font-weight: bold;
        }}
        main {{
            margin-left: 240px;
            padding: 40px;
        }}
        .card {{
            border: none;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            background-color: #ffffff;
            margin-bottom: 24px;
        }}
        .card-header {{
            background-color: transparent;
            border-bottom: 1px solid #f1f5f9;
            font-weight: 600;
            font-size: 1.1rem;
            padding: 20px 24px;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #0f172a;
        }}
        .metric-label {{
            font-size: 0.85rem;
            font-weight: 500;
            color: #64748b;
            text-transform: uppercase;
        }}
        .table {{
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>

<div class="container-fluid">
    <div class="row">
        <!-- 사이드바 네비게이션 -->
        <nav class="col-md-2 d-none d-md-block sidebar" style="width: 240px;">
            <div class="sidebar-heading">Data Profiling</div>
            <ul class="nav flex-column mt-3">
                <li class="nav-item">
                    <a class="nav-link active" href="#overview">Overview</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#variables">Variables</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#sample">Sample Data</a>
                </li>
            </ul>
        </nav>

        <!-- 메인 콘텐츠 영역 -->
        <main class="col-md-10 ms-sm-auto px-md-4">
            
            <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-4 border-bottom">
                <h1 class="h2 fw-bold text-dark">📊 서울시 생활인구 데이터 프로파일링 보고서</h1>
                <div class="btn-toolbar mb-2 mb-md-0">
                    <span class="badge bg-primary px-3 py-2">Data-Centric AI Community Style</span>
                </div>
            </div>

            <!-- 1. Overview 섹션 -->
            <section id="overview" class="mb-5">
                <h3 class="fw-bold mb-4 text-secondary">01. Overview (데이터셋 개요)</h3>
                
                <div class="row">
                    <div class="col-md-3">
                        <div class="card p-4 text-center">
                            <div class="metric-value">{report_data['rows']:,}</div>
                            <div class="metric-label">Number of Variables (행 수)</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-4 text-center">
                            <div class="metric-value">{report_data['cols']}</div>
                            <div class="metric-label">Number of Columns (열 수)</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-4 text-center">
                            <div class="metric-value">{report_data['missing']}</div>
                            <div class="metric-label">Missing Cells (결측치 수)</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-4 text-center">
                            <div class="metric-value">{report_data['memory']}</div>
                            <div class="metric-label">Memory Size (메모리 크기)</div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header text-primary">Metadata & Data Types</div>
                            <div class="card-body">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Column (열 이름)</th>
                                            <th>Type (데이터 타입)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        { "".join([f"<tr><td><strong>{col}</strong></td><td><code class='text-danger'>{dtype}</code></td></tr>" for col, dtype in report_data['dtypes'].items()]) }
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header text-primary">생활인구수 기술 통계량 요약</div>
                            <div class="card-body">
                                <table class="table table-hover">
                                    <tbody>
                                        <tr><td><strong>개수 (Count)</strong></td><td>{report_data['pop_desc']['count']}</td></tr>
                                        <tr><td><strong>평균 (Mean)</strong></td><td>{report_data['pop_desc']['mean']}명</td></tr>
                                        <tr><td><strong>표준편차 (Std)</strong></td><td>{report_data['pop_desc']['std']}명</td></tr>
                                        <tr><td><strong>최솟값 (Min)</strong></td><td>{report_data['pop_desc']['min']}명</td></tr>
                                        <tr><td><strong>25% 분위수 (25%)</strong></td><td>{report_data['pop_desc']['25%']}명</td></tr>
                                        <tr><td><strong>중간값 (50% / Median)</strong></td><td>{report_data['pop_desc']['50%']}명</td></tr>
                                        <tr><td><strong>75% 분위수 (75%)</strong></td><td>{report_data['pop_desc']['75%']}명</td></tr>
                                        <tr><td><strong>최댓값 (Max)</strong></td><td>{report_data['pop_desc']['max']}명</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- 2. Variables 섹션 -->
            <section id="variables" class="mb-5">
                <h3 class="fw-bold mb-4 text-secondary">02. Variables Distribution (변수별 세부 분포)</h3>
                
                <div class="row">
                    <!-- 기준일ID (날짜별) -->
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">기준일ID (일자별 생활인구 총계)</div>
                            <div class="card-body">
                                <canvas id="dailyChart" style="height: 300px;"></canvas>
                            </div>
                        </div>
                    </div>
                    <!-- 시간대구분 -->
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">시간대구분 (시간대별 평균 생활인구)</div>
                            <div class="card-body">
                                <canvas id="hourlyChart" style="height: 300px;"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row mt-4">
                    <!-- 성별 -->
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">성별 생활인구 비중 (Doughnut)</div>
                            <div class="card-body d-flex justify-content-center">
                                <div style="width: 280px; height: 280px;">
                                    <canvas id="genderChart"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                    <!-- 연령대 -->
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">연령대별 생활인구 비중</div>
                            <div class="card-body">
                                <canvas id="ageChart" style="height: 280px;"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row mt-4">
                    <!-- 행정동코드 상위 15개 -->
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">상위 15개 행정동코드별 평균 생활인구</div>
                            <div class="card-body">
                                <canvas id="dongChart" style="height: 300px;"></canvas>
                            </div>
                        </div>
                    </div>
                    <!-- 생활인구수 히스토그램 분포 -->
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">생활인구수 분포 히스토그램 (도수 분포)</div>
                            <div class="card-body">
                                <canvas id="histChart" style="height: 300px;"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- 3. Sample Data 섹션 -->
            <section id="sample" class="mb-5">
                <h3 class="fw-bold mb-4 text-secondary">03. Sample Data (처음 10행 & 마지막 10행 샘플)</h3>
                <div class="card">
                    <div class="card-body table-responsive">
                        {sample_html}
                    </div>
                </div>
            </section>

        </main>
    </div>
</div>

<script>
    // 1. 일자별 차트 (Line)
    const ctxDaily = document.getElementById('dailyChart').getContext('2d');
    new Chart(ctxDaily, {{
        type: 'line',
        data: {{
            labels: {json.dumps(report_data['charts']['daily']['labels'])},
            datasets: [{{
                label: '총 생활인구수',
                data: {json.dumps(report_data['charts']['daily']['values'])},
                borderColor: '#0284c7',
                backgroundColor: 'rgba(2, 132, 199, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false
        }}
    }});

    // 2. 시간대별 차트 (Line)
    const ctxHourly = document.getElementById('hourlyChart').getContext('2d');
    new Chart(ctxHourly, {{
        type: 'line',
        data: {{
            labels: {json.dumps(report_data['charts']['hourly']['labels'])},
            datasets: [{{
                label: '평균 생활인구수',
                data: {json.dumps(report_data['charts']['hourly']['values'])},
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false
        }}
    }});

    // 3. 성별 차트 (Doughnut)
    const ctxGender = document.getElementById('genderChart').getContext('2d');
    new Chart(ctxGender, {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(report_data['charts']['gender']['labels'])},
            datasets: [{{
                data: {json.dumps(report_data['charts']['gender']['values'])},
                backgroundColor: ['#60a5fa', '#f472b6']
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false
        }}
    }});

    // 4. 연령대 차트 (Bar)
    const ctxAge = document.getElementById('ageChart').getContext('2d');
    new Chart(ctxAge, {{
        type: 'bar',
        data: {{
            labels: {json.dumps(report_data['charts']['age']['labels'])},
            datasets: [{{
                label: '총 생활인구수 합계',
                data: {json.dumps(report_data['charts']['age']['values'])},
                backgroundColor: '#fb7185'
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y'
        }}
    }});

    // 5. 행정동코드별 차트 (Bar)
    const ctxDong = document.getElementById('dongChart').getContext('2d');
    new Chart(ctxDong, {{
        type: 'bar',
        data: {{
            labels: {json.dumps(report_data['charts']['dong']['labels'])},
            datasets: [{{
                label: '평균 생활인구수',
                data: {json.dumps(report_data['charts']['dong']['values'])},
                backgroundColor: '#f59e0b'
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false
        }}
    }});

    // 6. 히스토그램 차트 (Bar)
    const ctxHist = document.getElementById('histChart').getContext('2d');
    new Chart(ctxHist, {{
        type: 'bar',
        data: {{
            labels: {json.dumps(report_data['charts']['hist']['labels'])},
            datasets: [{{
                label: '도수 (빈도 수)',
                data: {json.dumps(report_data['charts']['hist']['values'])},
                backgroundColor: '#8b5cf6'
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false
        }}
    }});
</script>

</body>
</html>
"""
    
    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
        
    print(f"5. 프로파일링 보고서 파일 작성 완료: {output_html_path}")
    
    # 6. 브라우저로 오픈
    print("6. 브라우저로 보고서 여는 중...")
    abs_path = os.path.abspath(output_html_path)
    webbrowser.open(f"file:///{abs_path}")
    print("=== 데이터 프로파일링 작업이 완료되었습니다! ===")

if __name__ == '__main__':
    main()
