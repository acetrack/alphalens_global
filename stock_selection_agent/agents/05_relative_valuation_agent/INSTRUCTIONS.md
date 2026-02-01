# Agent 05: Relative Valuation Agent (상대가치 평가 에이전트)

## 역할

Peer 그룹 비교를 통한 상대가치 평가(Relative Valuation)를 수행합니다. 멀티플(PER, PBR, EV/EBITDA 등)을 활용하여 시장 대비 저평가/고평가 여부를 판단하고, Historical Valuation Band를 분석합니다.

## 입력

- `financial_analysis/`: 재무 분석 결과
- `industry_analysis/`: 산업 분석 결과
- Peer 그룹 데이터 (국내/해외)
- Historical 멀티플 데이터

## 출력

- `relative_valuations/`: 종목별 상대가치 평가
- `peer_comparison.json`: Peer 비교 분석

---

## ⚠️ 필수: 현재 날짜 확인

**분석 시작 전 반드시 현재 날짜를 확인하세요.**

```yaml
date_validation:
  required: true
  relative_valuation_context:
    # 현재가 2026년 2월이라면:
    trailing_multiples: "2025년 실적 기준"     # Trailing PER/PBR
    forward_multiples: "2026년 추정 기준"      # Forward PER/PBR
    historical_band: [2021, 2022, 2023, 2024, 2025]  # 5년 밸류밴드

  search_keywords:
    - "{company} PER PBR {current_year}"
    - "{company} 밸류에이션 {current_year}"
    - "{peer} 멀티플 비교 {current_year}"
    - "{company} 12개월 선행 PER"
```

---

## 상대가치 평가 기본 개념

### 멀티플 기반 밸류에이션

$$
Fair\,Value = Metric \times Fair\,Multiple
$$

```
┌─────────────────────────────────────────────────────────────┐
│               Relative Valuation Framework                   │
└─────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  Target Stock   │
                    │  적정 멀티플 산정 │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Peer Multiples │ │  Historical     │ │  Fundamental    │
│  동종업계 평균   │ │  Band           │ │  Justified      │
│                 │ │  과거 밸류밴드   │ │  펀더멘털 기반   │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Fair Multiple  │
                    │  × EPS/BPS     │
                    │  = Target Price │
                    └─────────────────┘
```

---

## 1단계: 주요 멀티플 분석

### PER (Price to Earnings Ratio)

$$
PER = \frac{Price}{EPS} = \frac{Market\,Cap}{Net\,Income}
$$

| PER 유형 | 계산 | 용도 |
|----------|------|------|
| **Trailing PER** | 현재가 / 과거 12M EPS | 실현 이익 기준 |
| **Forward PER** | 현재가 / 향후 12M EPS | 예상 이익 기준 |
| **Shiller PER** | 현재가 / 10년 평균 실질 EPS | 사이클 조정 |

#### PER 기반 적정가치

```python
def per_valuation(stock, fair_per):
    # Forward EPS 기준
    forward_eps = stock.consensus_eps_next_year
    fair_value = forward_eps * fair_per

    return {
        "fair_value": fair_value,
        "current_price": stock.price,
        "current_per": stock.forward_per,
        "applied_per": fair_per,
        "upside": (fair_value / stock.price - 1) * 100
    }
```

#### PER 적정 수준 판단

```yaml
per_fair_multiple_methods:
  1_peer_average:
    method: "동종업계 평균 PER"
    adjustment:
      - "+10%": "ROE 상위 20%"
      - "-10%": "성장률 하위 20%"

  2_historical_average:
    method: "과거 5년 평균 PER"
    consideration: "이익 사이클 정점/저점 제외"

  3_peg_implied:
    method: "PEG = 1 기준 역산"
    formula: "Fair PER = EPS Growth Rate"

  4_gordon_growth_implied:
    method: "DDM 역산"
    formula: "Fair PER = Payout / (k - g)"
```

---

### PBR (Price to Book Ratio)

$$
PBR = \frac{Price}{BPS} = \frac{Market\,Cap}{Book\,Value}
$$

#### ROE-PBR 관계

$$
Fair\,PBR = \frac{ROE - g}{r - g}
$$

여기서:
- ROE = 자기자본이익률
- r = 요구수익률 (Cost of Equity)
- g = 지속가능성장률

```python
def justified_pbr(stock):
    roe = stock.roe
    cost_of_equity = stock.cost_of_equity
    growth_rate = stock.sustainable_growth_rate

    if cost_of_equity - growth_rate <= 0:
        return None  # 의미 없음

    justified_pbr = (roe - growth_rate) / (cost_of_equity - growth_rate)

    return justified_pbr
```

#### PBR 분석 매트릭스

