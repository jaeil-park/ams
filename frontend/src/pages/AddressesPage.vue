<template>
  <div class="space-y-6 font-sans">
    <!-- Header Page Banner -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">납품주소 관리</h1>
        <p class="text-xs text-slate-400 mt-1">고객사별 납품 거점 정보</p>
      </div>
      <AppButton variant="primary" class="text-xs" @click="openCreateModal">
        <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        신규 주소 등록
      </AppButton>
    </div>

    <!-- Filter bar -->
    <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4 select-none">
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400 font-semibold">고객사 필터:</span>
        <select 
          v-model="customerFilter" 
          class="text-xs font-semibold bg-white border border-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 max-w-[180px]"
          @change="fetchAddresses"
        >
          <option value="">전체 고객사</option>
          <option v-for="c in activeCustomers" :key="c.id" :value="c.id">
            {{ c.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Main Table -->
    <AppTable :columns="columns" :items="addresses" :loading="loading">
      <template #customer_id="{ item }">
        <span class="font-semibold text-slate-700">
          {{ getCustomerName(item.customer_id) }}
        </span>
      </template>
      <template #actions="{ item }">
        <div class="flex items-center gap-2">
          <AppButton variant="secondary" class="px-2 py-1 text-2xs" @click="openEditModal(item)">수정</AppButton>
          <AppButton variant="danger" class="px-2 py-1 text-2xs" @click="handleDelete(item.id)">삭제</AppButton>
        </div>
      </template>
    </AppTable>

    <!-- Create/Edit Modal -->
    <AppModal 
      :is-open="isModalOpen" 
      :title="isEditMode ? '납품 주소 수정' : '신규 납품 주소 등록'" 
      size="md" 
      @close="closeModal"
    >
      <form class="space-y-4 text-xs font-sans" @submit.prevent="submitForm">
        <!-- Customer selection -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">고객사 선택 *</label>
          <select 
            required 
            v-model="form.customer_id"
            :disabled="isEditMode"
            class="block w-full px-3 py-2 border border-slate-300 rounded-md bg-white text-slate-900 focus:outline-none"
          >
            <option value="" disabled>고객사를 지정하세요</option>
            <option v-for="c in activeCustomers" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <!-- Location / Hub name -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">거점명 (Location) *</label>
          <input type="text" required v-model="form.location" placeholder="예: 평촌 IDC, 수원 연구소" class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none" />
        </div>
        <!-- Address -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">상세 주소 *</label>
          <input type="text" required v-model="form.address" placeholder="예: 경기도 안양시 동안구 시민대로 123" class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none" />
        </div>
        <!-- Memo -->
        <div>
          <label class="block font-semibold text-slate-500 mb-1">메모 (선택)</label>
          <input type="text" v-model="form.memo" placeholder="비고 정보" class="block w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none" />
        </div>
      </form>
      <template #footer>
        <AppButton variant="secondary" @click="closeModal">취소</AppButton>
        <AppButton variant="primary" :loading="submitLoading" @click="submitForm">확인</AppButton>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import AppButton from '@/components/common/AppButton.vue'
import AppTable from '@/components/common/AppTable.vue'
import type { ColumnDefinition } from '@/components/common/AppTable.vue'
import AppModal from '@/components/common/AppModal.vue'

const uiStore = useUiStore()

const addresses = ref<any[]>([])
const activeCustomers = ref<any[]>([])
const loading = ref(false)
const submitLoading = ref(false)

const customerFilter = ref('')

const columns: ColumnDefinition[] = [
  { key: 'customer_id', label: '고객사' },
  { key: 'location', label: '거점명 (Location)' },
  { key: 'address', label: '상세 주소' },
  { key: 'memo', label: '메모' },
  { key: 'actions', label: '관리' }
]

const isModalOpen = ref(false)
const isEditMode = ref(false)
const currentEditId = ref<number | null>(null)
const form = ref<any>({
  customer_id: '',
  location: '',
  address: '',
  memo: ''
})

onMounted(() => {
  fetchAddresses()
  fetchActiveCustomers()
})

async function fetchAddresses() {
  loading.value = true
  try {
    let url = '/addresses'
    if (customerFilter.value) {
      url += `?customer_id=${customerFilter.value}`
    }
    const res = await api.get(url)
    addresses.value = res.data.data
  } catch (error) {
    console.error(error)
    uiStore.addToast('납품 주소록 조회 실패', 'error')
  } finally {
    loading.value = false
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

function getCustomerName(id: number) {
  const c = activeCustomers.value.find(item => item.id === id)
  return c ? c.name : `고객사(ID:${id})`
}

function openCreateModal() {
  isEditMode.value = false
  currentEditId.value = null
  form.value = {
    customer_id: '',
    location: '',
    address: '',
    memo: ''
  }
  isModalOpen.value = true
}

function openEditModal(item: any) {
  isEditMode.value = true
  currentEditId.value = item.id
  form.value = {
    customer_id: item.customer_id,
    location: item.location,
    address: item.address,
    memo: item.memo || ''
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
    if (isEditMode.value && currentEditId.value) {
      await api.patch(`/addresses/${currentEditId.value}`, form.value)
      uiStore.addToast('납품 주소가 정상 수정되었습니다.', 'success')
    } else {
      await api.post('/addresses', form.value)
      uiStore.addToast('신규 주소가 정상 추가되었습니다.', 'success')
    }
    closeModal()
    fetchAddresses()
  } catch (error) {
    console.error(error)
    uiStore.addToast('요청 처리 실패', 'error')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(id: number) {
  if (!confirm('정말로 이 납품 주소를 삭제하시겠습니까?')) return
  try {
    await api.delete(`/addresses/${id}`)
    uiStore.addToast('납품 주소가 리스트에서 삭제되었습니다.', 'success')
    fetchAddresses()
  } catch (error) {
    console.error(error)
    uiStore.addToast('삭제 실패', 'error')
  }
}
</script>
