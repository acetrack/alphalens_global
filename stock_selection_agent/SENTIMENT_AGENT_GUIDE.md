# Sentiment Agent 사용 가이드

## 개요

Sentiment Agent는 주식의 시장 센티먼트를 분석하는 에이전트입니다. 뉴스, 애널리스트 의견, 공시, 실적 서프라이즈를 종합하여 0-100점의 센티먼트 점수를 산출합니다.

## 데이터 소스

### 1. 뉴스 센티먼트 (30%) ✅
- **데이터 소스**: 구글 RSS 피드 (실제 데이터)
- **분석 방법**: 한국어 금융 키워드 사전 기반 감성 분석
- **수집 기간**: 최근 30일
- **상태**: 정상 작동 중

### 2. 애널리스트 센티먼트 (35%) ✅
- **데이터 소스**: 이베스트투자증권 xingAPI Plus (실제 데이터)
- **수집 데이터**:
  - 투자의견 분포 (BUY/HOLD/SELL)
  - 목표주가 컨센서스
  - 증권사별 리포트
- **Fallback**: 네이버 금융 크롤링
- **상태**: 정상 작동 중 ✅

### 3. 공시 센티먼트 (20%) ✅
- **데이터 소스**: DART API (실제 데이터)
- **분석 항목**: 긍정/부정 공시 분류
- **수집 기간**: 최근 90일
- **상태**: 정상 작동 중

### 4. 실적 서프라이즈 (15%) ⚠️
- **데이터 소스**: 네이버 금융 크롤링 (fallback)
- **수집 데이터**: 분기별 EPS (actual vs estimate)
- **상태**: Fallback으로 작동 중 (eBest TR 코드 미확인)

## 설치

### 1. 필수 라이브러리 설치

```bash
pip install -r requirements.txt
```

주요 라이브러리:
- `requests`: HTTP 요청
- `beautifulsoup4`: 웹 크롤링
- `lxml`: HTML 파싱
- `feedparser`: RSS 피드 파싱
- `pandas`, `numpy`: 데이터 처리

### 2. DART API 키 발급 (선택적, 향후 사용)

1. https://opendart.fss.or.kr 접속
2. 회원가입 후 API 키 신청
3. 환경 변수 또는 설정 파일에 저장

```bash
export DART_API_KEY="your_api_key_here"
```

## 사용법

### 기본 사용

```python
from src.agents import SentimentAgent
from src.api.krx_client import KrxClient

# 1. KRX 클라이언트 초기화
krx_client = KrxClient()

# 2. Sentiment Agent 초기화
agent = SentimentAgent(krx_client=krx_client)

# 3. 분석 실행
result = agent.analyze(
    stock_code="005930",  # 삼성전자
    current_price=65000   # 현재주가 (옵션)
)

# 4. 결과 확인
print(f"센티먼트 점수: {result.total_score:.1f}/100")
print(f"센티먼트 등급: {result.sentiment_grade}")
print(f"투자 시그널: {result.investment_signal}")
print(f"주요 동인: {result.key_drivers}")
```

### 고급 설정

```python
from src.agents import SentimentAgent, SentimentAnalysisConfig

# 커스텀 설정
config = SentimentAnalysisConfig(
    news_weight=0.35,              # 뉴스 가중치 조정
    analyst_weight=0.30,           # 애널리스트 가중치 조정
    news_lookback_days=14,         # 뉴스 수집 기간 단축
    analyst_lookback_days=60       # 애널리스트 데이터 기간 단축
)

agent = SentimentAgent(krx_client=krx_client, config=config)
result = agent.analyze("005930")
```

### Master Orchestrator와 함께 사용

```python
from src.agents import MasterOrchestrator, OrchestratorConfig

# 오케스트레이터 설정
config = OrchestratorConfig(
    dart_api_key="your_dart_key"  # 선택적
)

orchestrator = MasterOrchestrator(config=config)

# 전체 분석 (센티먼트 포함)
result = orchestrator.analyze_stock("005930")

# 센티먼트 점수는 Conviction Score에 10% 반영됨
print(f"Conviction Score: {result.conviction_score}")
for score in result.agent_scores:
    if score.agent_name == "Sentiment Agent":
        print(f"센티먼트: {score.score:.1f} (가중치: {score.weight})")
```

## 출력 결과 구조

### SentimentAnalysisResult

