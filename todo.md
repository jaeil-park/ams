# AMS — TODO & 진행 이력

> **업데이트 규칙**: 작업 완료 시 `[ ]` → `[x]`로 변경하고, 하단에 완료일시 기록  
> **작업 중**: `[ ]` 앞에 `🔧` 추가  
> **블로킹**: `[ ]` 앞에 `🚫` 추가 (이유 옆에 기재)

---

## 📊 전체 진행률

| Phase | 내용 | 진행률 |
|---|---|---|
| Phase 0 | 환경 세팅 | ✅ 100% |
| Phase 1 | 백엔드 코어 | ✅ 100% |
| Phase 2 | 프론트엔드 코어 | ✅ 100% |
| Phase 3 | 도메인 기능 구현 | ✅ 100% |
| Phase 4 | 통합 연동 | ✅ 100% |
| Phase 5 | Docker & 배포 | 🔧 80% |

---

## Phase 0 — 프로젝트 환경 세팅

### 0-1. 모노레포 구조 초기화
- [x] `ams/` 루트 디렉토리 생성
- [x] `frontend/`, `backend/`, `infra/` 하위 디렉토리 생성
- [x] 루트 `.gitignore` 작성 (`.env`, `node_modules`, `__pycache__`, `*.pyc`)
- [x] `README.md` 초안 작성
- [x] Git 초기화 + 첫 커밋

### 0-2. Frontend 환경
- [x] `npm create vue@latest frontend` (Vue3 + TypeScript + Router + Pinia 선택)
- [x] Tailwind CSS v3 설치 및 설정
- [x] `tailwind.config.ts` — AMS 커스텀 색상 토큰 등록
- [x] `src/assets/styles/main.css` — Tailwind directives + 글로벌 스타일
- [x] @lucide/vue 설치 (lucide-vue-next deprecated → @lucide/vue 교체)
- [x] Axios 설치 + `src/utils/api.ts` Axios 인스턴스 구성 (baseURL, 인터셉터)
- [x] VueUse 설치
- [x] 절대경로 alias 설정 (`@/` → `src/`)
- [x] Vite proxy 설정 (개발 환경 API 프록시)

### 0-3. Backend 환경
- [x] Python 가상환경 생성 (`python -m venv .venv`) — Python 3.14.3
- [x] `requirements.txt` 작성 및 패키지 설치
- [x] `FastAPI`, `SQLAlchemy 2.0`, `Alembic`, `asyncpg` 포함
- [x] `app/core/config.py` — pydantic-settings 기반 환경변수 관리
- [x] `app/db/session.py` — async_sessionmaker 설정
- [x] `app/db/base.py` — DeclarativeBase + 공통 컬럼 (created_at, updated_at)
- [x] `alembic.ini` + `alembic/env.py` async 설정
- [x] `main.py` — FastAPI 앱 초기화 + CORS 설정

### 0-4. 개발 DB 세팅
- [x] `docker-compose.yml` — PostgreSQL 15 + pgAdmin 서비스 정의
- [x] DB 컨테이너 실행 확인
- [x] Alembic 첫 마이그레이션 실행 (`alembic upgrade head`)
- [x] `.env.example` 작성

---

## Phase 1 — 백엔드 코어

