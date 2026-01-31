# Agent 03: Industry Agent (산업 분석 에이전트)

## 역할

개별 기업을 넘어 산업 구조, 경쟁 환경, 산업 성장 단계를 분석하여 기업의 경쟁적 위치(Competitive Position)를 평가합니다. Porter's 5 Forces, Industry Lifecycle 등 전략 프레임워크를 활용합니다.

## 입력

- `screened_stocks.json`: 스크리닝 결과
- `financial_analysis/`: 재무 분석 결과
- 산업 보고서, 증권사 리서치

## 출력

- `industry_analysis/`: 산업별 분석 결과
- `competitive_position.json`: 종목별 경쟁 포지션 평가

---

## 1단계: 산업 분류 및 구조 파악

### GICS 섹터 분류

```yaml
gics_sectors:
  - code: "10"
    name: "에너지"
    sub_industries: ["석유/가스", "정유", "에너지장비"]

  - code: "15"
    name: "소재"
    sub_industries: ["화학", "철강", "비철금속", "건축자재"]

  - code: "20"
    name: "산업재"
    sub_industries: ["항공우주", "건설", "기계", "운송"]

  - code: "25"
    name: "경기소비재"
    sub_industries: ["자동차", "내구재", "호텔/레저", "소매"]

  - code: "30"
    name: "필수소비재"
    sub_industries: ["음식료", "가정용품", "담배"]

  - code: "35"
    name: "헬스케어"
    sub_industries: ["제약", "바이오", "의료기기", "헬스케어서비스"]

  - code: "40"
    name: "금융"
    sub_industries: ["은행", "보험", "증권", "다각화금융"]

  - code: "45"
    name: "IT"
    sub_industries: ["반도체", "소프트웨어", "하드웨어", "통신장비"]

  - code: "50"
    name: "커뮤니케이션서비스"
    sub_industries: ["통신", "미디어", "엔터테인먼트"]

  - code: "55"
    name: "유틸리티"
    sub_industries: ["전력", "가스", "수도"]

  - code: "60"
    name: "부동산"
    sub_industries: ["리츠", "부동산개발", "부동산관리"]
```

---

## 2단계: Porter's Five Forces 분석

### 분석 프레임워크

```
┌─────────────────────────────────────────────────────────────┐
│                   Porter's Five Forces                       │
└─────────────────────────────────────────────────────────────┘

                    ┌───────────────────┐
                    │  신규 진입 위협   │
                    │  (Threat of New   │
                    │    Entrants)      │
                    └─────────┬─────────┘
                              │
                              ▼
┌──────────────┐    ┌───────────────────┐    ┌──────────────┐
│  공급자      │    │                   │    │  구매자      │
│  교섭력      │◄───│   기존 경쟁 강도   │───►│  교섭력      │
│ (Supplier   │    │ (Industry Rivalry)│    │ (Buyer      │
│  Power)     │    │                   │    │  Power)     │
└──────────────┘    └─────────┬─────────┘    └──────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  대체재 위협      │
                    │ (Threat of       │
                    │  Substitutes)    │
                    └───────────────────┘
```

### Force 1: 기존 경쟁 강도 (Industry Rivalry)

| 평가 요소 | 높음 (불리) | 낮음 (유리) |
|-----------|-------------|-------------|
| 경쟁자 수 | 다수 | 소수 (과점) |
| 시장 성장률 | 정체/역성장 | 고성장 |
| 고정비 비중 | 높음 | 낮음 |
| 제품 차별화 | 낮음 (범용) | 높음 (특화) |
| 전환비용 | 낮음 | 높음 |
| 퇴출장벽 | 높음 | 낮음 |

```python
def analyze_rivalry(industry):
    score = 0

    # HHI (Herfindahl-Hirschman Index) 기반 집중도
    hhi = calculate_hhi(industry.market_shares)
    if hhi > 2500:
        score += 20  # 고집중 (과점) - 경쟁 약함
    elif hhi > 1500:
        score += 10  # 중집중
    else:
        score -= 10  # 저집중 - 경쟁 심함

    # 시장 성장률
    if industry.growth_rate > 10:
        score += 15
    elif industry.growth_rate < 3:
        score -= 15

    return {
        "rivalry_score": score,
        "hhi": hhi,
        "interpretation": "favorable" if score > 0 else "unfavorable"
    }
```

