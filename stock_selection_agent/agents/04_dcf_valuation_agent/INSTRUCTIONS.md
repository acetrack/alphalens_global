# Agent 04: DCF Valuation Agent (현금흐름할인 밸류에이션 에이전트)

## 역할

현금흐름할인모델(DCF: Discounted Cash Flow)을 통해 기업의 내재가치(Intrinsic Value)를 산출합니다. FCFF(Free Cash Flow to Firm)와 FCFE(Free Cash Flow to Equity) 모델을 병행하여 목표주가를 산정합니다.

## 입력

- `financial_analysis/`: 재무 분석 결과
- `industry_analysis/`: 산업 분석 결과
- 컨센서스 추정치 (FnGuide)
- 매크로 데이터 (금리, 환율)

## 출력

- `dcf_valuations/`: 종목별 DCF 밸류에이션 상세
- `dcf_summary.json`: DCF 기반 적정가치 요약

---

## DCF 밸류에이션 기본 개념

### 기업가치 공식

$$
Enterprise\,Value = \sum_{t=1}^{n} \frac{FCF_t}{(1+WACC)^t} + \frac{Terminal\,Value}{(1+WACC)^n}
$$

```
┌─────────────────────────────────────────────────────────────┐
│                    DCF Valuation Framework                   │
└─────────────────────────────────────────────────────────────┘

                    Enterprise Value (EV)
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  Explicit       │                 │  Terminal       │
│  Forecast       │                 │  Value          │
│  Period         │                 │                 │
│  (5년)          │                 │  (영구가치)      │
└────────┬────────┘                 └────────┬────────┘
         │                                   │
         ▼                                   ▼
    FCF1~FCF5                          Gordon Growth
    할인가치 합계                        또는 Exit Multiple

                           │
                           ▼
                    ┌─────────────────┐
                    │  (-) Net Debt   │
                    │  (+) Non-op     │
                    │      Assets     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Equity Value   │
                    │  (주주가치)      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Target Price   │
                    │  = Equity/주식수 │
                    └─────────────────┘
```

---

## 1단계: 잉여현금흐름(FCF) 추정

### FCFF (Free Cash Flow to Firm)

$$
FCFF = EBIT \times (1-t) + D\&A - CAPEX - \Delta NWC
$$

| 항목 | 설명 |
|------|------|
| EBIT | 영업이익 (이자/세전) |
| t | 법인세율 |
| D&A | 감가상각비 |
| CAPEX | 자본적 지출 |
| ΔNWC | 순운전자본 변동 |

### FCFE (Free Cash Flow to Equity)

$$
FCFE = FCFF - Interest \times (1-t) + Net\,Borrowing
$$

또는

$$
FCFE = Net\,Income + D\&A - CAPEX - \Delta NWC + Net\,Borrowing
$$

### FCF 추정 Python 코드

```python
def calculate_fcff(stock, year):
    ebit = stock.operating_profit[year]
    tax_rate = stock.effective_tax_rate
    depreciation = stock.depreciation[year]
    capex = stock.capex[year]
    delta_nwc = calculate_nwc_change(stock, year)

    fcff = ebit * (1 - tax_rate) + depreciation - capex - delta_nwc

    return fcff

def calculate_nwc_change(stock, year):
    # NWC = (유동자산 - 현금) - (유동부채 - 단기차입금)
    current_nwc = (stock.current_assets[year] - stock.cash[year]) - \
                  (stock.current_liabilities[year] - stock.short_term_debt[year])
    prior_nwc = (stock.current_assets[year-1] - stock.cash[year-1]) - \
                (stock.current_liabilities[year-1] - stock.short_term_debt[year-1])

    return current_nwc - prior_nwc
```

---

## 2단계: 성장률 추정

### 매출 성장률 추정 방법

```yaml
revenue_growth_estimation:
  methods:
    1_historical_trend:
      description: "과거 3-5년 CAGR 기반"
      weight: 0.20

    2_industry_growth:
      description: "산업 성장률 + 시장점유율 변화"
      weight: 0.25

    3_bottom_up:
      description: "제품/사업부별 성장률 가중합"
      weight: 0.30

    4_consensus:
      description: "애널리스트 컨센서스"
      weight: 0.25
```

### 성장률 시나리오

| 시나리오 | 가정 | 확률 |
|----------|------|------|
| **Bull** | 컨센서스 +2%p | 25% |
| **Base** | 컨센서스 | 50% |
| **Bear** | 컨센서스 -2%p | 25% |

