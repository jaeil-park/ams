from typing import Optional
from pydantic import BaseModel, EmailStr

# 공통 속성
class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = "USER"
    is_active: bool = True

# 생성 스키마
class UserCreate(UserBase):
    password: str

# 수정 스키마
class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

# 응답 스키마
class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True
