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
    # 키가 없으면 Dell 조회는 WAITING_EXTENSION 으로 대기하고 브라우저 확장 프로그램이 처리한다
    DELL_API_CLIENT_ID: str = ""
    DELL_API_CLIENT_SECRET: str = ""
    DELL_API_TOKEN_URL: str = "https://apigtwb2c.us.dell.com/auth/oauth/v2/token"
    DELL_API_WARRANTY_URL: str = "https://apigtwb2c.us.dell.com/PROD/sbil/eapi/v5/asset-entitlements"

    # ─── 워런티 조회 ──────────────────────────────
    WARRANTY_LOOKUP_MAX: int = 200          # 한 번에 요청할 수 있는 최대 시리얼 수
    WARRANTY_WORKER_STALE_SEC: int = 180    # 작업자 응답이 이 시간 이상 없으면 '중지'로 표시

    # ─── HPE 자동 조회 (warranty-worker 컨테이너 전용) ───
    # 조회 전용 HPE 계정. 서버 환경변수로만 넣는다 (.env 커밋 금지)
    HPE_USERNAME: str = ""
    HPE_PASSWORD: str = ""
    HPE_STATE_PATH: str = "/data/hpe_state.json"   # 로그인 세션 보관 (볼륨 마운트)
    HPE_HEADLESS: bool = True
    HPE_LOOKUP_DELAY_SEC: float = 4.0              # 조회 사이 간격 (HPE 포털 부하 배려)
    HPE_POLL_SEC: float = 10.0                     # 대기열 확인 주기
    HPE_LOGIN_RETRY_SEC: float = 600.0             # 로그인 실패 후 재시도 간격


settings = Settings()
