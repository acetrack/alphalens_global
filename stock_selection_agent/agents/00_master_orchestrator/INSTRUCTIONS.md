# Agent 00: Master Orchestrator (마스터 오케스트레이터)

## 역할

전체 종목 선정 워크플로우를 조율하고 각 Sub-Agent의 결과를 통합하여 최종 투자 의견과 포트폴리오를 산출합니다. 펀드매니저의 의사결정 프로세스를 총괄하는 메인 컨트롤러입니다.

## 입력

- 모든 Sub-Agent의 분석 결과
- workflow.yaml 설정
- 투자 제약조건 (섹터 비중, 종목 수 등)

## 출력

- `final_portfolio.json`: 최종 포트폴리오 구성
- `stock_recommendations.json`: 종목별 투자의견
- `execution_log.json`: 워크플로우 실행 로그

---

## ⚠️ 필수 선행 단계: 현재 날짜 확인

### 분석 시작 전 반드시 현재 날짜를 확인해야 합니다.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ⚠️ DATE VALIDATION (필수)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 시스템 날짜 확인 또는 사용자에게 현재 날짜 질문                    │
│  2. 현재 연도/분기 기준으로 분석 기간 설정                            │
│  3. 데이터 검색 시 올바른 연도 키워드 사용                            │
│  4. 모든 리포트에 분석 기준일 명시                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 날짜 확인 절차

```python
def validate_analysis_date():
    """
    분석 시작 전 필수 실행
    """
    # Step 1: 현재 날짜 확인
    current_date = get_current_date()  # 시스템 또는 사용자 확인

    # Step 2: 분석 기간 동적 설정
    current_year = current_date.year
    current_quarter = (current_date.month - 1) // 3 + 1

    analysis_context = {
        "analysis_date": current_date.strftime("%Y-%m-%d"),
        "current_year": current_year,
        "current_quarter": f"{current_year}Q{current_quarter}",
        "historical_start": current_year - 5,
        "historical_end": current_year - 1,
        "forecast_start": current_year,
        "forecast_end": current_year + 2,
        "latest_annual_report": current_year - 1,  # 가장 최근 연간 실적
        "latest_quarterly": f"{current_year}Q{current_quarter - 1}" if current_quarter > 1 else f"{current_year - 1}Q4"
    }

    return analysis_context
```

### 날짜 기반 데이터 검색 가이드

| 현재 날짜 | 검색 키워드 예시 |
|-----------|-----------------|
| 2026년 2월 | "2026년 실적 전망", "2025년 4분기 실적" |
| 2025년 8월 | "2025년 2분기 실적", "2025년 하반기 전망" |
| 2024년 3월 | "2024년 1분기 전망", "2023년 연간 실적" |

### 리포트 날짜 표기

모든 분석 리포트에 다음 정보를 포함해야 합니다:

```yaml
report_header:
  analysis_date: "2026-02-01"  # 분석 기준일
  data_as_of: "2026-01-31"     # 데이터 기준일
  current_fiscal_year: 2026
  latest_reported_quarter: "2025Q4"
  forecast_period: "2026E ~ 2028E"
```

---

## ⚠️ 필수 선행 단계 2: 데이터 신선도 검증

### 데이터 기준일과 분석 기준일이 다를 수 있음을 인지해야 합니다.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ⚠️ DATA FRESHNESS VALIDATION (필수)               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  문제: 검색된 주가가 "2026.01.19" 인데 분석일이 "2026.02.01" 인 경우    │
│  → 13일 전 데이터로 분석하면 부정확한 투자판단 초래                     │
│                                                                     │
│  해결책:                                                            │
│  1. 검색된 데이터의 날짜를 반드시 확인                                 │
│  2. 분석일과 데이터일 간의 차이 계산                                  │
│  3. 리포트에 두 날짜를 명확히 구분하여 표기                           │
│  4. 오래된 데이터 사용 시 경고 표시                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 데이터 신선도 검증 절차