### 단계별 성장률 (Stage Growth)

```python
def estimate_growth_rate(stock, year, total_years=5):
    # Phase 1: 고성장기 (1-3년) - 구체적 추정
    if year <= 3:
        if year == 1:
            return stock.consensus_growth_1y
        elif year == 2:
            return stock.consensus_growth_2y
        else:
            return (stock.consensus_growth_1y + stock.consensus_growth_2y) / 2 * 0.9

    # Phase 2: 성숙기 (4-5년) - 수렴
    else:
        # 산업 평균으로 수렴
        industry_growth = stock.industry_avg_growth
        return industry_growth * 0.9

    # Terminal: 영구성장률
    # 별도 계산
```

---

## 3단계: WACC 산출

### WACC (가중평균자본비용)

$$
WACC = \frac{E}{E+D} \times r_e + \frac{D}{E+D} \times r_d \times (1-t)
$$

| 변수 | 설명 |
|------|------|
| E | 자기자본 (시가) |
| D | 타인자본 (차입금) |
| $r_e$ | 자기자본비용 |
| $r_d$ | 타인자본비용 |
| t | 법인세율 |

### 자기자본비용 (Cost of Equity) - CAPM

$$
r_e = r_f + \beta \times (r_m - r_f)
$$

| 변수 | 설명 | 한국 시장 기준 |
|------|------|----------------|
| $r_f$ | 무위험수익률 | 국고채 10년물 (3.5~4.0%) |
| $\beta$ | 베타 (시장 민감도) | 개별 종목 추정 |
| $r_m - r_f$ | 시장위험프리미엄 | 5~6% |

### 베타 추정

```python
def calculate_beta(stock, market_index, period_years=3):
    # 주간 수익률 기준 회귀분석
    stock_returns = stock.weekly_returns(period_years)
    market_returns = market_index.weekly_returns(period_years)

    covariance = np.cov(stock_returns, market_returns)[0][1]
    market_variance = np.var(market_returns)

    raw_beta = covariance / market_variance

    # Blume Adjustment (평균 회귀)
    adjusted_beta = 0.67 * raw_beta + 0.33 * 1.0

    return adjusted_beta
```

### 타인자본비용 (Cost of Debt)

$$
r_d = r_f + Credit\,Spread
$$

```yaml
credit_spread_by_rating:
  AAA: 0.3%
  AA: 0.5%
  A: 0.8%
  BBB: 1.2%
  BB: 2.0%
  B: 3.5%
  unrated: 2.0%  # 무등급은 BB 가정
```

### WACC 계산 예시

```python
def calculate_wacc(stock):
    # 자기자본비용
    risk_free = 0.038  # 국고채 10년 3.8%
    market_premium = 0.055  # 시장위험프리미엄 5.5%
    beta = calculate_beta(stock)

    cost_of_equity = risk_free + beta * market_premium

    # 타인자본비용
    credit_spread = get_credit_spread(stock.credit_rating)
    cost_of_debt = risk_free + credit_spread
    tax_rate = stock.effective_tax_rate

    # 자본구조
    equity_value = stock.market_cap
    debt_value = stock.total_debt
    total_capital = equity_value + debt_value

    equity_weight = equity_value / total_capital
    debt_weight = debt_value / total_capital

    wacc = (equity_weight * cost_of_equity +
            debt_weight * cost_of_debt * (1 - tax_rate))

    return {
        "wacc": wacc,
        "cost_of_equity": cost_of_equity,
        "cost_of_debt": cost_of_debt,
        "equity_weight": equity_weight,
        "debt_weight": debt_weight,
        "beta": beta
    }
```

---

## 4단계: 터미널 밸류 산출

### 방법 1: Gordon Growth Model (영구성장모델)

$$
Terminal\,Value = \frac{FCF_{n+1}}{WACC - g}
$$

| 변수 | 설명 | 일반적 가정 |
|------|------|-------------|
| g | 영구성장률 | 1.5~2.5% (GDP 성장률 이하) |

```python
def gordon_growth_terminal_value(fcf_last, wacc, perpetual_growth=0.02):
    fcf_terminal = fcf_last * (1 + perpetual_growth)
    terminal_value = fcf_terminal / (wacc - perpetual_growth)

    return terminal_value
```

