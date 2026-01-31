# Agent 02: Financial Agent (재무 분석 에이전트)

## 역할

스크리닝을 통과한 종목의 재무제표를 심층 분석하여 기업의 펀더멘털 건전성과 수익성을 평가합니다. 단순 지표 나열이 아닌, 재무제표 간 연결성과 시계열 트렌드를 분석합니다.

## 입력

- `screened_stocks.json`: 01_screening_agent의 스크리닝 결과
- DART 재무제표 (연결/별도)
- 분기별 실적 데이터

## 출력

- `financial_analysis/`: 종목별 상세 재무 분석
- `financial_scores.json`: 재무 건전성 점수

---

## 재무제표 분석 체계

### 분석 대상 재무제표

```yaml
financial_statements:
  balance_sheet:
    name: "재무상태표"
    frequency: ["annual", "quarterly"]
    periods: 5  # 최근 5개년

  income_statement:
    name: "손익계산서"
    frequency: ["annual", "quarterly"]
    periods: 5

  cash_flow_statement:
    name: "현금흐름표"
    frequency: ["annual", "quarterly"]
    periods: 5
```

---

## 1단계: 수익성 분석 (Profitability Analysis)

### 핵심 수익성 지표

| 지표 | 계산식 | 우량 기준 | 경고 기준 |
|------|--------|-----------|-----------|
| **매출총이익률** | (매출 - 매출원가) / 매출 | > 30% | < 15% |
| **영업이익률** | 영업이익 / 매출 | > 10% | < 3% |
| **순이익률** | 당기순이익 / 매출 | > 7% | < 2% |
| **ROE** | 순이익 / 자기자본 | > 15% | < 5% |
| **ROA** | 순이익 / 총자산 | > 7% | < 2% |
| **ROIC** | NOPAT / 투하자본 | > 10% | < 5% |

### DuPont 분석

ROE를 3개 구성요소로 분해하여 수익성 원천을 파악합니다.

$$
ROE = \underbrace{\frac{Net\,Income}{Sales}}_{순이익률} \times \underbrace{\frac{Sales}{Assets}}_{자산회전율} \times \underbrace{\frac{Assets}{Equity}}_{재무레버리지}
$$

```
┌─────────────────────────────────────────────────────────────┐
│                     DuPont Analysis                          │
└─────────────────────────────────────────────────────────────┘

                         ROE (15%)
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
    순이익률 (5%)      자산회전율 (1.2x)   레버리지 (2.5x)
           │                │                │
    ┌──────┴──────┐   ┌─────┴─────┐   ┌──────┴──────┐
    │ 영업마진 우수 │   │ 자산 효율성│   │ 부채 수준   │
    │ 비용 관리    │   │ 재고 회전  │   │ 적정 활용   │
    └─────────────┘   └───────────┘   └─────────────┘
```

### 5개년 ROE 분해 분석

```python
def dupont_analysis(stock, years=5):
    analysis = []
    for year in range(years):
        net_margin = stock.net_income[year] / stock.revenue[year]
        asset_turnover = stock.revenue[year] / stock.total_assets[year]
        leverage = stock.total_assets[year] / stock.equity[year]
        roe = net_margin * asset_turnover * leverage

        analysis.append({
            "year": year,
            "roe": roe,
            "net_margin": net_margin,
            "asset_turnover": asset_turnover,
            "leverage": leverage
        })

    return analysis
```

---

## 2단계: 안정성 분석 (Stability Analysis)

### 유동성 지표 (Liquidity)

| 지표 | 계산식 | 우량 기준 | 위험 기준 |
|------|--------|-----------|-----------|
| **유동비율** | 유동자산 / 유동부채 | > 150% | < 100% |
| **당좌비율** | (유동자산 - 재고) / 유동부채 | > 100% | < 70% |
| **현금비율** | 현금성자산 / 유동부채 | > 30% | < 10% |

### 레버리지 지표 (Leverage)

