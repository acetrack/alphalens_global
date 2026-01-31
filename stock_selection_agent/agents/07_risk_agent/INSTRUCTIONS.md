# Agent 07: Risk Agent (리스크 분석 에이전트)

## 역할

투자 리스크를 정량화하고 평가합니다. 시장 리스크, 신용 리스크, 유동성 리스크 등 다양한 리스크 요인을 분석하여 포트폴리오 구성 시 리스크 조정 수익률(Risk-Adjusted Return)을 최적화할 수 있도록 지원합니다.

## 입력

- `financial_analysis/`: 재무 분석 결과
- `technical_analysis/`: 기술적 분석 결과
- 가격 히스토리 데이터
- 매크로 경제 데이터

## 출력

- `risk_analysis/`: 종목별 리스크 분석
- `risk_scores.json`: 리스크 점수 요약

---

## 리스크 분석 체계

```
┌─────────────────────────────────────────────────────────────┐
│                    Risk Analysis Framework                   │
└─────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   Total Risk    │
                    │   종합 리스크    │
                    └────────┬────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
    ▼                        ▼                        ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Market     │      │  Credit     │      │  Liquidity  │
│  Risk       │      │  Risk       │      │  Risk       │
│  시장 리스크 │      │  신용 리스크 │      │  유동성 리스크│
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ - Beta      │      │ - Z-Score   │      │ - Turnover  │
│ - VaR       │      │ - D/E Ratio │      │ - Bid-Ask   │
│ - Volatility│      │ - ICR       │      │ - Float     │
│ - MDD       │      │ - Rating    │      │ - Volume    │
└─────────────┘      └─────────────┘      └─────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Concentration  │
                    │  & Event Risk   │
                    │  집중/이벤트     │
                    └─────────────────┘
```

---

## 1단계: 시장 리스크 (Market Risk)

### Beta (베타)

시장 대비 민감도를 측정합니다.

$$
\beta = \frac{Cov(R_i, R_m)}{Var(R_m)}
$$

```python
def calculate_beta(stock, market_index, period_weeks=156):  # 3년
    stock_returns = stock.weekly_returns[-period_weeks:]
    market_returns = market_index.weekly_returns[-period_weeks:]

    covariance = np.cov(stock_returns, market_returns)[0][1]
    market_variance = np.var(market_returns)

    raw_beta = covariance / market_variance

    # Blume Adjustment (평균 회귀)
    adjusted_beta = 0.67 * raw_beta + 0.33 * 1.0

    # 해석
    if adjusted_beta > 1.5:
        risk_level = "high"
        interpretation = "시장 대비 변동성 매우 큼"
    elif adjusted_beta > 1.2:
        risk_level = "moderate_high"
        interpretation = "시장 대비 변동성 큼"
    elif adjusted_beta > 0.8:
        risk_level = "moderate"
        interpretation = "시장과 유사한 변동성"
    else:
        risk_level = "low"
        interpretation = "방어적 종목"

    return {
        "raw_beta": raw_beta,
        "adjusted_beta": adjusted_beta,
        "risk_level": risk_level,
        "interpretation": interpretation
    }
```

### Volatility (변동성)

#### Historical Volatility

$$
\sigma = \sqrt{\frac{\sum_{i=1}^{n}(R_i - \bar{R})^2}{n-1}} \times \sqrt{252}
$$

```python
def calculate_volatility(stock, period_days=252):
    returns = stock.daily_returns[-period_days:]

    # 일간 변동성
    daily_vol = np.std(returns)

    # 연환산 변동성
    annual_vol = daily_vol * np.sqrt(252)

    # 변동성 수준 평가
    if annual_vol > 0.50:
        risk_level = "very_high"
    elif annual_vol > 0.35:
        risk_level = "high"
    elif annual_vol > 0.20:
        risk_level = "moderate"
    else:
        risk_level = "low"

    return {
        "daily_volatility": daily_vol,
        "annual_volatility": annual_vol,
        "risk_level": risk_level
    }
```

### VaR (Value at Risk)

주어진 신뢰수준에서 최대 손실 가능 금액을 측정합니다.

$$
VaR_{95\%} = \mu - 1.65 \times \sigma
$$

