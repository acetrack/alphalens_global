"""
Financial Agent - 재무제표 분석
DART API를 사용한 자동화된 재무 분석
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from ..api.dart_client import DartClient, DartApiError
from ..models.stock import FinancialStatement


@dataclass
class FinancialAnalysisConfig:
    """재무 분석 설정"""
    years_to_analyze: int = 3  # 분석할 연도 수
    use_consolidated: bool = True  # 연결재무제표 사용 여부
    min_revenue_growth: float = 0.0  # 최소 매출 성장률
    min_op_margin: float = 5.0  # 최소 영업이익률
    max_debt_ratio: float = 200.0  # 최대 부채비율


class FinancialAgent:
    """
    재무제표 분석 에이전트

    기능:
    - DART API로 재무제표 조회
    - 수익성 분석 (영업이익률, ROE, ROA)
    - 안정성 분석 (부채비율, 유동비율)
    - 성장성 분석 (매출/이익 성장률)
    - DuPont 분석

    사용법:
        agent = FinancialAgent(api_key="your_dart_api_key")
        result = agent.analyze("00126380", "2024")  # 삼성전자
    """

    # 주요 기업 고유번호 매핑 (종목코드 -> DART 고유번호)
    CORP_CODE_MAP = {
        "005930": "00126380",  # 삼성전자
        "000660": "00164779",  # SK하이닉스
        "035420": "00401731",  # 네이버
        "035720": "00251416",  # 카카오
        "051910": "00356370",  # LG화학
        "006400": "00104954",  # 삼성SDI
        "373220": "01652607",  # LG에너지솔루션
        "207940": "00817524",  # 삼성바이오로직스
        "000270": "00102237",  # 기아
        "005380": "00164742",  # 현대차
        "068270": "00413046",  # 셀트리온
        "105560": "00401325",  # KB금융
        "055550": "00382199",  # 신한지주
        "096770": "00420143",  # SK이노베이션
        "028260": "00217342",  # 삼성물산
        "003550": "00118662",  # LG
        "017670": "00102939",  # SK텔레콤
        "034730": "00373489",  # SK
        "012330": "00155305",  # 현대모비스
        "066570": "00401854",  # LG전자
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        dart_client: Optional[DartClient] = None
    ):
        """
        재무 분석 에이전트 초기화

        Args:
            api_key: DART API 키
            dart_client: DartClient 인스턴스
        """
        self.dart = dart_client or DartClient(api_key=api_key) if api_key else None
        self.logger = logging.getLogger(__name__)

    def _get_corp_code(self, stock_code: str) -> Optional[str]:
        """종목코드에서 DART 고유번호 조회"""
        return self.CORP_CODE_MAP.get(stock_code)

    def analyze(
        self,
        corp_code: str,
        bsns_year: str,
        config: Optional[FinancialAnalysisConfig] = None
    ) -> Dict[str, Any]:
        """
        재무제표 분석 실행

        Args:
            corp_code: DART 고유번호 (또는 종목코드 - 자동 변환)
            bsns_year: 사업연도
            config: 분석 설정

        Returns:
            재무 분석 결과
        """
        config = config or FinancialAnalysisConfig()

        # 종목코드면 고유번호로 변환
        if len(corp_code) == 6:
            resolved_code = self._get_corp_code(corp_code)
            if not resolved_code:
                return {"error": f"종목코드 {corp_code}에 대한 DART 고유번호를 찾을 수 없습니다."}
            corp_code = resolved_code

        if not self.dart:
            return {"error": "DART API 클라이언트가 초기화되지 않았습니다."}

        try:
            # 기업 개황 조회
            company_info = self.dart.get_company_info(corp_code)

            # 재무제표 조회
            fs_data = self.dart.get_key_financials(corp_code, bsns_year)

            if "error" in fs_data:
                return fs_data

            # 재무 비율 분석
            analysis = self._analyze_ratios(fs_data)

            # 재무 등급 산정
            grade = self._calculate_financial_grade(analysis)

            return {
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "company_info": company_info,
                "financials": fs_data,
                "analysis": analysis,
                "grade": grade,
                "analysis_date": datetime.now().strftime("%Y-%m-%d")
            }

        except DartApiError as e:
            self.logger.error(f"재무 분석 실패: {e}")
            return {"error": str(e)}

    def analyze_by_stock_code(
        self,
        stock_code: str,
        bsns_year: str,
        config: Optional[FinancialAnalysisConfig] = None
    ) -> Dict[str, Any]:
        """
        종목코드로 재무제표 분석

        Args:
            stock_code: 종목코드 (6자리)
            bsns_year: 사업연도

        Returns:
            재무 분석 결과
        """
        corp_code = self._get_corp_code(stock_code)
        if not corp_code:
            return {
                "error": f"종목코드 {stock_code}에 대한 DART 고유번호가 없습니다.",
                "hint": "CORP_CODE_MAP에 매핑을 추가하거나 DART 고유번호를 직접 사용하세요."
            }

        return self.analyze(corp_code, bsns_year, config)

    def _analyze_ratios(self, fs_data: Dict[str, Any]) -> Dict[str, Any]:
        """재무 비율 분석"""
        analysis = {
            "profitability": {},  # 수익성
            "stability": {},      # 안정성
            "growth": {},         # 성장성
            "efficiency": {}      # 효율성
        }

        # 수익성 지표
        if fs_data.get("op_margin"):
            analysis["profitability"]["영업이익률"] = {
                "value": fs_data["op_margin"],
                "unit": "%",
                "grade": self._grade_metric(fs_data["op_margin"], [5, 10, 15, 20])
            }

        if fs_data.get("roe"):
            analysis["profitability"]["ROE"] = {
                "value": fs_data["roe"],
                "unit": "%",
                "grade": self._grade_metric(fs_data["roe"], [5, 10, 15, 20])
            }

        # 안정성 지표
        if fs_data.get("debt_ratio"):
            analysis["stability"]["부채비율"] = {
                "value": fs_data["debt_ratio"],
                "unit": "%",
                "grade": self._grade_metric(
                    200 - fs_data["debt_ratio"],  # 낮을수록 좋음
                    [50, 100, 150, 200]
                )
            }

        return analysis

    def _grade_metric(self, value: float, thresholds: List[float]) -> str:
        """지표 등급 산정"""
        if value >= thresholds[3]:
            return "A+"
        elif value >= thresholds[2]:
            return "A"
        elif value >= thresholds[1]:
            return "B"
        elif value >= thresholds[0]:
            return "C"
        else:
            return "D"

    def _calculate_financial_grade(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """종합 재무 등급 산정"""
        grades = []

        for category, metrics in analysis.items():
            for metric_name, metric_data in metrics.items():
                if isinstance(metric_data, dict) and "grade" in metric_data:
                    grades.append(metric_data["grade"])

        # 등급을 점수로 변환
        grade_to_score = {"A+": 5, "A": 4, "B": 3, "C": 2, "D": 1}
        scores = [grade_to_score.get(g, 0) for g in grades]

        if scores:
            avg_score = sum(scores) / len(scores)
            # 점수를 다시 등급으로
            if avg_score >= 4.5:
                overall = "A+"
            elif avg_score >= 3.5:
                overall = "A"
            elif avg_score >= 2.5:
                overall = "B"
            elif avg_score >= 1.5:
                overall = "C"
            else:
                overall = "D"
        else:
            overall = "N/A"
            avg_score = 0

        return {
            "overall_grade": overall,
            "score": round(avg_score, 2),
            "metrics_count": len(grades)
        }

    def get_multi_year_analysis(
        self,
        corp_code: str,
        end_year: int,
        years: int = 3
    ) -> Dict[str, Any]:
        """
        다년간 재무 분석

        Args:
            corp_code: DART 고유번호
            end_year: 종료 연도
            years: 분석 연도 수

        Returns:
            다년간 재무 분석 결과
        """
        results = {}

        for year_offset in range(years):
            year = end_year - year_offset
            result = self.analyze(corp_code, str(year))
            results[str(year)] = result

        # 성장률 계산
        if len(results) >= 2:
            years_list = sorted(results.keys())
            growth_analysis = self._calculate_growth(results, years_list)
            results["growth_analysis"] = growth_analysis

        return results

    def _calculate_growth(
        self,
        results: Dict[str, Dict[str, Any]],
        years: List[str]
    ) -> Dict[str, Any]:
        """성장률 계산"""
        growth = {}

        if len(years) < 2:
            return growth

        # 최근 연도와 전년도 비교
        latest = results.get(years[-1], {}).get("financials", {})
        prev = results.get(years[-2], {}).get("financials", {})

        # 매출 성장률
        if latest.get("revenue") and prev.get("revenue") and prev["revenue"] > 0:
            growth["revenue_growth"] = round(
                (latest["revenue"] - prev["revenue"]) / prev["revenue"] * 100, 2
            )

        # 영업이익 성장률
        if latest.get("operating_profit") and prev.get("operating_profit") and prev["operating_profit"] > 0:
            growth["op_growth"] = round(
                (latest["operating_profit"] - prev["operating_profit"]) / prev["operating_profit"] * 100, 2
            )

        return growth


def create_financial_agent_without_api() -> FinancialAgent:
    """
    API 키 없이 Financial Agent 생성 (테스트용)
    실제 DART API 호출은 불가능
    """
    agent = FinancialAgent()
    agent.dart = None
    return agent
