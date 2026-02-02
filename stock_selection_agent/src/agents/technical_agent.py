"""
Technical Agent - 기술적 분석 에이전트
이동평균, RSI, MACD, 거래량, 수급 분석
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
import math

from ..api.krx_client import KrxClient


@dataclass
class TechnicalAnalysisConfig:
    """기술적 분석 설정"""
    # 가중치
    trend_weight: float = 0.30  # 추세 분석
    momentum_weight: float = 0.30  # 모멘텀 분석
    volume_weight: float = 0.20  # 거래량 분석
    supply_demand_weight: float = 0.20  # 수급 분석

    # 이동평균 기간
    ma_periods: List[int] = field(default_factory=lambda: [5, 20, 60, 120])

    # RSI 설정
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0

    # 분석 기간
    lookback_days: int = 120


@dataclass
class TechnicalSignal:
    """기술적 시그널"""
    signal_type: str
    description: str
    strength: str  # "strong", "moderate", "weak"
    action: str  # "bullish", "bearish", "neutral"


@dataclass
class TechnicalAnalysisResult:
    """기술적 분석 결과"""
    stock_code: str
    stock_name: str
    analysis_date: str
    current_price: int

    # 점수 (0-100)
    total_score: float = 50.0
    trend_score: float = 50.0
    momentum_score: float = 50.0
    volume_score: float = 50.0
    supply_demand_score: float = 50.0

    # 추세 분석
    ma_arrangement: str = "mixed"  # "bullish_aligned", "bearish_aligned", "mixed"
    ma_positions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    price_vs_ma20: Optional[float] = None
    price_vs_ma60: Optional[float] = None

    # 모멘텀
    rsi_14: Optional[float] = None
    rsi_status: str = "neutral"  # "overbought", "oversold", "neutral"
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None

    # 거래량
    volume_ratio: Optional[float] = None  # 현재 거래량 / 평균 거래량
    volume_status: str = "normal"  # "surge", "above_average", "normal", "very_low"

    # 수급
    foreign_trend: str = "neutral"  # "buying", "selling", "neutral"
    institutional_trend: str = "neutral"
    foreign_net_20d: Optional[int] = None
    institutional_net_20d: Optional[int] = None

    # 시그널
    signals: List[TechnicalSignal] = field(default_factory=list)

    # 종합 판단
    overall_signal: str = "neutral"  # "bullish", "bearish", "neutral"
    recommendation: str = ""


class TechnicalAgent:
    """
    기술적 분석 에이전트

    기능:
    - 이동평균선 분석 (MA5, MA20, MA60, MA120)
    - 골든크로스/데드크로스 감지
    - RSI 과매수/과매도 분석
    - MACD 분석
    - 거래량 분석
    - 수급 분석 (외국인, 기관)

    사용법:
        agent = TechnicalAgent(krx_client=krx)
        result = agent.analyze("005930")  # 삼성전자
    """

    def __init__(
        self,
        krx_client: Optional[KrxClient] = None,
        config: Optional[TechnicalAnalysisConfig] = None
    ):
        """
        기술적 분석 에이전트 초기화

        Args:
            krx_client: KRX 데이터 클라이언트
            config: 분석 설정
        """
        self.krx = krx_client or KrxClient()
        self.config = config or TechnicalAnalysisConfig()
        self.logger = logging.getLogger(__name__)

    def analyze(self, stock_code: str) -> TechnicalAnalysisResult:
        """
        종목 기술적 분석 실행

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            기술적 분석 결과
        """
        self.logger.info(f"기술적 분석 시작: {stock_code}")

        # 1. 가격 히스토리 조회
        price_history = self.krx.get_stock_price_history(stock_code)
        if not price_history or len(price_history) < 20:
            self.logger.warning(f"가격 데이터 부족: {stock_code}")
            return self._create_default_result(stock_code)

        # 데이터 추출
        prices = [p["close_price"] for p in price_history]
        volumes = [p.get("volume", 0) for p in price_history]
        stock_name = self.krx._get_stock_name(stock_code)
        current_price = prices[-1]
        analysis_date = datetime.now().strftime("%Y-%m-%d")

        # 2. 추세 분석
        trend_result = self._analyze_trend(prices)

        # 3. 모멘텀 분석
        momentum_result = self._analyze_momentum(prices)

        # 4. 거래량 분석
        volume_result = self._analyze_volume(volumes)

        # 5. 수급 분석
        supply_demand_result = self._analyze_supply_demand(stock_code)

        # 6. 시그널 수집
        signals = self._collect_signals(trend_result, momentum_result, volume_result, supply_demand_result)

        # 7. 종합 점수 계산
        total_score = (
            trend_result["score"] * self.config.trend_weight +
            momentum_result["score"] * self.config.momentum_weight +
            volume_result["score"] * self.config.volume_weight +
            supply_demand_result["score"] * self.config.supply_demand_weight
        )

        # 8. 종합 판단
        if total_score >= 65:
            overall_signal = "bullish"
            recommendation = "매수 타이밍 양호, 분할 매수 고려"
        elif total_score <= 35:
            overall_signal = "bearish"
            recommendation = "매수 보류, 추가 하락 가능성 주의"
        else:
            overall_signal = "neutral"
            recommendation = "중립, 추세 확인 후 진입 권장"

        return TechnicalAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            analysis_date=analysis_date,
            current_price=current_price,
            total_score=round(total_score, 1),
            trend_score=round(trend_result["score"], 1),
            momentum_score=round(momentum_result["score"], 1),
            volume_score=round(volume_result["score"], 1),
            supply_demand_score=round(supply_demand_result["score"], 1),
            ma_arrangement=trend_result["arrangement"],
            ma_positions=trend_result["ma_positions"],
            price_vs_ma20=trend_result.get("price_vs_ma20"),
            price_vs_ma60=trend_result.get("price_vs_ma60"),
            rsi_14=momentum_result.get("rsi"),
            rsi_status=momentum_result.get("rsi_status", "neutral"),
            macd=momentum_result.get("macd"),
            macd_signal=momentum_result.get("macd_signal"),
            macd_histogram=momentum_result.get("macd_histogram"),
            volume_ratio=volume_result.get("ratio"),
            volume_status=volume_result.get("status", "normal"),
            foreign_trend=supply_demand_result.get("foreign_trend", "neutral"),
            institutional_trend=supply_demand_result.get("institutional_trend", "neutral"),
            foreign_net_20d=supply_demand_result.get("foreign_net"),
            institutional_net_20d=supply_demand_result.get("institutional_net"),
            signals=signals,
            overall_signal=overall_signal,
            recommendation=recommendation
        )

    def _analyze_trend(self, prices: List[float]) -> Dict[str, Any]:
        """추세 분석 (이동평균)"""
        result = {
            "score": 50,
            "arrangement": "mixed",
            "ma_positions": {},
            "signals": []
        }

        if len(prices) < 60:
            return result

        current_price = prices[-1]

        # 이동평균 계산
        ma_values = {}
        for period in self.config.ma_periods:
            if len(prices) >= period:
                ma = sum(prices[-period:]) / period
                ma_values[period] = ma

                pct_diff = ((current_price / ma) - 1) * 100
                result["ma_positions"][f"ma{period}"] = {
                    "value": round(ma, 0),
                    "vs_price": round(pct_diff, 2),
                    "position": "above" if current_price > ma else "below"
                }

        # 가격 vs MA20, MA60 기록
        if 20 in ma_values:
            result["price_vs_ma20"] = round(((current_price / ma_values[20]) - 1) * 100, 2)
        if 60 in ma_values:
            result["price_vs_ma60"] = round(((current_price / ma_values[60]) - 1) * 100, 2)

        # 정배열/역배열 판단
        if len(ma_values) >= 3:
            ma20 = ma_values.get(20, 0)
            ma60 = ma_values.get(60, 0)
            ma120 = ma_values.get(120, ma60)

            if ma20 > ma60 > ma120:
                result["arrangement"] = "bullish_aligned"
            elif ma20 < ma60 < ma120:
                result["arrangement"] = "bearish_aligned"
            else:
                result["arrangement"] = "mixed"

        # 골든크로스/데드크로스 체크 (MA20/MA60)
        if len(prices) >= 61 and 20 in ma_values and 60 in ma_values:
            # 전일 MA 계산
            prev_ma20 = sum(prices[-21:-1]) / 20
            prev_ma60 = sum(prices[-61:-1]) / 60

            ma20 = ma_values[20]
            ma60 = ma_values[60]

            if ma20 > ma60 and prev_ma20 <= prev_ma60:
                result["signals"].append({
                    "type": "golden_cross",
                    "description": "MA20이 MA60을 상향 돌파",
                    "strength": "strong"
                })
            elif ma20 < ma60 and prev_ma20 >= prev_ma60:
                result["signals"].append({
                    "type": "death_cross",
                    "description": "MA20이 MA60을 하향 돌파",
                    "strength": "strong"
                })

        # 점수 계산
        score = 50

        # 정배열/역배열 가감
        if result["arrangement"] == "bullish_aligned":
            score += 25
        elif result["arrangement"] == "bearish_aligned":
            score -= 25

        # 현재가가 MA20 위/아래
        if 20 in ma_values:
            if current_price > ma_values[20]:
                score += 10
            else:
                score -= 10

        # 골든/데드 크로스
        for signal in result["signals"]:
            if signal["type"] == "golden_cross":
                score += 15
            elif signal["type"] == "death_cross":
                score -= 15

        result["score"] = max(0, min(100, score))
        return result

    def _analyze_momentum(self, prices: List[float]) -> Dict[str, Any]:
        """모멘텀 분석 (RSI, MACD)"""
        result = {
            "score": 50,
            "rsi": None,
            "rsi_status": "neutral",
            "macd": None,
            "macd_signal": None,
            "macd_histogram": None,
            "signals": []
        }

        if len(prices) < self.config.rsi_period + 1:
            return result

        # RSI 계산
        rsi = self._calculate_rsi(prices, self.config.rsi_period)
        if rsi is not None:
            result["rsi"] = round(rsi, 1)

            if rsi > self.config.rsi_overbought:
                result["rsi_status"] = "overbought"
                result["signals"].append({
                    "type": "rsi_overbought",
                    "description": f"RSI {rsi:.1f} - 과매수 구간",
                    "strength": "moderate"
                })
            elif rsi < self.config.rsi_oversold:
                result["rsi_status"] = "oversold"
                result["signals"].append({
                    "type": "rsi_oversold",
                    "description": f"RSI {rsi:.1f} - 과매도 구간 (반등 기대)",
                    "strength": "moderate"
                })

        # MACD 계산
        macd_result = self._calculate_macd(prices)
        if macd_result:
            result["macd"] = round(macd_result["macd"], 2)
            result["macd_signal"] = round(macd_result["signal"], 2)
            result["macd_histogram"] = round(macd_result["histogram"], 2)

            # MACD 크로스
            if macd_result.get("bullish_cross"):
                result["signals"].append({
                    "type": "macd_bullish_cross",
                    "description": "MACD가 시그널선을 상향 돌파",
                    "strength": "moderate"
                })
            elif macd_result.get("bearish_cross"):
                result["signals"].append({
                    "type": "macd_bearish_cross",
                    "description": "MACD가 시그널선을 하향 돌파",
                    "strength": "moderate"
                })

        # 점수 계산
        score = 50

        # RSI 점수
        if rsi is not None:
            if rsi < 30:
                score += 20  # 과매도 - 반등 기대
            elif rsi < 40:
                score += 10
            elif rsi > 70:
                score -= 15  # 과매수 - 조정 경계
            elif rsi > 60:
                score -= 5

        # MACD 점수
        if macd_result:
            if macd_result.get("bullish_cross"):
                score += 15
            elif macd_result.get("bearish_cross"):
                score -= 15
            elif macd_result["histogram"] > 0:
                score += 5
            else:
                score -= 5

        result["score"] = max(0, min(100, score))
        return result

    def _analyze_volume(self, volumes: List[int]) -> Dict[str, Any]:
        """거래량 분석"""
        result = {
            "score": 50,
            "ratio": None,
            "status": "normal",
            "signals": []
        }

        if len(volumes) < 20:
            return result

        current_vol = volumes[-1]
        avg_vol = sum(volumes[-20:]) / 20

        if avg_vol > 0:
            ratio = current_vol / avg_vol
            result["ratio"] = round(ratio, 2)

            if ratio > 2.0:
                result["status"] = "surge"
                result["signals"].append({
                    "type": "volume_surge",
                    "description": f"거래량 급증 ({ratio:.1f}배)",
                    "strength": "strong"
                })
            elif ratio > 1.5:
                result["status"] = "above_average"
            elif ratio < 0.5:
                result["status"] = "very_low"
                result["signals"].append({
                    "type": "volume_dry",
                    "description": "거래량 급감",
                    "strength": "weak"
                })
            else:
                result["status"] = "normal"

        # 점수 계산
        score = 50
        if result["ratio"]:
            if result["ratio"] > 1.5:
                score += 15
            elif result["ratio"] > 1.2:
                score += 5
            elif result["ratio"] < 0.5:
                score -= 10

        result["score"] = max(0, min(100, score))
        return result

    def _analyze_supply_demand(self, stock_code: str) -> Dict[str, Any]:
        """수급 분석 (외국인, 기관)"""
        result = {
            "score": 50,
            "foreign_trend": "neutral",
            "institutional_trend": "neutral",
            "foreign_net": None,
            "institutional_net": None,
            "signals": []
        }

        try:
            investor_data = self.krx.get_investor_trading(stock_code)
            if not investor_data:
                return result

            # 20일 누적 순매수
            foreign_net = sum(d.get("foreign_net_buy", 0) for d in investor_data)
            inst_net = sum(d.get("institution_net_buy", 0) for d in investor_data)

            result["foreign_net"] = foreign_net
            result["institutional_net"] = inst_net

            # 추세 판단
            if foreign_net > 10_000_000_000:  # 100억 이상 순매수
                result["foreign_trend"] = "buying"
            elif foreign_net < -10_000_000_000:
                result["foreign_trend"] = "selling"

            if inst_net > 10_000_000_000:
                result["institutional_trend"] = "buying"
            elif inst_net < -10_000_000_000:
                result["institutional_trend"] = "selling"

            # 시그널
            if result["foreign_trend"] == "buying" and result["institutional_trend"] == "buying":
                result["signals"].append({
                    "type": "smart_money_buying",
                    "description": "외국인+기관 동반 순매수",
                    "strength": "strong"
                })
            elif result["foreign_trend"] == "selling" and result["institutional_trend"] == "selling":
                result["signals"].append({
                    "type": "smart_money_selling",
                    "description": "외국인+기관 동반 순매도",
                    "strength": "strong"
                })

            # 점수 계산
            score = 50
            if result["foreign_trend"] == "buying":
                score += 15
            elif result["foreign_trend"] == "selling":
                score -= 15

            if result["institutional_trend"] == "buying":
                score += 10
            elif result["institutional_trend"] == "selling":
                score -= 10

            result["score"] = max(0, min(100, score))

        except Exception as e:
            self.logger.warning(f"수급 분석 실패: {e}")

        return result

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """RSI 계산"""
        if len(prices) < period + 1:
            return None

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

        # 첫 평균
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # EMA 스타일 계산
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices: List[float]) -> Optional[Dict[str, Any]]:
        """MACD 계산"""
        if len(prices) < 26:
            return None

        # EMA 계산
        ema12 = self._calculate_ema(prices, 12)
        ema26 = self._calculate_ema(prices, 26)

        if ema12 is None or ema26 is None:
            return None

        macd_line = ema12 - ema26

        # MACD 히스토리 계산 (시그널용)
        macd_history = []
        ema12_hist = prices[-26]  # 시작점
        ema26_hist = prices[-26]
        k12 = 2 / (12 + 1)
        k26 = 2 / (26 + 1)

        for i in range(-26, 0):
            ema12_hist = prices[i] * k12 + ema12_hist * (1 - k12)
            ema26_hist = prices[i] * k26 + ema26_hist * (1 - k26)
            macd_history.append(ema12_hist - ema26_hist)

        # Signal (MACD의 9일 EMA)
        signal_line = self._calculate_ema(macd_history, 9)

        if signal_line is None:
            return None

        histogram = macd_line - signal_line

        # 전일 값으로 크로스 체크
        prev_macd = macd_history[-2] if len(macd_history) >= 2 else macd_line
        prev_signal = self._calculate_ema(macd_history[:-1], 9) if len(macd_history) > 9 else signal_line

        bullish_cross = macd_line > signal_line and (prev_macd <= prev_signal if prev_signal else False)
        bearish_cross = macd_line < signal_line and (prev_macd >= prev_signal if prev_signal else False)

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
            "bullish_cross": bullish_cross,
            "bearish_cross": bearish_cross
        }

    def _calculate_ema(self, data: List[float], period: int) -> Optional[float]:
        """지수이동평균(EMA) 계산"""
        if len(data) < period:
            return None

        k = 2 / (period + 1)
        ema = sum(data[:period]) / period  # 첫 SMA

        for price in data[period:]:
            ema = price * k + ema * (1 - k)

        return ema

    def _collect_signals(
        self,
        trend: Dict[str, Any],
        momentum: Dict[str, Any],
        volume: Dict[str, Any],
        supply_demand: Dict[str, Any]
    ) -> List[TechnicalSignal]:
        """모든 시그널 수집"""
        signals = []

        for result in [trend, momentum, volume, supply_demand]:
            for s in result.get("signals", []):
                action = "bullish" if "bullish" in s["type"] or "golden" in s["type"] or s["type"] == "rsi_oversold" or s["type"] == "smart_money_buying" else \
                         "bearish" if "bearish" in s["type"] or "death" in s["type"] or s["type"] == "rsi_overbought" or s["type"] == "smart_money_selling" else \
                         "neutral"

                signals.append(TechnicalSignal(
                    signal_type=s["type"],
                    description=s["description"],
                    strength=s["strength"],
                    action=action
                ))

        return signals

    def _create_default_result(self, stock_code: str) -> TechnicalAnalysisResult:
        """기본 결과 생성 (데이터 부족 시)"""
        return TechnicalAnalysisResult(
            stock_code=stock_code,
            stock_name=self.krx._get_stock_name(stock_code),
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            current_price=0,
            total_score=50.0,
            overall_signal="neutral",
            recommendation="데이터 부족으로 분석 불가"
        )