```python
def calculate_var(stock, confidence_levels=[0.95, 0.99], period_days=252):
    returns = stock.daily_returns[-period_days:]

    var_results = {}

    for conf in confidence_levels:
        # Parametric VaR (정규분포 가정)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        z_score = norm.ppf(1 - conf)

        parametric_var = -(mean_return + z_score * std_return)

        # Historical VaR (실제 분포 기반)
        historical_var = -np.percentile(returns, (1 - conf) * 100)

        var_results[f"var_{int(conf*100)}"] = {
            "parametric": parametric_var,
            "historical": historical_var,
            "interpretation": f"{conf*100}% 신뢰수준에서 일일 최대 손실 {historical_var*100:.2f}%"
        }

    return var_results
```

### CVaR (Conditional VaR / Expected Shortfall)

$$
CVaR = E[Loss | Loss > VaR]
$$

```python
def calculate_cvar(stock, confidence=0.95, period_days=252):
    returns = stock.daily_returns[-period_days:]

    var = np.percentile(returns, (1 - confidence) * 100)
    tail_losses = returns[returns <= var]

    cvar = -np.mean(tail_losses)

    return {
        "var_95": -var,
        "cvar_95": cvar,
        "interpretation": f"최악의 5% 시나리오에서 평균 {cvar*100:.2f}% 손실 예상"
    }
```

### Maximum Drawdown (MDD)

$$
MDD = \frac{Trough - Peak}{Peak}
$$

```python
def calculate_mdd(stock, period_days=756):  # 3년
    prices = stock.prices[-period_days:]

    peak = prices[0]
    max_drawdown = 0
    drawdown_start = 0
    drawdown_end = 0
    current_drawdown_start = 0

    for i, price in enumerate(prices):
        if price > peak:
            peak = price
            current_drawdown_start = i

        drawdown = (peak - price) / peak

        if drawdown > max_drawdown:
            max_drawdown = drawdown
            drawdown_start = current_drawdown_start
            drawdown_end = i

    # 회복 기간
    recovery_days = None
    for i in range(drawdown_end, len(prices)):
        if prices[i] >= prices[drawdown_start]:
            recovery_days = i - drawdown_end
            break

    return {
        "max_drawdown": max_drawdown,
        "mdd_percent": max_drawdown * 100,
        "drawdown_period": f"{drawdown_start} ~ {drawdown_end}",
        "recovery_days": recovery_days,
        "risk_level": "high" if max_drawdown > 0.40 else "moderate" if max_drawdown > 0.25 else "low"
    }
```

---

## 2단계: 신용 리스크 (Credit Risk)

### Altman Z-Score (파산 위험)

$$
Z = 1.2X_1 + 1.4X_2 + 3.3X_3 + 0.6X_4 + 1.0X_5
$$

```python
def calculate_z_score(stock):
    # X1: Working Capital / Total Assets
    x1 = stock.working_capital / stock.total_assets

    # X2: Retained Earnings / Total Assets
    x2 = stock.retained_earnings / stock.total_assets

    # X3: EBIT / Total Assets
    x3 = stock.ebit / stock.total_assets

    # X4: Market Cap / Total Liabilities
    x4 = stock.market_cap / stock.total_liabilities

    # X5: Sales / Total Assets
    x5 = stock.revenue / stock.total_assets

    z_score = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5

    # 해석
    if z_score > 2.99:
        zone = "safe"
        risk_level = "low"
        interpretation = "파산 가능성 낮음"
    elif z_score > 1.81:
        zone = "grey"
        risk_level = "moderate"
        interpretation = "주의 필요 (회색 지대)"
    else:
        zone = "distress"
        risk_level = "high"
        interpretation = "파산 위험 높음"

    return {
        "z_score": z_score,
        "zone": zone,
        "risk_level": risk_level,
        "interpretation": interpretation,
        "components": {"x1": x1, "x2": x2, "x3": x3, "x4": x4, "x5": x5}
    }
```

### 부채 관련 지표

