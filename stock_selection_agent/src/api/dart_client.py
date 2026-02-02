"""
DART (전자공시시스템) API Client
https://opendart.fss.or.kr

무료 API - API Key 필요 (https://opendart.fss.or.kr 에서 발급)
- 일일 호출 제한: 10,000회
- 재무제표, 기업개황, 공시정보 등 제공
"""

import os
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime, date
from dataclasses import dataclass
import time
import zipfile
import io
import xml.etree.ElementTree as ET
import json
from pathlib import Path
import logging


@dataclass
class DartConfig:
    """DART API 설정"""
    api_key: str
    base_url: str = "https://opendart.fss.or.kr/api"
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0


class DartClient:
    """
    DART 전자공시시스템 API 클라이언트

    주요 기능:
    - 기업 개황 조회
    - 재무제표 조회 (연결/별도)
    - 배당 정보 조회
    - 공시 목록 조회

    사용법:
        client = DartClient(api_key="your_api_key")
        # 또는 환경변수 DART_API_KEY 설정

        # 삼성전자 재무제표 조회
        fs = client.get_financial_statement("00126380", "2024", "11011")
    """

    def __init__(self, api_key: Optional[str] = None, config: Optional[DartConfig] = None):
        """
        DART API 클라이언트 초기화

        Args:
            api_key: DART API 키. 미입력시 환경변수 DART_API_KEY 사용
            config: DartConfig 객체. 미입력시 기본값 사용
        """
        self.api_key = api_key or os.environ.get("DART_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DART API 키가 필요합니다. "
                "api_key 파라미터로 전달하거나 DART_API_KEY 환경변수를 설정하세요. "
                "API 키는 https://opendart.fss.or.kr 에서 무료로 발급받을 수 있습니다."
            )

        self.config = config or DartConfig(api_key=self.api_key)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "StockSelectionAgent/1.0"
        })

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """API 요청 실행"""
        url = f"{self.config.base_url}/{endpoint}.json"
        params["crtfc_key"] = self.api_key

        for attempt in range(self.config.retry_count):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                data = response.json()

                # DART API 응답 코드 확인
                status = data.get("status", "000")
                if status == "000":  # 정상
                    return data
                elif status == "013":  # 조회된 데이터가 없음
                    return {"status": "013", "message": "조회된 데이터가 없습니다", "list": []}
                else:
                    raise DartApiError(f"DART API 오류: {data.get('message', '알 수 없는 오류')}")

            except requests.exceptions.RequestException as e:
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                raise DartApiError(f"API 요청 실패: {e}")

        raise DartApiError("최대 재시도 횟수 초과")

    # =========================================================================
    # 기업 개황
    # =========================================================================

    def get_corp_code(self, corp_name: str) -> Optional[str]:
        """
        회사명으로 고유번호(corp_code) 조회

        Args:
            corp_name: 회사명 (예: "삼성전자")

        Returns:
            고유번호 (예: "00126380")
        """
        self._ensure_corp_code_loaded()
        return self._name_to_corp_code.get(corp_name)

    def get_corp_code_by_stock_code(self, stock_code: str) -> Optional[str]:
        """
        종목코드로 고유번호(corp_code) 조회

        Args:
            stock_code: 종목코드 (예: "005930")

        Returns:
            고유번호 (예: "00126380")
        """
        self._ensure_corp_code_loaded()
        return self._stock_to_corp_code.get(stock_code)

    def get_stock_code_by_corp_code(self, corp_code: str) -> Optional[str]:
        """
        고유번호로 종목코드 조회

        Args:
            corp_code: 고유번호 (예: "00126380")

        Returns:
            종목코드 (예: "005930")
        """
        self._ensure_corp_code_loaded()
        return self._corp_to_stock_code.get(corp_code)

    def _ensure_corp_code_loaded(self):
        """기업코드 매핑 데이터가 로드되었는지 확인하고, 없으면 로드"""
        if hasattr(self, '_corp_code_loaded') and self._corp_code_loaded:
            return

        # 캐시 파일 경로
        cache_dir = Path(__file__).parent.parent.parent / "data"
        cache_file = cache_dir / "corp_code_mapping.json"

        # 캐시 파일이 있고 7일 이내면 캐시 사용
        if cache_file.exists():
            cache_age_days = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).days
            if cache_age_days < 7:
                self._load_corp_code_from_cache(cache_file)
                return

        # 새로 다운로드
        self._download_and_parse_corp_code(cache_dir, cache_file)

    def _load_corp_code_from_cache(self, cache_file: Path):
        """캐시 파일에서 기업코드 매핑 로드"""
        logger = logging.getLogger(__name__)
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._stock_to_corp_code = data.get("stock_to_corp", {})
            self._corp_to_stock_code = data.get("corp_to_stock", {})
            self._name_to_corp_code = data.get("name_to_corp", {})
            self._corp_code_loaded = True
            logger.info(f"기업코드 매핑 캐시 로드 완료: {len(self._stock_to_corp_code)}개 종목")
        except Exception as e:
            logger.warning(f"캐시 로드 실패, 새로 다운로드: {e}")
            self._download_and_parse_corp_code(cache_file.parent, cache_file)

    def _download_and_parse_corp_code(self, cache_dir: Path, cache_file: Path):
        """DART에서 corpCode.xml 다운로드 및 파싱"""
        logger = logging.getLogger(__name__)
        logger.info("DART corpCode.xml 다운로드 중...")

        url = f"{self.config.base_url}/corpCode.xml"
        params = {"crtfc_key": self.api_key}

        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()

            # ZIP 파일 압축 해제
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                xml_content = zf.read("CORPCODE.xml")

            # XML 파싱
            root = ET.fromstring(xml_content)

            self._stock_to_corp_code = {}
            self._corp_to_stock_code = {}
            self._name_to_corp_code = {}

            for item in root.findall("list"):
                corp_code = item.findtext("corp_code", "")
                corp_name = item.findtext("corp_name", "")
                stock_code = item.findtext("stock_code", "")

                if corp_code:
                    self._name_to_corp_code[corp_name] = corp_code

                    if stock_code and stock_code.strip():  # 상장사만
                        self._stock_to_corp_code[stock_code] = corp_code
                        self._corp_to_stock_code[corp_code] = stock_code

            self._corp_code_loaded = True
            logger.info(f"기업코드 파싱 완료: 상장사 {len(self._stock_to_corp_code)}개, 전체 {len(self._name_to_corp_code)}개")

            # 캐시 저장
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "stock_to_corp": self._stock_to_corp_code,
                "corp_to_stock": self._corp_to_stock_code,
                "name_to_corp": self._name_to_corp_code,
                "updated_at": datetime.now().isoformat()
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"기업코드 캐시 저장: {cache_file}")

        except Exception as e:
            logger.error(f"corpCode.xml 다운로드/파싱 실패: {e}")
            # 빈 매핑으로 초기화
            self._stock_to_corp_code = {}
            self._corp_to_stock_code = {}
            self._name_to_corp_code = {}
            self._corp_code_loaded = True
            raise DartApiError(f"기업코드 목록 로드 실패: {e}")

    def get_corp_list(self) -> List[Dict[str, Any]]:
        """
        전체 기업 고유번호 목록 조회

        Returns:
            기업 목록 [{corp_code, corp_name, stock_code}, ...]
        """
        self._ensure_corp_code_loaded()

        result = []
        for name, corp_code in self._name_to_corp_code.items():
            stock_code = self._corp_to_stock_code.get(corp_code, "")
            result.append({
                "corp_code": corp_code,
                "corp_name": name,
                "stock_code": stock_code
            })
        return result

    def get_company_info(self, corp_code: str) -> Dict[str, Any]:
        """
        기업 개황 조회

        Args:
            corp_code: 고유번호 (8자리)

        Returns:
            기업 개황 정보 (회사명, 대표자, 업종, 주소 등)
        """
        return self._request("company", {"corp_code": corp_code})

    # =========================================================================
    # 재무제표
    # =========================================================================

    def get_financial_statement(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str,
        fs_div: str = "CFS"
    ) -> Dict[str, Any]:
        """
        재무제표 조회 (단일회사)

        Args:
            corp_code: 고유번호 (8자리)
            bsns_year: 사업연도 (예: "2024")
            reprt_code: 보고서 코드
                - 11013: 1분기보고서
                - 11012: 반기보고서
                - 11014: 3분기보고서
                - 11011: 사업보고서 (연간)
            fs_div: 재무제표 구분
                - CFS: 연결재무제표
                - OFS: 별도재무제표

        Returns:
            재무제표 데이터 (재무상태표, 손익계산서 등)
        """
        return self._request("fnlttSinglAcnt", {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div
        })

    def get_financial_statement_all(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str,
        fs_div: str = "CFS"
    ) -> Dict[str, Any]:
        """
        재무제표 전체 조회 (상세 계정과목)

        Args:
            corp_code: 고유번호
            bsns_year: 사업연도
            reprt_code: 보고서 코드
            fs_div: 재무제표 구분 (CFS/OFS)

        Returns:
            전체 재무제표 데이터
        """
        return self._request("fnlttSinglAcntAll", {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div
        })

    def get_multi_financial_statement(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str
    ) -> Dict[str, Any]:
        """
        다중회사 재무제표 조회 (최대 100개)

        Args:
            corp_code: 고유번호 (콤마로 구분, 최대 100개)
            bsns_year: 사업연도
            reprt_code: 보고서 코드

        Returns:
            다중 회사 재무제표 데이터
        """
        return self._request("fnlttMultiAcnt", {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code
        })

    # =========================================================================
    # 배당 정보
    # =========================================================================

    def get_dividend(self, corp_code: str, bsns_year: str, reprt_code: str) -> Dict[str, Any]:
        """
        배당에 관한 사항 조회

        Args:
            corp_code: 고유번호
            bsns_year: 사업연도
            reprt_code: 보고서 코드

        Returns:
            배당 정보 (주당배당금, 배당성향 등)
        """
        return self._request("alotMatter", {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code
        })

    # =========================================================================
    # 공시 정보
    # =========================================================================

    def get_disclosure_list(
        self,
        corp_code: Optional[str] = None,
        bgn_de: Optional[str] = None,
        end_de: Optional[str] = None,
        pblntf_ty: Optional[str] = None,
        page_no: int = 1,
        page_count: int = 100
    ) -> Dict[str, Any]:
        """
        공시 목록 조회

        Args:
            corp_code: 고유번호 (선택)
            bgn_de: 시작일 (YYYYMMDD)
            end_de: 종료일 (YYYYMMDD)
            pblntf_ty: 공시유형
                - A: 정기공시
                - B: 주요사항보고
                - C: 발행공시
                - D: 지분공시
                - E: 기타공시
                - F: 외부감사관련
                - G: 펀드공시
                - H: 자산유동화
                - I: 거래소공시
                - J: 공정위공시
            page_no: 페이지 번호
            page_count: 페이지당 건수 (최대 100)

        Returns:
            공시 목록
        """
        params = {
            "page_no": str(page_no),
            "page_count": str(page_count)
        }

        if corp_code:
            params["corp_code"] = corp_code
        if bgn_de:
            params["bgn_de"] = bgn_de
        if end_de:
            params["end_de"] = end_de
        if pblntf_ty:
            params["pblntf_ty"] = pblntf_ty

        return self._request("list", params)

    # =========================================================================
    # 주요 재무 지표 계산
    # =========================================================================

    def get_key_financials(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011"
    ) -> Dict[str, Any]:
        """
        주요 재무 지표 조회 및 계산

        Args:
            corp_code: 고유번호
            bsns_year: 사업연도
            reprt_code: 보고서 코드 (기본값: 사업보고서)

        Returns:
            주요 재무 지표 (매출액, 영업이익, 순이익, ROE 등)
        """
        # 연결재무제표 조회
        fs_data = self.get_financial_statement(
            corp_code, bsns_year, reprt_code, "CFS"
        )

        if fs_data.get("status") != "000":
            # 연결재무제표 없으면 별도재무제표 조회
            fs_data = self.get_financial_statement(
                corp_code, bsns_year, reprt_code, "OFS"
            )

        if fs_data.get("status") != "000":
            return {"error": "재무제표 조회 실패"}

        # 재무제표 항목에서 주요 지표 추출
        items = fs_data.get("list", [])
        result = {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "fs_div": fs_data.get("fs_div", ""),
            "data_date": datetime.now().strftime("%Y-%m-%d"),
        }

        # 계정과목 매핑
        account_mapping = {
            "ifrs-full_Revenue": "revenue",  # 매출액
            "ifrs-full_GrossProfit": "gross_profit",  # 매출총이익
            "dart_OperatingIncomeLoss": "operating_profit",  # 영업이익
            "ifrs-full_ProfitLoss": "net_income",  # 당기순이익
            "ifrs-full_Assets": "total_assets",  # 자산총계
            "ifrs-full_Equity": "total_equity",  # 자본총계
            "ifrs-full_Liabilities": "total_liabilities",  # 부채총계
        }

        for item in items:
            account_id = item.get("account_id", "")
            account_nm = item.get("account_nm", "")

            # 계정과목명으로 매핑 (한글)
            if "매출액" in account_nm or "수익(매출액)" in account_nm:
                result["revenue"] = self._parse_amount(item.get("thstrm_amount"))
            elif "영업이익" in account_nm:
                result["operating_profit"] = self._parse_amount(item.get("thstrm_amount"))
            elif "당기순이익" in account_nm or "당기순손익" in account_nm:
                if "지배기업" in account_nm:
                    result["net_income"] = self._parse_amount(item.get("thstrm_amount"))
            elif "자산총계" in account_nm:
                result["total_assets"] = self._parse_amount(item.get("thstrm_amount"))
            elif "자본총계" in account_nm:
                result["total_equity"] = self._parse_amount(item.get("thstrm_amount"))
            elif "부채총계" in account_nm:
                result["total_liabilities"] = self._parse_amount(item.get("thstrm_amount"))

        # 주요 비율 계산
        if result.get("operating_profit") and result.get("revenue"):
            result["op_margin"] = round(
                result["operating_profit"] / result["revenue"] * 100, 2
            )

        if result.get("net_income") and result.get("total_equity"):
            result["roe"] = round(
                result["net_income"] / result["total_equity"] * 100, 2
            )

        if result.get("total_liabilities") and result.get("total_equity"):
            result["debt_ratio"] = round(
                result["total_liabilities"] / result["total_equity"] * 100, 2
            )

        return result

    def _parse_amount(self, amount_str: Optional[str]) -> Optional[int]:
        """금액 문자열을 정수로 변환 (단위: 원)"""
        if not amount_str:
            return None
        try:
            # 콤마 제거 후 정수 변환
            return int(amount_str.replace(",", "").replace("-", "0"))
        except (ValueError, AttributeError):
            return None


class DartApiError(Exception):
    """DART API 오류"""
    pass
