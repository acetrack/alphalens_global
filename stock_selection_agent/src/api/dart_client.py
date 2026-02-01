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
        # 전체 기업 목록에서 검색 필요
        # 실제로는 corp_code.xml을 다운로드하여 로컬에서 검색하는 것이 효율적
        corp_list = self.get_corp_list()
        for corp in corp_list:
            if corp.get("corp_name") == corp_name:
                return corp.get("corp_code")
        return None

    def get_corp_list(self) -> List[Dict[str, Any]]:
        """
        전체 기업 고유번호 목록 조회 (ZIP 파일)
        주의: 대용량 데이터이므로 캐싱 권장
        """
        # corp_code.xml은 ZIP 파일로 제공되어 별도 처리 필요
        # 여기서는 간단히 에러 발생시킴
        raise NotImplementedError(
            "전체 기업 목록은 corpCode.xml API를 통해 ZIP 파일로 제공됩니다. "
            "별도의 다운로드 및 파싱이 필요합니다."
        )

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
