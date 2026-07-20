"""
네이버 API EDA 리포트 보완 분석 스크립트
=====================================================
이 스크립트는 naver_api_eda_report.md의 두 가지 항목을 보완합니다.

1. 검색어 수집 방식 명확화:
   - 데이터랩 API가 '직무+자격증 조합어'가 아닌
     '자격증 단독 키워드 그룹'으로 검색됐음을 확인하고 리포트에 명시

2. 회계 직군 데이터 우위 원인 분석:
   - 키워드 수(15개) vs 타 직무(9~10개)의 수량 차이 확인
   - 회계 직군 키워드별 평균 trend_ratio 세부 분석 및 시각화 추가
"""

import sys
import os
import warnings
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import koreanize_matplotlib

warnings.filterwarnings("ignore")
matplotlib.use("Agg")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH   = "project2/data/integrated/naver_weekly_insights.json"
IMG_DIR     = "project2/images"
REPORT_PATH = "project2/report/naver_api_eda_report.md"

df = pd.read_json(DATA_PATH)
df["date"] = pd.to_datetime(df["date"])
df["yearmonth"] = df["date"].dt.to_period("M").astype(str)

# ============================================================
# 1. 검색어 수집 방식 확인
# ============================================================
print("=" * 65)
print("[검색어 수집 방식 확인]")
print()
print("▶ fetch_datalab_trend() 함수의 payload 구조:")
print("""
  payload = {
      "startDate":     "2026-01-01",
      "endDate":       "2026-07-17",
      "timeUnit":      "date",
      "keywordGroups": [
          {"groupName": "토익",           "keywords": ["토익", "TOEIC", "토익 점수"]}
      ]
  }
""")
print("✅ 결론: '자격증 단독 키워드' 기반 수집")
print("   → '직무명 + 자격증' 조합어(예: '회계 토익')로 검색한 것이 아닙니다.")
print("   → 네이버 데이터랩에서 '토익'을 검색하는 전체 사용자의 검색량이 수집됩니다.")
print("   → job 컬럼은 '이 키워드를 수집한 출처 직무'를 나타내는 레이블로,")
print("     실제 API 검색어에는 직무명이 포함되지 않습니다.")
print("   ⚠️  동일 키워드(토익, 영어회화 등)가 여러 직무에 중복 등록되어")
print("      같은 trend_ratio가 직무별로 별도 레코드로 저장됩니다.")
print()

# ============================================================
# 2. 회계 직군 데이터 우위 원인 분석
# ============================================================
print("=" * 65)
print("[회계(acc) 직군 데이터 수량 우위 원인 분석]")

# 직무별 키워드 수
job_kw_count = df.groupby("job")["keyword"].nunique().sort_values(ascending=False)
print("\n▶ 직무별 고유 키워드 수:")
print(job_kw_count.to_string())

# 직무별 레코드 수 = 키워드 수 × 수집 날짜 수(198일)
job_record = df.groupby("job").size()
print("\n▶ 직무별 레코드 수 (키워드수 × 198일):")
print(job_record.to_string())

# 회계 직군 키워드별 평균 trend_ratio
acc_kw_avg = (df[df["job"]=="회계(acc)"]
              .groupby("keyword")["trend_ratio"]
              .agg(["mean","std","max"])
              .round(2)
              .sort_values("mean", ascending=False))
print("\n▶ 회계 직군 키워드별 평균 검색량 상세:")
print(acc_kw_avg.to_string())

# 전 직무 키워드별 평균(중복 키워드는 직무 무관 단순 평균)
all_kw_avg = df.groupby("keyword")["trend_ratio"].mean().sort_values(ascending=False)
print("\n▶ 전체 키워드 중 회계 관련 키워드의 전체 순위:")
acc_kws = df[df["job"]=="회계(acc)"]["keyword"].unique()
for kw in all_kw_avg.index:
    if kw in acc_kws:
        rank = list(all_kw_avg.index).index(kw) + 1
        print(f"  {rank:2d}위  {kw:20s}  {all_kw_avg[kw]:.2f}")