### 1-1. 데이터베이스 모델 (models/)
- [x] `models/user.py` — User (id, email, password_hash, name, role, is_active) (✅ 2026-05-29)
- [x] `models/customer.py` — Customer (code, name, biz_no, manager, phone, status) (✅ 2026-05-29)
- [x] `models/address.py` — Address (customer_id, location, address, memo) (✅ 2026-05-29)
- [x] `models/project.py` — Project (po_number, name, customer_id, manager, phone, status, location, scheduled_date) (✅ 2026-05-29)
- [x] `models/server_inventory.py` — ServerInventory (serial_tag, category, model, vendor, status, project_id, in_date, host_name, service_ip, mgmt_ip, cpu_model, cpu_core, mem_capacity, mem_gen, mem_qty, disk1_spec, disk1_qty, disk1_raid, disk2_spec, disk2_qty, disk2_raid, nic1, nic2, bios_ver, idrac_ver, raid_ver, address_id, history) (✅ 2026-05-29)
- [x] `models/part_inventory.py` — PartInventory (category, model, qty, status, location, purchase_date, warranty_end, project_id) (✅ 2026-05-29)
- [x] `models/part_usage.py` — PartUsage (part_id, used_date, customer_id, location, reason, qty) (✅ 2026-05-29)
- [x] `models/warranty.py` — Warranty (server_id, start_date, end_date, source, last_synced) (✅ 2026-05-29)
- [x] `models/audit_log.py` — AuditLog (user_id, action, resource_type, resource_id, before, after) (✅ 2026-05-29)
- [x] `models/approval.py` — Approval (requester_id, approver_id, resource_type, resource_id, status, reason) (✅ 2026-05-29)
- [x] 전체 모델 `alembic revision --autogenerate -m "initial_schema"` + 검토 + `alembic upgrade head` (✅ 2026-05-29)

### 1-2. 인증 (Auth)
- [x] `app/core/security.py` — JWT 생성/검증 함수 (✅ 2026-05-29)
- [x] `app/core/deps.py` — `get_current_user`, `get_db`, `require_admin` Depends 함수 (✅ 2026-05-29)
- [x] `app/api/v1/endpoints/auth.py` (✅ 2026-05-29)
  - [x] `POST /auth/login` — 이메일/비밀번호 로그인 → Access + Refresh Token 반환
  - [x] `POST /auth/refresh` — Refresh Token으로 Access Token 갱신
  - [x] `POST /auth/logout` — 로그아웃 (클라이언트 토큰 삭제)
  - [x] `GET  /auth/me` — 현재 사용자 정보 조회
- [x] 초기 ADMIN 사용자 seed 스크립트 작성 (`scripts/init_user.py`) (✅ 2026-05-29)

### 1-3. CRUD 기반 클래스
- [x] `crud/base.py` — CRUDBase 제네릭 클래스 (get, get_multi, create, update, remove) (✅ 2026-05-29)
- [x] `crud/crud_customer.py` (✅ 2026-05-29)
- [x] `crud/crud_project.py` (✅ 2026-05-29)
- [x] `crud/crud_inventory.py` (server + part 분기) (✅ 2026-05-29)
- [x] `crud/crud_part.py` (✅ 2026-05-29)
- [x] `crud/crud_address.py` (✅ 2026-05-29)

### 1-4. API 엔드포인트 — 고객사
- [x] `GET    /api/v1/customers` — 목록 (검색/페이지네이션) (✅ 2026-05-29)
- [x] `GET    /api/v1/customers/{id}` (✅ 2026-05-29)
- [x] `POST   /api/v1/customers` (✅ 2026-05-29)
- [x] `PATCH  /api/v1/customers/{id}` (✅ 2026-05-29)
- [x] `DELETE /api/v1/customers/{id}` (soft delete) (✅ 2026-05-29)

### 1-5. API 엔드포인트 — 프로젝트
- [x] `GET    /api/v1/projects` — 목록 (status, customer_id 필터) (✅ 2026-05-29)
- [x] `GET    /api/v1/projects/{id}` — 납품품목(서버+파트) + 주소 포함 상세 (✅ 2026-05-29)
- [x] `POST   /api/v1/projects` (✅ 2026-05-29)
- [x] `PATCH  /api/v1/projects/{id}` (✅ 2026-05-29)
- [x] `DELETE /api/v1/projects/{id}` (soft delete) (✅ 2026-05-29)

