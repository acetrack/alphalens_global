#!/usr/bin/env python
"""
DART API 연결 테스트 스크립트
환경변수 DART_API_KEY가 설정되어 있어야 합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


def test_dart_api():
    """DART API 연결 테스트"""
    print("=" * 60)
    print("DART API 연결 테스트")
    print("=" * 60)

    # 1. API 키 확인
    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        print("\n❌ DART_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   설정 방법: export DART_API_KEY=your_api_key")
        print("   또는 .env 파일에 DART_API_KEY=your_api_key 추가")
        return False

    print(f"\n✅ API 키 확인: {api_key[:8]}...{api_key[-4:]}")

    # 2. DartClient 초기화
    from src.api.dart_client import DartClient, DartApiError
    try:
        client = DartClient(api_key=api_key)
        print("✅ DartClient 초기화 성공")
    except Exception as e:
        print(f"❌ DartClient 초기화 실패: {e}")
        return False

    # 3. 기업코드 매핑 다운로드 테스트
    print("\n--- 기업코드 매핑 로드 ---")
    try:
        # corpCode.xml 다운로드 및 파싱 (자동으로 캐시됨)
        corp_code = client.get_corp_code_by_stock_code("005930")  # 삼성전자 종목코드
        if corp_code:
            print(f"✅ 삼성전자 (005930) → 기업코드: {corp_code}")
        else:
            print("⚠️  삼성전자 기업코드를 찾을 수 없습니다.")
            corp_code = "00126380"  # 폴백

        # 회사명으로도 조회 테스트
        corp_code2 = client.get_corp_code("삼성전자")
        if corp_code2:
            print(f"✅ '삼성전자' → 기업코드: {corp_code2}")

        # SK하이닉스 테스트
        sk_corp_code = client.get_corp_code_by_stock_code("000660")
        if sk_corp_code:
            print(f"✅ SK하이닉스 (000660) → 기업코드: {sk_corp_code}")

    except DartApiError as e:
        print(f"❌ 기업코드 매핑 로드 실패: {e}")
        corp_code = "00126380"  # 폴백
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        corp_code = "00126380"  # 폴백

    # 4. 기업 개황 조회
    print("\n--- 기업 개황 조회 ---")
    try:
        company_info = client.get_company_info(corp_code)
        if company_info and "corp_name" in company_info:
            print(f"✅ 기업명: {company_info.get('corp_name')}")
            print(f"   종목코드: {company_info.get('stock_code')}")
            print(f"   대표자: {company_info.get('ceo_nm')}")
            print(f"   업종: {company_info.get('induty_code')}")
        else:
            print(f"⚠️  기업 정보 조회 결과: {company_info}")
    except DartApiError as e:
        print(f"❌ 기업 개황 조회 실패: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

    # 5. 재무제표 조회 (2024년 사업보고서)
    print("\n--- 재무제표 조회 (2024년) ---")
    try:
        # 2024년 3분기 보고서 시도
        fs = client.get_financial_statement(
            corp_code=corp_code,
            bsns_year="2024",
            reprt_code="11014"  # 3분기 보고서
        )
        if fs and "list" in fs and fs["list"]:
            print(f"✅ 재무제표 조회 성공: {len(fs['list'])}개 항목")
            # 주요 항목 출력
            for item in fs["list"][:5]:
                print(f"   - {item.get('account_nm')}: {item.get('thstrm_amount')}")
        else:
            print(f"⚠️  재무제표 데이터 없음 (status: {fs.get('status', 'N/A')})")
            print("   2023년 사업보고서로 재시도...")

            # 2023년 사업보고서 시도
            fs = client.get_financial_statement(
                corp_code=corp_code,
                bsns_year="2023",
                reprt_code="11011"  # 사업보고서
            )
            if fs and "list" in fs and fs["list"]:
                print(f"✅ 2023년 재무제표 조회 성공: {len(fs['list'])}개 항목")
                for item in fs["list"][:5]:
                    print(f"   - {item.get('account_nm')}: {item.get('thstrm_amount')}")
            else:
                print(f"⚠️  2023년 재무제표도 없음")

    except DartApiError as e:
        print(f"❌ 재무제표 조회 실패: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_dart_api()
    sys.exit(0 if success else 1)
