"""
Risk Agent - 리스크 분석 에이전트
시장 리스크, 신용 리스크, 유동성 리스크, 집중 리스크 분석
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
import math
import numpy as np

from ..api.krx_client import KrxClient


def norm_ppf(p: float) -> float:
    """
    정규분포의 역함수 (근사치)
    scipy.stats.norm.ppf의 간단한 대체 구현
    """
    # Beasley-Springer-Moro 알고리즘 근사
    if p <= 0 or p >= 1:
        raise ValueError("p must be between 0 and 1")

    if p < 0.5:
        # Lower tail
        sign = -1
        p = 1 - p
    else:
        sign = 1

    # Coefficients
    a = [2.50662823884, -18.61500062529, 41.39119773534, -25.44106049637]
    b = [-8.47351093090, 23.08336743743, -21.06224101826, 3.13082909833]
    c = [0.3374754822726147, 0.9761690190917186, 0.1607979714918209,
         0.0276438810333863, 0.0038405729373609, 0.0003951896511919,
         0.0000321767881768, 0.0000002888167364, 0.0000003960315187]

    y = math.log(-math.log(1 - p))
    x = 0
    for i in range(len(c)):
        x += c[i] * (y ** i)

    return sign * x


@dataclass
class RiskAnalysisConfig:
    """리스크 분석 설정"""
    # 가중치
    market_risk_weight: float = 0.35  # 시장 리스크
    credit_risk_weight: float = 0.30  # 신용 리스크
    liquidity_risk_weight: float = 0.20  # 유동성 리스크
    concentration_risk_weight: float = 0.15  # 집중 리스크

    # Beta 계산 기간
    beta_period_weeks: int = 156  # 3년

    # VaR/CVaR 설정
    var_confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    var_period_days: int = 252  # 1년

    # MDD 계산 기간
    mdd_period_days: int = 756  # 3년

    # 신용 리스크 임계값
    z_score_safe: float = 2.99
    z_score_grey: float = 1.81
    debt_to_equity_high: float = 2.0
    debt_to_equity_moderate: float = 1.5
    interest_coverage_low: float = 2.0
    interest_coverage_moderate: float = 3.0

    # 유동성 임계값 (원)
    liquidity_excellent: int = 10_000_000_000  # 100억
    liquidity_good: int = 5_000_000_000  # 50억
    liquidity_moderate: int = 1_000_000_000  # 10억
    liquidity_poor: int = 500_000_000  # 5억


@dataclass
class RiskFactor:
    """개별 리스크 요인"""
    name: str
    value: float
    risk_level: str  # "low", "moderate", "moderate_high", "high", "very_high"
    interpretation: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAnalysisResult:
    """리스크 분석 결과"""
    stock_code: str
    stock_name: str
    analysis_date: str

    # 종합 리스크 점수 (0-100, 높을수록 위험)
    total_risk_score: float = 50.0
    risk_grade: str = "Moderate Risk"

    # 세부 점수
    market_risk_score: float = 50.0
    credit_risk_score: float = 50.0
    liquidity_risk_score: float = 50.0
    concentration_risk_score: float = 50.0

    # 시장 리스크
    beta: Optional[float] = None
    beta_adjusted: Optional[float] = None
    annual_volatility: Optional[float] = None
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None
    max_drawdown: Optional[float] = None
    mdd_recovery_days: Optional[int] = None

    # 신용 리스크
    z_score: Optional[float] = None
    z_score_zone: str = "unknown"  # "safe", "grey", "distress"
    debt_to_equity: Optional[float] = None
    net_debt_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    credit_red_flags: List[str] = field(default_factory=list)

    # 유동성 리스크
    avg_daily_trading_value: Optional[int] = None
    liquidity_grade: str = "C"  # "A", "B", "C", "D", "F"
    turnover_ratio: Optional[float] = None
    free_float_ratio: Optional[float] = None
    bid_ask_spread: Optional[float] = None

    # 집중 리스크
    largest_shareholder_pct: Optional[float] = None
    foreign_ownership_pct: Optional[float] = None
    concentration_risks: List[Dict[str, str]] = field(default_factory=list)

    # 스트레스 테스트
    stress_test_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 주요 리스크 요인
    key_risks: List[str] = field(default_factory=list)

    # 리스크 조정 기대수익률
    risk_adjusted_expected_return: Optional[float] = None


class RiskAgent:
    """
    리스크 분석 에이전트

    기능:
    - 시장 리스크: Beta, Volatility, VaR, CVaR, MDD
    - 신용 리스크: Altman Z-Score, 부채비율, 이자보상배율
    - 유동성 리스크: 거래대금, 회전율, 호가 스프레드
    - 집중 리스크: 지분 구조, 사업 집중도
    - 스트레스 테스트: 시나리오 분석

    사용법:
        agent = RiskAgent(krx_client=krx)
        result = agent.analyze("005930", financial_data=financial_data)
    """

    def __init__(
        self,
        krx_client: Optional[KrxClient] = None,
        config: Optional[RiskAnalysisConfig] = None
    ):
        """
        리스크 분석 에이전트 초기화

        Args:
            krx_client: KRX 데이터 클라이언트
            config: 분석 설정
        """
        self.krx = krx_client or KrxClient()
        self.config = config or RiskAnalysisConfig()
        self.logger = logging.getLogger(__name__)

    def analyze(
        self,
        stock_code: str,
        financial_data: Optional[Dict[str, Any]] = None,
        technical_data: Optional[Dict[str, Any]] = None
    ) -> RiskAnalysisResult:
        """
        종목 리스크 분석 실행

        Args:
            stock_code: 종목코드 (6자리)
            financial_data: 재무 분석 데이터 (옵션)
            technical_data: 기술적 분석 데이터 (옵션)

        Returns:
            리스크 분석 결과
        """
        self.logger.info(f"리스크 분석 시작: {stock_code}")

        # 0. 날짜 확인
        analysis_date = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().year
        self.logger.info(f"분석 기준일: {analysis_date}, 현재 연도: {current_year}")

        # 1. 기본 정보
        stock_name = self.krx._get_stock_name(stock_code)

        # 2. 가격 히스토리 조회
        from datetime import timedelta
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=self.config.mdd_period_days)).strftime("%Y%m%d")
        price_history = self.krx.get_stock_price_history(stock_code, start_date=start_date, end_date=end_date)

        if not price_history or len(price_history) < 20:
            self.logger.warning(f"가격 데이터 부족: {stock_code}")
            return self._create_default_result(stock_code, stock_name, analysis_date)

        # 3. 시장 리스크 분석
        market_risk = self._analyze_market_risk(price_history)

        # 4. 신용 리스크 분석
        credit_risk = self._analyze_credit_risk(stock_code, financial_data)

        # 5. 유동성 리스크 분석
        liquidity_risk = self._analyze_liquidity_risk(stock_code, price_history)

        # 6. 집중 리스크 분석
        concentration_risk = self._analyze_concentration_risk(stock_code)

        # 7. 스트레스 테스트
        stress_test = self._perform_stress_test(
            stock_code,
            price_history,
            market_risk.get("beta", 1.0),
            credit_risk
        )

        # 8. 종합 리스크 점수 계산
        total_score, risk_grade = self._calculate_total_risk_score(
            market_risk,
            credit_risk,
            liquidity_risk,
            concentration_risk
        )

        # 9. 주요 리스크 식별
        key_risks = self._identify_key_risks(
            market_risk,
            credit_risk,
            liquidity_risk,
            concentration_risk,
            stress_test
        )

        return RiskAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            analysis_date=analysis_date,
            total_risk_score=round(total_score, 1),
            risk_grade=risk_grade,
            market_risk_score=round(market_risk["score"], 1),
            credit_risk_score=round(credit_risk["score"], 1),
            liquidity_risk_score=round(liquidity_risk["score"], 1),
            concentration_risk_score=round(concentration_risk["score"], 1),
            beta=market_risk.get("beta"),
            beta_adjusted=market_risk.get("beta_adjusted"),
            annual_volatility=market_risk.get("annual_volatility"),
            var_95=market_risk.get("var_95"),
            cvar_95=market_risk.get("cvar_95"),
            max_drawdown=market_risk.get("max_drawdown"),
            mdd_recovery_days=market_risk.get("recovery_days"),
            z_score=credit_risk.get("z_score"),
            z_score_zone=credit_risk.get("zone", "unknown"),
            debt_to_equity=credit_risk.get("debt_to_equity"),
            net_debt_ratio=credit_risk.get("net_debt_ratio"),
            interest_coverage=credit_risk.get("interest_coverage"),
            debt_to_ebitda=credit_risk.get("debt_to_ebitda"),
            credit_red_flags=credit_risk.get("red_flags", []),
            avg_daily_trading_value=liquidity_risk.get("avg_daily_trading_value"),
            liquidity_grade=liquidity_risk.get("liquidity_grade", "C"),
            turnover_ratio=liquidity_risk.get("turnover_ratio"),
            free_float_ratio=liquidity_risk.get("free_float_ratio"),
            bid_ask_spread=liquidity_risk.get("bid_ask_spread"),
            largest_shareholder_pct=concentration_risk.get("largest_shareholder"),
            foreign_ownership_pct=concentration_risk.get("foreign_ownership"),
            concentration_risks=concentration_risk.get("risks", []),
            stress_test_results=stress_test,
            key_risks=key_risks
        )

    def _analyze_market_risk(self, price_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """시장 리스크 분석"""
        result = {
            "score": 50,
            "beta": None,
            "beta_adjusted": None,
            "annual_volatility": None,
            "var_95": None,
            "cvar_95": None,
            "max_drawdown": None,
            "recovery_days": None
        }

        if len(price_history) < 20:
            return result

        prices = [p["close_price"] for p in price_history]

        # 1. Volatility 계산
        if len(prices) >= 252:
            returns = [(prices[i] / prices[i-1] - 1) for i in range(1, min(253, len(prices)))]
            daily_vol = np.std(returns)
            annual_vol = daily_vol * math.sqrt(252)
            result["annual_volatility"] = round(annual_vol, 4)

            # VaR 95% (Parametric)
            mean_return = np.mean(returns)
            z_95 = norm_ppf(0.05)  # -1.645
            var_95 = -(mean_return + z_95 * daily_vol)
            result["var_95"] = round(var_95, 4)

            # CVaR 95% (Historical)
            returns_array = np.array(returns)
            var_threshold = np.percentile(returns_array, 5)
            tail_losses = returns_array[returns_array <= var_threshold]
            if len(tail_losses) > 0:
                cvar_95 = -np.mean(tail_losses)
                result["cvar_95"] = round(cvar_95, 4)

        # 2. Beta 계산 (시장지수 대비)
        # 간단한 추정: KOSPI와의 상관관계 (실제로는 시장 데이터 필요)
        # 여기서는 변동성 기반 추정치 사용
        if result["annual_volatility"]:
            market_vol = 0.20  # KOSPI 평균 변동성 가정
            estimated_beta = result["annual_volatility"] / market_vol
            result["beta"] = round(estimated_beta, 2)

            # Blume Adjustment
            adjusted_beta = 0.67 * estimated_beta + 0.33 * 1.0
            result["beta_adjusted"] = round(adjusted_beta, 2)

        # 3. Maximum Drawdown
        if len(prices) >= 100:
            peak = prices[0]
            max_dd = 0
            dd_start_idx = 0
            dd_end_idx = 0
            current_dd_start = 0

            for i, price in enumerate(prices):
                if price > peak:
                    peak = price
                    current_dd_start = i

                drawdown = (peak - price) / peak
                if drawdown > max_dd:
                    max_dd = drawdown
                    dd_start_idx = current_dd_start
                    dd_end_idx = i

            result["max_drawdown"] = round(max_dd, 4)

            # 회복 기간 계산
            if dd_end_idx < len(prices) - 1:
                peak_price = prices[dd_start_idx]
                for i in range(dd_end_idx + 1, len(prices)):
                    if prices[i] >= peak_price:
                        result["recovery_days"] = i - dd_end_idx
                        break

        # 점수 계산 (낮을수록 좋음)
        score = 50

        # Beta 점수 (0.5 ~ 2.0 범위)
        if result["beta_adjusted"]:
            if result["beta_adjusted"] > 1.5:
                score += 25  # 고위험
            elif result["beta_adjusted"] > 1.2:
                score += 15
            elif result["beta_adjusted"] < 0.8:
                score -= 15  # 저위험

        # Volatility 점수
        if result["annual_volatility"]:
            if result["annual_volatility"] > 0.50:
                score += 30
            elif result["annual_volatility"] > 0.35:
                score += 20
            elif result["annual_volatility"] < 0.20:
                score -= 10

        # MDD 점수
        if result["max_drawdown"]:
            if result["max_drawdown"] > 0.50:
                score += 25
            elif result["max_drawdown"] > 0.35:
                score += 15
            elif result["max_drawdown"] < 0.20:
                score -= 10

        result["score"] = max(0, min(100, score))
        return result

    def _analyze_credit_risk(
        self,
        stock_code: str,
        financial_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """신용 리스크 분석"""
        result = {
            "score": 50,
            "z_score": None,
            "zone": "unknown",
            "debt_to_equity": None,
            "net_debt_ratio": None,
            "interest_coverage": None,
            "debt_to_ebitda": None,
            "red_flags": []
        }

        if not financial_data:
            self.logger.warning(f"재무 데이터 없음: {stock_code}")
            return result

        try:
            # 1. Altman Z-Score 계산
            total_assets = financial_data.get("total_assets", 0)
            if total_assets > 0:
                x1 = financial_data.get("working_capital", 0) / total_assets
                x2 = financial_data.get("retained_earnings", 0) / total_assets
                x3 = financial_data.get("ebit", 0) / total_assets

                market_cap = financial_data.get("market_cap", 0)
                total_liabilities = financial_data.get("total_liabilities", 1)
                x4 = market_cap / total_liabilities if total_liabilities > 0 else 0

                x5 = financial_data.get("revenue", 0) / total_assets

                z_score = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
                result["z_score"] = round(z_score, 2)

                if z_score > self.config.z_score_safe:
                    result["zone"] = "safe"
                elif z_score > self.config.z_score_grey:
                    result["zone"] = "grey"
                else:
                    result["zone"] = "distress"
                    result["red_flags"].append(f"Z-Score {z_score:.2f} - 파산 위험 높음")

            # 2. 부채 관련 지표
            equity = financial_data.get("equity", 1)
            total_debt = financial_data.get("total_debt", 0)

            if equity > 0:
                debt_to_equity = total_debt / equity
                result["debt_to_equity"] = round(debt_to_equity, 2)

                if debt_to_equity > self.config.debt_to_equity_high:
                    result["red_flags"].append(f"부채비율 {debt_to_equity:.1f} - 200% 초과")

                # 순차입금비율
                cash = financial_data.get("cash", 0)
                net_debt_ratio = (total_debt - cash) / equity
                result["net_debt_ratio"] = round(net_debt_ratio, 2)

            # 3. 이자보상배율
            ebit = financial_data.get("ebit", 0)
            interest_expense = financial_data.get("interest_expense", 0)

            if interest_expense > 0:
                icr = ebit / interest_expense
                result["interest_coverage"] = round(icr, 1)

                if icr < self.config.interest_coverage_low:
                    result["red_flags"].append(f"이자보상배율 {icr:.1f} - 2배 미만")
            else:
                result["interest_coverage"] = float('inf')

            # 4. Debt/EBITDA
            ebitda = financial_data.get("ebitda", 0)
            if ebitda > 0:
                debt_to_ebitda = total_debt / ebitda
                result["debt_to_ebitda"] = round(debt_to_ebitda, 2)

                if debt_to_ebitda > 4.0:
                    result["red_flags"].append(f"Debt/EBITDA {debt_to_ebitda:.1f} - 4배 초과")

            # 점수 계산
            score = 50

            # Z-Score 점수
            if result["zone"] == "distress":
                score += 30
            elif result["zone"] == "grey":
                score += 15
            elif result["zone"] == "safe":
                score -= 15

            # 부채비율 점수
            if result["debt_to_equity"]:
                if result["debt_to_equity"] > 2.0:
                    score += 25
                elif result["debt_to_equity"] > 1.5:
                    score += 15
                elif result["debt_to_equity"] < 0.5:
                    score -= 10

            # 이자보상배율 점수
            if result["interest_coverage"]:
                if result["interest_coverage"] != float('inf'):
                    if result["interest_coverage"] < 2:
                        score += 25
                    elif result["interest_coverage"] < 3:
                        score += 10
                    elif result["interest_coverage"] > 10:
                        score -= 15

            result["score"] = max(0, min(100, score))

        except Exception as e:
            self.logger.error(f"신용 리스크 분석 실패: {e}")

        return result

    def _analyze_liquidity_risk(
        self,
        stock_code: str,
        price_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """유동성 리스크 분석"""
        result = {
            "score": 50,
            "avg_daily_trading_value": None,
            "liquidity_grade": "C",
            "turnover_ratio": None,
            "free_float_ratio": None,
            "bid_ask_spread": None
        }

        if len(price_history) < 20:
            return result

        try:
            # 1. 일평균 거래대금 (최근 20일)
            recent_data = price_history[-20:]
            trading_values = []

            for day in recent_data:
                volume = day.get("volume", 0)
                price = day.get("close_price", 0)
                trading_value = volume * price
                trading_values.append(trading_value)

            avg_daily_value = sum(trading_values) / len(trading_values) if trading_values else 0
            result["avg_daily_trading_value"] = int(avg_daily_value)

            # 유동성 등급
            if avg_daily_value >= self.config.liquidity_excellent:
                result["liquidity_grade"] = "A"
                score = 20
            elif avg_daily_value >= self.config.liquidity_good:
                result["liquidity_grade"] = "B"
                score = 30
            elif avg_daily_value >= self.config.liquidity_moderate:
                result["liquidity_grade"] = "C"
                score = 50
            elif avg_daily_value >= self.config.liquidity_poor:
                result["liquidity_grade"] = "D"
                score = 70
            else:
                result["liquidity_grade"] = "F"
                score = 90

            # 2. 회전율 추정 (간략 버전)
            history_to_use = price_history[-252:] if len(price_history) >= 252 else price_history
            total_volume = sum(d.get("volume", 0) for d in history_to_use)
            # 유통주식수는 실제로는 별도 조회 필요, 여기서는 추정
            # turnover_ratio = 연간 거래량 / 유통주식수

            # 3. 호가 스프레드 (실시간 데이터 필요, 여기서는 생략)
            # result["bid_ask_spread"] = ...

            result["score"] = score

        except Exception as e:
            self.logger.error(f"유동성 리스크 분석 실패: {e}")

        return result

    def _analyze_concentration_risk(self, stock_code: str) -> Dict[str, Any]:
        """집중 리스크 분석"""
        result = {
            "score": 50,
            "largest_shareholder": None,
            "foreign_ownership": None,
            "risks": []
        }

        try:
            # 실제로는 지분 구조 데이터를 KRX나 DART에서 조회해야 함
            # 여기서는 기본값으로 처리

            # 지분 데이터가 없으면 중립 점수 유지
            result["score"] = 50

        except Exception as e:
            self.logger.error(f"집중 리스크 분석 실패: {e}")

        return result

    def _perform_stress_test(
        self,
        stock_code: str,
        price_history: List[Dict[str, Any]],
        beta: float,
        credit_risk: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """스트레스 테스트"""
        results = {}

        if not price_history:
            return results

        current_price = price_history[-1]["close_price"]

        try:
            # 1. 시장 급락 시나리오 (-20%)
            if beta is not None:
                market_crash_loss = beta * (-0.20) * 100
                results["market_crash"] = {
                    "description": "시장 급락 (-20%)",
                    "estimated_loss_pct": round(market_crash_loss, 2),
                    "severity": "high" if market_crash_loss < -25 else "moderate" if market_crash_loss < -15 else "low"
                }
            else:
                results["market_crash"] = {
                    "description": "시장 급락 (-20%)",
                    "estimated_loss_pct": -20.0,
                    "severity": "moderate"
                }

            # 2. 금리 충격 (200bp 인상)
            debt_ratio = credit_risk.get("debt_to_equity")
            if debt_ratio is not None:
                rate_shock_loss = -0.02 * debt_ratio * 5 * 100  # 단순 추정
            else:
                rate_shock_loss = -10.0  # 기본값
            results["interest_rate_shock"] = {
                "description": "금리 200bp 인상",
                "estimated_loss_pct": round(rate_shock_loss, 2),
                "severity": "high" if rate_shock_loss < -25 else "moderate" if rate_shock_loss < -10 else "low"
            }

            # 3. 원화 약세 시나리오
            # 수출/수입 데이터가 필요하므로 여기서는 중립 가정
            results["currency_depreciation"] = {
                "description": "원화 15% 약세",
                "estimated_loss_pct": 0.0,
                "severity": "neutral"
            }

            # 4. 섹터 침체
            sector_beta = 0.8  # 섹터 베타 가정
            sector_loss = sector_beta * (-0.15) * 100
            results["sector_downturn"] = {
                "description": "섹터 언더퍼폼 (-15%)",
                "estimated_loss_pct": round(sector_loss, 2),
                "severity": "moderate"
            }

        except Exception as e:
            self.logger.error(f"스트레스 테스트 실패: {e}")

        return results

    def _calculate_total_risk_score(
        self,
        market_risk: Dict[str, Any],
        credit_risk: Dict[str, Any],
        liquidity_risk: Dict[str, Any],
        concentration_risk: Dict[str, Any]
    ) -> tuple[float, str]:
        """종합 리스크 점수 계산"""
        total_score = (
            market_risk["score"] * self.config.market_risk_weight +
            credit_risk["score"] * self.config.credit_risk_weight +
            liquidity_risk["score"] * self.config.liquidity_risk_weight +
            concentration_risk["score"] * self.config.concentration_risk_weight
        )

        # 리스크 등급
        if total_score > 70:
            risk_grade = "High Risk"
        elif total_score > 50:
            risk_grade = "Moderate-High Risk"
        elif total_score > 30:
            risk_grade = "Moderate Risk"
        else:
            risk_grade = "Low Risk"

        return total_score, risk_grade

    def _identify_key_risks(
        self,
        market_risk: Dict[str, Any],
        credit_risk: Dict[str, Any],
        liquidity_risk: Dict[str, Any],
        concentration_risk: Dict[str, Any],
        stress_test: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """주요 리스크 요인 식별"""
        key_risks = []

        # 시장 리스크
        if market_risk.get("annual_volatility", 0) > 0.40:
            key_risks.append("높은 주가 변동성")

        if market_risk.get("max_drawdown", 0) > 0.40:
            key_risks.append("큰 최대 낙폭 (MDD)")

        # 신용 리스크
        if credit_risk.get("zone") == "distress":
            key_risks.append("파산 위험 (낮은 Z-Score)")

        for flag in credit_risk.get("red_flags", []):
            key_risks.append(flag)

        # 유동성 리스크
        if liquidity_risk.get("liquidity_grade") in ["D", "F"]:
            key_risks.append("낮은 유동성")

        # 스트레스 테스트
        for scenario, data in stress_test.items():
            if data.get("severity") == "high":
                key_risks.append(f"{data['description']}: {data['estimated_loss_pct']}% 손실 예상")

        return key_risks[:5]  # 상위 5개만 반환

    def _create_default_result(
        self,
        stock_code: str,
        stock_name: str,
        analysis_date: str
    ) -> RiskAnalysisResult:
        """기본 결과 생성 (데이터 부족 시)"""
        return RiskAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            analysis_date=analysis_date,
            total_risk_score=50.0,
            risk_grade="Unknown (데이터 부족)",
            key_risks=["데이터 부족으로 리스크 분석 불가"]
        )


def normalize_score(value: float, min_val: float, max_val: float) -> float:
    """값을 0-100 점수로 정규화"""
    if value <= min_val:
        return 0
    elif value >= max_val:
        return 100
    else:
        return ((value - min_val) / (max_val - min_val)) * 100


def grade_to_score(grade: str) -> float:
    """등급을 점수로 변환"""
    grade_map = {
        "A": 10,
        "B": 30,
        "C": 50,
        "D": 70,
        "F": 90
    }
    return grade_map.get(grade, 50)
