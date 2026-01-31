# Agent 01: Screening Agent (스크리닝 에이전트)

## 역할

전체 유니버스(KOSPI/KOSDAQ)에서 투자 가능한 종목을 멀티팩터 퀀트 스크리닝을 통해 100개 이내로 축소합니다. 펀드매니저가 실제로 사용하는 팩터 투자(Factor Investing) 방법론을 적용합니다.

## 입력

- 전체 상장 종목 리스트 (KRX)
- 기본 재무 데이터 (FnGuide, DART)
- 가격/거래량 데이터 (KRX, Naver Finance)

## 출력

- `screened_stocks.json`: 스크리닝 통과 종목 리스트
- `screening_report.json`: 팩터별 점수 및 스크리닝 결과

---

## 1단계: 기본 필터링 (Hard Filters)

투자 불가능하거나 유동성이 부족한 종목을 제외합니다.

### 필수 제외 조건

```yaml
hard_filters:
  exclude:
    - type: "관리종목"
    - type: "거래정지"
    - type: "스팩(SPAC)"
    - type: "투자주의환기종목"
    - type: "상장폐지 예정"

  minimum_requirements:
    market_cap: 100000000000      # 시가총액 1000억 이상
    daily_trading_value: 1000000000  # 일평균 거래대금 10억 이상
    listing_days: 365             # 상장 후 1년 경과
    free_float_ratio: 0.20        # 유동주식비율 20% 이상
```

### 필터링 후 예상 종목 수

```
전체 상장 종목: ~2,500개
├── 관리종목 제외: -50개
├── 스팩 제외: -100개
├── 시가총액 필터: -1,200개
├── 거래대금 필터: -400개
└── 최종: ~750개
```

---

## 2단계: 팩터 스크리닝 (Factor Screening)

5대 팩터(Value, Quality, Momentum, Growth, Size)에 대해 종목별 점수를 산출합니다.

### Factor 1: Value (가치 팩터) - 25%

저평가된 종목을 발굴합니다.

| 지표 | 계산식 | 비중 | 선호 방향 |
|------|--------|------|-----------|
| **PER** | 주가 / EPS | 30% | 낮을수록 좋음 |
| **PBR** | 주가 / BPS | 25% | 낮을수록 좋음 |
| **EV/EBITDA** | (시총+순차입금) / EBITDA | 30% | 낮을수록 좋음 |
| **PSR** | 시가총액 / 매출액 | 15% | 낮을수록 좋음 |

#### Value Score 산출

$$
Value\_Score = w_1 \cdot Rank(PER) + w_2 \cdot Rank(PBR) + w_3 \cdot Rank(EV/EBITDA) + w_4 \cdot Rank(PSR)
$$

```python
# Percentile Rank 변환 (0~100)
def calculate_value_score(stock):
    per_rank = percentile_rank(stock.per, ascending=True)  # 낮을수록 높은 점수
    pbr_rank = percentile_rank(stock.pbr, ascending=True)
    ev_ebitda_rank = percentile_rank(stock.ev_ebitda, ascending=True)
    psr_rank = percentile_rank(stock.psr, ascending=True)

    return (0.30 * per_rank +
            0.25 * pbr_rank +
            0.30 * ev_ebitda_rank +
            0.15 * psr_rank)
```

#### Value Trap 필터

단순 저PER/저PBR이 아닌 실질적 저평가 종목 선별:

```yaml
value_trap_filters:
  # 이익이 감소하는 저PER 제외
  - condition: "PER < 5 AND EPS_Growth_YoY < -20%"
    action: "exclude"

  # 자산 감소하는 저PBR 제외
  - condition: "PBR < 0.5 AND BPS_Growth_YoY < -10%"
    action: "exclude"

  # 실적 적자 전환 예상 종목 제외
  - condition: "Forward_EPS < 0"
    action: "exclude"
```

---

### Factor 2: Quality (품질 팩터) - 25%

재무적으로 우량한 기업을 선별합니다.

| 지표 | 계산식 | 비중 | 기준 |
|------|--------|------|------|
| **ROE** | 순이익 / 자기자본 | 30% | 10% 이상 |
| **ROIC** | NOPAT / 투하자본 | 25% | 8% 이상 |
| **부채비율** | 총부채 / 자기자본 | 25% | 150% 이하 |
| **이자보상배율** | EBIT / 이자비용 | 20% | 3배 이상 |

#### Quality Score 산출

