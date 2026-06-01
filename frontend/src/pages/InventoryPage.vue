<template>
  <div class="space-y-6 font-sans">
    <!-- Header Page Banner -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">납품목록 (서버 재고)</h1>
        <p class="text-xs text-slate-400 mt-1">서버 인벤토리 단건 및 동일 사양 대량 입고 제어</p>
      </div>
      <div class="flex gap-2">
        <AppButton variant="secondary" class="text-xs" @click="openBulkModal">
          <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
          </svg>
          동일사양 다건 복사 입고
        </AppButton>
        <AppButton variant="primary" class="text-xs" @click="openCreateModal">
          <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          서버 단건 입고 등록
        </AppButton>
      </div>
    </div>

    <!-- Search / Filter bar -->
    <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4 select-none">
      <div class="w-full sm:max-w-xs">
        <AppSearch v-model="search" placeholder="시리얼 태그(S/N) 또는 모델 검색..." @search="handleSearch" />
      </div>
      
      <div class="flex items-center gap-4">
        <!-- Status Filter -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-400 font-semibold">장비상태:</span>
          <select 
            v-model="statusFilter" 
            class="text-xs font-semibold bg-white border border-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="fetchInventory"
          >
            <option value="">전체 상태</option>
            <option value="IN_STOCK">재고 (IN_STOCK)</option>
            <option value="RESERVED">예약 (RESERVED)</option>
            <option value="SCHEDULED">납품예정 (SCHEDULED)</option>
            <option value="DELIVERED">납품완료 (DELIVERED)</option>
            <option value="RMA">RMA</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Master Table -->
    <AppTable 
      :columns="columns" 
      :items="servers" 
      :loading="loading"
      @sort="handleSort"
    >
      <template #serial_tag="{ item }">
        <span 
          class="font-mono font-bold text-blue-600 cursor-pointer hover:underline"
          @click="viewDetails(item.id)"
        >
          {{ item.serial_tag }}
        </span>
      </template>
      <template #status="{ item }">
        <AppBadge :status="item.status" />
      </template>
      <template #project_id="{ item }">
        <span class="text-xs text-slate-500 font-medium">
          {{ getProjectName(item.project_id) }}
        </span>
      </template>
      <template #actions="{ item }">
        <div class="flex items-center gap-2">
          <AppButton variant="secondary" class="px-2 py-1 text-2xs" @click="openEditModal(item)">수정</AppButton>
          <AppButton variant="danger" class="px-2 py-1 text-2xs" @click="handleDelete(item.id)">삭제</AppButton>
        </div>
      </template>
    </AppTable>

    <!-- Pagination -->
    <AppPagination 
      :current-page="page" 
      :total-pages="totalPages" 
      :total-items="totalItems" 
      :limit="limit"
      @page-change="handlePageChange"
    />

    <!-- 1. Create/Edit Single Modal -->
    <AppModal 
      :is-open="isModalOpen" 
      :title="isEditMode ? '서버 정보 수정' : '단건 입고 등록'" 
      size="lg" 
      @close="closeModal"
    >
      <form class="space-y-4 text-xs font-sans" @submit.prevent="submitForm">
        <!-- Basic info row -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block font-semibold text-slate-500 mb-1">시리얼 태그 (S/N) *</label>
            <input 
              type="text" 
              required 
              v-model="form.serial_tag"
              :disabled="isEditMode"
              placeholder="예: 7XYZ123"
              class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">장비 모델명 *</label>
            <input 
              type="text" 
              required 
              v-model="form.model"
              placeholder="예: PowerEdge R760"
              class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none"
            />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">제조사 (Vendor)</label>
            <input 
              type="text" 
              v-model="form.vendor"
              placeholder="예: DELL"
              class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none"
            />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">입고 날짜</label>
            <input 
              type="date" 
              v-model="form.in_date"
              class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none"
            />
          </div>
        </div>

        <h4 class="font-bold text-slate-800 pb-1 border-b border-slate-100 pt-3">하드웨어 상세 사양</h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <label class="block font-semibold text-slate-500 mb-1">CPU 모델</label>
            <input type="text" v-model="form.cpu_model" placeholder="Xeon Gold 6430" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">CPU 코어 수</label>
            <input type="number" v-model="form.cpu_core" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">MEM 총 용량 (GB)</label>
            <input type="number" v-model="form.mem_capacity" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">MEM 규격</label>
            <input type="text" v-model="form.mem_gen" placeholder="DDR5 ECC" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">MEM 장착 개수</label>
            <input type="number" v-model="form.mem_qty" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block font-semibold text-slate-500 mb-1">DISK 1 사양</label>
            <input type="text" v-model="form.disk1_spec" placeholder="1.92TB SATA SSD" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">DISK 1 수량 & RAID</label>
            <div class="flex gap-2">
              <input type="number" v-model="form.disk1_qty" placeholder="개수" class="block w-1/3 px-3 py-2 border border-slate-300 rounded-md" />
              <input type="text" v-model="form.disk1_raid" placeholder="RAID 1" class="block w-2/3 px-3 py-2 border border-slate-300 rounded-md" />
            </div>
          </div>
        </div>

        <h4 class="font-bold text-slate-800 pb-1 border-b border-slate-100 pt-3">소속 프로젝트 및 네트워크 정보</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block font-semibold text-slate-500 mb-1">프로젝트 할당</label>
            <select 
              v-model="form.project_id"
              class="block w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
            >
              <option :value="null">미할당 (재고 상태)</option>
              <option v-for="p in activeProjects" :key="p.id" :value="p.id">
                {{ p.name }} ({{ p.po_number }})
              </option>
            </select>
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">장비 상태</label>
            <select 
              v-model="form.status"
              class="block w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
            >
              <option value="IN_STOCK">재고 (IN_STOCK)</option>
              <option value="RESERVED">예약 (RESERVED)</option>
              <option value="SCHEDULED">납품예정 (SCHEDULED)</option>
              <option value="DELIVERED">납품완료 (DELIVERED)</option>
              <option value="RMA">RMA</option>
            </select>
          </div>
        </div>
      </form>
      
      <template #footer>
        <AppButton variant="secondary" @click="closeModal">취소</AppButton>
        <AppButton variant="primary" :loading="submitLoading" @click="submitForm">
          {{ isEditMode ? '수정완료' : '등록하기' }}
        </AppButton>
      </template>
    </AppModal>

    <!-- 2. Create Bulk Copy Modal -->
    <AppModal 
      :is-open="isBulkModalOpen" 
      title="동일사양 대량 복사 입고" 
      size="lg" 
      @close="closeBulkModal"
    >
      <div class="space-y-4 text-xs font-sans">
        <!-- Serial Tags Textarea -->
        <div>
          <label class="block font-bold text-slate-700 mb-1">시리얼 태그 리스트 *</label>
          <textarea 
            required 
            v-model="bulkSerialsText"
            rows="4"
            placeholder="시리얼 번호들을 엔터(줄바꿈) 또는 쉼표(,)로 분리해서 입력해 주세요. 입력한 개수만큼 장비 자산이 개별 등록됩니다."
            class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono text-xs"
          ></textarea>
        </div>

        <h4 class="font-bold text-slate-800 pb-1 border-b border-slate-100 pt-3">기본 입고 장비 공동 사양</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block font-semibold text-slate-500 mb-1">공동 모델명 *</label>
            <input type="text" required v-model="bulkForm.model" placeholder="PowerEdge R760" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
          <div>
            <label class="block font-semibold text-slate-500 mb-1">제조사 (Vendor)</label>
            <input type="text" v-model="bulkForm.vendor" placeholder="DELL" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
          </div>
        </div>
      </div>
      
      <template #footer>
        <AppButton variant="secondary" @click="closeBulkModal">취소</AppButton>
        <AppButton variant="primary" :loading="submitLoading" @click="submitBulkForm">
          대량 복사 등록 실행
        </AppButton>
      </template>
    </AppModal>

    <!-- 3. Server Detail Modal -->
    <ServerDetailModal 
      v-if="isDetailOpen && currentServerId" 
      :is-open="isDetailOpen" 
      :server-id="currentServerId" 
      @close="closeDetails"
      @updated="fetchInventory"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import AppButton from '@/components/common/AppButton.vue'
