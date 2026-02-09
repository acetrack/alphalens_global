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

## 1.5단계: 종목 유형 식별 및 구조적 할인 분석

### ⚠️ 핵심 원칙: 업종 평균 PER 직접 적용 금지

**업종 평균 PER을 개별 종목에 그대로 적용하면 안 됩니다.** 시장이 특정 종목에 낮은 밸류에이션을 부여하는 데는 반드시 이유가 있습니다.

```
⚠️ 잘못된 접근:
  업종 평균 PER 12배 × EPS 4,483원 = 목표가 53,796원
  → 현재가 9,950원 대비 +440% 상승여력? (비현실적)

✅ 올바른 접근:
  1. "왜 시장이 PER 2.2배에 거래시키는가?" 먼저 분석
  2. 종목 유형 식별 (지주회사? 사이클주? 적자기업?)
  3. 해당 유형에 맞는 밸류에이션 방법론 적용
  4. 구조적 할인/프리미엄 요인 반영
  5. 적정 밸류에이션 범위 산출
```

### 종목 유형별 밸류에이션 방법론

| 종목 유형 | 적합한 밸류에이션 | 부적합한 방법 | 식별 방법 |
|----------|------------------|--------------|----------|
| **지주회사** | NAV 할인법 (30-50% 할인) | 업종 평균 PER | 종목명에 '지주', '홀딩스' 포함 |
| **사이클 종목** | 정상화 이익 기준, Mid-cycle PER | 현재 EPS 기준 PER | 반도체, 철강, 화학, 해운 등 |
| **적자 기업** | PSR, EV/Sales | PER (음수) | 당기순이익 < 0 |
| **고성장주** | PEG, DCF | 단순 PER | EPS 성장률 > 30% |
| **금융주** | PBR, ROE 조정 PBR | EV/EBITDA | 은행, 보험, 증권 |
| **자산주/부동산** | NAV, 청산가치 | 수익 기반 PER | 자산 가치 > 시총 |
| **턴어라운드** | 정상화 이익 기준 | 현재 실적 기준 | 적자→흑자 전환 중 |

### 지주회사 밸류에이션

```python
def holding_company_valuation(stock):
    """
    지주회사는 NAV 할인법을 사용
    업종 평균 PER 적용은 부적절함
    """
    # 1. 자회사 가치 합산
    subsidiary_values = []
    for sub in stock.subsidiaries:
        ownership = sub.ownership_pct
        market_value = sub.market_cap * ownership
        subsidiary_values.append(market_value)

    gross_nav = sum(subsidiary_values) + stock.own_operating_assets

    # 2. 지주회사 할인 적용 (일반적으로 30-50%)
    base_discount = 0.40  # 기본 40% 할인

    # 할인율 조정 요인
    discount_adjustments = []

    if stock.governance_score > 80:
        base_discount -= 0.05  # 지배구조 우수
        discount_adjustments.append("지배구조 우수: -5%p")

    if stock.dividend_yield > 0.03:
        base_discount -= 0.05  # 고배당
        discount_adjustments.append("고배당 정책: -5%p")

    if stock.avg_daily_trading_value < 5_000_000_000:  # 50억 미만
        base_discount += 0.05  # 유동성 부족
        discount_adjustments.append("유동성 부족: +5%p")

    final_discount = max(0.20, min(0.60, base_discount))  # 20-60% 범위 제한

    fair_value = gross_nav * (1 - final_discount)
    fair_price = fair_value / stock.shares_outstanding

    return {
        "gross_nav": gross_nav,
        "holding_discount": final_discount,
        "discount_adjustments": discount_adjustments,
        "fair_value": fair_value,
        "fair_price": fair_price,
        "methodology": "NAV 할인법",
        "caveats": [
            "⚠️ 지주회사는 업종 평균 PER 적용 부적합",
            f"📊 적용 할인율: {final_discount*100:.0f}%"
        ]
    }

def is_holding_company(stock):
    """지주회사 여부 확인"""
    keywords = ["지주", "홀딩스", "Holdings", "홀딩스", "그룹"]
    return any(kw in stock.name for kw in keywords)
```

### NAV 할인법 상세 구현

지주회사에 대한 NAV(Net Asset Value) 할인법은 자회사 가치를 합산한 후 지주회사 할인율을 적용하는 방법입니다.

#### 데이터 소스

| 데이터 | 소스 | API/방법 | 비고 |
|--------|------|----------|------|
| **상장 자회사 시가총액** | KRX | pykrx 라이브러리 | `stock.get_market_cap_by_ticker()` |
| **자회사 지분율** | DART | 사업보고서 XBRL | 연결재무제표 주석 |
| **비상장 자회사 장부가** | DART | 사업보고서 XBRL | 종속기업투자 계정 |
| **공식 지주회사 현황** | 공정거래위원회 | Open API | 지주회사 지정 및 자회사 목록 |

