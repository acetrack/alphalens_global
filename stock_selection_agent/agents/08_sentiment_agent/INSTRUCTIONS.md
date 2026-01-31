# Agent 08: Sentiment Agent (센티먼트 분석 에이전트)

## 역할

뉴스, 공시, 애널리스트 의견, 소셜 미디어 등 비정형 데이터를 분석하여 시장 센티먼트를 파악합니다. 자연어처리(NLP)를 활용하여 긍정/부정 신호를 추출하고 투자 의사결정에 반영합니다.

## 입력

- `screened_stocks.json`: 스크리닝 결과
- 뉴스 기사 (네이버, 다음, 경제지)
- DART 공시 데이터
- 애널리스트 리포트/컨센서스

## 출력

- `sentiment_analysis/`: 종목별 센티먼트 분석
- `sentiment_scores.json`: 센티먼트 점수 요약

---

## 센티먼트 분석 체계

```
┌─────────────────────────────────────────────────────────────┐
│               Sentiment Analysis Framework                   │
└─────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │ Total Sentiment │
                    │   종합 센티먼트  │
                    └────────┬────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
    ▼                        ▼                        ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   News      │      │  Analyst    │      │  Disclosure │
│ Sentiment   │      │  Sentiment  │      │  Sentiment  │
│   뉴스       │      │  애널리스트  │      │   공시       │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ - Headlines │      │ - Ratings   │      │ - Earnings  │
│ - Article   │      │ - TP Change │      │ - M&A       │
│ - Sentiment │      │ - EPS Rev   │      │ - Buyback   │
│ - Volume    │      │ - Coverage  │      │ - Dividend  │
└─────────────┘      └─────────────┘      └─────────────┘
```

---

## 1단계: 뉴스 센티먼트 분석

### 뉴스 수집

```yaml
news_sources:
  major_portals:
    - name: "네이버 뉴스"
      url: "https://news.naver.com"
      method: "api"
      categories: ["경제", "증권"]

    - name: "다음 뉴스"
      url: "https://news.daum.net"
      method: "scraping"
      categories: ["경제"]

  financial_media:
    - name: "한국경제"
      reliability: "high"
    - name: "매일경제"
      reliability: "high"
    - name: "서울경제"
      reliability: "medium"
    - name: "이데일리"
      reliability: "medium"

  international:
    - name: "Reuters Korea"
      reliability: "high"
    - name: "Bloomberg Korea"
      reliability: "high"
```

### 뉴스 센티먼트 분석

```python
def analyze_news_sentiment(stock, days=30):
    # 뉴스 수집
    news_articles = fetch_news(stock.name, stock.code, days)

    sentiments = []
    for article in news_articles:
        # 헤드라인 센티먼트
        headline_sentiment = analyze_headline(article.headline)

        # 본문 센티먼트 (있는 경우)
        body_sentiment = analyze_body(article.body) if article.body else None

        # 종합 센티먼트
        if body_sentiment:
            combined = 0.4 * headline_sentiment + 0.6 * body_sentiment
        else:
            combined = headline_sentiment

        sentiments.append({
            "date": article.date,
            "source": article.source,
            "headline": article.headline,
            "sentiment": combined,
            "relevance": calculate_relevance(article, stock)
        })

    # 시간 가중 평균 (최근 뉴스에 더 높은 가중치)
    weighted_sentiment = calculate_time_weighted_sentiment(sentiments)

    # 뉴스 볼륨 분석
    news_volume = len(news_articles)
    avg_volume = stock.historical_news_volume_avg

    volume_signal = "surge" if news_volume > avg_volume * 2 else \
                    "above_normal" if news_volume > avg_volume * 1.5 else \
                    "normal"

    return {
        "weighted_sentiment": weighted_sentiment,
        "sentiment_trend": calculate_sentiment_trend(sentiments),
        "news_volume": news_volume,
        "volume_signal": volume_signal,
        "recent_headlines": sentiments[:5],
        "positive_count": len([s for s in sentiments if s["sentiment"] > 0.3]),
        "negative_count": len([s for s in sentiments if s["sentiment"] < -0.3])
    }
```

### 한국어 금융 센티먼트 분석

