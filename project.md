# AMS — Project Implementation Plan
> Asset Management System v1.0.0  
> 작성일: 2026-05-29 | 담당: 양재혁 (OPS LEAD)

---

## 1. 프로젝트 목표

AMS는 IT 납품 장비의 **입고~납품~폐기** 전 생애주기를 추적하고, 파트재고·고객사·프로젝트를 통합 관리하는 사내 웹 ERP입니다.

### 핵심 목표
- 시리얼 단위 서버 자산 이력 100% 추적 (Dell/HPE/Brocade 등)
- 파트재고(DISK/NIC/HBA/Gbic 등) 수량 실시간 관리 + Admin 승인 워크플로우
- Dell TechDirect API 연동으로 Warranty 자동 조회/갱신
- 프로젝트(PO) 기반 납품 품목 구조화 관리
- Portainer 기반 Synology NAS/Proxmox 온프레미스 자체 운영

---

## 2. 아키텍처 개요

```
┌─────────────────────────────────────────────────────────┐
│                      사용자 브라우저                         │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────────┐
│              Nginx Proxy Manager (NPM)                   │
│         /          →  frontend (Vue3 SPA)               │
│         /api/      →  backend (FastAPI)                  │
└─────────────────────┬───────────────────────────────────┘
          ┌───────────┴──────────┐
          ▼                      ▼
┌──────────────────┐   ┌──────────────────────────┐
│  Frontend        │   │  Backend                  │
│  Vue3 + Vite     │   │  FastAPI + Uvicorn        │
│  Tailwind CSS    │   │  SQLAlchemy 2.0 (async)   │
│  Pinia           │   │  Alembic                  │
│  (Nginx 서빙)     │   │  python-jose (JWT)        │
└──────────────────┘   └──────────┬───────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  PostgreSQL 15       │
                        │  (Synology NAS 볼륨) │
                        └─────────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Dell TechDirect API │
                        │  (외부 Warranty 조회)│
                        └─────────────────────┘

[ 컨테이너 오케스트레이션: Portainer + Docker Compose ]
[ 이미지 레지스트리: Synology NAS Private Registry    ]
```

---

## 3. 데이터베이스 스키마

### 3-1. 핵심 테이블 정의

#### users
```sql
id            SERIAL PRIMARY KEY
email         VARCHAR(255) UNIQUE NOT NULL
password_hash VARCHAR(255) NOT NULL
name          VARCHAR(100) NOT NULL
role          VARCHAR(20) NOT NULL DEFAULT 'USER'  -- USER | ADMIN
is_active     BOOLEAN DEFAULT TRUE
created_at    TIMESTAMPTZ DEFAULT now()
updated_at    TIMESTAMPTZ DEFAULT now()
```

#### customers (고객사)
```sql
id            SERIAL PRIMARY KEY
code          VARCHAR(20) UNIQUE NOT NULL      -- C2024-001
name          VARCHAR(100) NOT NULL
biz_no        VARCHAR(20)                      -- 사업자번호
manager       VARCHAR(50)
phone         VARCHAR(30)
status        VARCHAR(20) DEFAULT 'ACTIVE'     -- ACTIVE | INACTIVE
memo          TEXT
is_deleted    BOOLEAN DEFAULT FALSE
created_at    TIMESTAMPTZ DEFAULT now()
updated_at    TIMESTAMPTZ DEFAULT now()
```

#### addresses (납품주소)
```sql
id            SERIAL PRIMARY KEY
customer_id   INTEGER REFERENCES customers(id) NOT NULL
location      VARCHAR(100) NOT NULL            -- PIDC, LGCNS 본사 등
address       VARCHAR(255) NOT NULL
memo          TEXT
is_deleted    BOOLEAN DEFAULT FALSE
created_at    TIMESTAMPTZ DEFAULT now()
updated_at    TIMESTAMPTZ DEFAULT now()
```

#### projects (프로젝트)
```sql
id              SERIAL PRIMARY KEY
po_number       VARCHAR(50) NOT NULL           -- PO1234
name            VARCHAR(200) NOT NULL
customer_id     INTEGER REFERENCES customers(id)
manager         VARCHAR(50)                    -- 담당자 (프로젝트 참조)
phone           VARCHAR(30)                    -- 연락처
address_id      INTEGER REFERENCES addresses(id)
status          VARCHAR(30) DEFAULT 'SCHEDULED'
  -- SCHEDULED | IN_PROGRESS | WAITING | COMPLETED | CANCELLED
location        VARCHAR(100)
scheduled_date  DATE
completed_date  DATE
memo            TEXT
is_deleted      BOOLEAN DEFAULT FALSE
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()
```

