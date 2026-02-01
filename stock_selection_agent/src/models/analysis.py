"""
Analysis Result Models
분석 결과 데이터 모델
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


@dataclass
class ValuationResult:
    """밸류에이션 분석 결과"""
    per: Optional[float] = None
    pbr: Optional[float] = None
    dividend_yield: Optional[float] = None
    target_price: Optional[int] = None
    valuation_method: str = ""
    fair_value_range: Optional[Tuple[int, int]] = None


@dataclass
class AgentScore:
    """개별 에이전트 점수"""
    agent_name: str
    score: float  # 0-100
    weight: float  # 가중치 (0-1)
    rationale: str = ""  # 근거

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class RiskAssessment:
    """리스크 평가 결과"""
    overall_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    risk_factors: List[str] = field(default_factory=list)
    mitigation_strategies: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """종합 분석 결과"""
    # 기본 정보
    stock_code: str
    stock_name: str
    analysis_date: str

    # 투자 의견
    rating: str  # "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"
    conviction_score: float  # 0-100
    target_price: int
    current_price: int

    # 상세 분석
    agent_scores: List[AgentScore] = field(default_factory=list)
    valuation: Optional[ValuationResult] = None
    risk_assessment: Optional[RiskAssessment] = None
    data_freshness: Optional[Any] = None

    # 요약
    summary: str = ""

    # 스크리닝 순위 (옵션)
    screening_rank: Optional[int] = None

    # 밸류에이션 유의사항 및 코멘트
    valuation_caveats: List[str] = field(default_factory=list)
    valuation_comment: str = ""
    valuation_methodology: str = ""
    global_peer_info: Optional[Dict[str, Any]] = None

    @property
    def upside_pct(self) -> Optional[float]:
        """상승여력 계산"""
        if self.target_price and self.current_price and self.current_price > 0:
            return round((self.target_price - self.current_price) / self.current_price * 100, 1)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "report_header": {
                "analysis_date": self.analysis_date,
                "stock_code": self.stock_code,
                "stock_name": self.stock_name,
            },
            "investment_summary": {
                "rating": self.rating,
                "target_price": self.target_price,
                "current_price": self.current_price,
                "upside_pct": self.upside_pct,
                "conviction_score": self.conviction_score
            },
            "agent_scores": [
                {
                    "agent": s.agent_name,
                    "score": s.score,
                    "weight": s.weight,
                    "weighted_score": s.weighted_score,
                    "rationale": s.rationale
                }
                for s in self.agent_scores
            ],
            "valuation": {
                "per": self.valuation.per if self.valuation else None,
                "pbr": self.valuation.pbr if self.valuation else None,
                "target_price": self.valuation.target_price if self.valuation else None,
            } if self.valuation else None,
            "risk_assessment": {
                "level": self.risk_assessment.overall_level if self.risk_assessment else None,
                "factors": self.risk_assessment.risk_factors if self.risk_assessment else [],
            } if self.risk_assessment else None,
            "summary": self.summary
        }

    def to_markdown(self) -> str:
        """마크다운 리포트 생성"""
        upside = self.upside_pct or 0
        upside_str = f"+{upside:.1f}%" if upside > 0 else f"{upside:.1f}%"

        md = f"""# {self.stock_name} ({self.stock_code}) 투자분석 리포트

## Executive Summary

| 항목 | 내용 |
|------|------|
| **종목명** | {self.stock_name} |
| **종목코드** | {self.stock_code} |
| **분석기준일** | {self.analysis_date} |
| **현재주가** | {self.current_price:,}원 |
| **투자의견** | **{self.rating}** |
| **목표주가** | {self.target_price:,}원 |
| **업사이드** | {upside_str} |
| **Conviction Score** | {self.conviction_score}/100 |

---

## 투자 요약

{self.summary}

---

## Agent 점수

| 분석 영역 | 점수 | 비중 | 가중점수 | 근거 |
|-----------|------|------|----------|------|
"""
        for s in self.agent_scores:
            md += f"| {s.agent_name} | {s.score:.1f} | {s.weight*100:.0f}% | {s.weighted_score:.1f} | {s.rationale} |\n"

        md += f"\n**총 Conviction Score: {self.conviction_score}/100**\n\n"

        # 밸류에이션
        if self.valuation:
            md += "## 밸류에이션\n\n"

            # 밸류에이션 방법론
            if self.valuation_methodology:
                md += f"**산정 방식**: {self.valuation_methodology}\n\n"

            # 글로벌 Peer 정보
            if self.global_peer_info:
                md += "### 글로벌 Peer 비교\n\n"
                md += f"- **비교 대상**: {self.global_peer_info.get('peer_name', 'N/A')}\n"
                if self.global_peer_info.get('peer_per'):
                    md += f"- **Peer PER**: {self.global_peer_info['peer_per']}배\n"
                if self.global_peer_info.get('peer_pbr'):
                    md += f"- **Peer PBR**: {self.global_peer_info['peer_pbr']}배\n"
                md += "\n"

            md += "| 지표 | 값 |\n"
            md += "|------|----|\n"
            if self.valuation.per:
                md += f"| PER | {self.valuation.per:.2f} |\n"
            if self.valuation.pbr:
                md += f"| PBR | {self.valuation.pbr:.2f} |\n"
            if self.valuation.dividend_yield:
                md += f"| 배당수익률 | {self.valuation.dividend_yield:.2f}% |\n"
            md += "\n"

        # 목표가 산정 유의사항
        if self.valuation_caveats:
            md += "## 📋 목표가 산정 유의사항\n\n"
            for caveat in self.valuation_caveats:
                md += f"{caveat}\n"
            md += "\n"

        # 애널리스트 코멘트
        if self.valuation_comment:
            md += "## 💬 애널리스트 코멘트\n\n"
            md += f"> {self.valuation_comment}\n\n"

        # 리스크
        if self.risk_assessment and self.risk_assessment.risk_factors:
            md += f"## 리스크 평가 ({self.risk_assessment.overall_level})\n\n"
            for factor in self.risk_assessment.risk_factors:
                md += f"- {factor}\n"
            md += "\n"

        # 데이터 신선도
        if self.data_freshness:
            md += "## 데이터 기준일 안내\n\n"
            md += "| 데이터 유형 | 기준일 | 경과일 |\n"
            md += "|------------|--------|--------|\n"

            if hasattr(self.data_freshness, 'price_data_date') and self.data_freshness.price_data_date:
                md += f"| 주가 데이터 | {self.data_freshness.price_data_date} | {self.data_freshness.price_data_age_days}일 |\n"
            if hasattr(self.data_freshness, 'valuation_data_date') and self.data_freshness.valuation_data_date:
                md += f"| 밸류에이션 | {self.data_freshness.valuation_data_date} | {self.data_freshness.valuation_data_age_days}일 |\n"

            if hasattr(self.data_freshness, 'warning_message') and self.data_freshness.warning_message:
                md += f"\n⚠️ **경고**: {self.data_freshness.warning_message}\n"
            md += "\n"

        md += f"""---

*본 리포트는 투자 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다.*

**분석일**: {self.analysis_date}
**작성**: Stock Selection Agent
"""
        return md