#### DART API를 통한 자회사 정보 추출

```python
def get_subsidiaries_from_dart(corp_code: str, api_key: str) -> List[Dict]:
    """
    DART 사업보고서에서 종속기업 투자 내역 추출

    Returns:
        List[Dict]: 자회사 정보 리스트
        [
            {
                "name": "현대백화점",
                "stock_code": "069960",    # 상장사인 경우
                "is_listed": True,
                "ownership_pct": 0.424,     # 지분율 42.4%
                "book_value": 1234567890,   # 장부가 (비상장시 사용)
                "acquisition_cost": 987654321
            },
            ...
        ]
    """
    # 1. 사업보고서 목록 조회
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": "20240101",
        "pblntf_ty": "A",  # 사업보고서
        "page_count": 10
    }
    response = requests.get(url, params=params)
    reports = response.json()["list"]

    # 2. 가장 최신 사업보고서의 rcept_no 가져오기
    latest_report = reports[0]
    rcept_no = latest_report["rcept_no"]

    # 3. 사업보고서 XBRL 다운로드 및 파싱
    # (dart-fss 라이브러리 사용 권장)
    subsidiaries = parse_subsidiary_investments_xbrl(rcept_no)

    return subsidiaries

def parse_subsidiary_investments_xbrl(rcept_no: str) -> List[Dict]:
    """
    XBRL에서 종속기업투자 관련 항목 파싱

    파싱 대상 계정:
    - InvestmentsInSubsidiaries: 종속기업투자
    - InvestmentsInAssociates: 관계기업투자
    - EquityMethodInvestments: 지분법적용투자
    """
    # dart-fss 라이브러리 사용 예시
    import dart_fss as dart

    # 보고서 객체 가져오기
    report = dart.search(rcept_no=rcept_no)[0]

    # 연결재무제표 주석에서 종속기업 정보 추출
    notes = report.get("consolidated_notes")

    subsidiaries = []
    for note in notes:
        if "종속기업" in note.title or "관계기업" in note.title:
            # 테이블 데이터 추출
            for row in note.tables:
                subsidiary = {
                    "name": row.get("회사명"),
                    "ownership_pct": parse_percentage(row.get("지분율")),
                    "book_value": parse_amount(row.get("장부금액")),
                    "is_listed": check_if_listed(row.get("회사명"))
                }
                subsidiaries.append(subsidiary)

    return subsidiaries
```

#### 상장 자회사 시가총액 조회 (KRX)

```python
from pykrx import stock

def get_listed_subsidiary_value(stock_code: str, ownership_pct: float) -> Dict:
    """
    상장 자회사의 시가총액 기준 지분가치 계산

    Args:
        stock_code: 자회사 종목코드
        ownership_pct: 지분율 (0.0 ~ 1.0)

    Returns:
        Dict: 지분가치 정보
    """
    # 최근 거래일 시가총액 조회
    from datetime import datetime, timedelta

    today = datetime.now().strftime("%Y%m%d")
    market_cap = stock.get_market_cap_by_ticker(today).loc[stock_code, "시가총액"]

    equity_value = market_cap * ownership_pct

    return {
        "stock_code": stock_code,
        "market_cap": market_cap,
        "ownership_pct": ownership_pct,
        "equity_value": equity_value,
        "valuation_method": "시가총액 기준"
    }
```

#### NAV 계산 로직

