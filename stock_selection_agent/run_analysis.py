#!/usr/bin/env python
"""
Stock Selection Agent - 실행 스크립트
종목 분석 및 스크리닝 실행

사용법:
    # 개별 종목 분석
    python run_analysis.py --stock 005930

    # 여러 종목 분석
    python run_analysis.py --stock 005930 000660 035420

    # 전체 스크리닝
    python run_analysis.py --screening --top 10

    # DART API 키 설정하여 실행
    DART_API_KEY=your_key python run_analysis.py --stock 005930
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.agents import MasterOrchestrator, OrchestratorConfig, ScreeningCriteria


def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def analyze_stocks(orchestrator: MasterOrchestrator, stock_codes: list, save: bool = True):
    """개별 종목 분석 실행"""
    results = []

    for code in stock_codes:
        print(f"\n{'='*60}")
        print(f"📊 종목 분석: {code}")
        print(f"{'='*60}")

        result = orchestrator.analyze_stock(code)
        results.append(result)

        # 결과 출력
        print(f"\n📌 종목명: {result.stock_name}")
        print(f"📈 투자의견: {result.rating}")
        print(f"🎯 Conviction Score: {result.conviction_score}/100")
        print(f"💰 현재가: {result.current_price:,}원")
        print(f"🎯 목표가: {result.target_price:,}원")

        if result.target_price and result.current_price:
            upside = ((result.target_price - result.current_price) / result.current_price) * 100
            print(f"📊 상승여력: {upside:+.1f}%")

        # 데이터 신선도 경고
        if result.data_freshness and result.data_freshness.warning_level != "LOW":
            print(f"\n⚠️  데이터 경고: {result.data_freshness.warning_message}")

        # 에이전트 스코어
        if result.agent_scores:
            print("\n📋 에이전트별 스코어:")
            for score in result.agent_scores:
                print(f"   - {score.agent_name}: {score.score:.1f}")

        # 리스크 요인
        if result.risk_assessment and result.risk_assessment.risk_factors:
            print(f"\n⚠️  리스크 요인 ({result.risk_assessment.overall_level}):")
            for factor in result.risk_assessment.risk_factors:
                print(f"   - {factor}")

        # 보고서 저장
        if save:
            saved = orchestrator.save_report(result)
            print(f"\n📁 보고서 저장: {saved.get('markdown', 'N/A')}")

    return results


def run_screening(orchestrator: MasterOrchestrator, top_n: int = 10, save: bool = True):
    """전체 스크리닝 실행"""
    print(f"\n{'='*60}")
    print(f"🔍 KOSPI 종목 스크리닝 (상위 {top_n}개)")
    print(f"{'='*60}")

    criteria = ScreeningCriteria(
        min_market_cap=1_000_000_000_000,  # 1조원 이상
        min_trading_value=0,  # 거래대금 필터 비활성화 (주말/휴일 대응)
        min_per=0,
        max_per=30,
        min_pbr=0,
        max_pbr=5,
        min_dividend_yield=0
    )

    results = orchestrator.run_full_screening(criteria, top_n)

    if not results:
        print("\n❌ 스크리닝 결과가 없습니다.")
        return results

    def get_price_date_str(result):
        if result.data_freshness and hasattr(result.data_freshness, 'price_data_date') and result.data_freshness.price_data_date:
            pd = result.data_freshness.price_data_date
            if len(pd) == 8:
                return f"({pd[4:6]}/{pd[6:8]})"
        return ""

    def get_upside(result):
        if result.target_price and result.current_price and result.current_price > 0:
            return ((result.target_price - result.current_price) / result.current_price) * 100
        return None

    def print_conviction_table(ranked_results, title):
        """Conviction Score 기준 테이블 (멀티팩터 점수 강조)"""
        print(f"\n{title}")
        print("-" * 130)
        print(f"{'순위':^4} | {'종목명':^12} | {'코드':^8} | {'★Conviction★':^14} | {'등급':^10} | {'현재가(기준일)':^18} | {'목표가':^12} | {'상승여력':^10}")
        print("-" * 130)

        for i, result in enumerate(ranked_results, 1):
            price_date_str = get_price_date_str(result)
            upside = get_upside(result)
            upside_str = f"+{upside:.1f}%" if upside and upside > 0 else (f"{upside:.1f}%" if upside else "N/A")
            current_price_str = f"{result.current_price:,}원 {price_date_str}"
            print(
                f"{i:^4} | {result.stock_name:^12} | {result.stock_code:^8} | "
                f"{result.conviction_score:^14.1f} | {result.rating:^10} | {current_price_str:^18} | "
                f"{result.target_price:>10,}원 | {upside_str:^10}"
            )

    def print_upside_table(ranked_results, title):
        """상승여력 기준 테이블 (상승여력 강조)"""
        print(f"\n{title}")
        print("-" * 130)
        print(f"{'순위':^4} | {'종목명':^12} | {'코드':^8} | {'★상승여력★':^12} | {'현재가(기준일)':^18} | {'목표가':^12} | {'등급':^10} | {'Conviction':^10}")
        print("-" * 130)

        for i, result in enumerate(ranked_results, 1):
            price_date_str = get_price_date_str(result)
            upside = get_upside(result)
            upside_str = f"+{upside:.1f}%" if upside and upside > 0 else (f"{upside:.1f}%" if upside else "N/A")
            current_price_str = f"{result.current_price:,}원 {price_date_str}"
            print(
                f"{i:^4} | {result.stock_name:^12} | {result.stock_code:^8} | "
                f"{upside_str:^12} | {current_price_str:^18} | "
                f"{result.target_price:>10,}원 | {result.rating:^10} | {result.conviction_score:^10.1f}"
            )

    # 상승여력 양수인 종목만 필터링 (매수 매력 있는 종목)
    positive_upside_results = [r for r in results if get_upside(r) is not None and get_upside(r) > 0]

    if not positive_upside_results:
        print("\n⚠️ 상승여력이 양수인 종목이 없습니다.")
        return results

    print(f"\n📌 분석 대상: {len(results)}개 중 상승여력 양수 {len(positive_upside_results)}개 종목")

    # 1. Conviction Score 기준 정렬 (상승여력 양수만)
    by_conviction = sorted(positive_upside_results, key=lambda x: x.conviction_score, reverse=True)
    print_conviction_table(by_conviction, f"📊 [1] Conviction Score 기준 (멀티팩터) - {len(positive_upside_results)}개 종목")

    # 2. 상승여력 기준 정렬 (상승여력 양수만)
    by_upside = sorted(positive_upside_results, key=lambda x: get_upside(x), reverse=True)
    print_upside_table(by_upside, f"\n📈 [2] 상승여력 기준 - {len(by_upside)}개 종목")

    if save:
        report_path = orchestrator.save_screening_report(results)
        print(f"\n📁 스크리닝 보고서 저장: {report_path}")

    return results


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="종목 선정 에이전트 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  %(prog)s --stock 005930                    # 삼성전자 분석
  %(prog)s --stock 005930 000660 035420      # 여러 종목 분석
  %(prog)s --screening --top 10              # 상위 10개 스크리닝
  %(prog)s --stock 005930 --no-save          # 저장 없이 분석

환경 변수:
  DART_API_KEY    DART API 키 (재무 분석용)
  OUTPUT_DIR      출력 디렉토리 (기본: output)
        """
    )

    parser.add_argument(
        "--stock", "-s",
        nargs="+",
        help="분석할 종목코드 (예: 005930)"
    )
    parser.add_argument(
        "--screening",
        action="store_true",
        help="전체 스크리닝 실행"
    )
    parser.add_argument(
        "--top", "-t",
        type=int,
        default=10,
        help="스크리닝 상위 종목 수 (기본: 10)"
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="출력 디렉토리 (기본: output)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="보고서 저장 안함"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 로그 출력"
    )

    args = parser.parse_args()

    # 환경 변수 로드
    load_dotenv()

    # 로깅 설정
    setup_logging(args.verbose)

    # 오케스트레이터 설정
    config = OrchestratorConfig(
        dart_api_key=os.getenv("DART_API_KEY"),
        output_dir=args.output
    )

    # DART API 키 확인
    if not config.dart_api_key:
        print("⚠️  DART_API_KEY가 설정되지 않았습니다.")
        print("   재무제표 분석이 제한됩니다.")
        print("   API 키 발급: https://opendart.fss.or.kr")
        print()

    # 오케스트레이터 초기화
    orchestrator = MasterOrchestrator(config)

    print("\n" + "=" * 60)
    print("🚀 종목 선정 에이전트 시스템 v1.0")
    print("=" * 60)

    save = not args.no_save

    if args.stock:
        analyze_stocks(orchestrator, args.stock, save)
    elif args.screening:
        run_screening(orchestrator, args.top, save)
    else:
        # 기본: 삼성전자 분석
        print("\n💡 사용법: python run_analysis.py --help")
        print("\n📌 기본 예시: 삼성전자 (005930) 분석\n")
        analyze_stocks(orchestrator, ["005930"], save)


if __name__ == "__main__":
    main()