| 지표 | 계산식 | 우량 기준 | 위험 기준 |
|------|--------|-----------|-----------|
| **부채비율** | 총부채 / 자기자본 | < 100% | > 200% |
| **순차입금비율** | (차입금-현금) / 자기자본 | < 50% | > 100% |
| **이자보상배율** | EBIT / 이자비용 | > 5x | < 2x |
| **부채/EBITDA** | 총부채 / EBITDA | < 3x | > 5x |

### Altman Z-Score (파산 예측)

$$
Z = 1.2X_1 + 1.4X_2 + 3.3X_3 + 0.6X_4 + 1.0X_5
$$

| 변수 | 설명 |
|------|------|
| $X_1$ | 운전자본 / 총자산 |
| $X_2$ | 이익잉여금 / 총자산 |
| $X_3$ | EBIT / 총자산 |
| $X_4$ | 시가총액 / 총부채 |
| $X_5$ | 매출 / 총자산 |

```yaml
z_score_interpretation:
  safe_zone: "> 2.99"       # 파산 가능성 낮음
  grey_zone: "1.81 ~ 2.99"  # 주의 필요
  distress_zone: "< 1.81"   # 파산 위험 높음
```

---

## 3단계: 효율성 분석 (Efficiency Analysis)

### 회전율 지표

| 지표 | 계산식 | 의미 |
|------|--------|------|
| **총자산회전율** | 매출 / 총자산 | 자산 활용 효율 |
| **재고자산회전율** | 매출원가 / 평균재고 | 재고 관리 효율 |
| **매출채권회전율** | 매출 / 평균매출채권 | 채권 회수 효율 |
| **매입채무회전율** | 매출원가 / 평균매입채무 | 지급 관리 효율 |

### 현금전환주기 (CCC: Cash Conversion Cycle)

$$
CCC = DIO + DSO - DPO
$$

```
┌─────────────────────────────────────────────────────────────┐
│                 Cash Conversion Cycle                        │
└─────────────────────────────────────────────────────────────┘

 원재료 구매        재고 판매        대금 회수
      │               │               │
      ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│   DIO    │ +  │   DSO    │ -  │   DPO    │ = CCC
│ (재고일) │    │(매출채권)│    │(매입채무)│
│  45일    │    │  30일    │    │  40일    │   35일
└──────────┘    └──────────┘    └──────────┘
```

| 지표 | 계산식 |
|------|--------|
| **DIO** (Days Inventory Outstanding) | 365 / 재고회전율 |
| **DSO** (Days Sales Outstanding) | 365 / 매출채권회전율 |
| **DPO** (Days Payable Outstanding) | 365 / 매입채무회전율 |

```python
def calculate_ccc(stock):
    dio = 365 / stock.inventory_turnover
    dso = 365 / stock.receivable_turnover
    dpo = 365 / stock.payable_turnover

    ccc = dio + dso - dpo

    return {
        "dio": dio,
        "dso": dso,
        "dpo": dpo,
        "ccc": ccc,
        "assessment": "good" if ccc < 60 else "concern" if ccc > 90 else "normal"
    }
```

---

## 4단계: 성장성 분석 (Growth Analysis)

### 성장률 지표

| 지표 | 계산식 | 분석 방법 |
|------|--------|-----------|
| **매출 성장률** | (매출_Y - 매출_Y-1) / 매출_Y-1 | CAGR 3년/5년 |
| **영업이익 성장률** | (OP_Y - OP_Y-1) / OP_Y-1 | CAGR 3년/5년 |
| **순이익 성장률** | (NI_Y - NI_Y-1) / NI_Y-1 | CAGR 3년/5년 |
| **EPS 성장률** | (EPS_Y - EPS_Y-1) / EPS_Y-1 | CAGR 3년/5년 |
| **BPS 성장률** | (BPS_Y - BPS_Y-1) / BPS_Y-1 | CAGR 3년/5년 |