```
┌─────────────────────────────────────────────────────────────┐
│                   ROE-PBR Matrix                             │
└─────────────────────────────────────────────────────────────┘

              PBR
              높음
               │
               │   고ROE-고PBR    │   저ROE-고PBR
               │   (프리미엄 정당) │   (과대평가)
               │                  │
ROE  낮음 ─────┼──────────────────┼───────────── 높음
               │                  │
               │   저ROE-저PBR    │   고ROE-저PBR
               │   (가치 함정)     │   (저평가 기회!)
               │
              낮음
```

---

### EV/EBITDA

$$
EV/EBITDA = \frac{Enterprise\,Value}{EBITDA}
$$

$$
EV = Market\,Cap + Net\,Debt - Non\,Operating\,Assets
$$

| 특징 | 설명 |
|------|------|
| **장점** | 자본구조 중립, 비현금비용 제거 |
| **적합** | M&A 밸류에이션, 자본집약 산업 |
| **한계** | CAPEX 차이 미반영 |

#### 산업별 EV/EBITDA 기준

```yaml
ev_ebitda_benchmarks:
  반도체: 6-10x
  소프트웨어: 12-18x
  통신: 5-7x
  유틸리티: 6-8x
  소비재: 8-12x
  제약: 10-15x
  은행: N/A (예금 기반)
  철강: 4-6x
  자동차: 3-5x
```

```python
def ev_ebitda_valuation(stock, fair_multiple):
    ebitda = stock.ebitda
    fair_ev = ebitda * fair_multiple

    # 주주가치로 변환
    equity_value = fair_ev - stock.net_debt
    fair_price = equity_value / stock.shares_outstanding

    return {
        "fair_ev": fair_ev,
        "fair_equity": equity_value,
        "fair_price": fair_price,
        "current_multiple": stock.ev_ebitda,
        "applied_multiple": fair_multiple
    }
```

---

### PSR (Price to Sales Ratio)

$$
PSR = \frac{Market\,Cap}{Revenue}
$$

| 적합 케이스 | 부적합 케이스 |
|-------------|---------------|
| 적자 기업 | 고수익 기업 |
| 성장주 | 성숙기 기업 |
| 매출 성장 중요 | 마진이 핵심 |

```python
def psr_valuation(stock, peers):
    # 마진 조정 PSR
    peer_avg_psr = np.mean([p.psr for p in peers])
    peer_avg_margin = np.mean([p.net_margin for p in peers])

    margin_adjustment = stock.net_margin / peer_avg_margin
    adjusted_fair_psr = peer_avg_psr * margin_adjustment

    fair_value = stock.revenue_per_share * adjusted_fair_psr

    return {
        "fair_value": fair_value,
        "peer_avg_psr": peer_avg_psr,
        "adjusted_psr": adjusted_fair_psr,
        "margin_adjustment": margin_adjustment
    }
```

---

## 2단계: Peer 그룹 비교

### Peer 선정 기준

```yaml
peer_selection:
  primary_criteria:
    - same_gics_sub_industry: true
    - revenue_range: "0.5x ~ 2.0x"
    - similar_business_model: true

  secondary_criteria:
    - similar_growth_profile
    - similar_margin_structure
    - geographic_exposure

  peer_count:
    domestic: 5-8
    global: 3-5
    total_max: 10
```

### Peer 비교 테이블

```python
def peer_comparison_table(stock, peers):
    metrics = ["market_cap", "revenue", "operating_margin", "roe",
               "per", "pbr", "ev_ebitda", "eps_growth"]

    comparison = {
        "stock": {
            "code": stock.code,
            "name": stock.name,
            "metrics": {m: getattr(stock, m) for m in metrics}
        },
        "peers": [],
        "statistics": {}
    }

    peer_values = {m: [] for m in metrics}

    for peer in peers:
        peer_data = {
            "code": peer.code,
            "name": peer.name,
            "metrics": {m: getattr(peer, m) for m in metrics}
        }
        comparison["peers"].append(peer_data)

        for m in metrics:
            peer_values[m].append(getattr(peer, m))

    # 통계 산출
    for m in metrics:
        comparison["statistics"][m] = {
            "peer_avg": np.mean(peer_values[m]),
            "peer_median": np.median(peer_values[m]),
            "stock_percentile": percentile_rank(
                getattr(stock, m), peer_values[m]
            ),
            "vs_avg": (getattr(stock, m) / np.mean(peer_values[m]) - 1) * 100
        }

    return comparison
```

### 프리미엄/디스카운트 분석

| 프리미엄 요인 | 디스카운트 요인 |
|---------------|-----------------|
| 높은 ROE | 낮은 ROE |
| 강한 성장성 | 성장 둔화 |
| 시장 지배력 | 약한 경쟁력 |
| 우수한 경영진 | 거버넌스 이슈 |
| 배당 안정성 | 변동성 높음 |

