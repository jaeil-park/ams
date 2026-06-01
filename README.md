# AMS — Asset Management System

> IT 납품 장비 이력관리, 파트재고, 고객사·프로젝트 통합 관리 시스템

---

## 기술 스택

| Layer | Stack |
|---|---|
| **Frontend** | Vue 3 (Composition API) · Vite · Tailwind CSS v3 · Pinia · Vue Router 4 |
| **Backend** | Python 3.11+ · FastAPI · SQLAlchemy 2.0 (async) · Alembic · PostgreSQL 15 |
| **Infra** | Docker · Docker Compose · Nginx Proxy Manager · Portainer |

---

## 로컬 개발 가이드

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- Docker Desktop

### 1. DB 실행

```bash
docker compose -f infra/docker-compose.yml up -d
```

### 2. Backend 실행

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

### 3. Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

### 접속 URL

| 서비스 | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |

---

## 디렉토리 구조

```
ams/
├── frontend/          # Vue3 + Vite SPA
├── backend/           # FastAPI + SQLAlchemy
├── infra/             # Docker, Nginx 설정
├── claude_rule.md     # AI 코딩 어시스턴트 규칙
├── project.md         # 프로젝트 구현 계획
├── todo.md            # 작업 진행 이력
└── README.md
```

---

## 환경 변수

`.env.example` 파일을 참고하여 `.env` 파일을 생성하세요.

```bash
cp .env.example backend/.env
```

---

## 라이선스

Private — Internal Use Only
