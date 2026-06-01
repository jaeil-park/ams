"""
app/services/dell_warranty.py — Dell TechDirect API 연동 서비스 Mock/Stub
- 실제 Dell TechDirect Client Credential 토큰 교환 및 S/N 정보 fetch를 모방합니다.
- 실제 운영 키가 발급되면 비동기 httpx 클라이언트로 API를 호출합니다.
"""

from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


class DellWarrantyService:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def fetch_warranty_by_serial(self, serial_tag: str) -> dict | None:
        """
        주어진 S/N(시리얼 태그)을 기준으로 Dell Warranty 정보를 비동기로 조회합니다.
        (현재는 Dev Mock API 모드로 동작하여 가상의 정상 보증 데이터를 즉시 생성 및 반환합니다.)
        """
        logger.info(f"Dell API Warranty fetch 시도: S/N={serial_tag}")
        
        # 실제 키가 있는 경우의 가상 API 호출
        if self.client_id and self.client_secret:
            logger.info("Dell TechDirect API Key 감지됨. 비동기 HTTP 호출 연동 준비")
            # TODO: httpx.AsyncClient를 이용한 실제 Dell API 호출 추가
        
        # Mock/Stub 데이터 반환 (비즈니스 로직 §2: 시리얼 태그 입력 시 보증기간 자동 세팅)
        # 3년 보증 기간 생성
        start_dt = date.today() - timedelta(days=120)
        end_dt = start_dt + timedelta(days=365 * 3)
        
        return {
            "serial_tag": serial_tag,
            "start_date": start_dt,
            "end_date": end_dt,
            "source": "DELL",
        }
