<template>
  <div class="p-6 space-y-6">
    <!-- 페이지 헤더 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-slate-900">승인 관리</h1>
        <p class="text-xs text-slate-500 mt-0.5">파트 수량 수정 및 기타 변경 요청 처리</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- 상태 필터 -->
        <select
          v-model="statusFilter"
          class="border border-slate-300 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="fetchApprovals"
        >
          <option value="">전체</option>
          <option value="PENDING">대기 중</option>
          <option value="APPROVED">승인됨</option>
          <option value="REJECTED">반려됨</option>
        </select>
      </div>
    </div>

    <!-- 통계 카드 -->
    <div class="grid grid-cols-3 gap-4">
      <div class="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <p class="text-xs font-semibold text-amber-600 uppercase tracking-wider">대기 중</p>
        <p class="text-2xl font-bold text-amber-700 mt-1">{{ stats.pending }}</p>
      </div>
      <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
        <p class="text-xs font-semibold text-emerald-600 uppercase tracking-wider">승인됨</p>
        <p class="text-2xl font-bold text-emerald-700 mt-1">{{ stats.approved }}</p>
      </div>
      <div class="bg-red-50 border border-red-200 rounded-xl p-4">
        <p class="text-xs font-semibold text-red-500 uppercase tracking-wider">반려됨</p>
        <p class="text-2xl font-bold text-red-600 mt-1">{{ stats.rejected }}</p>
      </div>
    </div>

    <!-- 승인 목록 테이블 -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full text-xs">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">ID</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">자원 타입</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">요청 내용</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">상태</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">요청일시</th>
              <th class="px-4 py-3 text-center font-bold text-slate-500 uppercase tracking-wider">처리</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="loading">
              <td colspan="6" class="px-4 py-8 text-center text-slate-400">
                <div class="flex justify-center">
                  <svg class="animate-spin h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                </div>
              </td>
            </tr>
            <tr v-else-if="!approvals.length">
              <td colspan="6" class="px-4 py-10 text-center text-slate-400 font-medium">
                승인 요청 내역이 없습니다.
              </td>
            </tr>
            <tr
              v-for="item in approvals"
              :key="item.id"
              class="hover:bg-slate-50 transition-colors"
            >
              <td class="px-4 py-3 font-mono text-slate-500">#{{ item.id }}</td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider"
                  :class="resourceTypeBadge(item.resource_type)">
                  {{ item.resource_type }}
                </span>
              </td>
              <td class="px-4 py-3 text-slate-700 max-w-xs">
                <div class="font-semibold">자원 ID: {{ item.resource_id }}</div>
                <div class="text-slate-500 mt-0.5" v-if="item.payload">
                  <span v-if="item.payload.qty !== undefined">
                    수량 변경 → <span class="font-bold text-blue-600">{{ item.payload.qty }}개</span>
                  </span>
                </div>
                <div class="text-slate-400 mt-0.5" v-if="item.reason">사유: {{ item.reason }}</div>
              </td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider"
                  :class="statusClass(item.status)"
                >
                  <span class="h-1.5 w-1.5 rounded-full" :class="statusDot(item.status)" />
                  {{ statusLabel(item.status) }}
                </span>
              </td>
              <td class="px-4 py-3 text-slate-500">
                {{ formatDate(item.created_at) }}
              </td>
              <td class="px-4 py-3">
                <div v-if="item.status === 'PENDING'" class="flex justify-center gap-2">
                  <button
                    type="button"
                    class="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-3xs font-bold hover:bg-emerald-700 transition-colors"
                    :disabled="processingId === item.id"
                    @click="handleApprove(item.id)"
                  >
                    승인
                  </button>
                  <button
                    type="button"
                    class="px-3 py-1.5 bg-red-500 text-white rounded-lg text-3xs font-bold hover:bg-red-600 transition-colors"
                    :disabled="processingId === item.id"
                    @click="openRejectModal(item)"
                  >
                    반려
                  </button>
                </div>
                <div v-else class="text-center text-slate-400 font-medium">—</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 페이지네이션 -->
    <AppPagination
      v-if="totalPages > 1"
      :current-page="currentPage"
      :total-pages="totalPages"
      :total-items="approvals.length"
      :limit="30"
      @page-change="onPageChange"
    />

    <!-- 반려 사유 입력 모달 -->
    <AppModal :is-open="rejectModalOpen" title="반려 사유 입력" size="sm" @close="rejectModalOpen = false">
      <div class="space-y-4">
        <p class="text-xs text-slate-600">
          <span class="font-bold text-slate-800">요청 #{{ rejectTarget?.id }}</span> 을 반려합니다.
        </p>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">반려 사유 <span class="text-red-400">(선택)</span></label>
          <textarea
            v-model="rejectReason"
            rows="3"
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-red-400 resize-none"
            placeholder="반려 사유를 입력하세요..."
          />
        </div>
        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="px-4 py-2 text-slate-600 text-xs font-semibold hover:bg-slate-100 rounded-lg transition-colors"
            @click="rejectModalOpen = false"
          >
            취소
          </button>
          <button
            type="button"
            class="px-4 py-2 bg-red-500 text-white text-xs font-bold rounded-lg hover:bg-red-600 transition-colors"
            @click="handleReject"
          >
            반려 확정
          </button>
        </div>
      </div>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import AppModal from '@/components/common/AppModal.vue'
