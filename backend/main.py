"""
AMS Backend — FastAPI Application Entry Point
"""

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.api.v1.router import api_router
from app.services.system_log import record_system_log

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


# ─── 전역 예외 핸들러 (system_logs 자동 기록) ─────────
# 정상적인 비즈니스 검증 실패(400/401/403)는 노이즈이므로 기록 대상에서 제외되고
# (app/services/system_log.py 참고), 라우트/스키마 불일치를 나타내는 404·422와
# 모든 5xx만 system_logs 테이블에 남는다.

@app.exception_handler(StarletteHTTPException)
async def logged_http_exception_handler(request: Request, exc: StarletteHTTPException):
    await record_system_log(request, status_code=exc.status_code, message=str(exc.detail))
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def logged_validation_exception_handler(request: Request, exc: RequestValidationError):
    await record_system_log(request, status_code=422, message=str(exc.errors()))
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(Exception)
async def logged_unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    await record_system_log(
        request,
        status_code=500,
        message=str(exc) or exc.__class__.__name__,
        detail=traceback.format_exc(),
    )
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다."})


# ─── Health Check ────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """서비스 헬스체크"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
