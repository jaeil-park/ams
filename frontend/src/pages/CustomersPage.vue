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
        <!-- Code (server-assigned) -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">고객사 코드</label>
          <input
            type="text"
            disabled
            :value="isEditMode ? form.code : '등록 시 자동 배정됩니다'"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-slate-50 text-slate-400 focus:outline-none"
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
        <!-- Main Manager (dropdown from registered contacts when available, free text otherwise) -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">메인 담당자</label>
          <select
            v-if="isEditMode && contacts.length > 0"
            v-model="selectedMainContactId"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="onMainContactSelect"
          >
            <option value="">직접 입력</option>
            <option v-for="c in contacts" :key="c.id" :value="c.id">
              {{ c.name }} ({{ c.phone || '연락처 없음' }})
            </option>
          </select>
          <p v-if="isEditMode && contacts.length > 0" class="text-3xs text-slate-400 mt-1 mb-2">
            아래 "담당자 관리" 목록에 없는 새 담당자는 목록에 먼저 추가한 뒤 여기서 선택하세요.
          </p>
        </div>
        <!-- Manager Name -->
        <div>
          <label class="block text-xs font-semibold text-slate-500 mb-1">담당자 성함</label>
          <input
            type="text"
            v-model="form.manager"
            placeholder="홍길동"
            class="block w-full px-3 py-2 text-sm border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @input="selectedMainContactId = ''"
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
            @input="selectedMainContactId = ''"
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

      <!-- Contacts Management (edit mode only — requires an existing customer_id) -->
      <div v-if="isEditMode" class="mt-6 pt-4 border-t border-slate-200">
        <label class="block text-xs font-semibold text-slate-500 mb-2">담당자 관리</label>

        <div v-if="contacts.length === 0" class="text-xs text-slate-400 mb-3">
          등록된 담당자가 없습니다.
        </div>
        <ul v-else class="space-y-2 mb-3">
          <li
            v-for="c in contacts"
            :key="c.id"
            class="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-md px-3 py-2"
          >
            <div class="flex-1 grid grid-cols-3 gap-2">
              <span class="text-sm font-semibold text-slate-700 truncate">{{ c.name }}</span>
              <span class="text-xs text-slate-500 font-mono truncate">{{ c.phone || '-' }}</span>
              <span class="text-xs text-slate-500 truncate">{{ c.email || '-' }}</span>
            </div>
            <button
              type="button"
              class="text-slate-400 hover:text-red-600 transition-colors shrink-0"
              title="담당자 삭제"
              @click="deleteContact(c.id)"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
            </button>
          </li>
        </ul>

        <div class="grid grid-cols-3 gap-2">
          <input
            type="text"
            v-model="newContact.name"
            placeholder="담당자명"
            class="px-2.5 py-1.5 text-xs border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            type="text"
            v-model="newContact.phone"
            placeholder="연락처"
            class="px-2.5 py-1.5 text-xs border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            type="email"
            v-model="newContact.email"
            placeholder="이메일"
            class="px-2.5 py-1.5 text-xs border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <AppButton variant="secondary" class="mt-2 px-2 py-1 text-2xs" @click="addContact">+ 담당자 추가</AppButton>
      </div>

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
  contacts.value = []
  newContact.value = { name: '', phone: '', email: '' }
  selectedMainContactId.value = ''
  isModalOpen.value = true
}

async function openEditModal(item: any) {
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
  await fetchContacts(item.id)
  const matched = contacts.value.find(c => c.name === item.manager)
  selectedMainContactId.value = matched ? matched.id : ''
}

function closeModal() {
  isModalOpen.value = false
}

// Contacts (per-customer) management
const contacts = ref<any[]>([])
const newContact = ref({ name: '', phone: '', email: '' })
const selectedMainContactId = ref<number | ''>('')

function onMainContactSelect() {
  if (!selectedMainContactId.value) return
  const contact = contacts.value.find(c => c.id === selectedMainContactId.value)
  if (contact) {
    form.value.manager = contact.name
    form.value.phone = contact.phone || ''
  }
}

async function fetchContacts(customerId: number) {
  try {
    const res = await api.get('/contacts', { params: { customer_id: customerId } })
    contacts.value = res.data.data
  } catch (error) {
    console.error('담당자 목록 조회 실패:', error)
  }
}

async function addContact() {
  if (!currentEditId.value) return
  if (!newContact.value.name.trim()) {
    uiStore.addToast('담당자명을 입력해 주세요.', 'warning')
    return
  }
  try {
    await api.post('/contacts', { customer_id: currentEditId.value, ...newContact.value })
    newContact.value = { name: '', phone: '', email: '' }
    fetchContacts(currentEditId.value)
  } catch (error) {
    console.error(error)
    uiStore.addToast('담당자 추가 실패', 'error')
  }
}

async function deleteContact(id: number) {
  if (!confirm('이 담당자를 삭제하시겠습니까?')) return
  try {
    await api.delete(`/contacts/${id}`)
    if (currentEditId.value) fetchContacts(currentEditId.value)
  } catch (error) {
    console.error(error)
    uiStore.addToast('담당자 삭제 실패', 'error')
  }
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