```python
def analyze_headline(headline):
    # 금융 특화 키워드 사전
    positive_keywords = {
        "실적 호조": 0.8, "흑자 전환": 0.9, "사상 최대": 0.8,
        "수주 확대": 0.7, "신사업 진출": 0.6, "배당 확대": 0.7,
        "자사주 매입": 0.6, "목표가 상향": 0.8, "투자의견 상향": 0.8,
        "어닝 서프라이즈": 0.9, "성장 가속": 0.7, "수출 호조": 0.6,
        "규제 완화": 0.5, "신제품 출시": 0.5
    }

    negative_keywords = {
        "실적 악화": -0.8, "적자 전환": -0.9, "하향 조정": -0.7,
        "수주 감소": -0.7, "구조조정": -0.6, "배당 삭감": -0.7,
        "목표가 하향": -0.8, "투자의견 하향": -0.8, "어닝 쇼크": -0.9,
        "성장 둔화": -0.6, "수출 부진": -0.6, "규제 강화": -0.5,
        "소송": -0.4, "횡령": -0.8, "분식회계": -0.9
    }

    score = 0
    matched_keywords = []

    for keyword, weight in positive_keywords.items():
        if keyword in headline:
            score += weight
            matched_keywords.append((keyword, weight))

    for keyword, weight in negative_keywords.items():
        if keyword in headline:
            score += weight
            matched_keywords.append((keyword, weight))

    # -1 ~ 1 범위로 정규화
    normalized_score = max(-1, min(1, score))

    return normalized_score
```

---

## 2단계: 애널리스트 센티먼트

### 컨센서스 분석

```python
def analyze_analyst_sentiment(stock):
    # 투자의견 분포
    ratings = stock.analyst_ratings
    rating_distribution = {
        "strong_buy": ratings.count("Strong Buy"),
        "buy": ratings.count("Buy"),
        "hold": ratings.count("Hold"),
        "sell": ratings.count("Sell"),
        "strong_sell": ratings.count("Strong Sell")
    }

    # 컨센서스 점수 (-2 ~ +2)
    consensus_score = calculate_consensus_score(rating_distribution)

    # 의견 변화 (최근 3개월)
    rating_changes = stock.rating_changes_3m
    upgrades = len([r for r in rating_changes if r["direction"] == "up"])
    downgrades = len([r for r in rating_changes if r["direction"] == "down"])

    rating_momentum = (upgrades - downgrades) / max(len(rating_changes), 1)

    return {
        "consensus": get_consensus_label(consensus_score),
        "consensus_score": consensus_score,
        "rating_distribution": rating_distribution,
        "total_analysts": sum(rating_distribution.values()),
        "rating_momentum": rating_momentum,
        "upgrades_3m": upgrades,
        "downgrades_3m": downgrades
    }

def calculate_consensus_score(distribution):
    weights = {
        "strong_buy": 2,
        "buy": 1,
        "hold": 0,
        "sell": -1,
        "strong_sell": -2
    }

    total_weight = sum(distribution[k] * weights[k] for k in distribution)
    total_count = sum(distribution.values())

    if total_count == 0:
        return 0

    return total_weight / total_count

def get_consensus_label(score):
    if score > 1.5:
        return "Strong Buy"
    elif score > 0.5:
        return "Buy"
    elif score > -0.5:
        return "Hold"
    elif score > -1.5:
        return "Sell"
    else:
        return "Strong Sell"
```

### 목표주가 분석

```python
def analyze_target_price(stock):
    current_price = stock.price
    target_prices = stock.analyst_target_prices

    if not target_prices:
        return None

    avg_target = np.mean(target_prices)
    median_target = np.median(target_prices)
    high_target = max(target_prices)
    low_target = min(target_prices)

    # 목표주가 대비 현재가 위치
    upside_to_avg = (avg_target / current_price - 1) * 100
    upside_to_median = (median_target / current_price - 1) * 100

    # 목표주가 변화 추이
    tp_changes = stock.target_price_changes_3m
    avg_change = np.mean([c["change_pct"] for c in tp_changes]) if tp_changes else 0

    # 시그널
    signals = []
    if upside_to_avg > 30:
        signals.append({"type": "significant_upside", "value": upside_to_avg})
    if avg_change > 5:
        signals.append({"type": "tp_upgrade_trend", "value": avg_change})
    if avg_change < -5:
        signals.append({"type": "tp_downgrade_trend", "value": avg_change})

    return {
        "current_price": current_price,
        "avg_target": avg_target,
        "median_target": median_target,
        "high_target": high_target,
        "low_target": low_target,
        "upside_to_avg": upside_to_avg,
        "upside_to_median": upside_to_median,
        "tp_change_3m": avg_change,
        "signals": signals
    }
```