### 1-6. API 엔드포인트 — 납품목록(재고)
- [x] `GET    /api/v1/inventory` — 목록 (category, status, location, search 필터) (✅ 2026-05-29)
- [x] `GET    /api/v1/inventory/{id}` (✅ 2026-05-29)
- [x] `POST   /api/v1/inventory` — 단건 입고 등록 (✅ 2026-05-29)
- [x] `POST   /api/v1/inventory/bulk` — 동일사양 다건 입고 복사 (✅ 2026-05-29)
- [x] `PATCH  /api/v1/inventory/{id}` (✅ 2026-05-29)
- [x] `DELETE /api/v1/inventory/{id}` (soft delete) (✅ 2026-05-29)

### 1-7. API 엔드포인트 — 파트재고
- [x] `GET    /api/v1/parts` — 목록 (category 필터) (✅ 2026-05-29)
- [x] `GET    /api/v1/parts/{id}` — 사용내역(PartUsage) 포함 상세 (✅ 2026-05-29)
- [x] `POST   /api/v1/parts` (✅ 2026-05-29)
- [x] `POST   /api/v1/parts/{id}/usage` — 사용내역 등록 (✅ 2026-05-29)
- [x] `PATCH  /api/v1/parts/{id}/qty` — 수량 수정 (ADMIN 승인 요청) (✅ 2026-05-29)
- [x] `GET    /api/v1/approvals` — 승인 대기 목록 (ADMIN only) (✅ 2026-05-29)
- [x] `POST   /api/v1/approvals/{id}/approve` — 승인 (ADMIN only) (✅ 2026-05-29)
- [x] `POST   /api/v1/approvals/{id}/reject` — 반려 (ADMIN only) (✅ 2026-05-29)

### 1-8. API 엔드포인트 — 납품주소
- [x] `GET    /api/v1/addresses` — 고객사별 목록 (✅ 2026-05-29)
- [x] `POST   /api/v1/addresses` (✅ 2026-05-29)
- [x] `PATCH  /api/v1/addresses/{id}` (✅ 2026-05-29)
- [x] `DELETE /api/v1/addresses/{id}` (✅ 2026-05-29)

### 1-9. API 엔드포인트 — Dell Warranty
- [x] `services/dell_warranty.py` — Dell TechDirect API 연동 서비스 (✅ 2026-05-29)
- [x] `GET    /api/v1/warranty/{serial_no}` — S/N으로 Warranty 조회 (✅ 2026-05-29)
- [x] `POST   /api/v1/warranty/sync/{inventory_id}` — 특정 서버 Warranty 강제 동기화 (✅ 2026-05-29)

### 1-10. 대시보드 API
- [x] `GET    /api/v1/dashboard/kpi` — 입고수/납품예정/프로젝트수/납품완료수 (✅ 2026-05-29)
- [x] `GET    /api/v1/dashboard/customer-delivery` — 고객사별 상태별 납품 현황 (✅ 2026-05-29)
- [x] `GET    /api/v1/dashboard/parts-summary` — 파트재고 도넛 데이터 (✅ 2026-05-29)

---

## Phase 2 — 프론트엔드 코어

### 2-1. 공통 컴포넌트
- [x] `AppLayout.vue` — 사이드바(240px) + 헤더(55px) + 콘텐츠 영역 레이아웃 (✅ 2026-05-29)
- [x] `AppSidebar.vue` — MAIN 7개 + OPS 4개 네비게이션 + 활성 상태 + 배지 (✅ 2026-05-29)
- [x] `AppHeader.vue` — breadcrumb + 전역검색 + SYS OK + 사용자 아바타 (✅ 2026-05-29)
- [x] `AppBadge.vue` — status prop → 자동 색상 배지 (STATUS 정의 기반) (✅ 2026-05-29)
- [x] `AppTable.vue` — 컬럼 정의 + 정렬 + 로딩 스켈레톤 + 빈 상태 (✅ 2026-05-29)
- [x] `AppModal.vue` — 기본 모달 래퍼 (Teleport to body) (✅ 2026-05-29)
- [x] `AppButton.vue` — primary/secondary/ghost variant + loading 상태 (✅ 2026-05-29)
- [x] `AppSearch.vue` — debounce(300ms) 검색 인풋 (✅ 2026-05-29)
- [x] `AppPagination.vue` (✅ 2026-05-29)

