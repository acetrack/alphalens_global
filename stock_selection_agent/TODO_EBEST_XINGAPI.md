# TODO: 이베스트투자증권 xingAPI Plus 연동

## 목표
sentiment_agent에 애널리스트 데이터와 실적 데이터를 연동하여 완전한 센티먼트 분석 구현

## 현재 상태 (2026-02-02)

### 작동 중 ✅
- **뉴스 센티먼트 (60%)**: 구글 RSS 피드 - 실제 데이터 수집 중
- **공시 센티먼트 (40%)**: DART API - 실제 데이터 수집 중

### 연동 필요 ⏳
- **애널리스트 센티먼트 (35% 예정)**: 이베스트 xingAPI 연동 필요
- **실적 서프라이즈 (15% 예정)**: 이베스트 xingAPI 연동 필요

## 작업 계획

### Phase 1: 이베스트 계좌 개설 및 API 신청
- [ ] 이베스트투자증권 계좌 개설
- [ ] xingAPI Plus 신청 (https://www.ebestsec.co.kr)
- [ ] API 키 발급 대기 (1-2일 소요)
- [ ] API 문서 확인 및 테스트

### Phase 2: xingAPI 클라이언트 구현
- [ ] `src/api/ebest_client.py` 생성
- [ ] REST API 인증 구현 (OAuth2 토큰)
- [ ] 애널리스트 데이터 조회 API 연동
  - 투자의견 조회 (TR: t3320?)
  - 목표주가 조회
  - EPS 컨센서스 조회
- [ ] 실적 데이터 조회 API 연동
  - 분기별 실적 조회
  - 컨센서스 조회
- [ ] 에러 핸들링 및 fallback 처리

### Phase 3: sentiment_agent 통합
- [ ] `_fetch_analyst_data_ebest()` 메서드 구현
- [ ] `_fetch_earnings_data_ebest()` 메서드 구현
- [ ] EbestClient를 sentiment_agent에 주입
- [ ] 가중치 조정:
  - 뉴스: 60% → 30%
  - 공시: 40% → 20%
  - 애널리스트: 0% → 35%
  - 실적: 0% → 15%

### Phase 4: 테스트 및 검증
- [ ] 단위 테스트 작성
- [ ] 여러 종목에 대해 실제 데이터 수집 테스트
- [ ] 데이터 품질 검증
- [ ] 성능 테스트 (API 호출 제한 확인)

### Phase 5: 문서화
- [ ] EBEST_XINGAPI_GUIDE.md 작성
- [ ] SENTIMENT_AGENT_GUIDE.md 업데이트
- [ ] requirements.txt 업데이트 (필요시)

## 기술적 고려사항

### xingAPI Plus 특징
- **플랫폼**: REST API + WebSocket (macOS 지원 ✅)
- **인증**: OAuth2 기반
- **요청 제한**: 분당 약 200건
- **데이터 품질**: 증권사 공식 데이터로 신뢰도 높음

### 필요한 TR 코드 (예상)
```python
# 애널리스트 데이터
- t3320: 투자의견 조회
- t1764: 목표주가 조회
- t8436: EPS 컨센서스

# 실적 데이터
- t1717: 분기별 실적 조회
- t8424: 실적 컨센서스
```

### 환경 변수 설정
```bash
export EBEST_APP_KEY="PSKOFQ9K2bhCoFKnQrct1UgLKuhOz1VkEsW9"
export EBEST_APP_SECRET="JmEvPvQhO5of0Olxh879nxYPbieMrUZh"
```

## 예상 일정
- Phase 1: 3-5일 (계좌 개설 및 승인 대기)
- Phase 2-3: 2-3일 (API 클라이언트 구현 및 통합)
- Phase 4-5: 1-2일 (테스트 및 문서화)
- **총 예상 기간**: 약 1-2주

## 참고 자료
- 이베스트 xingAPI 문서: https://www.ebestsec.co.kr/apiguide
- xingAPI Plus 가이드: https://wikidocs.net/book/7845
- Python requests 라이브러리: https://docs.python-requests.org

## 진행 상황
- [ ] Phase 1 시작
- [ ] Phase 2 시작
- [ ] Phase 3 시작
- [ ] Phase 4 시작
- [ ] Phase 5 완료

---

**현재 작업 상태**: Phase 1 대기 중 (계좌 개설 필요)
**최종 업데이트**: 2026-02-02
