<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import { Plus, Edit2, ShieldAlert, KeyRound, ShieldCheck, Mail, User as UserIcon } from '@lucide/vue'

import AppTable from '@/components/common/AppTable.vue'
import AppButton from '@/components/common/AppButton.vue'
import AppModal from '@/components/common/AppModal.vue'
import AppBadge from '@/components/common/AppBadge.vue'

interface User {
  id: number
  email: string
  name: string
  role: string
  is_active: boolean
}

const uiStore = useUiStore()

const loading = ref(true)
const users = ref<User[]>([])

// Data Fetching
const fetchUsers = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/users')
    users.value = data.data
  } catch (error) {
    uiStore.addToast('사용자 목록을 불러오는데 실패했습니다.', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchUsers()
})

// Modal State
const showModal = ref(false)
const modalType = ref<'create' | 'edit'>('create')
const formData = ref({
  id: 0,
  email: '',
  name: '',
  role: 'USER',
  password: '',
  is_active: true
})

const openCreateModal = () => {
  modalType.value = 'create'
  formData.value = {
    id: 0,
    email: '',
    name: '',
    role: 'USER',
    password: '',
    is_active: true
  }
  showModal.value = true
}

const openEditModal = (user: User) => {
  modalType.value = 'edit'
  formData.value = {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    password: '', // Edit mode: leave empty unless changing
    is_active: user.is_active
  }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}

// Submitting Form
const saving = ref(false)
const submitForm = async () => {
  saving.value = true
  try {
    if (modalType.value === 'create') {
      if (!formData.value.password) {
        uiStore.addToast('초기 비밀번호를 입력해주세요.', 'warning')
        saving.value = false
        return
      }
      await api.post('/users', formData.value)
      uiStore.addToast('사용자가 성공적으로 생성되었습니다.', 'success')
    } else {
      const payload: any = {
        name: formData.value.name,
        role: formData.value.role,
        is_active: formData.value.is_active
      }
      if (formData.value.password) {
        payload.password = formData.value.password
      }
      await api.patch(`/users/${formData.value.id}`, payload)
      uiStore.addToast('사용자 정보가 수정되었습니다.', 'success')
    }
    closeModal()
    fetchUsers()
  } catch (error: any) {
    if (error.response?.status === 400 && error.response?.data?.detail) {
      uiStore.addToast(error.response.data.detail, 'error')
    } else {
      uiStore.addToast('작업에 실패했습니다.', 'error')
    }
  } finally {
    saving.value = false
  }
}

