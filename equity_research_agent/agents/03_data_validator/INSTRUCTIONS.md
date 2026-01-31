# Agent 03: Data Validator (데이터 검증 에이전트)

## 역할

수집된 원시 데이터의 품질을 검증하고, 일관성을 확인하며, 분석에 적합한 형태로 정제합니다.

## 입력

- `raw_data/`: 02_data_collector가 수집한 원시 데이터
- `data_requirements.json`: 01_data_identifier의 데이터 명세

## 출력

- `validated_data/`: 검증 완료된 정제 데이터
- `validation_report.json`: 검증 결과 및 품질 리포트
- `data_issues.json`: 발견된 이슈 및 처리 내역

## 검증 워크플로우

### Phase 1: 완전성 검증 (Completeness Check)

모든 필수 데이터 항목이 수집되었는지 확인합니다.

```yaml
completeness_check:
  required_indices:
    - MSCI Korea
    - MSCI Taiwan
    - MSCI China
    - MSCI India

  required_metrics:
    P1: ["12MF EPS Growth", "Forward P/E"]
    P2: ["EBITDA Growth", "ROE"]
    P3: ["Net Margin", "P/B Ratio"]

  required_periods:
    historical: [2021, 2022, 2023, 2024]
    forecast: [2025, 2026]
```

**검증 룰**:
```python
def check_completeness(data, requirements):
    missing = []
    for index in requirements['indices']:
        for metric in requirements['metrics']['P1']:
            if metric not in data.get(index, {}):
                missing.append(f"{index}/{metric}")
    return missing
```

### Phase 2: 일관성 검증 (Consistency Check)

동일 지표에 대한 다중 소스 데이터 간 일관성을 확인합니다.

#### 크로스 소스 비교

| 지표 | 소스 1 | 소스 2 | 차이 | 판정 |
|------|--------|--------|------|------|
| Korea Fwd P/E | I/B/E/S: 9.5 | MSCI: 9.8 | 0.3 | ✅ 허용 |
| Taiwan EPS Growth | Yardeni: 20% | 미래에셋: 25% | 5%p | ⚠️ 주의 |

**허용 오차 기준**:
```yaml
tolerance_thresholds:
  forward_pe: 1.0        # ±1.0x
  eps_growth: 5.0        # ±5%p
  roe: 2.0               # ±2%p
  dividend_yield: 0.5    # ±0.5%p
```

**불일치 처리 규칙**:
```yaml
reconciliation_rules:
  - if: "deviation <= threshold"
    action: "use_average"

  - if: "deviation > threshold AND primary_source_available"
    action: "use_primary_source"
    primary_sources: ["I/B/E/S", "MSCI"]

  - if: "deviation > threshold AND no_primary"
    action: "flag_for_review"
```

### Phase 3: 유효성 검증 (Validity Check)

데이터 값이 합리적인 범위 내에 있는지 확인합니다.

```yaml
validity_ranges:
  forward_pe:
    min: 5
    max: 50
    alert_if: "<8 or >35"

  eps_growth:
    min: -50
    max: 100
    alert_if: "<-30 or >70"

  roe:
    min: -20
    max: 40
    alert_if: "<0 or >30"

  dividend_yield:
    min: 0
    max: 10
    alert_if: ">7"
```

### Phase 4: 시계열 연속성 검증

연도별 데이터의 급격한 변화를 감지합니다.

```python
def check_time_series_continuity(data):
    alerts = []
    for index, values in data.items():
        for year in range(len(values) - 1):
            yoy_change = abs(values[year+1] - values[year])
            if yoy_change > 30:  # 30%p 이상 변화
                alerts.append({
                    "index": index,
                    "years": f"{year}-{year+1}",
                    "change": yoy_change,
                    "severity": "high"
                })
    return alerts
```

## 데이터 정제 절차

### Step 1: 결측치 처리

```yaml
missing_data_handling:
  strategy_1:
    condition: "single_source_missing"
    action: "use_alternative_source"

  strategy_2:
    condition: "all_sources_missing"
    action: "interpolate_or_calculate"
    methods:
      - "linear_interpolation"
      - "eps_reverse_calculation"

  strategy_3:
    condition: "critical_data_missing"
    action: "flag_and_exclude"
```

### Step 2: 단위 표준화

```yaml
unit_standardization:
  eps_growth:
    target_unit: "percentage"
    conversion:
      - from: "decimal"
        multiply: 100
      - from: "basis_points"
        divide: 100

  market_cap:
    target_unit: "USD_billions"
    conversion:
      - from: "KRW"
        divide: 1350000000000  # 환율 적용
```

### Step 3: 이상치 처리

```python
def handle_outliers(data, method='winsorize'):
    if method == 'winsorize':
        # 상하위 5% 값을 경계값으로 대체
        lower = np.percentile(data, 5)
        upper = np.percentile(data, 95)
        return np.clip(data, lower, upper)
    elif method == 'flag':
        # 이상치 플래그만 추가, 값은 유지
        return data, identify_outliers(data)
```

## 출력 스키마

### validated_data.json

```json
{
  "metadata": {
    "validated_at": "2025-01-31T10:30:00Z",
    "total_records": 24,
    "passed": 22,
    "flagged": 2
  },
  "data": {
    "MSCI Korea": {
      "eps_growth": {
        "2024A": 55.0,
        "2025E": 15.0,
        "2026E": 12.0,
        "source": "I/B/E/S (primary)",
        "confidence": "high"
      },
      "forward_pe": {
        "value": 9.5,
        "source": "MSCI Factsheet",
        "confidence": "high"
      }
    }
  }
}
```

### validation_report.json

```json
{
  "summary": {
    "total_checks": 150,
    "passed": 142,
    "warnings": 6,
    "errors": 2
  },
  "issues": [
    {
      "type": "consistency",
      "index": "MSCI Taiwan",
      "metric": "eps_growth_2025e",
      "sources": {"Yardeni": 20, "Mirae": 25},
      "resolution": "used_average",
      "final_value": 22.5
    }
  ]
}
```

## 다음 단계

검증 완료된 데이터를 `04_analyst` 에이전트로 전달합니다.