### 이익 추정치 수정 (Earnings Revision)

```python
def analyze_earnings_revision(stock):
    # 현재 컨센서스 EPS
    current_eps_est = stock.consensus_eps_current_year
    current_eps_est_next = stock.consensus_eps_next_year

    # 3개월 전 컨센서스 EPS
    eps_est_3m_ago = stock.consensus_eps_3m_ago
    eps_est_next_3m_ago = stock.consensus_eps_next_3m_ago

    # 수정률 계산
    revision_current = (current_eps_est / eps_est_3m_ago - 1) * 100 if eps_est_3m_ago else 0
    revision_next = (current_eps_est_next / eps_est_next_3m_ago - 1) * 100 if eps_est_next_3m_ago else 0

    # 수정 방향
    up_revisions = stock.eps_up_revisions_3m
    down_revisions = stock.eps_down_revisions_3m

    revision_ratio = up_revisions / (up_revisions + down_revisions) if (up_revisions + down_revisions) > 0 else 0.5

    # 이익 모멘텀 점수
    if revision_ratio > 0.7 and revision_current > 5:
        earnings_momentum = "strong_positive"
        score = 0.8
    elif revision_ratio > 0.5 and revision_current > 0:
        earnings_momentum = "positive"
        score = 0.4
    elif revision_ratio < 0.3 and revision_current < -5:
        earnings_momentum = "strong_negative"
        score = -0.8
    elif revision_ratio < 0.5 and revision_current < 0:
        earnings_momentum = "negative"
        score = -0.4
    else:
        earnings_momentum = "neutral"
        score = 0

    return {
        "current_year_revision": revision_current,
        "next_year_revision": revision_next,
        "up_revisions": up_revisions,
        "down_revisions": down_revisions,
        "revision_ratio": revision_ratio,
        "earnings_momentum": earnings_momentum,
        "score": score
    }
```

---

## 3단계: 공시 센티먼트 분석

### DART 공시 분석

```python
def analyze_disclosure_sentiment(stock, days=90):
    disclosures = fetch_dart_disclosures(stock.code, days)

    positive_events = []
    negative_events = []
    neutral_events = []

    for disclosure in disclosures:
        event_type = classify_disclosure(disclosure)
        sentiment = calculate_disclosure_sentiment(disclosure)

        event = {
            "date": disclosure.date,
            "title": disclosure.title,
            "type": event_type,
            "sentiment": sentiment
        }

        if sentiment > 0.3:
            positive_events.append(event)
        elif sentiment < -0.3:
            negative_events.append(event)
        else:
            neutral_events.append(event)

    return {
        "total_disclosures": len(disclosures),
        "positive_events": positive_events,
        "negative_events": negative_events,
        "neutral_events": neutral_events,
        "net_sentiment": len(positive_events) - len(negative_events),
        "recent_material_events": get_material_events(disclosures)
    }

def classify_disclosure(disclosure):
    title = disclosure.title.lower()

    # 긍정적 공시
    if any(kw in title for kw in ["자기주식", "배당", "수주", "계약체결", "신규사업"]):
        return "positive"

    # 부정적 공시
    if any(kw in title for kw in ["소송", "분쟁", "감자", "유상증자", "횡령", "배임"]):
        return "negative"

    # 실적 관련 (별도 분석 필요)
    if any(kw in title for kw in ["영업실적", "매출", "잠정실적"]):
        return "earnings"

    # 지배구조
    if any(kw in title for kw in ["이사회", "대표이사", "임원", "주총"]):
        return "governance"

    return "other"

def calculate_disclosure_sentiment(disclosure):
    title = disclosure.title

    positive_signals = {
        "자기주식 취득": 0.7,
        "배당 결정": 0.6,
        "대규모 수주": 0.8,
        "신사업 진출": 0.5,
        "실적 개선": 0.6,
        "흑자 전환": 0.8
    }

    negative_signals = {
        "유상증자": -0.6,
        "CB 발행": -0.4,
        "소송 제기": -0.5,
        "손실 발생": -0.7,
        "감자": -0.8,
        "횡령": -0.9
    }

    sentiment = 0
    for signal, weight in positive_signals.items():
        if signal in title:
            sentiment += weight

    for signal, weight in negative_signals.items():
        if signal in title:
            sentiment += weight

    return max(-1, min(1, sentiment))
```