### CAGR 계산

$$
CAGR = \left( \frac{Ending\,Value}{Beginning\,Value} \right)^{1/n} - 1
$$

### 성장 지속가능성 분석

```yaml
sustainable_growth_rate:
  formula: "ROE × (1 - Payout Ratio)"
  interpretation:
    - "실제 성장률 > SGR: 외부 자금 조달 필요"
    - "실제 성장률 < SGR: 자체 자금으로 성장 가능"
    - "실제 성장률 = SGR: 이상적 균형"
```

```python
def calculate_sustainable_growth(stock):
    roe = stock.roe
    payout_ratio = stock.dividend / stock.net_income

    sgr = roe * (1 - payout_ratio)
    actual_growth = stock.revenue_growth_yoy

    return {
        "sgr": sgr,
        "actual_growth": actual_growth,
        "funding_gap": actual_growth - sgr,
        "assessment": "sustainable" if actual_growth <= sgr else "needs_funding"
    }
```

---

## 5단계: 현금흐름 분석 (Cash Flow Analysis)

### 현금흐름표 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Cash Flow Analysis                        │
└─────────────────────────────────────────────────────────────┘

                  영업현금흐름 (CFO)
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    투자현금흐름 (CFI)        재무현금흐름 (CFF)
            │                       │
            ▼                       ▼
      CAPEX, M&A              차입, 배당
```

### 핵심 현금흐름 지표

| 지표 | 계산식 | 의미 |
|------|--------|------|
| **잉여현금흐름 (FCF)** | CFO - CAPEX | 실제 창출 현금 |
| **FCF 마진** | FCF / 매출 | 현금 창출 효율 |
| **FCF Yield** | FCF / 시가총액 | 현금 기준 밸류에이션 |
| **CAPEX/CFO** | CAPEX / CFO | 재투자 강도 |

### 이익의 질 (Earnings Quality)

$$
Accrual\,Ratio = \frac{Net\,Income - CFO}{Total\,Assets}
$$

```yaml
earnings_quality:
  excellent: "CFO > Net Income (Accrual < 0)"
  good: "0 < Accrual < 5%"
  concern: "Accrual > 10%"
  warning: "CFO < 0 while Net Income > 0"
```

```python
def analyze_earnings_quality(stock):
    cfo = stock.operating_cash_flow
    net_income = stock.net_income
    total_assets = stock.total_assets

    accrual_ratio = (net_income - cfo) / total_assets

    # 현금이익비율 (CFO/NI)
    cash_earnings_ratio = cfo / net_income if net_income > 0 else 0

    return {
        "accrual_ratio": accrual_ratio,
        "cash_earnings_ratio": cash_earnings_ratio,
        "earnings_quality": "high" if cash_earnings_ratio > 1 else "low"
    }
```

---

## 6단계: 분기별 실적 트렌드

### QoQ / YoY 분석

```python
def quarterly_trend_analysis(stock, quarters=8):
    trends = []
    for q in range(quarters):
        trends.append({
            "quarter": stock.quarters[q],
            "revenue": stock.quarterly_revenue[q],
            "revenue_yoy": calculate_yoy(stock.quarterly_revenue, q),
            "revenue_qoq": calculate_qoq(stock.quarterly_revenue, q),
            "operating_profit": stock.quarterly_op[q],
            "op_margin": stock.quarterly_op[q] / stock.quarterly_revenue[q],
            "beat_estimate": stock.quarterly_actual_eps[q] > stock.quarterly_estimate_eps[q]
        })

    return trends
```

### 실적 서프라이즈 분석

```yaml
earnings_surprise:
  metric: "실적 발표 EPS vs 컨센서스 EPS"
  interpretation:
    positive_surprise: "> +5% beat"
    inline: "-5% ~ +5%"
    negative_surprise: "< -5% miss"

  track_record:
    consecutive_beats: "3분기 연속 beat = 긍정적"
    consecutive_misses: "2분기 연속 miss = 부정적"
