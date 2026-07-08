---
marp: true
theme: default
paginate: true
header: "통합 내부감사 채용공고 데이터 분석 (EDA)"
footer: "Swiss International Style · IA_recruit Project"
style: |
  section {
    background-color: #FAFAFA;
    color: #111111;
    font-family: 'Helvetica Neue', Arial, sans-serif;
    padding: 50px 80px;
    font-size: 18px;
  }
  h1 {
    color: #111111;
    font-size: 34pt;
    font-family: 'Helvetica Neue Bold', Arial, sans-serif;
    margin-top: 10px;
    margin-bottom: 20px;
    border-bottom: 5px solid #E8000D; /* Swiss Accent Line */
    padding-bottom: 10px;
  }
  h2 {
    color: #E8000D;
    font-size: 20pt;
    margin-top: 0;
    font-family: 'Helvetica Neue Bold', Arial, sans-serif;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 40px;
    align-items: center;
  }
  .grid-2-equal {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
  }
  .caption {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    letter-spacing: 3px;
    color: #888888;
    text-transform: uppercase;
    margin-bottom: 15px;
  }
  .highlight {
    color: #E8000D;
    font-weight: bold;
  }
  .kpi-box {
    text-align: center;
    background: #FFFFFF;
    border: 1px solid #DDDDDD;
    padding: 20px;
  }
  .kpi {
    font-size: 44pt;
    font-weight: bold;
    color: #E8000D;
    line-height: 1;
    margin-bottom: 5px;
  }
  .kpi-label {
    font-size: 12px;
    color: #555555;
    font-weight: bold;
  }
  .bullet-list {
    margin-top: 15px;
    line-height: 1.6;
  }
  .bullet-list li {
    margin-bottom: 8px;
  }
  /* Swiss International left-border line effect */
  section::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 10px;
    background-color: #E8000D;
  }
---

<!-- page_number: false -->
<!-- _header: "" -->
<!-- _footer: "" -->

<div class="caption">DATA ANALYSIS REPORT PRESENTATION</div>

# 통합 내부감사 채용 데이터<br>탐색적 데이터 분석 (EDA)

<div class="grid-2" style="margin-top: 40px;">
  <div>
    <h2 style="color: #111111;">사람인 & 잡코리아 통합 데이터셋 기반</h2>
    <p style="color: #555555; line-height: 1.6;">
      검색어 "내부감사"로 추출된 총 597건의 실제 공고 데이터를 전처리하고 분석하여 직무 실태, 요구 스펙, 핵심 키워드 및 연관 직무를 실용적으로 도출한 결과 보고서입니다.
    </p>
  </div>
  <div class="grid-2-equal">
    <div class="kpi-box">
      <div class="kpi">597</div>
      <div class="kpi-label">분석 공고 수</div>
    </div>
    <div class="kpi-box">
      <div class="kpi">3.5</div>
      <div class="kpi-label">평균 경력(년)</div>
    </div>
  </div>
</div>

<div style="margin-top: 40px; font-size: 12px; color: #888888; font-family: 'Space Mono', monospace;">
  DATE: 2026-06-27 | ANALYST: 20-YEAR EXPERT IN EDA
</div>

---

<div class="caption">SECTION 01: JOB GROUP CLASSIFICATION</div>

<h1>검색 노이즈 및 실제 직무군 분포</h1>

<div class="grid-2">
  <div>
    <h2>"내부감사" 검색 시 실제 직무 부합율 10.6%</h2>
    <ul class="bullet-list">
      <li><strong>검색 노이즈 과다</strong>: 포털에서 내부감사로 검색하여 나오는 공고의 절반 이상(<span class="highlight">52.6%</span>)은 일반 재무/회계/세무 실무 공고입니다.</li>
      <li><strong>순수 내부감사 비율</strong>: 실제 독립적인 통제 및 감사 설계/평가를 전담하는 공고는 단 <span class="highlight">63건 (10.6%)</span>에 불과합니다.</li>
      <li><strong>IT 감사의 부상</strong>: ITGC 및 시스템 거버넌스를 감사하는 IT감사 직무는 전체의 0.5%로 수량은 적으나 고가치 영역입니다.</li>
      <li><span class="highlight">구직 전략</span>: 공고 제목 필터링 및 요강 내 '내부회계관리제도/통제' 명시 여부를 필히 사전 확인해야 합니다.</li>
    </ul>
  </div>
  <div>
    <img src="../images/chart1_job_groups.png" alt="직무군 분포" style="width: 100%; border: 1px solid #ddd;" />
  </div>
</div>

---

