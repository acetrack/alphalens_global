# Agent 06: Technical Agent (기술적 분석 에이전트)

## 역할

가격 차트, 거래량, 기술적 지표를 분석하여 매매 타이밍과 추세를 파악합니다. 펀더멘털 분석과 기술적 분석을 결합하여 진입/청산 시점에 대한 인사이트를 제공합니다.

## 입력

- `screened_stocks.json`: 스크리닝 결과
- 가격/거래량 데이터 (일봉, 주봉, 월봉)
- 수급 데이터 (외국인, 기관, 개인)

## 출력

- `technical_analysis/`: 종목별 기술적 분석
- `technical_signals.json`: 기술적 시그널 요약

---

## ⚠️ 필수: 현재 날짜 확인

**분석 시작 전 반드시 현재 날짜를 확인하세요.**

```yaml
date_validation:
  required: true
  technical_context:
    # 현재가 2026년 2월 1일이라면:
    analysis_date: "2026-02-01"
    price_data_end: "2026-01-31"   # 가장 최근 거래일
    lookback_periods:
      daily: 120    # 최근 120거래일
      weekly: 52    # 최근 52주
      monthly: 36   # 최근 36개월

  search_keywords:
    - "{company} 주가 차트 {current_year}년 {current_month}월"
    - "{company} 외국인 기관 매매 동향 {current_year}"
    - "{company} 기술적 분석 {current_year}"
    - "{company} 이동평균선 {current_date}"
```

---

## ⚠️ 필수: 주가 데이터 신선도 검증

**기술적 분석에서 주가 데이터의 신선도는 매우 중요합니다.**

```yaml
data_freshness:
  required: true
  price_data_rules:
    # 주가 데이터 허용 기준
    max_age_days: 3        # 최대 3일 전 데이터까지 허용
    warning_threshold: 1   # 1일 이상이면 경고

    # 검색 우선순위
    search_priority:
      - "{company} 현재가 실시간"
      - "{company} 주가 오늘"
      - "{company} 최근 종가"
      - "{company} 주가 {current_year}년 {current_month}월"

    # 데이터 출처 우선순위
    source_priority:
      - "네이버 금융 실시간"
      - "다음 금융 실시간"
      - "한국거래소 종가"
      - "증권사 HTS/MTS"

  validation_steps:
    1: "검색 결과에서 주가 데이터의 날짜를 확인"
    2: "분석일과 데이터일 간의 차이(일수) 계산"
    3: "차이가 1일 이상이면 리포트에 경고 표시"
    4: "차이가 3일 이상이면 재검색 시도"

  report_format: |
    ## 주가 데이터 기준일 안내

    | 항목 | 값 | 비고 |
    |------|-----|-----|
    | 분석 기준일 | {analysis_date} | 오늘 |
    | 주가 데이터 | {price_date} | {days_diff}일 전 |
    | 현재가 | {current_price}원 | {freshness_status} |

    {warning_message}

  warning_templates:
    fresh: ""  # 0-1일: 경고 없음
    stale: |
      > ⚠️ **주의**: 주가 데이터가 {days_diff}일 전 기준입니다.
      > 실제 투자 결정 시 최신 시세를 확인하세요.
    very_stale: |
      > 🚨 **경고**: 주가 데이터가 {days_diff}일 전으로 매우 오래되었습니다.
      > 본 분석의 기술적 지표는 참고용으로만 활용하고,
      > 반드시 최신 차트와 시세를 직접 확인하세요.
```

### 신선도 상태 표시 기준

| 차이(일) | 상태 | 표시 | 조치 |
|---------|------|------|------|
| 0~1일 | 최신 | ✅ | 정상 분석 |
| 2~3일 | 주의 | ⚠️ | 경고 표시 |
| 4~7일 | 오래됨 | ⚠️⚠️ | 강력 경고 + 재검색 권고 |
| 7일+ | 매우 오래됨 | 🚨 | 분석 신뢰도 낮음 명시 |

---

## 기술적 분석 체계

```
┌─────────────────────────────────────────────────────────────┐
│               Technical Analysis Framework                   │
└─────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  Price Action   │
                    │  가격 움직임     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Trend          │ │  Momentum       │ │  Volume         │
│  추세 분석       │ │  모멘텀 분석     │ │  거래량 분석     │
│  - 이동평균     │ │  - RSI          │ │  - OBV          │
│  - MACD        │ │  - Stochastic   │ │  - Volume MA    │
│  - ADX         │ │  - CCI          │ │  - MFI          │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Supply/Demand  │
                    │  수급 분석       │
                    │  - 외국인       │
                    │  - 기관         │
                    │  - 공매도       │
                    └─────────────────┘
```