import AppBadge from '@/components/common/AppBadge.vue'
import AppTable from '@/components/common/AppTable.vue'
import type { ColumnDefinition } from '@/components/common/AppTable.vue'
import AppSearch from '@/components/common/AppSearch.vue'
import AppPagination from '@/components/common/AppPagination.vue'
import AppModal from '@/components/common/AppModal.vue'
import ServerDetailModal from '@/components/domain/ServerDetailModal.vue'

const uiStore = useUiStore()

const servers = ref<any[]>([])
const activeProjects = ref<any[]>([])
const loading = ref(false)
const submitLoading = ref(false)

// Query filters
const search = ref('')
const statusFilter = ref('')
const page = ref(1)
const limit = ref(10)
const totalPages = ref(1)
const totalItems = ref(0)
const sortField = ref('created_at')
const sortOrder = ref('desc')

const columns: ColumnDefinition[] = [
  { key: 'in_date', label: '입고일자', sortable: true },
  { key: 'serial_tag', label: '시리얼태그(S/N)', sortable: true },
  { key: 'model', label: '장비 모델', sortable: true },
  { key: 'status', label: '상태' },
  { key: 'project_id', label: '소속 프로젝트' },
  { key: 'actions', label: '관리' }
]

// Modal Form State (Single)
const isModalOpen = ref(false)
const isEditMode = ref(false)
const currentEditId = ref<number | null>(null)
const form = ref<any>({
  serial_tag: '',
  model: '',
  vendor: 'DELL',
  in_date: '',
  status: 'IN_STOCK',
  project_id: null,
  cpu_model: '',
  cpu_core: null,
  mem_capacity: null,
  mem_gen: 'DDR5 ECC',
  mem_qty: null,
  disk1_spec: '',
  disk1_qty: null,
  disk1_raid: ''
})

