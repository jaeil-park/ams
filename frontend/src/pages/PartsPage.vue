<template>
  <div class="space-y-6 font-sans">
    <!-- Header Page Banner -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">부품(파트) 재고 관리</h1>
        <p class="text-xs text-slate-400 mt-1">부품 재고 및 출고 이력 제어</p>
      </div>
      <div class="flex gap-2">
        <AppButton variant="primary" class="text-xs" @click="openCreateModal">
          <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          신규 파트 추가
        </AppButton>
      </div>
    </div>

    <!-- Search / Filter bar -->
    <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4 select-none">
      <div class="w-full sm:max-w-xs">
        <AppSearch v-model="search" placeholder="파트 모델명 또는 위치 검색..." @search="handleSearch" />
      </div>
      
      <!-- Project Filter -->
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400 font-semibold">프로젝트:</span>
        <select 
          v-model="projectFilter" 
          class="text-xs font-semibold bg-white border border-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 max-w-[150px]"
          @change="fetchParts"
        >
          <option value="">전체 프로젝트</option>
          <option v-for="p in activeProjects" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Master Data Table -->
    <AppTable 
      :columns="columns" 
      :items="parts" 
      :loading="loading"
    >
      <template #model="{ item }">
        <span 
          class="font-semibold text-blue-600 cursor-pointer hover:underline"
          @click="viewPartHistory(item.id)"
        >
          {{ item.model }}
        </span>
      </template>
      <template #qty="{ item }">
        <span class="font-bold text-slate-800">{{ item.qty }} 개</span>
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
          <!-- Register part usage trigger -->
          <AppButton variant="secondary" class="px-2 py-1 text-2xs bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border-emerald-300" @click="openUsageModal(item)">사용등록</AppButton>
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

    <!-- 1. Create/Edit Part Modal -->
    <AppModal 
      :is-open="isModalOpen" 
      :title="isEditMode ? '파트 정보 수정' : '신규 파트 추가'" 
      size="md" 
      @close="closeModal"
    >
      <form class="space-y-4 text-xs font-sans" @submit.prevent="submitForm">
        <!-- Model -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">부품 모델명 *</label>
          <input type="text" required v-model="form.model" placeholder="예: 1.92TB SATA 2.5 SSD" class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none" />
        </div>
        <!-- Category -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">카테고리</label>
          <input type="text" v-model="form.category" placeholder="PART" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
        </div>
        <!-- Qty -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">입고 수량 *</label>
          <input type="number" required v-model="form.qty" :disabled="isEditMode" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
        </div>
        <!-- Status -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">상태</label>
          <select v-model="form.status" class="block w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none">
            <option value="IN_STOCK">재고 (IN_STOCK)</option>
            <option value="RMA">RMA</option>
          </select>
        </div>
        <!-- Purchase Date -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">구매일자</label>
          <input type="date" v-model="form.purchase_date" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
        </div>
        <!-- Location -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">보관 위치</label>
          <input type="text" v-model="form.location" placeholder="본사 2층 자산창고 A-3" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
        </div>
        <!-- Project Mapping -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">프로젝트 할당</label>
          <select v-model="form.project_id" class="block w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900">
            <option :value="null">미할당 (가용 파트)</option>
            <option v-for="p in activeProjects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
      </form>
      <template #footer>
        <AppButton variant="secondary" @click="closeModal">취소</AppButton>
        <AppButton variant="primary" :loading="submitLoading" @click="submitForm">확인</AppButton>
      </template>
    </AppModal>

    <!-- 2. Part Usage Modal -->
    <AppModal 
      :is-open="isUsageModalOpen" 
      title="부품(파트) 출고/사용 내역 등록" 
      size="md" 
      @close="closeUsageModal"
    >
      <form class="space-y-4 text-xs font-sans" @submit.prevent="submitUsage">
        <div class="bg-slate-50 p-3 rounded border border-slate-200 font-semibold text-slate-700">
          대상 부품: {{ selectedPart?.model }} (보유 재고: {{ selectedPart?.qty }}개)
        </div>
        <!-- Customer -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">출고 납품 고객사 *</label>
          <select required v-model="usageForm.customer_id" class="block w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900">
            <option value="" disabled>고객사를 선택하세요</option>
            <option v-for="c in activeCustomers" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <!-- Qty -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">사용 출고 수량 *</label>
          <input type="number" required v-model="usageForm.qty" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
        </div>
        <!-- Location -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">납품 상세 주소/위치</label>
          <input type="text" v-model="usageForm.location" placeholder="수원 전산실 3층 A열" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
        </div>
        <!-- Reason -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">출고 및 장착 사유</label>
          <input type="text" v-model="usageForm.reason" placeholder="서버 용량 증설 건" class="block w-full px-3 py-2 border border-slate-300 rounded-md" />
        </div>
      </form>
      <template #footer>
        <AppButton variant="secondary" @click="closeUsageModal">취소</AppButton>
        <AppButton variant="primary" :loading="submitLoading" @click="submitUsage">출고 등록</AppButton>
      </template>
    </AppModal>

    <!-- 3. Part History / Detail Modal -->
    <PartHistoryModal 
      v-if="isHistoryOpen && currentPartId" 
      :is-open="isHistoryOpen" 
      :part-id="currentPartId" 
      @close="closePartHistory"
      @updated="fetchParts"
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
import PartHistoryModal from '@/components/domain/PartHistoryModal.vue'