$$
Quality\_Score = w_1 \cdot Rank(ROE) + w_2 \cdot Rank(ROIC) + w_3 \cdot Rank(1/D\_Ratio) + w_4 \cdot Rank(ICR)
$$

```python
def calculate_quality_score(stock):
    roe_rank = percentile_rank(stock.roe, ascending=False)  # 높을수록 높은 점수
    roic_rank = percentile_rank(stock.roic, ascending=False)
    debt_rank = percentile_rank(stock.debt_ratio, ascending=True)  # 낮을수록 높은 점수
    icr_rank = percentile_rank(stock.interest_coverage, ascending=False)

    return (0.30 * roe_rank +
            0.25 * roic_rank +
            0.25 * debt_rank +
            0.20 * icr_rank)
```

#### Quality 세부 필터

```yaml
quality_minimum:
  roe: 5%           # 최소 ROE
  operating_margin: 3%  # 최소 영업이익률
  debt_ratio: 300%   # 최대 부채비율
  current_ratio: 100%  # 최소 유동비율
```

---

### Factor 3: Momentum (모멘텀 팩터) - 20%

상승 추세에 있는 종목을 선별합니다.

| 지표 | 계산식 | 비중 | 설명 |
|------|--------|------|------|
| **12M 수익률** | (현재가 - 12M전 가격) / 12M전 가격 | 40% | 1년 가격 모멘텀 |
| **이익수정률** | 컨센서스 변화율 | 35% | 애널리스트 추정치 상향 |
| **1M 수익률** | (현재가 - 1M전 가격) / 1M전 가격 | 25% | 단기 모멘텀 |

#### 이익수정률 (Earnings Revision) 상세

$$
Earnings\_Revision = \frac{EPS_{current} - EPS_{3M\_ago}}{|EPS_{3M\_ago}|} \times 100
$$

```yaml
earnings_revision:
  # 긍정적 수정
  positive:
    threshold: 3%  # 3% 이상 상향
    weight: 1.5x

  # 부정적 수정
  negative:
    threshold: -3%  # 3% 이상 하향
    weight: 0.5x
```

#### Momentum Score 산출

```python
def calculate_momentum_score(stock):
    # 12M 수익률 (최근 1개월 제외 - Mean Reversion 효과 고려)
    mom_12m = (stock.price / stock.price_12m_ago - 1) * 100
    mom_12m_rank = percentile_rank(mom_12m, ascending=False)

    # 이익수정률
    earnings_rev = stock.consensus_eps_change_3m
    earnings_rev_rank = percentile_rank(earnings_rev, ascending=False)

    # 1M 수익률
    mom_1m = (stock.price / stock.price_1m_ago - 1) * 100
    mom_1m_rank = percentile_rank(mom_1m, ascending=False)

    return (0.40 * mom_12m_rank +
            0.35 * earnings_rev_rank +
            0.25 * mom_1m_rank)
```

---

### Factor 4: Growth (성장 팩터) - 20%

높은 성장성을 보이는 종목을 선별합니다.

| 지표 | 계산식 | 비중 | 기준 |
|------|--------|------|------|
| **매출 성장률** | (매출_Y - 매출_Y-1) / 매출_Y-1 | 35% | YoY |
| **EPS 성장률** | (EPS_Y - EPS_Y-1) / EPS_Y-1 | 40% | YoY |
| **영업이익 성장률** | (OP_Y - OP_Y-1) / OP_Y-1 | 25% | YoY |

#### Forward Growth 반영

$$
Growth\_Score = 0.5 \times Historical\_Growth + 0.5 \times Forward\_Growth
$$

```python
def calculate_growth_score(stock):
    # Historical Growth (실적 기반)
    rev_growth = stock.revenue_growth_yoy
    eps_growth = stock.eps_growth_yoy
    op_growth = stock.operating_profit_growth_yoy

    hist_score = (0.35 * percentile_rank(rev_growth) +
                  0.40 * percentile_rank(eps_growth) +
                  0.25 * percentile_rank(op_growth))

    # Forward Growth (컨센서스 기반)
    fwd_eps_growth = stock.consensus_eps_growth_next_year
    fwd_score = percentile_rank(fwd_eps_growth)

    return 0.5 * hist_score + 0.5 * fwd_score
```

---

### Factor 5: Size (규모 팩터) - 10%

적정 규모와 유동성을 확보한 종목을 선별합니다.

| 지표 | 계산식 | 비중 | 설명 |
|------|--------|------|------|
| **시가총액** | 주가 × 발행주식수 | 60% | 대형주 선호 |
| **거래대금** | 일평균 거래량 × 주가 | 40% | 유동성 확보 |

