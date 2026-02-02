"""
Risk Agent 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.risk_agent import RiskAgent, RiskAnalysisConfig


def test_risk_agent_basic():
    """RiskAgent 기본 테스트"""
    print("=" * 60)
    print("RiskAgent 기본 테스트")
    print("=" * 60)

    # 1. RiskAgent 초기화
    print("\n1. RiskAgent 초기화...")
    agent = RiskAgent()
    print("   ✓ RiskAgent 초기화 성공")

    # 2. 설정 확인
    print("\n2. 설정 확인...")
    config = agent.config
    print(f"   - 시장 리스크 가중치: {config.market_risk_weight}")
    print(f"   - 신용 리스크 가중치: {config.credit_risk_weight}")
    print(f"   - 유동성 리스크 가중치: {config.liquidity_risk_weight}")
    print(f"   - 집중 리스크 가중치: {config.concentration_risk_weight}")
    print("   ✓ 설정 확인 완료")

    # 3. 종목 분석 테스트 (삼성전자: 005930)
    print("\n3. 종목 분석 테스트 (삼성전자)...")
    try:
        # 간단한 재무 데이터 (테스트용)
        test_financial_data = {
            "total_assets": 100000000000,
            "working_capital": 10000000000,
            "retained_earnings": 20000000000,
            "ebit": 5000000000,
            "ebitda": 6000000000,
            "total_liabilities": 40000000000,
            "total_debt": 20000000000,
            "equity": 60000000000,
            "cash": 5000000000,
            "interest_expense": 500000000,
            "revenue": 80000000000,
            "market_cap": 300000000000
        }

        result = agent.analyze("005930", financial_data=test_financial_data)

        print(f"\n   종목명: {result.stock_name}")
        print(f"   종목코드: {result.stock_code}")
        print(f"   분석일: {result.analysis_date}")
        print(f"\n   === 리스크 점수 ===")
        print(f"   종합 리스크 점수: {result.total_risk_score:.1f}")
        print(f"   리스크 등급: {result.risk_grade}")
        print(f"\n   === 세부 점수 ===")
        print(f"   시장 리스크: {result.market_risk_score:.1f}")
        print(f"   신용 리스크: {result.credit_risk_score:.1f}")
        print(f"   유동성 리스크: {result.liquidity_risk_score:.1f}")
        print(f"   집중 리스크: {result.concentration_risk_score:.1f}")

        if result.beta_adjusted:
            print(f"\n   === 시장 리스크 상세 ===")
            print(f"   Beta (조정): {result.beta_adjusted:.2f}")
            print(f"   연간 변동성: {result.annual_volatility:.2%}" if result.annual_volatility else "")
            print(f"   VaR 95%: {result.var_95:.2%}" if result.var_95 else "")
            print(f"   최대 낙폭(MDD): {result.max_drawdown:.2%}" if result.max_drawdown else "")

        if result.z_score:
            print(f"\n   === 신용 리스크 상세 ===")
            print(f"   Z-Score: {result.z_score:.2f} ({result.z_score_zone})")
            print(f"   부채비율: {result.debt_to_equity:.2f}" if result.debt_to_equity else "")
            print(f"   이자보상배율: {result.interest_coverage:.1f}" if result.interest_coverage else "")

        if result.liquidity_grade:
            print(f"\n   === 유동성 리스크 상세 ===")
            print(f"   유동성 등급: {result.liquidity_grade}")
            print(f"   일평균 거래대금: {result.avg_daily_trading_value:,}원" if result.avg_daily_trading_value else "")

        if result.key_risks:
            print(f"\n   === 주요 리스크 요인 ===")
            for i, risk in enumerate(result.key_risks, 1):
                print(f"   {i}. {risk}")

        print("\n   ✓ 종목 분석 성공")

    except Exception as e:
        print(f"   ✗ 종목 분석 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    test_risk_agent_basic()
