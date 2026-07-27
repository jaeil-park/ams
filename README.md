# AMS — Asset Management System

> IT 납품 장비 이력관리, 파트재고, 고객사·프로젝트 통합 관리 시스템 (이제누리)

---

## 기술 스택

| Layer | Stack |
|---|---|
| **Frontend** | Vue 3 (Composition API) · Vite · Tailwind CSS v3 · Pinia · Vue Router 4 |
| **Backend** | Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · PostgreSQL 15 |
| **Infra** | Docker · Docker Compose · GitHub Actions (GHCR 빌드/배포) · Portainer |

---

## 주요 기능

| 메뉴 | 설명 |
|---|---|
| 대시보드 | 서버 재고·프로젝트 현황·최근 입고 이력 요약 |
| 고객사 관리 | 고객사 기본정보 + 담당자(복수) 등록/관리 |
| 프로젝트 관리 | PO 단위 납품 프로젝트, 고객사 담당자 선택 시 연락처/이메일 자동 입력 |
| 납품목록 (서버) | 서버 단건/동일사양 대량 복사 입고, CPU·MEM·DISK 1·2 상세 사양, 비고 |
| 파트재고 | 부품 재고 및 프로젝트 할당, 수량 변경은 승인 관리를 통해 반영 |
| 납품이력 / 납품주소 | 납품 완료 이력 조회, 고객사별 배송 거점 관리 |
| 승인 관리 | 수량 변경 등 민감 변경 요청의 ADMIN 승인/반려 |
| 사용자 관리 (Admin) | 계정 생성/수정/비활성화/삭제 (자기 자신 잠금 방지) |
| 감사 로그 (Admin) | 모든 등록/수정/삭제 이력 필드 단위 추적 |
| 사용 설명서 | `/manual.html` — 별도 정적 페이지, 사이드바 Admin 섹션에서 링크 |

---

## 로컬 개발 가이드

### 사전 요구사항

- Python 3.12+
- Node.js 20+
- Docker Desktop

### 1. DB 실행

```bash
docker compose -f infra/docker-compose.yml up -d
```

PostgreSQL(`localhost:5432`)과 pgAdmin(`http://localhost:5050`, `admin@ams.dev` / `admin`)이 함께 뜹니다.

### 2. Backend 실행

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8080
```

> 포트는 반드시 **8080**으로 실행하세요. `frontend/vite.config.ts`의 `/api` 프록시가 `http://localhost:8080`을 바라보도록 고정되어 있습니다. (Docker 배포 시에는 컨테이너 내부 포트가 8000이며, 로컬 개발 포트와는 별개입니다 — `backend/Dockerfile` 참고.)

### 3. Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

### 접속 URL (로컬 개발)

| 서비스 | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8080 (프론트에서는 `/api/v1` 프록시로 접근) |
| API Docs (Swagger) | http://localhost:8080/docs |
| 사용 설명서 | http://localhost:5173/manual.html |
| pgAdmin | http://localhost:5050 |

---

## 버전 관리 & 배포

`VERSION` 파일(레포 루트)이 릴리즈 버전의 단일 소스입니다.

- `main` 브랜치에 푸시되면 GitHub Actions(`.github/workflows/deploy.yml`)가 `VERSION` 값을 읽어 백엔드/프론트엔드 Docker 이미지를 빌드하고, `ghcr.io`에 **`:latest`**, **`:v<VERSION>`**, **`:<commit-sha>`** 세 태그로 푸시합니다.
- 같은 버전 값이 빌드 시 `APP_VERSION` 빌드 인자로 두 이미지에 주입되어, 실행 중인 컨테이너의 `/health` 응답과 로그인 화면·사이드바 하단에 실제 배포 버전이 그대로 표시됩니다.
- `infra/docker-compose.prod.yml`의 이미지 태그는 `${TAG:-latest}`를 사용합니다 — 특정 버전을 고정 배포하거나 롤백하려면 `infra/.env.prod`에 `TAG=v1.0.3`처럼 지정하세요 (기본값은 `latest`).

### 릴리즈 절차

1. `VERSION` 파일을 다음 버전(`1.0.1`, `1.0.2`, …)으로 올리고 커밋
2. `main`에 푸시 → GitHub Actions가 자동으로 이미지 빌드/푸시 (Actions 탭에서 진행 확인)
3. Portainer → Stacks → `ams` → **Update the stack**(`Re-pull image and redeploy` 켠 상태)로 재배포
4. 이번 릴리즈에 새 DB 마이그레이션이 포함되어 있다면, `ams-backend` 컨테이너 콘솔에서 반드시 실행:
   ```bash
   alembic upgrade head
   ```
   (컨테이너 시작 시 마이그레이션이 자동 실행되지 않으므로 수동 실행 필수)

---

## 디렉토리 구조

```
ams/
├── frontend/                 # Vue3 + Vite SPA
│   ├── public/manual.html    # 사용 설명서 (정적 페이지)
│   └── src/
├── backend/                  # FastAPI + SQLAlchemy
│   └── alembic/versions/     # DB 마이그레이션
├── infra/                    # Docker Compose, Nginx 설정
├── .github/workflows/        # CI (GHCR 빌드/배포)
├── VERSION                   # 릴리즈 버전 단일 소스
├── claude_rule.md            # AI 코딩 어시스턴트 규칙
├── project.md                 # 프로젝트 구현 계획
├── todo.md                   # 작업 진행 이력
└── README.md
```

---

## 환경 변수

`.env.example` 파일을 참고하여 `backend/.env` 파일을 생성하세요.

```bash
cp .env.example backend/.env
```

운영 배포용 환경 변수는 `infra/.env.prod.example`을 복사해 `infra/.env.prod`로 작성합니다 (`.gitignore`에 포함되어 있어 커밋되지 않습니다).

---

## 라이선스

Private — Internal Use Only