### 2-2. 라우터 구성
- [x] `router/index.ts` — History 모드, 인증 Navigation Guard (✅ 2026-05-29)
- [x] 각 페이지 lazy import (code splitting) (✅ 2026-05-29)
- [x] 비인증 접근 시 `/login` 리다이렉트 (✅ 2026-05-29)

### 2-3. 인증 Store + 페이지
- [x] `stores/auth.ts` — 로그인/로그아웃/토큰 관리 (localStorage) (✅ 2026-05-29)
- [x] `LoginPage.vue` — 이메일/비밀번호 폼 (✅ 2026-05-29)
- [x] Axios 인터셉터 — 401 시 자동 토큰 갱신 or 로그인 이동 (✅ 2026-05-29)

### 2-4. UI Store
- [x] `stores/ui.ts` — 사이드바 접힘/열림, 전역 toast 알림 (✅ 2026-05-29)
- [x] Toast 알림 컴포넌트 (success/error/warning) (✅ 2026-05-29)

---

## Phase 3 — 도메인 기능 구현

### 3-1. 대시보드
- [x] `DashboardPage.vue` (✅ 2026-05-29)
- [x] KPI 카드 4개 (입고/납품예정/프로젝트진행/납품완료) — 클릭 시 해당 페이지 필터 이동 (✅ 2026-05-29)
- [x] 고객사별 납품 현황 스택바 차트 (Vanilla SVG/CSS 기반 완벽 구현) (✅ 2026-05-29)
- [x] 납품이력 최근 5건 리스트 (✅ 2026-05-29)
- [x] 파트재고 도넛차트 + 범례 (Vanilla SVG/CSS 기반 완벽 구현) (✅ 2026-05-29)

### 3-2. 고객사 관리
- [x] 신규 등록 / 수정 모달 및 Soft Delete (✅ 2026-05-29)
- [x] 상태 토글 (활성/비활성) (✅ 2026-05-29)

### 3-3. 프로젝트 관리
- [x] `ProjectsPage.vue` — 마스터 행 리스트 (접힘/펼침 toggle) (✅ 2026-05-29)
- [x] 펼침 시: 납품 품목 (서버 목록 + 파트 목록) + 주소 섹션 노출 (✅ 2026-05-29)
- [x] 서버 `상세정보` 버튼 → 납품이력 페이지 해당 프로젝트 필터 이동 (✅ 2026-05-29)
- [x] 파트 `상세정보` 버튼 → 파트재고 페이지 연결 (✅ 2026-05-29)
- [x] 프로젝트 등록 모달 (Location 클릭 → 주소 선택) (✅ 2026-05-29)
- [x] `ProjectItemsPanel.vue` — 확장 패널 컴포넌트 (✅ 2026-05-29)

### 3-4. 납품목록 (서버 인벤토리)
- [x] `InventoryPage.vue` (✅ 2026-05-29)
- [x] KPI 2개 (가용재고 / 예약) (✅ 2026-05-29)
- [x] 테이블 (입고날짜/시리얼태그/구분/모델/Status) + 필터 (CAT/LOC) (✅ 2026-05-29)
- [x] 시리얼태그 클릭 → `category` 분기 → ServerDetailModal or PartDetailModal (✅ 2026-05-29)
- [x] `ServerDetailModal.vue` (✅ 2026-05-29)
  - [x] 담당자/연락처/프로젝트명/호스트명 (✅ 2026-05-29)
  - [x] Warranty (Dell API 자동 조회 버튼 + 자동 표시) (✅ 2026-05-29)
  - [x] IP정보 (서비스/MGMT) (✅ 2026-05-29)
  - [x] 모델명 / S/N / CPU / MEM / DISK1·2 / NIC1·2 / Firmware / 주소 (✅ 2026-05-29)
  - [x] HISTORY 섹션 (텍스트 에리어) (✅ 2026-05-29)
  - [x] 프로젝트 선택 → 담당자/연락처/주소 자동 입력 (✅ 2026-05-29)