```python
def calculate_size_score(stock):
    # 대형주일수록 높은 점수 (기관 투자 가능성)
    cap_rank = percentile_rank(stock.market_cap, ascending=False)

    # 거래대금 높을수록 높은 점수
    volume_rank = percentile_rank(stock.daily_trading_value, ascending=False)

    return 0.60 * cap_rank + 0.40 * volume_rank
```

---

## 3단계: 종합 점수 산출

### Composite Score 계산

$$
Composite\_Score = \sum_{i=1}^{5} w_i \times Factor\_Score_i
$$

```yaml
factor_weights:
  value: 0.25
  quality: 0.25
  momentum: 0.20
  growth: 0.20
  size: 0.10
```

```python
def calculate_composite_score(stock):
    value_score = calculate_value_score(stock)
    quality_score = calculate_quality_score(stock)
    momentum_score = calculate_momentum_score(stock)
    growth_score = calculate_growth_score(stock)
    size_score = calculate_size_score(stock)

    composite = (0.25 * value_score +
                 0.25 * quality_score +
                 0.20 * momentum_score +
                 0.20 * growth_score +
                 0.10 * size_score)

    return composite
```

### 섹터 중립화 (Sector Neutralization)

섹터 편향을 방지하기 위해 섹터 내 상대 순위로 조정:

```python
def sector_neutralize(stocks):
    for sector in sectors:
        sector_stocks = stocks.filter(sector=sector)
        for stock in sector_stocks:
            stock.neutralized_score = percentile_rank(
                stock.composite_score,
                within=sector_stocks
            )
    return stocks
```

---

## 4단계: 최종 후보군 선정

### 선정 기준

```yaml
final_selection:
  target_count: 100
  min_composite_score: 60  # 최소 60점 이상

  sector_constraints:
    max_per_sector: 20  # 섹터당 최대 20종목
    min_per_sector: 2   # 섹터당 최소 2종목 (다각화)

  liquidity_recheck:
    min_daily_value: 500000000  # 5억 이상 재확인
```

### 출력 형식

#### screened_stocks.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "total_universe": 2500,
  "after_hard_filter": 750,
  "final_screened": 100,
  "stocks": [
    {
      "code": "005930",
      "name": "삼성전자",
      "sector": "IT",
      "market_cap": 350000000000000,
      "composite_score": 85.2,
      "factor_scores": {
        "value": 72.5,
        "quality": 88.3,
        "momentum": 79.1,
        "growth": 65.8,
        "size": 99.5
      },
      "key_metrics": {
        "per": 12.5,
        "pbr": 1.2,
        "roe": 15.3,
        "debt_ratio": 35.2,
        "eps_growth": 25.5
      }
    }
  ]
}
```

#### screening_report.json

```json
{
  "summary": {
    "execution_time": "2025-01-31T12:00:00Z",
    "universe_coverage": "KOSPI + KOSDAQ150"
  },
  "filter_results": {
    "step1_hard_filter": {
      "input": 2500,
      "output": 750,
      "excluded_reasons": {
        "market_cap_too_small": 650,
        "trading_value_too_low": 450,
        "management_issue": 50,
        "spac": 100
      }
    },
    "step2_factor_screening": {
      "input": 750,
      "output": 100,
      "score_distribution": {
        "90+": 5,
        "80-90": 25,
        "70-80": 35,
        "60-70": 35
      }
    }
  },
  "sector_distribution": {
    "IT": 25,
    "금융": 15,
    "헬스케어": 12,
    "산업재": 18,
    "소비재": 15,
    "소재": 10,
    "유틸리티": 5
  }
}
```

---

## 데이터 소스 및 API

### KRX (한국거래소)

```yaml
krx_data:
  endpoint: "http://data.krx.co.kr"
  data_types:
    - stock_list
    - market_cap
    - trading_volume
    - sector_classification
```

### DART (전자공시)

```yaml
dart_data:
  endpoint: "https://opendart.fss.or.kr"
  api_key: "${DART_API_KEY}"
  data_types:
    - financial_statements
    - eps
    - bps
```

### FnGuide

```yaml
fnguide_data:
  method: "web_scraping"
  url: "https://comp.fnguide.com"
  data_types:
    - consensus_eps
    - per
    - pbr
    - roe
```

---

## 다음 단계

스크리닝 결과(`screened_stocks.json`)를 `02_financial_agent`로 전달하여 상세 재무 분석을 수행합니다.
