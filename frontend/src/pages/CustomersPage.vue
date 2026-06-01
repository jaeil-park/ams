<template>
  <div class="space-y-6 font-sans">
    <!-- Header Page Banner -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">고객사 관리</h1>
        <p class="text-xs text-slate-400 mt-1">AMS 연동 기업 목록 및 기본정보</p>
      </div>
      <AppButton variant="primary" class="text-xs" @click="openCreateModal">
        <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        고객사 신규 등록
      </AppButton>
    </div>

    <!-- Search / Filter bar -->
    <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="w-full sm:max-w-xs">
        <AppSearch v-model="search" placeholder="고객사명 또는 코드 검색..." @search="handleSearch" />
      </div>
      
      <!-- Status Filter -->
      <div class="flex items-center gap-2 self-end sm:self-auto select-none">
        <span class="text-xs text-slate-400 font-semibold">필터:</span>
        <select 
          v-model="statusFilter" 
          class="text-xs font-semibold bg-white border border-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
          @change="fetchCustomers"
        >
          <option value="">전체 상태</option>
          <option value="ACTIVE">활성 (ACTIVE)</option>
          <option value="INACTIVE">비활성 (INACTIVE)</option>
        </select>
      </div>
    </div>

    <!-- Main Data Table -->
    <AppTable 
      :columns="columns" 
      :items="customers" 
      :loading="loading"
      @sort="handleSort"
    >
      <template #status="{ item }">
        <AppBadge :status="item.status" />
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

    <!-- Create/Edit Modal -->
    <AppModal 
      :is-open="isModalOpen" 
      :title="isEditMode ? '고객사 정보 수정' : '신규 고객사 등록'" 
      size="md" 
      @close="closeModal"
    >
      <form class="space-y-4" @submit.prevent="submitForm">
        <!-- Code -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">고객사 코드 (Unique)</label>
          <input 
            type="text" 
            required 
            v-model="form.code"
            :disabled="isEditMode"
            placeholder="예: DAEWOONG, LINE"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400"
          />
        </div>
        <!-- Name -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">회사명 / 고객사명</label>
          <input 
            type="text" 
            required 
            v-model="form.name"
            placeholder="예: 대웅제약, 라인플러스"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <!-- Biz No -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">사업자등록번호</label>
          <input 
            type="text" 
            v-model="form.biz_no"
            placeholder="123-45-67890"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <!-- Manager -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">담당자 성함</label>
          <input 
            type="text" 
            v-model="form.manager"
            placeholder="홍길동"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <!-- Phone -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">담당자 연락처</label>
          <input 
            type="text" 
            v-model="form.phone"
            placeholder="010-1234-5678"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <!-- Status -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">상태</label>
          <select 
            v-model="form.status"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="ACTIVE">활성 (ACTIVE)</option>
            <option value="INACTIVE">비활성 (INACTIVE)</option>
          </select>
        </div>
      </form>
      
      <template #footer>
        <AppButton variant="secondary" @click="closeModal">취소</AppButton>
        <AppButton variant="primary" :loading="submitLoading" @click="submitForm">
          {{ isEditMode ? '수정완료' : '등록하기' }}
        </AppButton>
      </template>
    </AppModal>
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

const uiStore = useUiStore()

const customers = ref<any[]>([])
const loading = ref(false)
const submitLoading = ref(false)

// Query / Filter state
const search = ref('')
const statusFilter = ref('')
const page = ref(1)
const limit = ref(10)
const totalPages = ref(1)
const totalItems = ref(0)
const sortField = ref('created_at')
const sortOrder = ref('desc')

const columns: ColumnDefinition[] = [
  { key: 'code', label: '고객사 코드', sortable: true },
  { key: 'name', label: '고객사명', sortable: true },
  { key: 'biz_no', label: '사업자번호' },
  { key: 'manager', label: '담당자' },
  { key: 'phone', label: '연락처' },
  { key: 'status', label: '상태' },
  { key: 'actions', label: '관리' }
]

// Modal & Form State
const isModalOpen = ref(false)
const isEditMode = ref(false)
const currentEditId = ref<number | null>(null)
const form = ref({
  code: '',
  name: '',
  biz_no: '',
  manager: '',
  phone: '',
  status: 'ACTIVE'
})

onMounted(() => {
  fetchCustomers()
})

async function fetchCustomers() {
  loading.value = true
  try {
    let url = `/customers?page=${page.value}&limit=${limit.value}`
    if (search.value) url += `&search=${encodeURIComponent(search.value)}`
    if (statusFilter.value) url += `&status=${statusFilter.value}`
    
    const res = await api.get(url)
    customers.value = res.data.data
    
    const meta = res.data.meta
    if (meta) {
      totalItems.value = meta.total
      totalPages.value = meta.total_pages
    }
  } catch (error) {
    console.error(error)
    uiStore.addToast('고객사 목록 조회 실패', 'error')
  } finally {
    loading.value = false
  }
}

function handleSearch(val: string) {
  search.value = val
  page.value = 1
  fetchCustomers()
}

function handlePageChange(newPage: number) {
  page.value = newPage
  fetchCustomers()
}

function handleSort(payload: { key: string; order: 'asc' | 'desc' }) {
  sortField.value = payload.key
  sortOrder.value = payload.order
  fetchCustomers()
}

// Create/Edit Workflow
function openCreateModal() {
  isEditMode.value = false
  currentEditId.value = null
  form.value = {
    code: '',
    name: '',
    biz_no: '',
    manager: '',
    phone: '',
    status: 'ACTIVE'
  }
  isModalOpen.value = true
}

function openEditModal(item: any) {
  isEditMode.value = true
  currentEditId.value = item.id
  form.value = {
    code: item.code,
    name: item.name,
    biz_no: item.biz_no || '',
    manager: item.manager || '',
    phone: item.phone || '',
    status: item.status
  }
  isModalOpen.value = true
}

function closeModal() {
  isModalOpen.value = false
}

async function submitForm() {
  submitLoading.value = true
  try {
    if (isEditMode.value && currentEditId.value) {
      const res = await api.patch(`/customers/${currentEditId.value}`, form.value)
      if (res.data.data) {
        uiStore.addToast('고객사 정보가 수정되었습니다.', 'success')
      }
    } else {
      const res = await api.post('/customers', form.value)
      if (res.data.data) {
        uiStore.addToast('새 고객사가 등록되었습니다.', 'success')
      }
    }
    closeModal()
    fetchCustomers()
  } catch (error: any) {
    console.error(error)
    const errorMsg = error.response?.data?.detail || '요청 처리 실패'
    uiStore.addToast(errorMsg, 'error')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(id: number) {
  if (!confirm('정말로 이 고객사를 삭제하시겠습니까? (Soft Delete)')) return
  try {
    await api.delete(`/customers/${id}`)
    uiStore.addToast('고객사 정보가 성공적으로 삭제되었습니다.', 'success')
    fetchCustomers()
  } catch (error) {
    console.error(error)
    uiStore.addToast('고객사 삭제 실패', 'error')
  }
}
</script>