---

## 1단계: 추세 분석 (Trend Analysis)

### 이동평균선 (Moving Averages)

| 이동평균 | 기간 | 용도 |
|----------|------|------|
| **MA5** | 5일 | 초단기 추세 |
| **MA20** | 20일 | 단기 추세 |
| **MA60** | 60일 | 중기 추세 |
| **MA120** | 120일 | 장기 추세 |
| **MA200** | 200일 | 초장기 추세 |

#### 골든크로스 / 데드크로스

```
┌─────────────────────────────────────────────────────────────┐
│              Golden Cross / Death Cross                      │
└─────────────────────────────────────────────────────────────┘

        Golden Cross                    Death Cross
        (매수 신호)                      (매도 신호)

           MA20                            MA20
            │  ╲                            │  ╱
            │   ╲                           │ ╱
            │    ╲                          │╱
            │     ╲                        ╱│
            │      ╲                      ╱ │
   MA60 ────┼───────╳───────    MA60 ────╳──┼────────
            │      ╱ ╲                    ╲ │
            │     ╱   ╲                    ╲│
            │    ╱     ╲                    │╲
            │   ╱       ╲                   │ ╲
            │  ╱         ╲                  │  ╲
```

```python
def moving_average_analysis(stock, prices):
    ma_periods = [5, 20, 60, 120, 200]
    mas = {}

    for period in ma_periods:
        mas[f"ma{period}"] = calculate_ma(prices, period)

    # 현재가와 이동평균 비교
    current_price = prices[-1]
    ma_positions = {}

    for period in ma_periods:
        ma_value = mas[f"ma{period}"][-1]
        ma_positions[f"ma{period}"] = {
            "value": ma_value,
            "vs_price": (current_price / ma_value - 1) * 100,
            "position": "above" if current_price > ma_value else "below"
        }

    # 골든크로스/데드크로스 체크
    signals = []
    if mas["ma20"][-1] > mas["ma60"][-1] and mas["ma20"][-2] <= mas["ma60"][-2]:
        signals.append({"type": "golden_cross", "mas": "20/60", "strength": "strong"})
    if mas["ma20"][-1] < mas["ma60"][-1] and mas["ma20"][-2] >= mas["ma60"][-2]:
        signals.append({"type": "death_cross", "mas": "20/60", "strength": "strong"})

    # 정배열/역배열
    if mas["ma20"][-1] > mas["ma60"][-1] > mas["ma120"][-1]:
        arrangement = "bullish_aligned"  # 정배열
    elif mas["ma20"][-1] < mas["ma60"][-1] < mas["ma120"][-1]:
        arrangement = "bearish_aligned"  # 역배열
    else:
        arrangement = "mixed"

    return {
        "moving_averages": ma_positions,
        "signals": signals,
        "arrangement": arrangement,
        "trend": "uptrend" if arrangement == "bullish_aligned" else "downtrend" if arrangement == "bearish_aligned" else "sideways"
    }
```

### MACD (Moving Average Convergence Divergence)

$$
MACD = EMA_{12} - EMA_{26}
$$
$$
Signal = EMA_9(MACD)
$$
$$
Histogram = MACD - Signal
$$

```python
def macd_analysis(prices):
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)

    macd = ema12 - ema26
    signal = calculate_ema(macd, 9)
    histogram = macd - signal

    # 시그널 판단
    current_macd = macd[-1]
    current_signal = signal[-1]
    current_hist = histogram[-1]
    prev_hist = histogram[-2]

    signals = []

    # MACD 크로스
    if current_macd > current_signal and macd[-2] <= signal[-2]:
        signals.append({"type": "macd_bullish_cross", "strength": "moderate"})
    if current_macd < current_signal and macd[-2] >= signal[-2]:
        signals.append({"type": "macd_bearish_cross", "strength": "moderate"})

    # 히스토그램 전환
    if current_hist > 0 and prev_hist <= 0:
        signals.append({"type": "histogram_bullish", "strength": "weak"})
    if current_hist < 0 and prev_hist >= 0:
        signals.append({"type": "histogram_bearish", "strength": "weak"})

    # 다이버전스
    divergence = check_divergence(prices, macd)

    return {
        "macd": current_macd,
        "signal": current_signal,
        "histogram": current_hist,
        "signals": signals,
        "divergence": divergence
    }
```