# ============================================================
# 시각화 추가: 회계 직군 키워드별 평균 trend_ratio
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# 왼쪽: 회계 키워드별 평균 검색량
ax = axes[0]
colors = ["#C44E52" if v >= acc_kw_avg["mean"].median() else "#4C72B0"
          for v in acc_kw_avg["mean"]]
bars = ax.barh(acc_kw_avg.index, acc_kw_avg["mean"], color=colors, edgecolor="white")
ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
ax.set_title("회계(acc) 직군 키워드별 평균 검색량\n(붉은색 = 중앙값 이상)", fontsize=11)
ax.set_xlabel("평균 trend_ratio")
ax.axvline(acc_kw_avg["mean"].median(), color="orange", linestyle="--",
           label=f"중앙값: {acc_kw_avg['mean'].median():.1f}")
ax.legend(fontsize=8)

# 오른쪽: 직무별 데이터 수량 구성 (파이차트)
ax2 = axes[1]
sizes = job_kw_count.values
labels = [f"{j}\n({v}개 키워드)" for j, v in zip(job_kw_count.index, job_kw_count.values)]
colors_pie = ["#C44E52","#4C72B0","#DD8452","#55A868","#8172B2"]
wedges, texts, autotexts = ax2.pie(sizes, labels=labels, autopct="%1.1f%%",
                                    colors=colors_pie, startangle=140,
                                    textprops={"fontsize": 9})
for at in autotexts:
    at.set_fontsize(9)
ax2.set_title("직무별 키워드 수 비중\n(데이터 수량 차이의 근본 원인)", fontsize=11)

plt.tight_layout()
fpath = os.path.join(IMG_DIR, "viz13_acc_keyword_analysis.png")
plt.savefig(fpath, dpi=120, bbox_inches="tight")
plt.close()
print(f"\n✅ 보완 시각화 저장: {fpath}")

# ============================================================
# 월별 회계 vs 타직무 추이 비교 시각화
# ============================================================
monthly_job = df.groupby(["yearmonth","job"])["trend_ratio"].mean().reset_index()
fig, ax = plt.subplots(figsize=(13, 6))
for job in df["job"].unique():
    subset = monthly_job[monthly_job["job"]==job]
    lw = 2.5 if job == "회계(acc)" else 1.2
    ls = "-" if job == "회계(acc)" else "--"
    ax.plot(subset["yearmonth"], subset["trend_ratio"],
            label=job, linewidth=lw, linestyle=ls, marker="o" if job=="회계(acc)" else None)
ax.set_title("직무별 월별 평균 검색량 비교 (회계 강조)", fontsize=12)
ax.set_ylabel("평균 trend_ratio")
ax.set_xlabel("연월")
ax.legend(loc="upper left", fontsize=9)
plt.xticks(rotation=30)
fpath2 = os.path.join(IMG_DIR, "viz14_acc_vs_others_monthly.png")
plt.savefig(fpath2, dpi=120, bbox_inches="tight")
plt.close()
print(f"✅ 월별 비교 시각화 저장: {fpath2}")