#### server_inventories (납품목록 — 서버)
```sql
id              SERIAL PRIMARY KEY
serial_tag      VARCHAR(50) UNIQUE NOT NULL    -- SN-DR75-2411001
category        VARCHAR(10) NOT NULL DEFAULT 'SERVER'
vendor          VARCHAR(50)                    -- Dell | HPE | Brocade 등
model           VARCHAR(100)                   -- PowerEdge R750
status          VARCHAR(20) DEFAULT 'IN_STOCK'
  -- IN_STOCK | RESERVED | SCHEDULED | DELIVERED | RMA
in_date         DATE NOT NULL                  -- 입고날짜
project_id      INTEGER REFERENCES projects(id)
address_id      INTEGER REFERENCES addresses(id)
-- 상세 스펙
host_name       VARCHAR(100)
service_ip      INET
mgmt_ip         INET
cpu_model       VARCHAR(100)
cpu_core        VARCHAR(50)                    -- "24C × 2"
mem_capacity    VARCHAR(50)                    -- "384GB"
mem_gen         VARCHAR(50)                    -- "DDR5/4800"
mem_qty         VARCHAR(50)                    -- "12 × 32GB"
disk1_spec      VARCHAR(100)
disk1_qty_raid  VARCHAR(50)                    -- "6 × RAID5"
disk2_spec      VARCHAR(100)
disk2_qty_raid  VARCHAR(50)
nic1            VARCHAR(100)
nic2            VARCHAR(100)
firmware_bios   VARCHAR(50)
firmware_idrac  VARCHAR(50)
firmware_raid   VARCHAR(50)
history         TEXT                           -- 특이사항, 요청사항
is_deleted      BOOLEAN DEFAULT FALSE
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()
-- 인덱스
INDEX ON status
INDEX ON in_date
INDEX ON project_id
INDEX ON serial_tag
```

#### warranties (워런티)
```sql
id              SERIAL PRIMARY KEY
server_id       INTEGER REFERENCES server_inventories(id) UNIQUE
start_date      DATE
end_date        DATE
source          VARCHAR(20) DEFAULT 'DELL_API' -- DELL_API | MANUAL
last_synced     TIMESTAMPTZ
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()
```

#### part_inventories (파트재고)
```sql
id              SERIAL PRIMARY KEY
category        VARCHAR(20) NOT NULL           -- DISK | NIC | HBA | Gbic | RAM
model           VARCHAR(150) NOT NULL
qty             INTEGER NOT NULL DEFAULT 0
status          VARCHAR(20) DEFAULT 'IN_STOCK'
location        VARCHAR(100)                   -- 본사창고-A
purchase_date   DATE
warranty_end    DATE                           -- 구매일 + 1년 자동
project_id      INTEGER REFERENCES projects(id)
memo            TEXT
is_deleted      BOOLEAN DEFAULT FALSE
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()
INDEX ON category
INDEX ON status
```

#### part_usages (파트 사용내역)
```sql
id              SERIAL PRIMARY KEY
part_id         INTEGER REFERENCES part_inventories(id) NOT NULL
used_date       DATE NOT NULL
customer_id     INTEGER REFERENCES customers(id)
location        VARCHAR(100)
reason          VARCHAR(300)                   -- PowerEdge R760 [1EJFN] Bay1 장애로 1EA 사용
qty             INTEGER NOT NULL DEFAULT 1
used_by         INTEGER REFERENCES users(id)
created_at      TIMESTAMPTZ DEFAULT now()
```

#### approvals (파트 수량 Admin 승인)
```sql
id              SERIAL PRIMARY KEY
requester_id    INTEGER REFERENCES users(id)
approver_id     INTEGER REFERENCES users(id)
resource_type   VARCHAR(30) DEFAULT 'PART_QTY'
resource_id     INTEGER                        -- part_inventories.id
before_qty      INTEGER
after_qty       INTEGER
reason          TEXT
status          VARCHAR(20) DEFAULT 'PENDING'  -- PENDING | APPROVED | REJECTED
processed_at    TIMESTAMPTZ
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()
```