```python
def validate_data_freshness(analysis_date, data_date, data_type):
    """
    데이터 신선도를 검증하고 경고 수준을 결정
    """
    from datetime import datetime

    days_diff = (analysis_date - data_date).days

    # 데이터 유형별 허용 기준
    thresholds = {
        "price": {"warning": 1, "error": 5},      # 주가: 1일 경고, 5일 오류
        "financial": {"warning": 30, "error": 90}, # 재무: 30일 경고, 90일 오류
        "analyst": {"warning": 14, "error": 60},   # 애널리스트: 14일 경고, 60일 오류
    }

    threshold = thresholds.get(data_type, {"warning": 7, "error": 30})

    if days_diff <= threshold["warning"]:
        return {"status": "fresh", "label": "최신", "emoji": "✅"}
    elif days_diff <= threshold["error"]:
        return {"status": "stale", "label": f"⚠️ {days_diff}일 전", "emoji": "⚠️"}
    else:
        return {"status": "very_stale", "label": f"⚠️⚠️ {days_diff}일 전", "emoji": "🚨"}
```

### 리포트 필수 포함 사항

모든 분석 리포트에는 다음과 같은 **데이터 기준일 테이블**을 반드시 포함해야 합니다:

```markdown
## 데이터 기준일 안내

| 데이터 유형 | 기준일 | 분석일과의 차이 | 신선도 |
|------------|--------|----------------|--------|
| **분석 기준일** | 2026-02-01 | - | - |
| 주가 데이터 | 2026-01-30 | 2일 | ✅ 최신 |
| 재무 데이터 | 2025-12-31 | 32일 | ✅ 최신 (분기 기준) |
| 애널리스트 | 2026-01-15 | 17일 | ⚠️ 참고 필요 |

> **참고**: 주가 데이터가 분석일과 3일 이상 차이나는 경우,
> 실제 투자 결정 전 최신 시세를 반드시 확인하시기 바랍니다.
```

### 데이터 신선도 경고 문구

데이터가 오래된 경우 다음과 같은 경고를 리포트에 포함:

```markdown
### ⚠️ 데이터 신선도 경고

본 리포트의 주가 데이터는 **2026년 1월 19일** 기준이며,
분석 기준일(2026년 2월 1일)과 **13일** 차이가 있습니다.

실제 투자 결정 시 다음 사항을 확인하세요:
1. 네이버/다음 금융에서 최신 주가 확인
2. 주가 변동에 따른 밸류에이션 재계산 필요
3. 목표주가 대비 현재가 괴리율 재확인
```

### 검색 시 최신 데이터 확보 전략

1. **주가 검색 키워드**: "실시간", "오늘", "현재가", "최신"
2. **검색 예시**:
   - "{종목명} 현재가 실시간"
   - "{종목명} 주가 오늘"
   - "{종목명} 2026년 2월 시세"
3. **데이터 출처 우선순위**:
   - 1순위: 실시간 API (네이버/다음 금융)
   - 2순위: 당일 종가 데이터
   - 3순위: 최근 거래일 종가

---

## 오케스트레이션 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MASTER ORCHESTRATOR                             │
│                   (Investment Decision Engine)                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────┐
│   PHASE 1     │        │   PHASE 2     │        │   PHASE 3     │
│   Discovery   │   →    │   Analysis    │   →    │  Validation   │
│   종목 발굴    │        │   심층 분석    │        │   검증/확정    │
└───────┬───────┘        └───────┬───────┘        └───────┬───────┘
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────┐
│ 01_Screening  │        │ 02_Financial  │        │ 06_Technical  │
│               │        │ 03_Industry   │        │ 07_Risk       │
│ 2000+ → 100   │        │ 04_DCF        │        │ 08_Sentiment  │
│               │        │ 05_Relative   │        │               │
└───────────────┘        └───────────────┘        └───────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │     Score Integration     │
                    │       점수 통합            │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │   Portfolio Construction  │
                    │     포트폴리오 구성         │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │     Final Output          │
                    │   최종 투자 의견           │
                    └───────────────────────────┘