### ADX (Average Directional Index)

| ADX 값 | 해석 |
|--------|------|
| 0-20 | 추세 없음 (횡보) |
| 20-40 | 추세 시작/약한 추세 |
| 40-60 | 강한 추세 |
| 60+ | 매우 강한 추세 |

---

## 2단계: 모멘텀 분석 (Momentum Analysis)

### RSI (Relative Strength Index)

$$
RSI = 100 - \frac{100}{1 + RS}
$$
$$
RS = \frac{Average\,Gain}{Average\,Loss}
$$

```yaml
rsi_interpretation:
  overbought: "> 70"      # 과매수
  neutral: "30 ~ 70"      # 중립
  oversold: "< 30"        # 과매도

  signals:
    - "RSI 30 이하에서 반등: 매수 신호"
    - "RSI 70 이상에서 하락: 매도 신호"
    - "RSI 다이버전스: 추세 전환 가능성"
```

```python
def rsi_analysis(prices, period=14):
    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = calculate_ema(gains, period)
    avg_loss = calculate_ema(losses, period)

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    current_rsi = rsi[-1]

    # 시그널
    status = "neutral"
    signal = None

    if current_rsi > 70:
        status = "overbought"
        if rsi[-2] <= 70:
            signal = {"type": "rsi_overbought_entry", "action": "caution"}
    elif current_rsi < 30:
        status = "oversold"
        if rsi[-2] >= 30:
            signal = {"type": "rsi_oversold_entry", "action": "watch_for_bounce"}

    # 다이버전스 체크
    divergence = check_rsi_divergence(prices, rsi)

    return {
        "rsi": current_rsi,
        "status": status,
        "signal": signal,
        "divergence": divergence
    }
```

### Stochastic Oscillator

$$
\%K = \frac{Close - Low_{14}}{High_{14} - Low_{14}} \times 100
$$
$$
\%D = SMA_3(\%K)
$$

```python
def stochastic_analysis(prices, highs, lows, k_period=14, d_period=3):
    stoch_k = []
    for i in range(k_period-1, len(prices)):
        low_min = min(lows[i-k_period+1:i+1])
        high_max = max(highs[i-k_period+1:i+1])
        k = (prices[i] - low_min) / (high_max - low_min) * 100
        stoch_k.append(k)

    stoch_d = calculate_sma(stoch_k, d_period)

    current_k = stoch_k[-1]
    current_d = stoch_d[-1]

    # 시그널
    signals = []
    if current_k < 20 and current_d < 20:
        signals.append({"type": "stoch_oversold", "strength": "moderate"})
    if current_k > 80 and current_d > 80:
        signals.append({"type": "stoch_overbought", "strength": "moderate"})

    # %K와 %D 크로스
    if current_k > current_d and stoch_k[-2] <= stoch_d[-2]:
        signals.append({"type": "stoch_bullish_cross", "strength": "weak"})

    return {
        "stoch_k": current_k,
        "stoch_d": current_d,
        "signals": signals
    }
```

---

## 3단계: 변동성 분석 (Volatility Analysis)

### Bollinger Bands

$$
Upper\,Band = MA_{20} + 2\sigma
$$
$$
Lower\,Band = MA_{20} - 2\sigma
$$

```python
def bollinger_bands_analysis(prices, period=20, std_dev=2):
    ma = calculate_sma(prices, period)
    std = calculate_rolling_std(prices, period)

    upper = ma + std_dev * std
    lower = ma - std_dev * std

    current_price = prices[-1]
    current_upper = upper[-1]
    current_lower = lower[-1]
    current_ma = ma[-1]

    # Bandwidth
    bandwidth = (current_upper - current_lower) / current_ma * 100

    # %B (현재가 위치)
    percent_b = (current_price - current_lower) / (current_upper - current_lower) * 100

    # 시그널
    signals = []
    if current_price >= current_upper:
        signals.append({"type": "bb_upper_touch", "action": "potential_reversal_down"})
    if current_price <= current_lower:
        signals.append({"type": "bb_lower_touch", "action": "potential_reversal_up"})
    if bandwidth < 10:  # 밴드 수축
        signals.append({"type": "bb_squeeze", "action": "volatility_expansion_expected"})

    return {
        "upper": current_upper,
        "middle": current_ma,
        "lower": current_lower,
        "bandwidth": bandwidth,
        "percent_b": percent_b,
        "signals": signals
    }
```