### Force 2: 신규 진입 위협

| 진입장벽 | 평가 지표 |
|----------|-----------|
| **규모의 경제** | MES (Minimum Efficient Scale) |
| **자본 요구** | 초기 투자 규모 |
| **기술/특허** | R&D 집약도, 특허 수 |
| **브랜드 충성도** | 시장점유율 안정성 |
| **규제** | 인허가 요건 |
| **유통채널** | 접근 용이성 |

```yaml
entry_barriers:
  high_barrier_industries:
    - "반도체": "대규모 Capex, 기술력"
    - "제약": "임상 규제, R&D"
    - "통신": "주파수 할당, 인프라"
    - "은행": "금융 인허가"

  low_barrier_industries:
    - "소매": "진입 용이"
    - "소프트웨어": "낮은 초기 자본"
    - "식음료": "상대적 낮은 장벽"
```

### Force 3: 공급자 교섭력

| 평가 요소 | 높은 교섭력 | 낮은 교섭력 |
|-----------|-------------|-------------|
| 공급자 집중도 | 소수 독점 | 다수 분산 |
| 전환비용 | 높음 | 낮음 |
| 대체 공급원 | 없음 | 존재 |
| 전방통합 위협 | 높음 | 낮음 |

### Force 4: 구매자 교섭력

| 평가 요소 | 높은 교섭력 | 낮은 교섭력 |
|-----------|-------------|-------------|
| 구매자 집중도 | 소수 대형 | 다수 소형 |
| 구매 비중 | 높음 | 낮음 |
| 전환비용 | 낮음 | 높음 |
| 후방통합 위협 | 높음 | 낮음 |
| 가격 민감도 | 높음 | 낮음 |

### Force 5: 대체재 위협

| 평가 요소 | 높은 위협 | 낮은 위협 |
|-----------|-----------|-----------|
| 대체재 성능 | 우수 | 열등 |
| 전환비용 | 낮음 | 높음 |
| 대체재 가격 | 낮음 | 높음 |

### Five Forces 종합 점수

```python
def five_forces_score(industry):
    rivalry = analyze_rivalry(industry)
    new_entrants = analyze_entry_barriers(industry)
    supplier_power = analyze_supplier_power(industry)
    buyer_power = analyze_buyer_power(industry)
    substitutes = analyze_substitutes(industry)

    # 각 Force 점수 (0-100, 높을수록 산업 매력도 높음)
    total_score = (
        0.30 * rivalry +
        0.20 * new_entrants +
        0.15 * supplier_power +
        0.20 * buyer_power +
        0.15 * substitutes
    )

    return {
        "total_score": total_score,
        "forces": {
            "rivalry": rivalry,
            "new_entrants": new_entrants,
            "supplier_power": supplier_power,
            "buyer_power": buyer_power,
            "substitutes": substitutes
        },
        "attractiveness": "high" if total_score > 70 else "medium" if total_score > 40 else "low"
    }
```

---

## 3단계: Industry Lifecycle 분석

### 산업 생명주기 단계

```
┌─────────────────────────────────────────────────────────────┐
│                   Industry Lifecycle                         │
└─────────────────────────────────────────────────────────────┘

           매출/이익
              │
              │                    ┌─────────┐
              │                   /│ 성숙기  │\
              │            ┌─────/ │ Mature │ \─────┐
              │           /│성장기 └─────────┘ 쇠퇴기│\
              │          / │Growth │         │Decline│ \
              │    ┌────/  └───────┘         └───────┘  \────┐
              │   /│도입기│                                   │
              │  / │Intro │                                   │
              │ /  └──────┘                                   │
              └────────────────────────────────────────────────► 시간
```

| 단계 | 특징 | 투자 전략 |
|------|------|-----------|
| **도입기** | 높은 성장, 적자, 낮은 경쟁 | 성장주 투자 (High Risk/Return) |
| **성장기** | 고성장, 흑자 전환, 경쟁 증가 | 선도 기업 투자 |
| **성숙기** | 안정 성장, 높은 수익성, 과점 | 배당주, 우량주 투자 |
| **쇠퇴기** | 역성장, 구조조정, 퇴출 | 회피 또는 턴어라운드 |

