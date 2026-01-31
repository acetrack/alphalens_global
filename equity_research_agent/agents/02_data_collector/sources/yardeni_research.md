# Yardeni Research 데이터 수집 가이드

## 개요

Yardeni Research는 Dr. Ed Yardeni가 운영하는 독립 리서치 기관으로, 글로벌 이익 전망 차트(Squiggles)와 밸류에이션 데이터를 무료로 공개합니다.

## 접근 경로

### 공식 웹사이트
- URL: https://www.yardeni.com
- Research 섹션에서 무료 리포트 다운로드

### 주요 리포트

| 리포트명 | 내용 | 업데이트 주기 |
|----------|------|---------------|
| Global Index Briefing: MSCI Forward Earnings | 국가별 선행 EPS | 주간 |
| Stock Market Briefing: Earnings Squiggles | 이익 전망 추이 차트 | 주간 |
| Global Economic Briefing | 매크로 지표 | 주간 |

## 주요 추출 데이터

### Earnings Squiggles (이익 전망 추이)

"Squiggles"는 시간에 따른 컨센서스 EPS 전망치 변화를 보여주는 차트입니다.

```
     ▲ EPS
     │
 110 │      ╭───────────  2026E
     │     ╱
 100 │    ╱  ╭──────────  2025E
     │   ╱  ╱
  90 │  ╱  ╱
     │ ╱  ╱
  80 │╱  ╱
     │──────────────────▶ Time
     Jan   Apr   Jul   Oct
```

### 추출 포인트

1. **연도별 EPS 전망치**: 2024A, 2025E, 2026E
2. **전망 수정 추이**: 상향/하향 트렌드
3. **YoY 성장률**: 연간 EPS 성장률

## 국가별 데이터 위치

### Global Index Briefing 내 위치

| 국가/지역 | 차트 페이지 | 데이터 포인트 |
|-----------|-------------|---------------|
| Emerging Markets | p.5-8 | MSCI EM Forward EPS |
| Asia ex-Japan | p.9-12 | 국가별 세부 데이터 |
| Korea | p.10 | MSCI Korea EPS |
| Taiwan | p.11 | MSCI Taiwan EPS |
| China | p.12 | MSCI China EPS |
| India | p.13 | MSCI India EPS |

## 데이터 추출 절차

### Step 1: 리포트 다운로드

```bash
# Yardeni 웹사이트에서 최신 리포트 다운로드
# 경로: raw_data/yardeni/global_index_briefing_YYYYMMDD.pdf
```

### Step 2: 차트 데이터 디지타이징

차트에서 수치 추출 (수동 또는 OCR):

```json
{
  "index": "MSCI Korea",
  "chart_type": "earnings_squiggle",
  "data_points": [
    {"date": "2024-01", "2024E": 95, "2025E": 105, "2026E": 115},
    {"date": "2024-04", "2024E": 96, "2025E": 108, "2026E": 118},
    {"date": "2024-07", "2024E": 98, "2025E": 110, "2026E": 120}
  ]
}
```

### Step 3: 성장률 계산

$$
\text{EPS Growth}_{2025} = \frac{EPS_{2025E} - EPS_{2024A}}{EPS_{2024A}} \times 100
$$

### Step 4: 구조화된 출력

```json
{
  "source": "Yardeni Research",
  "report": "Global Index Briefing",
  "report_date": "2025-01-27",
  "data": {
    "MSCI Korea": {
      "eps_2024a": 98,
      "eps_2025e": 110,
      "eps_2026e": 120,
      "growth_2025e": 12.2,
      "growth_2026e": 9.1,
      "revision_trend": "improving"
    },
    "MSCI Taiwan": {
      "eps_2024a": 85,
      "eps_2025e": 102,
      "eps_2026e": 112,
      "growth_2025e": 20.0,
      "growth_2026e": 9.8,
      "revision_trend": "stable"
    }
  }
}
```

## 차트 해석 가이드

### 상향 수정 신호
- 최근 Squiggle이 우상향
- 최신 전망치가 과거 전망치보다 높음

### 하향 수정 신호
- 최근 Squiggle이 우하향
- 최신 전망치가 과거 전망치보다 낮음

### 컨센서스 수렴
- Squiggle 간격이 좁아짐
- 불확실성 감소 의미

## 주의사항

1. **인덱싱 기준**: Yardeni 데이터는 인덱스 형태(기준년=100)일 수 있음
2. **소스 확인**: I/B/E/S 기반 데이터임을 명시
3. **시차**: 리포트 작성 시점과 데이터 시점 차이 확인

## 보완 데이터

Yardeni에서 추가로 확인 가능한 데이터:
- Forward P/E 추이
- Valuation Model (Fed Model 등)
- Macro indicators (GDP, PMI 등)
