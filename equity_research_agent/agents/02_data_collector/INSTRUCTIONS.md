# Agent 02: Data Collector (데이터 수집 에이전트)

## 역할

`01_data_identifier`가 정의한 데이터 요구사항에 따라 다양한 소스에서 데이터를 수집합니다.

## 입력

- `data_requirements.json` (01_data_identifier 출력)
- 데이터 소스 접근 정보

## 출력

- `raw_data/`: 소스별 원시 데이터
- `collection_log.json`: 수집 로그 및 메타데이터

## 데이터 소스 우선순위

### Tier 1: 고신뢰 무료 소스

| 소스 | 데이터 유형 | 업데이트 주기 | 상세 가이드 |
|------|-------------|---------------|-------------|
| LSEG I/B/E/S | 이익 수정 비율, 컨센서스 | 주간 | [lseg_ibes.md](sources/lseg_ibes.md) |
| MSCI Factsheets | 지수 펀더멘털, P/E | 월간 | [msci_factsheets.md](sources/msci_factsheets.md) |
| Yardeni Research | 글로벌 이익 차트 | 주간 | [yardeni_research.md](sources/yardeni_research.md) |

### Tier 2: 증권사 리서치

| 소스 | 데이터 유형 | 접근 방법 | 상세 가이드 |
|------|-------------|-----------|-------------|
| 미래에셋 글로벌 전략 | 국가별 컨센서스 | 공개 리포트 | [brokerage_reports.md](sources/brokerage_reports.md) |
| 삼성증권 글로벌 전략 | 밸류에이션 테이블 | 공개 리포트 | [brokerage_reports.md](sources/brokerage_reports.md) |

## 수집 워크플로우

### Phase 1: LSEG I/B/E/S Weekly Aggregates

```yaml
source: "LSEG I/B/E/S"
endpoint: "Weekly Aggregates Report"
extraction_points:
  - "Earnings Revision Ratio by Country"
  - "12-Month Forward EPS Growth"
  - "Consensus Estimate Changes"
```

**수집 절차:**
1. LSEG 공개 리서치 페이지 접속
2. "Weekly Aggregates" 리포트 다운로드
3. 국가별 이익 수정 비율 테이블 추출
4. JSON 형식으로 변환 저장

### Phase 2: MSCI Index Factsheets

```yaml
source: "MSCI"
documents:
  - "MSCI Korea Index Factsheet"
  - "MSCI Taiwan Index Factsheet"
  - "MSCI India Index Factsheet"
  - "MSCI China Index Factsheet"
extraction_points:
  - "Fundamentals > Forward P/E"
  - "Fundamentals > Price/Book"
  - "Fundamentals > Dividend Yield"
```

**수집 절차:**
1. MSCI 공식 웹사이트 접속
2. 각 국가별 Factsheet PDF 다운로드
3. Fundamentals 섹션 파싱
4. 구조화된 데이터로 변환

### Phase 3: Yardeni Research

```yaml
source: "Yardeni Research"
reports:
  - "Global Index Briefing: MSCI Forward Earnings"
  - "Global Stock Market Briefing: Earnings Squiggles"
extraction_points:
  - "Annual EPS Growth Charts"
  - "Consensus Trend Changes"
```

**수집 절차:**
1. Yardeni Research 공개 자료실 접속
2. 관련 PDF 리포트 다운로드
3. 차트 데이터 디지타이징
4. 시계열 데이터로 구조화

### Phase 4: 증권사 리서치 리포트

```yaml
source: "Korean Brokerages"
targets:
  - company: "미래에셋"
    report_type: "글로벌 자산배분 전략"
  - company: "삼성증권"
    report_type: "글로벌 주식 전략"
extraction_points:
  - "국가별 EPS 성장률 전망"
  - "밸류에이션 비교 테이블"
```

## 데이터 스키마

수집된 데이터는 다음 스키마를 따릅니다:

```json
{
  "source": "string",
  "collected_at": "ISO8601",
  "index": "string",
  "period": "string",
  "metrics": {
    "eps_growth_12mf": "number",
    "forward_pe": "number",
    "trailing_pe": "number",
    "pb_ratio": "number",
    "roe": "number",
    "dividend_yield": "number"
  },
  "confidence": "high|medium|low",
  "notes": "string"
}
```

## 에러 처리

### 데이터 부재 시 대안

1. **Primary 소스 실패**: Tier 2 소스로 대체
2. **모든 소스 실패**: EPS 역산 공식 적용

```
Index Level ÷ Forward P/E = Implied EPS
```

3. **과거 데이터만 가용**: 트렌드 외삽(extrapolation) 적용 (별도 표시)

## 다음 단계

수집된 원시 데이터를 `03_data_validator` 에이전트로 전달합니다.