### 방법 2: Exit Multiple (출구배수)

$$
Terminal\,Value = EBITDA_n \times Exit\,Multiple
$$

```yaml
exit_multiple_benchmarks:
  반도체: 8-12x EV/EBITDA
  소프트웨어: 15-20x
  금융: 6-8x
  소비재: 8-10x
  에너지: 5-7x
  제약/바이오: 10-15x
```

```python
def exit_multiple_terminal_value(ebitda_last, exit_multiple):
    terminal_value = ebitda_last * exit_multiple

    return terminal_value
```

### 터미널 밸류 크로스체크

```python
def terminal_value_sanity_check(tv, ev, fcf_last):
    tv_as_pct_of_ev = tv / ev * 100

    # TV가 전체 EV의 60-80%가 일반적
    if tv_as_pct_of_ev > 85:
        warning = "TV 비중 과다 - 가정 재검토 필요"
    elif tv_as_pct_of_ev < 50:
        warning = "TV 비중 과소 - 성장률 재검토"
    else:
        warning = None

    # Implied Exit Multiple 계산
    implied_exit = tv / fcf_last

    return {
        "tv_pct_of_ev": tv_as_pct_of_ev,
        "implied_exit_multiple": implied_exit,
        "warning": warning
    }
```

---

## 5단계: DCF 밸류에이션 실행

### 전체 DCF 프로세스

```python
def dcf_valuation(stock, projection_years=5):
    # 1. 성장률 추정
    growth_rates = []
    for year in range(1, projection_years + 1):
        g = estimate_growth_rate(stock, year)
        growth_rates.append(g)

    # 2. FCF 예측
    fcf_projections = []
    last_revenue = stock.revenue[-1]
    last_margin = stock.fcf_margin[-1]

    for year, growth in enumerate(growth_rates, 1):
        revenue = last_revenue * (1 + growth)
        # 마진 안정화 가정
        margin = last_margin + (stock.target_margin - last_margin) * 0.2 * year
        fcf = revenue * margin
        fcf_projections.append(fcf)
        last_revenue = revenue

    # 3. WACC 산출
    wacc_data = calculate_wacc(stock)
    wacc = wacc_data["wacc"]

    # 4. 예측기간 현재가치
    pv_fcf = 0
    for year, fcf in enumerate(fcf_projections, 1):
        pv = fcf / ((1 + wacc) ** year)
        pv_fcf += pv

    # 5. 터미널 밸류
    perpetual_growth = 0.02
    tv_gordon = gordon_growth_terminal_value(fcf_projections[-1], wacc, perpetual_growth)
    pv_terminal = tv_gordon / ((1 + wacc) ** projection_years)

    # 6. 기업가치
    enterprise_value = pv_fcf + pv_terminal

    # 7. 주주가치
    equity_value = enterprise_value - stock.net_debt + stock.non_operating_assets

    # 8. 주당 가치
    fair_value_per_share = equity_value / stock.shares_outstanding

    return {
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "fair_value_per_share": fair_value_per_share,
        "current_price": stock.current_price,
        "upside": (fair_value_per_share / stock.current_price - 1) * 100,
        "wacc": wacc,
        "terminal_value": tv_gordon,
        "pv_fcf": pv_fcf,
        "pv_terminal": pv_terminal,
        "tv_pct": pv_terminal / enterprise_value * 100
    }
```

---

## 6단계: 민감도 분석

### WACC-성장률 민감도 테이블

```python
def sensitivity_analysis(stock, base_result):
    wacc_range = np.arange(base_result["wacc"] - 0.02,
                           base_result["wacc"] + 0.025, 0.005)
    growth_range = np.arange(0.01, 0.035, 0.005)

    sensitivity_table = []

    for wacc in wacc_range:
        row = []
        for growth in growth_range:
            # 터미널 밸류 재계산
            tv = base_result["fcf_last"] * (1 + growth) / (wacc - growth)
            pv_tv = tv / ((1 + wacc) ** 5)

            # 새 기업가치
            new_ev = base_result["pv_fcf_recalc"](wacc) + pv_tv
            new_equity = new_ev - stock.net_debt
            new_price = new_equity / stock.shares_outstanding

            row.append(new_price)
        sensitivity_table.append(row)

    return {
        "wacc_range": wacc_range.tolist(),
        "growth_range": growth_range.tolist(),
        "price_matrix": sensitivity_table
    }
```