```python
def calculate_nav_valuation(holding_company_code: str) -> Dict:
    """
    지주회사 NAV 할인법 밸류에이션

    Returns:
        Dict: NAV 기반 적정주가 정보
    """
    # 1. 자회사 정보 수집
    subsidiaries = get_subsidiaries_from_dart(holding_company_code, DART_API_KEY)

    # 2. 자회사별 가치 계산
    total_listed_value = 0
    total_unlisted_value = 0
    subsidiary_valuations = []

    for sub in subsidiaries:
        if sub["is_listed"]:
            # 상장 자회사: 시가총액 기준
            value_info = get_listed_subsidiary_value(
                sub["stock_code"],
                sub["ownership_pct"]
            )
            total_listed_value += value_info["equity_value"]
            subsidiary_valuations.append({
                **sub,
                "valuation_method": "시가총액",
                "calculated_value": value_info["equity_value"]
            })
        else:
            # 비상장 자회사: 장부가 기준 (보수적 접근)
            # 또는 추정 PBR 적용
            estimated_value = sub["book_value"] * 1.0  # PBR 1.0배 가정
            total_unlisted_value += estimated_value
            subsidiary_valuations.append({
                **sub,
                "valuation_method": "장부가 기준",
                "calculated_value": estimated_value
            })

    # 3. 총 NAV 계산
    gross_nav = total_listed_value + total_unlisted_value

    # 4. 지주회사 할인율 결정
    discount_rate = determine_holding_discount(holding_company_code)

    # 5. 순자산가치 계산
    net_nav = gross_nav * (1 - discount_rate)

    # 6. 주당 가치
    shares_outstanding = get_shares_outstanding(holding_company_code)
    fair_price = net_nav / shares_outstanding

    return {
        "gross_nav": gross_nav,
        "listed_subsidiary_value": total_listed_value,
        "unlisted_subsidiary_value": total_unlisted_value,
        "discount_rate": discount_rate,
        "net_nav": net_nav,
        "fair_price_per_share": fair_price,
        "subsidiary_breakdown": subsidiary_valuations,
        "methodology": "NAV 할인법",
        "caveats": [
            "비상장 자회사는 장부가 기준 (보수적 추정)",
            f"지주회사 할인율 {discount_rate*100:.0f}% 적용"
        ]
    }

def determine_holding_discount(corp_code: str) -> float:
    """
    지주회사 할인율 결정

    기본 할인율: 40%
    조정 요인:
    - 지배구조 우수: -5%p
    - 고배당 정책 (3% 이상): -5%p
    - 유동성 부족 (일평균 50억 미만): +5%p
    - 복잡한 순환출자: +10%p

    범위: 20% ~ 60%
    """
    base_discount = 0.40
    adjustments = []

    # 지배구조 평가 (ESG 등급 활용)
    governance_score = get_governance_score(corp_code)
    if governance_score and governance_score >= 80:
        base_discount -= 0.05
        adjustments.append("지배구조 우수: -5%p")

    # 배당수익률
    dividend_yield = get_dividend_yield(corp_code)
    if dividend_yield and dividend_yield >= 0.03:
        base_discount -= 0.05
        adjustments.append(f"고배당 ({dividend_yield*100:.1f}%): -5%p")

    # 유동성
    adtv = get_avg_daily_trading_value(corp_code)
    if adtv < 5_000_000_000:  # 50억 미만
        base_discount += 0.05
        adjustments.append("유동성 부족: +5%p")

    # 범위 제한
    final_discount = max(0.20, min(0.60, base_discount))

    return final_discount
```

#### NAV 밸류에이션 출력 형식

```json
{
  "stock_code": "005440",
  "stock_name": "현대지에프홀딩스",
  "valuation_date": "2026-02-07",
  "current_price": 9950,
  "nav_valuation": {
    "gross_nav": 2500000000000,
    "listed_subsidiaries": [
      {
        "name": "현대백화점",
        "stock_code": "069960",
        "ownership_pct": 42.4,
        "market_cap": 3000000000000,
        "equity_value": 1272000000000
      },
      {
        "name": "현대그린푸드",
        "stock_code": "005440",
        "ownership_pct": 35.2,
        "market_cap": 800000000000,
        "equity_value": 281600000000
      }
    ],
    "unlisted_subsidiaries": [
      {
        "name": "현대리바트",
        "book_value": 150000000000,
        "estimated_value": 150000000000
      }
    ],
    "discount_rate": 0.40,
    "discount_adjustments": [
      "기본 할인율: 40%",
      "유동성 부족: +5%p",
      "최종 할인율: 45%"
    ],
    "net_nav": 1375000000000,
    "fair_price_per_share": 32000,
    "upside_pct": 221.6
  },
  "caveats": [
    "⚠️ 지주회사: 업종 평균 PER 직접 적용 부적합",
    "📊 NAV 할인법 적용 (할인율 45%)",
    "비상장 자회사는 장부가 기준 보수적 추정"
  ]
}
```

#### 데이터 수집 우선순위

1. **상장 자회사** (정확도 높음)
   - KRX에서 실시간 시가총액 조회 가능
   - 지분율은 DART 사업보고서에서 확인

2. **비상장 자회사** (추정 필요)
   - DART 사업보고서의 장부가 사용
   - 보수적으로 PBR 1.0배 적용
   - 실적이 좋은 자회사는 상향 조정 가능

3. **자체 영업가치**
   - 지주회사 본사의 영업이익 기반 가치
   - 브랜드 수수료 수익 등

### 구조적 할인/프리미엄 요인

