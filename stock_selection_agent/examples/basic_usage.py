#!/usr/bin/env python
"""
Stock Selection Agent - 기본 사용 예제

이 예제는 종목 선정 에이전트 시스템의 기본 사용법을 보여줍니다.
"""

import sys
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api import KrxClient, DartClient
from src.agents import (
    ScreeningAgent,
    ScreeningCriteria,
    FinancialAgent,
    MasterOrchestrator,
    OrchestratorConfig
)


def example_krx_client():
    """KRX 클라이언트 사용 예제"""
    print("\n" + "=" * 50)
    print("📊 KRX 클라이언트 예제")
    print("=" * 50)

    client = KrxClient()

    # KOSPI 종목 목록 조회
    print("\n1. KOSPI 종목 목록 (상위 5개):")
    stocks = client.get_kospi_stocks()
    if "stocks" in stocks:
        for stock in stocks["stocks"][:5]:
            print(f"   - {stock['stock_name']} ({stock['stock_code']})")

    # 개별 종목 주가 조회
    print("\n2. 삼성전자 (005930) 주가 정보:")
    price = client.get_stock_price("005930")
    if "close_price" in price:
        print(f"   현재가: {price['close_price']:,}원")
        print(f"   등락률: {price.get('change_rate', 0):.2f}%")
        print(f"   거래량: {price.get('volume', 0):,}주")

    # 밸류에이션 정보 조회
    print("\n3. 삼성전자 (005930) 밸류에이션:")
    val = client.get_stock_valuation("005930")
    if "per" in val:
        print(f"   PER: {val['per']}")
        print(f"   PBR: {val['pbr']}")
        print(f"   배당수익률: {val.get('dividend_yield', 'N/A')}%")


def example_screening():
    """스크리닝 에이전트 예제"""
    print("\n" + "=" * 50)
    print("🔍 스크리닝 에이전트 예제")
    print("=" * 50)

    agent = ScreeningAgent()

    # 스크리닝 조건 설정
    criteria = ScreeningCriteria(
        min_market_cap=5_000_000_000_000,  # 5조원 이상
        max_per=20,  # PER 20 이하
        max_pbr=3,   # PBR 3 이하
        min_dividend_yield=1.0  # 배당수익률 1% 이상
    )

    print("\n스크리닝 조건:")
    print(f"   - 시가총액: {criteria.min_market_cap/1e12:.1f}조원 이상")
    print(f"   - PER: {criteria.max_per} 이하")
    print(f"   - PBR: {criteria.max_pbr} 이하")
    print(f"   - 배당수익률: {criteria.min_dividend_yield}% 이상")

    # 스크리닝 실행
    result = agent.run_screening(criteria)

    if "filtered_stocks" in result:
        print(f"\n스크리닝 결과: {len(result['filtered_stocks'])}개 종목")
        print("\n상위 5개 종목:")
        for i, stock in enumerate(result["filtered_stocks"][:5], 1):
            print(f"   {i}. {stock['stock_name']} ({stock['stock_code']}) - 점수: {stock.get('total_score', 'N/A')}")


def example_master_orchestrator():
    """마스터 오케스트레이터 예제"""
    print("\n" + "=" * 50)
    print("🎯 마스터 오케스트레이터 예제")
    print("=" * 50)

    # 설정 (DART API 키 없이도 기본 분석 가능)
    config = OrchestratorConfig(
        dart_api_key=None,  # 환경변수에서 로드하거나 None
        output_dir="examples/output"
    )

    orchestrator = MasterOrchestrator(config)

    # 삼성전자 분석
    print("\n삼성전자 (005930) 분석 중...")
    result = orchestrator.analyze_stock("005930")

    print(f"\n분석 결과:")
    print(f"   종목명: {result.stock_name}")
    print(f"   투자의견: {result.rating}")
    print(f"   Conviction Score: {result.conviction_score}/100")
    print(f"   현재가: {result.current_price:,}원")
    print(f"   목표가: {result.target_price:,}원")

    if result.target_price and result.current_price:
        upside = ((result.target_price - result.current_price) / result.current_price) * 100
        print(f"   상승여력: {upside:+.1f}%")

    # 에이전트별 스코어
    if result.agent_scores:
        print(f"\n에이전트별 스코어:")
        for score in result.agent_scores:
            print(f"   - {score.agent_name}: {score.score:.1f} (가중치: {score.weight:.0%})")

    # 데이터 신선도
    if result.data_freshness:
        print(f"\n데이터 신선도:")
        if result.data_freshness.price_data_date:
            print(f"   - 주가 데이터: {result.data_freshness.price_data_date} ({result.data_freshness.price_data_age_days}일 전)")
        if result.data_freshness.warning_message:
            print(f"   ⚠️  {result.data_freshness.warning_message}")


def example_multiple_stocks():
    """여러 종목 분석 예제"""
    print("\n" + "=" * 50)
    print("📈 여러 종목 분석 예제")
    print("=" * 50)

    orchestrator = MasterOrchestrator()

    # 분석할 종목 목록
    stock_codes = ["005930", "000660", "035420"]  # 삼성전자, SK하이닉스, 네이버

    results = []
    for code in stock_codes:
        result = orchestrator.analyze_stock(code)
        results.append(result)

    # 결과 비교
    print("\n종목 비교:")
    print("-" * 70)
    print(f"{'종목명':^12} | {'등급':^10} | {'Conviction':^10} | {'현재가':^12} | {'목표가':^12}")
    print("-" * 70)

    for r in sorted(results, key=lambda x: x.conviction_score, reverse=True):
        print(
            f"{r.stock_name:^12} | {r.rating:^10} | "
            f"{r.conviction_score:^10.1f} | "
            f"{r.current_price:>10,}원 | "
            f"{r.target_price:>10,}원"
        )


if __name__ == "__main__":
    print("\n🚀 Stock Selection Agent - 예제 실행\n")

    try:
        # 1. KRX 클라이언트 예제
        example_krx_client()

        # 2. 스크리닝 예제
        example_screening()

        # 3. 오케스트레이터 예제
        example_master_orchestrator()

        # 4. 여러 종목 분석 예제
        example_multiple_stocks()

        print("\n" + "=" * 50)
        print("✅ 모든 예제가 성공적으로 실행되었습니다!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