- [x] `PartDetailModal.vue` (✅ 2026-05-29)
  - [x] 담당자/연락처/프로젝트명/구분 (✅ 2026-05-29)
  - [x] Warranty = 구매일 + 1년 자동 계산 표시 (✅ 2026-05-29)
  - [x] 파트명/수량/주소 (✅ 2026-05-29)
  - [x] HISTORY (추가 장착 시리얼 목록) (✅ 2026-05-29)
- [x] 입고 등록 모달 (단건 + 동일사양 복사) (✅ 2026-05-29)
- [x] `BarcodeScanner.vue` — 카메라 스캔 -> 시리얼태그 자동 입력 (✅ 2026-05-29)

### 3-5. 파트재고
- [x] `PartsPage.vue` (✅ 2026-05-29)
- [x] 테이블 (구분/품목/수량/상태/위치) (✅ 2026-05-29)
- [x] 품목 클릭 → `PartHistoryModal.vue` (✅ 2026-05-29)
  - [x] 현재 수량 + 수정 버튼 (ADMIN role만 활성화) (✅ 2026-05-29)
  - [x] 수량 수정 시 → 승인 요청 API 호출 → "승인 대기" 표시 (✅ 2026-05-29)
  - [x] 사용 내역 테이블 (사용날짜/고객사/Location/사유) (✅ 2026-05-29)
- [x] 파트 등록 모달 (✅ 2026-05-29)

### 3-6. 납품이력
- [x] `DeliveriesPage.vue` (✅ 2026-05-29)
- [x] KPI 4개 (가용재고/예약/납품완료/RMA) (✅ 2026-05-29)
- [x] 테이블 (납품완료날짜/시리얼태그/구분/모델/Status/Warranty/IN DATE/ACT) (✅ 2026-05-29)
- [x] 시리얼태그 클릭 → ServerDetailModal / PartDetailModal (✅ 2026-05-29)
- [x] 바코드 스캔 버튼 + 입고 등록 (✅ 2026-05-29)

### 3-7. 납품주소
- [x] `AddressesPage.vue` (✅ 2026-05-29)
- [x] 테이블 (고객사/Location/주소/납품건수/최근납품일/지도 버튼) (✅ 2026-05-29)
- [x] 주소 등록/수정 모달 (✅ 2026-05-29)
- [x] 지도 버튼 → 카카오맵/네이버지도 주소 검색 팝업 (선택) (✅ 2026-05-29)

---

## Phase 4 — 통합 연동 및 고급 기능

### 4-1. Warranty 수기 등록
- [x] `services/dell_warranty.py` Dell API 연동 → 수기 등록 방식으로 변경 (✅ 2026-06-01)
- [x] 서버 상세 팝업 — 시작일/종료일 직접 입력 폼 + 저장/삭제 버튼 (✅ 2026-06-01)
- [x] `PUT /api/v1/warranty/server/{id}` — 수기 Upsert 엔드포인트 (✅ 2026-06-01)
- [x] 워런티 만료 D-30일 이내 시 badge amber 강조, 만료 시 red 표시 (✅ 2026-06-01)

### 4-2. Admin 승인 워크플로우
- [x] 파트 수량 수정 → Approval 레코드 생성 (PENDING) (✅ 2026-06-01)
- [x] 헤더 알림 아이콘에 승인 대기 건수 표시 (✅ 2026-06-01)
- [x] ADMIN 전용 승인 처리 페이지 — `ApprovalsPage.vue` (✅ 2026-06-01)
- [x] 승인/반려 후 수량 자동 반영 + AuditLog 기록 (✅ 2026-06-01)

