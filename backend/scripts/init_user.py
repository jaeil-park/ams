"""
scripts/init_user.py — 초기 ADMIN 사용자 시딩(seeding) 스크립트
"""

import asyncio
import os
import sys

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from app.db.session import async_session
from app.models.user import User
from app.core.security import get_password_hash


async def main():
    print("AMS 초기 ADMIN 사용자 생성을 시작합니다...")
    
    async with async_session() as session:
        # 이미 ADMIN 계정이 있는지 확인
        result = await session.execute(select(User).where(User.email == "admin@ams.dev"))
        admin = result.scalars().first()
        
        if admin:
            print("이미 admin@ams.dev 사용자가 존재합니다.")
            return
        
        # 새 ADMIN 계정 생성
        admin_user = User(
            email="admin@ams.dev",
            password_hash=get_password_hash("admin"),
            name="시스템 관리자",
            role="ADMIN",
            is_active=True,
        )
        
        session.add(admin_user)
        await session.commit()
        print("성공적으로 초기 ADMIN 사용자 계정을 생성했습니다!")
        print("이메일: admin@ams.dev")
        print("비밀번호: admin")


if __name__ == "__main__":
    asyncio.run(main())