```python
def analyze_debt_risk(stock):
    # 부채비율
    debt_to_equity = stock.total_debt / stock.equity

    # 순차입금비율
    net_debt_ratio = (stock.total_debt - stock.cash) / stock.equity

    # 이자보상배율
    interest_coverage = stock.ebit / stock.interest_expense if stock.interest_expense > 0 else float('inf')

    # 부채/EBITDA
    debt_to_ebitda = stock.total_debt / stock.ebitda if stock.ebitda > 0 else float('inf')

    # 종합 신용 리스크
    risk_score = 0
    red_flags = []

    if debt_to_equity > 2.0:
        risk_score += 30
        red_flags.append("부채비율 200% 초과")
    elif debt_to_equity > 1.5:
        risk_score += 15

    if interest_coverage < 2:
        risk_score += 30
        red_flags.append("이자보상배율 2배 미만")
    elif interest_coverage < 3:
        risk_score += 15

    if debt_to_ebitda > 4:
        risk_score += 25
        red_flags.append("부채/EBITDA 4배 초과")

    return {
        "debt_to_equity": debt_to_equity,
        "net_debt_ratio": net_debt_ratio,
        "interest_coverage": interest_coverage,
        "debt_to_ebitda": debt_to_ebitda,
        "risk_score": risk_score,
        "risk_level": "high" if risk_score > 50 else "moderate" if risk_score > 25 else "low",
        "red_flags": red_flags
    }
```

---

## 3단계: 유동성 리스크 (Liquidity Risk)

### 거래량 기반 유동성

```python
def analyze_liquidity_risk(stock):
    # 일평균 거래대금
    avg_daily_value = stock.avg_daily_trading_value_20d

    # 회전율
    turnover_ratio = stock.annual_trading_volume / stock.shares_outstanding

    # 유동주식비율
    free_float_ratio = stock.free_float / stock.shares_outstanding

    # 대량 매도 영향 추정
    # 1억원 매도 시 예상 가격 영향
    price_impact_100m = estimate_price_impact(stock, 100000000)

    # 유동성 점수
    if avg_daily_value > 10000000000:  # 100억 이상
        liquidity_grade = "A"
        risk_level = "low"
    elif avg_daily_value > 5000000000:  # 50억 이상
        liquidity_grade = "B"
        risk_level = "low"
    elif avg_daily_value > 1000000000:  # 10억 이상
        liquidity_grade = "C"
        risk_level = "moderate"
    elif avg_daily_value > 500000000:  # 5억 이상
        liquidity_grade = "D"
        risk_level = "moderate_high"
    else:
        liquidity_grade = "F"
        risk_level = "high"

    return {
        "avg_daily_trading_value": avg_daily_value,
        "turnover_ratio": turnover_ratio,
        "free_float_ratio": free_float_ratio,
        "price_impact_100m": price_impact_100m,
        "liquidity_grade": liquidity_grade,
        "risk_level": risk_level
    }

def estimate_price_impact(stock, trade_value):
    # Kyle's Lambda 기반 추정 (단순화)
    avg_daily_value = stock.avg_daily_trading_value_20d
    impact = (trade_value / avg_daily_value) * stock.historical_volatility * 0.5

    return impact * 100  # 퍼센트 영향
```

### 호가 스프레드

```python
def bid_ask_spread_analysis(stock):
    bid = stock.bid_price
    ask = stock.ask_price
    mid = (bid + ask) / 2

    spread = (ask - bid) / mid * 100

    if spread < 0.1:
        spread_grade = "excellent"
    elif spread < 0.3:
        spread_grade = "good"
    elif spread < 0.5:
        spread_grade = "moderate"
    else:
        spread_grade = "poor"

    return {
        "bid_ask_spread": spread,
        "spread_grade": spread_grade,
        "transaction_cost": spread / 2  # 편도 거래비용
    }
```

---

## 4단계: 집중 리스크 (Concentration Risk)

### 지분 구조 리스크

