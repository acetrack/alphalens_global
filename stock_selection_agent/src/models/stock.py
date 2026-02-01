"""
Stock Data Models
종목 관련 데이터 모델 정의
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class Market(Enum):
    """시장 구분"""
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    KONEX = "KONEX"


class InvestmentRating(Enum):
    """투자 의견"""
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"


@dataclass
class Stock:
    """종목 기본 정보"""
    code: str  # 종목코드 (6자리)
    name: str  # 종목명
    market: Market  # 시장 구분

    # 회사 정보 (선택)
    corp_code: Optional[str] = None  # DART 고유번호
    sector: Optional[str] = None  # 업종
    industry: Optional[str] = None  # 세부 산업
    ceo: Optional[str] = None  # 대표자
    established: Optional[date] = None  # 설립일
    listing_date: Optional[date] = None  # 상장일

    def __post_init__(self):
        # 종목코드 6자리 검증
        if len(self.code) != 6:
            raise ValueError(f"종목코드는 6자리여야 합니다: {self.code}")

        # Market enum 변환
        if isinstance(self.market, str):
            self.market = Market(self.market)


@dataclass
class StockPrice:
    """주가 정보"""
    stock_code: str
    trade_date: str  # YYYYMMDD

    # 가격 정보
    close_price: int  # 종가
    open_price: Optional[int] = None  # 시가
    high_price: Optional[int] = None  # 고가
    low_price: Optional[int] = None  # 저가

    # 변동
    change: Optional[int] = None  # 전일대비
    change_rate: Optional[float] = None  # 등락률 (%)

    # 거래량/거래대금
    volume: Optional[int] = None  # 거래량
    trading_value: Optional[int] = None  # 거래대금

    # 시가총액
    market_cap: Optional[int] = None  # 시가총액
    shares_outstanding: Optional[int] = None  # 상장주식수

    # 데이터 신선도
    data_freshness: Optional[Dict[str, Any]] = None

    @property
    def is_fresh(self) -> bool:
        """데이터가 최신인지 확인 (3일 이내)"""
        if not self.data_freshness:
            return False
        return self.data_freshness.get("days_old", 999) <= 3


@dataclass
class StockValuation:
    """종목 밸류에이션 지표"""
    stock_code: str
    trade_date: str

    # 수익성 지표
    eps: Optional[int] = None  # 주당순이익
    bps: Optional[int] = None  # 주당순자산
    dps: Optional[int] = None  # 주당배당금

    # 밸류에이션 배수
    per: Optional[float] = None  # PER
    pbr: Optional[float] = None  # PBR
    dividend_yield: Optional[float] = None  # 배당수익률

    # 추가 지표 (계산 필요)
    ev_ebitda: Optional[float] = None  # EV/EBITDA
    psr: Optional[float] = None  # PSR
    pcr: Optional[float] = None  # PCR


@dataclass
class FinancialStatement:
    """재무제표 데이터"""
    corp_code: str  # DART 고유번호
    stock_code: Optional[str] = None
    bsns_year: str = ""  # 사업연도
    reprt_code: str = ""  # 보고서 코드
    fs_div: str = "CFS"  # 재무제표 구분 (CFS: 연결, OFS: 별도)

    # 손익계산서
    revenue: Optional[int] = None  # 매출액
    gross_profit: Optional[int] = None  # 매출총이익
    operating_profit: Optional[int] = None  # 영업이익
    net_income: Optional[int] = None  # 당기순이익

    # 재무상태표
    total_assets: Optional[int] = None  # 자산총계
    total_liabilities: Optional[int] = None  # 부채총계
    total_equity: Optional[int] = None  # 자본총계

    # 현금흐름
    operating_cash_flow: Optional[int] = None  # 영업활동현금흐름
    investing_cash_flow: Optional[int] = None  # 투자활동현금흐름
    financing_cash_flow: Optional[int] = None  # 재무활동현금흐름

    # 계산된 비율
    op_margin: Optional[float] = None  # 영업이익률
    net_margin: Optional[float] = None  # 순이익률
    roe: Optional[float] = None  # ROE
    roa: Optional[float] = None  # ROA
    debt_ratio: Optional[float] = None  # 부채비율
    current_ratio: Optional[float] = None  # 유동비율

    # 메타데이터
    data_date: Optional[str] = None  # 데이터 조회일

    def calculate_ratios(self):
        """비율 지표 계산"""
        # 영업이익률
        if self.revenue and self.operating_profit:
            self.op_margin = round(self.operating_profit / self.revenue * 100, 2)

        # 순이익률
        if self.revenue and self.net_income:
            self.net_margin = round(self.net_income / self.revenue * 100, 2)

        # ROE
        if self.total_equity and self.net_income:
            self.roe = round(self.net_income / self.total_equity * 100, 2)

        # ROA
        if self.total_assets and self.net_income:
            self.roa = round(self.net_income / self.total_assets * 100, 2)

        # 부채비율
        if self.total_equity and self.total_liabilities:
            self.debt_ratio = round(self.total_liabilities / self.total_equity * 100, 2)


@dataclass
class InvestorTrading:
    """투자자별 매매동향"""
    stock_code: str
    trade_date: str

    # 순매수 금액/수량
    foreign_net_buy: Optional[int] = None  # 외국인
    institution_net_buy: Optional[int] = None  # 기관
    individual_net_buy: Optional[int] = None  # 개인

    # 매수/매도 분리 (선택)
    foreign_buy: Optional[int] = None
    foreign_sell: Optional[int] = None
    institution_buy: Optional[int] = None
    institution_sell: Optional[int] = None


@dataclass
class ScreeningResult:
    """스크리닝 결과"""
    stock: Stock
    price: StockPrice
    valuation: Optional[StockValuation] = None
    financial: Optional[FinancialStatement] = None

    # 스크리닝 점수
    value_score: Optional[float] = None  # 가치 점수
    quality_score: Optional[float] = None  # 품질 점수
    momentum_score: Optional[float] = None  # 모멘텀 점수
    growth_score: Optional[float] = None  # 성장성 점수
    total_score: Optional[float] = None  # 종합 점수

    # 통과 여부
    passed: bool = False
    pass_reasons: List[str] = field(default_factory=list)
    fail_reasons: List[str] = field(default_factory=list)


@dataclass
class DataFreshness:
    """데이터 신선도 정보"""
    # 기본 필드는 모두 Optional로 변경
    analysis_date: Optional[str] = None  # 분석 기준일
    price_data_date: Optional[str] = None  # 주가 데이터 기준일
    price_data_age_days: Optional[int] = None  # 주가 데이터 경과일
    valuation_data_date: Optional[str] = None  # 밸류에이션 데이터 기준일
    valuation_data_age_days: Optional[int] = None  # 밸류에이션 데이터 경과일
    financial_data_date: Optional[str] = None  # 재무 데이터 기준일
    analyst_data_date: Optional[str] = None  # 애널리스트 데이터 기준일

    price_freshness: str = ""  # 주가 신선도 상태
    financial_freshness: str = ""  # 재무 신선도 상태
    analyst_freshness: str = ""  # 애널리스트 신선도 상태

    warning_level: str = "LOW"  # LOW, MEDIUM, HIGH
    warning_message: Optional[str] = None  # 경고 메시지

    warnings: List[str] = field(default_factory=list)  # 경고 메시지 목록

    def check_all(self) -> bool:
        """모든 데이터가 허용 범위 내인지 확인"""
        return len(self.warnings) == 0

    def to_markdown_table(self) -> str:
        """마크다운 테이블 형식으로 반환"""
        table = """## 데이터 기준일 안내

| 데이터 유형 | 기준일 | 신선도 |
|------------|--------|--------|
| **분석 기준일** | {analysis_date} | - |
| 주가 데이터 | {price_date} | {price_status} |
| 재무 데이터 | {financial_date} | {financial_status} |
| 애널리스트 | {analyst_date} | {analyst_status} |
""".format(
            analysis_date=self.analysis_date,
            price_date=self.price_data_date,
            price_status=self.price_freshness,
            financial_date=self.financial_data_date or "N/A",
            financial_status=self.financial_freshness or "N/A",
            analyst_date=self.analyst_data_date or "N/A",
            analyst_status=self.analyst_freshness or "N/A"
        )

        if self.warnings:
            table += "\n### 경고\n"
            for warning in self.warnings:
                table += f"- {warning}\n"

        return table
