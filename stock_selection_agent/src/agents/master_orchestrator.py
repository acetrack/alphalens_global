"""
Master Orchestrator - 종목 분석 통합 조율 에이전트
모든 서브 에이전트를 조율하고 최종 분석 결과 생성
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

from .screening_agent import ScreeningAgent, ScreeningCriteria
from .financial_agent import FinancialAgent, FinancialAnalysisConfig
from .valuation_agent import ValuationAgent
from ..api.dart_client import DartClient
from ..api.krx_client import KrxClient
from ..models.stock import Stock, DataFreshness
from ..models.analysis import AnalysisResult, AgentScore, ValuationResult, RiskAssessment


@dataclass
class OrchestratorConfig:
    """오케스트레이터 설정"""
    dart_api_key: Optional[str] = None
    output_dir: str = "output"
    max_data_age_days: int = 3  # 최대 데이터 경과일
    warning_data_age_days: int = 1  # 경고 데이터 경과일

    # 에이전트 가중치 (Conviction Score 계산용)
    weights: Dict[str, float] = None

    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                "financial": 0.25,
                "valuation": 0.20,
                "industry": 0.15,
                "technical": 0.15,
                "risk": 0.15,
                "sentiment": 0.10
            }


class MasterOrchestrator:
    """
    종목 분석 마스터 오케스트레이터

    기능:
    - 전체 분석 워크플로우 조율
    - 서브 에이전트 실행 및 결과 통합
    - 데이터 신선도 검증
    - 최종 투자 의견 생성
    - 분석 보고서 출력

    사용법:
        orchestrator = MasterOrchestrator(dart_api_key="your_key")
        result = orchestrator.analyze_stock("005930")  # 삼성전자
        orchestrator.save_report(result)
    """

    # 투자 등급 기준
    RATING_THRESHOLDS = {
        "STRONG_BUY": 80,
        "BUY": 65,
        "HOLD": 50,
        "SELL": 35,
        "STRONG_SELL": 0
    }

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        오케스트레이터 초기화

        Args:
            config: 오케스트레이터 설정
        """
        self.config = config or OrchestratorConfig()
        self.logger = logging.getLogger(__name__)

        # API 클라이언트 초기화
        self.krx_client = KrxClient()
        self.dart_client = None
        if self.config.dart_api_key:
            self.dart_client = DartClient(api_key=self.config.dart_api_key)

        # 서브 에이전트 초기화
        self.screening_agent = ScreeningAgent(krx_client=self.krx_client)
        self.financial_agent = FinancialAgent(
            dart_client=self.dart_client
        ) if self.dart_client else None
        self.valuation_agent = ValuationAgent(krx_client=self.krx_client)

        # 분석 날짜
        self.analysis_date = datetime.now()

    def analyze_stock(
        self,
        stock_code: str,
        include_screening: bool = False
    ) -> AnalysisResult:
        """
        개별 종목 분석 실행

        Args:
            stock_code: 종목코드 (6자리)
            include_screening: 스크리닝 결과 포함 여부

        Returns:
            통합 분석 결과
        """
        self.logger.info(f"종목 분석 시작: {stock_code}")

        # 1. 기본 주가 정보 조회
        price_data = self.krx_client.get_stock_price(stock_code)
        if "error" in price_data:
            return self._create_error_result(stock_code, price_data["error"])

        # 2. 밸류에이션 정보 조회
        valuation_data = self.krx_client.get_stock_valuation(stock_code)

        # 3. 데이터 신선도 검증
        freshness = self._validate_data_freshness(price_data, valuation_data)

        # 4. 재무제표 분석 (DART API 사용 가능한 경우)
        financial_result = {}
        if self.financial_agent:
            bsns_year = str(self.analysis_date.year - 1)  # 전년도 재무제표
            financial_result = self.financial_agent.analyze_by_stock_code(
                stock_code, bsns_year
            )

        # 5. 목표가 산정 (ValuationAgent 사용)
        valuation_result = self.valuation_agent.calculate_target_price(
            stock_code,
            current_price=price_data.get("close_price"),
            current_per=valuation_data.get("per"),
            current_pbr=valuation_data.get("pbr"),
            eps=valuation_data.get("eps"),
            bps=valuation_data.get("bps")
        )
        target_price = valuation_result.target_price

        # 6. 에이전트 스코어 계산 (밸류에이션 스코어 포함)
        agent_scores = self._calculate_agent_scores(
            price_data, valuation_data, financial_result, valuation_result
        )

        # 7. 종합 Conviction Score 계산
        conviction_score = self._calculate_conviction_score(agent_scores)

        # 8. 투자 등급 결정
        rating = self._determine_rating(conviction_score)

        # 9. 리스크 평가
        risk_assessment = self._assess_risk(price_data, valuation_data)

        # 결과 생성
        result = AnalysisResult(
            stock_code=stock_code,
            stock_name=price_data.get("stock_name", "Unknown"),
            analysis_date=self.analysis_date.strftime("%Y-%m-%d"),
            rating=rating,
            conviction_score=conviction_score,
            target_price=target_price,
            current_price=price_data.get("close_price", 0),
            agent_scores=agent_scores,
            valuation=self._create_valuation_result(valuation_data, target_price),
            risk_assessment=risk_assessment,
            data_freshness=freshness,
            summary=self._generate_summary(
                stock_code, rating, conviction_score, target_price, price_data
            ),
            # 밸류에이션 유의사항 및 코멘트
            valuation_caveats=valuation_result.caveats if valuation_result else [],
            valuation_comment=valuation_result.analyst_comment if valuation_result else "",
            valuation_methodology=valuation_result.methodology if valuation_result else "",
            global_peer_info=valuation_result.global_peer_info if valuation_result else None
        )

        return result

    def run_full_screening(
        self,
        criteria: Optional[ScreeningCriteria] = None,
        top_n: int = 10
    ) -> List[AnalysisResult]:
        """
        전체 스크리닝 및 상위 종목 분석

        Args:
            criteria: 스크리닝 조건
            top_n: 분석할 상위 종목 수

        Returns:
            상위 종목 분석 결과 리스트
        """
        self.logger.info("전체 스크리닝 시작")

        # 1. 스크리닝 실행 (List[ScreeningResult] 반환)
        screening_results = self.screening_agent.run_screening(market="ALL", criteria=criteria, top_n=top_n)

        if not screening_results:
            self.logger.warning("스크리닝 결과가 없습니다.")
            return []

        # 2. 개별 종목 분석
        results = []
        for i, sr in enumerate(screening_results[:top_n]):
            stock_code = sr.stock.code if sr.stock else None
            if stock_code:
                result = self.analyze_stock(stock_code)
                result.screening_rank = i + 1
                results.append(result)

        # 4. Conviction Score로 정렬
        results.sort(key=lambda x: x.conviction_score, reverse=True)

        return results

    def _validate_data_freshness(
        self,
        price_data: Dict[str, Any],
        valuation_data: Dict[str, Any]
    ) -> DataFreshness:
        """데이터 신선도 검증"""
        freshness = DataFreshness()

        # 주가 데이터 신선도
        if price_data.get("freshness"):
            price_freshness = price_data["freshness"]
            freshness.price_data_date = price_freshness.get("data_date")
            freshness.price_data_age_days = price_freshness.get("days_old", 0)

        # 밸류에이션 데이터 신선도
        if valuation_data.get("freshness"):
            val_freshness = valuation_data["freshness"]
            freshness.valuation_data_date = val_freshness.get("data_date")
            freshness.valuation_data_age_days = val_freshness.get("days_old", 0)

        # 경고 상태 설정
        max_age = max(
            freshness.price_data_age_days or 0,
            freshness.valuation_data_age_days or 0
        )

        if max_age > self.config.max_data_age_days:
            freshness.warning_level = "HIGH"
            freshness.warning_message = f"데이터가 {max_age}일 경과되어 신뢰도가 낮습니다."
        elif max_age > self.config.warning_data_age_days:
            freshness.warning_level = "MEDIUM"
            freshness.warning_message = f"데이터가 {max_age}일 경과되었습니다."
        else:
            freshness.warning_level = "LOW"
            freshness.warning_message = None

        return freshness

    def _calculate_agent_scores(
        self,
        price_data: Dict[str, Any],
        valuation_data: Dict[str, Any],
        financial_result: Dict[str, Any],
        valuation_result: Optional[Any] = None
    ) -> List[AgentScore]:
        """각 에이전트별 스코어 계산"""
        scores = []

        # Financial Agent Score
        if financial_result and "grade" in financial_result:
            grade_info = financial_result["grade"]
            fin_score = grade_info.get("score", 0) * 20  # 5점 만점 -> 100점 만점
            scores.append(AgentScore(
                agent_name="Financial Agent",
                score=fin_score,
                weight=self.config.weights["financial"],
                rationale=f"재무등급: {grade_info.get('overall_grade', 'N/A')}"
            ))
        else:
            # 기본 스코어 (재무 데이터 없음)
            scores.append(AgentScore(
                agent_name="Financial Agent",
                score=50,
                weight=self.config.weights["financial"],
                rationale="재무 데이터 없음 - 기본값 적용"
            ))

        # Valuation Score (ValuationAgent 결과 사용)
        if valuation_result:
            val_score = valuation_result.valuation_score
            val_rationale = f"{valuation_result.valuation_status} (목표가: {valuation_result.target_price:,}원, 상승여력: {valuation_result.upside_pct:+.1f}%)"
        else:
            val_score = self._calculate_valuation_score(valuation_data)
            val_rationale = f"PER: {valuation_data.get('per', 'N/A')}, PBR: {valuation_data.get('pbr', 'N/A')}"

        scores.append(AgentScore(
            agent_name="Valuation Agent",
            score=val_score,
            weight=self.config.weights["valuation"],
            rationale=val_rationale
        ))

        # Technical Score (단순화 - 모멘텀 기반)
        tech_score = self._calculate_technical_score(price_data)
        scores.append(AgentScore(
            agent_name="Technical Agent",
            score=tech_score,
            weight=self.config.weights["technical"],
            rationale=f"등락률: {price_data.get('change_rate', 0):.2f}%"
        ))

        # Industry Score (기본값 - 추후 확장)
        scores.append(AgentScore(
            agent_name="Industry Agent",
            score=60,
            weight=self.config.weights["industry"],
            rationale="업종 분석 - 기본값 적용"
        ))

        # Risk Score
        risk_score = self._calculate_risk_score(valuation_data)
        scores.append(AgentScore(
            agent_name="Risk Agent",
            score=risk_score,
            weight=self.config.weights["risk"],
            rationale="위험 평가 기반"
        ))

        # Sentiment Score (기본값 - 추후 확장)
        scores.append(AgentScore(
            agent_name="Sentiment Agent",
            score=55,
            weight=self.config.weights["sentiment"],
            rationale="심리 분석 - 기본값 적용"
        ))

        return scores

    def _calculate_valuation_score(self, valuation_data: Dict[str, Any]) -> float:
        """밸류에이션 스코어 계산"""
        score = 50  # 기본값

        per = valuation_data.get("per")
        pbr = valuation_data.get("pbr")

        if per and per > 0:
            # PER이 낮을수록 높은 점수
            if per < 10:
                score += 20
            elif per < 15:
                score += 10
            elif per < 20:
                score += 0
            elif per < 30:
                score -= 10
            else:
                score -= 20

        if pbr and pbr > 0:
            # PBR이 낮을수록 높은 점수
            if pbr < 1.0:
                score += 15
            elif pbr < 1.5:
                score += 5
            elif pbr < 2.0:
                score -= 5
            else:
                score -= 10

        return max(0, min(100, score))

    def _calculate_technical_score(self, price_data: Dict[str, Any]) -> float:
        """기술적 분석 스코어 계산 (단순화)"""
        score = 50  # 기본값

        change_rate = price_data.get("change_rate", 0)

        # 최근 등락률 기반 모멘텀
        if change_rate > 3:
            score += 20
        elif change_rate > 1:
            score += 10
        elif change_rate > -1:
            score += 0
        elif change_rate > -3:
            score -= 10
        else:
            score -= 20

        return max(0, min(100, score))

    def _calculate_risk_score(self, valuation_data: Dict[str, Any]) -> float:
        """리스크 스코어 계산 (높을수록 낮은 리스크)"""
        score = 60  # 기본값

        per = valuation_data.get("per")

        if per:
            if per < 0:  # 적자 기업
                score -= 30
            elif per > 50:  # 고평가
                score -= 20
            elif per < 5:  # 저평가 또는 이상치
                score -= 10

        return max(0, min(100, score))

    def _calculate_conviction_score(self, agent_scores: List[AgentScore]) -> float:
        """종합 Conviction Score 계산"""
        weighted_sum = 0
        total_weight = 0

        for score in agent_scores:
            weighted_sum += score.score * score.weight
            total_weight += score.weight

        if total_weight > 0:
            return round(weighted_sum / total_weight, 1)
        return 50.0

    def _determine_rating(self, conviction_score: float) -> str:
        """투자 등급 결정"""
        if conviction_score >= self.RATING_THRESHOLDS["STRONG_BUY"]:
            return "STRONG BUY"
        elif conviction_score >= self.RATING_THRESHOLDS["BUY"]:
            return "BUY"
        elif conviction_score >= self.RATING_THRESHOLDS["HOLD"]:
            return "HOLD"
        elif conviction_score >= self.RATING_THRESHOLDS["SELL"]:
            return "SELL"
        else:
            return "STRONG SELL"

    def _estimate_target_price(
        self,
        price_data: Dict[str, Any],
        valuation_data: Dict[str, Any],
        conviction_score: float
    ) -> int:
        """목표가 산정 (단순화된 버전)"""
        current_price = price_data.get("close_price", 0)

        if not current_price:
            return 0

        # Conviction Score 기반 상승 여력 계산
        # 80점 이상: +30%, 65점 이상: +15%, 50점 이상: 0%, 그 이하: -15%
        if conviction_score >= 80:
            upside = 0.30
        elif conviction_score >= 65:
            upside = 0.15
        elif conviction_score >= 50:
            upside = 0.05
        elif conviction_score >= 35:
            upside = -0.10
        else:
            upside = -0.20

        target = int(current_price * (1 + upside))

        # 1000원 단위로 반올림
        target = round(target / 1000) * 1000

        return target

    def _create_valuation_result(
        self,
        valuation_data: Dict[str, Any],
        target_price: int
    ) -> ValuationResult:
        """밸류에이션 결과 생성"""
        return ValuationResult(
            per=valuation_data.get("per"),
            pbr=valuation_data.get("pbr"),
            dividend_yield=valuation_data.get("dividend_yield"),
            target_price=target_price,
            valuation_method="Multi-Factor Scoring",
            fair_value_range=(
                int(target_price * 0.9) if target_price else None,
                int(target_price * 1.1) if target_price else None
            )
        )

    def _assess_risk(
        self,
        price_data: Dict[str, Any],
        valuation_data: Dict[str, Any]
    ) -> RiskAssessment:
        """리스크 평가"""
        risk_factors = []

        per = valuation_data.get("per")
        if per:
            if per < 0:
                risk_factors.append("적자 기업 (음의 PER)")
            elif per > 30:
                risk_factors.append("고평가 위험 (PER > 30)")

        pbr = valuation_data.get("pbr")
        if pbr and pbr > 3:
            risk_factors.append("높은 PBR (> 3.0)")

        change_rate = price_data.get("change_rate", 0)
        if abs(change_rate) > 5:
            risk_factors.append(f"높은 변동성 (당일 {change_rate:.1f}%)")

        # 리스크 레벨 결정
        if len(risk_factors) >= 3:
            level = "HIGH"
        elif len(risk_factors) >= 1:
            level = "MEDIUM"
        else:
            level = "LOW"

        return RiskAssessment(
            overall_level=level,
            risk_factors=risk_factors,
            mitigation_strategies=[
                "분산 투자를 통한 리스크 관리",
                "손절 라인 설정 권장",
                "정기적인 포트폴리오 리밸런싱"
            ]
        )

    def _generate_summary(
        self,
        stock_code: str,
        rating: str,
        conviction_score: float,
        target_price: int,
        price_data: Dict[str, Any]
    ) -> str:
        """요약 생성"""
        stock_name = price_data.get("stock_name", stock_code)
        current_price = price_data.get("close_price", 0)

        if target_price and current_price:
            upside = ((target_price - current_price) / current_price) * 100
            upside_text = f"+{upside:.1f}%" if upside > 0 else f"{upside:.1f}%"
        else:
            upside_text = "N/A"

        return (
            f"{stock_name}({stock_code})에 대해 {rating} 의견을 제시합니다. "
            f"Conviction Score {conviction_score}/100으로 "
            f"목표가 {target_price:,}원(상승여력 {upside_text})을 설정했습니다."
        )

    def _create_error_result(self, stock_code: str, error_msg: str) -> AnalysisResult:
        """에러 결과 생성"""
        return AnalysisResult(
            stock_code=stock_code,
            stock_name="Unknown",
            analysis_date=self.analysis_date.strftime("%Y-%m-%d"),
            rating="N/A",
            conviction_score=0,
            target_price=0,
            current_price=0,
            agent_scores=[],
            valuation=None,
            risk_assessment=None,
            data_freshness=None,
            summary=f"분석 실패: {error_msg}"
        )

    def save_report(
        self,
        result: AnalysisResult,
        format: str = "both"
    ) -> Dict[str, str]:
        """
        분석 보고서 저장

        Args:
            result: 분석 결과
            format: 출력 형식 ("md", "json", "both")

        Returns:
            저장된 파일 경로
        """
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        base_name = f"{result.stock_name}_{result.stock_code}_analysis_{result.analysis_date}"
        saved_files = {}

        if format in ("md", "both"):
            md_path = output_dir / f"{base_name}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(result.to_markdown())
            saved_files["markdown"] = str(md_path)
            self.logger.info(f"마크다운 보고서 저장: {md_path}")

        if format in ("json", "both"):
            json_path = output_dir / f"{base_name}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            saved_files["json"] = str(json_path)
            self.logger.info(f"JSON 보고서 저장: {json_path}")

        return saved_files

    def save_screening_report(
        self,
        results: List[AnalysisResult],
        report_name: str = "screening_report"
    ) -> str:
        """
        스크리닝 보고서 저장

        Args:
            results: 분석 결과 리스트
            report_name: 보고서 이름

        Returns:
            저장된 파일 경로
        """
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        date_str = self.analysis_date.strftime("%Y%m%d")
        file_path = output_dir / f"{report_name}_{date_str}.md"

        content = f"# 종목 스크리닝 보고서\n\n"
        content += f"**분석일자**: {self.analysis_date.strftime('%Y-%m-%d')}\n"
        content += f"**분석 종목 수**: {len(results)}개\n\n"

        content += "## 📊 스크리닝 결과 요약\n\n"
        content += "| 순위 | 종목명 | 종목코드 | 등급 | Conviction | 현재가 | 목표가 | 상승여력 |\n"
        content += "|:---:|:------|:------:|:---:|:---:|------:|------:|:---:|\n"

        for i, result in enumerate(results, 1):
            if result.target_price and result.current_price:
                upside = ((result.target_price - result.current_price) / result.current_price) * 100
                upside_str = f"+{upside:.1f}%" if upside > 0 else f"{upside:.1f}%"
            else:
                upside_str = "N/A"

            content += (
                f"| {i} | {result.stock_name} | {result.stock_code} | "
                f"{result.rating} | {result.conviction_score} | "
                f"{result.current_price:,}원 | {result.target_price:,}원 | {upside_str} |\n"
            )

        content += "\n---\n\n"
        content += "## 📋 개별 종목 분석\n\n"

        for result in results:
            content += f"### {result.stock_name} ({result.stock_code})\n\n"
            content += f"{result.summary}\n\n"

            if result.agent_scores:
                content += "**에이전트 스코어**:\n"
                for score in result.agent_scores:
                    content += f"- {score.agent_name}: {score.score:.1f} ({score.rationale})\n"
                content += "\n"

            content += "---\n\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.logger.info(f"스크리닝 보고서 저장: {file_path}")
        return str(file_path)


def create_orchestrator_with_env() -> MasterOrchestrator:
    """
    환경 변수에서 설정을 로드하여 오케스트레이터 생성

    환경 변수:
        DART_API_KEY: DART API 키
        OUTPUT_DIR: 출력 디렉토리 (기본: output)
    """
    import os

    config = OrchestratorConfig(
        dart_api_key=os.getenv("DART_API_KEY"),
        output_dir=os.getenv("OUTPUT_DIR", "output")
    )

    return MasterOrchestrator(config)
