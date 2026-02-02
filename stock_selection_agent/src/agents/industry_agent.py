"""
Industry Agent - 업종/섹터 분석
DART API 및 KRX 데이터를 활용한 업종 분석
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

from ..api.dart_client import DartClient
from ..api.krx_client import KrxClient


@dataclass
class IndustryAnalysisConfig:
    """업종 분석 설정"""
    peer_comparison_weight: float = 0.4  # 동종업계 비교 가중치
    sector_outlook_weight: float = 0.3  # 업종 전망 가중치
    market_position_weight: float = 0.3  # 시장 내 위치 가중치


@dataclass
class IndustryAnalysisResult:
    """업종 분석 결과"""
    stock_code: str
    stock_name: str
    industry_code: str
    industry_name: str
    sector_name: str

    # 업종 평균 대비 비교
    sector_avg_per: Optional[float] = None
    sector_avg_pbr: Optional[float] = None
    per_vs_sector: Optional[float] = None  # +: 고평가, -: 저평가
    pbr_vs_sector: Optional[float] = None

    # 업종 내 순위
    market_cap_rank_in_sector: Optional[int] = None
    total_peers_in_sector: Optional[int] = None

    # 점수
    peer_comparison_score: float = 50.0
    sector_outlook_score: float = 50.0
    market_position_score: float = 50.0
    total_score: float = 50.0

    # 코멘트
    analysis_comment: str = ""


class IndustryAgent:
    """
    업종/섹터 분석 에이전트

    기능:
    - DART API로 기업 업종 정보 조회
    - 동종업계 평균 밸류에이션 비교
    - 업종 내 시가총액 순위 분석
    - 업종 전망 평가

    사용법:
        agent = IndustryAgent(dart_client=dart, krx_client=krx)
        result = agent.analyze("005930")  # 삼성전자
    """

    # KSIC (한국표준산업분류) 업종코드 -> 섹터 매핑
    # 대분류 기준 (첫 2자리)
    SECTOR_MAPPING = {
        # 제조업
        "26": ("전자부품/컴퓨터", "IT/전자"),
        "27": ("의료/정밀기기", "헬스케어"),
        "28": ("전기장비", "산업재"),
        "29": ("기타기계/장비", "산업재"),
        "30": ("자동차/트레일러", "자동차"),
        "31": ("운송장비", "산업재"),
        "20": ("화학제품", "소재"),
        "21": ("의약품", "헬스케어"),
        "22": ("고무/플라스틱", "소재"),
        "23": ("비금속광물", "소재"),
        "24": ("1차금속", "소재"),
        "25": ("금속가공", "산업재"),
        "10": ("식료품", "필수소비재"),
        "11": ("음료", "필수소비재"),
        "13": ("섬유제품", "경기소비재"),
        "14": ("의복/의류", "경기소비재"),
        "17": ("펄프/종이", "소재"),
        "18": ("인쇄/기록매체", "경기소비재"),
        "19": ("석유정제/코크스", "에너지"),
        # 서비스업
        "58": ("출판업", "커뮤니케이션"),
        "59": ("영상/오디오", "커뮤니케이션"),
        "60": ("방송업", "커뮤니케이션"),
        "61": ("통신업", "커뮤니케이션"),
        "62": ("컴퓨터프로그래밍", "IT/소프트웨어"),
        "63": ("정보서비스업", "IT/소프트웨어"),
        "64": ("금융업", "금융"),
        "65": ("보험/연금", "금융"),
        "66": ("금융/보험관련", "금융"),
        "68": ("부동산업", "부동산"),
        "41": ("건설업", "건설"),
        "45": ("자동차판매", "유통"),
        "46": ("도매업", "유통"),
        "47": ("소매업", "유통"),
        "49": ("육상운송", "운송"),
        "50": ("수상운송", "운송"),
        "51": ("항공운송", "운송"),
        "52": ("창고/운송관련", "운송"),
        "35": ("전기/가스", "유틸리티"),
        "36": ("수도사업", "유틸리티"),
        "37": ("하수/폐기물", "유틸리티"),
    }

    # 업종별 기본 전망 점수 (0-100, 시장 성장성 기반)
    SECTOR_OUTLOOK = {
        "IT/전자": 70,
        "IT/소프트웨어": 80,
        "헬스케어": 75,
        "자동차": 60,
        "금융": 55,
        "소재": 50,
        "산업재": 55,
        "필수소비재": 50,
        "경기소비재": 55,
        "에너지": 45,
        "커뮤니케이션": 60,
        "유틸리티": 45,
        "부동산": 40,
        "건설": 45,
        "유통": 50,
        "운송": 50,
    }

    def __init__(
        self,
        dart_client: Optional[DartClient] = None,
        krx_client: Optional[KrxClient] = None,
        config: Optional[IndustryAnalysisConfig] = None
    ):
        """
        업종 분석 에이전트 초기화

        Args:
            dart_client: DART API 클라이언트
            krx_client: KRX 데이터 클라이언트
            config: 분석 설정
        """
        self.dart = dart_client
        self.krx = krx_client or KrxClient()
        self.config = config or IndustryAnalysisConfig()
        self.logger = logging.getLogger(__name__)

        # 업종별 종목 캐시
        self._sector_stocks_cache: Dict[str, List[Dict[str, Any]]] = {}

    def analyze(self, stock_code: str) -> IndustryAnalysisResult:
        """
        종목의 업종 분석 실행

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            업종 분석 결과
        """
        self.logger.info(f"업종 분석 시작: {stock_code}")

        # 1. 기업 정보 조회 (업종코드 포함)
        company_info = self._get_company_info(stock_code)
        industry_code = company_info.get("induty_code", "")
        stock_name = company_info.get("corp_name", stock_code)

        # 2. 업종/섹터 매핑
        industry_name, sector_name = self._map_industry_to_sector(industry_code)

        # 3. 동종업계 비교 분석
        peer_analysis = self._analyze_peers(stock_code, industry_code, sector_name)

        # 4. 업종 전망 점수
        sector_outlook_score = self.SECTOR_OUTLOOK.get(sector_name, 50)

        # 5. 시장 내 위치 분석
        market_position = self._analyze_market_position(stock_code, sector_name)

        # 6. 종합 점수 계산
        peer_score = peer_analysis.get("score", 50)
        position_score = market_position.get("score", 50)

        total_score = (
            peer_score * self.config.peer_comparison_weight +
            sector_outlook_score * self.config.sector_outlook_weight +
            position_score * self.config.market_position_weight
        )

        # 7. 분석 코멘트 생성
        comment = self._generate_comment(
            stock_name, sector_name, peer_analysis, sector_outlook_score, market_position
        )

        return IndustryAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            industry_code=industry_code,
            industry_name=industry_name,
            sector_name=sector_name,
            sector_avg_per=peer_analysis.get("sector_avg_per"),
            sector_avg_pbr=peer_analysis.get("sector_avg_pbr"),
            per_vs_sector=peer_analysis.get("per_vs_sector"),
            pbr_vs_sector=peer_analysis.get("pbr_vs_sector"),
            market_cap_rank_in_sector=market_position.get("rank"),
            total_peers_in_sector=market_position.get("total"),
            peer_comparison_score=peer_score,
            sector_outlook_score=sector_outlook_score,
            market_position_score=position_score,
            total_score=round(total_score, 1),
            analysis_comment=comment
        )

    def _get_company_info(self, stock_code: str) -> Dict[str, Any]:
        """기업 정보 조회 (DART API)"""
        if not self.dart:
            return {"induty_code": "", "corp_name": stock_code}

        try:
            corp_code = self.dart.get_corp_code_by_stock_code(stock_code)
            if corp_code:
                info = self.dart.get_company_info(corp_code)
                return info
        except Exception as e:
            self.logger.warning(f"기업 정보 조회 실패: {e}")

        return {"induty_code": "", "corp_name": stock_code}

    def _map_industry_to_sector(self, industry_code: str) -> tuple:
        """업종코드를 섹터로 매핑"""
        if not industry_code:
            return ("기타", "기타")

        # 첫 2자리로 대분류 섹터 확인
        prefix = str(industry_code)[:2]

        if prefix in self.SECTOR_MAPPING:
            return self.SECTOR_MAPPING[prefix]

        # 매핑되지 않은 경우
        return (f"업종코드 {industry_code}", "기타")

    def _analyze_peers(
        self,
        stock_code: str,
        industry_code: str,
        sector_name: str
    ) -> Dict[str, Any]:
        """동종업계 비교 분석"""
        result = {
            "score": 50,
            "sector_avg_per": None,
            "sector_avg_pbr": None,
            "per_vs_sector": None,
            "pbr_vs_sector": None
        }

        try:
            # 현재 종목의 밸류에이션
            stock_val = self.krx.get_stock_valuation(stock_code)
            stock_per = stock_val.get("per", 0)
            stock_pbr = stock_val.get("pbr", 0)

            if not stock_per or stock_per <= 0:
                return result

            # 전체 시장 밸류에이션 조회
            kospi_val = self.krx.get_market_valuation("KOSPI")
            kosdaq_val = self.krx.get_market_valuation("KOSDAQ")
            all_valuations = kospi_val + kosdaq_val

            # 섹터 평균 계산 (업종코드 기반 필터링이 어려우므로 전체 시장 평균 사용)
            # TODO: 업종별 종목 목록을 별도로 관리하여 정확한 섹터 평균 계산
            valid_pers = [v["per"] for v in all_valuations if v.get("per") and 0 < v["per"] < 100]
            valid_pbrs = [v["pbr"] for v in all_valuations if v.get("pbr") and 0 < v["pbr"] < 10]

            if valid_pers:
                sector_avg_per = sum(valid_pers) / len(valid_pers)
                result["sector_avg_per"] = round(sector_avg_per, 2)
                result["per_vs_sector"] = round(stock_per - sector_avg_per, 2)

            if valid_pbrs:
                sector_avg_pbr = sum(valid_pbrs) / len(valid_pbrs)
                result["sector_avg_pbr"] = round(sector_avg_pbr, 2)
                result["pbr_vs_sector"] = round(stock_pbr - sector_avg_pbr, 2)

            # 점수 계산 (저평가일수록 높은 점수)
            score = 50
            if result["per_vs_sector"] is not None:
                # PER이 섹터 평균보다 낮으면 가점
                per_diff_pct = (result["per_vs_sector"] / sector_avg_per) * 100 if sector_avg_per else 0
                score += min(25, max(-25, -per_diff_pct))  # -25% ~ +25%

            if result["pbr_vs_sector"] is not None:
                # PBR이 섹터 평균보다 낮으면 가점
                pbr_diff_pct = (result["pbr_vs_sector"] / sector_avg_pbr) * 100 if sector_avg_pbr else 0
                score += min(15, max(-15, -pbr_diff_pct * 0.5))  # -15% ~ +15%

            result["score"] = max(0, min(100, round(score, 1)))

        except Exception as e:
            self.logger.warning(f"동종업계 분석 실패: {e}")

        return result

    def _analyze_market_position(
        self,
        stock_code: str,
        sector_name: str
    ) -> Dict[str, Any]:
        """시장 내 위치 분석"""
        result = {
            "rank": None,
            "total": None,
            "score": 50
        }

        try:
            # 시가총액 순위 조회
            market_cap_ranking = self.krx.get_market_cap_ranking("ALL", top_n=500)

            if not market_cap_ranking:
                return result

            # 현재 종목 순위 찾기
            for i, stock in enumerate(market_cap_ranking, 1):
                if stock.get("stock_code") == stock_code:
                    result["rank"] = i
                    result["total"] = len(market_cap_ranking)
                    break

            # 순위 기반 점수 (상위일수록 높은 점수)
            if result["rank"]:
                rank_percentile = (result["total"] - result["rank"]) / result["total"] * 100
                result["score"] = max(30, min(90, 40 + rank_percentile * 0.5))

        except Exception as e:
            self.logger.warning(f"시장 위치 분석 실패: {e}")

        return result

    def _generate_comment(
        self,
        stock_name: str,
        sector_name: str,
        peer_analysis: Dict[str, Any],
        sector_outlook_score: float,
        market_position: Dict[str, Any]
    ) -> str:
        """분석 코멘트 생성"""
        comments = []

        # 섹터 정보
        comments.append(f"{stock_name}은(는) {sector_name} 섹터에 속합니다.")

        # 밸류에이션 비교
        per_vs = peer_analysis.get("per_vs_sector")
        if per_vs is not None:
            if per_vs < -5:
                comments.append(f"시장 평균 대비 PER이 {abs(per_vs):.1f}배 저평가 상태입니다.")
            elif per_vs > 5:
                comments.append(f"시장 평균 대비 PER이 {per_vs:.1f}배 고평가 상태입니다.")
            else:
                comments.append("밸류에이션은 시장 평균 수준입니다.")

        # 시장 위치
        rank = market_position.get("rank")
        total = market_position.get("total")
        if rank and total:
            if rank <= 50:
                comments.append(f"시가총액 기준 상위 {rank}위로 대형주에 해당합니다.")
            elif rank <= 200:
                comments.append(f"시가총액 기준 {rank}위로 중형주에 해당합니다.")

        # 섹터 전망
        if sector_outlook_score >= 70:
            comments.append(f"{sector_name} 섹터는 성장 전망이 긍정적입니다.")
        elif sector_outlook_score <= 45:
            comments.append(f"{sector_name} 섹터는 성장 전망이 다소 불투명합니다.")

        return " ".join(comments)

    def get_sector_stocks(self, sector_name: str) -> List[Dict[str, Any]]:
        """특정 섹터에 속하는 종목 목록 조회 (향후 확장용)"""
        # TODO: 섹터별 종목 목록 데이터베이스 구축 필요
        return []
