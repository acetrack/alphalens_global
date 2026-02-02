"""
t3341 (재무순위종합) 테스트
"""
import logging
import json
from src.api.ebest_client import EbestClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("=" * 80)
print("t3341 (재무순위종합) 테스트")
print("=" * 80)

try:
    client = EbestClient()
    
    # t3341 테스트 - 엔드포인트는 /stock/investinfo로 시도
    params = {
        "gicode": "005930",  # 삼성전자
        "gubun": "",  # 전체
    }
    
    result = client._request("t3341", params)
    
    print(f"\n응답 타입: {type(result)}")
    if result:
        print(f"응답 키: {list(result.keys())}")
        print(f"\n응답 데이터 (처음 2000자):")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
    else:
        print("응답 없음")
    
    client.close()
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
