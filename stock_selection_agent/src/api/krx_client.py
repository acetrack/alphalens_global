"""
KRX (한국거래소) Data Client
pykrx 라이브러리 기반

무료 - 별도 인증 불필요
- 주가, 거래량, 시가총액
- 투자자별 매매동향 (외국인, 기관)
- PER/PBR/배당수익률
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from pykrx import stock as krx


@dataclass
class KrxConfig:
    """KRX Data 설정"""
    timeout: int = 30
    retry_count: int = 3


class KrxApiError(Exception):
    """KRX API 오류"""
    pass


class KrxClient:
    """
    한국거래소 데이터 클라이언트 (pykrx 기반)

    주요 기능:
    - KOSPI/KOSDAQ 전체 종목 조회
    - 개별 종목 시세 조회
    - 투자자별 매매동향
    - PER/PBR/배당수익률

    사용법:
        client = KrxClient()

        # 삼성전자 시세 조회
        price = client.get_stock_price("005930")

        # 삼성전자 밸류에이션 조회
        valuation = client.get_stock_valuation("005930")
    """

    def __init__(self, config: Optional[KrxConfig] = None):
        """KRX 클라이언트 초기화"""
        self.config = config or KrxConfig()
        self.logger = logging.getLogger(__name__)
        self._ticker_cache: Dict[str, str] = {}  # 종목코드 -> 종목명 캐시

    # =========================================================================
    # 종목 목록
    # =========================================================================

    def get_kospi_stocks(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        코스피 전체 종목 시세 조회

        Args:
            trade_date: 조회일자 (YYYYMMDD). 미입력시 최근 거래일

        Returns:
            {"stocks": [...], "trade_date": "...", "count": N}
        """
        if not trade_date:
            trade_date = self._get_latest_trade_date()

        try:
            # 코스피 종목 목록
            tickers = krx.get_market_ticker_list(trade_date, market="KOSPI")

            # OHLCV 데이터 조회
            ohlcv = krx.get_market_ohlcv_by_ticker(trade_date, market="KOSPI")

            # 시가총액 조회
            cap = krx.get_market_cap_by_ticker(trade_date, market="KOSPI")

            stocks = []
            for ticker in tickers:
                name = krx.get_market_ticker_name(ticker)
                self._ticker_cache[ticker] = name

                row_ohlcv = ohlcv.loc[ticker] if ticker in ohlcv.index else None
                row_cap = cap.loc[ticker] if ticker in cap.index else None

                stocks.append({
                    "stock_code": ticker,
                    "stock_name": name,
                    "market": "KOSPI",
                    "close_price": int(row_ohlcv["종가"]) if row_ohlcv is not None else 0,
                    "change": int(row_ohlcv["등락"]) if row_ohlcv is not None and "등락" in row_ohlcv.index else 0,
                    "change_rate": round(row_ohlcv["등락률"], 2) if row_ohlcv is not None and "등락률" in row_ohlcv.index else 0,
                    "open_price": int(row_ohlcv["시가"]) if row_ohlcv is not None else 0,
                    "high_price": int(row_ohlcv["고가"]) if row_ohlcv is not None else 0,
                    "low_price": int(row_ohlcv["저가"]) if row_ohlcv is not None else 0,
                    "volume": int(row_ohlcv["거래량"]) if row_ohlcv is not None else 0,
                    "trading_value": int(row_ohlcv["거래대금"]) if row_ohlcv is not None else 0,
                    "market_cap": int(row_cap["시가총액"]) if row_cap is not None else 0,
                    "shares_outstanding": int(row_cap["상장주식수"]) if row_cap is not None else 0,
                    "trade_date": trade_date,
                    "data_freshness": self._calculate_freshness(trade_date)
                })

            return {
                "stocks": stocks,
                "trade_date": trade_date,
                "count": len(stocks)
            }

        except Exception as e:
            self.logger.error(f"KOSPI 종목 조회 실패: {e}")
            return {"error": str(e), "stocks": []}

    def get_kosdaq_stocks(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        코스닥 전체 종목 시세 조회

        Args:
            trade_date: 조회일자 (YYYYMMDD)

        Returns:
            {"stocks": [...], "trade_date": "...", "count": N}
        """
        if not trade_date:
            trade_date = self._get_latest_trade_date()

        try:
            tickers = krx.get_market_ticker_list(trade_date, market="KOSDAQ")
            ohlcv = krx.get_market_ohlcv_by_ticker(trade_date, market="KOSDAQ")
            cap = krx.get_market_cap_by_ticker(trade_date, market="KOSDAQ")

            stocks = []
            for ticker in tickers:
                name = krx.get_market_ticker_name(ticker)
                self._ticker_cache[ticker] = name

                row_ohlcv = ohlcv.loc[ticker] if ticker in ohlcv.index else None
                row_cap = cap.loc[ticker] if ticker in cap.index else None

                stocks.append({
                    "stock_code": ticker,
                    "stock_name": name,
                    "market": "KOSDAQ",
                    "close_price": int(row_ohlcv["종가"]) if row_ohlcv is not None else 0,
                    "change": int(row_ohlcv["등락"]) if row_ohlcv is not None and "등락" in row_ohlcv.index else 0,
                    "change_rate": round(row_ohlcv["등락률"], 2) if row_ohlcv is not None and "등락률" in row_ohlcv.index else 0,
                    "open_price": int(row_ohlcv["시가"]) if row_ohlcv is not None else 0,
                    "high_price": int(row_ohlcv["고가"]) if row_ohlcv is not None else 0,
                    "low_price": int(row_ohlcv["저가"]) if row_ohlcv is not None else 0,
                    "volume": int(row_ohlcv["거래량"]) if row_ohlcv is not None else 0,
                    "trading_value": int(row_ohlcv["거래대금"]) if row_ohlcv is not None else 0,
                    "market_cap": int(row_cap["시가총액"]) if row_cap is not None else 0,
                    "shares_outstanding": int(row_cap["상장주식수"]) if row_cap is not None else 0,
                    "trade_date": trade_date,
                    "data_freshness": self._calculate_freshness(trade_date)
                })

            return {
                "stocks": stocks,
                "trade_date": trade_date,
                "count": len(stocks)
            }

        except Exception as e:
            self.logger.error(f"KOSDAQ 종목 조회 실패: {e}")
            return {"error": str(e), "stocks": []}

    # =========================================================================
    # 개별 종목 시세
    # =========================================================================

    def get_stock_price(self, stock_code: str, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        개별 종목 현재가 조회

        Args:
            stock_code: 종목코드 (6자리)
            trade_date: 조회일자 (기본: 최근 거래일)

        Returns:
            종목 시세 정보
        """
        if not trade_date:
            trade_date = self._get_latest_trade_date()

        try:
            # 종목명 조회
            stock_name = self._get_stock_name(stock_code)

            # 일별 OHLCV (최근 7일)
            end_dt = datetime.strptime(trade_date, "%Y%m%d")
            start_dt = end_dt - timedelta(days=7)
            df = krx.get_market_ohlcv_by_date(
                start_dt.strftime("%Y%m%d"),
                trade_date,
                stock_code
            )

            if df.empty:
                return {"error": f"종목코드 {stock_code}의 시세 정보를 찾을 수 없습니다."}

            row = df.iloc[-1]
            actual_date = df.index[-1].strftime("%Y%m%d")

            # 시가총액 조회
            try:
                cap_df = krx.get_market_cap_by_date(actual_date, actual_date, stock_code)
                market_cap = int(cap_df.iloc[-1]["시가총액"]) if not cap_df.empty else 0
            except Exception:
                market_cap = 0

            # 등락률 계산 (컬럼이 없는 경우)
            change_rate = 0
            if len(df) >= 2:
                prev_close = df.iloc[-2]["종가"]
                if prev_close > 0:
                    change_rate = round((row["종가"] - prev_close) / prev_close * 100, 2)

            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "close_price": int(row["종가"]),
                "change": int(row["종가"] - df.iloc[-2]["종가"]) if len(df) >= 2 else 0,
                "change_rate": change_rate,
                "open_price": int(row["시가"]),
                "high_price": int(row["고가"]),
                "low_price": int(row["저가"]),
                "volume": int(row["거래량"]),
                "trading_value": int(row.get("거래대금", 0)) if "거래대금" in row.index else 0,
                "market_cap": market_cap,
                "trade_date": actual_date,
                "freshness": self._calculate_freshness(actual_date)
            }

        except Exception as e:
            self.logger.error(f"종목 {stock_code} 시세 조회 실패: {e}")
            return {"error": str(e)}

    def get_stock_price_history(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        개별 종목 일별 시세 히스토리

        Args:
            stock_code: 종목코드
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)

        Returns:
            일별 시세 목록
        """
        if not end_date:
            end_date = self._get_latest_trade_date()
        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y%m%d") - timedelta(days=30)
            start_date = start_dt.strftime("%Y%m%d")

        try:
            df = krx.get_market_ohlcv_by_date(start_date, end_date, stock_code)

            result = []
            for date_idx, row in df.iterrows():
                trade_date = date_idx.strftime("%Y%m%d")
                result.append({
                    "stock_code": stock_code,
                    "trade_date": trade_date,
                    "close_price": int(row["종가"]),
                    "change_rate": round(row.get("등락률", 0), 2),
                    "open_price": int(row["시가"]),
                    "high_price": int(row["고가"]),
                    "low_price": int(row["저가"]),
                    "volume": int(row["거래량"]),
                })

            return result

        except Exception as e:
            self.logger.error(f"종목 {stock_code} 시세 히스토리 조회 실패: {e}")
            return []

    # =========================================================================
    # 밸류에이션 (PER/PBR/배당수익률)
    # =========================================================================

    def get_stock_valuation(self, stock_code: str, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        개별 종목 PER/PBR/배당수익률 조회

        Args:
            stock_code: 종목코드

        Returns:
            종목 밸류에이션 정보
        """
        if not trade_date:
            trade_date = self._get_latest_trade_date()

        try:
            # 기본 정보 (종목명 등)
            stock_name = self._get_stock_name(stock_code)

            # PER/PBR/배당수익률
            df = krx.get_market_fundamental_by_date(trade_date, trade_date, stock_code)

            if df.empty:
                # 전일 데이터 시도
                prev_date = (datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
                df = krx.get_market_fundamental_by_date(prev_date, prev_date, stock_code)
                trade_date = prev_date

            if df.empty:
                return {"error": f"종목코드 {stock_code}의 밸류에이션 정보를 찾을 수 없습니다."}

            row = df.iloc[-1]

            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "bps": int(row.get("BPS", 0)),
                "per": round(row.get("PER", 0), 2),
                "pbr": round(row.get("PBR", 0), 2),
                "eps": int(row.get("EPS", 0)),
                "dps": int(row.get("DPS", 0)),  # 주당배당금
                "dividend_yield": round(row.get("DIV", 0), 2),  # 배당수익률
                "trade_date": trade_date,
                "freshness": self._calculate_freshness(trade_date)
            }

        except Exception as e:
            self.logger.error(f"종목 {stock_code} 밸류에이션 조회 실패: {e}")
            return {"error": str(e)}

    def get_market_valuation(self, market: str = "KOSPI", trade_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        전체 시장 PER/PBR 조회

        Args:
            market: 시장 구분 ("KOSPI" 또는 "KOSDAQ")
            trade_date: 조회일자

        Returns:
            종목별 밸류에이션 목록
        """
        if not trade_date:
            trade_date = self._get_latest_trade_date()

        try:
            df = krx.get_market_fundamental_by_ticker(trade_date, market=market)

            result = []
            for ticker, row in df.iterrows():
                result.append({
                    "stock_code": ticker,
                    "stock_name": self._get_stock_name(ticker),
                    "bps": int(row.get("BPS", 0)),
                    "per": round(row.get("PER", 0), 2),
                    "pbr": round(row.get("PBR", 0), 2),
                    "eps": int(row.get("EPS", 0)),
                    "dps": int(row.get("DPS", 0)),
                    "dividend_yield": round(row.get("DIV", 0), 2),
                    "trade_date": trade_date
                })

            return result

        except Exception as e:
            self.logger.error(f"시장 {market} 밸류에이션 조회 실패: {e}")
            return []

    # =========================================================================
    # 투자자별 매매동향
    # =========================================================================

    def get_investor_trading(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        투자자별 매매동향 조회 (일별 순매수 금액)

        Args:
            stock_code: 종목코드
            start_date: 시작일
            end_date: 종료일

        Returns:
            투자자별 순매수량 목록 (일별)
        """
        if not end_date:
            end_date = self._get_latest_trade_date()
        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y%m%d") - timedelta(days=20)
            start_date = start_dt.strftime("%Y%m%d")

        try:
            # get_market_trading_value_by_date: 일별 투자자별 순매수 금액
            # Columns: 기관합계, 기타법인, 개인, 외국인합계, 전체
            df = krx.get_market_trading_value_by_date(
                start_date, end_date, stock_code
            )

            if df.empty:
                return []

            result = []
            for date_idx, row in df.iterrows():
                # 기관합계 순매수
                institution_net = int(row.get("기관합계", 0))
                # 외국인합계 순매수
                foreign_net = int(row.get("외국인합계", 0))
                # 개인 순매수
                individual_net = int(row.get("개인", 0))

                result.append({
                    "stock_code": stock_code,
                    "trade_date": date_idx.strftime("%Y%m%d"),
                    "institution_net_buy": institution_net,
                    "foreign_net_buy": foreign_net,
                    "individual_net_buy": individual_net,
                })

            return result

        except Exception as e:
            self.logger.error(f"종목 {stock_code} 투자자 동향 조회 실패: {e}")
            return []

    # =========================================================================
    # 시가총액 상위
    # =========================================================================

    def get_market_cap_ranking(
        self,
        market: str = "ALL",
        top_n: int = 100,
        trade_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        시가총액 상위 종목 조회

        Args:
            market: 시장 구분 ("ALL", "KOSPI", "KOSDAQ")
            top_n: 상위 N개
            trade_date: 조회일자

        Returns:
            시가총액 상위 종목 목록
        """
        if not trade_date:
            trade_date = self._get_latest_trade_date()

        try:
            if market == "KOSPI":
                cap_df = krx.get_market_cap_by_ticker(trade_date, market="KOSPI")
            elif market == "KOSDAQ":
                cap_df = krx.get_market_cap_by_ticker(trade_date, market="KOSDAQ")
            else:
                kospi_df = krx.get_market_cap_by_ticker(trade_date, market="KOSPI")
                kosdaq_df = krx.get_market_cap_by_ticker(trade_date, market="KOSDAQ")
                import pandas as pd
                cap_df = pd.concat([kospi_df, kosdaq_df])

            # 시가총액 기준 정렬
            cap_df = cap_df.sort_values("시가총액", ascending=False).head(top_n)

            result = []
            for ticker, row in cap_df.iterrows():
                result.append({
                    "stock_code": ticker,
                    "stock_name": self._get_stock_name(ticker),
                    "market_cap": int(row["시가총액"]),
                    "shares_outstanding": int(row["상장주식수"]),
                    "trade_date": trade_date
                })

            return result

        except Exception as e:
            self.logger.error(f"시가총액 상위 조회 실패: {e}")
            return []

    # =========================================================================
    # NAV 계산용 시가총액 조회
    # =========================================================================

    def get_stock_market_cap(
        self,
        stock_code: str,
        trade_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        개별 종목 시가총액 조회 (NAV 계산용)

        Args:
            stock_code: 종목코드 (6자리)
            trade_date: 조회일자 (기본: 최근 거래일)

        Returns:
            시가총액 정보 (원 단위)
        """
        if not trade_date:
            trade_date = self._get_latest_trade_date()

        try:
            stock_name = self._get_stock_name(stock_code)

            # 시가총액 조회
            cap_df = krx.get_market_cap_by_date(trade_date, trade_date, stock_code)

            if cap_df.empty:
                # 전일 시도
                prev_date = (datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
                cap_df = krx.get_market_cap_by_date(prev_date, prev_date, stock_code)
                trade_date = prev_date

            if cap_df.empty:
                return {"error": f"종목코드 {stock_code}의 시가총액 정보를 찾을 수 없습니다."}

            row = cap_df.iloc[-1]

            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "market_cap": int(row["시가총액"]),
                "shares_outstanding": int(row["상장주식수"]),
                "trade_date": trade_date,
                "freshness": self._calculate_freshness(trade_date)
            }

        except Exception as e:
            self.logger.error(f"종목 {stock_code} 시가총액 조회 실패: {e}")
            return {"error": str(e)}

    def get_multiple_market_caps(
        self,
        stock_codes: List[str],
        trade_date: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        여러 종목의 시가총액 일괄 조회 (NAV 계산용)

        Args:
            stock_codes: 종목코드 리스트
            trade_date: 조회일자

        Returns:
            종목코드별 시가총액 정보 딕셔너리
        """
        if not trade_date:
            trade_date = self._get_latest_trade_date()

        result = {}

        try:
            # 전체 시장 시가총액 조회 (더 효율적)
            kospi_cap = krx.get_market_cap_by_ticker(trade_date, market="KOSPI")
            kosdaq_cap = krx.get_market_cap_by_ticker(trade_date, market="KOSDAQ")

            for code in stock_codes:
                if code in kospi_cap.index:
                    row = kospi_cap.loc[code]
                    result[code] = {
                        "stock_code": code,
                        "stock_name": self._get_stock_name(code),
                        "market_cap": int(row["시가총액"]),
                        "shares_outstanding": int(row["상장주식수"]),
                        "market": "KOSPI",
                        "trade_date": trade_date
                    }
                elif code in kosdaq_cap.index:
                    row = kosdaq_cap.loc[code]
                    result[code] = {
                        "stock_code": code,
                        "stock_name": self._get_stock_name(code),
                        "market_cap": int(row["시가총액"]),
                        "shares_outstanding": int(row["상장주식수"]),
                        "market": "KOSDAQ",
                        "trade_date": trade_date
                    }
                else:
                    result[code] = {"error": f"종목코드 {code}를 찾을 수 없습니다."}

            return result

        except Exception as e:
            self.logger.error(f"시가총액 일괄 조회 실패: {e}")
            return {code: {"error": str(e)} for code in stock_codes}

    # =========================================================================
    # 유틸리티
    # =========================================================================

    def _get_latest_trade_date(self) -> str:
        """최근 거래일 반환 (주말 및 장 마감 전 고려)"""
        today = datetime.now()

        # 장 마감 전이면 전일 데이터 사용 (15:30 이전)
        # 안전하게 항상 전일 데이터 사용
        target = today - timedelta(days=1)

        # 주말이면 금요일로
        if target.weekday() == 5:  # 토요일
            target -= timedelta(days=1)
        elif target.weekday() == 6:  # 일요일
            target -= timedelta(days=2)

        return target.strftime("%Y%m%d")

    def _get_stock_name(self, stock_code: str) -> str:
        """종목코드로 종목명 조회"""
        if stock_code in self._ticker_cache:
            return self._ticker_cache[stock_code]

        try:
            name = krx.get_market_ticker_name(stock_code)
            self._ticker_cache[stock_code] = name
            return name
        except Exception:
            return stock_code

    def _calculate_freshness(self, data_date: str) -> Dict[str, Any]:
        """데이터 신선도 계산"""
        try:
            data_dt = datetime.strptime(data_date, "%Y%m%d")
            today = datetime.now()
            days_old = (today - data_dt).days

            if days_old <= 1:
                status, label = "fresh", "최신"
            elif days_old <= 3:
                status, label = "recent", "최근"
            elif days_old <= 7:
                status, label = "acceptable", "허용범위"
            elif days_old <= 14:
                status, label = "stale", f"⚠️ {days_old}일 전"
            else:
                status, label = "very_stale", f"🚨 {days_old}일 전"

            return {
                "days_old": days_old,
                "status": status,
                "label": label,
                "data_date": data_date,
                "check_date": today.strftime("%Y%m%d")
            }
        except ValueError:
            return {
                "days_old": None,
                "status": "unknown",
                "label": "알 수 없음",
                "data_date": data_date
            }