```

---

## 1단계: 워크플로우 실행

### 에이전트 실행 순서

```yaml
execution_order:
  phase_1_discovery:
    - agent: "01_screening_agent"
      parallel: false
      required: true
      output: "screened_stocks.json"

  phase_2_analysis:
    - agent: "02_financial_agent"
      parallel: true
      required: true
      depends_on: ["01_screening_agent"]

    - agent: "03_industry_agent"
      parallel: true
      required: true
      depends_on: ["01_screening_agent"]

    - agent: "04_dcf_valuation_agent"
      parallel: false
      required: true
      depends_on: ["02_financial_agent", "03_industry_agent"]

    - agent: "05_relative_valuation_agent"
      parallel: true
      required: true
      depends_on: ["02_financial_agent", "03_industry_agent"]

  phase_3_validation:
    - agent: "06_technical_agent"
      parallel: true
      required: false
      depends_on: ["01_screening_agent"]

    - agent: "07_risk_agent"
      parallel: true
      required: true
      depends_on: ["02_financial_agent", "06_technical_agent"]

    - agent: "08_sentiment_agent"
      parallel: true
      required: false
      depends_on: ["01_screening_agent"]
```

### 실행 관리

```python
class MasterOrchestrator:
    def __init__(self, config_path):
        self.config = load_config(config_path)
        self.results = {}
        self.execution_log = []

    def run_workflow(self):
        # Phase 1: Discovery
        self.log("Starting Phase 1: Discovery")
        self.run_agent("01_screening_agent")

        # Phase 2: Analysis (병렬 실행)
        self.log("Starting Phase 2: Analysis")
        parallel_tasks = [
            ("02_financial_agent", self.results["01_screening_agent"]),
            ("03_industry_agent", self.results["01_screening_agent"])
        ]
        self.run_parallel(parallel_tasks)

        # 밸류에이션 (순차 실행 - 의존성)
        self.run_agent("04_dcf_valuation_agent",
                       inputs=["02_financial_agent", "03_industry_agent"])
        self.run_agent("05_relative_valuation_agent",
                       inputs=["02_financial_agent", "03_industry_agent"])

        # Phase 3: Validation (병렬 실행)
        self.log("Starting Phase 3: Validation")
        parallel_tasks = [
            ("06_technical_agent", self.results["01_screening_agent"]),
            ("08_sentiment_agent", self.results["01_screening_agent"])
        ]
        self.run_parallel(parallel_tasks)

        self.run_agent("07_risk_agent",
                       inputs=["02_financial_agent", "06_technical_agent"])

        # Final: Integration
        self.log("Starting Final Integration")
        self.integrate_results()
        self.construct_portfolio()

        return self.generate_output()
```

---

## 2단계: 점수 통합 (Score Integration)

### 종합 투자 점수 산출

```python
def calculate_conviction_score(stock, results):
    """
    각 에이전트 점수를 가중 평균하여 종합 확신도 점수 산출
    """
    weights = {
        "screening": 0.10,       # 스크리닝 점수
        "financial": 0.20,       # 재무 건전성
        "industry": 0.10,        # 산업 경쟁력
        "dcf_valuation": 0.20,   # DCF 업사이드
        "relative_valuation": 0.15,  # 상대가치 업사이드
        "technical": 0.10,       # 기술적 신호
        "risk": 0.10,            # 리스크 (역수)
        "sentiment": 0.05        # 센티먼트
    }

    scores = {}

    # Screening Score
    scores["screening"] = results["screening"].get(stock.code, {}).get("composite_score", 50)

    # Financial Score
    scores["financial"] = results["financial"].get(stock.code, {}).get("total", 50)

    # Industry Score
    scores["industry"] = results["industry"].get(stock.code, {}).get("industry_score", 50)

    # DCF Upside → Score 변환
    dcf_upside = results["dcf"].get(stock.code, {}).get("upside_pct", 0)
    scores["dcf_valuation"] = upside_to_score(dcf_upside)

    # Relative Upside → Score 변환
    rel_upside = results["relative"].get(stock.code, {}).get("upside_pct", 0)
    scores["relative_valuation"] = upside_to_score(rel_upside)

    # Technical Score
    scores["technical"] = results["technical"].get(stock.code, {}).get("total", 50)

    # Risk Score (역수 - 리스크 낮을수록 높은 점수)
    risk_score = results["risk"].get(stock.code, {}).get("total", 50)
    scores["risk"] = 100 - risk_score

    # Sentiment Score
    scores["sentiment"] = results["sentiment"].get(stock.code, {}).get("total", 50)

    # 가중 평균
    conviction_score = sum(weights[k] * scores[k] for k in weights)

    return {
        "conviction_score": conviction_score,
        "component_scores": scores,
        "weights": weights
    }