```python
def ownership_concentration_risk(stock):
    largest_shareholder = stock.largest_shareholder_pct
    top5_shareholders = stock.top5_shareholders_pct
    foreign_ownership = stock.foreign_ownership_pct

    risks = []

    # 최대주주 지분 집중
    if largest_shareholder > 50:
        risks.append({
            "type": "controlling_shareholder",
            "description": f"최대주주 지분 {largest_shareholder}% - 소수주주권 제한",
            "severity": "moderate"
        })

    # 외국인 지분 과다
    if foreign_ownership > 50:
        risks.append({
            "type": "foreign_concentration",
            "description": f"외국인 지분 {foreign_ownership}% - 외부 충격 취약",
            "severity": "moderate"
        })

    # 유동주식 부족
    free_float = 100 - largest_shareholder - stock.treasury_stock_pct
    if free_float < 30:
        risks.append({
            "type": "low_free_float",
            "description": f"유동주식 비율 {free_float}% - 유동성 제한",
            "severity": "high"
        })

    return {
        "largest_shareholder": largest_shareholder,
        "top5_shareholders": top5_shareholders,
        "foreign_ownership": foreign_ownership,
        "free_float": free_float,
        "risks": risks
    }
```

### 사업 집중 리스크

```python
def business_concentration_risk(stock):
    risks = []

    # 매출 집중도
    if stock.top_customer_revenue_pct > 30:
        risks.append({
            "type": "customer_concentration",
            "description": f"최대 고객 매출 비중 {stock.top_customer_revenue_pct}%",
            "severity": "high"
        })

    # 제품 집중도
    if stock.top_product_revenue_pct > 50:
        risks.append({
            "type": "product_concentration",
            "description": f"주력 제품 매출 비중 {stock.top_product_revenue_pct}%",
            "severity": "moderate"
        })

    # 지역 집중도
    if stock.domestic_revenue_pct > 80:
        risks.append({
            "type": "geographic_concentration",
            "description": "내수 의존도 80% 이상",
            "severity": "low"
        })

    return {
        "customer_concentration": stock.top_customer_revenue_pct,
        "product_concentration": stock.top_product_revenue_pct,
        "geographic_concentration": stock.domestic_revenue_pct,
        "risks": risks
    }
```

---

## 5단계: 스트레스 테스트

### 시나리오 분석

```python
def stress_test(stock):
    scenarios = {
        "market_crash": {
            "description": "시장 급락 (-20%)",
            "market_return": -0.20,
            "calculation": lambda s: s.price * (1 + s.beta * (-0.20))
        },
        "interest_rate_shock": {
            "description": "금리 200bp 인상",
            "rate_change": 0.02,
            "calculation": lambda s: estimate_rate_sensitivity(s, 0.02)
        },
        "currency_depreciation": {
            "description": "원화 15% 약세",
            "fx_change": -0.15,
            "calculation": lambda s: estimate_fx_sensitivity(s, -0.15)
        },
        "sector_downturn": {
            "description": "섹터 언더퍼폼 (-15%)",
            "sector_return": -0.15,
            "calculation": lambda s: s.price * (1 + (-0.15) * s.sector_beta)
        }
    }

    results = {}
    for name, scenario in scenarios.items():
        stressed_price = scenario["calculation"](stock)
        loss_pct = (stressed_price / stock.price - 1) * 100

        results[name] = {
            "description": scenario["description"],
            "stressed_price": stressed_price,
            "loss_percent": loss_pct,
            "severity": "high" if loss_pct < -25 else "moderate" if loss_pct < -15 else "low"
        }

    return results

def estimate_rate_sensitivity(stock, rate_change):
    # Duration 기반 추정 (고부채 기업에 불리)
    debt_ratio = stock.total_debt / stock.equity
    sensitivity = -rate_change * debt_ratio * 5  # 단순화된 추정
    return stock.price * (1 + sensitivity)

def estimate_fx_sensitivity(stock, fx_change):
    # 수출/수입 비중에 따른 민감도
    export_ratio = stock.export_revenue_pct / 100
    import_ratio = stock.import_cost_pct / 100
    net_exposure = export_ratio - import_ratio

    # 원화 약세 시: 수출 기업 유리, 수입 의존 기업 불리
    sensitivity = fx_change * net_exposure * 0.5
    return stock.price * (1 + sensitivity)
```

---

## 6단계: 종합 리스크 점수

### Risk Score 산출

