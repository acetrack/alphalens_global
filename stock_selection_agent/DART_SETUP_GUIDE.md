# DART API 연동 가이드

## ✅ 환경 변수 설정 확인

DART API 키가 이미 환경 변수로 설정되어 있습니다:

```bash
echo $DART_API_KEY
# 출력: b99849c69fd14f5a71a659b82cc20855005f23ec
```

## 🚀 sentiment_agent에서 자동으로 사용됨

### 자동 초기화
sentiment_agent는 환경 변수에서 자동으로 DART API 키를 읽어서 초기화합니다:

```python
from src.agents import SentimentAgent

# DART API 키가 환경 변수에 있으면 자동으로 DART 클라이언트 초기화됨
agent = SentimentAgent()

# 공시 데이터는 자동으로 DART에서 가져옴
result = agent.analyze("005930")
```

### 수동 초기화 (선택사항)
필요시 DartClient를 직접 전달할 수도 있습니다:

```python
from src.agents import SentimentAgent
from src.api import DartClient

dart_client = DartClient(api_key="your_key")
agent = SentimentAgent(dart_client=dart_client)
```

## 📋 공시 데이터 수집 과정

### 1. 종목코드 → corp_code 변환
```python
# 내부적으로 자동 변환
stock_code = "005930"  # 삼성전자
corp_code = dart_client.get_corp_code_by_stock_code(stock_code)
# → "00126380"
```

### 2. DART API 공시 조회
```python
# 최근 90일 공시 조회
disclosures = dart_client.get_disclosure_list(
    corp_code=corp_code,
    bgn_de="20240101",
    end_de="20240331",
    page_count=100
)
```

### 3. 공시 센티먼트 분석
수집된 공시의 제목을 분석하여 긍정/부정 분류:

**긍정 공시 키워드:**
- 자기주식 취득
- 배당 결정
- 대규모 수주
- 신사업 진출
- 실적 개선

**부정 공시 키워드:**
- 유상증자
- CB/BW 발행
- 소송 제기
- 손실 발생
- 감자

## 🧪 테스트

### 기본 테스트
```bash
cd stock_selection_agent
python3 test_sentiment_agent.py
```

### DART API 직접 테스트
```python
from src.api import DartClient

# 초기화 (환경 변수에서 자동으로 API 키 로드)
dart = DartClient()

# 삼성전자 corp_code 조회
corp_code = dart.get_corp_code_by_stock_code("005930")
print(f"삼성전자 corp_code: {corp_code}")

# 공시 목록 조회
disclosures = dart.get_disclosure_list(
    corp_code=corp_code,
    bgn_de="20260101",
    end_de="20260202"
)

print(f"공시 건수: {len(disclosures.get('list', []))}")
for item in disclosures.get('list', [])[:5]:
    print(f"- {item['rcept_dt']}: {item['report_nm']}")
```

## 📊 출력 예시

```python
result = agent.analyze("005930")

# 공시 센티먼트 확인
print(f"총 공시: {result.total_disclosures}건")
print(f"긍정 공시: {result.positive_disclosures}건")
print(f"부정 공시: {result.negative_disclosures}건")
print(f"순 센티먼트: {result.net_disclosure_sentiment:+d}")

# 주요 공시 이벤트
for event in result.material_events:
    print(f"[{event['date']}] {event['title']}")
```

## ⚙️ 설정

### 공시 수집 기간 변경
```python
from src.agents import SentimentAgent, SentimentAnalysisConfig

config = SentimentAnalysisConfig(
    disclosure_lookback_days=60  # 기본값 90일에서 60일로 변경
)

agent = SentimentAgent(config=config)
```

## ⚠️ 주의사항

### 1. API 호출 제한
- DART API는 일일 **10,000회** 호출 제한
- sentiment_agent는 종목당 1~2회 호출 (효율적)

### 2. corp_code 캐시
- 첫 실행 시 전체 기업 목록 다운로드 (약 1분)
- 이후 캐시 파일 사용 (`~/.dart_cache/corp_code_mapping.json`)
- 캐시는 자동으로 관리됨

### 3. Fallback 처리
DART API 호출 실패 시 자동으로 Mock 데이터 사용:
```
[WARNING] DART 공시 수집 실패: timeout
[INFO] Mock 데이터를 사용합니다.
```

## 🔧 문제 해결

### "DART API 키가 필요합니다" 오류

환경 변수 확인:
```bash
echo $DART_API_KEY
```

없으면 설정:
```bash
export DART_API_KEY="b99849c69fd14f5a71a659b82cc20855005f23ec"

# 영구 설정 (~/.zshrc 또는 ~/.bashrc)
echo 'export DART_API_KEY="b99849c69fd14f5a71a659b82cc20855005f23ec"' >> ~/.zshrc
source ~/.zshrc
```

### "corp_code를 찾을 수 없습니다" 오류

캐시 삭제 후 재시도:
```bash
rm -rf ~/.dart_cache
python3 test_sentiment_agent.py
```

### API 응답 느림

정상입니다. 첫 실행 시 corp_code 매핑 다운로드에 시간이 걸립니다:
- 첫 실행: 약 1분
- 이후 실행: 1초 이내

## 📈 성능

| 작업 | 첫 실행 | 캐시 사용 |
|------|---------|----------|
| corp_code 로드 | ~60초 | <1초 |
| 공시 조회 (1종목) | ~2초 | ~2초 |
| 전체 센티먼트 분석 | ~5초 | ~5초 |

## 🎯 다음 단계

### Option A: 실적 데이터 연동
현재는 Mock 데이터만 사용합니다. 향후 추가 예정:
1. DART에서 실제 실적 (Actual) 수집
2. 네이버 금융에서 컨센서스 (Estimate) 크롤링
3. 실적 서프라이즈 계산 (Actual vs Estimate)

### Option B: 공시 분류 고도화
현재는 키워드 기반 간단한 분류입니다. 향후:
1. LLM 기반 공시 내용 분석
2. 공시 유형별 세분화 분류
3. 공시 중요도 가중치 적용

## ✅ 현재 상태

| 데이터 소스 | 상태 | 비고 |
|-----------|------|------|
| 뉴스 (네이버) | ✅ 완료 | 웹 크롤링 |
| 뉴스 (구글) | ✅ 완료 | RSS 피드 |
| 애널리스트 | ✅ 완료 | 네이버 크롤링 |
| **공시 (DART)** | **✅ 완료** | **API 연동** |
| 실적 | ⚠️ Mock | 향후 구현 |

DART API 연동이 완료되어 **실제 공시 데이터**를 사용합니다! 🎉