def upside_to_score(upside_pct):
    """업사이드 %를 0-100 점수로 변환"""
    if upside_pct >= 50:
        return 100
    elif upside_pct >= 30:
        return 80 + (upside_pct - 30) * 1
    elif upside_pct >= 15:
        return 60 + (upside_pct - 15) * 1.33
    elif upside_pct >= 0:
        return 40 + upside_pct * 1.33
    elif upside_pct >= -15:
        return 20 + (upside_pct + 15) * 1.33
    else:
        return max(0, 20 + upside_pct)
```

### 투자의견 결정

```python
def determine_investment_rating(stock, conviction_score, results):
    """
    종합 점수 기반 투자의견 결정
    """
    # 기본 투자의견 (점수 기반)
    if conviction_score >= 80:
        base_rating = "Strong Buy"
    elif conviction_score >= 65:
        base_rating = "Buy"
    elif conviction_score >= 50:
        base_rating = "Hold"
    elif conviction_score >= 35:
        base_rating = "Underweight"
    else:
        base_rating = "Sell"

    # 조정 요인 체크
    adjustments = []

    # 리스크 경고
    risk_score = results["risk"].get(stock.code, {}).get("total", 50)
    if risk_score > 70:
        adjustments.append({
            "factor": "high_risk",
            "impact": "downgrade_one_notch",
            "reason": f"리스크 점수 {risk_score} (높음)"
        })

    # 밸류에이션 괴리
    dcf_upside = results["dcf"].get(stock.code, {}).get("upside_pct", 0)
    rel_upside = results["relative"].get(stock.code, {}).get("upside_pct", 0)

    if abs(dcf_upside - rel_upside) > 30:
        adjustments.append({
            "factor": "valuation_divergence",
            "impact": "flag_for_review",
            "reason": f"DCF ({dcf_upside}%) vs Relative ({rel_upside}%) 괴리"
        })

    # 기술적 신호 반영
    tech_signal = results["technical"].get(stock.code, {}).get("signal", "neutral")
    if tech_signal == "bearish" and base_rating in ["Strong Buy", "Buy"]:
        adjustments.append({
            "factor": "technical_warning",
            "impact": "timing_caution",
            "reason": "기술적 지표 약세 - 진입 타이밍 주의"
        })

    # 최종 의견
    final_rating = apply_adjustments(base_rating, adjustments)

    return {
        "rating": final_rating,
        "base_rating": base_rating,
        "adjustments": adjustments,
        "conviction_score": conviction_score
    }

def apply_adjustments(base_rating, adjustments):
    rating_order = ["Strong Buy", "Buy", "Hold", "Underweight", "Sell"]
    current_idx = rating_order.index(base_rating)

    for adj in adjustments:
        if adj["impact"] == "downgrade_one_notch":
            current_idx = min(current_idx + 1, len(rating_order) - 1)
        elif adj["impact"] == "upgrade_one_notch":
            current_idx = max(current_idx - 1, 0)

    return rating_order[current_idx]