### ATR (Average True Range)

```python
def atr_analysis(prices, highs, lows, period=14):
    true_ranges = []
    for i in range(1, len(prices)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - prices[i-1]),
            abs(lows[i] - prices[i-1])
        )
        true_ranges.append(tr)

    atr = calculate_ema(true_ranges, period)
    current_atr = atr[-1]

    # 변동성 수준
    atr_percent = current_atr / prices[-1] * 100

    volatility_level = "low" if atr_percent < 2 else "moderate" if atr_percent < 4 else "high"

    return {
        "atr": current_atr,
        "atr_percent": atr_percent,
        "volatility_level": volatility_level
    }
```

---

## 4단계: 거래량 분석 (Volume Analysis)

### OBV (On-Balance Volume)

```python
def obv_analysis(prices, volumes):
    obv = [0]
    for i in range(1, len(prices)):
        if prices[i] > prices[i-1]:
            obv.append(obv[-1] + volumes[i])
        elif prices[i] < prices[i-1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])

    # OBV 추세
    obv_ma = calculate_sma(obv, 20)

    # 가격-OBV 다이버전스
    divergence = check_price_obv_divergence(prices, obv)

    return {
        "obv": obv[-1],
        "obv_ma": obv_ma[-1],
        "obv_trend": "rising" if obv[-1] > obv_ma[-1] else "falling",
        "divergence": divergence
    }
```

### 거래량 이동평균

```python
def volume_analysis(volumes, period=20):
    vol_ma = calculate_sma(volumes, period)
    current_vol = volumes[-1]
    avg_vol = vol_ma[-1]

    volume_ratio = current_vol / avg_vol

    # 거래량 급증/급감
    if volume_ratio > 2:
        status = "surge"  # 거래량 급증
    elif volume_ratio > 1.5:
        status = "above_average"
    elif volume_ratio < 0.5:
        status = "very_low"
    else:
        status = "normal"

    return {
        "current_volume": current_vol,
        "average_volume": avg_vol,
        "volume_ratio": volume_ratio,
        "status": status
    }
```

---

## 5단계: 수급 분석 (Supply/Demand Analysis)

### 투자자별 매매 동향

```python
def investor_flow_analysis(stock, days=20):
    foreign_net = stock.foreign_net_buy(days)  # 외국인 순매수
    inst_net = stock.institutional_net_buy(days)  # 기관 순매수
    retail_net = stock.retail_net_buy(days)  # 개인 순매수

    # 누적 순매수
    foreign_cum = sum(foreign_net)
    inst_cum = sum(inst_net)
    retail_cum = sum(retail_net)

    # 최근 추세
    foreign_recent = sum(foreign_net[-5:])
    inst_recent = sum(inst_net[-5:])

    # 수급 신호
    signals = []
    if foreign_cum > 0 and inst_cum > 0:
        signals.append({
            "type": "smart_money_buying",
            "description": "외국인+기관 동반 순매수",
            "strength": "strong"
        })
    if foreign_cum < 0 and inst_cum < 0:
        signals.append({
            "type": "smart_money_selling",
            "description": "외국인+기관 동반 순매도",
            "strength": "strong"
        })

    return {
        "foreign": {
            "cumulative": foreign_cum,
            "recent_5d": foreign_recent,
            "trend": "buying" if foreign_recent > 0 else "selling"
        },
        "institutional": {
            "cumulative": inst_cum,
            "recent_5d": inst_recent,
            "trend": "buying" if inst_recent > 0 else "selling"
        },
        "retail": {
            "cumulative": retail_cum,
            "trend": "buying" if retail_cum > 0 else "selling"
        },
        "signals": signals
    }
```

### 공매도 분석

```python
def short_interest_analysis(stock):
    short_volume = stock.short_volume
    total_volume = stock.trading_volume
    shares_outstanding = stock.shares_outstanding

    # 공매도 비율
    short_ratio = short_volume / total_volume * 100

    # Days to Cover
    days_to_cover = stock.short_interest / stock.avg_daily_volume

    # 신호
    signals = []
    if short_ratio > 20:
        signals.append({
            "type": "high_short_interest",
            "implication": "short_squeeze_potential"
        })
    if days_to_cover > 5:
        signals.append({
            "type": "extended_days_to_cover",
            "implication": "covering_pressure"
        })

    return {
        "short_ratio": short_ratio,
        "days_to_cover": days_to_cover,
        "signals": signals
    }
```

