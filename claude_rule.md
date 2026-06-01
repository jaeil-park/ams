# AMS — Project Rules
> Claude Code / Cursor / Windsurf AI 코딩 어시스턴트 전용 규칙 파일  
> 이 파일을 항상 먼저 읽고 작업을 시작할 것

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **프로젝트명** | AMS (Asset Management System) |
| **목적** | IT 납품 장비 이력관리, 파트재고, 고객사·프로젝트 통합 관리 |
| **사용자** | 내부 IT 엔지니어, 자산 관리 담당자, ADMIN |
| **버전** | v1.0.0 |
| **디자인 톤** | 라이트 ERP (이카운트/SAP/더존 스타일) — 슬레이트 사이드바 + 블루 액센트 |

---

## 2. 기술 스택

### Frontend
```
Vue 3          — Composition API + <script setup lang="ts"> 필수
Vite           — 빌드 툴
Tailwind CSS   — v3, utility-first
Pinia          — 상태관리 (Vuex 사용 금지)
Vue Router 4   — History 모드
Axios          — HTTP 클라이언트 (fetch 직접 사용 금지)
Lucide Vue     — 아이콘 (다른 아이콘 라이브러리 혼용 금지)
VueUse         — 유틸리티 composables
jsQR           — 바코드 스캔
```

### Backend
```
Python 3.11+
FastAPI        — async 라우터 필수
SQLAlchemy 2.0 — async 모드 (sync 사용 금지)
Alembic        — DB 마이그레이션
PostgreSQL 15  — 운영 DB
python-jose    — JWT
passlib        — bcrypt 해싱
httpx          — Dell Warranty API 연동 (비동기)
pydantic v2    — 스키마 검증
```

### Infrastructure
```
Docker + Docker Compose
Portainer       — 컨테이너 관리
Nginx Proxy Manager — 리버스 프록시
Synology NAS    — Private Registry + 볼륨 마운트
Proxmox VE      — VM 운영 환경 (대안)
```

---

## 3. 디렉토리 구조

```
ams/
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   │   └── styles/
│   │   │       └── main.css          # Tailwind directives
│   │   ├── components/
│   │   │   ├── common/               # 재사용 공통 컴포넌트
│   │   │   │   ├── AppBadge.vue      # 상태 배지 (StatusBadge)
│   │   │   │   ├── AppButton.vue
│   │   │   │   ├── AppModal.vue      # 기본 모달 래퍼
│   │   │   │   ├── AppTable.vue      # 테이블 (정렬/페이지네이션)
│   │   │   │   ├── AppSearch.vue     # 검색 인풋
│   │   │   │   └── AppPagination.vue
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.vue     # 전체 레이아웃 (사이드바+헤더+콘텐츠)
│   │   │   │   ├── AppSidebar.vue    # 좌측 네비게이션
│   │   │   │   └── AppHeader.vue     # 상단 헤더
│   │   │   └── domain/               # 도메인별 컴포넌트
│   │   │       ├── ServerDetailModal.vue   # 서버 상세 팝업
│   │   │       ├── PartDetailModal.vue     # 파트 상세 팝업
│   │   │       ├── PartHistoryModal.vue    # 파트재고 History 팝업
│   │   │       ├── ProjectItemsPanel.vue   # 프로젝트 납품품목 확장 패널
│   │   │       └── BarcodeScanner.vue      # 바코드 스캔 모달
│   │   ├── composables/
│   │   │   ├── useInventory.ts
│   │   │   ├── useProjects.ts
│   │   │   ├── useParts.ts
│   │   │   ├── useCustomers.ts
│   │   │   └── useWarranty.ts        # Dell API 워런티 조회
│   │   ├── pages/
│   │   │   ├── DashboardPage.vue
│   │   │   ├── CustomersPage.vue
│   │   │   ├── ProjectsPage.vue
│   │   │   ├── InventoryPage.vue     # 납품목록
│   │   │   ├── PartsPage.vue         # 파트재고
│   │   │   ├── DeliveriesPage.vue    # 납품이력
│   │   │   ├── AddressesPage.vue     # 납품주소
│   │   │   └── LoginPage.vue
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   ├── inventory.ts
│   │   │   ├── projects.ts
│   │   │   ├── parts.ts
│   │   │   ├── customers.ts
│   │   │   └── ui.ts                 # 사이드바 열림/닫힘 등 UI 상태
│   │   ├── types/
│   │   │   ├── index.ts              # 공통 타입 export
│   │   │   ├── inventory.ts
│   │   │   ├── project.ts
│   │   │   ├── part.ts
│   │   │   └── customer.ts
│   │   └── utils/
│   │       ├── api.ts                # Axios 인스턴스 + 인터셉터
│   │       ├── date.ts               # 날짜 포맷 유틸
│   │       └── status.ts             # 상태 라벨/색상 맵
│   ├── index.html
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── auth.py
│   │   │       │   ├── customers.py
│   │   │       │   ├── projects.py
│   │   │       │   ├── inventory.py
│   │   │       │   ├── parts.py
│   │   │       │   ├── deliveries.py
│   │   │       │   ├── addresses.py
│   │   │       │   └── warranty.py   # Dell API 프록시
│   │   │       └── router.py
│   │   ├── core/
│   │   │   ├── config.py             # Settings (pydantic-settings)
│   │   │   ├── security.py           # JWT 생성/검증
│   │   │   └── deps.py               # FastAPI Depends
│   │   ├── crud/
│   │   │   ├── base.py               # CRUDBase 제네릭 클래스
│   │   │   ├── crud_inventory.py
│   │   │   ├── crud_project.py
│   │   │   ├── crud_part.py
│   │   │   └── crud_customer.py
│   │   ├── db/
│   │   │   ├── base.py               # DeclarativeBase
│   │   │   └── session.py            # async_sessionmaker
│   │   ├── models/                   # SQLAlchemy ORM 모델
│   │   │   ├── user.py
│   │   │   ├── customer.py
│   │   │   ├── project.py
│   │   │   ├── server_inventory.py
│   │   │   ├── part_inventory.py
│   │   │   ├── part_usage.py
│   │   │   ├── address.py
│   │   │   ├── warranty.py
│   │   │   └── audit_log.py
│   │   ├── schemas/                  # Pydantic v2 스키마
│   │   │   ├── inventory.py
│   │   │   ├── project.py
│   │   │   ├── part.py
│   │   │   └── customer.py
│   │   └── services/
│   │       ├── dell_warranty.py      # Dell API 연동 서비스
│   │       └── approval.py           # 파트 수량 admin 승인 서비스
│   ├── alembic/
│   │   └── versions/
│   ├── alembic.ini
│   ├── main.py
│   └── requirements.txt
│
├── infra/
│   ├── docker-compose.yml            # 개발 환경
│   ├── docker-compose.prod.yml       # 운영 환경
│   ├── nginx/
│   │   └── default.conf
│   └── Makefile                      # 빌드/배포 자동화
│
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. 코딩 컨벤션

### Vue3 Frontend 규칙

```ts
// ✅ 올바른 컴포넌트 구조
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { ServerInventory } from '@/types'