### 주요 이벤트 분류

```yaml
material_events:
  highly_positive:
    - "대규모 자사주 매입 공시"
    - "특별배당 결정"
    - "대형 수주 계약"
    - "M&A 완료 (시너지 기대)"

  positive:
    - "정기배당 증가"
    - "신규 사업 진출"
    - "주요 고객사 확보"
    - "R&D 성과 (특허 등록)"

  negative:
    - "유상증자 결정"
    - "CB/BW 발행"
    - "대표이사 변경 (비정상)"
    - "소송 피소"

  highly_negative:
    - "분식회계 적발"
    - "횡령/배임 혐의"
    - "상장폐지 사유 발생"
    - "대규모 손실 발생"
```

---

## 4단계: 실적 서프라이즈 분석

```python
def analyze_earnings_surprise(stock, quarters=8):
    surprises = []

    for q in range(quarters):
        actual_eps = stock.quarterly_actual_eps[q]
        estimate_eps = stock.quarterly_estimate_eps[q]

        if estimate_eps != 0:
            surprise_pct = (actual_eps - estimate_eps) / abs(estimate_eps) * 100
        else:
            surprise_pct = 0

        surprises.append({
            "quarter": stock.quarters[q],
            "actual": actual_eps,
            "estimate": estimate_eps,
            "surprise_pct": surprise_pct,
            "beat": actual_eps > estimate_eps
        })

    # 연속 beat/miss 카운트
    consecutive_beats = 0
    consecutive_misses = 0

    for s in surprises:
        if s["beat"]:
            consecutive_beats += 1
            consecutive_misses = 0
        else:
            consecutive_misses += 1
            consecutive_beats = 0

    # 평균 서프라이즈
    avg_surprise = np.mean([s["surprise_pct"] for s in surprises])

    # 시그널
    signals = []
    if consecutive_beats >= 4:
        signals.append({"type": "consistent_beater", "quarters": consecutive_beats})
    if consecutive_misses >= 2:
        signals.append({"type": "consistent_misser", "quarters": consecutive_misses})
    if avg_surprise > 5:
        signals.append({"type": "avg_positive_surprise", "value": avg_surprise})

    return {
        "surprises": surprises,
        "avg_surprise": avg_surprise,
        "consecutive_beats": consecutive_beats,
        "consecutive_misses": consecutive_misses,
        "beat_rate": len([s for s in surprises if s["beat"]]) / len(surprises),
        "signals": signals
    }
```

---

## 5단계: 종합 센티먼트 점수

### Sentiment Score 산출