```yaml
structural_discounts:
  holding_company_discount:
    range: "30-50%"
    reason: "복잡한 지배구조, 이중과세, 유동성 부족"
    applicable: "종목명에 '지주', '홀딩스' 포함"

  liquidity_discount:
    thresholds:
      - daily_trading_value < 10억원: "15-20% 할인"
      - daily_trading_value < 50억원: "5-10% 할인"
      - daily_trading_value < 100억원: "3-5% 할인"

  governance_discount:
    factors:
      - 순환출자 구조: "5-10%"
      - 오너 리스크: "5-15%"
      - 소액주주 보호 미흡: "5-10%"

  small_cap_discount:
    reason: "정보 비대칭, 애널리스트 커버리지 부족"
    threshold: "시총 3000억원 미만"
    range: "5-15%"

  conglomerate_discount:
    reason: "복합 사업 구조로 인한 비효율"
    range: "10-20%"

  no_growth_discount:
    condition: "매출 역성장 또는 0% 성장"
    range: "10-30%"

structural_premiums:
  market_leader:
    condition: "시장점유율 1위 또는 30% 이상"
    range: "+10-20%"

  high_growth:
    condition: "EPS 성장률 > 업종 평균의 1.5배"
    range: "+10-30%"

  high_dividend:
    condition: "배당수익률 > 4%"
    range: "+5-10%"
```

### 현재 밸류에이션 원인 분석 (필수 단계)

**적정가치 산출 전에 반드시 "왜 시장이 이 가격에 거래시키는가"를 분석해야 합니다.**

```python
def analyze_valuation_reason(stock, sector_avg):
    """
    현재 밸류에이션의 원인 분석 - 적정가치 산출 전 필수 단계

    Returns:
        dict: 밸류에이션 원인 분석 결과 및 적절한 방법론 추천
    """
    reasons = []
    discount_factors = []
    total_structural_discount = 0

    # 1. 종목 유형 식별
    stock_type = identify_stock_type(stock)

    # 2. 지주회사 여부
    if is_holding_company(stock):
        reasons.append("지주회사 구조")
        discount_factors.append({
            "factor": "holding_discount",
            "pct": 40,
            "note": "NAV 할인법 적용 필요"
        })
        total_structural_discount += 40

    # 3. 유동성 체크
    adtv = stock.avg_daily_trading_value
    if adtv < 10_000_000_000:  # 100억원 미만
        if adtv < 1_000_000_000:  # 10억원 미만
            liq_discount = 17.5
        elif adtv < 5_000_000_000:  # 50억원 미만
            liq_discount = 7.5
        else:
            liq_discount = 4
        reasons.append(f"유동성 부족 (일평균 {adtv/1e8:.0f}억원)")
        discount_factors.append({
            "factor": "liquidity_discount",
            "pct": liq_discount
        })
        total_structural_discount += liq_discount

    # 4. 성장 정체
    if stock.revenue_growth_3y is not None and stock.revenue_growth_3y < 0:
        reasons.append("매출 역성장")
        discount_factors.append({
            "factor": "no_growth_discount",
            "pct": 15
        })
        total_structural_discount += 15

    # 5. 사이클 산업
    cyclical_sectors = ["반도체", "철강", "화학", "해운", "조선"]
    if stock.sector in cyclical_sectors:
        reasons.append(f"사이클 산업 ({stock.sector})")
        discount_factors.append({
            "factor": "cyclical_adjustment",
            "note": "정상화 이익 기준 PER 사용 필요"
        })

    # 6. 적절한 밸류에이션 방법 추천
    recommended_method = get_recommended_valuation_method(stock_type)

    return {
        "current_per": stock.per,
        "sector_avg_per": sector_avg.per,
        "discount_to_sector_pct": (stock.per / sector_avg.per - 1) * 100,
        "identified_reasons": reasons,
        "discount_factors": discount_factors,
        "total_structural_discount_pct": total_structural_discount,
        "stock_type": stock_type,
        "recommended_method": recommended_method,
        "warning": "업종 평균 PER 직접 적용 금지" if total_structural_discount > 20 else None
    }

def get_recommended_valuation_method(stock_type):
    """종목 유형별 추천 밸류에이션 방법"""
    methods = {
        "holding_company": {
            "primary": "NAV 할인법",
            "secondary": "Sum-of-the-Parts",
            "avoid": "업종 평균 PER"
        },
        "cyclical": {
            "primary": "정상화 이익 기준 PER",
            "secondary": "Mid-cycle 밸류에이션",
            "avoid": "현재 EPS 기준 PER"
        },
        "growth": {
            "primary": "PEG, DCF",
            "secondary": "Forward PER",
            "avoid": "Trailing PER"
        },
        "financial": {
            "primary": "PBR",
            "secondary": "ROE 조정 PBR",
            "avoid": "EV/EBITDA"
        },
        "loss_making": {
            "primary": "PSR, EV/Sales",
            "secondary": "정상화 이익 기준",
            "avoid": "PER (음수)"
        },
        "standard": {
            "primary": "Peer 평균 PER (조정)",
            "secondary": "Historical Band",
            "note": "구조적 할인 요인 반영 필수"
        }
    }
    return methods.get(stock_type, methods["standard"])
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
