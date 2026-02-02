"""
Screening Agent - 멀티팩터 퀀트 스크리닝
KRX API를 사용한 자동화된 종목 스크리닝
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from ..api.krx_client import KrxClient, KrxApiError
from ..models.stock import Stock, StockPrice, StockValuation, ScreeningResult, Market


@dataclass
class ScreeningCriteria:
    """스크리닝 기준"""
    # 시가총액
    min_market_cap: int = 100_000_000_000  # 1000억 이상
    max_market_cap: Optional[int] = None

    # 거래대금
    min_trading_value: int = 1_000_000_000  # 일평균 10억 이상

    # 밸류에이션
    max_per: float = 30.0  # PER 30 이하
    min_per: float = 0.0  # PER 0 이상 (적자 기업 제외)
    min_pbr: float = 0.0  # PBR 0 이상 (자본잠식 기업 제외)
    max_pbr: float = 5.0  # PBR 5 이하

    # 배당
    min_dividend_yield: float = 0.0  # 배당수익률 0% 이상

    # 수익성
    min_roe: Optional[float] = None  # ROE 기준

    # 제외 조건
    exclude_financial: bool = True  # 금융주 제외
    exclude_holding: bool = True  # 지주회사 제외


class ScreeningAgent:
    """
    멀티팩터 퀀트 스크리닝 에이전트

    기능:
    - KOSPI/KOSDAQ 전체 종목 조회
    - 시가총액, 거래대금, PER, PBR 기준 필터링
    - 멀티팩터 점수 계산
    - 상위 종목 선정

    사용법:
        agent = ScreeningAgent()
        results = agent.run_screening(
            market="KOSPI",
            criteria=ScreeningCriteria(min_market_cap=500_000_000_000)
        )
    """

    def __init__(self, krx_client: Optional[KrxClient] = None):
        """
        스크리닝 에이전트 초기화

        Args:
            krx_client: KRX 클라이언트. 미입력시 새로 생성
        """
        self.krx = krx_client or KrxClient()
        self.logger = logging.getLogger(__name__)

    def run_screening(
        self,
        market: str = "ALL",
        criteria: Optional[ScreeningCriteria] = None,
        top_n: int = 100
    ) -> List[ScreeningResult]:
        """
        스크리닝 실행

        Args:
            market: 시장 구분 ("ALL", "KOSPI", "KOSDAQ")
            criteria: 스크리닝 기준
            top_n: 최종 선정 종목 수

        Returns:
            스크리닝 통과 종목 목록
        """
        criteria = criteria or ScreeningCriteria()
        analysis_date = datetime.now().strftime("%Y-%m-%d")

        self.logger.info(f"스크리닝 시작: market={market}, top_n={top_n}")

        # 1. 전체 종목 시세 조회
        all_stocks = self._get_all_stocks(market)
        self.logger.info(f"전체 종목 수: {len(all_stocks)}")

        # 2. 기본 필터링 (시가총액, 거래대금)
        filtered = self._apply_basic_filters(all_stocks, criteria)
        self.logger.info(f"기본 필터 통과: {len(filtered)}")

        # 3. 밸류에이션 데이터 조회
        valuations = self._get_valuations(market)

        # 4. 밸류에이션 필터링
        results = self._apply_valuation_filters(filtered, valuations, criteria)
        self.logger.info(f"밸류에이션 필터 통과: {len(results)}")

        # 5. 멀티팩터 점수 계산
        scored_results = self._calculate_scores(results)

        # 6. 정렬 및 상위 N개 선정
        sorted_results = sorted(
            scored_results,
            key=lambda x: x.total_score or 0,
            reverse=True
        )[:top_n]

        self.logger.info(f"최종 선정: {len(sorted_results)}개 종목")

        return sorted_results

    def _get_all_stocks(self, market: str) -> List[Dict[str, Any]]:
        """전체 종목 시세 조회"""
        try:
            if market.upper() == "KOSPI":
                result = self.krx.get_kospi_stocks()
                return result.get("stocks", [])
            elif market.upper() == "KOSDAQ":
                result = self.krx.get_kosdaq_stocks()
                return result.get("stocks", [])
            else:
                # 전체 시장
                kospi_result = self.krx.get_kospi_stocks()
                kosdaq_result = self.krx.get_kosdaq_stocks()
                kospi_stocks = kospi_result.get("stocks", [])
                kosdaq_stocks = kosdaq_result.get("stocks", [])
                return kospi_stocks + kosdaq_stocks
        except KrxApiError as e:
            self.logger.error(f"종목 조회 실패: {e}")
            return []

    def _apply_basic_filters(
        self,
        stocks: List[Dict[str, Any]],
        criteria: ScreeningCriteria
    ) -> List[Dict[str, Any]]:
        """기본 필터 적용 (시가총액, 거래대금)"""
        filtered = []

        for stock in stocks:
            market_cap = stock.get("market_cap") or 0
            trading_value = stock.get("trading_value") or 0

            # 시가총액 필터
            if market_cap < criteria.min_market_cap:
                continue
            if criteria.max_market_cap and market_cap > criteria.max_market_cap:
                continue

            # 거래대금 필터
            if trading_value < criteria.min_trading_value:
                continue

            filtered.append(stock)

        return filtered

    def _get_valuations(self, market: str) -> Dict[str, Dict[str, Any]]:
        """밸류에이션 데이터 조회"""
        valuations = {}

        try:
            if market.upper() in ["KOSPI", "ALL"]:
                kospi_val = self.krx.get_market_valuation("KOSPI")
                for v in kospi_val:
                    code = v.get("stock_code", "")
                    if code:
                        valuations[code] = v

            if market.upper() in ["KOSDAQ", "ALL"]:
                kosdaq_val = self.krx.get_market_valuation("KOSDAQ")
                for v in kosdaq_val:
                    code = v.get("stock_code", "")
                    if code:
                        valuations[code] = v

        except KrxApiError as e:
            self.logger.warning(f"밸류에이션 조회 실패: {e}")

        return valuations

    def _apply_valuation_filters(
        self,
        stocks: List[Dict[str, Any]],
        valuations: Dict[str, Dict[str, Any]],
        criteria: ScreeningCriteria
    ) -> List[ScreeningResult]:
        """밸류에이션 필터 적용"""
        results = []

        for stock_data in stocks:
            code = stock_data.get("stock_code", "")
            name = stock_data.get("stock_name", "")
            market_str = stock_data.get("market", "KOSPI")

            # 밸류에이션 데이터 매칭
            val_data = valuations.get(code, {})
            per = val_data.get("per")
            pbr = val_data.get("pbr")
            div_yield = val_data.get("dividend_yield", 0)

            # 필터링 사유 기록
            pass_reasons = []
            fail_reasons = []

            # PER 필터
            if per is not None:
                if per <= 0:
                    fail_reasons.append(f"적자 기업 (PER: {per})")
                    continue
                elif per > criteria.max_per:
                    fail_reasons.append(f"PER 고평가 ({per} > {criteria.max_per})")
                    continue
                else:
                    pass_reasons.append(f"PER 적정 ({per})")

            # PBR 필터
            if pbr is not None:
                if pbr < criteria.min_pbr:
                    fail_reasons.append(f"PBR 저평가/자본잠식 ({pbr} < {criteria.min_pbr})")
                    continue
                elif pbr > criteria.max_pbr:
                    fail_reasons.append(f"PBR 고평가 ({pbr} > {criteria.max_pbr})")
                    continue
                else:
                    pass_reasons.append(f"PBR 적정 ({pbr})")

            # 배당수익률 필터
            if div_yield is not None and div_yield >= criteria.min_dividend_yield:
                pass_reasons.append(f"배당수익률 {div_yield}%")

            # Stock 객체 생성
            try:
                market_enum = Market(market_str)
            except ValueError:
                market_enum = Market.KOSPI

            stock_obj = Stock(
                code=code,
                name=name,
                market=market_enum
            )

            # StockPrice 객체 생성
            price_obj = StockPrice(
                stock_code=code,
                trade_date=stock_data.get("trade_date", ""),
                close_price=stock_data.get("close_price", 0),
                open_price=stock_data.get("open_price"),
                high_price=stock_data.get("high_price"),
                low_price=stock_data.get("low_price"),
                change=stock_data.get("change"),
                change_rate=stock_data.get("change_rate"),
                volume=stock_data.get("volume"),
                trading_value=stock_data.get("trading_value"),
                market_cap=stock_data.get("market_cap"),
                data_freshness=stock_data.get("data_freshness")
            )

            # StockValuation 객체 생성
            val_obj = StockValuation(
                stock_code=code,
                trade_date=val_data.get("trade_date", ""),
                eps=val_data.get("eps"),
                bps=val_data.get("bps"),
                dps=val_data.get("dps"),
                per=per,
                pbr=pbr,
                dividend_yield=div_yield
            )

            # ScreeningResult 생성
            result = ScreeningResult(
                stock=stock_obj,
                price=price_obj,
                valuation=val_obj,
                passed=True,
                pass_reasons=pass_reasons,
                fail_reasons=fail_reasons
            )

            results.append(result)

        return results

    def _calculate_scores(self, results: List[ScreeningResult]) -> List[ScreeningResult]:
        """멀티팩터 점수 계산"""
        for result in results:
            # Value Score (저평가 = 높은 점수)
            per = result.valuation.per if result.valuation else None
            pbr = result.valuation.pbr if result.valuation else None

            if per and per > 0:
                # PER 역수 기반 점수 (낮을수록 높은 점수)
                result.value_score = min(100, max(0, (30 - per) / 30 * 100))
            else:
                result.value_score = 0

            # Quality Score (시가총액 기반 임시 점수)
            market_cap = result.price.market_cap or 0
            if market_cap > 0:
                # 로그 스케일로 정규화
                import math
                log_cap = math.log10(market_cap / 1_000_000_000)  # 10억 단위
                result.quality_score = min(100, max(0, log_cap * 20))
            else:
                result.quality_score = 0

            # Momentum Score (등락률 기반)
            change_rate = result.price.change_rate or 0
            result.momentum_score = min(100, max(0, 50 + change_rate * 5))

            # Growth Score (배당수익률 기반 임시)
            div_yield = result.valuation.dividend_yield if result.valuation else 0
            result.growth_score = min(100, max(0, div_yield * 20))

            # Total Score (가중 평균)
            weights = {
                "value": 0.35,
                "quality": 0.25,
                "momentum": 0.20,
                "growth": 0.20
            }

            result.total_score = (
                (result.value_score or 0) * weights["value"] +
                (result.quality_score or 0) * weights["quality"] +
                (result.momentum_score or 0) * weights["momentum"] +
                (result.growth_score or 0) * weights["growth"]
            )

        return results

    def get_market_cap_ranking(
        self,
        market: str = "ALL",
        top_n: int = 50
    ) -> List[Dict[str, Any]]:
        """
        시가총액 상위 종목 조회

        Args:
            market: 시장 구분
            top_n: 상위 N개

        Returns:
            시가총액 상위 종목 목록
        """
        return self.krx.get_market_cap_ranking(market, top_n)

    def export_results(
        self,
        results: List[ScreeningResult],
        output_path: str,
        format: str = "json"
    ):
        """
        스크리닝 결과 저장

        Args:
            results: 스크리닝 결과
            output_path: 저장 경로
            format: 저장 형식 ("json", "csv")
        """
        import json

        if format == "json":
            data = {
                "screening_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_count": len(results),
                "results": [
                    {
                        "rank": i + 1,
                        "stock_code": r.stock.code,
                        "stock_name": r.stock.name,
                        "market": r.stock.market.value,
                        "close_price": r.price.close_price,
                        "market_cap": r.price.market_cap,
                        "per": r.valuation.per if r.valuation else None,
                        "pbr": r.valuation.pbr if r.valuation else None,
                        "total_score": round(r.total_score, 2) if r.total_score else None,
                        "value_score": round(r.value_score, 2) if r.value_score else None,
                        "quality_score": round(r.quality_score, 2) if r.quality_score else None,
                        "data_freshness": r.price.data_freshness
                    }
                    for i, r in enumerate(results)
                ]
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"결과 저장 완료: {output_path}")
