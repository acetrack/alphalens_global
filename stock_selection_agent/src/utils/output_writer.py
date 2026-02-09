"""
상세 에이전트 결과 파일 저장 모듈

각 에이전트의 분석 결과를 개별 JSON 파일로 저장
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .serializers import dataclass_to_dict


class DetailedOutputWriter:
    """
    상세 에이전트 결과 파일 저장

    각 에이전트별 분석 결과를 개별 JSON 파일로 저장합니다.

    출력 디렉토리 구조:
        output/
        ├── financial_analysis/{code}.json
        ├── industry_analysis/{code}.json
        ├── technical_analysis/{code}.json
        ├── risk_analysis/{code}.json
        ├── sentiment_analysis/{code}.json
        └── valuations/{code}.json
    """

    # 서브디렉토리 이름
    SUBDIRS = [
        "financial_analysis",
        "industry_analysis",
        "technical_analysis",
        "risk_analysis",
        "sentiment_analysis",
        "valuations",
    ]

    def __init__(self, base_output_dir: str = "output"):
        """
        초기화

        Args:
            base_output_dir: 기본 출력 디렉토리 경로
        """
        self.base_dir = Path(base_output_dir)
        self.logger = logging.getLogger(__name__)
        self._ensure_directories()

    def _ensure_directories(self):
        """필수 서브디렉토리 생성"""
        for subdir in self.SUBDIRS:
            dir_path = self.base_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)

    def _save_json(self, filepath: Path, data: Dict[str, Any]) -> str:
        """
        JSON 파일 저장

        Args:
            filepath: 저장할 파일 경로
            data: 저장할 데이터

        Returns:
            저장된 파일 경로 문자열
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"상세 분석 저장: {filepath}")
        return str(filepath)

    def save_financial_analysis(
        self,
        stock_code: str,
        result: Dict[str, Any],
        analysis_date: Optional[str] = None
    ) -> Optional[str]:
        """
        재무 분석 결과 저장

        Args:
            stock_code: 종목코드
            result: FinancialAgent 분석 결과 (Dict)
            analysis_date: 분석일 (없으면 오늘)

        Returns:
            저장된 파일 경로 또는 None
        """
        if not result:
            return None

        analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d")

        data = {
            "stock_code": stock_code,
            "analysis_date": analysis_date,
            **result  # Financial Agent는 이미 Dict 반환
        }

        filepath = self.base_dir / "financial_analysis" / f"{stock_code}.json"
        return self._save_json(filepath, data)

    def save_industry_analysis(
        self,
        stock_code: str,
        result: Any,
        analysis_date: Optional[str] = None
    ) -> Optional[str]:
        """
        산업 분석 결과 저장

        Args:
            stock_code: 종목코드
            result: IndustryAnalysisResult dataclass
            analysis_date: 분석일

        Returns:
            저장된 파일 경로 또는 None
        """
        if not result:
            return None

        analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d")

        data = dataclass_to_dict(result)
        data["analysis_date"] = analysis_date

        filepath = self.base_dir / "industry_analysis" / f"{stock_code}.json"
        return self._save_json(filepath, data)

    def save_technical_analysis(
        self,
        stock_code: str,
        result: Any,
        analysis_date: Optional[str] = None
    ) -> Optional[str]:
        """
        기술적 분석 결과 저장

        Args:
            stock_code: 종목코드
            result: TechnicalAnalysisResult dataclass
            analysis_date: 분석일

        Returns:
            저장된 파일 경로 또는 None
        """
        if not result:
            return None

        analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d")

        data = dataclass_to_dict(result)
        if "analysis_date" not in data or not data.get("analysis_date"):
            data["analysis_date"] = analysis_date

        filepath = self.base_dir / "technical_analysis" / f"{stock_code}.json"
        return self._save_json(filepath, data)

    def save_risk_analysis(
        self,
        stock_code: str,
        result: Any,
        analysis_date: Optional[str] = None
    ) -> Optional[str]:
        """
        리스크 분석 결과 저장

        Args:
            stock_code: 종목코드
            result: RiskAnalysisResult dataclass
            analysis_date: 분석일

        Returns:
            저장된 파일 경로 또는 None
        """
        if not result:
            return None

        analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d")

        data = dataclass_to_dict(result)
        if "analysis_date" not in data or not data.get("analysis_date"):
            data["analysis_date"] = analysis_date

        filepath = self.base_dir / "risk_analysis" / f"{stock_code}.json"
        return self._save_json(filepath, data)

    def save_sentiment_analysis(
        self,
        stock_code: str,
        result: Any,
        analysis_date: Optional[str] = None
    ) -> Optional[str]:
        """
        센티먼트 분석 결과 저장

        Args:
            stock_code: 종목코드
            result: SentimentAnalysisResult dataclass
            analysis_date: 분석일

        Returns:
            저장된 파일 경로 또는 None
        """
        if not result:
            return None

        analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d")

        data = dataclass_to_dict(result)
        if "analysis_date" not in data or not data.get("analysis_date"):
            data["analysis_date"] = analysis_date

        filepath = self.base_dir / "sentiment_analysis" / f"{stock_code}.json"
        return self._save_json(filepath, data)

    def save_valuation(
        self,
        stock_code: str,
        result: Any,
        analysis_date: Optional[str] = None
    ) -> Optional[str]:
        """
        밸류에이션 결과 저장

        Args:
            stock_code: 종목코드
            result: TargetPriceResult dataclass (to_dict 메서드 있음)
            analysis_date: 분석일

        Returns:
            저장된 파일 경로 또는 None
        """
        if not result:
            return None

        analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d")

        # TargetPriceResult는 to_dict() 메서드가 있음
        if hasattr(result, "to_dict"):
            data = result.to_dict()
        else:
            data = dataclass_to_dict(result)

        data["analysis_date"] = analysis_date

        filepath = self.base_dir / "valuations" / f"{stock_code}.json"
        return self._save_json(filepath, data)

    def save_all(
        self,
        stock_code: str,
        financial_result: Optional[Dict] = None,
        industry_result: Optional[Any] = None,
        technical_result: Optional[Any] = None,
        risk_result: Optional[Any] = None,
        sentiment_result: Optional[Any] = None,
        valuation_result: Optional[Any] = None,
        analysis_date: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        모든 에이전트 결과 일괄 저장

        Args:
            stock_code: 종목코드
            financial_result: 재무 분석 결과
            industry_result: 산업 분석 결과
            technical_result: 기술적 분석 결과
            risk_result: 리스크 분석 결과
            sentiment_result: 센티먼트 분석 결과
            valuation_result: 밸류에이션 결과
            analysis_date: 분석일

        Returns:
            에이전트별 저장된 파일 경로 딕셔너리
        """
        analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d")

        saved_files = {
            "financial": self.save_financial_analysis(
                stock_code, financial_result, analysis_date
            ),
            "industry": self.save_industry_analysis(
                stock_code, industry_result, analysis_date
            ),
            "technical": self.save_technical_analysis(
                stock_code, technical_result, analysis_date
            ),
            "risk": self.save_risk_analysis(
                stock_code, risk_result, analysis_date
            ),
            "sentiment": self.save_sentiment_analysis(
                stock_code, sentiment_result, analysis_date
            ),
            "valuation": self.save_valuation(
                stock_code, valuation_result, analysis_date
            ),
        }

        # 저장된 파일 수 로깅
        saved_count = sum(1 for v in saved_files.values() if v is not None)
        self.logger.info(
            f"상세 분석 파일 저장 완료: {stock_code} ({saved_count}/6개 에이전트)"
        )

        return saved_files