// Modal Form State (Bulk)
const isBulkModalOpen = ref(false)
const bulkSerialsText = ref('')
const bulkForm = ref<any>({
  model: '',
  vendor: 'DELL',
  status: 'IN_STOCK',
  project_id: null
})

// Detail modal state
const isDetailOpen = ref(false)
const currentServerId = ref<number | null>(null)

onMounted(() => {
  fetchInventory()
  fetchActiveProjects()
})

async function fetchInventory() {
  loading.value = true
  try {
    let url = `/inventory?page=${page.value}&limit=${limit.value}`
    if (search.value) url += `&search=${encodeURIComponent(search.value)}`
    if (statusFilter.value) url += `&status=${statusFilter.value}`

    const res = await api.get(url)
    servers.value = res.data.data

    const meta = res.data.meta
    if (meta) {
      totalItems.value = meta.total
      totalPages.value = meta.total_pages
    }
  } catch (error) {
    console.error(error)
    uiStore.addToast('서버 재고 목록 조회 실패', 'error')
  } finally {
    loading.value = false
  }
}

async function fetchActiveProjects() {
  try {
    const res = await api.get('/projects?limit=100')
    activeProjects.value = res.data.data
  } catch (error) {
    console.error('Active projects list failed:', error)
  }
}

function getProjectName(projId: number | null) {
  if (!projId) return '미할당 (가용재고)'
  const p = activeProjects.value.find(item => item.id === projId)
  return p ? p.name : `프로젝트(ID:${projId})`
}

function handleSearch(val: string) {
  search.value = val
  page.value = 1
  fetchInventory()
}

function handlePageChange(newPage: number) {
  page.value = newPage
  fetchInventory()
}

function handleSort(payload: { key: string; order: 'asc' | 'desc' }) {
  sortField.value = payload.key
  sortOrder.value = payload.order
  fetchInventory()
}

