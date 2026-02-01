"""
Valuation Agent - 목표가 산정 에이전트
상대가치 평가, 글로벌 peer 비교, 예외 처리를 통한 정교한 목표가 산정
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from ..api.krx_client import KrxClient


@dataclass
class ValuationConfig:
    """밸류에이션 설정"""
    # PER 기반 목표가 가중치
    per_weight: float = 0.4
    # PBR 기반 목표가 가중치
    pbr_weight: float = 0.3
    # 업종/글로벌 peer 평균 대비 가중치
    peer_weight: float = 0.3

    # 목표 PER 프리미엄/할인 범위
    max_premium: float = 0.30  # 최대 30% 프리미엄
    max_discount: float = 0.30  # 최대 30% 할인


@dataclass
class StockOverride:
    """종목별 예외 설정"""
    stock_code: str
    stock_name: str

    # 글로벌 peer 사용 여부
    use_global_peer: bool = False
    global_peer_name: str = ""
    global_peer_per: Optional[float] = None
    global_peer_pbr: Optional[float] = None

    # 사용자 지정 목표 PER/PBR
    custom_target_per: Optional[float] = None
    custom_target_pbr: Optional[float] = None

    # 목표가 산정 방식 override
    valuation_method: str = "standard"  # "standard", "global_peer", "custom"

    # 유의사항/코멘트
    caveats: List[str] = field(default_factory=list)
    analyst_comment: str = ""


@dataclass
class TargetPriceResult:
    """목표가 산정 결과"""
    stock_code: str
    stock_name: str
    current_price: int

    # 개별 방법론 목표가
    per_based_target: Optional[int] = None
    pbr_based_target: Optional[int] = None
    peer_based_target: Optional[int] = None

    # 최종 목표가
    target_price: int = 0
    target_price_low: int = 0  # 보수적 목표가
    target_price_high: int = 0  # 낙관적 목표가

    # 업사이드
    upside_pct: float = 0.0

    # 밸류에이션 상태
    valuation_status: str = ""  # "저평가", "적정", "고평가"
    valuation_score: float = 0.0  # 0-100 (높을수록 저평가)

    # 근거
    methodology: str = ""
    rationale: List[str] = field(default_factory=list)

    # 유의사항 및 코멘트
    caveats: List[str] = field(default_factory=list)
    analyst_comment: str = ""

    # 글로벌 peer 정보
    global_peer_info: Optional[Dict[str, Any]] = None

    # 예외 처리 적용 여부
    has_override: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "current_price": self.current_price,
            "target_price": self.target_price,
            "target_price_low": self.target_price_low,
            "target_price_high": self.target_price_high,
            "upside_pct": self.upside_pct,
            "valuation_status": self.valuation_status,
            "valuation_score": self.valuation_score,
            "per_based_target": self.per_based_target,
            "pbr_based_target": self.pbr_based_target,
            "peer_based_target": self.peer_based_target,
            "methodology": self.methodology,
            "rationale": self.rationale,
            "caveats": self.caveats,
            "analyst_comment": self.analyst_comment,
            "global_peer_info": self.global_peer_info,
            "has_override": self.has_override
        }


class ValuationAgent:
    """
    밸류에이션 에이전트 - 목표가 산정

    방법론:
    1. 상대가치 평가 (업종 평균 PER/PBR 대비)
    2. 글로벌 peer 비교 (특수 종목)
    3. 종목별 예외 처리
    4. 가중평균 목표가 산출

    사용법:
        agent = ValuationAgent()
        result = agent.calculate_target_price("005930")

        # 예외 설정 추가
        agent.add_override("005930", custom_target_per=20.0, analyst_comment="메모리 사이클 고려")
    """

    # 업종별 적정 PER 기준 (한국 시장)
    SECTOR_PER_BASELINE = {
        "반도체": 15.0,
        "메모리반도체": 12.0,  # 사이클 산업 특성
        "전자부품": 12.0,
        "IT서비스": 25.0,
        "인터넷": 30.0,
        "바이오": 40.0,
        "제약": 20.0,
        "은행": 8.0,
        "증권": 10.0,
        "보험": 10.0,
        "자동차": 8.0,
        "철강": 6.0,
        "화학": 10.0,
        "유통": 15.0,
        "건설": 8.0,
        "기타": 12.0,
    }

    # 주요 종목 업종 매핑
    STOCK_SECTOR_MAP = {
        "005930": "메모리반도체",  # 삼성전자
        "000660": "메모리반도체",  # SK하이닉스
        "035420": "인터넷",        # 네이버
        "035720": "인터넷",        # 카카오
        "051910": "화학",          # LG화학
        "006400": "전자부품",      # 삼성SDI
        "373220": "전자부품",      # LG에너지솔루션
        "207940": "바이오",        # 삼성바이오로직스
        "000270": "자동차",        # 기아
        "005380": "자동차",        # 현대차
        "068270": "바이오",        # 셀트리온
        "105560": "은행",          # KB금융
        "055550": "은행",          # 신한지주
        "066570": "전자부품",      # LG전자
    }

    # 글로벌 Peer 데이터 (수동 업데이트 필요)
    # 실제로는 Bloomberg, Reuters 등에서 실시간 조회 필요
    GLOBAL_PEER_DATA = {
        # 메모리 반도체 - Micron Technology (MU)
        "메모리반도체": {
            "peer_name": "Micron Technology (MU)",
            "peer_per": 25.0,  # 2026년 1월 기준 추정
            "peer_pbr": 2.5,
            "peer_market": "NASDAQ",
            "last_updated": "2026-01-30",
            "note": "글로벌 메모리 반도체 대표 기업"
        },
        # 파운드리 - TSMC
        "파운드리": {
            "peer_name": "TSMC (TSM)",
            "peer_per": 22.0,
            "peer_pbr": 6.0,
            "peer_market": "NYSE",
            "last_updated": "2026-01-30",
            "note": "글로벌 파운드리 1위"
        },
        # 인터넷 - Google, Meta
        "인터넷_글로벌": {
            "peer_name": "Meta Platforms (META)",
            "peer_per": 28.0,
            "peer_pbr": 8.0,
            "peer_market": "NASDAQ",
            "last_updated": "2026-01-30",
            "note": "글로벌 인터넷/플랫폼 대표"
        }
    }

    # 기본 예외 설정 (종목별)
    DEFAULT_OVERRIDES: Dict[str, StockOverride] = {}

    def __init__(
        self,
        krx_client: Optional[KrxClient] = None,
        config: Optional[ValuationConfig] = None
    ):
        self.krx = krx_client or KrxClient()
        self.config = config or ValuationConfig()
        self.logger = logging.getLogger(__name__)

        # 종목별 예외 설정
        self.overrides: Dict[str, StockOverride] = {}

        # 기본 예외 설정 초기화
        self._init_default_overrides()

        # 업종별 밸류에이션 캐시
        self._sector_valuation_cache: Dict[str, Dict[str, float]] = {}

    def _init_default_overrides(self):
        """기본 예외 설정 초기화"""
        # 삼성전자 - 글로벌 메모리 peer 비교
        self.overrides["005930"] = StockOverride(
            stock_code="005930",
            stock_name="삼성전자",
            use_global_peer=True,
            global_peer_name="Micron Technology (MU)",
            global_peer_per=25.0,
            global_peer_pbr=2.5,
            valuation_method="global_peer",
            caveats=[
                "⚠️ 메모리 반도체는 사이클 산업으로 PER 변동성이 큼",
                "⚠️ 국내 비교 대상 부재 - 글로벌 peer(Micron) 기준 적용",
                "⚠️ 현재 PER이 높은 것은 메모리 다운사이클 영향일 수 있음",
                "📊 향후 이익 정상화 시 PER 하락 예상"
            ],
            analyst_comment="메모리 사이클 저점 통과 여부 모니터링 필요. Micron 대비 프리미엄 정당화 근거 검토 요망."
        )

        # SK하이닉스 - 글로벌 메모리 peer 비교
        self.overrides["000660"] = StockOverride(
            stock_code="000660",
            stock_name="SK하이닉스",
            use_global_peer=True,
            global_peer_name="Micron Technology (MU)",
            global_peer_per=25.0,
            global_peer_pbr=2.5,
            valuation_method="global_peer",
            caveats=[
                "⚠️ 메모리 반도체는 사이클 산업으로 PER 변동성이 큼",
                "⚠️ 국내 비교 대상 부재 - 글로벌 peer(Micron) 기준 적용",
                "⚠️ HBM 관련 프리미엄 반영 여부 검토 필요",
                "📊 AI 수혜주로 Micron 대비 프리미엄 가능"
            ],
            analyst_comment="HBM 시장 리더십 감안 시 Micron 대비 10-20% 프리미엄 정당화 가능."
        )

        # 한미반도체 - 글로벌 반도체 장비 peer 비교
        self.overrides["042700"] = StockOverride(
            stock_code="042700",
            stock_name="한미반도체",
            use_global_peer=True,
            global_peer_name="ASML / Applied Materials",
            global_peer_per=35.0,  # 반도체 장비 평균 PER
            global_peer_pbr=10.0,  # 고성장 장비주 PBR
            valuation_method="global_peer",
            caveats=[
                "⚠️ HBM 장비 대표주로 고성장 프리미엄 반영 필요",
                "⚠️ 글로벌 반도체 장비주(ASML, AMAT) 평균 PER 35배 기준",
                "⚠️ 현재 PER(132배)은 이익 급성장 구간 특성 반영",
                "📊 향후 이익 증가 시 PER 정상화 예상 (Forward PER 고려 필요)",
                "📈 HBM 시장 성장률 연 30%+ 감안 시 프리미엄 정당화 가능"
            ],
            analyst_comment="HBM 시장 독과점 지위 및 고객사(SK하이닉스) 투자 확대 모멘텀 감안. 단, 높은 밸류에이션으로 주가 변동성 주의."
        )

        # 현대차 - 글로벌 완성차 peer 비교
        self.overrides["005380"] = StockOverride(
            stock_code="005380",
            stock_name="현대차",
            use_global_peer=True,
            global_peer_name="Toyota / Volkswagen",
            global_peer_per=10.0,  # 글로벌 완성차 평균
            global_peer_pbr=1.0,
            valuation_method="global_peer",
            caveats=[
                "⚠️ 글로벌 완성차 peer(Toyota PER 10배) 기준 적용",
                "📊 EV 전환 비용 및 중국 시장 리스크 존재",
                "📈 제네시스 브랜드 성장 프리미엄 가능"
            ],
            analyst_comment="글로벌 완성차 대비 적정 수준. EV 전환 성과에 따라 리레이팅 가능."
        )

        # 기아 - 글로벌 완성차 peer 비교
        self.overrides["000270"] = StockOverride(
            stock_code="000270",
            stock_name="기아",
            use_global_peer=True,
            global_peer_name="Toyota / Volkswagen",
            global_peer_per=10.0,
            global_peer_pbr=1.0,
            valuation_method="global_peer",
            caveats=[
                "⚠️ 글로벌 완성차 peer(Toyota PER 10배) 기준 적용",
                "📊 현대차그룹 시너지 효과 존재"
            ],
            analyst_comment="현대차 대비 밸류에이션 매력도 높음. EV3 등 신차 모멘텀 주목."
        )

    def add_override(
        self,
        stock_code: str,
        stock_name: Optional[str] = None,
        use_global_peer: bool = False,
        global_peer_name: str = "",
        global_peer_per: Optional[float] = None,
        global_peer_pbr: Optional[float] = None,
        custom_target_per: Optional[float] = None,
        custom_target_pbr: Optional[float] = None,
        valuation_method: str = "standard",
        caveats: Optional[List[str]] = None,
        analyst_comment: str = ""
    ):
        """
        종목별 예외 설정 추가

        Args:
            stock_code: 종목코드
            use_global_peer: 글로벌 peer 사용 여부
            global_peer_per: 글로벌 peer PER
            custom_target_per: 사용자 지정 목표 PER
            caveats: 유의사항 리스트
            analyst_comment: 애널리스트 코멘트
        """
        if stock_name is None:
            stock_name = self.krx._get_stock_name(stock_code)

        self.overrides[stock_code] = StockOverride(
            stock_code=stock_code,
            stock_name=stock_name,
            use_global_peer=use_global_peer,
            global_peer_name=global_peer_name,
            global_peer_per=global_peer_per,
            global_peer_pbr=global_peer_pbr,
            custom_target_per=custom_target_per,
            custom_target_pbr=custom_target_pbr,
            valuation_method=valuation_method,
            caveats=caveats or [],
            analyst_comment=analyst_comment
        )

    def remove_override(self, stock_code: str):
        """종목별 예외 설정 제거"""
        if stock_code in self.overrides:
            del self.overrides[stock_code]

    def calculate_target_price(
        self,
        stock_code: str,
        current_price: Optional[int] = None,
        current_per: Optional[float] = None,
        current_pbr: Optional[float] = None,
        eps: Optional[int] = None,
        bps: Optional[int] = None
    ) -> TargetPriceResult:
        """
        목표가 산정

        Args:
            stock_code: 종목코드
            current_price: 현재가 (없으면 조회)
            current_per: 현재 PER
            current_pbr: 현재 PBR
            eps: 주당순이익
            bps: 주당순자산

        Returns:
            목표가 산정 결과
        """
        # 1. 기본 데이터 조회
        if current_price is None or current_per is None:
            price_data = self.krx.get_stock_price(stock_code)
            val_data = self.krx.get_stock_valuation(stock_code)

            current_price = current_price or price_data.get("close_price", 0)
            current_per = current_per or val_data.get("per")
            current_pbr = current_pbr or val_data.get("pbr")
            eps = eps or val_data.get("eps")
            bps = bps or val_data.get("bps")
            stock_name = price_data.get("stock_name", stock_code)
        else:
            stock_name = self.krx._get_stock_name(stock_code)

        result = TargetPriceResult(
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=current_price
        )

        rationale = []
        caveats = []

        # 2. 예외 설정 확인
        override = self.overrides.get(stock_code)
        if override:
            result.has_override = True
            caveats.extend(override.caveats)
            result.analyst_comment = override.analyst_comment

        # 3. 업종 정보 조회
        sector = self._get_sector(stock_code)

        # 4. 목표 PER/PBR 결정
        if override and override.use_global_peer:
            # 글로벌 peer 기준
            target_per = override.global_peer_per or self.SECTOR_PER_BASELINE.get(sector, 12.0)
            target_pbr = override.global_peer_pbr or 1.5

            result.global_peer_info = {
                "peer_name": override.global_peer_name,
                "peer_per": override.global_peer_per,
                "peer_pbr": override.global_peer_pbr
            }

            rationale.append(f"글로벌 Peer 기준: {override.global_peer_name} (PER {target_per}배)")
            result.methodology = f"글로벌 Peer 비교 ({override.global_peer_name})"

        elif override and override.custom_target_per:
            # 사용자 지정
            target_per = override.custom_target_per
            target_pbr = override.custom_target_pbr or 1.5

            rationale.append(f"사용자 지정 PER: {target_per}배")
            result.methodology = "사용자 지정 밸류에이션"

        else:
            # 표준 업종 평균
            target_per = self.SECTOR_PER_BASELINE.get(sector, 12.0)
            target_pbr = self._get_sector_target_pbr(sector)

            rationale.append(f"업종({sector}) 평균 PER: {target_per}배")
            result.methodology = "상대가치 평가 (업종 평균)"

        # 5. PER 기반 목표가
        if eps and eps > 0:
            per_target = int(eps * target_per)
            result.per_based_target = per_target
            rationale.append(f"PER 기반: EPS {eps:,}원 × {target_per}배 = {per_target:,}원")

        # 6. PBR 기반 목표가
        if bps and bps > 0:
            pbr_target = int(bps * target_pbr)
            result.pbr_based_target = pbr_target
            rationale.append(f"PBR 기반: BPS {bps:,}원 × {target_pbr}배 = {pbr_target:,}원")

        # 7. 가중평균 목표가 산출
        target_prices = []
        weights = []

        if result.per_based_target:
            target_prices.append(result.per_based_target)
            weights.append(self.config.per_weight)

        if result.pbr_based_target:
            target_prices.append(result.pbr_based_target)
            weights.append(self.config.pbr_weight)

        if target_prices:
            # 가중평균
            weighted_sum = sum(p * w for p, w in zip(target_prices, weights))
            total_weight = sum(weights)
            target_price = int(weighted_sum / total_weight)

            # 1000원 단위 반올림
            result.target_price = round(target_price / 1000) * 1000

            # 보수적/낙관적 목표가 (±15%)
            result.target_price_low = round(result.target_price * 0.85 / 1000) * 1000
            result.target_price_high = round(result.target_price * 1.15 / 1000) * 1000

            # 업사이드 계산
            if current_price > 0:
                result.upside_pct = round(
                    (result.target_price - current_price) / current_price * 100, 1
                )
        else:
            # 폴백: 현재가 기준
            result.target_price = current_price
            result.target_price_low = current_price
            result.target_price_high = current_price
            rationale.append("밸류에이션 데이터 부족 - 현재가 유지")

        # 8. 밸류에이션 상태 판단 (글로벌 peer 기준)
        result.valuation_status, result.valuation_score = self._assess_valuation_status(
            current_per, current_pbr, target_per, target_pbr
        )

        rationale.append(f"밸류에이션 상태: {result.valuation_status} (점수: {result.valuation_score:.0f}/100)")

        # 9. 자동 유의사항 추가
        if not override:
            # 표준 방식인 경우 기본 caveat
            if current_per and target_per and current_per > target_per * 1.5:
                caveats.append(f"⚠️ 현재 PER({current_per:.1f}배)이 목표 PER({target_per}배) 대비 높음")

            if sector == "메모리반도체":
                caveats.append("⚠️ 메모리 반도체는 사이클 산업으로 업종 PER 기준 적용에 한계가 있음")

        result.rationale = rationale
        result.caveats = caveats

        return result

    def _get_sector_target_pbr(self, sector: str) -> float:
        """업종별 목표 PBR 반환"""
        sector_pbr_map = {
            "메모리반도체": 2.5,
            "반도체": 2.0,
            "전자부품": 1.5,
            "IT서비스": 3.0,
            "인터넷": 4.0,
            "바이오": 5.0,
            "은행": 0.5,
            "증권": 0.8,
            "자동차": 0.8,
            "철강": 0.5,
            "화학": 1.0,
            "기타": 1.2,
        }
        return sector_pbr_map.get(sector, 1.2)

    def _assess_valuation_status(
        self,
        current_per: Optional[float],
        current_pbr: Optional[float],
        target_per: float,
        target_pbr: float
    ) -> Tuple[str, float]:
        """밸류에이션 상태 평가"""
        score = 50.0  # 기본값 (적정)

        if current_per and current_per > 0 and target_per > 0:
            # PER 대비 평가
            per_ratio = current_per / target_per

            if per_ratio < 0.7:
                score += 25  # 강한 저평가
            elif per_ratio < 0.9:
                score += 15  # 저평가
            elif per_ratio < 1.1:
                score += 0   # 적정
            elif per_ratio < 1.3:
                score -= 15  # 고평가
            else:
                score -= 25  # 강한 고평가

        if current_pbr and current_pbr > 0 and target_pbr > 0:
            # PBR 대비 평가
            pbr_ratio = current_pbr / target_pbr

            if pbr_ratio < 0.7:
                score += 15
            elif pbr_ratio < 0.9:
                score += 8
            elif pbr_ratio < 1.1:
                score += 0
            elif pbr_ratio < 1.3:
                score -= 8
            else:
                score -= 15

        # 점수 범위 제한
        score = max(0, min(100, score))

        # 상태 결정
        if score >= 65:
            status = "저평가"
        elif score >= 35:
            status = "적정"
        else:
            status = "고평가"

        return status, score

    def _get_sector(self, stock_code: str) -> str:
        """종목의 업종 반환"""
        return self.STOCK_SECTOR_MAP.get(stock_code, "기타")

    def get_valuation_summary(self, stock_code: str) -> Dict[str, Any]:
        """밸류에이션 요약 조회"""
        result = self.calculate_target_price(stock_code)

        return {
            "stock_code": result.stock_code,
            "stock_name": result.stock_name,
            "current_price": result.current_price,
            "target_price": result.target_price,
            "upside_pct": result.upside_pct,
            "valuation_status": result.valuation_status,
            "valuation_score": result.valuation_score,
            "target_range": {
                "low": result.target_price_low,
                "mid": result.target_price,
                "high": result.target_price_high
            },
            "methodology": result.methodology,
            "rationale": result.rationale,
            "caveats": result.caveats,
            "analyst_comment": result.analyst_comment,
            "has_override": result.has_override,
            "global_peer_info": result.global_peer_info
        }

    def list_overrides(self) -> List[Dict[str, Any]]:
        """현재 설정된 예외 목록 반환"""
        return [
            {
                "stock_code": o.stock_code,
                "stock_name": o.stock_name,
                "valuation_method": o.valuation_method,
                "global_peer_name": o.global_peer_name,
                "custom_target_per": o.custom_target_per,
                "caveats_count": len(o.caveats)
            }
            for o in self.overrides.values()
        ]