const uiStore = useUiStore()

const parts = ref<any[]>([])
const activeProjects = ref<any[]>([])
const activeCustomers = ref<any[]>([])
const loading = ref(false)
const submitLoading = ref(false)

// Query filters
const search = ref('')
const projectFilter = ref('')
const page = ref(1)
const limit = ref(10)
const totalPages = ref(1)
const totalItems = ref(0)

const columns: ColumnDefinition[] = [
  { key: 'category', label: '구분' },
  { key: 'model', label: '부품 모델명' },
  { key: 'qty', label: '보유 수량' },
  { key: 'status', label: '상태' },
  { key: 'location', label: '보관 위치' },
  { key: 'project_id', label: '할당 프로젝트' },
  { key: 'actions', label: '관리' }
]

// Modal & Form State
const isModalOpen = ref(false)
const isEditMode = ref(false)
const currentEditId = ref<number | null>(null)
const form = ref<any>({
  model: '',
  category: 'PART',
  qty: 0,
  status: 'IN_STOCK',
  purchase_date: '',
  location: '',
  project_id: null
})

// Usage Modal state
const isUsageModalOpen = ref(false)
const selectedPart = ref<any>(null)
const usageForm = ref<any>({
  qty: 1,
  customer_id: '',
  location: '',
  reason: ''
})

// History modal state
const isHistoryOpen = ref(false)
const currentPartId = ref<number | null>(null)

onMounted(() => {
  fetchParts()
  fetchActiveProjects()
  fetchActiveCustomers()
})

async function fetchParts() {
  loading.value = true
  try {
    let url = `/parts?page=${page.value}&limit=${limit.value}`
    if (search.value) url += `&search=${encodeURIComponent(search.value)}`
    
    const res = await api.get(url)
    let data = res.data.data
    
    // Project filter (local bypass)
    if (projectFilter.value) {
      data = data.filter((p: any) => p.project_id === Number(projectFilter.value))
    }
    
    parts.value = data
    
    const meta = res.data.meta
    if (meta) {
      totalItems.value = meta.total
      totalPages.value = meta.total_pages
    }
  } catch (error) {
    console.error(error)
    uiStore.addToast('파트 재고 조회 실패', 'error')
  } finally {
    loading.value = false
  }
}

