# Expert Equity Research Analyst Agent System

## 개요

글로벌 투자 은행 수준의 주식 리서치 분석을 자동화하는 멀티 에이전트 시스템입니다. 블룸버그(Bloomberg)와 같은 고가의 터미널 데이터 없이 공신력 있는 무료/저비용 소스를 활용하여 국가별 이익 증감률 데이터를 추출하고, 매크로 분석과 결합한 전문적인 리서치 보고서를 생성합니다.

## 페르소나

> 글로벌 투자 은행의 수석 주식 애널리스트이자 퀀트 리서처

## 핵심 목표

1. **EPS 성장률 파악**: MSCI Korea, Taiwan, India, China 등 주요 국가 지수의 연도별(2024~2026) 이익 성장률 및 EBITDA 전망치
2. **상관관계 분석**: AI Capex, 공급망 재편, 정책적 변화와 이익 간의 인과관계 분석
3. **데이터 역산**: 데이터 부재 시 지수 레벨과 선행 P/E를 활용한 EPS 역산

## 프로젝트 구조

```
equity_research_agent/
├── README.md                          # 프로젝트 개요
├── config/
│   └── workflow.yaml                  # 워크플로우 설정
├── agents/
│   ├── 01_data_identifier/            # 1단계: 데이터 식별 에이전트
│   │   └── INSTRUCTIONS.md
│   ├── 02_data_collector/             # 2단계: 데이터 수집 에이전트
│   │   ├── INSTRUCTIONS.md
│   │   └── sources/                   # 데이터 소스별 가이드
│   │       ├── lseg_ibes.md
│   │       ├── msci_factsheets.md
│   │       ├── yardeni_research.md
│   │       └── brokerage_reports.md
│   ├── 03_data_validator/             # 3단계: 데이터 검증 에이전트
│   │   └── INSTRUCTIONS.md
│   ├── 04_analyst/                    # 4단계: 분석 에이전트
│   │   └── INSTRUCTIONS.md
│   └── 05_report_generator/           # 5단계: 보고서 생성 에이전트
│       └── INSTRUCTIONS.md
├── templates/
│   └── report_template.md             # 보고서 템플릿
└── output/                            # 생성된 보고서 저장
```

## 에이전트 워크플로우

```
┌─────────────────────┐
│  01_data_identifier │  ← 핵심 지표 정의 (EPS, EBITDA, ROE, P/E)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  02_data_collector  │  ← 멀티소스 데이터 수집
│    ├── LSEG I/B/E/S │
│    ├── MSCI         │
│    ├── Yardeni      │
│    └── 증권사 리서치  │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  03_data_validator  │  ← 데이터 일관성 검증 & 정제
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│    04_analyst       │  ← 파생 인사이트 도출
│    ├── AI 사이클     │
│    ├── 정책 요인     │
│    └── 내수 모멘텀   │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 05_report_generator │  ← 최종 보고서 생성
└─────────────────────┘
```

## 실행 방법

### 1. 전체 워크플로우 실행

```bash
# 워크플로우 설정 확인
cat config/workflow.yaml

# 각 에이전트 순차 실행
for agent in agents/*/; do
    echo "Running: $agent"
    # 에이전트별 INSTRUCTIONS.md를 기반으로 작업 수행
done
```

### 2. 개별 에이전트 실행

특정 에이전트만 실행하려면 해당 폴더의 `INSTRUCTIONS.md`를 참조하여 작업을 수행합니다.

```bash
# 예시: 데이터 식별 에이전트 실행
cat agents/01_data_identifier/INSTRUCTIONS.md
```

## 출력 형식

- **표 형식**: 국가별 2021~2026년 이익 증감률 비교 테이블
- **수식**: LaTeX 형식의 밸류에이션 및 EPS 역산 수식
- **인용**: 모든 데이터의 출처 명시 (Refinitiv, MSCI, I/B/E/S 등)

## 라이선스

Internal Use Only