### 생명주기 판단 기준

```yaml
lifecycle_indicators:
  introduction:
    revenue_growth: "> 30%"
    profitability: "적자 또는 저마진"
    market_penetration: "< 10%"
    competition: "1-2개 선도업체"

  growth:
    revenue_growth: "15-30%"
    profitability: "흑자 전환, 마진 개선"
    market_penetration: "10-40%"
    competition: "신규 진입 활발"

  maturity:
    revenue_growth: "0-10%"
    profitability: "안정적 고마진"
    market_penetration: "> 60%"
    competition: "과점 구조"

  decline:
    revenue_growth: "< 0%"
    profitability: "마진 하락"
    market_penetration: "축소"
    competition: "퇴출/통합"
```

```python
def determine_lifecycle_stage(industry):
    growth = industry.revenue_growth_3y_avg
    margin = industry.avg_operating_margin
    penetration = industry.market_penetration

    if growth > 30 and margin < 5:
        return "introduction"
    elif growth > 15 and margin > 5:
        return "growth"
    elif 0 < growth < 15 and margin > 10:
        return "maturity"
    else:
        return "decline"
```

---

## 4단계: 경쟁 포지션 분석

### 시장점유율 분석

$$
Market\,Share = \frac{Company\,Revenue}{Industry\,Total\,Revenue} \times 100
$$

### CR(n) - 상위 n개사 집중률

$$
CR_n = \sum_{i=1}^{n} S_i
$$

### HHI (Herfindahl-Hirschman Index)

$$
HHI = \sum_{i=1}^{N} S_i^2 \times 10000
$$

```yaml
hhi_interpretation:
  competitive: "< 1500"
  moderately_concentrated: "1500 - 2500"
  highly_concentrated: "> 2500"
```

### 경쟁 포지션 매트릭스

```
┌─────────────────────────────────────────────────────────────┐
│              Competitive Position Matrix                     │
└─────────────────────────────────────────────────────────────┘

           상대적 시장점유율
           높음            낮음
         ┌─────────────┬─────────────┐
    높   │             │             │
    음   │   Star      │  Question   │
         │   (스타)     │  Mark       │
  시     │             │  (물음표)    │
  장     ├─────────────┼─────────────┤
  성     │             │             │
  장     │  Cash Cow   │    Dog      │
  률     │  (현금젖소)  │   (개)      │
         │             │             │
    낮   └─────────────┴─────────────┘
    음
```

### 경쟁 우위 평가

| 경쟁 우위 유형 | 평가 지표 | 지속 가능성 |
|----------------|-----------|-------------|
| **원가 우위** | 영업이익률 > 업계 평균 | 규모, 기술 |
| **차별화 우위** | 프리미엄 가격, 높은 브랜드 가치 | 브랜드, R&D |
| **집중화 전략** | 니치 시장 지배 | 전문성 |

```python
def analyze_competitive_advantage(stock, industry_avg):
    advantages = []

    # 원가 우위
    if stock.operating_margin > industry_avg.operating_margin * 1.2:
        advantages.append({
            "type": "cost_leadership",
            "evidence": f"영업이익률 {stock.operating_margin}% vs 업계 {industry_avg.operating_margin}%",
            "moat_strength": "strong"
        })

    # 차별화 우위
    if stock.gross_margin > industry_avg.gross_margin * 1.3:
        advantages.append({
            "type": "differentiation",
            "evidence": f"매출총이익률 {stock.gross_margin}% (프리미엄 가격력)",
            "moat_strength": "moderate"
        })

    # 시장 지배력
    if stock.market_share > 30:
        advantages.append({
            "type": "market_dominance",
            "evidence": f"시장점유율 {stock.market_share}%",
            "moat_strength": "strong"
        })

    return advantages
```

---

## 5단계: 경제적 해자 (Economic Moat) 평가

### 해자 유형

| 해자 유형 | 설명 | 대표 사례 |
|-----------|------|-----------|
| **네트워크 효과** | 사용자 증가 → 가치 증가 | 카카오, 네이버 |
| **전환비용** | 고객 이탈 비용 높음 | 삼성SDS, ERP |
| **원가 우위** | 규모/기술 기반 저비용 | 삼성전자, 현대차 |
| **무형자산** | 브랜드, 특허, 라이선스 | 아모레퍼시픽, 셀트리온 |
| **효율적 규모** | 신규 진입 비경제적 | KT, SK텔레콤 |