<div class="caption">SECTION 02: CAREER DEMAND</div>

<h1>연차별 채용 수요 집중도</h1>

<div class="grid-2">
  <div>
    <h2>주니어 및 미들 실무자급 수요 중심 시장</h2>
    <ul class="bullet-list">
      <li><strong>중앙값 3.0년</strong>: 전체 평균 요구 경력은 3.5년이나, 신입/무관을 제외한 경력직 공고의 평균 연차는 <span class="highlight">4.9년</span>입니다.</li>
      <li><strong>주요 타겟 구간</strong>: 주니어(1~3년)가 <span class="highlight">33.3%</span>로 가장 높고, 미들(4~7년) 구간이 <span class="highlight">24.0%</span>로 그 뒤를 잇습니다.</li>
      <li><strong>신입/무관(29.0%)</strong>: 주로 회계법인 스텝 경력을 우대하거나 타 업무와 병행하는 일반 중소기업의 유연한 채용 조건입니다.</li>
      <li><strong>디렉터급(1.5%)</strong>: 13년 이상의 고연차 감사인 채용은 공채보다 주로 헤드헌팅 채널로 진행됩니다.</li>
    </ul>
  </div>
  <div>
    <img src="../images/chart2_career_segments.png" alt="경력 세그먼트" style="width: 100%; border: 1px solid #ddd;" />
  </div>
</div>

---

<div class="caption">SECTION 03: BARRIERS BY COMPANY TYPE</div>

<h1>기업 형태별 학력 진입 장벽</h1>

<div class="grid-2">
  <div>
    <h2>대기업·상장사의 견고한 대졸 조건과 중소기업의 유연성</h2>
    <ul class="bullet-list">
      <li><strong>대기업/그룹사</strong>: 학력 제한이 매우 엄격하며 대졸 이상 요구율이 지배적입니다. 지배구조 법제 준수 요건이 높기 때문입니다.</li>
      <li><strong>일반/중소기업</strong>: 학력 무관 비율이 <span class="highlight">41.2%</span>에 달해 학벌 스펙보다 실무 처리 역량을 중심으로 선발합니다.</li>
      <li><strong>경력 분포의 격차</strong>: 대기업 감사실은 중앙값 7년 전후의 검증된 경력을 원하나, 중소기업은 3년 이하를 타겟으로 합니다.</li>
      <li><span class="highlight">취업 가이드</span>: 주니어 경력자는 일반 상장사/중소기업에서 내부통제 빌드업 경험을 쌓고 대기업/상장사로 점진적 점프업을 해야 합니다.</li>
    </ul>
  </div>
  <div>
    <img src="../images/chart3_company_education.png" alt="학력 조건" style="width: 100%; border: 1px solid #ddd;" />
  </div>
</div>

---

<div class="caption">SECTION 04: CERTIFICATION MARKET VALUE</div>

<h1>우대 자격증 & 스킬의 커리어 매핑</h1>

<div class="grid-2">
  <div>
    <h2>보유 자격에 따른 타겟 연차의 설계</h2>
    <ul class="bullet-list">
      <li><strong>최고 진입 장벽 (CPA)</strong>: 회계사 우대 공고의 평균 경력은 <span class="highlight">3.7년</span>(최대 10년)으로 고경력 전문가 포지션 매핑이 뚜렷합니다.</li>
      <li><strong>실무형 우대 기술 (K-SOX)</strong>: 내부회계관리제도 실무 지식 우대는 평균 경력 <span class="highlight">3.8년</span>으로, 미들급의 이직 성공률을 결정짓는 핵심 열쇠입니다.</li>
      <li><strong>IT 통제 전문성 (CISA)</strong>: 평균 경력 3.7년으로, 일반 감사 대비 IT 거버넌스 영역의 희소성을 무기로 고연봉 진입이 가능합니다.</li>
      <li><strong>ERP 필수 (SAP)</strong>: 상세 요강 내 SAP 언급이 가장 많으며, 주니어(평균 3.5년) 전입 시 필수 스펙입니다.</li>
    </ul>
  </div>
  <div>
    <img src="../images/chart5_certs_career_boxplot.png" alt="자격증 경력 분포" style="width: 100%; border: 1px solid #ddd;" />
  </div>
</div>

---

<div class="caption">SECTION 05: REQUIRED COMPETENCY METHODOLOGY</div>

<h1>필수 요건(MUST) vs 우대 조건(PREFER)</h1>

