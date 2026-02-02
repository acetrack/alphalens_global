"""
eBest 이베스트투자증권 xingAPI Plus 클라이언트

REST API를 통해 애널리스트 데이터, 실적 데이터 등을 조회
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
import urllib3

# SSL 인증서 경고 억제 (개발 환경)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class EbestClient:
    """
    eBest xingAPI Plus REST API 클라이언트

    사용법:
        client = EbestClient()
        # 자동으로 환경 변수에서 API 키 로드

        # 애널리스트 데이터 조회
        analyst_data = client.get_analyst_consensus("005930")

        # 실적 데이터 조회
        earnings_data = client.get_earnings_data("005930")
    """

    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        base_url: str = "https://openapi.ls-sec.co.kr:8080"
    ):
        """
        eBest 클라이언트 초기화

        Args:
            app_key: API 앱 키 (None이면 환경 변수에서 로드)
            app_secret: API 시크릿 (None이면 환경 변수에서 로드)
            base_url: API 베이스 URL
        """
        self.logger = logging.getLogger(__name__)

        # API 키 설정
        self.app_key = app_key or os.environ.get("EBEST_APP_KEY")
        self.app_secret = app_secret or os.environ.get("EBEST_APP_SECRET")

        if not self.app_key or not self.app_secret:
            raise ValueError("EBEST_APP_KEY와 EBEST_APP_SECRET 환경 변수가 필요합니다.")

        self.base_url = base_url
        self.access_token = None
        self.token_expires_at = None

        # 세션 생성
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "StockSelectionAgent/1.0"
        })

        # 인증
        self._authenticate()

    def _authenticate(self):
        """OAuth2 토큰 발급"""
        try:
            url = f"{self.base_url}/oauth2/token"

            # Form-urlencoded 형식으로 데이터 전송
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecretkey": self.app_secret,
                "scope": "oob"
            }

            # Content-Type을 지정하지 않고 data로 전송 (form-urlencoded)
            response = requests.post(url, data=data, timeout=10, verify=False)
            response.raise_for_status()

            result = response.json()

            self.access_token = result.get("access_token")
            expires_in = result.get("expires_in", 86400)  # 기본 24시간

            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5분 여유

            # 세션 헤더에 토큰 추가
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })

            self.logger.info("eBest API 인증 완료")

        except Exception as e:
            self.logger.error(f"eBest API 인증 실패: {e}")
            raise

    def _ensure_authenticated(self):
        """토큰 만료 확인 및 재발급"""
        if not self.access_token or datetime.now() >= self.token_expires_at:
            self.logger.info("토큰 만료, 재발급 중...")
            self._authenticate()

    def _request(self, tr_code: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        xingAPI TR 요청

        Args:
            tr_code: TR 코드 (예: t3320, t1717)
            params: 요청 파라미터

        Returns:
            응답 데이터
        """
        self._ensure_authenticated()

        # TR 코드별 엔드포인트 매핑
        tr_endpoint_map = {
            "t3401": "/stock/investinfo",  # 투자의견 조회
            "t3320": "/stock/investinfo",  # 기업 정보
            "t1717": "/stock/accno",  # 분기별 실적
            "t8436": "/stock/consensus",  # EPS 컨센서스
            "t8424": "/stock/consensus",  # 실적 컨센서스
        }

        # 엔드포인트 결정
        endpoint = tr_endpoint_map.get(tr_code, "/stock/market")

        try:
            url = f"{self.base_url}{endpoint}"

            # eBest API 형식: {"t3320InBlock": {"gicode": "001200"}}
            # TR 코드에 "InBlock" 접미사 추가
            block_name = f"{tr_code}InBlock"

            # JSON body 구조
            body_data = {
                block_name: params
            }

            # TR 코드를 헤더에 전달 (필수!)
            headers = {
                "tr_cd": tr_code,  # TR 코드 (필수)
                "tr_cont": "N",    # 연속 조회 여부
                "tr_cont_key": ""  # 연속 조회 키
            }

            # POST 방식으로 JSON 요청
            response = self.session.post(
                url,
                json=body_data,  # JSON 형식
                headers=headers,  # TR 코드 헤더
                timeout=30,
                verify=False
            )

            # 응답 확인
            if response.status_code == 404:
                self.logger.error(f"404 Not Found: {endpoint} (TR: {tr_code})")
                return {}

            response.raise_for_status()
            result = response.json()

            # API 응답 확인
            if result.get("rsp_cd") not in ["00000", "0000", None]:
                error_msg = result.get("rsp_msg", "Unknown error")
                self.logger.error(f"API 오류 ({tr_code}): {error_msg}")
                self.logger.debug(f"응답 내용: {result}")
                return {}

            self.logger.info(f"성공: {endpoint} (TR: {tr_code})")
            return result

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP 오류 ({tr_code}): {e}")
            if hasattr(e.response, 'text'):
                self.logger.debug(f"응답 본문: {e.response.text[:500]}")
            return {}
        except Exception as e:
            self.logger.error(f"API 요청 실패 ({tr_code}): {e}")
            return {}

    def get_analyst_consensus(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        애널리스트 컨센서스 조회

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            애널리스트 데이터 딕셔너리
            {
                "rating_distribution": {...},
                "target_prices": [...],
                "eps_revision_current": float,
                "eps_revision_next": float,
                ...
            }
        """
        try:
            # t3401: 투자의견 조회
            params = {
                "shcode": stock_code.zfill(6),  # 종목코드 (6자리)
                "gubun1": "",   # 전체
                "tradno": "",   # 전체 증권사
                "cts_date": ""  # 연속 조회 키
            }

            result = self._request("t3401", params)

            if not result:
                return None

            # 응답 데이터 파싱 (t3401OutBlock1은 배열)
            output = result.get("t3401OutBlock1", [])

            if not output:
                return None

            # 투자의견 집계
            rating_distribution = {
                "strong_buy": 0,
                "buy": 0,
                "hold": 0,
                "sell": 0,
                "strong_sell": 0
            }

            target_prices = []

            for item in output:
                # 투자의견 (bopn 필드)
                opinion = item.get("bopn", "").upper()
                if "BUY" in opinion:
                    if "STRONG" in opinion:
                        rating_distribution["strong_buy"] += 1
                    else:
                        rating_distribution["buy"] += 1
                elif "HOLD" in opinion or "중립" in opinion:
                    rating_distribution["hold"] += 1
                elif "SELL" in opinion:
                    if "STRONG" in opinion:
                        rating_distribution["strong_sell"] += 1
                    else:
                        rating_distribution["sell"] += 1

                # 목표주가 (noga 필드)
                target_price = item.get("noga", 0)
                if target_price and target_price > 0:
                    target_prices.append(int(target_price))

            return {
                "rating_distribution": rating_distribution,
                "target_prices": target_prices,
                "upgrades_3m": 0,  # TODO: 변경 추이 계산
                "downgrades_3m": 0,
                "tp_change_3m": 0.0,
                "eps_revision_current": 0.0,  # TODO: t8436 EPS 컨센서스
                "eps_revision_next": 0.0,
                "eps_up_count": 0,
                "eps_down_count": 0
            }

        except Exception as e:
            self.logger.error(f"애널리스트 데이터 조회 실패: {e}")
            return None

    def get_earnings_data(self, stock_code: str) -> List[Dict[str, Any]]:
        """
        실적 데이터 조회 (t3320 사용)

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            실적 데이터 리스트 (trailing + forward)
            [
                {
                    "period": "202412",
                    "period_type": "actual",
                    "eps": 3472,
                    "per": 43.32,
                    "roe": 10.23,
                    "roa": 7.58,
                    "pbr": 3.77
                },
                {
                    "period": "202509",
                    "period_type": "estimate",
                    "eps": 3087,
                    "per": 48.72
                }
            ]
        """
        try:
            # t3320: 기업 재무 정보 조회
            params = {
                "gicode": stock_code.zfill(6)  # 6자리 코드 (접두사 없음)
            }

            result = self._request("t3320", params)

            if not result:
                return []

            # 응답 데이터 파싱
            block = result.get("t3320OutBlock1", {})

            if not block:
                return []

            earnings_data = []

            # Actual (Trailing) 데이터
            gsym = block.get("gsym", "")  # 실제 실적 기간
            eps = float(block.get("eps", 0) or 0)
            per = float(block.get("per", 0) or 0)
            roe = float(block.get("roe", 0) or 0)
            roa = float(block.get("roa", 0) or 0)
            pbr = float(block.get("pbr", 0) or 0)

            if gsym and eps:
                earnings_data.append({
                    "period": gsym,
                    "period_type": "actual",
                    "eps": eps,
                    "per": per,
                    "roe": roe,
                    "roa": roa,
                    "pbr": pbr
                })

            # Estimate (Forward) 데이터
            t_gsym = block.get("t_gsym", "")  # 추정 실적 기간
            t_eps = float(block.get("t_eps", 0) or 0)
            t_per = float(block.get("t_per", 0) or 0)

            if t_gsym and t_eps:
                earnings_data.append({
                    "period": t_gsym,
                    "period_type": "estimate",
                    "eps": t_eps,
                    "per": t_per
                })

            return earnings_data

        except Exception as e:
            self.logger.error(f"실적 데이터 조회 실패: {e}")
            return []

    def close(self):
        """세션 종료"""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
