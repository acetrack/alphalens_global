"""
eBest xingAPI 샘플 종목코드 테스트
"""
import logging
from src.api.ebest_client import EbestClient

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("eBest API 테스트 (종목코드: 001200)")
print("=" * 80)

try:
    client = EbestClient()
    print(f"✅ 인증 성공!")
    
    # 샘플 종목코드로 테스트
    print(f"\n종목코드 001200으로 애널리스트 데이터 조회...")
    analyst_data = client.get_analyst_consensus("001200")
    
    if analyst_data:
        print(f"✅ 데이터 수신 성공!")
        print(f"응답 데이터: {analyst_data}")
    else:
        print(f"⚠️ 데이터가 없습니다.")
        
    client.close()
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)