<div class="grid-2-equal">
  <div class="card">
    <div class="caption">Must-Have Skills</div>
    <h2 style="color: #111111;">필수 자격 요건 (TF-IDF)</h2>
    <img src="../images/chart7_must_keywords.png" alt="필수 키워드" style="width: 100%; border: 1px solid #eee; margin: 10px 0;" />
    <p style="font-size: 13px; color: #555555; line-height: 1.5;">
      <strong>회계, 감사, 실무 경험</strong> 등 기본적인 하드웨어 역량과 <strong>내부회계관리제도(K-SOX)</strong> 구축/운영 지식이 기본적으로 탑재되어 있어야 서류 통과가 가능합니다.
    </p>
  </div>
  <div class="card">
    <div class="caption">Preferred Qualities</div>
    <h2 style="color: #111111;">우대 우대 조건 (TF-IDF)</h2>
    <img src="../images/chart8_prefer_keywords.png" alt="우대 키워드" style="width: 100%; border: 1px solid #eee; margin: 10px 0;" />
    <p style="font-size: 13px; color: #555555; line-height: 1.5;">
      <strong>CPA, CIA, CISA</strong> 전문 자격증 소지 여부가 합격을 결정짓는 핵심 알파 요소입니다. 이에 더해 <strong>상장사 근무 경험</strong>과 <strong>외국어(영어)</strong> 능력이 강력하게 작용합니다.
    </p>
  </div>
</div>

---

<div class="caption">SECTION 06: GEOGRAPHIC CAREER MAP</div>

<h1>지리적 경력 지도 분석</h1>

<div class="grid-2">
  <div>
    <h2>비즈니스 허브 지역별 요구 경력 편차</h2>
    <ul class="bullet-list">
      <li><strong>판교 테크노밸리 (성남시)</strong>: 평균 요구 경력이 <span class="highlight">4.8년</span>으로 조사 대상 지역 중 가장 높습니다. IT/SaaS 상장사의 통제 인프라 구축 수요가 시니어 감사인에게 집중되는 경향을 보입니다.</li>
      <li><strong>서울 강남/서초구</strong>: 평균 요구 경력 <span class="highlight">3.5~3.6년</span>으로 가장 많은 채용 공고(강남구 77건)를 보유하고 있으며 다양한 규모의 기업이 포진해 있습니다.</li>
      <li><strong>화성시/경기 제조업</strong>: 대형 생산 법인 관리 목적으로 2.8년 전후의 주니어~미들 실무자 수요가 다수 포진해 있습니다.</li>
    </ul>
  </div>
  <div>
    <img src="../images/chart4_region_career.png" alt="지역별 요구 경력" style="width: 100%; border: 1px solid #ddd;" />
  </div>
</div>

---

<div class="caption">CONCLUSION & ROADMAP</div>

<h1>데이터 기반 내부감사 구직/이직 전략</h1>

<div class="grid-3" style="margin-top: 30px;">
  <div class="card">
    <h2>1. 타겟 검색어 최적화</h2>
    <p style="font-size: 13px; color: #555555; line-height: 1.6;">
      '내부감사' 검색 시 50% 이상의 재무회계 공고가 혼입되므로, 검색 쿼리를 <strong>"내부회계", "내부통제", "K-SOX", "CISA"</strong> 등으로 조합 및 고도화하여 실제 전담 공고를 타겟팅해야 합니다.
    </p>
  </div>
  <div class="card">
    <h2>2. 커리어 패스 빌드업</h2>
    <p style="font-size: 13px; color: #555555; line-height: 1.6;">
      주니어(1~3년)는 중소기업이나 상장사 스태프로 시작하여 <strong>SAP ERP 실무와 K-SOX 검증 프로세스</strong>를 직접 설계해 본 뒤, 미들(4~7년) 진입 시점에 <strong>CIA/CISA</strong>를 취득하여 대형 상장사/대기업 감사실로 수평 점프업해야 합니다.
    </p>
  </div>
  <div class="card">
    <h2>3. 스펙 믹스 전략</h2>
    <p style="font-size: 13px; color: #555555; line-height: 1.6;">
      단순 학력 스펙보다 본문에 언급이 잦은 <strong>외국어(영어/중국어 등 글로벌 감사 능력)</strong> 및 <strong>IT 통제 지식(시스템 감사)</strong>을 포트폴리오에 어필하는 것이 CPA 등 하드웨어 자격증이 없는 비전공 구직자의 성공 전략입니다.
    </p>
  </div>
</div>

<div class="highlight" style="margin-top: 40px; text-align: center; font-size: 15px; font-weight: bold;">
  "실무 역량을 증명하는 K-SOX 경험과 전문 자격증이 감사인의 시장 가치를 결정합니다."
</div>
