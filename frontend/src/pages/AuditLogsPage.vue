<template>
  <div class="p-6 space-y-6">
    <!-- 페이지 헤더 -->
    <div>
      <h1 class="text-xl font-bold text-slate-900">감사 로그</h1>
      <p class="text-xs text-slate-500 mt-0.5">모든 자산 변경 이력을 추적합니다 (ADMIN 전용)</p>
    </div>

    <!-- 필터 바 -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap gap-3 items-center shadow-sm">
      <select
        v-model="filters.resource_type"
        class="border border-slate-300 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">전체 자원</option>
        <option value="CUSTOMER">고객사</option>
        <option value="SERVER">서버</option>
        <option value="SERVER_BULK">서버(일괄)</option>
        <option value="PROJECT">프로젝트</option>
        <option value="PART">파트</option>
      </select>

      <select
        v-model="filters.action"
        class="border border-slate-300 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">전체 작업</option>
        <option value="CREATE">등록</option>
        <option value="UPDATE">수정</option>
        <option value="DELETE">삭제</option>
      </select>

      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-500 font-medium">기간:</span>
        <input
          v-model="filters.date_from"
          type="date"
          class="border border-slate-300 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <span class="text-slate-400">~</span>
        <input
          v-model="filters.date_to"
          type="date"
          class="border border-slate-300 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <button
        type="button"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-700 transition-colors"
        @click="fetchLogs"
      >
        조회
      </button>
      <button
        type="button"
        class="px-3 py-2 text-slate-500 border border-slate-300 rounded-lg text-xs font-medium hover:bg-slate-50 transition-colors"
        @click="resetFilters"
      >
        초기화
      </button>

      <span class="ml-auto text-xs text-slate-400">총 {{ total }}건</span>
    </div>

    <!-- 감사 로그 테이블 -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full text-xs">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider w-32">일시</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider w-16">작업</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider w-24">자원 타입</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider w-16">자원 ID</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">변경 전</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">변경 후</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="loading">
              <td colspan="6" class="px-4 py-10 text-center text-slate-400">
                <div class="flex justify-center">
                  <svg class="animate-spin h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                </div>
              </td>
            </tr>
            <tr v-else-if="!logs.length">
              <td colspan="6" class="px-4 py-10 text-center text-slate-400 font-medium">
                조건에 해당하는 감사 로그가 없습니다.
              </td>
            </tr>
            <tr
              v-for="log in logs"
              :key="log.id"
              class="hover:bg-slate-50 transition-colors group"
            >
              <td class="px-4 py-3 text-slate-500 whitespace-nowrap">{{ formatDate(log.created_at) }}</td>
              <td class="px-4 py-3">
                <span
                  class="px-2 py-0.5 rounded-full font-bold text-3xs uppercase tracking-wider"
                  :class="actionBadge(log.action)"
                >
                  {{ actionLabel(log.action) }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span class="font-semibold text-slate-700">{{ log.resource_type }}</span>
              </td>
              <td class="px-4 py-3 font-mono text-slate-500">
                {{ log.resource_id ?? '—' }}
              </td>
              <td class="px-4 py-3 max-w-xs">
                <pre
                  v-if="log.before"
                  class="text-red-600 bg-red-50 rounded p-1.5 text-3xs font-mono whitespace-pre-wrap max-h-16 overflow-y-auto"
                >{{ JSON.stringify(log.before, null, 2) }}</pre>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="px-4 py-3 max-w-xs">
                <pre
                  v-if="log.after"
                  class="text-emerald-700 bg-emerald-50 rounded p-1.5 text-3xs font-mono whitespace-pre-wrap max-h-16 overflow-y-auto"
                >{{ JSON.stringify(log.after, null, 2) }}</pre>
                <span v-else class="text-slate-300">—</span>
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
      :total-items="total"
      :limit="30"
      @page-change="onPageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/utils/api'
import AppPagination from '@/components/common/AppPagination.vue'

const logs = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const total = ref(0)

const filters = ref({
  resource_type: '',
  action: '',
  date_from: '',
  date_to: '',
})

onMounted(() => {
  fetchLogs()
})

async function fetchLogs() {
  loading.value = true
  try {
    const params: any = { page: currentPage.value, limit: 30 }
    if (filters.value.resource_type) params.resource_type = filters.value.resource_type
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.date_from) params.date_from = filters.value.date_from
    if (filters.value.date_to) params.date_to = filters.value.date_to

    const res = await api.get('/audit-logs', { params })
    logs.value = res.data.data || []
    totalPages.value = res.data.meta?.total_pages || 1
    total.value = res.data.meta?.total || 0
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = { resource_type: '', action: '', date_from: '', date_to: '' }
  currentPage.value = 1
  fetchLogs()
}

function onPageChange(page: number) {
  currentPage.value = page
  fetchLogs()
}

function actionBadge(action: string) {
  if (action === 'CREATE') return 'bg-emerald-100 text-emerald-700'
  if (action === 'UPDATE') return 'bg-blue-100 text-blue-700'
  if (action === 'DELETE') return 'bg-red-100 text-red-600'
  return 'bg-slate-100 text-slate-600'
}

function actionLabel(action: string) {
  const map: Record<string, string> = { CREATE: '등록', UPDATE: '수정', DELETE: '삭제' }
  return map[action] || action
}

function formatDate(d: string) {
  if (!d) return '-'
  return new Date(d).toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}
</script>
