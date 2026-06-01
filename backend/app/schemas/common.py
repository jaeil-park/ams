"""
app/schemas/common.py — 공통 API 응답 및 에러 스키마
"""

from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class MetaSchema(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int


class ResponseEnvelope(BaseModel, Generic[T]):
    """Standard API Response Envelope"""
    data: T
    meta: MetaSchema | None = None


class ErrorEnvelope(BaseModel):
    """Standard API Error Response"""
    code: str
    message: str
