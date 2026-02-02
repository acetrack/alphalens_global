"""
eBest API 응답 데이터 확인
"""
import logging
import json
from src.api.ebest_client import EbestClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("eBest API 응답 데이터 확인")
print("=" * 80)

try:
    client = EbestClient()
    
    # _request 메서드를 직접 호출해서 원시 응답 확인
    params = {"gicode": "001200"}
    result = client._request("t3320", params)
    
    print(f"\n응답 타입: {type(result)}")
    print(f"응답 데이터:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    client.close()
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
