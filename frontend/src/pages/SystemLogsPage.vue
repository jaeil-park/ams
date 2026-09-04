<template>
  <div class="p-6 space-y-6">
    <!-- 페이지 헤더 -->
    <div>
      <h1 class="text-2xl font-bold text-slate-900">시스템 로그</h1>
      <p class="text-sm text-slate-500 mt-1">
        API 요청 처리 중 발생한 오류/실패를 자동 기록합니다 (ADMIN 전용). 정상적인 업무 검증 실패(중복 코드, 재고 부족 등)는 기록되지 않습니다.
      </p>
    </div>

    <!-- 필터 바 -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap gap-3 items-center shadow-sm">
      <select
        v-model="filters.level"
        class="border border-slate-300 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">전체 레벨</option>
        <option value="ERROR">ERROR</option>
        <option value="WARNING">WARNING</option>
      </select>

      <div class="flex items-center gap-2">
        <span class="text-sm text-slate-500 font-medium">기간:</span>
        <input v-model="filters.date_from" type="date" class="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        <span class="text-slate-400">~</span>
        <input v-model="filters.date_to" type="date" class="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
      </div>

      <button type="button" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-colors" @click="fetchLogs">조회</button>
      <button type="button" class="px-3 py-2 text-slate-500 border border-slate-300 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors" @click="resetFilters">초기화</button>

      <span class="ml-auto text-sm text-slate-400">총 {{ total }}건</span>
    </div>

    <!-- 시스템 로그 테이블 -->
    <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider w-40">일시</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider w-24">레벨</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider w-24">상태코드</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">요청</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider w-40">사용자</th>
              <th class="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">메시지</th>
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
                조건에 해당하는 시스템 로그가 없습니다.
              </td>
            </tr>
            <template v-for="log in logs" :key="log.id">
              <tr
                class="hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0 cursor-pointer"
                @click="toggleExpand(log.id)"
              >
                <td class="px-4 py-3 text-slate-500 whitespace-nowrap">{{ formatDate(log.created_at) }}</td>
                <td class="px-4 py-3">
                  <span class="px-2.5 py-1 rounded-full font-bold text-xs uppercase tracking-wider" :class="levelBadge(log.level)">
                    {{ log.level }}
                  </span>
                </td>
                <td class="px-4 py-3 font-mono font-bold text-slate-600">{{ log.status_code }}</td>
                <td class="px-4 py-3 font-mono text-slate-700">
                  <span class="font-bold text-slate-500">{{ log.method }}</span> {{ log.path }}
                </td>
                <td class="px-4 py-3 text-slate-500">{{ log.user_email || '-' }}</td>
                <td class="px-4 py-3 text-slate-600 max-w-md truncate">{{ log.message || '-' }}</td>
              </tr>
              <tr v-if="expandedId === log.id && log.detail" class="bg-slate-50">
                <td colspan="6" class="px-4 py-3">
                  <pre class="text-xs text-slate-600 whitespace-pre-wrap font-mono bg-white border border-slate-200 rounded p-3 max-h-80 overflow-y-auto">{{ log.detail }}</pre>
                </td>
              </tr>
            </template>
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
const expandedId = ref<number | null>(null)

const today = new Date().toISOString().substring(0, 10)

const filters = ref({
  level: '',
  date_from: today,
  date_to: today,
})

onMounted(() => {
  fetchLogs()
})

async function fetchLogs() {
  loading.value = true
  try {
    const params: any = { page: currentPage.value, limit: 30 }
    if (filters.value.level) params.level = filters.value.level
    if (filters.value.date_from) params.date_from = filters.value.date_from
    if (filters.value.date_to) params.date_to = filters.value.date_to

    const res = await api.get('/system-logs', { params })
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
  filters.value = { level: '', date_from: today, date_to: today }
  currentPage.value = 1
  fetchLogs()
}

function onPageChange(page: number) {
  currentPage.value = page
  fetchLogs()
}

function toggleExpand(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

function levelBadge(level: string) {
  if (level === 'ERROR') return 'bg-red-100 text-red-600'
  if (level === 'WARNING') return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-600'
}

function formatDate(d: string) {
  if (!d) return '-'
  return new Date(d).toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}
</script>