```python
def calculate_premium_discount(stock, peer_avg):
    adjustments = []

    # ROE 프리미엄
    if stock.roe > peer_avg.roe * 1.2:
        adjustments.append({"factor": "high_roe", "adjustment": 0.10})
    elif stock.roe < peer_avg.roe * 0.8:
        adjustments.append({"factor": "low_roe", "adjustment": -0.10})

    # 성장 프리미엄
    if stock.eps_growth > peer_avg.eps_growth * 1.3:
        adjustments.append({"factor": "high_growth", "adjustment": 0.15})
    elif stock.eps_growth < peer_avg.eps_growth * 0.7:
        adjustments.append({"factor": "low_growth", "adjustment": -0.10})

    # 시장 지위 프리미엄
    if stock.market_share > 30:
        adjustments.append({"factor": "market_leader", "adjustment": 0.10})

    total_adjustment = sum([a["adjustment"] for a in adjustments])

    return {
        "adjustments": adjustments,
        "total_adjustment": total_adjustment,
        "adjusted_multiple": peer_avg.per * (1 + total_adjustment)
    }
```

---

## 3단계: Historical Valuation Band

### 밸류에이션 밴드 분석

```
┌─────────────────────────────────────────────────────────────┐
│              Historical PER Band (5Y)                        │
└─────────────────────────────────────────────────────────────┘

PER
 │
25├─────────────────────────────────────────── 90th percentile
 │                      ╱╲
20├───────────────────╱──╲─────────────────── 75th percentile
 │            ╱╲    ╱    ╲    ╱╲
15├─────────╱──╲──╱──────╲──╱──╲───────────── Median
 │        ╱    ╲╱        ╲╱    ╲
10├──────╱──────────────────────╲───────────── 25th percentile
 │     ╱                        ╲
 5├────────────────────────────────────────── 10th percentile
 │
 └────────────────────────────────────────────► Time
      2020    2021    2022    2023    2024
```

### 밴드 분석 코드

```python
def historical_band_analysis(stock, years=5):
    # 과거 멀티플 데이터
    historical_per = stock.get_historical_per(years)
    historical_pbr = stock.get_historical_pbr(years)
    historical_ev_ebitda = stock.get_historical_ev_ebitda(years)

    def calculate_band(data):
        return {
            "min": np.min(data),
            "p10": np.percentile(data, 10),
            "p25": np.percentile(data, 25),
            "median": np.median(data),
            "mean": np.mean(data),
            "p75": np.percentile(data, 75),
            "p90": np.percentile(data, 90),
            "max": np.max(data),
            "current_percentile": percentile_rank(data[-1], data)
        }

    return {
        "per_band": calculate_band(historical_per),
        "pbr_band": calculate_band(historical_pbr),
        "ev_ebitda_band": calculate_band(historical_ev_ebitda),
        "assessment": assess_current_valuation(stock, historical_per)
    }

def assess_current_valuation(stock, historical_data):
    current_pctl = percentile_rank(stock.per, historical_data)

    if current_pctl < 20:
        return {"status": "undervalued", "confidence": "high", "percentile": current_pctl}
    elif current_pctl < 40:
        return {"status": "undervalued", "confidence": "moderate", "percentile": current_pctl}
    elif current_pctl < 60:
        return {"status": "fair_value", "confidence": "moderate", "percentile": current_pctl}
    elif current_pctl < 80:
        return {"status": "overvalued", "confidence": "moderate", "percentile": current_pctl}
    else:
        return {"status": "overvalued", "confidence": "high", "percentile": current_pctl}
```

---

## 4단계: 글로벌 Peer 비교

### 글로벌 동종업체 매핑

```yaml
global_peer_mapping:
  삼성전자:
    domestic: ["SK하이닉스"]
    global: ["TSMC", "Intel", "Micron", "SK Hynix ADR"]

  현대차:
    domestic: ["기아"]
    global: ["Toyota", "Volkswagen", "GM", "Ford"]

  삼성바이오로직스:
    domestic: ["셀트리온"]
    global: ["Lonza", "WuXi Biologics", "Catalent"]

  네이버:
    domestic: ["카카오"]
    global: ["Google", "Meta", "Baidu", "Yahoo Japan"]
```

### 글로벌 밸류에이션 갭 분석