#### audit_logs (감사로그)
```sql
id              SERIAL PRIMARY KEY
user_id         INTEGER REFERENCES users(id)
action          VARCHAR(20)                    -- CREATE | UPDATE | DELETE
resource_type   VARCHAR(50)                    -- server_inventory | project 등
resource_id     INTEGER
before_data     JSONB
after_data      JSONB
ip_address      INET
created_at      TIMESTAMPTZ DEFAULT now()
INDEX ON resource_type, resource_id
INDEX ON user_id
INDEX ON created_at DESC
```

---

### 3-2. ERD 관계 요약

```
customers ──< addresses         (1:N)
customers ──< projects          (1:N)
projects  ──< server_inventories (1:N, project_id nullable)
projects  ──< part_inventories  (1:N, project_id nullable)
server_inventories ──|| warranties (1:1)
part_inventories ──< part_usages (1:N)
part_inventories ──< approvals  (1:N)
users ──< approvals (requester, 1:N)
users ──< audit_logs (1:N)
```

---

## 4. API 엔드포인트 전체 목록

### Auth
| Method | Path | 설명 | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/login` | 로그인 | ❌ |
| POST | `/api/v1/auth/refresh` | 토큰 갱신 | ❌ |
| POST | `/api/v1/auth/logout` | 로그아웃 | ✅ |
| GET  | `/api/v1/auth/me` | 내 정보 | ✅ |

### Customers
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/customers` | 목록 (search, status) | ✅ |
| GET    | `/api/v1/customers/{id}` | 상세 | ✅ |
| POST   | `/api/v1/customers` | 생성 | ✅ |
| PATCH  | `/api/v1/customers/{id}` | 수정 | ✅ |
| DELETE | `/api/v1/customers/{id}` | 삭제(soft) | ✅ |

### Projects
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/projects` | 목록 (status, customer_id) | ✅ |
| GET    | `/api/v1/projects/{id}` | 상세 + 납품품목 + 주소 | ✅ |
| POST   | `/api/v1/projects` | 생성 | ✅ |
| PATCH  | `/api/v1/projects/{id}` | 수정 | ✅ |
| DELETE | `/api/v1/projects/{id}` | 삭제(soft) | ✅ |

### Inventory (납품목록/재고)
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/inventory` | 목록 (category, status, location, project_id, search) | ✅ |
| GET    | `/api/v1/inventory/{id}` | 상세 (warranty 포함) | ✅ |
| POST   | `/api/v1/inventory` | 단건 입고 | ✅ |
| POST   | `/api/v1/inventory/bulk` | 동일사양 다건 복사 입고 | ✅ |
| PATCH  | `/api/v1/inventory/{id}` | 수정 | ✅ |
| DELETE | `/api/v1/inventory/{id}` | 삭제(soft) | ✅ |

### Parts (파트재고)
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/parts` | 목록 (category) | ✅ |
| GET    | `/api/v1/parts/{id}` | 상세 + 사용내역 | ✅ |
| POST   | `/api/v1/parts` | 파트 등록 | ✅ |
| PATCH  | `/api/v1/parts/{id}` | 기본 정보 수정 | ✅ |
| POST   | `/api/v1/parts/{id}/usage` | 사용내역 등록 | ✅ |
| POST   | `/api/v1/parts/{id}/qty-request` | 수량 수정 요청 (Admin 승인) | ✅ |
| DELETE | `/api/v1/parts/{id}` | 삭제(soft) | ✅ |

### Approvals (Admin 승인)
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/approvals` | 대기 목록 | ADMIN |
| POST   | `/api/v1/approvals/{id}/approve` | 승인 | ADMIN |
| POST   | `/api/v1/approvals/{id}/reject` | 반려 | ADMIN |

### Addresses (납품주소)
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/addresses` | 목록 (customer_id) | ✅ |
| POST   | `/api/v1/addresses` | 생성 | ✅ |
| PATCH  | `/api/v1/addresses/{id}` | 수정 | ✅ |
| DELETE | `/api/v1/addresses/{id}` | 삭제 | ✅ |

### Warranty
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/warranty/{serial_no}` | Dell API 조회 | ✅ |
| POST   | `/api/v1/warranty/sync/{inventory_id}` | 강제 동기화 + 저장 | ✅ |