// Props & Emits — 반드시 interface로 정의
interface Props {
  serverId: number
  readonly?: boolean
}
const props = withDefaults(defineProps<Props>(), { readonly: false })
const emit = defineEmits<{ close: []; saved: [item: ServerInventory] }>()

// 상태
const loading = ref(false)
const error = ref<string | null>(null)
</script>
```

```ts
// ✅ Pinia Store 구조
export const useInventoryStore = defineStore('inventory', () => {
  // state
  const items = ref<ServerInventory[]>([])
  const total = ref(0)
  const loading = ref(false)

  // getters
  const inStockCount = computed(() => items.value.filter(i => i.status === 'IN_STOCK').length)

  // actions
  async function fetchItems(params: InventoryParams) { ... }
  async function updateItem(id: number, data: Partial<ServerInventory>) { ... }

  return { items, total, loading, inStockCount, fetchItems, updateItem }
})
```

**금지 사항:**
- Options API 사용 금지 (Composition API only)
- `any` 타입 사용 금지 (unknown 사용)
- `v-html` 사용 금지 (XSS 위험)
- 직접 `fetch()` 호출 금지 → `utils/api.ts` Axios 인스턴스 사용

### FastAPI Backend 규칙

```python
# ✅ 올바른 라우터 구조
@router.get("/{item_id}", response_model=schemas.ServerInventoryOut)
async def get_server_inventory(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> schemas.ServerInventoryOut:
    """서버 재고 단건 조회"""
    item = await crud.inventory.get(db, id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="해당 자산을 찾을 수 없습니다.")
    return item
```

```python
# ✅ Pydantic v2 스키마
class ServerInventoryBase(BaseModel):
    serial_tag: str = Field(..., min_length=1, max_length=50)
    model: str
    category: Literal["SERVER", "PART"]
    status: ServerStatus = ServerStatus.IN_STOCK

class ServerInventoryCreate(ServerInventoryBase):
    project_id: int | None = None

class ServerInventoryOut(ServerInventoryBase):
    id: int
    in_date: date
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

**금지 사항:**
- `sync` DB 세션 사용 금지 (async only)
- Raw SQL 문자열 사용 금지 → SQLAlchemy ORM 사용
- `print()` 디버깅 금지 → `logging` 사용
- 하드코딩 환경변수 금지 → `core/config.py` Settings 참조

---

## 5. 데이터베이스 규칙

| 규칙 | 내용 |
|---|---|
| 테이블명 | 복수형 snake_case (`server_inventories`, `part_usages`) |
| PK | `id: Integer, autoincrement, primary_key` |
| 공통 컬럼 | `created_at`, `updated_at` (자동 설정) |
| 외래키 | `{테이블단수명}_id` (예: `customer_id`, `project_id`) |
| Soft Delete | `is_deleted: Boolean = False` — 실제 DELETE 쿼리 사용 금지 |
| 인덱스 | `serial_tag`, `status`, `customer_id`, `project_id` 필수 인덱스 |
| 마이그레이션 | 스키마 변경 시 반드시 `alembic revision --autogenerate` 후 검토 |

---

## 6. API 설계 규칙

```
Base URL:     /api/v1/
인증:         Authorization: Bearer {access_token}
Content-Type: application/json

# 목록 조회
GET    /api/v1/inventory?page=1&limit=20&search=&status=&category=&location=

# 단건 조회
GET    /api/v1/inventory/{id}

# 생성
POST   /api/v1/inventory

# 수정
PATCH  /api/v1/inventory/{id}     ← PUT 사용 금지 (부분 수정)

# 삭제 (soft delete)
DELETE /api/v1/inventory/{id}

# 응답 형식
{
  "data": T | T[],
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "total_pages": 5
  }
}

# 에러 형식
{
  "code": "NOT_FOUND",
  "message": "해당 자산을 찾을 수 없습니다."
}
```

---

## 7. 상태(Status) 정의

| 값 | 한국어 | 색상 | 사용 위치 |
|---|---|---|---|
| `IN_STOCK` | 재고 | emerald | 서버/파트 |
| `RESERVED` | 예약 | amber | 서버 |
| `SCHEDULED` | 납품예정 | blue | 서버/프로젝트 |
| `IN_PROGRESS` | 진행중 | cyan | 프로젝트 |
| `DELIVERED` | 납품완료 | blue | 서버 |
| `WAITING` | 대기 | orange | 프로젝트 |
| `RMA` | RMA | rose | 서버 |
| `COMPLETED` | 완료 | emerald | 프로젝트 |
| `ACTIVE` | 활성 | emerald | 고객사 |
| `INACTIVE` | 비활성 | slate | 고객사 |

---

## 8. 디자인 토큰

```ts
// tailwind.config.ts에 반영
export default {
  theme: {
    extend: {
      colors: {
        sidebar: '#0F172A',
        accent:  '#2563EB',
        // Status
        'status-stock':     '#10B981',  // emerald
        'status-reserved':  '#F59E0B',  // amber
        'status-delivered': '#3B82F6',  // blue
        'status-rma':       '#F43F5E',  // rose
        'status-progress':  '#06B6D4',  // cyan
        'status-waiting':   '#F97316',  // orange
        'status-part':      '#8B5CF6',  // violet
      }
    }
  }
}
```

```css
/* 공통 배경 */
--bg-base:    #F8FAFC;
--bg-card:    #FFFFFF;
--border:     #E2E8F0;
--text-main:  #0F172A;
--text-mute:  #64748B;
--text-light: #94A3B8;
```

---

## 9. 보안 규칙

- JWT Access Token 만료: **24h**, Refresh Token: **7d**
- 파트 수량 수정: `ADMIN` role 필수 — `Depends(require_admin)` 사용
- 모든 `/api/v1/*` 경로: 인증 필수 (로그인/회원가입 제외)
- `.env` 파일: git commit 절대 금지 (`.gitignore`에 반드시 포함)
- 비밀번호: bcrypt 해싱 필수, 평문 저장 금지
- Dell API Key: 서버 환경변수로만 관리 (프론트 노출 금지)
- CORS: 운영 환경에서 `FRONTEND_URL` 도메인만 허용

---

## 10. 핵심 비즈니스 로직 요약

1. **프로젝트 자동 입력**: 프로젝트 선택 → 담당자/연락처/납품주소 자동 채움
2. **Dell Warranty 자동 연동**: S/N 입력 시 Dell TechDirect API → Warranty 시작/종료일 자동 조회
3. **파트 Warranty 자동 계산**: 구매일 + 365일 = 만료일 (백엔드에서 계산)
4. **Admin 승인 워크플로우**: 파트 수량 수정 → `PENDING` 상태 → ADMIN 승인 → 자동 반영
5. **2종 팝업 분기**: 시리얼태그 클릭 시 `category === 'SERVER'` → ServerDetailModal, `'PART'` → PartDetailModal
6. **바코드 스캔**: `navigator.mediaDevices.getUserMedia` + `jsQR` → 시리얼태그 자동 입력
7. **동일사양 복사**: 같은 `model` + `in_date` 조건 → S/N만 교체하여 다건 등록

---

## 11. Docker 환경 변수

```env
# .env.example
# Backend
DATABASE_URL=postgresql+asyncpg://ams:password@db:5432/ams_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
DELL_API_CLIENT_ID=
DELL_API_CLIENT_SECRET=
FRONTEND_URL=http://localhost:5173

# Frontend (Vite)
VITE_API_BASE_URL=http://localhost:8000
```

---

## 12. Git 커밋 컨벤션

```
feat:     새 기능
fix:      버그 수정
refactor: 리팩토링
style:    코드 스타일 (기능 변화 없음)
docs:     문서 수정
chore:    빌드/설정 변경
db:       DB 스키마/마이그레이션 변경
infra:    Docker/배포 설정 변경

예시:
feat: 서버 상세 팝업 Dell Warranty 자동 조회 연동
fix: 파트재고 수량 수정 admin 승인 후 미반영 버그
db: part_usages 테이블 location 컬럼 추가
```