```python
def calculate_total_sentiment_score(stock):
    # 뉴스 센티먼트 (30%)
    news = analyze_news_sentiment(stock)
    news_score = (news["weighted_sentiment"] + 1) / 2 * 100  # 0-100 스케일

    # 애널리스트 센티먼트 (35%)
    analyst = analyze_analyst_sentiment(stock)
    target_price = analyze_target_price(stock)
    earnings_rev = analyze_earnings_revision(stock)

    analyst_score = (
        0.30 * ((analyst["consensus_score"] + 2) / 4 * 100) +
        0.30 * (min(max(target_price["upside_to_avg"], -30), 50) + 30) / 80 * 100 +
        0.40 * ((earnings_rev["score"] + 1) / 2 * 100)
    )

    # 공시 센티먼트 (20%)
    disclosure = analyze_disclosure_sentiment(stock)
    disclosure_score = 50 + disclosure["net_sentiment"] * 10

    # 실적 서프라이즈 (15%)
    surprise = analyze_earnings_surprise(stock)
    surprise_score = 50 + surprise["avg_surprise"] * 2

    # 종합 점수
    total_score = (
        0.30 * news_score +
        0.35 * analyst_score +
        0.20 * disclosure_score +
        0.15 * surprise_score
    )

    # 센티먼트 등급
    if total_score > 70:
        sentiment_grade = "Very Bullish"
    elif total_score > 55:
        sentiment_grade = "Bullish"
    elif total_score > 45:
        sentiment_grade = "Neutral"
    elif total_score > 30:
        sentiment_grade = "Bearish"
    else:
        sentiment_grade = "Very Bearish"

    return {
        "total_score": total_score,
        "sentiment_grade": sentiment_grade,
        "breakdown": {
            "news": news_score,
            "analyst": analyst_score,
            "disclosure": disclosure_score,
            "surprise": surprise_score
        },
        "key_drivers": identify_key_drivers(news, analyst, disclosure, surprise)
    }

def identify_key_drivers(news, analyst, disclosure, surprise):
    drivers = []

    if news["volume_signal"] == "surge":
        drivers.append("뉴스 관심도 급증")

    if analyst["rating_momentum"] > 0.3:
        drivers.append("애널리스트 의견 상향 추세")
    elif analyst["rating_momentum"] < -0.3:
        drivers.append("애널리스트 의견 하향 추세")

    if disclosure["positive_events"]:
        drivers.append(f"긍정적 공시 {len(disclosure['positive_events'])}건")

    if surprise["consecutive_beats"] >= 3:
        drivers.append(f"실적 {surprise['consecutive_beats']}분기 연속 beat")

    return drivers
```

---

## 출력 형식

### sentiment_analysis/{stock_code}.json

```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "analysis_date": "2025-01-31",
  "sentiment_score": {
    "total": 68,
    "grade": "Bullish",
    "breakdown": {
      "news": 65,
      "analyst": 72,
      "disclosure": 60,
      "surprise": 75
    }
  },
  "news_sentiment": {
    "weighted_sentiment": 0.35,
    "news_volume": 150,
    "volume_signal": "above_normal",
    "positive_ratio": 0.55,
    "recent_headlines": [
      {
        "date": "2025-01-30",
        "headline": "삼성전자, AI 반도체 수주 확대 기대",
        "sentiment": 0.7
      }
    ]
  },
  "analyst_sentiment": {
    "consensus": "Buy",
    "consensus_score": 1.2,
    "rating_distribution": {
      "strong_buy": 5,
      "buy": 20,
      "hold": 8,
      "sell": 2
    },
    "avg_target_price": 85000,
    "upside_to_target": 30.8
  },
  "earnings_revision": {
    "current_year_revision": 8.5,
    "revision_ratio": 0.72,
    "earnings_momentum": "positive"
  },
  "disclosure_sentiment": {
    "total_disclosures": 12,
    "material_events": [
      {
        "date": "2025-01-15",
        "title": "자기주식 취득 신탁계약 체결",
        "sentiment": "positive"
      }
    ]
  },
  "key_drivers": [
    "애널리스트 의견 상향 추세",
    "실적 4분기 연속 beat"
  ]
}
```

### sentiment_scores.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "summary": {
    "avg_sentiment_score": 52,
    "bullish_count": 30,
    "neutral_count": 45,
    "bearish_count": 25
  },
  "top_bullish": [
    {
      "code": "005930",
      "name": "삼성전자",
      "score": 68,
      "key_driver": "애널리스트 의견 상향"
    }
  ],
  "top_bearish": [
    {
      "code": "000720",
      "name": "현대건설",
      "score": 32,
      "key_driver": "PF 관련 부정적 뉴스"
    }
  ],
  "sector_sentiment": {
    "IT": 62,
    "금융": 48,
    "헬스케어": 55
  }
}
```

---

## 다음 단계

센티먼트 분석 결과를 `00_master_orchestrator`로 전달하여 종합 투자 의견 도출에 활용합니다.
