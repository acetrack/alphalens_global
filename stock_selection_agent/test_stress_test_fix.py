"""
스트레스 테스트 수정 검증
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.risk_agent import RiskAgent


def test_stress_test_with_none_values():
    """None 값이 포함된 경우 스트레스 테스트"""
    print("=" * 60)
    print("스트레스 테스트 None 값 처리 검증")
    print("=" * 60)

    agent = RiskAgent()

    # 테스트 케이스 1: beta가 None인 경우
    print("\n1. Beta가 None인 경우 테스트...")
    try:
        price_history = [{"close_price": 50000}]
        credit_risk = {"debt_to_equity": 1.5}

        result = agent._perform_stress_test(
            "000000",
            price_history,
            beta=None,  # None 값
            credit_risk=credit_risk
        )

        print(f"   ✓ 성공 - 시장 급락 시나리오: {result['market_crash']['estimated_loss_pct']}%")
        print(f"   ✓ 성공 - 금리 충격 시나리오: {result['interest_rate_shock']['estimated_loss_pct']}%")
    except Exception as e:
        print(f"   ✗ 실패: {e}")
        import traceback
        traceback.print_exc()

    # 테스트 케이스 2: debt_to_equity가 None인 경우
    print("\n2. Debt-to-Equity가 None인 경우 테스트...")
    try:
        price_history = [{"close_price": 50000}]
        credit_risk = {"debt_to_equity": None}  # None 값

        result = agent._perform_stress_test(
            "000000",
            price_history,
            beta=1.2,
            credit_risk=credit_risk
        )

        print(f"   ✓ 성공 - 시장 급락 시나리오: {result['market_crash']['estimated_loss_pct']}%")
        print(f"   ✓ 성공 - 금리 충격 시나리오: {result['interest_rate_shock']['estimated_loss_pct']}%")
    except Exception as e:
        print(f"   ✗ 실패: {e}")
        import traceback
        traceback.print_exc()

    # 테스트 케이스 3: 정상 케이스
    print("\n3. 정상 값인 경우 테스트...")
    try:
        price_history = [{"close_price": 50000}]
        credit_risk = {"debt_to_equity": 1.5}

        result = agent._perform_stress_test(
            "000000",
            price_history,
            beta=1.2,
            credit_risk=credit_risk
        )

        print(f"   ✓ 성공 - 시장 급락 시나리오: {result['market_crash']['estimated_loss_pct']}%")
        print(f"   ✓ 성공 - 금리 충격 시나리오: {result['interest_rate_shock']['estimated_loss_pct']}%")
        print(f"   ✓ 성공 - 원화 약세 시나리오: {result['currency_depreciation']['estimated_loss_pct']}%")
        print(f"   ✓ 성공 - 섹터 침체 시나리오: {result['sector_downturn']['estimated_loss_pct']}%")
    except Exception as e:
        print(f"   ✗ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("검증 완료")
    print("=" * 60)


if __name__ == "__main__":
    test_stress_test_with_none_values()
