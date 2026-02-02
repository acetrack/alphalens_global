"""
하이브리드 실적 데이터 수집 테스트

DART (공식) + Naver (속보성) 조합 테스트
"""

import sys
import os
import logging

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.sentiment_agent import SentimentAgent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_hybrid_earnings():
    """하이브리드 실적 데이터 수집 테스트"""

    print("=" * 80)
    print("하이브리드 실적 데이터 수집 테스트")
    print("=" * 80)
    print()

    # 에이전트 초기화
    agent = SentimentAgent()

    # 테스트 종목: 삼성전자
    # 1월 29일 2025 Q4 실적 발표 (DART에는 2월 14일까지 없을 예정)
    stock_code = "005930"
    stock_name = "삼성전자"

    print(f"테스트 종목: {stock_name} ({stock_code})")
    print()

    print("기대 동작:")
    print("1. DART에서 2025 Q4 조회 시도 → 없음 (아직 공시 안됨)")
    print("2. DART에서 2025 Q3 데이터 확인 → 있음")
    print("3. 최신 분기 없으므로 Naver 금융에서 2025 Q4 확인 시도")
    print("4. Naver에 2025 Q4 있으면 → Naver 데이터 사용")
    print("5. Naver에도 없으면 → DART 2025 Q3 데이터 사용")
    print()

    print("-" * 80)
    print("실적 데이터 수집 시작...")
    print("-" * 80)
    print()

    # 센티먼트 분석 실행
    result = agent.analyze(stock_code, stock_name)

    print()
    print("=" * 80)
    print("실적 분석 결과")
    print("=" * 80)
    print()

    print(f"실적 점수: {result.earnings_surprise_score:.1f}/100")
    print()

    surprises = result.earnings_surprises
    if surprises:
        print("실적 상세:")
        for surprise in surprises:
            quarter = surprise.get("quarter", "")
            actual = surprise.get("actual", 0)
            estimate = surprise.get("estimate", 0)
            surprise_pct = surprise.get("surprise_pct", 0)
            beat = "✅ Beat" if surprise.get("beat") else "❌ Miss"

            print(f"  {quarter}:")
            print(f"    실제: {actual:,.0f}")
            print(f"    비교: {estimate:,.0f}")
            print(f"    성장률: {surprise_pct:+.1f}%")
            print(f"    결과: {beat}")
            print()

    print("-" * 80)
    print("전체 센티먼트 분석 결과")
    print("-" * 80)
    print()

    print(f"총 센티먼트 점수: {result.total_score:.1f}/100")
    print(f"투자 시그널: {result.investment_signal}")
    print()

    print("세부 점수:")
    print(f"  뉴스: {result.news_score:.1f}/100 (가중치 30%)")
    print(f"  애널리스트: {result.analyst_score:.1f}/100 (가중치 35%)")
    print(f"  공시: {result.disclosure_score:.1f}/100 (가중치 20%)")
    print(f"  실적: {result.earnings_surprise_score:.1f}/100 (가중치 15%)")
    print()

    print("=" * 80)
    print("테스트 완료")
    print("=" * 80)

if __name__ == "__main__":
    test_hybrid_earnings()