```python
def calculate_total_risk_score(stock):
    # 시장 리스크 (35%)
    beta_analysis = calculate_beta(stock)
    volatility = calculate_volatility(stock)
    var_analysis = calculate_var(stock)
    mdd = calculate_mdd(stock)

    market_risk_score = (
        0.30 * normalize_score(beta_analysis["adjusted_beta"], 0.5, 2.0) +
        0.25 * normalize_score(volatility["annual_volatility"], 0.15, 0.50) +
        0.25 * normalize_score(var_analysis["var_95"]["historical"], 0.01, 0.05) +
        0.20 * normalize_score(mdd["max_drawdown"], 0.15, 0.50)
    )

    # 신용 리스크 (30%)
    z_score = calculate_z_score(stock)
    debt_risk = analyze_debt_risk(stock)

    credit_risk_score = (
        0.40 * (100 - normalize_score(z_score["z_score"], 1.0, 4.0)) +
        0.60 * debt_risk["risk_score"]
    )

    # 유동성 리스크 (20%)
    liquidity = analyze_liquidity_risk(stock)
    spread = bid_ask_spread_analysis(stock)

    liquidity_risk_score = (
        0.70 * grade_to_score(liquidity["liquidity_grade"]) +
        0.30 * normalize_score(spread["bid_ask_spread"], 0.1, 1.0)
    )

    # 집중 리스크 (15%)
    ownership = ownership_concentration_risk(stock)
    business = business_concentration_risk(stock)

    concentration_risk_score = len(ownership["risks"]) * 15 + len(business["risks"]) * 10

    # 종합 리스크 점수 (높을수록 리스크 높음)
    total_risk_score = (
        0.35 * market_risk_score +
        0.30 * credit_risk_score +
        0.20 * liquidity_risk_score +
        0.15 * concentration_risk_score
    )

    # 리스크 등급
    if total_risk_score > 70:
        risk_grade = "High Risk"
    elif total_risk_score > 50:
        risk_grade = "Moderate-High Risk"
    elif total_risk_score > 30:
        risk_grade = "Moderate Risk"
    else:
        risk_grade = "Low Risk"

    return {
        "total_score": total_risk_score,
        "risk_grade": risk_grade,
        "breakdown": {
            "market_risk": market_risk_score,
            "credit_risk": credit_risk_score,
            "liquidity_risk": liquidity_risk_score,
            "concentration_risk": concentration_risk_score
        }
    }
```

---

## 출력 형식

### risk_analysis/{stock_code}.json

```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "analysis_date": "2025-01-31",
  "risk_score": {
    "total": 32,
    "grade": "Moderate Risk",
    "breakdown": {
      "market_risk": 35,
      "credit_risk": 15,
      "liquidity_risk": 20,
      "concentration_risk": 45
    }
  },
  "market_risk": {
    "beta": 1.15,
    "annual_volatility": 0.28,
    "var_95": 0.025,
    "cvar_95": 0.035,
    "max_drawdown": 0.32
  },
  "credit_risk": {
    "z_score": 3.8,
    "zone": "safe",
    "debt_to_equity": 0.35,
    "interest_coverage": 25.3
  },
  "liquidity_risk": {
    "avg_daily_trading_value": 850000000000,
    "liquidity_grade": "A",
    "bid_ask_spread": 0.05
  },
  "concentration_risk": {
    "largest_shareholder": 18.5,
    "foreign_ownership": 52.3,
    "risks": ["외국인 지분 과다"]
  },
  "stress_test": {
    "market_crash": {"loss": -23, "severity": "moderate"},
    "interest_rate_shock": {"loss": -5, "severity": "low"},
    "currency_depreciation": {"loss": 8, "severity": "positive"}
  },
  "key_risks": [
    "반도체 사이클 변동성",
    "중국 시장 의존도"
  ],
  "risk_adjusted_expected_return": 12.5
}
```

### risk_scores.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "summary": {
    "avg_risk_score": 42,
    "low_risk_count": 25,
    "moderate_risk_count": 50,
    "high_risk_count": 25
  },
  "rankings": [
    {
      "rank": 1,
      "code": "005930",
      "name": "삼성전자",
      "risk_score": 32,
      "grade": "Moderate Risk"
    }
  ],
  "risk_distribution": {
    "market_risk_avg": 38,
    "credit_risk_avg": 35,
    "liquidity_risk_avg": 45,
    "concentration_risk_avg": 50
  }
}
```

---

## 다음 단계

리스크 분석 결과를 `00_master_orchestrator`로 전달하여 리스크 조정 수익률 기반 최종 포트폴리오 구성에 활용합니다.
