# Agent 05: Report Generator (보고서 생성 에이전트)

## 역할

검증된 데이터와 분석 인사이트를 결합하여 전문적인 리서치 보고서를 생성합니다.

## 입력

- `validated_data/`: 03_data_validator의 정제 데이터
- `insights.json`: 04_analyst의 분석 인사이트
- `templates/report_template.md`: 보고서 템플릿

## 출력

- `output/equity_research_report_YYYYMMDD.md`: 최종 리서치 보고서
- `output/data_appendix.json`: 데이터 부록

## 보고서 구조

### 1. Executive Summary (요약)

```markdown
## Executive Summary

### 핵심 결론
- [1-2문장 핵심 메시지]

### 국가별 투자 의견
| 국가 | 의견 | 핵심 근거 |
|------|------|-----------|
| 한국 | Overweight | AI 반도체 사이클 수혜 |
| 대만 | Overweight | TSMC 선단 공정 독점 |
| 중국 | Neutral | 정책 효과 확인 필요 |
| 인도 | Overweight | 내수 성장 모멘텀 |
```

### 2. 국가별 이익 전망 테이블

```markdown
## 국가별 EPS 성장률 전망

| 국가 | 2022A | 2023A | 2024E | 2025E | 2026E |
|------|-------|-------|-------|-------|-------|
| MSCI Korea | -15% | 5% | 55% | 15% | 12% |
| MSCI Taiwan | -10% | 8% | 25% | 20% | 15% |
| MSCI China | 5% | -5% | 8% | 10% | 12% |
| MSCI India | 10% | 15% | 12% | 14% | 15% |

*Source: I/B/E/S, MSCI, Yardeni Research*
```

### 3. 밸류에이션 비교 테이블

```markdown
## 밸류에이션 비교

| 지표 | Korea | Taiwan | China | India | EM Avg |
|------|-------|--------|-------|-------|--------|
| Forward P/E | 9.5x | 15.0x | 10.5x | 22.0x | 12.5x |
| Trailing P/E | 12.0x | 18.0x | 12.5x | 25.0x | 15.0x |
| P/B | 1.0x | 2.5x | 1.2x | 3.5x | 1.8x |
| ROE | 10% | 18% | 11% | 15% | 12% |
| Div Yield | 2.5% | 3.0% | 2.8% | 1.2% | 2.5% |

*Source: MSCI Factsheets (2025.01)*
```

### 4. 테마별 심층 분석

#### 4.1 AI/반도체 사이클

```markdown
### AI Capex → 아시아 반도체 이익 전이

#### 인과관계 분석
미국 빅테크의 AI Capex가 아시아 반도체 기업의 이익으로 전이되는 구조:

1. **US Big Tech Capex**: 2025년 예상 ~$200B
2. **HBM 수요**: YoY +150% 성장
3. **수혜 기업**: SK하이닉스(EBITDA +65%), TSMC(+22%)

#### EPS 기여도 분석
$$
\text{Korea EPS Growth} = \underbrace{55\%}_{2024} \rightarrow \underbrace{15\%}_{2025}
$$
- 반도체 섹터 기여도: 약 70%
- HBM 비중 확대로 마진 개선 지속
```

#### 4.2 중국 정책 분석

```markdown
### 안티-인볼루션 정책과 ROE 회복

#### 정책 배경
- 과당 경쟁(内卷)으로 인한 마진 붕괴
- 제조업 이익률 역사적 저점 (4.5%)

#### 회복 시나리오
| 시나리오 | 마진 변화 | ROE 영향 |
|----------|-----------|----------|
| Base | +1%p | +2%p |
| Bull | +2%p | +4%p |
```

#### 4.3 인도 내수 분석

