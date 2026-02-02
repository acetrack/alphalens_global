"""
Sentiment Agent - 센티먼트 분석 에이전트
뉴스, 공시, 애널리스트 의견, 소셜 미디어 등 비정형 데이터를 분석하여 시장 센티먼트를 파악
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import re
import time
from urllib.parse import quote

from ..api.krx_client import KrxClient
from ..api.dart_client import DartClient
from ..api.ebest_client import EbestClient

# 외부 라이브러리 (선택적 import)
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class SentimentAnalysisConfig:
    """센티먼트 분석 설정"""
    # 가중치 (실제 데이터 사용)
    news_weight: float = 0.30  # 뉴스 센티먼트 (구글 RSS)
    analyst_weight: float = 0.35  # 애널리스트 센티먼트 (이베스트 xingAPI Plus)
    disclosure_weight: float = 0.20  # 공시 센티먼트 (DART API)
    earnings_surprise_weight: float = 0.15  # 실적 서프라이즈 (네이버 금융 fallback)

    # 뉴스 설정
    news_lookback_days: int = 30
    news_volume_threshold: float = 1.5  # 평균 대비 배수

    # 애널리스트 설정
    analyst_lookback_days: int = 90
    target_price_significant_upside: float = 30.0  # 목표가 업사이드 %
    eps_revision_threshold: float = 5.0  # EPS 수정률 임계값 %

    # 공시 설정
    disclosure_lookback_days: int = 90

    # 실적 서프라이즈
    earnings_quarters: int = 8
    consecutive_beats_threshold: int = 3


@dataclass
class NewsArticle:
    """뉴스 기사"""
    date: str
    source: str
    headline: str
    body: Optional[str] = None
    sentiment: float = 0.0  # -1.0 ~ 1.0
    relevance: float = 1.0  # 0.0 ~ 1.0


@dataclass
class AnalystRating:
    """애널리스트 투자의견"""
    date: str
    firm: str
    rating: str  # "Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"
    target_price: Optional[int] = None


@dataclass
class Disclosure:
    """공시 정보"""
    date: str
    title: str
    disclosure_type: str
    sentiment: float = 0.0  # -1.0 ~ 1.0


@dataclass
class EarningsSurprise:
    """실적 서프라이즈"""
    quarter: str
    actual_eps: float
    estimate_eps: float
    surprise_pct: float
    beat: bool


@dataclass
class SentimentAnalysisResult:
    """센티먼트 분석 결과"""
    stock_code: str
    stock_name: str
    analysis_date: str

    # 종합 센티먼트 점수 (0-100)
    total_score: float = 50.0
    sentiment_grade: str = "Neutral"  # "Very Bullish", "Bullish", "Neutral", "Bearish", "Very Bearish"

    # 세부 점수 (0-100)
    news_score: float = 50.0
    analyst_score: float = 50.0
    disclosure_score: float = 50.0
    earnings_surprise_score: float = 50.0

    # 뉴스 센티먼트
    news_weighted_sentiment: Optional[float] = None  # -1.0 ~ 1.0
    news_volume: int = 0
    news_volume_signal: str = "normal"  # "surge", "above_normal", "normal"
    positive_news_count: int = 0
    negative_news_count: int = 0
    recent_headlines: List[Dict[str, Any]] = field(default_factory=list)

    # 애널리스트 센티먼트
    analyst_consensus: str = "Hold"
    consensus_score: float = 0.0  # -2.0 ~ 2.0
    rating_distribution: Dict[str, int] = field(default_factory=dict)
    total_analysts: int = 0
    rating_momentum: float = 0.0  # -1.0 ~ 1.0
    upgrades_3m: int = 0
    downgrades_3m: int = 0

    # 목표주가
    current_price: Optional[int] = None
    avg_target_price: Optional[int] = None
    median_target_price: Optional[int] = None
    upside_to_avg: Optional[float] = None
    target_price_change_3m: Optional[float] = None

    # 이익 추정치 수정
    current_year_eps_revision: Optional[float] = None
    next_year_eps_revision: Optional[float] = None
    eps_up_revisions: int = 0
    eps_down_revisions: int = 0
    revision_ratio: float = 0.5
    earnings_momentum: str = "neutral"  # "strong_positive", "positive", "neutral", "negative", "strong_negative"

    # 공시 센티먼트
    total_disclosures: int = 0
    positive_disclosures: int = 0
    negative_disclosures: int = 0
    net_disclosure_sentiment: int = 0
    material_events: List[Dict[str, Any]] = field(default_factory=list)

    # 실적 서프라이즈
    avg_earnings_surprise: Optional[float] = None
    consecutive_beats: int = 0
    consecutive_misses: int = 0
    beat_rate: Optional[float] = None
    earnings_surprises: List[Dict[str, Any]] = field(default_factory=list)

    # 주요 동인
    key_drivers: List[str] = field(default_factory=list)

    # 투자 시그널
    investment_signal: str = "neutral"  # "strong_buy", "buy", "hold", "sell", "strong_sell"


class SentimentAgent:
    """
    센티먼트 분석 에이전트

    기능:
    - 뉴스 센티먼트 분석 (긍정/부정 키워드 기반)
    - 애널리스트 센티먼트 (투자의견, 목표주가, EPS 수정)
    - 공시 센티먼트 (DART 공시 분석)
    - 실적 서프라이즈 분석 (컨센서스 대비 실적)

    사용법:
        agent = SentimentAgent(krx_client=krx)
        result = agent.analyze("005930", current_price=65000)
    """

    def __init__(
        self,
        krx_client: Optional[KrxClient] = None,
        dart_client: Optional[DartClient] = None,
        ebest_client: Optional[EbestClient] = None,
        config: Optional[SentimentAnalysisConfig] = None
    ):
        """
        센티먼트 분석 에이전트 초기화

        Args:
            krx_client: KRX 데이터 클라이언트
            dart_client: DART API 클라이언트 (선택)
            ebest_client: eBest xingAPI 클라이언트 (선택)
            config: 분석 설정
        """
        self.krx = krx_client or KrxClient()
        self.config = config or SentimentAnalysisConfig()
        self.logger = logging.getLogger(__name__)

        # DART 클라이언트 초기화 (환경 변수에서 API 키 자동 로드)
        self.dart = dart_client
        if self.dart is None:
            try:
                import os
                if os.environ.get("DART_API_KEY"):
                    self.dart = DartClient()
                    self.logger.info("DART API 클라이언트 초기화 완료")
            except Exception as e:
                self.logger.warning(f"DART API 클라이언트 초기화 실패: {e}")
                self.dart = None

        # eBest 클라이언트 초기화 (환경 변수에서 API 키 자동 로드)
        self.ebest = ebest_client
        if self.ebest is None:
            try:
                import os
                if os.environ.get("EBEST_APP_KEY") and os.environ.get("EBEST_APP_SECRET"):
                    self.ebest = EbestClient()
                    self.logger.info("eBest xingAPI 클라이언트 초기화 완료")
            except Exception as e:
                self.logger.warning(f"eBest 클라이언트 초기화 실패: {e}")
                self.ebest = None

        # 한국어 금융 키워드 사전 초기화
        self._initialize_keyword_dict()

    def _initialize_keyword_dict(self):
        """금융 특화 키워드 사전 초기화"""
        self.positive_keywords = {
            "실적 호조": 0.8,
            "흑자 전환": 0.9,
            "사상 최대": 0.8,
            "수주 확대": 0.7,
            "신사업 진출": 0.6,
            "배당 확대": 0.7,
            "자사주 매입": 0.6,
            "목표가 상향": 0.8,
            "투자의견 상향": 0.8,
            "어닝 서프라이즈": 0.9,
            "성장 가속": 0.7,
            "수출 호조": 0.6,
            "규제 완화": 0.5,
            "신제품 출시": 0.5,
            "매출 증가": 0.6,
            "영업이익 증가": 0.7,
            "시장점유율 확대": 0.6,
            "배당 증가": 0.6,
        }

        self.negative_keywords = {
            "실적 악화": -0.8,
            "적자 전환": -0.9,
            "하향 조정": -0.7,
            "수주 감소": -0.7,
            "구조조정": -0.6,
            "배당 삭감": -0.7,
            "목표가 하향": -0.8,
            "투자의견 하향": -0.8,
            "어닝 쇼크": -0.9,
            "성장 둔화": -0.6,
            "수출 부진": -0.6,
            "규제 강화": -0.5,
            "소송": -0.4,
            "횡령": -0.8,
            "분식회계": -0.9,
            "매출 감소": -0.6,
            "영업손실": -0.7,
            "적자": -0.7,
        }

        # 공시 키워드
        self.positive_disclosure_keywords = {
            "자기주식 취득": 0.7,
            "배당 결정": 0.6,
            "대규모 수주": 0.8,
            "신사업 진출": 0.5,
            "실적 개선": 0.6,
            "흑자 전환": 0.8,
            "계약체결": 0.5,
        }

        self.negative_disclosure_keywords = {
            "유상증자": -0.6,
            "CB 발행": -0.4,
            "BW 발행": -0.4,
            "소송 제기": -0.5,
            "손실 발생": -0.7,
            "감자": -0.8,
            "횡령": -0.9,
            "배임": -0.8,
        }

    def analyze(
        self,
        stock_code: str,
        current_price: Optional[int] = None,
        financial_data: Optional[Dict[str, Any]] = None
    ) -> SentimentAnalysisResult:
        """
        종목 센티먼트 분석 실행

        Args:
            stock_code: 종목코드 (6자리)
            current_price: 현재주가 (옵션)
            financial_data: 재무 데이터 (옵션)

        Returns:
            센티먼트 분석 결과
        """
        self.logger.info(f"센티먼트 분석 시작: {stock_code}")

        # 0. 날짜 확인
        analysis_date = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().year
        current_month = datetime.now().month
        self.logger.info(f"분석 기준일: {analysis_date}, 현재: {current_year}년 {current_month}월")

        # 1. 기본 정보
        stock_name = self.krx._get_stock_name(stock_code)

        # 현재가 조회 (제공되지 않은 경우)
        if current_price is None:
            price_data = self.krx.get_stock_price(stock_code)
            if price_data and "close_price" in price_data:
                current_price = price_data["close_price"]

        # 2. 뉴스 센티먼트 분석
        news_result = self._analyze_news_sentiment(stock_code, stock_name)

        # 3. 애널리스트 센티먼트 분석
        analyst_result = self._analyze_analyst_sentiment(
            stock_code,
            stock_name,
            current_price
        )

        # 4. 공시 센티먼트 분석
        disclosure_result = self._analyze_disclosure_sentiment(stock_code, stock_name)

        # 5. 실적 서프라이즈 분석
        earnings_result = self._analyze_earnings_surprise(stock_code, financial_data)

        # 6. 종합 센티먼트 점수 계산
        total_score, sentiment_grade = self._calculate_total_sentiment_score(
            news_result,
            analyst_result,
            disclosure_result,
            earnings_result
        )

        # 7. 주요 동인 식별
        key_drivers = self._identify_key_drivers(
            news_result,
            analyst_result,
            disclosure_result,
            earnings_result
        )

        # 8. 투자 시그널 결정
        investment_signal = self._determine_investment_signal(total_score, key_drivers)

        return SentimentAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            analysis_date=analysis_date,
            total_score=round(total_score, 1),
            sentiment_grade=sentiment_grade,
            news_score=round(news_result["score"], 1),
            analyst_score=round(analyst_result["score"], 1),
            disclosure_score=round(disclosure_result["score"], 1),
            earnings_surprise_score=round(earnings_result["score"], 1),
            # 뉴스
            news_weighted_sentiment=news_result.get("weighted_sentiment"),
            news_volume=news_result.get("volume", 0),
            news_volume_signal=news_result.get("volume_signal", "normal"),
            positive_news_count=news_result.get("positive_count", 0),
            negative_news_count=news_result.get("negative_count", 0),
            recent_headlines=news_result.get("recent_headlines", []),
            # 애널리스트
            analyst_consensus=analyst_result.get("consensus", "Hold"),
            consensus_score=analyst_result.get("consensus_score", 0.0),
            rating_distribution=analyst_result.get("rating_distribution", {}),
            total_analysts=analyst_result.get("total_analysts", 0),
            rating_momentum=analyst_result.get("rating_momentum", 0.0),
            upgrades_3m=analyst_result.get("upgrades", 0),
            downgrades_3m=analyst_result.get("downgrades", 0),
            current_price=current_price,
            avg_target_price=analyst_result.get("avg_target"),
            median_target_price=analyst_result.get("median_target"),
            upside_to_avg=analyst_result.get("upside_to_avg"),
            target_price_change_3m=analyst_result.get("tp_change_3m"),
            current_year_eps_revision=analyst_result.get("current_year_revision"),
            next_year_eps_revision=analyst_result.get("next_year_revision"),
            eps_up_revisions=analyst_result.get("up_revisions", 0),
            eps_down_revisions=analyst_result.get("down_revisions", 0),
            revision_ratio=analyst_result.get("revision_ratio", 0.5),
            earnings_momentum=analyst_result.get("earnings_momentum", "neutral"),
            # 공시
            total_disclosures=disclosure_result.get("total", 0),
            positive_disclosures=disclosure_result.get("positive_count", 0),
            negative_disclosures=disclosure_result.get("negative_count", 0),
            net_disclosure_sentiment=disclosure_result.get("net_sentiment", 0),
            material_events=disclosure_result.get("material_events", []),
            # 실적 서프라이즈
            avg_earnings_surprise=earnings_result.get("avg_surprise"),
            consecutive_beats=earnings_result.get("consecutive_beats", 0),
            consecutive_misses=earnings_result.get("consecutive_misses", 0),
            beat_rate=earnings_result.get("beat_rate"),
            earnings_surprises=earnings_result.get("surprises", []),
            # 종합
            key_drivers=key_drivers,
            investment_signal=investment_signal
        )

    def _analyze_news_sentiment(
        self,
        stock_code: str,
        stock_name: str
    ) -> Dict[str, Any]:
        """뉴스 센티먼트 분석"""
        result = {
            "score": 50,
            "weighted_sentiment": 0.0,
            "volume": 0,
            "volume_signal": "normal",
            "positive_count": 0,
            "negative_count": 0,
            "recent_headlines": []
        }

        try:
            # 네이버 금융 뉴스 + 구글 RSS 뉴스 수집
            news_articles = []

            # 1. 네이버 금융 뉴스 (국내)
            naver_news = self._fetch_news_naver(stock_code, stock_name, days=self.config.news_lookback_days)
            news_articles.extend(naver_news)

            # 2. 구글 RSS 뉴스 (해외)
            google_news = self._fetch_news_google_rss(stock_name, days=self.config.news_lookback_days)
            news_articles.extend(google_news)

            if not news_articles:
                self.logger.warning(f"뉴스 데이터 없음: {stock_code}")
                return result

            result["volume"] = len(news_articles)

            # 각 기사 센티먼트 분석
            sentiments = []
            for article in news_articles:
                sentiment = self._analyze_headline(article["headline"])
                sentiments.append({
                    "date": article["date"],
                    "source": article["source"],
                    "headline": article["headline"],
                    "sentiment": sentiment
                })

                if sentiment > 0.3:
                    result["positive_count"] += 1
                elif sentiment < -0.3:
                    result["negative_count"] += 1

            # 최근 헤드라인 저장 (최대 5개)
            result["recent_headlines"] = sentiments[:5]

            # 시간 가중 평균 센티먼트 계산
            if sentiments:
                # 최근 뉴스에 더 높은 가중치 (지수 감소)
                total_weight = 0
                weighted_sum = 0
                for i, s in enumerate(sentiments):
                    weight = 0.95 ** i  # 시간 감쇠
                    weighted_sum += s["sentiment"] * weight
                    total_weight += weight

                weighted_sentiment = weighted_sum / total_weight if total_weight > 0 else 0
                result["weighted_sentiment"] = round(weighted_sentiment, 3)

            # 뉴스 볼륨 시그널
            avg_volume = 20  # 평균 뉴스 개수 가정
            if result["volume"] > avg_volume * 2:
                result["volume_signal"] = "surge"
            elif result["volume"] > avg_volume * self.config.news_volume_threshold:
                result["volume_signal"] = "above_normal"

            # 점수 계산 (0-100)
            score = 50 + (result["weighted_sentiment"] * 50)  # -1~1을 0~100으로 변환

            # 뉴스 볼륨에 따른 조정
            if result["volume_signal"] == "surge":
                if result["weighted_sentiment"] > 0:
                    score += 10
                else:
                    score -= 10

            result["score"] = max(0, min(100, score))

        except Exception as e:
            self.logger.error(f"뉴스 센티먼트 분석 실패: {e}")

        return result

    def _analyze_headline(self, headline: str) -> float:
        """헤드라인 센티먼트 분석"""
        score = 0
        matched_keywords = []

        # 긍정 키워드 체크
        for keyword, weight in self.positive_keywords.items():
            if keyword in headline:
                score += weight
                matched_keywords.append((keyword, weight))

        # 부정 키워드 체크
        for keyword, weight in self.negative_keywords.items():
            if keyword in headline:
                score += weight
                matched_keywords.append((keyword, weight))

        # -1 ~ 1 범위로 정규화
        normalized_score = max(-1, min(1, score))

        return normalized_score

    def _analyze_analyst_sentiment(
        self,
        stock_code: str,
        stock_name: str,
        current_price: Optional[int]
    ) -> Dict[str, Any]:
        """애널리스트 센티먼트 분석"""
        result = {
            "score": 50,
            "consensus": "Hold",
            "consensus_score": 0.0,
            "rating_distribution": {
                "strong_buy": 0,
                "buy": 0,
                "hold": 0,
                "sell": 0,
                "strong_sell": 0
            },
            "total_analysts": 0,
            "rating_momentum": 0.0,
            "upgrades": 0,
            "downgrades": 0,
            "avg_target": None,
            "median_target": None,
            "upside_to_avg": None,
            "tp_change_3m": None,
            "current_year_revision": None,
            "next_year_revision": None,
            "up_revisions": 0,
            "down_revisions": 0,
            "revision_ratio": 0.5,
            "earnings_momentum": "neutral"
        }

        try:
            # 1차: eBest xingAPI에서 애널리스트 데이터 수집
            analyst_data = None
            if self.ebest:
                analyst_data = self._fetch_analyst_data_ebest(stock_code)

            # 2차: 네이버 금융에서 애널리스트 컨센서스 데이터 수집 (fallback)
            if not analyst_data:
                analyst_data = self._fetch_analyst_data_naver(stock_code)

            if not analyst_data:
                self.logger.warning(f"애널리스트 데이터 없음: {stock_code}")
                return result

            # 1. 투자의견 분포
            result["rating_distribution"] = analyst_data.get("rating_distribution", result["rating_distribution"])
            result["total_analysts"] = sum(result["rating_distribution"].values())

            # 컨센서스 점수 계산 (-2 ~ +2)
            weights = {
                "strong_buy": 2,
                "buy": 1,
                "hold": 0,
                "sell": -1,
                "strong_sell": -2
            }

            total_weight = sum(result["rating_distribution"][k] * weights[k] for k in result["rating_distribution"])
            if result["total_analysts"] > 0:
                consensus_score = total_weight / result["total_analysts"]
                result["consensus_score"] = round(consensus_score, 2)
                result["consensus"] = self._get_consensus_label(consensus_score)

            # 2. 의견 변화 모멘텀
            result["upgrades"] = analyst_data.get("upgrades_3m", 0)
            result["downgrades"] = analyst_data.get("downgrades_3m", 0)

            total_changes = result["upgrades"] + result["downgrades"]
            if total_changes > 0:
                result["rating_momentum"] = (result["upgrades"] - result["downgrades"]) / total_changes

            # 3. 목표주가 분석
            target_prices = analyst_data.get("target_prices", [])
            if target_prices and current_price:
                result["avg_target"] = int(sum(target_prices) / len(target_prices))
                result["median_target"] = int(sorted(target_prices)[len(target_prices) // 2])
                result["upside_to_avg"] = round((result["avg_target"] / current_price - 1) * 100, 2)
                result["tp_change_3m"] = analyst_data.get("tp_change_3m", 0.0)

            # 4. 이익 추정치 수정
            result["current_year_revision"] = analyst_data.get("eps_revision_current", 0.0)
            result["next_year_revision"] = analyst_data.get("eps_revision_next", 0.0)
            result["up_revisions"] = analyst_data.get("eps_up_count", 0)
            result["down_revisions"] = analyst_data.get("eps_down_count", 0)

            total_revisions = result["up_revisions"] + result["down_revisions"]
            if total_revisions > 0:
                result["revision_ratio"] = result["up_revisions"] / total_revisions

            # 이익 모멘텀 판단
            if result["revision_ratio"] > 0.7 and result["current_year_revision"] > 5:
                result["earnings_momentum"] = "strong_positive"
                earnings_score = 0.8
            elif result["revision_ratio"] > 0.5 and result["current_year_revision"] > 0:
                result["earnings_momentum"] = "positive"
                earnings_score = 0.4
            elif result["revision_ratio"] < 0.3 and result["current_year_revision"] < -5:
                result["earnings_momentum"] = "strong_negative"
                earnings_score = -0.8
            elif result["revision_ratio"] < 0.5 and result["current_year_revision"] < 0:
                result["earnings_momentum"] = "negative"
                earnings_score = -0.4
            else:
                result["earnings_momentum"] = "neutral"
                earnings_score = 0

            # 점수 계산
            # 컨센서스 점수: 30%
            consensus_component = ((result["consensus_score"] + 2) / 4) * 100 * 0.30

            # 목표주가 업사이드: 30%
            if result["upside_to_avg"] is not None:
                upside_normalized = (min(max(result["upside_to_avg"], -30), 50) + 30) / 80 * 100
                upside_component = upside_normalized * 0.30
            else:
                upside_component = 50 * 0.30

            # 이익 모멘텀: 40%
            earnings_component = ((earnings_score + 1) / 2) * 100 * 0.40

            result["score"] = consensus_component + upside_component + earnings_component

        except Exception as e:
            self.logger.error(f"애널리스트 센티먼트 분석 실패: {e}")

        return result

    def _analyze_disclosure_sentiment(
        self,
        stock_code: str,
        stock_name: str
    ) -> Dict[str, Any]:
        """공시 센티먼트 분석"""
        result = {
            "score": 50,
            "total": 0,
            "positive_count": 0,
            "negative_count": 0,
            "net_sentiment": 0,
            "material_events": []
        }

        try:
            # DART API를 통해 공시 데이터 수집
            disclosures = self._fetch_disclosures_dart(stock_code, days=self.config.disclosure_lookback_days)

            if not disclosures:
                self.logger.warning(f"공시 데이터 없음: {stock_code}")
                return result

            result["total"] = len(disclosures)

            positive_events = []
            negative_events = []

            for disclosure in disclosures:
                sentiment = self._calculate_disclosure_sentiment(disclosure["title"])
                disclosure["sentiment"] = sentiment

                if sentiment > 0.3:
                    positive_events.append(disclosure)
                    result["positive_count"] += 1
                elif sentiment < -0.3:
                    negative_events.append(disclosure)
                    result["negative_count"] += 1

            result["net_sentiment"] = result["positive_count"] - result["negative_count"]
            result["material_events"] = (positive_events[:3] + negative_events[:3])[:5]

            # 점수 계산
            score = 50 + (result["net_sentiment"] * 10)
            result["score"] = max(0, min(100, score))

        except Exception as e:
            self.logger.error(f"공시 센티먼트 분석 실패: {e}")

        return result

    def _calculate_disclosure_sentiment(self, title: str) -> float:
        """공시 센티먼트 계산"""
        sentiment = 0

        # 긍정 공시 키워드
        for keyword, weight in self.positive_disclosure_keywords.items():
            if keyword in title:
                sentiment += weight

        # 부정 공시 키워드
        for keyword, weight in self.negative_disclosure_keywords.items():
            if keyword in title:
                sentiment += weight

        return max(-1, min(1, sentiment))

    def _analyze_earnings_surprise(
        self,
        stock_code: str,
        financial_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """실적 서프라이즈 분석"""
        result = {
            "score": 50,
            "avg_surprise": None,
            "consecutive_beats": 0,
            "consecutive_misses": 0,
            "beat_rate": None,
            "surprises": []
        }

        try:
            # 하이브리드 접근: DART 최우선, 하지만 최신 분기 없으면 Naver 보충
            earnings_data = []
            has_recent_quarter = False

            # 1차: DART에서 실적 데이터 수집
            if self.dart:
                earnings_data, has_recent_quarter = self._fetch_earnings_data_dart(stock_code)

            # 2차: DART에 최신 분기가 없으면 Naver로 보충 시도
            if earnings_data and not has_recent_quarter:
                self.logger.info(f"DART에 최신 분기 없음. Naver 금융에서 최신 실적 확인 중...")
                naver_data = self._fetch_earnings_data_naver(stock_code)

                if naver_data:
                    # Naver에서 가장 최신 데이터를 가져와서 사용
                    # Naver 데이터가 더 신선하므로 우선 사용
                    self.logger.info(f"Naver 금융에서 최신 실적 수집 성공. Naver 데이터 우선 사용.")
                    earnings_data = naver_data
                else:
                    self.logger.info(f"Naver 금융에서도 최신 실적 없음. DART의 최신 데이터 사용.")
                    # earnings_data는 DART 데이터 그대로 사용

            # 3차: DART에 데이터가 아예 없으면 eBest 시도
            if not earnings_data and self.ebest:
                self.logger.info(f"DART 실적 없음. eBest API 시도 중...")
                earnings_data = self._fetch_earnings_data_ebest(stock_code)

            # 4차: 모두 실패하면 Naver 최종 시도
            if not earnings_data:
                self.logger.info(f"DART/eBest 실적 없음. Naver 금융 최종 시도 중...")
                earnings_data = self._fetch_earnings_data_naver(stock_code)

            if not earnings_data:
                self.logger.warning(f"실적 데이터 없음: {stock_code}")
                return result

            # 데이터 소스 로깅
            data_source = earnings_data[0].get("source", "Unknown") if earnings_data else "Unknown"
            self.logger.info(f"실적 데이터 소스: {data_source}")

            surprises = []
            consecutive_beats = 0
            consecutive_misses = 0

            for quarter_data in earnings_data:
                actual = quarter_data["actual_eps"]
                estimate = quarter_data["estimate_eps"]

                if estimate != 0:
                    surprise_pct = (actual - estimate) / abs(estimate) * 100
                else:
                    surprise_pct = 0

                beat = actual > estimate
                surprises.append({
                    "quarter": quarter_data["quarter"],
                    "actual": actual,
                    "estimate": estimate,
                    "surprise_pct": round(surprise_pct, 2),
                    "beat": beat
                })

                # 연속 beat/miss 카운트
                if beat:
                    consecutive_beats += 1
                    consecutive_misses = 0
                else:
                    consecutive_misses += 1
                    consecutive_beats = 0

            result["surprises"] = surprises
            result["consecutive_beats"] = consecutive_beats
            result["consecutive_misses"] = consecutive_misses

            if surprises:
                result["avg_surprise"] = round(sum(s["surprise_pct"] for s in surprises) / len(surprises), 2)
                result["beat_rate"] = round(len([s for s in surprises if s["beat"]]) / len(surprises), 2)

            # 점수 계산
            score = 50
            if result["avg_surprise"]:
                score += result["avg_surprise"] * 2  # 평균 서프라이즈 반영

            if consecutive_beats >= self.config.consecutive_beats_threshold:
                score += 15
            elif consecutive_misses >= 2:
                score -= 15

            result["score"] = max(0, min(100, score))

        except Exception as e:
            self.logger.error(f"실적 서프라이즈 분석 실패: {e}")

        return result

    def _calculate_total_sentiment_score(
        self,
        news_result: Dict[str, Any],
        analyst_result: Dict[str, Any],
        disclosure_result: Dict[str, Any],
        earnings_result: Dict[str, Any]
    ) -> tuple[float, str]:
        """종합 센티먼트 점수 계산"""
        total_score = (
            news_result["score"] * self.config.news_weight +
            analyst_result["score"] * self.config.analyst_weight +
            disclosure_result["score"] * self.config.disclosure_weight +
            earnings_result["score"] * self.config.earnings_surprise_weight
        )

        # 센티먼트 등급 결정
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

        return total_score, sentiment_grade

    def _identify_key_drivers(
        self,
        news_result: Dict[str, Any],
        analyst_result: Dict[str, Any],
        disclosure_result: Dict[str, Any],
        earnings_result: Dict[str, Any]
    ) -> List[str]:
        """주요 센티먼트 동인 식별"""
        drivers = []

        # 뉴스
        if news_result.get("volume_signal") == "surge":
            drivers.append("뉴스 관심도 급증")

        # 애널리스트
        if analyst_result.get("rating_momentum", 0) > 0.3:
            drivers.append("애널리스트 의견 상향 추세")
        elif analyst_result.get("rating_momentum", 0) < -0.3:
            drivers.append("애널리스트 의견 하향 추세")

        if analyst_result.get("upside_to_avg") and analyst_result["upside_to_avg"] > 30:
            drivers.append(f"목표주가 상승여력 {analyst_result['upside_to_avg']:.1f}%")

        if analyst_result.get("earnings_momentum") == "strong_positive":
            drivers.append("이익 추정치 상향 조정 강세")

        # 공시
        if disclosure_result.get("positive_count", 0) >= 2:
            drivers.append(f"긍정적 공시 {disclosure_result['positive_count']}건")
        if disclosure_result.get("negative_count", 0) >= 2:
            drivers.append(f"부정적 공시 {disclosure_result['negative_count']}건")

        # 실적 서프라이즈
        if earnings_result.get("consecutive_beats", 0) >= 3:
            drivers.append(f"실적 {earnings_result['consecutive_beats']}분기 연속 beat")
        elif earnings_result.get("consecutive_misses", 0) >= 2:
            drivers.append(f"실적 {earnings_result['consecutive_misses']}분기 연속 miss")

        return drivers[:5]  # 상위 5개만

    def _determine_investment_signal(
        self,
        total_score: float,
        key_drivers: List[str]
    ) -> str:
        """투자 시그널 결정"""
        if total_score > 75:
            return "strong_buy"
        elif total_score > 60:
            return "buy"
        elif total_score > 40:
            return "hold"
        elif total_score > 25:
            return "sell"
        else:
            return "strong_sell"

    def _get_consensus_label(self, score: float) -> str:
        """컨센서스 점수를 라벨로 변환"""
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

    # ========================================================================
    # 실제 데이터 수집 함수들
    # ========================================================================

    def _fetch_news_naver(self, stock_code: str, stock_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """네이버 금융 뉴스 수집 (웹 크롤링)"""
        if not REQUESTS_AVAILABLE:
            self.logger.warning("requests 라이브러리가 설치되지 않았습니다. Mock 데이터를 사용합니다.")
            return self._get_mock_news(stock_name)

        news_list = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # 네이버 금융 종목 뉴스 페이지
            url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1&sm=title_entity_id.basic&clusterId="

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 뉴스 리스트 파싱
            news_items = soup.select('.newsList .articleSubject a')
            date_items = soup.select('.newsList .date')

            for i, (news_link, date_elem) in enumerate(zip(news_items[:20], date_items[:20])):
                headline = news_link.get('title', news_link.text.strip())
                date_str = date_elem.text.strip()

                # 날짜 파싱 (예: "2026.02.02" 형식)
                try:
                    if '.' in date_str:
                        date_obj = datetime.strptime(date_str, "%Y.%m.%d")
                    else:
                        date_obj = datetime.now()

                    # 지정된 기간 내 뉴스만
                    if (datetime.now() - date_obj).days > days:
                        continue

                    news_list.append({
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "source": "네이버금융",
                        "headline": headline,
                        "url": "https://finance.naver.com" + news_link.get('href', '')
                    })
                except Exception as e:
                    self.logger.debug(f"날짜 파싱 오류: {e}")
                    continue

            self.logger.info(f"네이버 금융 뉴스 {len(news_list)}개 수집 완료")

        except Exception as e:
            self.logger.error(f"네이버 금융 뉴스 수집 실패: {e}")
            return []

        return news_list  # 빈 리스트여도 그대로 반환 (구글 RSS에서 수집)

    def _fetch_news_google_rss(self, stock_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """구글 RSS 뉴스 수집 (해외 뉴스)"""
        if not FEEDPARSER_AVAILABLE:
            self.logger.warning("feedparser 라이브러리가 설치되지 않았습니다.")
            return []

        news_list = []
        try:
            # 구글 뉴스 RSS (한국어, 해외 뉴스 포함)
            query = f"{stock_name} stock OR 주가"
            # URL 인코딩 적용
            encoded_query = quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:10]:  # 최대 10개
                try:
                    # 날짜 파싱
                    if hasattr(entry, 'published_parsed'):
                        pub_date = datetime(*entry.published_parsed[:6])
                    else:
                        pub_date = datetime.now()

                    # 지정된 기간 내 뉴스만
                    if (datetime.now() - pub_date).days > days:
                        continue

                    news_list.append({
                        "date": pub_date.strftime("%Y-%m-%d"),
                        "source": entry.get('source', {}).get('title', 'Google News'),
                        "headline": entry.title,
                        "url": entry.link
                    })
                except Exception as e:
                    self.logger.debug(f"RSS 엔트리 파싱 오류: {e}")
                    continue

            self.logger.info(f"구글 RSS 뉴스 {len(news_list)}개 수집 완료")

        except Exception as e:
            self.logger.error(f"구글 RSS 뉴스 수집 실패: {e}")

        return news_list

    def _fetch_analyst_data_naver(self, stock_code: str) -> Dict[str, Any]:
        """네이버 금융 애널리스트 데이터 크롤링"""
        if not REQUESTS_AVAILABLE:
            self.logger.warning("requests 라이브러리가 설치되지 않았습니다. Mock 데이터를 사용합니다.")
            return self._get_mock_analyst_data()

        result = {
            "rating_distribution": {
                "strong_buy": 0,
                "buy": 0,
                "hold": 0,
                "sell": 0,
                "strong_sell": 0
            },
            "upgrades_3m": 0,
            "downgrades_3m": 0,
            "target_prices": [],
            "tp_change_3m": 0.0,
            "eps_revision_current": 0.0,
            "eps_revision_next": 0.0,
            "eps_up_count": 0,
            "eps_down_count": 0
        }

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # 네이버 금융 투자의견 페이지
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 투자의견 파싱
            try:
                consensus_area = soup.select_one('.cop_analysis')
                if consensus_area:
                    # 컨센서스 의견 (매수/보유/매도)
                    opinion_items = consensus_area.select('.tb_type1 tr')
                    for item in opinion_items:
                        cells = item.select('td')
                        if len(cells) >= 4:
                            # 증권사명, 투자의견, 목표주가, 날짜
                            opinion_text = cells[1].text.strip() if len(cells) > 1 else ""
                            target_price_text = cells[2].text.strip() if len(cells) > 2 else ""

                            # 투자의견 매핑
                            if "매수" in opinion_text or "BUY" in opinion_text.upper():
                                if "적극" in opinion_text or "STRONG" in opinion_text.upper():
                                    result["rating_distribution"]["strong_buy"] += 1
                                else:
                                    result["rating_distribution"]["buy"] += 1
                            elif "보유" in opinion_text or "HOLD" in opinion_text.upper():
                                result["rating_distribution"]["hold"] += 1
                            elif "매도" in opinion_text or "SELL" in opinion_text.upper():
                                result["rating_distribution"]["sell"] += 1

                            # 목표주가 파싱
                            if target_price_text:
                                try:
                                    tp = int(target_price_text.replace(",", "").replace("원", ""))
                                    if tp > 0:
                                        result["target_prices"].append(tp)
                                except:
                                    pass
            except Exception as e:
                self.logger.debug(f"투자의견 파싱 오류: {e}")

            # EPS 컨센서스 파싱 (간략 버전)
            try:
                eps_area = soup.select('.gray .tbody')
                # 실제 구현 시 상세 파싱 필요
            except Exception as e:
                self.logger.debug(f"EPS 파싱 오류: {e}")

            self.logger.info(f"애널리스트 데이터 수집 완료: {sum(result['rating_distribution'].values())}명")

        except Exception as e:
            self.logger.error(f"네이버 금융 애널리스트 데이터 수집 실패: {e}")
            return None

        # 데이터가 없으면 None 반환 (TODO: 이베스트 xingAPI 연동)
        if sum(result['rating_distribution'].values()) == 0:
            return None

        return result

    def _fetch_disclosures_dart(self, stock_code: str, days: int = 90) -> List[Dict[str, Any]]:
        """DART API로 공시 수집"""
        if not self.dart:
            self.logger.warning("DART 클라이언트가 없습니다.")
            return []

        disclosures = []
        try:
            # 종목코드 -> corp_code 변환
            corp_code = self.dart.get_corp_code_by_stock_code(stock_code)
            if not corp_code:
                self.logger.warning(f"종목코드 {stock_code}에 대한 corp_code를 찾을 수 없습니다.")
                return []

            # 날짜 계산
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            # DART API 공시 목록 조회
            result = self.dart.get_disclosure_list(
                corp_code=corp_code,
                bgn_de=start_date,
                end_de=end_date,
                page_count=100
            )

            # 공시 목록 파싱
            if result.get("status") == "000" and "list" in result:
                for item in result["list"]:
                    disclosures.append({
                        "date": item.get("rcept_dt", ""),  # 접수일자
                        "title": item.get("report_nm", ""),  # 보고서명
                        "type": item.get("corp_cls", "")  # 법인구분
                    })

            self.logger.info(f"DART 공시 {len(disclosures)}건 수집 완료")

        except Exception as e:
            self.logger.error(f"DART 공시 수집 실패: {e}")
            return []

        return disclosures

    def _fetch_earnings_data_naver(self, stock_code: str) -> List[Dict[str, Any]]:
        """네이버 금융에서 실적 데이터 수집 (실제 + 컨센서스) - TODO: 이베스트 xingAPI 연동"""
        if not REQUESTS_AVAILABLE:
            self.logger.warning("requests 라이브러리가 설치되지 않았습니다.")
            return []

        earnings_data = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # 네이버 금융 투자정보 페이지
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 실적 분석 탭에서 분기별 EPS 데이터 파싱
            try:
                # 컨센서스 실적 테이블 (tb_type1 클래스)
                # 네이버 금융의 "투자정보" 섹션에서 실적 데이터 추출
                finance_table = soup.select('.sub_section.cop_analysis')

                if finance_table:
                    # EPS 관련 테이블 찾기
                    tables = soup.select('.gray')

                    for table in tables:
                        # EPS 또는 실적 관련 테이블 찾기
                        header = table.select_one('th')
                        if header and ('EPS' in header.text or '주당순이익' in header.text):
                            rows = table.select('tr')

                            # 연도/분기 정보 파싱
                            quarters = []
                            actual_values = []
                            estimate_values = []

                            for row in rows:
                                cells = row.select('td')
                                if len(cells) >= 2:
                                    # 분기 정보
                                    quarter_text = cells[0].text.strip()
                                    if quarter_text and ('Q' in quarter_text or '/' in quarter_text):
                                        quarters.append(quarter_text)

                                        # 실제 값
                                        actual_text = cells[1].text.strip() if len(cells) > 1 else ""
                                        try:
                                            actual = float(actual_text.replace(',', '')) if actual_text and actual_text != '-' else 0
                                            actual_values.append(actual)
                                        except:
                                            actual_values.append(0)

                                        # 추정치 (있는 경우)
                                        estimate_text = cells[2].text.strip() if len(cells) > 2 else ""
                                        try:
                                            estimate = float(estimate_text.replace(',', '')) if estimate_text and estimate_text != '-' else 0
                                            estimate_values.append(estimate)
                                        except:
                                            estimate_values.append(0)

                            # 데이터 조합
                            for i, quarter in enumerate(quarters[:8]):  # 최대 8분기
                                actual = actual_values[i] if i < len(actual_values) else 0
                                estimate = estimate_values[i] if i < len(estimate_values) else actual * 0.95  # 추정치가 없으면 실제값의 95%로 가정

                                earnings_data.append({
                                    "quarter": quarter,
                                    "actual_eps": actual,
                                    "estimate_eps": estimate,
                                    "source": "Naver"
                                })

                            break  # 첫 번째 EPS 테이블만 사용

                # 간단한 방식: API 방식으로 시도 (네이버 금융 AJAX)
                if not earnings_data:
                    # 네이버 금융은 일부 데이터를 AJAX로 제공
                    # TODO: 이베스트 xingAPI로 대체 필요
                    self.logger.warning(f"실적 테이블을 찾을 수 없습니다: {stock_code}")
                    return []

            except Exception as e:
                self.logger.debug(f"실적 데이터 파싱 오류: {e}")
                return []

            self.logger.info(f"실적 데이터 {len(earnings_data)}분기 수집 완료")

        except Exception as e:
            self.logger.error(f"네이버 금융 실적 데이터 수집 실패: {e}")
            return []

        return earnings_data

    # ========================================================================
    # eBest xingAPI 데이터 수집 함수들
    # ========================================================================

    def _fetch_analyst_data_ebest(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """eBest xingAPI로 애널리스트 데이터 수집"""
        try:
            analyst_data = self.ebest.get_analyst_consensus(stock_code)

            if analyst_data:
                self.logger.info(f"eBest 애널리스트 데이터 수집 완료: {sum(analyst_data['rating_distribution'].values())}명")

            return analyst_data

        except Exception as e:
            self.logger.error(f"eBest 애널리스트 데이터 수집 실패: {e}")
            return None

    def _fetch_earnings_data_dart(self, stock_code: str) -> tuple[List[Dict[str, Any]], bool]:
        """
        DART로 실적 데이터 수집 (최신 분기별 실적)

        DART에서 최근 4분기 실적을 가져와서
        YoY 성장률을 "earnings surprise" 대용으로 사용

        Returns:
            (earnings_data, has_recent_quarter)
            - earnings_data: 변환된 실적 데이터
            - has_recent_quarter: DART에 가장 최근 분기 데이터가 있는지 여부
        """
        try:
            if not self.dart:
                return [], False

            # 종목코드 → DART corp_code 변환
            corp_code = self.dart.get_corp_code_by_stock_code(stock_code)
            if not corp_code:
                self.logger.warning(f"DART corp_code를 찾을 수 없습니다: {stock_code}")
                return [], False

            # 현재 날짜 기준 예상 최근 분기 계산 (45일 지연 고려)
            from datetime import datetime
            now = datetime.now()
            current_year = now.year
            current_month = now.month

            if current_month <= 5:
                expected_recent_quarter = 4
                expected_recent_year = current_year - 1
            elif current_month <= 8:
                expected_recent_quarter = 1
                expected_recent_year = current_year
            elif current_month <= 11:
                expected_recent_quarter = 2
                expected_recent_year = current_year
            else:
                expected_recent_quarter = 3
                expected_recent_year = current_year

            # 분기별 실적 조회
            earnings = self.dart.get_quarterly_earnings(corp_code)

            if not earnings or len(earnings) < 2:
                return [], False

            # DART에 가장 최근 분기가 있는지 확인
            latest = earnings[0]
            latest_year = int(latest.get("year", 0))
            latest_quarter = latest.get("quarter", 0)

            has_recent_quarter = (
                latest_year == expected_recent_year and
                latest_quarter == expected_recent_quarter
            )

            # 최신 분기와 전년 동기 비교
            # earnings는 최신 분기부터 내림차순 정렬되어 있음
            yoy_compare = None    # 전년 동기 (4분기 전)

            if len(earnings) >= 4:
                yoy_compare = earnings[3]  # 4분기 전 = 전년 동기

            if not yoy_compare:
                # 전년 동기 데이터 없으면 전분기와 비교
                if len(earnings) >= 2:
                    yoy_compare = earnings[1]

            if not yoy_compare:
                return [], has_recent_quarter

            # 순이익 기반 성장률 계산 (EPS가 없으면 순이익 사용)
            latest_metric = latest.get("eps") or latest.get("net_income", 0)
            compare_metric = yoy_compare.get("eps") or yoy_compare.get("net_income", 0)

            if compare_metric == 0:
                return [], has_recent_quarter

            growth_rate = (latest_metric / compare_metric - 1) * 100

            # sentiment_agent 기존 형식으로 변환
            transformed = [{
                "quarter": f"{latest.get('period', '')} vs {yoy_compare.get('period', '')}",
                "actual_eps": latest_metric,        # 최신 분기 실적
                "estimate_eps": compare_metric,     # 비교 대상 (전년동기 또는 전분기)
                "source": "DART"
            }]

            self.logger.info(
                f"DART 실적 데이터 수집 완료: "
                f"{latest.get('period')} {latest.get('freshness', '')} "
                f"성장률 {growth_rate:+.1f}% "
                f"(최신분기 {'포함' if has_recent_quarter else '미포함'})"
            )

            return transformed, has_recent_quarter

        except Exception as e:
            self.logger.error(f"DART 실적 데이터 수집 실패: {e}")
            return [], False

    def _fetch_earnings_data_ebest(self, stock_code: str) -> List[Dict[str, Any]]:
        """
        eBest xingAPI로 실적 데이터 수집 (t3320) - FALLBACK

        DART 데이터 수집 실패 시에만 사용
        t3320은 trailing/forward EPS를 제공하므로, EPS 성장률을 계산
        """
        try:
            raw_data = self.ebest.get_earnings_data(stock_code)

            if not raw_data or len(raw_data) < 2:
                return []

            # t3320 응답: [actual, estimate] 형태
            actual_data = None
            estimate_data = None

            for item in raw_data:
                if item.get("period_type") == "actual":
                    actual_data = item
                elif item.get("period_type") == "estimate":
                    estimate_data = item

            if not actual_data or not estimate_data:
                return []

            # EPS 성장률 기반 "surprise" 계산
            # 실제로는 trailing vs forward EPS 비교
            trailing_eps = actual_data.get("eps", 0)
            forward_eps = estimate_data.get("eps", 0)

            if trailing_eps == 0:
                return []

            # "Surprise"를 EPS 성장률로 정의
            # 양수 성장 = 긍정적 surprise
            # 음수 성장 = 부정적 surprise
            growth_rate = (forward_eps / trailing_eps - 1) * 100

            # sentiment_agent의 기존 형식으로 변환
            # (quarter, actual_eps, estimate_eps)
            # 여기서는 "actual"을 forward로, "estimate"를 trailing으로 사용
            # 이렇게 하면 growth > 0일 때 beat으로 계산됨
            transformed = [{
                "quarter": f"{actual_data.get('period', '')} (Trailing) vs {estimate_data.get('period', '')} (Forward)",
                "actual_eps": forward_eps,  # Forward EPS를 "actual"로
                "estimate_eps": trailing_eps,  # Trailing EPS를 "estimate"로
                "source": "eBest"
            }]

            self.logger.info(f"eBest 실적 데이터 수집 완료: EPS 성장률 {growth_rate:+.1f}%")

            return transformed

        except Exception as e:
            self.logger.error(f"eBest 실적 데이터 수집 실패: {e}")
            return []

    # ========================================================================
    # Fallback Mock 데이터 함수들
    # ========================================================================

    def _get_mock_news(self, stock_name: str) -> List[Dict[str, Any]]:
        """Mock 데이터 제거 - 빈 리스트 반환"""
        self.logger.warning(f"뉴스 데이터를 수집할 수 없습니다: {stock_name}")
        return []

    def _get_mock_analyst_data(self) -> None:
        """Mock 데이터 제거 - None 반환 (TODO: 이베스트 xingAPI 연동)"""
        self.logger.warning("애널리스트 데이터를 수집할 수 없습니다. 이베스트 xingAPI 연동이 필요합니다.")
        return None

    def _get_mock_disclosures(self) -> List[Dict[str, Any]]:
        """Mock 데이터 제거 - 빈 리스트 반환"""
        self.logger.warning("공시 데이터를 수집할 수 없습니다.")
        return []

    def _get_mock_earnings(self) -> List[Dict[str, Any]]:
        """Mock 데이터 제거 - 빈 리스트 반환 (TODO: 이베스트 xingAPI 연동)"""
        self.logger.warning("실적 데이터를 수집할 수 없습니다. 이베스트 xingAPI 연동이 필요합니다.")
        return []
