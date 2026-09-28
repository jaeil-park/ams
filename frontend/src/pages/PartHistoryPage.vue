<template>
  <div class="space-y-6 font-sans">
    <!-- Header -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">파트이력</h1>
        <p class="text-xs text-slate-400 mt-1">부품(파트) 출고 및 사용 히스토리</p>
      </div>
    </div>

    <!-- 요약 -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 select-none">
      <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
        <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">출고 건수</span>
        <h3 class="text-xl font-black text-slate-800 mt-1">{{ total }} 건</h3>
      </div>
      <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
        <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">조회된 출고 수량</span>
        <h3 class="text-xl font-black text-slate-800 mt-1">{{ pageQtySum }} 개</h3>
        <span class="text-4xs text-slate-400">현재 페이지 기준</span>
      </div>
    </div>

    <!-- 필터 -->
    <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4 select-none">
      <div class="w-full sm:max-w-xs">
        <AppSearch v-model="search" placeholder="파트명, 파트넘버, PO, 고객사 검색..." @search="handleSearch" />
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400 font-semibold">기간:</span>
        <input v-model="dateFrom" type="date" class="text-xs border border-slate-300 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500" />
        <span class="text-slate-400">~</span>
        <input v-model="dateTo" type="date" class="text-xs border border-slate-300 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500" />
        <AppButton variant="primary" class="text-xs px-3 py-1.5" @click="handleSearch(search)">조회</AppButton>
        <AppButton variant="secondary" class="text-xs px-3 py-1.5" @click="resetFilters">초기화</AppButton>
      </div>
    </div>

    <!-- 이력 테이블 -->
    <div class="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50 select-none">
            <tr>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs w-28">출고일자</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">파트</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs w-24">구분</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs w-20">수량</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">고객사</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">PO / PR</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">납품 위치</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-500 uppercase tracking-wider text-xs">사유</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="loading">
              <td colspan="8" class="px-4 py-12 text-center text-slate-400">데이터를 불러오는 중...</td>
            </tr>
            <tr v-else-if="!usages.length">
              <td colspan="8" class="px-4 py-12 text-center text-slate-400 font-medium">
                조회된 파트 출고 이력이 없습니다.
              </td>
            </tr>
            <tr v-for="item in usages" :key="item.id" class="hover:bg-slate-50 transition-colors">
              <td class="px-4 py-3 font-mono text-slate-500">{{ item.used_date }}</td>
              <td class="px-4 py-3">
                <button
                  type="button"
                  class="font-semibold text-blue-600 hover:underline text-left"
                  title="파트재고에서 이 파트를 조회합니다"
                  @click="goToPart(item)"
                >
                  {{ item.part_model }}
                </button>
                <div v-if="item.part_number" class="text-3xs font-mono text-slate-400">{{ item.part_number }}</div>
              </td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded-full text-3xs font-bold bg-slate-100 text-slate-600">
                  {{ item.category || '미분류' }}
                </span>
              </td>
              <td class="px-4 py-3 font-bold text-slate-800">{{ item.qty }} 개</td>
              <td class="px-4 py-3 text-slate-600 font-medium">{{ item.customer_name || '-' }}</td>
              <td class="px-4 py-3 font-mono text-slate-500">{{ item.po_number || '-' }}</td>
              <td class="px-4 py-3 text-slate-500">{{ item.location || '-' }}</td>
              <td class="px-4 py-3 text-slate-500">{{ item.reason || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p class="text-3xs text-slate-400 select-none">
      관리자 승인이 완료된 출고 건만 기록됩니다. 승인 대기 중인 건은 승인 관리 화면에서 확인하세요.
    </p>

    <AppPagination
      :current-page="page"
      :total-pages="totalPages"
      :total-items="total"
      :limit="limit"
      @page-change="handlePageChange"
      @limit-change="handleLimitChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'
import { useUiStore } from '@/stores/ui'
import AppButton from '@/components/common/AppButton.vue'
import AppSearch from '@/components/common/AppSearch.vue'
import AppPagination from '@/components/common/AppPagination.vue'

const router = useRouter()
const uiStore = useUiStore()

const usages = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const page = ref(1)
const limit = ref(30)
const total = ref(0)
const totalPages = ref(1)

const pageQtySum = computed(() => usages.value.reduce((sum, u) => sum + (u.qty || 0), 0))

onMounted(() => {
  fetchHistory()
})

async function fetchHistory() {
  loading.value = true
  try {
    const params: any = { page: page.value, limit: limit.value }
    if (search.value) params.search = search.value
    if (dateFrom.value) params.date_from = dateFrom.value
    if (dateTo.value) params.date_to = dateTo.value

    const res = await api.get('/parts/usage-history', { params })
    usages.value = res.data.data || []
    total.value = res.data.meta?.total || 0
    totalPages.value = res.data.meta?.total_pages || 1
  } catch (error) {
    console.error(error)
    uiStore.addToast('파트 이력 조회 실패', 'error')
  } finally {
    loading.value = false
  }
}

function handleSearch(val: string) {
  search.value = val
  page.value = 1
  fetchHistory()
}

function resetFilters() {
  search.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  page.value = 1
  fetchHistory()
}

function handlePageChange(newPage: number) {
  page.value = newPage
  fetchHistory()
}

function handleLimitChange(newLimit: number) {
  limit.value = newLimit
  page.value = 1
  fetchHistory()
}

function goToPart(item: any) {
  router.push({ name: 'parts', query: { search: item.part_number || item.part_model } })
}
</script>
