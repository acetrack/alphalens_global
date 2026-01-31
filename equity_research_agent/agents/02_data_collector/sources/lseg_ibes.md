# LSEG I/B/E/S 데이터 수집 가이드

## 개요

LSEG(구 Refinitiv) I/B/E/S는 글로벌 이익 추정치 데이터의 표준입니다. Weekly Aggregates Report를 통해 국가별 이익 수정 비율 및 성장률 데이터를 무료로 확인할 수 있습니다.

## 접근 경로

### 1. LSEG Workspace (유료)
- 전체 데이터 접근
- API 활용 가능

### 2. Weekly Aggregates Report (무료 공개)
- URL: LSEG 리서치 페이지에서 "I/B/E/S Weekly Aggregates" 검색
- 매주 월요일 업데이트
- PDF 형식

## 주요 추출 데이터

### Earnings Revision Ratio (이익 수정 비율)

| 지표 | 설명 | 계산식 |
|------|------|--------|
| Up/Down Ratio | 상향 대비 하향 수정 비율 | (상향 건수) / (하향 건수) |
| Net Revisions | 순 수정 비율 | (상향 - 하향) / 전체 |
| Revision Momentum | 수정 모멘텀 | 4주 이동평균 변화 |

### 국가별 EPS 성장률

| 국가 | 지표 | 비고 |
|------|------|------|
| Korea | 12MF EPS Growth | KOSPI 대형주 기준 |
| Taiwan | 12MF EPS Growth | TWSE 대형주 기준 |
| China | 12MF EPS Growth | CSI300 + H주 포함 |
| India | 12MF EPS Growth | Nifty 50 기준 |

## 데이터 추출 절차

### Step 1: 리포트 다운로드
```bash
# 수동 다운로드 후 저장
# 경로: raw_data/lseg/ibes_weekly_YYYYMMDD.pdf
```

### Step 2: 테이블 파싱

PDF에서 다음 테이블을 찾아 추출:
- "Earnings Revisions by Country/Region"
- "Forward EPS Growth Rates"

### Step 3: 데이터 변환

```json
{
  "source": "LSEG I/B/E/S",
  "report_date": "2025-01-27",
  "data": [
    {
      "index": "MSCI Korea",
      "eps_growth_12mf": 15.2,
      "revision_ratio": 1.05,
      "up_revisions": 52,
      "down_revisions": 48
    }
  ]
}
```

## 주의사항

1. **데이터 지연**: 무료 리포트는 1주일 지연 가능
2. **지수 매핑**: I/B/E/S 국가 분류와 MSCI 지수 매핑 필요
3. **섹터 가중치**: 섹터별 이익 기여도 별도 확인 필요

## 대체 소스

I/B/E/S 데이터 접근 불가 시:
- Yardeni Research 참조
- Bloomberg 컨센서스 뉴스 기사 크롤링