### Dashboard
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/dashboard/kpi` | 4종 KPI 수치 | ✅ |
| GET    | `/api/v1/dashboard/customer-delivery` | 고객사별 상태별 현황 | ✅ |
| GET    | `/api/v1/dashboard/parts-summary` | 파트재고 카테고리별 합계 | ✅ |

### Search
| Method | Path | 설명 | Auth |
|---|---|---|---|
| GET    | `/api/v1/search?q=` | 통합 검색 (S/N, 고객사, 모델, PO) | ✅ |

---

## 5. 페이지별 컴포넌트 구조

### 5-1. DashboardPage
```
DashboardPage
├── KpiCard × 4           (입고/납품예정/프로젝트/납품완료, 클릭 → 라우터 이동)
├── CustomerDeliveryChart (ECharts 스택바, 고객사별 × 상태별)
├── RecentDeliveriesTable (최근 5건 납품이력)
└── PartsSummaryDonut     (파트재고 도넛 + 범례)
```

### 5-2. ProjectsPage
```
ProjectsPage
├── ToolBar               (총 N건, + 프로젝트 등록, 전체 펼치기)
├── ProjectMasterRow × N  (▶/▼ toggle)
│   └── ProjectItemsPanel (펼침 시)
│       ├── ServerItemList (서버 목록, 상세정보 버튼)
│       ├── PartItemList   (파트 목록, 상세정보 버튼)
│       └── AddressSection (주소 표시)
└── ProjectFormModal      (등록/수정)
```

### 5-3. InventoryPage
```
InventoryPage
├── KpiRow               (가용재고 / 예약)
├── ToolBar              (검색, CAT필터, LOC필터, + 입고 등록, 바코드 스캔)
├── InventoryTable       (시리얼태그 클릭 → 모달 분기)
│   ├── ServerDetailModal   (category === 'SERVER')
│   └── PartDetailModal     (category === 'PART')
├── InventoryFormModal   (단건 입고)
├── BulkCopyModal        (동일사양 복사 입고)
└── BarcodeScanner       (카메라 스캔)
```

### 5-4. PartsPage
```
PartsPage
├── ToolBar              (총 N카테고리, 승인대기 배지, + 파트 등록)
├── PartsTable           (품목 클릭 → History 팝업)
│   └── PartHistoryModal
│       ├── CurrentQtyPanel  (현재 수량, 수정 버튼 [ADMIN only])
│       └── UsageHistoryTable
└── PartFormModal
```

---

## 6. 상태(Status) 전환 흐름

### 서버 인벤토리 상태 흐름
```
입고 등록
    │
    ▼
IN_STOCK ──────────────────────► RESERVED (프로젝트 배정)
    │                                  │
    │                                  ▼
    │                           SCHEDULED (납품예정)
    │                                  │
    │                                  ▼
    │                           DELIVERED (납품완료)
    │
    └──────────────────────────► RMA (장애 반환)
                                       │
                                       ▼
                                   IN_STOCK (수리 후 복귀)
```

### 프로젝트 상태 흐름
```
SCHEDULED → IN_PROGRESS → COMPLETED
              │
              ▼
           WAITING
              │
              ▼
          IN_PROGRESS
```

### 파트 수량 수정 흐름
```
사용자 수정 요청
    │
    ▼
APPROVAL 생성 (PENDING)
    │
    ├── ADMIN 승인 → qty 자동 갱신 + 감사로그
    └── ADMIN 반려 → qty 변경 없음 + 사유 기록
```

---

## 7. 핵심 비즈니스 로직 구현 상세

### 7-1. 프로젝트 선택 시 자동 입력
```ts
// composables/useProjectAutoFill.ts
watch(selectedProjectId, async (id) => {
  if (!id) return
  const project = await projectStore.getById(id)
  form.manager = project.manager
  form.phone   = project.phone
  form.address = project.address?.address ?? ''
})
```

### 7-2. Dell Warranty 자동 조회
```python
# services/dell_warranty.py
async def fetch_warranty(serial_no: str) -> dict:
    """Dell TechDirect API OAuth2 → Warranty 조회"""
    token = await get_dell_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://apigtwb2c.us.dell.com/PROD/sbil/eapi/v5/asset-entitlements",
            params={"servicetags": serial_no},
            headers={"Authorization": f"Bearer {token}"}
        )
    data = resp.json()
    return {
        "start_date": data[0]["entitlements"][0]["startDate"],
        "end_date":   data[0]["entitlements"][0]["endDate"],
    }