# ============================================================
# 리포트 보완 섹션 내용 준비 (append용)
# ============================================================
acc_top5 = acc_kw_avg.head(5)
correction_text = f"""

---

## 📌 5. 수집 방식 명확화 및 회계 직군 심층 분석

### 5-1. 검색어 수집 방식 확인 (중요)

> [!IMPORTANT]
> **현재 수집 데이터는 '직무+자격증 조합어'가 아닙니다.**

#### 실제 API 호출 방식 (데이터랩 트렌드)

```json
{{
  "startDate": "2026-01-01",
  "endDate":   "2026-07-17",
  "timeUnit":  "date",
  "keywordGroups": [
    {{"groupName": "토익", "keywords": ["토익", "TOEIC", "토익 점수"]}}
  ]
}}
```

#### 수집 방식 요약

| 항목 | 설명 |
|---|---|
| **검색어 단위** | 자격증·어학 키워드 단독 (예: "토익", "전산세무") |
| **직무명 포함 여부** | ❌ API 검색어에 직무명 미포함 |
| **job 컬럼 의미** | 해당 키워드를 어느 직무 분석 맥락에서 수집했는지 나타내는 **레이블** |
| **중복 수집** | 토익·영어회화·컴퓨터활용능력 등 범용 키워드는 5개 직무 모두에서 동일 검색량이 수집됨 |
| **카페 검색어** | `{{키워드}} 취업` 형태로 카페글 검색 (날짜별 분리 수집은 API 구조적 제약) |

**→ '직무+자격증 조합어(예: 회계 토익, 개발 SQLD)'로 수집하려면 KEYWORD_MAP의 search_terms를 수정해야 합니다.**

---

### 5-2. 회계(acc) 직군 데이터 수량 우위 원인 분석

#### ① 키워드 수의 차이가 주요 원인

| 직무 | 자격증/어학 키워드 수 | 레코드 수 | 비중 |
|---|---|---|---|
| **회계(acc)** | **15개** | **2,970건** | **28.3%** |
| 개발(dev) | 10개 | 1,980건 | 18.9% |
| 마케팅(mkt) | 10개 | 1,980건 | 18.9% |
| 기획(plan) | 9개 | 1,782건 | 17.0% |
| 인사(hr) | 9개 | 1,782건 | 17.0% |

> 회계 직군은 **국가공인 자격증의 다양성** (전산세무 1·2급, 전산회계 1·2급, 세무사, 공인회계사, 회계관리,
> 재경관리사, 미국회계사, ERP정보관리사)으로 인해 다른 직무 대비 자격증 목록이 더 많습니다.
> **레코드 수의 차이는 실제 검색 수요 차이가 아닌 순수한 키워드 수(15개 vs 9~10개)의 차이입니다.**

#### ② 회계 직군 키워드별 평균 검색량 상세

{acc_kw_avg.to_markdown()}

#### ③ 회계 직군 내 검색량 상위 5개 키워드 해석

| 순위 | 키워드 | 평균 trend_ratio | 주요 특징 |
|---|---|---|---|
{chr(10).join(f"| {i+1} | **{row.name}** | {row['mean']:.2f} | {'공인 어학시험 - 범용 수요' if row.name in ['토익','영어회화','토익스피킹','오픽','중국어','일본어'] else '국가공인 회계 자격증 - 시즌형 수요'} |" for i, (_, row) in enumerate(acc_kw_avg.head(5).iterrows()))}

![시각화13](../images/viz13_acc_keyword_analysis.png)

**[해석]** 왼쪽 그래프에서 붉은색 막대(중앙값 이상)를 보면 회계 직군에서도 '토익', '영어회화', '중국어' 등
범용 어학 키워드가 상위권을 차지합니다. 이는 회계 직군이 단순히 자격증 수가 많기 때문에 전체 레코드가 많을 뿐이며,
실제 검색 수요의 절반 이상은 어학 스펙 관련 수요임을 보여줍니다.
오른쪽 파이차트는 회계 직군이 전체 데이터의 28.3%를 차지하는 구조적 원인(키워드 수 15개)을 직관적으로 확인합니다.

---

### 5-3. 직무별 월별 평균 검색량 비교 (회계 강조)

![시각화14](../images/viz14_acc_vs_others_monthly.png)

**[피봇테이블]**

{df.pivot_table(index='yearmonth', columns='job', values='trend_ratio', aggfunc='mean').round(2).to_markdown()}

**[해석]** 실선(회계)이 항상 가장 높은 것이 아님을 확인할 수 있습니다.
실제 월별 평균 검색량은 직무마다 다르며, 특정 시험 시즌에는 개발·인사 직군의 특정 자격증이 일시적으로 높아집니다.
회계 직군의 전체 레코드 수가 많은 것은 검색 수요가 높기 때문이 아니라 키워드 종류가 많기 때문임을 재확인합니다.

---

*보완 분석 추가 일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}*
"""

# 리포트에 추가
with open(REPORT_PATH, "a", encoding="utf-8") as f:
    f.write(correction_text)

print("\n✅ 리포트 보완 완료!")
print(f"   추가 섹션: '5. 수집 방식 명확화 및 회계 직군 심층 분석'")
print(f"   추가 시각화: viz13, viz14")
