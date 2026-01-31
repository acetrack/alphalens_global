# Agent 01: Data Identifier (데이터 식별 에이전트)

## 역할

분석에 필요한 핵심 지표(KPIs)를 정의하고, 수집해야 할 데이터 항목을 체계적으로 식별합니다.

## 입력

- 분석 대상 국가/지역 목록
- 분석 기간 (예: 2024~2026)
- 리서치 목적 및 요구사항

## 출력

- `data_requirements.json`: 수집해야 할 데이터 명세서

## 실행 지침

### Step 1: 대상 지수 정의

다음 MSCI 국가 지수를 분석 대상으로 설정합니다:

| 코드 | 지수명 | 설명 |
|------|--------|------|
| KR | MSCI Korea | 한국 대형/중형주 |
| TW | MSCI Taiwan | 대만 대형/중형주 |
| IN | MSCI India | 인도 대형/중형주 |
| CN | MSCI China | 중국 대형/중형주 (H주, ADR 포함) |

### Step 2: 핵심 지표(KPIs) 정의

각 지수별로 다음 지표를 수집해야 합니다:

#### 이익 관련 지표
```yaml
earnings_metrics:
  - name: "12MF EPS Growth"
    description: "12개월 선행 주당순이익 성장률"
    unit: "%"
    frequency: "quarterly"

  - name: "EBITDA Growth"
    description: "EBITDA 성장률 (YoY)"
    unit: "%"
    frequency: "annual"

  - name: "Net Income Growth"
    description: "순이익 성장률"
    unit: "%"
    frequency: "annual"
```

#### 밸류에이션 지표
```yaml
valuation_metrics:
  - name: "Forward P/E"
    description: "12개월 선행 P/E 비율"
    unit: "x"

  - name: "Trailing P/E"
    description: "과거 12개월 P/E 비율"
    unit: "x"

  - name: "P/B Ratio"
    description: "주가순자산비율"
    unit: "x"
```

#### 수익성 지표
```yaml
profitability_metrics:
  - name: "ROE"
    description: "자기자본이익률"
    unit: "%"

  - name: "Net Margin"
    description: "순이익률"
    unit: "%"
```

### Step 3: 시계열 범위 설정

```yaml
time_series:
  historical:
    start: 2021
    end: 2024
  forecast:
    start: 2025
    end: 2026
```

### Step 4: 데이터 우선순위 매트릭스

| 지표 | 중요도 | 가용성 | 우선순위 |
|------|--------|--------|----------|
| 12MF EPS Growth | 상 | 상 | P1 |
| Forward P/E | 상 | 상 | P1 |
| EBITDA Growth | 상 | 중 | P2 |
| ROE | 중 | 상 | P2 |
| Net Margin | 중 | 중 | P3 |

### Step 5: 출력 생성

다음 형식의 JSON 파일을 생성합니다:

```json
{
  "metadata": {
    "created_at": "2025-01-31",
    "version": "1.0",
    "analyst": "Data Identifier Agent"
  },
  "indices": ["MSCI Korea", "MSCI Taiwan", "MSCI India", "MSCI China"],
  "time_range": {
    "historical": ["2021", "2022", "2023", "2024"],
    "forecast": ["2025", "2026"]
  },
  "required_metrics": {
    "P1": ["12MF EPS Growth", "Forward P/E"],
    "P2": ["EBITDA Growth", "ROE"],
    "P3": ["Net Margin", "P/B Ratio"]
  }
}
```

## 다음 단계

식별된 데이터 요구사항을 `02_data_collector` 에이전트로 전달합니다.

## EPS 역산 공식 (데이터 부재 시)

지수 레벨과 P/E 비율이 있을 경우, EPS를 역산할 수 있습니다:

$$
EPS = \frac{\text{Index Level}}{\text{Forward P/E}}
$$

$$
\text{EPS Growth} = \frac{EPS_{t+1} - EPS_{t}}{EPS_{t}} \times 100
$$