// Delete (Deactivate)
const confirmDeactivate = async (user: User) => {
  if (confirm(`'${user.name}' 사용자를 비활성화하시겠습니까?`)) {
    try {
      await api.delete(`/users/${user.id}`)
      uiStore.addToast('사용자가 비활성화되었습니다.', 'success')
      fetchUsers()
    } catch (error: any) {
      if (error.response?.status === 400) {
        uiStore.addToast(error.response.data.detail, 'error')
      } else {
        uiStore.addToast('비활성화 처리에 실패했습니다.', 'error')
      }
    }
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 tracking-tight">사용자 관리</h1>
        <p class="mt-1 text-sm text-gray-500">시스템 접근이 가능한 계정을 생성하고 권한을 관리합니다.</p>
      </div>
      <div class="flex items-center gap-3">
        <AppButton @click="openCreateModal">
          <Plus class="w-4 h-4 mr-2" />
          계정 생성
        </AppButton>
      </div>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <AppTable
        :items="users"
        :columns="[
          { key: 'email', label: '이메일 계정' },
          { key: 'name', label: '이름' },
          { key: 'role', label: '권한' },
          { key: 'is_active', label: '상태' },
          { key: 'actions', label: '' }
        ]"
        :loading="loading"
      >
        <!-- Cell: Email -->
        <template #email="{ item }">
          <div class="flex items-center text-gray-900 font-medium">
            <Mail class="w-4 h-4 mr-2 text-gray-400" />
            {{ item.email }}
          </div>
        </template>
        
        <!-- Cell: Name -->
        <template #name="{ item }">
          <div class="flex items-center text-gray-600">
            <UserIcon class="w-4 h-4 mr-2 text-gray-400" />
            {{ item.name }}
          </div>
        </template>

        <!-- Cell: Role -->
        <template #role="{ item }">
          <div class="flex items-center gap-1.5" :class="item.role === 'ADMIN' ? 'text-indigo-600 font-medium' : 'text-gray-600'">
            <ShieldCheck v-if="item.role === 'ADMIN'" class="w-4 h-4" />
            <span v-else class="w-4 h-4 rounded-full bg-gray-100 flex items-center justify-center text-[10px] text-gray-500 font-bold">U</span>
            {{ item.role === 'ADMIN' ? '관리자' : '일반 사용자' }}
          </div>
        </template>

        <!-- Cell: Status -->
        <template #is_active="{ item }">
          <AppBadge :status="item.is_active ? 'ACTIVE' : 'INACTIVE'">
            {{ item.is_active ? '활성' : '비활성' }}
          </AppBadge>
        </template>

        <!-- Cell: Actions -->
        <template #actions="{ item }">
          <div class="flex items-center justify-end gap-2">
            <AppButton variant="ghost" size="sm" @click="openEditModal(item)">
              <Edit2 class="w-4 h-4" />
            </AppButton>
            <AppButton v-if="item.is_active" variant="ghost" size="sm" class="text-red-600 hover:text-red-700 hover:bg-red-50" @click="confirmDeactivate(item)">
              <ShieldAlert class="w-4 h-4" />
            </AppButton>
          </div>
        </template>
      </AppTable>
    </div>

    <!-- Create/Edit Modal -->
    <AppModal
      :is-open="showModal"
      :title="modalType === 'create' ? '새 계정 생성' : '계정 정보 수정'"
      @close="closeModal"
    >
      <form @submit.prevent="submitForm" class="space-y-4">
        <!-- Email -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">이메일 주소</label>
          <input
            v-model="formData.email"
            type="email"
            required
            :disabled="modalType === 'edit'"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
            placeholder="user@ams.dev"
          />
          <p v-if="modalType === 'edit'" class="mt-1 text-xs text-gray-500">이메일은 수정할 수 없습니다.</p>
        </div>

        <!-- Name -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">이름</label>
          <input
            v-model="formData.name"
            type="text"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="홍길동"
          />
        </div>

        <!-- Password -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            비밀번호
            <span v-if="modalType === 'edit'" class="text-gray-400 font-normal">(변경할 경우에만 입력)</span>
          </label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <KeyRound class="h-4 w-4 text-gray-400" />
            </div>
            <input
              v-model="formData.password"
              type="password"
              :required="modalType === 'create'"
              class="w-full pl-10 px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="••••••••"
            />
          </div>
        </div>

        <!-- Role & Status (Side by side) -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">시스템 권한</label>
            <select
              v-model="formData.role"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            >
              <option value="USER">일반 사용자 (USER)</option>
              <option value="ADMIN">관리자 (ADMIN)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">계정 상태</label>
            <select
              v-model="formData.is_active"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            >
              <option :value="true">활성 상태 (로그인 가능)</option>
              <option :value="false">비활성 상태 (로그인 차단)</option>
            </select>
          </div>
        </div>

        <!-- Actions -->
        <div class="pt-4 flex justify-end gap-3 border-t border-gray-100 mt-6">
          <AppButton type="button" variant="secondary" @click="closeModal" :disabled="saving">
            취소
          </AppButton>
          <AppButton type="submit" :loading="saving">
            {{ modalType === 'create' ? '계정 생성' : '저장' }}
          </AppButton>
        </div>
      </form>
    </AppModal>
  </div>
</template>