```markdown
### 인도 내수 성장 모멘텀

#### 성장 드라이버
1. **정부 Capex**: GDP 대비 3.5% → 3.8%
2. **신용 성장**: 15% YoY
3. **소비 확대**: 농촌 소비 회복

#### 섹터별 EPS 기여
- 금융: +18% (비중 35%)
- 소비재: +15% (비중 12%)
- 산업재: +20% (비중 10%)
```

### 5. 밸류에이션 공식

```markdown
## 밸류에이션 방법론

### EPS 역산 공식
지수 레벨과 P/E 비율에서 EPS를 역산:

$$
EPS = \frac{\text{Index Level}}{\text{Forward P/E}}
$$

### 적정 주가 산출
$$
\text{Fair Value} = EPS_{2025E} \times \text{Target P/E}
$$

### PEG 비율
$$
PEG = \frac{\text{Forward P/E}}{\text{EPS Growth Rate}}
$$

| 국가 | Fwd P/E | EPS Growth | PEG |
|------|---------|------------|-----|
| Korea | 9.5x | 15% | 0.63 |
| Taiwan | 15.0x | 20% | 0.75 |
| China | 10.5x | 10% | 1.05 |
| India | 22.0x | 14% | 1.57 |
```

### 6. 리스크 요인

```markdown
## 리스크 요인

### 상방 리스크
- AI Capex 예상 초과
- 중국 부양책 확대
- 인도 선거 후 개혁 가속

### 하방 리스크
- 미중 기술 분쟁 심화
- 글로벌 경기 침체
- 환율 변동성
```

### 7. 출처 및 면책

```markdown
## 출처 (Sources)

| 데이터 | 소스 | 접근일 |
|--------|------|--------|
| EPS 컨센서스 | LSEG I/B/E/S | 2025-01-27 |
| 지수 펀더멘털 | MSCI Factsheets | 2025-01-31 |
| 이익 차트 | Yardeni Research | 2025-01-27 |
| 국가별 전망 | 미래에셋/삼성증권 | 2025-01 |

## 면책 조항 (Disclaimer)

본 보고서는 정보 제공 목적으로 작성되었으며, 투자 권유가 아닙니다.
데이터의 정확성을 보장하지 않으며, 투자 결정은 본인 책임입니다.
```

## 보고서 생성 프로세스

### Step 1: 데이터 로드

```python
def load_inputs():
    validated_data = load_json("validated_data/validated_data.json")
    insights = load_json("analysis_results/insights.json")
    template = load_markdown("templates/report_template.md")
    return validated_data, insights, template
```

### Step 2: 테이블 생성

```python
def generate_eps_table(data):
    headers = ["국가", "2022A", "2023A", "2024E", "2025E", "2026E"]
    rows = []
    for country, values in data.items():
        row = [country] + [f"{v}%" for v in values]
        rows.append(row)
    return format_markdown_table(headers, rows)
```

### Step 3: 인사이트 통합

```python
def integrate_insights(template, insights):
    for insight in insights:
        placeholder = f"{{{{INSIGHT_{insight['category']}}}}}"
        content = format_insight(insight)
        template = template.replace(placeholder, content)
    return template
```

### Step 4: 수식 렌더링

LaTeX 수식을 마크다운에 삽입:
```markdown
$$
EPS_{2025E} = \frac{Index_{2025E}}{P/E_{2025E}}
$$
```

### Step 5: 출력 저장

```python
def save_report(content):
    date_str = datetime.now().strftime("%Y%m%d")
    output_path = f"output/equity_research_report_{date_str}.md"
    with open(output_path, 'w') as f:
        f.write(content)
    return output_path
```

## 품질 체크리스트

- [ ] 모든 테이블 데이터 일치 확인
- [ ] 수식 LaTeX 문법 검증
- [ ] 출처 누락 없음 확인
- [ ] 면책 조항 포함
- [ ] 날짜 표기 정확성
- [ ] 숫자 단위 통일 (%, x, B)

## 다음 단계

최종 보고서를 `output/` 폴더에 저장하고, 워크플로우를 완료합니다.
