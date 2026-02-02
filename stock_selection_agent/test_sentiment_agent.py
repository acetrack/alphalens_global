"""
Sentiment Agent 테스트 스크립트
"""

import logging
from src.agents.sentiment_agent import SentimentAgent, SentimentAnalysisConfig
from src.api.krx_client import KrxClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_sentiment_agent():
    """센티먼트 에이전트 테스트"""
    print("=" * 80)
    print("Sentiment Agent 테스트")
    print("=" * 80)

    # KRX 클라이언트 초기화
    krx_client = KrxClient()

    # Sentiment Agent 초기화
    agent = SentimentAgent(krx_client=krx_client)

    # 테스트 종목: 삼성전자 (005930)
    stock_code = "005930"
    print(f"\n종목 코드: {stock_code}")
    print("-" * 80)

    # 센티먼트 분석 실행
    result = agent.analyze(
        stock_code=stock_code,
        current_price=65000  # 예시 현재가
    )

    # 결과 출력
    print(f"\n### 센티먼트 분석 결과 ###\n")
    print(f"종목명: {result.stock_name}")
    print(f"분석일: {result.analysis_date}")
    print(f"현재주가: {result.current_price:,}원" if result.current_price else "현재주가: N/A")
    print(f"\n종합 센티먼트 점수: {result.total_score:.1f}/100")
    print(f"센티먼트 등급: {result.sentiment_grade}")
    print(f"투자 시그널: {result.investment_signal}")

    print(f"\n### 세부 점수 ###")
    print(f"뉴스 센티먼트: {result.news_score:.1f}/100")
    print(f"애널리스트 센티먼트: {result.analyst_score:.1f}/100")
    print(f"공시 센티먼트: {result.disclosure_score:.1f}/100")
    print(f"실적 서프라이즈: {result.earnings_surprise_score:.1f}/100")

    print(f"\n### 뉴스 센티먼트 ###")
    print(f"뉴스 가중 센티먼트: {result.news_weighted_sentiment:.3f}" if result.news_weighted_sentiment else "N/A")
    print(f"뉴스 개수: {result.news_volume}개")
    print(f"뉴스 볼륨 시그널: {result.news_volume_signal}")
    print(f"긍정 뉴스: {result.positive_news_count}개")
    print(f"부정 뉴스: {result.negative_news_count}개")

    if result.recent_headlines:
        print(f"\n최근 헤드라인:")
        for i, headline in enumerate(result.recent_headlines[:3], 1):
            print(f"  {i}. [{headline['date']}] {headline['headline']}")
            print(f"     센티먼트: {headline['sentiment']:.3f}")

    print(f"\n### 애널리스트 센티먼트 ###")
    print(f"컨센서스: {result.analyst_consensus}")
    print(f"컨센서스 점수: {result.consensus_score:.2f}")
    print(f"분석 애널리스트: {result.total_analysts}명")
    print(f"3개월 의견 변화: 상향 {result.upgrades_3m}건, 하향 {result.downgrades_3m}건")
    print(f"레이팅 모멘텀: {result.rating_momentum:.2f}")

    if result.rating_distribution:
        print(f"\n투자의견 분포:")
        print(f"  Strong Buy: {result.rating_distribution.get('strong_buy', 0)}명")
        print(f"  Buy: {result.rating_distribution.get('buy', 0)}명")
        print(f"  Hold: {result.rating_distribution.get('hold', 0)}명")
        print(f"  Sell: {result.rating_distribution.get('sell', 0)}명")
        print(f"  Strong Sell: {result.rating_distribution.get('strong_sell', 0)}명")

    if result.avg_target_price and result.current_price:
        print(f"\n목표주가:")
        print(f"  평균 목표가: {result.avg_target_price:,}원")
        print(f"  중간 목표가: {result.median_target_price:,}원" if result.median_target_price else "")
        print(f"  상승여력: {result.upside_to_avg:+.2f}%")

    print(f"\n이익 추정치 수정:")
    print(f"  금년 EPS 수정률: {result.current_year_eps_revision:+.2f}%" if result.current_year_eps_revision else "  금년 EPS 수정률: N/A")
    print(f"  내년 EPS 수정률: {result.next_year_eps_revision:+.2f}%" if result.next_year_eps_revision else "  내년 EPS 수정률: N/A")
    print(f"  수정 비율: {result.revision_ratio:.2f} (상향 {result.eps_up_revisions}건, 하향 {result.eps_down_revisions}건)")
    print(f"  이익 모멘텀: {result.earnings_momentum}")

    print(f"\n### 공시 센티먼트 ###")
    print(f"총 공시: {result.total_disclosures}건")
    print(f"긍정 공시: {result.positive_disclosures}건")
    print(f"부정 공시: {result.negative_disclosures}건")
    print(f"순 센티먼트: {result.net_disclosure_sentiment:+d}")

    if result.material_events:
        print(f"\n주요 공시 이벤트:")
        for i, event in enumerate(result.material_events[:3], 1):
            print(f"  {i}. [{event['date']}] {event['title']}")

    print(f"\n### 실적 서프라이즈 ###")
    print(f"평균 서프라이즈: {result.avg_earnings_surprise:+.2f}%" if result.avg_earnings_surprise else "평균 서프라이즈: N/A")
    print(f"연속 beat: {result.consecutive_beats}분기")
    print(f"연속 miss: {result.consecutive_misses}분기")
    print(f"Beat 비율: {result.beat_rate:.2%}" if result.beat_rate else "Beat 비율: N/A")

    if result.earnings_surprises:
        print(f"\n최근 실적 서프라이즈:")
        for surprise in result.earnings_surprises[:4]:
            beat_str = "✓" if surprise['beat'] else "✗"
            print(f"  {beat_str} {surprise['quarter']}: 실제 {surprise['actual']}, 추정 {surprise['estimate']} ({surprise['surprise_pct']:+.1f}%)")

    print(f"\n### 주요 동인 ###")
    if result.key_drivers:
        for i, driver in enumerate(result.key_drivers, 1):
            print(f"  {i}. {driver}")
    else:
        print("  식별된 주요 동인 없음")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)

    return result


def test_with_multiple_stocks():
    """여러 종목 테스트"""
    print("\n" + "=" * 80)
    print("여러 종목 센티먼트 분석 테스트")
    print("=" * 80)

    krx_client = KrxClient()
    agent = SentimentAgent(krx_client=krx_client)

    # 테스트 종목들
    test_stocks = [
        ("005930", "삼성전자", 65000),
        ("000660", "SK하이닉스", 180000),
        ("035420", "NAVER", 250000),
    ]

    results = []
    for stock_code, stock_name, price in test_stocks:
        print(f"\n### {stock_name} ({stock_code}) ###")
        try:
            result = agent.analyze(stock_code=stock_code, current_price=price)
            print(f"센티먼트 점수: {result.total_score:.1f}/100 ({result.sentiment_grade})")
            print(f"투자 시그널: {result.investment_signal}")
            print(f"주요 동인: {', '.join(result.key_drivers[:2]) if result.key_drivers else 'N/A'}")
            results.append(result)
        except Exception as e:
            print(f"분석 실패: {e}")

    print("\n" + "=" * 80)
    print("여러 종목 테스트 완료")
    print("=" * 80)

    return results


if __name__ == "__main__":
    # 단일 종목 테스트
    result = test_sentiment_agent()

    # 여러 종목 테스트
    # results = test_with_multiple_stocks()