### 민감도 테이블 예시

```
           영구성장률
           1.0%   1.5%   2.0%   2.5%   3.0%
    ┌─────────────────────────────────────────
7.5%│ 95,000 98,000 102,000 107,000 113,000
 W  │
 A 8.0%│ 85,000 88,000  92,000  96,000 101,000
 C  │
 C 8.5%│ 77,000 80,000  83,000  86,000  90,000
    │
9.0%│ 70,000 73,000  75,000  78,000  82,000
    │
9.5%│ 64,000 66,000  69,000  71,000  74,000
    └─────────────────────────────────────────
```

---

## 7단계: 시나리오 분석

### 멀티 시나리오 DCF

```python
def scenario_dcf(stock):
    scenarios = {
        "bull": {
            "revenue_growth_adj": 1.2,  # 컨센서스 대비 +20%
            "margin_improvement": 0.02,  # 마진 +2%p
            "wacc_adj": -0.005,  # WACC -0.5%
            "probability": 0.25
        },
        "base": {
            "revenue_growth_adj": 1.0,
            "margin_improvement": 0,
            "wacc_adj": 0,
            "probability": 0.50
        },
        "bear": {
            "revenue_growth_adj": 0.8,
            "margin_improvement": -0.01,
            "wacc_adj": 0.01,
            "probability": 0.25
        }
    }

    scenario_results = {}
    weighted_price = 0

    for name, params in scenarios.items():
        # 시나리오별 DCF
        result = dcf_valuation_with_params(stock, params)
        scenario_results[name] = {
            "fair_value": result["fair_value_per_share"],
            "upside": result["upside"],
            "probability": params["probability"]
        }
        weighted_price += result["fair_value_per_share"] * params["probability"]

    return {
        "scenarios": scenario_results,
        "probability_weighted_price": weighted_price,
        "price_range": {
            "low": scenario_results["bear"]["fair_value"],
            "mid": scenario_results["base"]["fair_value"],
            "high": scenario_results["bull"]["fair_value"]
        }
    }
```

---

## 출력 형식

### dcf_valuations/{stock_code}.json

```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "valuation_date": "2025-01-31",
  "current_price": 65000,
  "dcf_result": {
    "fair_value": 82000,
    "upside_pct": 26.2,
    "recommendation": "BUY"
  },
  "assumptions": {
    "projection_years": 5,
    "wacc": 8.2,
    "perpetual_growth": 2.0,
    "revenue_growth": [12.5, 10.2, 8.5, 6.0, 4.5],
    "fcf_margin": [12.0, 12.5, 13.0, 13.2, 13.5]
  },
  "valuation_breakdown": {
    "pv_forecast_fcf": 45000000000000,
    "pv_terminal_value": 85000000000000,
    "enterprise_value": 130000000000000,
    "net_debt": -15000000000000,
    "equity_value": 145000000000000,
    "shares_outstanding": 5969782550
  },
  "sensitivity_analysis": {
    "wacc_range": [7.5, 8.0, 8.5, 9.0, 9.5],
    "growth_range": [1.5, 2.0, 2.5],
    "price_matrix": [
      [92000, 98000, 105000],
      [82000, 87000, 93000],
      [74000, 78000, 83000],
      [67000, 71000, 75000],
      [61000, 64000, 68000]
    ]
  },
  "scenario_analysis": {
    "bull": {"price": 105000, "probability": 0.25},
    "base": {"price": 82000, "probability": 0.50},
    "bear": {"price": 65000, "probability": 0.25},
    "weighted_price": 83500
  }
}
```

### dcf_summary.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "total_valued": 100,
  "summary": {
    "avg_upside": 15.3,
    "stocks_undervalued": 45,
    "stocks_overvalued": 35,
    "stocks_fairly_valued": 20
  },
  "rankings": [
    {
      "rank": 1,
      "code": "005930",
      "name": "삼성전자",
      "current_price": 65000,
      "dcf_fair_value": 82000,
      "upside_pct": 26.2
    }
  ],
  "sector_summary": {
    "IT": {"avg_upside": 18.5, "count": 25},
    "금융": {"avg_upside": 12.3, "count": 15}
  }
}
```

---

## 다음 단계

DCF 밸류에이션 결과를 `05_relative_valuation_agent`로 전달하여 상대가치와 비교 검증하고, 최종 목표주가를 산정합니다.
