FROM python:3.12-slim

# ─── 시스템 의존성 ─────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─── Python 패키지 설치 (레이어 캐시 최적화) ────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─── 소스코드 복사 ────────────────────────────────────────────────────────────
COPY . .

EXPOSE 8000

# ─── 헬스체크 ─────────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ─── 실행 ─────────────────────────────────────────────────────────────────────
# workers 수 = (CPU 코어 수 × 2) + 1 권장, 단일 NAS에서는 2로 고정
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