```

---

## 3단계: 목표주가 산정

### 통합 목표주가

```python
def calculate_target_price(stock, results):
    """
    DCF와 상대가치 결과를 가중평균하여 최종 목표주가 산정
    """
    dcf_result = results["dcf"].get(stock.code, {})
    rel_result = results["relative"].get(stock.code, {})

    # 개별 목표주가
    dcf_target = dcf_result.get("fair_value_per_share", stock.price)
    rel_target = rel_result.get("weighted_fair_value", stock.price)

    # 시나리오별 DCF (있는 경우)
    dcf_bull = dcf_result.get("scenario_analysis", {}).get("bull", {}).get("price", dcf_target * 1.2)
    dcf_bear = dcf_result.get("scenario_analysis", {}).get("bear", {}).get("price", dcf_target * 0.8)

    # 가중평균 (DCF 50%, Relative 50%)
    primary_target = 0.50 * dcf_target + 0.50 * rel_target

    # 목표주가 범위
    target_high = max(dcf_bull, rel_target * 1.1)
    target_low = min(dcf_bear, rel_target * 0.9)

    # 현재가 대비 업사이드
    current_price = stock.price
    upside = (primary_target / current_price - 1) * 100

    return {
        "target_price": round(primary_target, -2),  # 100원 단위 반올림
        "target_high": round(target_high, -2),
        "target_low": round(target_low, -2),
        "current_price": current_price,
        "upside_pct": upside,
        "valuation_method": {
            "dcf_contribution": dcf_target,
            "relative_contribution": rel_target,
            "dcf_weight": 0.50,
            "relative_weight": 0.50
        }
    }
```

---

## 4단계: 포트폴리오 구성

### 최적 포트폴리오 산출

```python
def construct_portfolio(stocks, results, constraints):
    """
    확신도 점수 기반 포트폴리오 구성
    """
    # 1. 종목별 확신도 점수 계산
    scored_stocks = []
    for stock in stocks:
        score_data = calculate_conviction_score(stock, results)
        rating_data = determine_investment_rating(stock, score_data["conviction_score"], results)
        target_data = calculate_target_price(stock, results)

        scored_stocks.append({
            "stock": stock,
            "conviction_score": score_data["conviction_score"],
            "rating": rating_data["rating"],
            "target_price": target_data["target_price"],
            "upside": target_data["upside_pct"],
            "risk_score": results["risk"].get(stock.code, {}).get("total", 50)
        })

    # 2. 점수순 정렬
    scored_stocks.sort(key=lambda x: x["conviction_score"], reverse=True)

    # 3. 필터링 (최소 확신도, 투자의견)
    qualified_stocks = [
        s for s in scored_stocks
        if s["conviction_score"] >= constraints["min_conviction_score"]
        and s["rating"] in ["Strong Buy", "Buy"]
    ]

    # 4. 섹터 제약 적용
    portfolio = []
    sector_allocations = {}

    for s in qualified_stocks:
        sector = s["stock"].sector

        # 섹터 비중 체크
        current_sector_count = sector_allocations.get(sector, 0)
        if current_sector_count >= constraints["max_stocks_per_sector"]:
            continue

        # 총 종목 수 체크
        if len(portfolio) >= constraints["max_total_stocks"]:
            break

        # 포트폴리오 추가
        portfolio.append(s)
        sector_allocations[sector] = current_sector_count + 1

    # 5. 비중 산정
    total_score = sum(s["conviction_score"] for s in portfolio)

    for s in portfolio:
        # 점수 비례 비중 (기본)
        raw_weight = s["conviction_score"] / total_score

        # 리스크 조정
        risk_adj = 1 - (s["risk_score"] / 200)  # 리스크 높으면 비중 축소

        adjusted_weight = raw_weight * risk_adj

        # 최대 비중 제한
        s["weight"] = min(adjusted_weight, constraints["max_single_stock_weight"])

    # 비중 정규화 (합계 100%)
    weight_sum = sum(s["weight"] for s in portfolio)
    for s in portfolio:
        s["weight"] = s["weight"] / weight_sum

    return portfolio
```

### 포트폴리오 제약조건

```yaml
portfolio_constraints:
  max_total_stocks: 30
  min_conviction_score: 65
  max_single_stock_weight: 0.10  # 10%
  min_single_stock_weight: 0.02  # 2%
  max_sector_weight: 0.30  # 30%
  max_stocks_per_sector: 8
  min_liquidity_grade: "C"
  max_risk_grade: "Moderate-High"
