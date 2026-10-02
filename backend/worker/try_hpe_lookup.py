"""
worker/try_hpe_lookup.py — HPE 자동 조회 단독 시험 (DB 불필요, 배포 전 PC 에서 확인용)

사용법 (backend 폴더에서, 조회 전용 HPE 계정 정보를 환경변수로 넣고 실행):
  set HPE_USERNAME=조회전용계정@회사
  set HPE_PASSWORD=********
  set HPE_HEADLESS=false              # 브라우저 화면을 보면서 확인하려면
  set HPE_STATE_PATH=.hpe_state.json
  python -m worker.try_hpe_lookup SGHD45FLRB CN703816MW

비밀번호는 명령줄 인자나 파일에 남기지 말고 환경변수로만 넣을 것.
"""

import asyncio
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused:unused@localhost:5432/unused")

from app.services.hpe_portal import HpeLoginRequired, HpePortalClient  # noqa: E402


async def main(serials: list[str]) -> None:
    client = HpePortalClient()
    await client.start()
    try:
        await client.ensure_login()
        for s in serials:
            r = await client.lookup(s)
            print(f"{s}: {r.get('status')} {r.get('start_date')} ~ {r.get('end_date')} "
                  f"[{r.get('service_level')}] {r.get('product_name') or ''} {r.get('error') or ''}")
    except HpeLoginRequired as e:
        print("로그인 필요:", e)
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python -m worker.try_hpe_lookup <시리얼> [시리얼 ...]")
        sys.exit(1)
    asyncio.run(main(sys.argv[1:]))