import AppPagination from '@/components/common/AppPagination.vue'

const uiStore = useUiStore()

const approvals = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const statusFilter = ref('PENDING')
const processingId = ref<number | null>(null)

// 반려 모달
const rejectModalOpen = ref(false)
const rejectTarget = ref<any>(null)
const rejectReason = ref('')

// 통계
const stats = computed(() => ({
  pending: approvals.value.filter(a => a.status === 'PENDING').length,
  approved: approvals.value.filter(a => a.status === 'APPROVED').length,
  rejected: approvals.value.filter(a => a.status === 'REJECTED').length,
}))

onMounted(() => {
  fetchApprovals()
})

async function fetchApprovals() {
  loading.value = true
  try {
    const params: any = { page: currentPage.value, limit: 30 }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await api.get('/approvals', { params })
    approvals.value = res.data.data || []
    totalPages.value = res.data.meta?.total_pages || 1
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

async function handleApprove(id: number) {
  processingId.value = id
  try {
    await api.post(`/approvals/${id}/approve`)
    uiStore.addToast('승인 처리되었습니다.', 'success')
    fetchApprovals()
  } catch (err) {
    uiStore.addToast('승인 처리 실패', 'error')
  } finally {
    processingId.value = null
  }
}

function openRejectModal(item: any) {
  rejectTarget.value = item
  rejectReason.value = ''
  rejectModalOpen.value = true
}

async function handleReject() {
  if (!rejectTarget.value) return
  processingId.value = rejectTarget.value.id
  try {
    const params: any = {}
    if (rejectReason.value.trim()) params.reason = rejectReason.value.trim()
    await api.post(`/approvals/${rejectTarget.value.id}/reject`, null, { params })
    uiStore.addToast('반려 처리되었습니다.', 'success')
    rejectModalOpen.value = false
    fetchApprovals()
  } catch (err) {
    uiStore.addToast('반려 처리 실패', 'error')
  } finally {
    processingId.value = null
  }
}

function onPageChange(page: number) {
  currentPage.value = page
  fetchApprovals()
}

function resourceTypeBadge(type: string) {
  const map: Record<string, string> = {
    PART_QTY: 'bg-purple-100 text-purple-700',
    SERVER: 'bg-blue-100 text-blue-700',
    PROJECT: 'bg-emerald-100 text-emerald-700',
  }
  return map[type] || 'bg-slate-100 text-slate-600'
}

function statusClass(s: string) {
  if (s === 'PENDING') return 'bg-amber-100 text-amber-700'
  if (s === 'APPROVED') return 'bg-emerald-100 text-emerald-700'
  if (s === 'REJECTED') return 'bg-red-100 text-red-600'
  return 'bg-slate-100 text-slate-500'
}

function statusDot(s: string) {
  if (s === 'PENDING') return 'bg-amber-500 animate-pulse'
  if (s === 'APPROVED') return 'bg-emerald-500'
  if (s === 'REJECTED') return 'bg-red-500'
  return 'bg-slate-400'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { PENDING: '대기 중', APPROVED: '승인됨', REJECTED: '반려됨' }
  return map[s] || s
}

function formatDate(d: string) {
  if (!d) return '-'
  return new Date(d).toLocaleString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>
