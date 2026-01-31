# MSCI Index Factsheets 데이터 수집 가이드

## 개요

MSCI는 각 지수의 월별 Factsheet를 무료로 공개합니다. 지수의 섹터 구성, 밸류에이션 지표, 성과 데이터를 확인할 수 있습니다.

## 접근 경로

### 공식 웹사이트
- URL: https://www.msci.com/indexes
- 각 국가별 지수 페이지에서 Factsheet PDF 다운로드

### 직접 링크 패턴
```
https://www.msci.com/documents/10199/{document-id}/{index-name}-factsheet.pdf
```

## 주요 추출 데이터

### Fundamentals 섹션

| 지표 | 설명 | 위치 |
|------|------|------|
| Forward P/E | 12개월 선행 P/E | Fundamentals 테이블 |
| Trailing P/E | 과거 12개월 P/E | Fundamentals 테이블 |
| Price/Book | 주가순자산비율 | Fundamentals 테이블 |
| Dividend Yield | 배당수익률 | Fundamentals 테이블 |

### Sector Weights 섹션

| 섹터 | 데이터 포인트 |
|------|---------------|
| Information Technology | 비중(%), 수익기여도 |
| Financials | 비중(%), 수익기여도 |
| Consumer Discretionary | 비중(%), 수익기여도 |
| ... | ... |

## 지수별 수집 대상

### MSCI Korea
```yaml
index_code: "MXKR"
components: ~100 종목
key_sectors:
  - Information Technology (삼성전자, SK하이닉스)
  - Financials
  - Industrials
```

### MSCI Taiwan
```yaml
index_code: "MXTW"
components: ~90 종목
key_sectors:
  - Information Technology (TSMC, MediaTek)
  - Financials
  - Materials
```

### MSCI China
```yaml
index_code: "MXCN"
components: ~700 종목
variants:
  - MSCI China (Offshore)
  - MSCI China A (Onshore)
key_sectors:
  - Communication Services (Tencent, Alibaba)
  - Consumer Discretionary
  - Financials
```

### MSCI India
```yaml
index_code: "MXIN"
components: ~140 종목
key_sectors:
  - Financials (HDFC, ICICI)
  - Information Technology (Infosys, TCS)
  - Energy (Reliance)
```

## 데이터 추출 절차

### Step 1: Factsheet 다운로드
```bash
# 각 지수별 최신 Factsheet 다운로드
# 경로: raw_data/msci/{index_code}_factsheet_YYYYMM.pdf
```

### Step 2: PDF 파싱

Fundamentals 테이블 추출:
```
┌─────────────────────────────────────────┐
│          INDEX FUNDAMENTALS             │
├─────────────────┬───────────┬───────────┤
│                 │   Index   │ ACWI IMI  │
├─────────────────┼───────────┼───────────┤
│ Forward P/E     │   12.5    │   17.2    │
│ Trailing P/E    │   14.3    │   20.1    │
│ Price/Book      │   1.2     │   2.8     │
│ Dividend Yield  │   2.1%    │   1.9%    │
└─────────────────┴───────────┴───────────┘
```

### Step 3: 데이터 구조화

```json
{
  "source": "MSCI Factsheet",
  "index": "MSCI Korea",
  "index_code": "MXKR",
  "as_of_date": "2025-01-31",
  "fundamentals": {
    "forward_pe": 12.5,
    "trailing_pe": 14.3,
    "price_book": 1.2,
    "dividend_yield": 2.1
  },
  "sector_weights": {
    "Information Technology": 42.5,
    "Financials": 15.2,
    "Industrials": 11.3
  }
}
```

## EPS 역산 활용

Forward P/E와 지수 레벨로 EPS 추정:

$$
EPS_{12MF} = \frac{\text{Index Level}}{\text{Forward P/E}}
$$

**예시 (MSCI Korea)**:
- Index Level: 1,250
- Forward P/E: 12.5
- Implied EPS: 1,250 / 12.5 = 100

## 주의사항

1. **업데이트 시점**: Factsheet는 월말 기준, 다음 달 중순 공개
2. **지수 레벨**: Factsheet에는 지수 레벨이 없을 수 있음 → 별도 확인 필요
3. **통화**: 지수 레벨은 USD 기준