```

### 7-3. 파트 워런티 자동 계산
```python
# models/part_inventory.py
from datetime import date, timedelta

@property
def warranty_end(self) -> date | None:
    if self.purchase_date:
        return self.purchase_date + timedelta(days=365)
    return None
```

### 7-4. 동일사양 복사 입고
```python
# crud/crud_inventory.py
async def bulk_copy(db: AsyncSession, base_id: int, serial_tags: list[str]):
    """같은 스펙으로 시리얼만 바꿔서 다건 등록"""
    base = await db.get(ServerInventory, base_id)
    new_items = [
        ServerInventory(
            **{k: v for k, v in base.__dict__.items()
               if k not in ('id', 'serial_tag', 'created_at', 'updated_at')},
            serial_tag=tag
        )
        for tag in serial_tags
    ]
    db.add_all(new_items)
    await db.commit()
    return new_items
```

### 7-5. 바코드 스캔
```ts
// components/domain/BarcodeScanner.vue
import jsQR from 'jsqr'

async function startScan() {
  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
  // canvas에 프레임 캡처 → jsQR.decode → emit('scanned', code)
}
```

---

## 8. 배포 구성

### docker-compose.prod.yml 핵심 서비스
```yaml
version: '3.9'
services:
  frontend:
    image: registry.local/ams-frontend:latest
    restart: always

  backend:
    image: registry.local/ams-backend:latest
    restart: always
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - DELL_API_CLIENT_ID=${DELL_API_CLIENT_ID}
      - DELL_API_CLIENT_SECRET=${DELL_API_CLIENT_SECRET}

  db:
    image: postgres:15-alpine
    restart: always
    volumes:
      - /volume1/docker/ams/postgres:/var/lib/postgresql/data  # Synology NAS 경로
    environment:
      POSTGRES_DB: ams_db
      POSTGRES_USER: ams
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
```

### Makefile
```makefile
REGISTRY=registry.local:5000
TAG=latest

build:
	docker build -t $(REGISTRY)/ams-frontend:$(TAG) ./frontend
	docker build -t $(REGISTRY)/ams-backend:$(TAG) ./backend

push:
	docker push $(REGISTRY)/ams-frontend:$(TAG)
	docker push $(REGISTRY)/ams-backend:$(TAG)

migrate:
	docker compose -f infra/docker-compose.prod.yml exec backend \
	  alembic upgrade head

prod:
	docker compose -f infra/docker-compose.prod.yml up -d

logs:
	docker compose -f infra/docker-compose.prod.yml logs -f --tail=100
```

---

## 9. 개발 일정 (참고용)

| 주차 | Phase | 목표 |
|---|---|---|
| 1주 | Phase 0 | 환경 세팅 완료, Hello World 빌드/배포 확인 |
| 2주 | Phase 1 | 백엔드 모델 + Auth + 기본 CRUD API |
| 3주 | Phase 1 | 나머지 API 엔드포인트 + Dell Warranty 연동 |
| 4주 | Phase 2 | 프론트 공통 컴포넌트 + 라우터 + Auth 흐름 |
| 5주 | Phase 3 | 대시보드 + 고객사 + 프로젝트 페이지 |
| 6주 | Phase 3 | 납품목록 + 파트재고 + 상세 팝업 2종 |
| 7주 | Phase 3 | 납품이력 + 납품주소 + 전역검색 |
| 8주 | Phase 4 | Admin 승인 + 감사로그 + 바코드 스캔 |
| 9주 | Phase 5 | Docker 빌드 + Portainer 배포 + 실사용 테스트 |
| 10주 | 안정화 | 버그 수정 + 성능 튜닝 + 문서 정리 |

---

## 10. 참고 링크

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Vue3 Composition API](https://vuejs.org/guide/extras/composition-api-faq)
- [Pinia 공식 문서](https://pinia.vuejs.org/)
- [Dell TechDirect API](https://developer.dell.com/)
- [jsQR 바코드 라이브러리](https://github.com/cozmo/jsQR)
- [Portainer 공식 문서](https://docs.portainer.io/)
