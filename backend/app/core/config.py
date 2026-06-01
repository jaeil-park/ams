"""
app/core/config.py — 환경변수 관리 (pydantic-settings)
하드코딩 환경변수 금지 → Settings 참조 (claude_rule.md §4)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정 — .env 파일 또는 환경변수에서 로드"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── Application ─────────────────────────────
    APP_NAME: str = "AMS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ─── Database ────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://ams:ams_dev_password@localhost:5432/ams_db"

    # ─── JWT Auth ────────────────────────────────
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440   # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── CORS ────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    # ─── Dell TechDirect API ─────────────────────
    DELL_API_CLIENT_ID: str = ""
    DELL_API_CLIENT_SECRET: str = ""


settings = Settings()