```

---

## 7단계: 종합 재무 점수

### Financial Score 산출

```yaml
financial_score_weights:
  profitability: 0.30
  stability: 0.25
  efficiency: 0.15
  growth: 0.20
  cash_flow: 0.10
```

```python
def calculate_financial_score(stock):
    # 수익성 점수 (30%)
    profitability_score = (
        0.3 * percentile_rank(stock.roe) +
        0.3 * percentile_rank(stock.roic) +
        0.2 * percentile_rank(stock.operating_margin) +
        0.2 * percentile_rank(stock.net_margin)
    )

    # 안정성 점수 (25%)
    stability_score = (
        0.3 * percentile_rank(stock.debt_ratio, ascending=True) +
        0.3 * percentile_rank(stock.interest_coverage) +
        0.2 * percentile_rank(stock.current_ratio) +
        0.2 * percentile_rank(stock.z_score)
    )

    # 효율성 점수 (15%)
    efficiency_score = (
        0.4 * percentile_rank(stock.asset_turnover) +
        0.3 * percentile_rank(stock.inventory_turnover) +
        0.3 * percentile_rank(stock.ccc, ascending=True)
    )

    # 성장성 점수 (20%)
    growth_score = (
        0.4 * percentile_rank(stock.revenue_cagr_3y) +
        0.4 * percentile_rank(stock.eps_cagr_3y) +
        0.2 * percentile_rank(stock.bps_cagr_3y)
    )

    # 현금흐름 점수 (10%)
    cash_flow_score = (
        0.5 * percentile_rank(stock.fcf_margin) +
        0.3 * percentile_rank(stock.cash_earnings_ratio) +
        0.2 * percentile_rank(stock.fcf_yield)
    )

    total_score = (
        0.30 * profitability_score +
        0.25 * stability_score +
        0.15 * efficiency_score +
        0.20 * growth_score +
        0.10 * cash_flow_score
    )

    return {
        "total": total_score,
        "profitability": profitability_score,
        "stability": stability_score,
        "efficiency": efficiency_score,
        "growth": growth_score,
        "cash_flow": cash_flow_score
    }
```

---

## 출력 형식

### financial_analysis/{stock_code}.json

```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "analysis_date": "2025-01-31",
  "financial_score": {
    "total": 82.5,
    "profitability": 85.2,
    "stability": 88.1,
    "efficiency": 72.3,
    "growth": 78.9,
    "cash_flow": 80.5
  },
  "key_metrics": {
    "roe": 15.3,
    "roic": 12.8,
    "operating_margin": 18.5,
    "debt_ratio": 35.2,
    "z_score": 3.8,
    "fcf_margin": 12.1
  },
  "dupont_analysis": {
    "roe": 15.3,
    "net_margin": 12.5,
    "asset_turnover": 0.85,
    "leverage": 1.44
  },
  "trends": {
    "revenue_cagr_3y": 8.5,
    "eps_cagr_3y": 12.3,
    "margin_trend": "improving"
  },
  "red_flags": [],
  "green_flags": [
    "ROE 15% 이상 유지",
    "무차입 경영",
    "FCF 지속 창출"
  ]
}
```

### financial_scores.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "total_analyzed": 100,
  "summary": {
    "avg_score": 68.5,
    "median_score": 70.2,
    "top_10_avg": 85.3
  },
  "rankings": [
    {
      "rank": 1,
      "code": "005930",
      "name": "삼성전자",
      "score": 82.5,
      "grade": "A"
    }
  ],
  "grade_distribution": {
    "A": 10,
    "B": 25,
    "C": 40,
    "D": 20,
    "F": 5
  }
}
```

---

## 다음 단계

재무 분석 결과를 `03_industry_agent`와 `04_dcf_valuation_agent`로 전달하여 산업 분석 및 밸류에이션을 수행합니다.