### 4-3. 감사로그 (AuditLog)
- [x] 모든 CUD(Create/Update/Delete) 작업 시 자동 로그 기록 — Customer/Server/Project (✅ 2026-06-01)
- [x] `services/audit.py` 공통 유틸 함수 (✅ 2026-06-01)
- [x] 감사로그 조회 페이지 (ADMIN only) — `AuditLogsPage.vue` (✅ 2026-06-01)
- [x] `GET /api/v1/audit-logs` — 필터: 자원타입/Action/날짜범위 (✅ 2026-06-01)

### 4-4. 전역 검색
- [x] `GET /api/v1/search?q=` — S/N, 고객사명, 납품번호, 모델명 통합 검색 (✅ 2026-06-01)
- [x] 헤더 검색바 → 결과 드롭다운 (카테고리별 그룹핑) (✅ 2026-06-01)

### 4-5. 바코드 스캔
- [x] `BarcodeScanner.vue` — `getUserMedia` + `jsQR` 라이브러리 (✅ 2026-06-01)
- [x] 스캔 결과 → 시리얼태그 필드 자동 입력 (✅ 2026-06-01)
- [x] 미지원 브라우저 fallback (수동 입력) (✅ 2026-06-01)

---

## Phase 5 — Docker & 배포

### 5-1. Dockerfile 작성
- [x] `frontend/Dockerfile` — Node 빌드 + Nginx 서빙 (multi-stage) (✅ 2026-06-01)
- [x] `backend/Dockerfile` — Python slim + uvicorn (✅ 2026-06-01)

### 5-2. Docker Compose
- [x] `infra/docker-compose.yml` — 개발 환경 (hot reload) (✅ 2026-06-01)
- [x] `infra/docker-compose.prod.yml` — 운영 환경 (볼륨 마운트, 재시작 정책) (✅ 2026-06-01)
  - [x] services: frontend, backend, db (PostgreSQL)
  - [x] volumes: postgres_data → Synology NAS 마운트 경로 (`/volume1/docker/portainer/`)

### 5-3. Nginx 설정
- [x] `frontend/nginx.conf` — Nginx를 프론트 컨테이너 내부로 통합하여 복잡성 해결 (✅ 2026-06-01)
  - [x] `/` → frontend (Vue3 빌드 정적파일)
  - [x] `/api/` → backend (FastAPI)
  - [x] gzip 압축, 캐시 헤더 설정 완료

### 5-4. Makefile 자동화
- [x] `Makefile` 작성 완료 (dev, build, push, prod, migrate, seed 등 명령 완비) (✅ 2026-06-01)

### 5-5. Portainer Stack 배포 가이드 제공
- [ ] Synology NAS Private Registry 이미지 등록 확인
- [ ] Portainer Stack YAML 작성 (docker-compose.prod.yml 기반)
- [ ] Nginx Proxy Manager — 도메인/SSL 설정
- [ ] 초기 DB seed 실행 (ADMIN 계정 + 기초 데이터)
- [ ] 서비스 헬스체크 확인

---

## 📝 완료 이력

| 날짜 | Phase | 내용 | 담당 |
|---|---|---|---|
| - | - | - | - |

---

## 🚫 블로킹 이슈

| 번호 | 내용 | 해결 방법 | 상태 |
|---|---|---|---|
| - | - | - | - |

---

## 💡 추후 고려 사항 (백로그)

- [ ] RMA 페이지 구현
- [ ] 리포트 페이지 (PDF 출력, 엑셀 다운로드)
- [ ] 다국어(i18n) 지원 (영문 UI)
- [ ] 이메일 알림 (Warranty 만료 D-30 자동 알림)
- [ ] 모바일 반응형 최적화
- [ ] 프론트엔드 테스트 (Vitest + Vue Test Utils)
- [ ] 백엔드 테스트 (pytest + httpx TestClient)
- [ ] CI/CD 파이프라인 (GitHub Actions)
- [ ] 카카오/네이버맵 주소 검색 연동