```

---

## 5단계: 최종 출력 생성

### stock_recommendations.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "analyst": "Stock Selection Agent System",
  "recommendations": [
    {
      "rank": 1,
      "code": "005930",
      "name": "삼성전자",
      "sector": "IT",
      "investment_rating": "Strong Buy",
      "conviction_score": 85.2,
      "current_price": 65000,
      "target_price": 85000,
      "upside_pct": 30.8,
      "portfolio_weight": 8.5,
      "key_thesis": [
        "AI 반도체 수요 확대로 HBM 매출 급증",
        "글로벌 Peer 대비 저평가 (코리아 디스카운트)",
        "강력한 재무 건전성 (무차입 경영)"
      ],
      "risks": [
        "반도체 사이클 변동성",
        "중국 규제 불확실성"
      ],
      "scores": {
        "financial": 82.5,
        "valuation": 78.3,
        "technical": 68.0,
        "risk": 32.0,
        "sentiment": 68.0
      }
    }
  ]
}
```

### final_portfolio.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "portfolio_name": "High Conviction Korea Equity",
  "benchmark": "KOSPI",
  "summary": {
    "total_stocks": 25,
    "avg_conviction_score": 75.3,
    "avg_upside": 22.5,
    "avg_risk_score": 38.2,
    "expected_return": 18.5,
    "expected_volatility": 22.0,
    "sharpe_ratio": 0.84
  },
  "sector_allocation": {
    "IT": 28.5,
    "금융": 18.2,
    "헬스케어": 12.5,
    "산업재": 15.3,
    "소비재": 10.5,
    "소재": 8.0,
    "기타": 7.0
  },
  "holdings": [
    {
      "rank": 1,
      "code": "005930",
      "name": "삼성전자",
      "sector": "IT",
      "weight": 8.5,
      "shares": 1300,
      "current_value": 84500000,
      "target_value": 110500000,
      "rating": "Strong Buy"
    }
  ],
  "portfolio_metrics": {
    "beta": 1.05,
    "weighted_per": 12.8,
    "weighted_pbr": 1.15,
    "weighted_roe": 14.5,
    "dividend_yield": 2.8
  },
  "rebalancing": {
    "frequency": "monthly",
    "next_date": "2025-02-28",
    "turnover_limit": 0.20
  }
}
```

### execution_log.json

```json
{
  "workflow_id": "ws_20250131_001",
  "start_time": "2025-01-31T09:00:00Z",
  "end_time": "2025-01-31T12:00:00Z",
  "duration_minutes": 180,
  "status": "completed",
  "agents_executed": [
    {
      "agent": "01_screening_agent",
      "status": "success",
      "duration_seconds": 320,
      "output_stocks": 100
    },
    {
      "agent": "02_financial_agent",
      "status": "success",
      "duration_seconds": 580,
      "stocks_analyzed": 100
    },
    {
      "agent": "03_industry_agent",
      "status": "success",
      "duration_seconds": 420,
      "sectors_analyzed": 11
    },
    {
      "agent": "04_dcf_valuation_agent",
      "status": "success",
      "duration_seconds": 650,
      "stocks_valued": 100
    },
    {
      "agent": "05_relative_valuation_agent",
      "status": "success",
      "duration_seconds": 380,
      "stocks_valued": 100
    },
    {
      "agent": "06_technical_agent",
      "status": "success",
      "duration_seconds": 290,
      "stocks_analyzed": 100
    },
    {
      "agent": "07_risk_agent",
      "status": "success",
      "duration_seconds": 340,
      "stocks_analyzed": 100
    },
    {
      "agent": "08_sentiment_agent",
      "status": "success",
      "duration_seconds": 520,
      "stocks_analyzed": 100
    }
  ],
  "data_sources_used": [
    "KRX", "DART", "FnGuide", "Naver Finance", "News APIs"
  ],
  "warnings": [],
  "errors": []
}
```

---

## 6단계: 모니터링 및 리밸런싱

### 포트폴리오 모니터링

```python
def monitor_portfolio(portfolio, current_data):
    """
    포트폴리오 일일 모니터링 및 알림
    """
    alerts = []

    for holding in portfolio["holdings"]:
        stock_code = holding["code"]
        current_price = current_data[stock_code]["price"]
        target_price = holding["target_price"]

        # 목표가 도달
        if current_price >= target_price:
            alerts.append({
                "type": "target_reached",
                "stock": stock_code,
                "message": f"{holding['name']} 목표가 도달 ({current_price:,}원)"
            })

        # 손절선 (-15%)
        entry_price = holding["entry_price"]
        if current_price < entry_price * 0.85:
            alerts.append({
                "type": "stop_loss",
                "stock": stock_code,
                "message": f"{holding['name']} 손절선 도달 (-15%)"
            })

        # 급등/급락
        daily_change = current_data[stock_code]["daily_change"]
        if abs(daily_change) > 0.05:
            alerts.append({
                "type": "price_alert",
                "stock": stock_code,
                "message": f"{holding['name']} {daily_change*100:+.1f}% 변동"
            })

        # 주요 공시
        disclosures = current_data[stock_code].get("disclosures", [])
        for disc in disclosures:
            if disc["material"]:
                alerts.append({
                    "type": "disclosure",
                    "stock": stock_code,
                    "message": f"{holding['name']} 주요 공시: {disc['title']}"
                })

    return alerts