// Single edit workflow
function openCreateModal() {
  isEditMode.value = false
  currentEditId.value = null
  form.value = {
    serial_tag: '',
    model: '',
    vendor: 'DELL',
    in_date: new Date().toISOString().substring(0, 10),
    status: 'IN_STOCK',
    project_id: null,
    cpu_model: '',
    cpu_core: null,
    mem_capacity: null,
    mem_gen: 'DDR5 ECC',
    mem_qty: null,
    disk1_spec: '',
    disk1_qty: null,
    disk1_raid: ''
  }
  isModalOpen.value = true
}

function openEditModal(item: any) {
  isEditMode.value = true
  currentEditId.value = item.id
  form.value = {
    serial_tag: item.serial_tag,
    model: item.model,
    vendor: item.vendor || 'DELL',
    in_date: item.in_date || '',
    status: item.status,
    project_id: item.project_id,
    cpu_model: item.cpu_model || '',
    cpu_core: item.cpu_core || null,
    mem_capacity: item.mem_capacity || null,
    mem_gen: item.mem_gen || 'DDR5 ECC',
    mem_qty: item.mem_qty || null,
    disk1_spec: item.disk1_spec || '',
    disk1_qty: item.disk1_qty || null,
    disk1_raid: item.disk1_raid || ''
  }
  isModalOpen.value = true
}

function closeModal() {
  isModalOpen.value = false
}

async function submitForm() {
  submitLoading.value = true
  try {
    const payload = { ...form.value }
    if (isEditMode.value && currentEditId.value) {
      await api.patch(`/inventory/${currentEditId.value}`, payload)
      uiStore.addToast('서버 자산 정보가 수정되었습니다.', 'success')
    } else {
      await api.post('/inventory', payload)
      uiStore.addToast('신규 서버 장비가 안전하게 입고되었습니다.', 'success')
    }
    closeModal()
    fetchInventory()
  } catch (error: any) {
    console.error(error)
    const errDetail = error.response?.data?.detail || '입고 처리 실패'
    uiStore.addToast(errDetail, 'error')
  } finally {
    submitLoading.value = false
  }
}

// Bulk edit workflow
function openBulkModal() {
  bulkSerialsText.value = ''
  bulkForm.value = {
    model: '',
    vendor: 'DELL',
    status: 'IN_STOCK',
    project_id: null
  }
  isBulkModalOpen.value = true
}

function closeBulkModal() {
  isBulkModalOpen.value = false
}

async function submitBulkForm() {
  if (!bulkSerialsText.value.trim()) {
    uiStore.addToast('하나 이상의 Serial Tag를 입력해 주세요.', 'warning')
    return
  }
  
  // Parse serial list
  const tags = bulkSerialsText.value
    .split(/[\n,]/)
    .map(t => t.trim())
    .filter(t => t.length > 0)

  if (tags.length === 0) {
    uiStore.addToast('유효한 시리얼 태그 리스트를 찾을 수 없습니다.', 'warning')
    return
  }

  submitLoading.value = true
  try {
    const payload = {
      serial_tags: tags,
      base_info: {
        serial_tag: 'BULK_TEMP_VAL', // backend validator bypass
        ...bulkForm.value
      }
    }

    await api.post('/inventory/bulk', payload)
    uiStore.addToast(`성공적으로 ${tags.length}대의 서버 장비 입고 완료!`, 'success')
    closeBulkModal()
    fetchInventory()
  } catch (error: any) {
    console.error(error)
    const errDetail = error.response?.data?.detail || '대량 입고 처리 실패'
    uiStore.addToast(errDetail, 'error')
  } finally {
    submitLoading.value = false
  }
}

// Detail workflow
function viewDetails(id: number) {
  currentServerId.value = id
  isDetailOpen.value = true
}

function closeDetails() {
  isDetailOpen.value = false
  currentServerId.value = null
}

async function handleDelete(id: number) {
  if (!confirm('정말로 이 서버 자산을 삭제하시겠습니까? (Soft Delete)')) return
  try {
    await api.delete(`/inventory/${id}`)
    uiStore.addToast('자산이 성공적으로 삭제(Soft Delete) 처리되었습니다.', 'success')
    fetchInventory()
  } catch (error) {
    console.error(error)
    uiStore.addToast('자산 삭제 처리 실패', 'error')
  }
}
</script>
