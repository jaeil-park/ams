# ═══════════════════════════════════════════════════════════════════════════════
# AMS Makefile — 빌드 & 배포 자동화
# OS: Windows (Git Bash / WSL) 또는 Linux/macOS
#
# 사용법: make <target>
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 변수 ──────────────────────────────────────────────────────────────────────
REGISTRY       := 192.168.0.22:5000
IMAGE_FRONTEND := $(REGISTRY)/ams-frontend
IMAGE_BACKEND  := $(REGISTRY)/ams-backend
TAG            := latest

COMPOSE_DEV    := docker compose -f infra/docker-compose.yml
COMPOSE_PROD   := docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod

NAS_HOST       := 192.168.0.22
NAS_USER       := admin
BACKEND_CTR    := ams-backend

.PHONY: help dev dev-down build push prod prod-down migrate seed logs logs-backend logs-frontend logs-db ps clean

# ─── 도움말 ────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  AMS Makefile Commands"
	@echo "  ─────────────────────────────────────────────"
	@echo "  make dev            개발 환경 DB 컨테이너 시작 (PostgreSQL + pgAdmin)"
	@echo "  make dev-down       개발 환경 종료"
	@echo "  make build          프론트엔드 + 백엔드 Docker 이미지 빌드"
	@echo "  make push           빌드된 이미지를 NAS Registry에 푸시"
	@echo "  make prod           운영 환경 전체 스택 시작 (NAS 로컬 실행용)"
	@echo "  make prod-down      운영 환경 종료"
	@echo "  make migrate        DB 마이그레이션 실행 (alembic upgrade head)"
	@echo "  make seed           초기 ADMIN 계정 seed 실행"
	@echo "  make logs           모든 운영 컨테이너 로그 tail"
	@echo "  make logs-backend   백엔드 로그만 tail"
	@echo "  make logs-frontend  프론트엔드 로그만 tail"
	@echo "  make logs-db        DB 로그만 tail"
	@echo "  make ps             컨테이너 상태 확인"
	@echo "  make clean          dangling 이미지 정리"
	@echo ""

# ─── 개발 환경 ──────────────────────────────────────────────────────────────────
dev:
	@echo "▶ 개발 환경 DB 시작..."
	$(COMPOSE_DEV) up -d
	@echo "✓ PostgreSQL: localhost:5432"
	@echo "✓ pgAdmin:    http://localhost:5050  (admin@ams.dev / admin)"

dev-down:
	@echo "▶ 개발 환경 종료..."
	$(COMPOSE_DEV) down

# ─── 빌드 ──────────────────────────────────────────────────────────────────────
build: build-frontend build-backend

build-frontend:
	@echo "▶ Frontend 이미지 빌드..."
	docker build -t $(IMAGE_FRONTEND):$(TAG) ./frontend
	@echo "✓ $(IMAGE_FRONTEND):$(TAG)"

build-backend:
	@echo "▶ Backend 이미지 빌드..."
	docker build -t $(IMAGE_BACKEND):$(TAG) ./backend
	@echo "✓ $(IMAGE_BACKEND):$(TAG)"

# ─── Registry 푸시 ──────────────────────────────────────────────────────────────
push: push-frontend push-backend

push-frontend:
	@echo "▶ Frontend 이미지 푸시 → $(REGISTRY)..."
	docker push $(IMAGE_FRONTEND):$(TAG)

push-backend:
	@echo "▶ Backend 이미지 푸시 → $(REGISTRY)..."
	docker push $(IMAGE_BACKEND):$(TAG)

# ─── 운영 환경 ──────────────────────────────────────────────────────────────────
prod:
	@echo "▶ 운영 환경 시작..."
	@test -f infra/.env.prod || (echo "❌ infra/.env.prod 파일이 없습니다. infra/.env.prod.example 을 복사하여 작성하세요." && exit 1)
	$(COMPOSE_PROD) pull
	$(COMPOSE_PROD) up -d
	@echo "✓ AMS 운영 환경 시작됨: http://$(NAS_HOST)"

prod-down:
	@echo "▶ 운영 환경 종료..."
	$(COMPOSE_PROD) down

# ─── DB 마이그레이션 ───────────────────────────────────────────────────────────
migrate:
	@echo "▶ Alembic 마이그레이션 실행..."
	docker exec $(BACKEND_CTR) alembic upgrade head
	@echo "✓ 마이그레이션 완료"

# ─── 초기 Seed ─────────────────────────────────────────────────────────────────
seed:
	@echo "▶ 초기 ADMIN 계정 생성..."
	docker exec $(BACKEND_CTR) python scripts/init_user.py
	@echo "✓ seed 완료"

# ─── 로그 ──────────────────────────────────────────────────────────────────────
logs:
	$(COMPOSE_PROD) logs -f

logs-backend:
	$(COMPOSE_PROD) logs -f backend

logs-frontend:
	$(COMPOSE_PROD) logs -f frontend

logs-db:
	$(COMPOSE_PROD) logs -f db

# ─── 상태 확인 ─────────────────────────────────────────────────────────────────
ps:
	$(COMPOSE_PROD) ps

# ─── 정리 ──────────────────────────────────────────────────────────────────────
clean:
	@echo "▶ dangling 이미지 정리..."
	docker image prune -f
	@echo "✓ 정리 완료"