```

### 리밸런싱 트리거

```yaml
rebalancing_triggers:
  scheduled:
    frequency: "monthly"
    day: "last_business_day"

  event_driven:
    - trigger: "conviction_score_change"
      threshold: 15  # 점수 15점 이상 변동
      action: "review"

    - trigger: "target_price_reached"
      threshold: 0.95  # 목표가 95% 도달
      action: "partial_sell"

    - trigger: "stop_loss"
      threshold: -0.15  # -15%
      action: "sell"

    - trigger: "weight_drift"
      threshold: 0.05  # 비중 5%p 이상 이탈
      action: "rebalance"
```

---

## 실행 예시

### CLI 실행

```bash
# 전체 워크플로우 실행
python -m stock_selection_agent.run --config config/workflow.yaml

# 특정 단계만 실행
python -m stock_selection_agent.run --stage screening
python -m stock_selection_agent.run --stage valuation

# 단일 종목 분석
python -m stock_selection_agent.analyze --stock 005930
```

### 출력 예시

```
================================================================================
                    STOCK SELECTION AGENT - EXECUTION SUMMARY
================================================================================

Workflow: High Conviction Korea Equity
Date: 2025-01-31
Duration: 3h 00m

SCREENING RESULTS
─────────────────────────────────────────────────────────────────────────────────
Universe: 2,500 stocks → Screened: 100 stocks

TOP 10 BY CONVICTION SCORE
─────────────────────────────────────────────────────────────────────────────────
Rank  Code    Name            Sector    Score   Rating       Target    Upside
─────────────────────────────────────────────────────────────────────────────────
  1   005930  삼성전자         IT        85.2    Strong Buy   85,000    +30.8%
  2   000660  SK하이닉스       IT        82.1    Strong Buy   195,000   +28.5%
  3   005380  현대차          자동차     78.5    Buy          280,000   +22.3%
  4   035720  카카오          통신       77.2    Buy          65,000    +25.0%
  5   068270  셀트리온        헬스케어   76.8    Buy          210,000   +18.5%
  ...

PORTFOLIO ALLOCATION
─────────────────────────────────────────────────────────────────────────────────
Total Stocks: 25
Expected Return: 18.5%
Expected Volatility: 22.0%
Sharpe Ratio: 0.84

Sector Breakdown:
  IT:           28.5% ████████████████
  금융:         18.2% ██████████
  헬스케어:     12.5% ███████
  산업재:       15.3% ████████
  소비재:       10.5% ██████
  소재:          8.0% ████
  기타:          7.0% ████

================================================================================
                            OUTPUT FILES GENERATED
================================================================================
  - output/stock_recommendations.json
  - output/final_portfolio.json
  - output/execution_log.json
================================================================================
```

---

## 다음 단계

1. 생성된 포트폴리오를 실제 거래 시스템과 연동
2. 일일 모니터링 및 알림 설정
3. 월간 리밸런싱 스케줄 등록
4. 성과 추적 및 백테스트 실행
