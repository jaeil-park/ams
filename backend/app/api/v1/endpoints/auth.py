"""
app/api/v1/endpoints/auth.py — JWT 로그인 및 사용자 인증 엔드포인트
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core import security
from app.core.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.post("/login")
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    이메일과 비밀번호로 로그인하여 Access 및 Refresh Token을 획득합니다.
    (OAuth2 규격 준수를 위해 username 필드를 이메일로 활용합니다)
    """
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 사용자 계정입니다."
        )
        
    access_token = security.create_access_token(data={"sub": user.email})
    refresh_token = security.create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(
    refresh_token_input: str,
    db: AsyncSession = Depends(get_db),
):
    """Refresh Token으로 Access Token을 갱신합니다."""
    try:
        payload = security.jwt.decode(
            refresh_token_input, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다."
            )
    except security.jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 서명 검증 실패 또는 만료되었습니다."
        )
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없거나 비활성화되었습니다."
        )
        
    new_access_token = security.create_access_token(data={"sub": user.email})
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """현재 로그인된 사용자의 프로필 정보를 조회합니다."""
    return ResponseEnvelope(
        data={
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "role": current_user.role,
            "is_active": current_user.is_active,
        }
    )


@router.post("/logout")
async def logout():
    """로그아웃을 시도합니다. 클라이언트 측 토큰 삭제를 권장합니다."""
    return {"message": "성공적으로 로그아웃되었습니다."}