---

## 6단계: 종합 기술적 점수

### Technical Score 산출

```python
def calculate_technical_score(stock):
    # 추세 점수 (30%)
    ma_analysis = moving_average_analysis(stock)
    macd_result = macd_analysis(stock.prices)

    trend_score = 50  # 기본 점수
    if ma_analysis["arrangement"] == "bullish_aligned":
        trend_score += 30
    elif ma_analysis["arrangement"] == "bearish_aligned":
        trend_score -= 30

    for signal in ma_analysis["signals"]:
        if signal["type"] == "golden_cross":
            trend_score += 20
        elif signal["type"] == "death_cross":
            trend_score -= 20

    # 모멘텀 점수 (30%)
    rsi = rsi_analysis(stock.prices)
    stoch = stochastic_analysis(stock.prices, stock.highs, stock.lows)

    momentum_score = 50
    if rsi["status"] == "oversold":
        momentum_score += 25  # 반등 기대
    elif rsi["status"] == "overbought":
        momentum_score -= 15  # 조정 경계

    # 거래량 점수 (20%)
    vol = volume_analysis(stock.volumes)
    obv = obv_analysis(stock.prices, stock.volumes)

    volume_score = 50
    if vol["status"] == "surge" and stock.price_change > 0:
        volume_score += 25  # 거래량 수반 상승
    if obv["obv_trend"] == "rising":
        volume_score += 15

    # 수급 점수 (20%)
    flow = investor_flow_analysis(stock)

    supply_demand_score = 50
    if flow["foreign"]["trend"] == "buying" and flow["institutional"]["trend"] == "buying":
        supply_demand_score += 30

    # 종합
    total_score = (
        0.30 * trend_score +
        0.30 * momentum_score +
        0.20 * volume_score +
        0.20 * supply_demand_score
    )

    return {
        "total_score": total_score,
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "volume_score": volume_score,
        "supply_demand_score": supply_demand_score,
        "signal": "bullish" if total_score > 65 else "bearish" if total_score < 35 else "neutral"
    }
```

---

## 출력 형식

### technical_analysis/{stock_code}.json

```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "analysis_date": "2025-01-31",
  "current_price": 65000,
  "technical_score": {
    "total": 68,
    "trend": 72,
    "momentum": 65,
    "volume": 70,
    "supply_demand": 62
  },
  "trend_analysis": {
    "arrangement": "bullish_aligned",
    "ma_positions": {
      "ma20": {"value": 63500, "vs_price": 2.4},
      "ma60": {"value": 61000, "vs_price": 6.6},
      "ma120": {"value": 58000, "vs_price": 12.1}
    },
    "macd": {
      "value": 850,
      "signal": 720,
      "histogram": 130,
      "trend": "bullish"
    }
  },
  "momentum": {
    "rsi_14": 58,
    "stochastic_k": 65,
    "status": "neutral"
  },
  "volume": {
    "current_vs_avg": 1.35,
    "obv_trend": "rising"
  },
  "supply_demand": {
    "foreign_20d": 125000000000,
    "institutional_20d": 85000000000,
    "short_ratio": 8.5
  },
  "signals": [
    {
      "type": "golden_cross",
      "description": "MA20이 MA60을 상향 돌파",
      "strength": "strong",
      "action": "bullish"
    }
  ],
  "recommendation": {
    "timing": "favorable",
    "action": "accumulate_on_dips"
  }
}
```

### technical_signals.json

```json
{
  "generated_at": "2025-01-31T12:00:00Z",
  "signal_summary": {
    "bullish_stocks": 35,
    "bearish_stocks": 20,
    "neutral_stocks": 45
  },
  "top_bullish": [
    {
      "code": "005930",
      "name": "삼성전자",
      "score": 78,
      "key_signals": ["golden_cross", "foreign_buying"]
    }
  ],
  "top_bearish": [
    {
      "code": "000660",
      "name": "SK하이닉스",
      "score": 32,
      "key_signals": ["death_cross", "rsi_overbought"]
    }
  ]
}
```

---

## 다음 단계

기술적 분석 결과를 `07_risk_agent`와 `00_master_orchestrator`로 전달하여 종합 투자 의견 도출에 활용합니다.
