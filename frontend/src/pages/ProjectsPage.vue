<template>
  <div class="space-y-6 font-sans">
    <!-- Header Page Banner -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">프로젝트 관리</h1>
        <p class="text-xs text-slate-400 mt-1">AMS 연동 프로젝트 및 납품처 정보</p>
      </div>
      <AppButton variant="primary" class="text-xs" @click="openCreateModal">
        <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        프로젝트 등록
      </AppButton>
    </div>

    <!-- Search / Filter bar -->
    <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4 select-none">
      <div class="w-full sm:max-w-xs">
        <AppSearch v-model="search" placeholder="프로젝트명 또는 PO 번호 검색..." @search="handleSearch" />
      </div>
      
      <div class="flex items-center gap-4">
        <!-- Status Filter -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-400 font-semibold">진행상태:</span>
          <select 
            v-model="statusFilter" 
            class="text-xs font-semibold bg-white border border-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="fetchProjects"
          >
            <option value="">전체 상태</option>
            <option value="WAITING">대기 (WAITING)</option>
            <option value="IN_PROGRESS">진행중 (IN_PROGRESS)</option>
            <option value="COMPLETED">완료 (COMPLETED)</option>
          </select>
        </div>

        <!-- Customer Filter -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-400 font-semibold">고객사:</span>
          <select 
            v-model="customerFilter" 
            class="text-xs font-semibold bg-white border border-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 max-w-[150px]"
            @change="fetchProjects"
          >
            <option value="">전체 고객사</option>
            <option v-for="c in activeCustomers" :key="c.id" :value="c.id">
              {{ c.name }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Master Table with Accordion Panel -->
    <div class="overflow-x-auto rounded-lg border border-slate-200 shadow-sm bg-white">
      <table class="min-w-full divide-y divide-slate-200 text-sm">
        <thead class="bg-slate-50 select-none">
          <tr>
            <th class="px-6 py-3 w-10"></th>
            <th class="px-6 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">PO 번호</th>
            <th class="px-6 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">프로젝트명</th>
            <th class="px-6 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">고객사</th>
            <th class="px-6 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">담당자/연락처</th>
            <th class="px-6 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">납품일정</th>
            <th class="px-6 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">상태</th>
            <th class="px-6 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">관리</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-200 bg-white">
          <tr v-if="loading">
            <td colspan="8" class="px-6 py-12 text-center text-slate-400">데이터를 불러오는 중...</td>
          </tr>
          <tr v-else-if="projects.length === 0">
            <td colspan="8" class="px-6 py-12 text-center text-slate-400">조회된 프로젝트가 없습니다.</td>
          </tr>
          <template v-else v-for="proj in projects" :key="proj.id">
            <!-- Master Row -->
            <tr class="hover:bg-slate-50 transition-colors">
              <td class="px-6 py-4 text-center">
                <button 
                  type="button" 
                  class="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none"
                  @click="toggleRow(proj.id)"
                >
                  <svg 
                    :class="['h-4 w-4 transform transition-transform duration-200', expandedRows.includes(proj.id) ? 'rotate-90' : '']"
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </td>
              <td class="px-6 py-4 font-mono font-bold text-slate-700">{{ proj.po_number }}</td>
              <td class="px-6 py-4 text-slate-700 font-semibold">{{ proj.name }}</td>
              <td class="px-6 py-4 text-slate-500 font-semibold">{{ getCustomerName(proj.customer_id) }}</td>
              <td class="px-6 py-4 text-slate-500">
                <div class="font-medium text-slate-700">{{ proj.manager || '-' }}</div>
                <div class="text-3xs font-mono">{{ proj.phone || '-' }}</div>
              </td>
              <td class="px-6 py-4 text-slate-500 font-mono">{{ proj.scheduled_date || '-' }}</td>
              <td class="px-6 py-4"><AppBadge :status="proj.status" /></td>
              <td class="px-6 py-4">
                <div class="flex items-center gap-2">
                  <AppButton variant="secondary" class="px-2 py-1 text-2xs" @click="openEditModal(proj)">수정</AppButton>
                  <AppButton variant="danger" class="px-2 py-1 text-2xs" @click="handleDelete(proj.id)">삭제</AppButton>
                </div>
              </td>
            </tr>

            <!-- Expanded Detail Row -->
            <tr v-if="expandedRows.includes(proj.id)">
              <td colspan="8" class="px-6 py-2 bg-slate-50">
                <ProjectItemsPanel :project-id="proj.id" />
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

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
      :title="isEditMode ? '프로젝트 정보 수정' : '신규 프로젝트 생성'" 
      size="md" 
      @close="closeModal"
    >
      <form class="space-y-4 font-sans" @submit.prevent="submitForm">
        <!-- PO Number -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">PO 번호</label>
          <input 
            type="text" 
            required 
            v-model="form.po_number"
            :disabled="isEditMode"
            placeholder="예: PO-202605-001"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          />
        </div>
        <!-- Name -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">프로젝트명</label>
          <input 
            type="text" 
            required 
            v-model="form.name"
            placeholder="예: 대웅제약 ERP 납품 건"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          />
        </div>
        <!-- Customer Selection -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">고객사 선택</label>
          <select 
            required
            v-model="form.customer_id"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          >
            <option value="" disabled>고객사를 선택하세요</option>
            <option v-for="c in activeCustomers" :key="c.id" :value="c.id">
              {{ c.name }}
            </option>
          </select>
        </div>
        <!-- Manager -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">납품 담당자명</label>
          <input 
            type="text" 
            v-model="form.manager"
            placeholder="홍길동"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          />
        </div>
        <!-- Phone -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">담당자 연락처</label>
          <input 
            type="text" 
            v-model="form.phone"
            placeholder="010-1234-5678"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          />
        </div>
        <!-- Scheduled Date -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">납품 예정일</label>
          <input 
            type="date" 
            v-model="form.scheduled_date"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          />
        </div>
        <!-- Location -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">납품 주소지</label>
          <input 
            type="text" 
            v-model="form.location"
            placeholder="예: 서울특별시 강남구 테헤란로 123"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          />
        </div>
        <!-- Status -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">프로젝트 상태</label>
          <select 
            v-model="form.status"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          >
            <option value="WAITING">대기 (WAITING)</option>
            <option value="IN_PROGRESS">진행중 (IN_PROGRESS)</option>
            <option value="COMPLETED">완료 (COMPLETED)</option>
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
import AppPagination from '@/components/common/AppPagination.vue'
import AppModal from '@/components/common/AppModal.vue'
import AppSearch from '@/components/common/AppSearch.vue'
import ProjectItemsPanel from '@/components/domain/ProjectItemsPanel.vue'

const uiStore = useUiStore()

const projects = ref<any[]>([])
const activeCustomers = ref<any[]>([])
const loading = ref(false)
const submitLoading = ref(false)

const expandedRows = ref<number[]>([])

// Query filters
const search = ref('')
const statusFilter = ref('')
const customerFilter = ref('')
const page = ref(1)
const limit = ref(10)
const totalPages = ref(1)
const totalItems = ref(0)

// Modal form state
const isModalOpen = ref(false)
const isEditMode = ref(false)
const currentEditId = ref<number | null>(null)
const form = ref<any>({
  po_number: '',
  name: '',
  customer_id: '',
  manager: '',
  phone: '',
  scheduled_date: '',
  location: '',
  status: 'WAITING'
})

onMounted(() => {
  fetchProjects()
  fetchActiveCustomers()
})

async function fetchProjects() {
  loading.value = true
  try {
    let url = `/projects?page=${page.value}&limit=${limit.value}`
    if (search.value) url += `&search=${encodeURIComponent(search.value)}`
    if (statusFilter.value) url += `&status=${statusFilter.value}`
    if (customerFilter.value) url += `&customer_id=${customerFilter.value}`

    const res = await api.get(url)
    projects.value = res.data.data

    const meta = res.data.meta
    if (meta) {
      totalItems.value = meta.total
      totalPages.value = meta.total_pages
    }
  } catch (error) {
    console.error(error)
    uiStore.addToast('프로젝트 목록 조회 실패', 'error')
  } finally {
    loading.value = false
  }
}

async function fetchActiveCustomers() {
  try {
    const res = await api.get('/customers?limit=100&status=ACTIVE')
    activeCustomers.value = res.data.data
  } catch (error) {
    console.error('Active customers fetch failed:', error)
  }
}

function getCustomerName(customerId: number) {
  const c = activeCustomers.value.find(item => item.id === customerId)
  return c ? c.name : `고객사(ID:${customerId})`
}

function toggleRow(id: number) {
  if (expandedRows.value.includes(id)) {
    expandedRows.value = expandedRows.value.filter(rId => rId !== id)
  } else {
    expandedRows.value.push(id)
  }
}

function handleSearch(val: string) {
  search.value = val
  page.value = 1
  fetchProjects()
}

function handlePageChange(newPage: number) {
  page.value = newPage
  fetchProjects()
}

function openCreateModal() {
  isEditMode.value = false
  currentEditId.value = null
  form.value = {
    po_number: '',
    name: '',
    customer_id: '',
    manager: '',
    phone: '',
    scheduled_date: '',
    location: '',
    status: 'WAITING'
  }
  isModalOpen.value = true
}

function openEditModal(item: any) {
  isEditMode.value = true
  currentEditId.value = item.id
  form.value = {
    po_number: item.po_number,
    name: item.name,
    customer_id: item.customer_id,
    manager: item.manager || '',
    phone: item.phone || '',
    scheduled_date: item.scheduled_date || '',
    location: item.location || '',
    status: item.status
  }
  isModalOpen.value = true
}

function closeModal() {
  isModalOpen.value = false
}

async function submitForm() {
  if (!form.value.customer_id) {
    uiStore.addToast('고객사를 선택해 주세요.', 'warning')
    return
  }
  submitLoading.value = true
  try {
    const payload = { ...form.value }
    if (!payload.scheduled_date) delete payload.scheduled_date

    if (isEditMode.value && currentEditId.value) {
      await api.patch(`/projects/${currentEditId.value}`, payload)
      uiStore.addToast('프로젝트 정보가 수정되었습니다.', 'success')
    } else {
      await api.post('/projects', payload)
      uiStore.addToast('새 프로젝트가 등록되었습니다.', 'success')
    }
    closeModal()
    fetchProjects()
  } catch (error: any) {
    console.error(error)
    const errDetail = error.response?.data?.detail || '요청 처리 실패'
    uiStore.addToast(errDetail, 'error')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(id: number) {
  if (!confirm('정말로 이 프로젝트를 삭제하시겠습니까? (Soft Delete)')) return
  try {
    await api.delete(`/projects/${id}`)
    uiStore.addToast('프로젝트가 안전하게 삭제되었습니다.', 'success')
    fetchProjects()
  } catch (error) {
    console.error(error)
    uiStore.addToast('프로젝트 삭제 실패', 'error')
  }
}
</script>