```python
def global_valuation_gap(stock, global_peers):
    # 국내 멀티플 vs 글로벌 멀티플
    global_avg_per = np.mean([p.per for p in global_peers])
    global_avg_pbr = np.mean([p.pbr for p in global_peers])
    global_avg_ev_ebitda = np.mean([p.ev_ebitda for p in global_peers])

    gap_analysis = {
        "per": {
            "domestic": stock.per,
            "global_avg": global_avg_per,
            "discount": (stock.per / global_avg_per - 1) * 100
        },
        "pbr": {
            "domestic": stock.pbr,
            "global_avg": global_avg_pbr,
            "discount": (stock.pbr / global_avg_pbr - 1) * 100
        },
        "ev_ebitda": {
            "domestic": stock.ev_ebitda,
            "global_avg": global_avg_ev_ebitda,
            "discount": (stock.ev_ebitda / global_avg_ev_ebitda - 1) * 100
        }
    }

    # 코리아 디스카운트 계산
    avg_discount = np.mean([
        gap_analysis["per"]["discount"],
        gap_analysis["pbr"]["discount"],
        gap_analysis["ev_ebitda"]["discount"]
    ])

    gap_analysis["korea_discount"] = {
        "average": avg_discount,
        "assessment": "significant" if avg_discount < -20 else "moderate" if avg_discount < -10 else "minimal"
    }

    return gap_analysis
```

---

## 5단계: 종합 적정가치 산출

### 멀티플별 가중 평균

```python
def weighted_relative_valuation(stock, peers, global_peers):
    # 1. PER 기반 적정가치
    peer_per = calculate_fair_per(stock, peers)
    per_value = stock.forward_eps * peer_per

    # 2. PBR 기반 적정가치
    justified_pbr = calculate_justified_pbr(stock)
    pbr_value = stock.bps * justified_pbr

    # 3. EV/EBITDA 기반 적정가치
    fair_ev_ebitda = calculate_fair_ev_ebitda(stock, peers)
    ev_ebitda_equity = stock.ebitda * fair_ev_ebitda - stock.net_debt
    ev_ebitda_value = ev_ebitda_equity / stock.shares_outstanding

    # 4. PSR 기반 (선택적)
    if stock.net_margin > 0:
        psr_weight = 0.10
    else:
        psr_weight = 0.20  # 적자 기업은 PSR 비중 높임

    # 가중 평균
    weights = {
        "per": 0.40,
        "pbr": 0.20,
        "ev_ebitda": 0.30,
        "psr": 0.10
    }

    weighted_value = (
        weights["per"] * per_value +
        weights["pbr"] * pbr_value +
        weights["ev_ebitda"] * ev_ebitda_value +
        weights["psr"] * psr_value
    )

    return {
        "weighted_fair_value": weighted_value,
        "method_values": {
            "per_based": per_value,
            "pbr_based": pbr_value,
            "ev_ebitda_based": ev_ebitda_value,
            "psr_based": psr_value
        },
        "weights": weights,
        "upside": (weighted_value / stock.price - 1) * 100
    }
```

---

## 출력 형식

### relative_valuations/{stock_code}.json

```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "valuation_date": "2025-01-31",
  "current_price": 65000,
  "relative_valuation": {
    "weighted_fair_value": 78000,
    "upside_pct": 20.0,
    "method_breakdown": {
      "per_based": {
        "fair_value": 75000,
        "applied_per": 12.5,
        "peer_avg_per": 11.8,
        "premium_applied": 6
      },
      "pbr_based": {
        "fair_value": 72000,
        "applied_pbr": 1.35,
        "justified_pbr": 1.42,
        "current_pbr": 1.15
      },
      "ev_ebitda_based": {
        "fair_value": 82000,
        "applied_multiple": 7.5,
        "peer_avg": 7.2
      }
    }
  },
  "peer_comparison": {
    "domestic_peers": ["SK하이닉스"],
    "global_peers": ["TSMC", "Intel", "Micron"],
    "vs_peer_avg": {
      "per": -8.5,
      "pbr": -15.2,
      "ev_ebitda": -10.1
    }
  },
  "historical_band": {
    "per": {
      "current": 10.8,
      "5y_median": 12.5,
      "percentile": 25,
      "status": "below_average"
    }
  },
  "korea_discount": {
    "vs_global_peers": -22.5,
    "assessment": "significant"
  }
}
```

### peer_comparison.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "comparisons": [
    {
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "sector": "반도체",
      "peers": [
        {
          "code": "000660",
          "name": "SK하이닉스",
          "type": "domestic"
        },
        {
          "ticker": "TSM",
          "name": "TSMC",
          "type": "global"
        }
      ],
      "relative_metrics": {
        "per_vs_peers": -12.5,
        "pbr_vs_peers": -18.3,
        "ev_ebitda_vs_peers": -10.2,
        "roe_vs_peers": 5.2,
        "growth_vs_peers": -3.1
      },
      "valuation_status": "undervalued_vs_peers"
    }
  ]
}
```

---

## 다음 단계

상대가치 평가 결과를 DCF 밸류에이션 결과와 통합하여 최종 목표주가를 산정합니다. `00_master_orchestrator`에서 두 방법론의 가중평균으로 최종 적정가치를 도출합니다.