### 해자 강도 평가

```python
def evaluate_moat(stock):
    moat_score = 0
    moat_sources = []

    # 네트워크 효과
    if stock.user_base_growth > 20 and stock.engagement_rate > 50:
        moat_score += 25
        moat_sources.append("network_effect")

    # 전환비용
    if stock.customer_retention > 90:
        moat_score += 20
        moat_sources.append("switching_cost")

    # 원가 우위
    if stock.operating_margin > industry_avg * 1.5:
        moat_score += 20
        moat_sources.append("cost_advantage")

    # 무형자산
    if stock.rd_intensity > 10 or stock.brand_value > 0:
        moat_score += 20
        moat_sources.append("intangible_assets")

    # 효율적 규모
    if stock.market_share > 40 and industry_growth < 5:
        moat_score += 15
        moat_sources.append("efficient_scale")

    return {
        "moat_score": moat_score,
        "moat_width": "wide" if moat_score > 60 else "narrow" if moat_score > 30 else "none",
        "sources": moat_sources
    }
```

---

## 6단계: Peer 그룹 구성

### Peer 선정 기준

```yaml
peer_selection_criteria:
  primary:
    - same_gics_sub_industry
    - similar_revenue_scale  # ±50%
    - similar_business_model

  secondary:
    - global_peers  # 해외 동종 기업
    - value_chain_peers  # 밸류체인 연관
```

### Peer 비교 분석

```python
def peer_comparison(stock, peers):
    comparison = {
        "stock": stock.code,
        "peers": [p.code for p in peers],
        "metrics": {}
    }

    for metric in ["revenue", "operating_margin", "roe", "per", "pbr"]:
        stock_value = getattr(stock, metric)
        peer_avg = np.mean([getattr(p, metric) for p in peers])
        peer_median = np.median([getattr(p, metric) for p in peers])

        comparison["metrics"][metric] = {
            "stock": stock_value,
            "peer_avg": peer_avg,
            "peer_median": peer_median,
            "percentile": percentile_rank(stock_value, [getattr(p, metric) for p in peers]),
            "vs_avg": (stock_value / peer_avg - 1) * 100
        }

    return comparison
```

---

## 출력 형식

### industry_analysis/{sector}.json

```json
{
  "sector": "반도체",
  "gics_code": "45301020",
  "analysis_date": "2025-01-31",
  "five_forces": {
    "total_score": 72,
    "attractiveness": "high",
    "forces": {
      "rivalry": 65,
      "new_entrants": 85,
      "supplier_power": 70,
      "buyer_power": 60,
      "substitutes": 80
    }
  },
  "lifecycle": {
    "stage": "maturity",
    "evidence": "성장률 8%, 영업이익률 20%, 과점 구조"
  },
  "market_structure": {
    "hhi": 2850,
    "cr4": 78.5,
    "top_players": [
      {"name": "삼성전자", "share": 45.2},
      {"name": "SK하이닉스", "share": 25.3}
    ]
  },
  "key_trends": [
    "AI 반도체 수요 급증",
    "HBM 시장 확대",
    "중국 반도체 규제"
  ]
}
```

### competitive_position.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "positions": [
    {
      "code": "005930",
      "name": "삼성전자",
      "sector": "반도체",
      "market_share": 45.2,
      "position": "leader",
      "moat": {
        "width": "wide",
        "score": 85,
        "sources": ["cost_advantage", "efficient_scale", "intangible_assets"]
      },
      "competitive_advantages": [
        "수직계열화 (팹리스→파운드리→메모리)",
        "HBM 기술 선도",
        "스케일 기반 원가 경쟁력"
      ],
      "competitive_risks": [
        "중국 반도체 추격",
        "TSMC 파운드리 격차"
      ],
      "industry_score": 78
    }
  ]
}
```

---

## 다음 단계

산업 분석 결과를 `04_dcf_valuation_agent`와 `05_relative_valuation_agent`로 전달하여 밸류에이션 시 산업 프리미엄/디스카운트를 반영합니다.