```python
@dataclass
class SentimentAnalysisResult:
    # 기본 정보
    stock_code: str                    # 종목코드
    stock_name: str                    # 종목명
    analysis_date: str                 # 분석일

    # 종합 점수
    total_score: float                 # 0-100점
    sentiment_grade: str               # Very Bullish/Bullish/Neutral/Bearish/Very Bearish
    investment_signal: str             # strong_buy/buy/hold/sell/strong_sell

    # 세부 점수
    news_score: float                  # 뉴스 점수
    analyst_score: float               # 애널리스트 점수
    disclosure_score: float            # 공시 점수
    earnings_surprise_score: float     # 실적 서프라이즈 점수

    # 뉴스 센티먼트
    news_weighted_sentiment: float     # -1.0 ~ 1.0
    news_volume: int                   # 뉴스 개수
    news_volume_signal: str            # surge/above_normal/normal
    recent_headlines: List             # 최근 헤드라인 목록

    # 애널리스트 센티먼트
    analyst_consensus: str             # Buy/Hold/Sell
    consensus_score: float             # -2.0 ~ 2.0
    rating_distribution: Dict          # 의견 분포
    avg_target_price: int              # 평균 목표주가
    upside_to_avg: float               # 상승여력 %

    # 공시/실적
    material_events: List              # 주요 공시
    earnings_surprises: List           # 실적 서프라이즈 내역

    # 주요 동인
    key_drivers: List[str]             # 센티먼트 주요 동인 (최대 5개)
```

## 센티먼트 등급 기준

| 점수 범위 | 등급 | 투자 시그널 | 의미 |
|----------|------|------------|------|
| 75+ | Very Bullish | Strong Buy | 매우 긍정적 |
| 60-75 | Bullish | Buy | 긍정적 |
| 40-60 | Neutral | Hold | 중립 |
| 25-40 | Bearish | Sell | 부정적 |
| 0-25 | Very Bearish | Strong Sell | 매우 부정적 |

## 주의사항

### 1. 데이터 품질

현재 버전의 데이터 수집 방식:

| 항목 | 상태 | 데이터 소스 | 가중치 |
|-----|------|-----------|--------|
| 뉴스 | ✅ 작동 중 | 구글 RSS | 30% |
| 애널리스트 | ✅ 작동 중 | 이베스트 xingAPI Plus (t3401) | 35% |
| 공시 | ✅ 작동 중 | DART API | 20% |
| 실적 | ⚠️ Fallback | 네이버 금융 크롤링 | 15% |

**현재는 실제 데이터만 사용하여 센티먼트 분석을 수행합니다 (Mock 데이터 제거됨).**

### 2. 크롤링 주의사항

- **속도 제한**: 네이버 금융 크롤링 시 과도한 요청 방지 필요
- **User-Agent**: 크롤링 시 적절한 User-Agent 사용
- **법적 고려**: 웹 크롤링은 사이트 이용약관 확인 필요

### 3. Fallback 메커니즘

라이브러리가 설치되지 않았거나 크롤링 실패 시 자동으로 Mock 데이터로 전환됩니다:

```python
# feedparser 미설치 시
if not FEEDPARSER_AVAILABLE:
    logger.warning("feedparser not installed, using mock data")
    return self._get_mock_news()
```

### 4. 향후 개선 사항

- [ ] DART API 완전 연동
- [ ] 네이버 컨센서스 EPS 크롤링 고도화
- [ ] 증권사 리포트 PDF 파싱
- [ ] LLM 기반 뉴스 감성 분석
- [ ] 소셜 미디어 센티먼트 추가

## 테스트

```bash
# 테스트 스크립트 실행
python3 test_sentiment_agent.py
```

테스트 스크립트는 다음을 검증합니다:
- 기본 분석 실행
- 모든 세부 항목 출력
- 여러 종목 동시 분석

## 문제 해결

### ImportError: No module named 'feedparser'

```bash
pip install feedparser
```

### ImportError: No module named 'bs4'

```bash
pip install beautifulsoup4 lxml
```

### 크롤링 실패 (HTTP 403/429)

- User-Agent 변경
- 요청 간격 증가 (`time.sleep()` 추가)
- VPN 사용 고려

### Mock 데이터만 반환됨

1. 필수 라이브러리 설치 확인
2. 네트워크 연결 확인
3. 로그 확인: `logging.DEBUG` 레벨로 상세 로그 출력

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 라이선스

Internal Use Only

## 문의

프로젝트 이슈: https://github.com/your-repo/issues
