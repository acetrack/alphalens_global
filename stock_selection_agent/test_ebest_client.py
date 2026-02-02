"""
eBest xingAPI 클라이언트 테스트
"""

import logging
from src.api.ebest_client import EbestClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_ebest_authentication():
    """eBest API 인증 테스트"""
    print("=" * 80)
    print("eBest API 인증 테스트")
    print("=" * 80)

    try:
        client = EbestClient()
        print(f"✅ 인증 성공!")
        print(f"Access Token: {client.access_token[:20]}...")
        print(f"토큰 만료: {client.token_expires_at}")
        return client
    except Exception as e:
        print(f"❌ 인증 실패: {e}")
        return None


def test_analyst_data(client, stock_code="005930"):
    """애널리스트 데이터 조회 테스트"""
    print("\n" + "=" * 80)
    print(f"애널리스트 데이터 조회 테스트 ({stock_code})")
    print("=" * 80)

    try:
        data = client.get_analyst_consensus(stock_code)

        if data:
            print("✅ 애널리스트 데이터 조회 성공!")
            print(f"  투자의견 분포:")
            for rating, count in data["rating_distribution"].items():
                print(f"    {rating}: {count}명")
            print(f"  목표주가: {len(data['target_prices'])}개")
            if data['target_prices']:
                avg_tp = sum(data['target_prices']) / len(data['target_prices'])
                print(f"  평균 목표주가: {avg_tp:,.0f}원")
        else:
            print("⚠️ 데이터가 없습니다.")

    except Exception as e:
        print(f"❌ 조회 실패: {e}")


def test_earnings_data(client, stock_code="005930"):
    """실적 데이터 조회 테스트"""
    print("\n" + "=" * 80)
    print(f"실적 데이터 조회 테스트 ({stock_code})")
    print("=" * 80)

    try:
        data = client.get_earnings_data(stock_code)

        if data:
            print(f"✅ 실적 데이터 조회 성공! ({len(data)}분기)")
            for item in data[:4]:
                print(f"  {item['quarter']}: 실제 {item['actual_eps']}, 추정 {item['estimate_eps']}")
        else:
            print("⚠️ 데이터가 없습니다.")

    except Exception as e:
        print(f"❌ 조회 실패: {e}")


if __name__ == "__main__":
    # 1. 인증 테스트
    client = test_ebest_authentication()

    if client:
        # 2. 애널리스트 데이터 테스트
        test_analyst_data(client, "005930")

        # 3. 실적 데이터 테스트
        test_earnings_data(client, "005930")

        # 세션 종료
        client.close()

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)
