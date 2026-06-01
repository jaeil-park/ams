"""
AMS Backend — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router

# ─── Logging ─────────────────────────────────────
# print() 디버깅 금지 → logging 사용 (claude_rule.md §4)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Lifespan ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 이벤트"""
    logger.info("🚀 AMS Backend starting up...")
    yield
    logger.info("🛑 AMS Backend shutting down...")


# ─── FastAPI App ─────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="IT 납품 장비 이력관리 · 파트재고 · 고객사/프로젝트 통합 관리 시스템",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────
# 운영 환경에서 FRONTEND_URL 도메인만 허용 (claude_rule.md §9)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Router ──────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ─── Health Check ────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """서비스 헬스체크"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