async function fetchActiveProjects() {
  try {
    const res = await api.get('/projects?limit=100')
    activeProjects.value = res.data.data
  } catch (error) {
    console.error(error)
  }
}

async function fetchActiveCustomers() {
  try {
    const res = await api.get('/customers?limit=100&status=ACTIVE')
    activeCustomers.value = res.data.data
  } catch (error) {
    console.error(error)
  }
}

function getProjectName(projId: number | null) {
  if (!projId) return '미할당 (가용파트)'
  const p = activeProjects.value.find(item => item.id === projId)
  return p ? p.name : `프로젝트(ID:${projId})`
}

function handleSearch(val: string) {
  search.value = val
  page.value = 1
  fetchParts()
}

function handlePageChange(newPage: number) {
  page.value = newPage
  fetchParts()
}

// Single edit workflow
function openCreateModal() {
  isEditMode.value = false
  currentEditId.value = null
  form.value = {
    model: '',
    category: 'PART',
    qty: 1,
    status: 'IN_STOCK',
    purchase_date: new Date().toISOString().substring(0, 10),
    location: '',
    project_id: null
  }
  isModalOpen.value = true
}

function openEditModal(item: any) {
  isEditMode.value = true
  currentEditId.value = item.id
  form.value = {
    model: item.model,
    category: item.category || 'PART',
    qty: item.qty,
    status: item.status,
    purchase_date: item.purchase_date || '',
    location: item.location || '',
    project_id: item.project_id
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
    if (!payload.purchase_date) delete payload.purchase_date
    
    if (isEditMode.value && currentEditId.value) {
      await api.patch(`/parts/${currentEditId.value}`, payload)
      uiStore.addToast('파트 정보가 변경되었습니다.', 'success')
    } else {
      await api.post('/parts', payload)
      uiStore.addToast('신규 부품이 안전하게 등록되었습니다.', 'success')
    }
    closeModal()
    fetchParts()
  } catch (error: any) {
    console.error(error)
    const errDetail = error.response?.data?.detail || '파트 등록 실패'
    uiStore.addToast(errDetail, 'error')
  } finally {
    submitLoading.value = false
  }
}

// Usage workflow
function openUsageModal(item: any) {
  selectedPart.value = item
  usageForm.value = {
    qty: 1,
    customer_id: '',
    location: '',
    reason: ''
  }
  isUsageModalOpen.value = true
}

function closeUsageModal() {
  isUsageModalOpen.value = false
  selectedPart.value = null
}

async function submitUsage() {
  if (!usageForm.value.customer_id) {
    uiStore.addToast('고객사를 지정해 주세요.', 'warning')
    return
  }
  if (usageForm.value.qty > selectedPart.value.qty) {
    uiStore.addToast('출고 수량이 재고 수량보다 많습니다.', 'warning')
    return
  }

  submitLoading.value = true
  try {
    const res = await api.post(`/parts/${selectedPart.value.id}/usage`, usageForm.value)
    if (res.data.data) {
      uiStore.addToast('파트가 성공적으로 출고 처리되었습니다.', 'success')
      closeUsageModal()
      fetchParts()
    }
  } catch (error) {
    console.error(error)
    uiStore.addToast('출고 등록 실패', 'error')
  } finally {
    submitLoading.value = false
  }
}

// History workflow
function viewPartHistory(id: number) {
  currentPartId.value = id
  isHistoryOpen.value = true
}

function closePartHistory() {
  isHistoryOpen.value = false
  currentPartId.value = null
}

async function handleDelete(id: number) {
  if (!confirm('정말로 이 부품 자산을 삭제하시겠습니까? (Soft Delete)')) return
  try {
    await api.delete(`/parts/${id}`)
    uiStore.addToast('부품이 목록에서 안전하게 삭제되었습니다.', 'success')
    fetchParts()
  } catch (error) {
    console.error(error)
    uiStore.addToast('부품 삭제 실패', 'error')
  }
}
</script>
