<template>
  <div class="space-y-6 font-sans">
    <!-- Header Page Banner -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">종합 대시보드</h1>
        <p class="text-xs text-slate-400 mt-1">실시간 자산 및 납품 정보 요약</p>
      </div>
      <div class="text-xs text-slate-400 font-semibold bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm">
        기준일시: {{ nowString }}
      </div>
    </div>

    <!-- 1. KPI Cards Row -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Card 1: In Stock -->
      <div 
        class="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between cursor-pointer hover:border-blue-500 transition-all"
        @click="goTo('inventory', { status: 'IN_STOCK' })"
      >
        <div>
          <p class="text-4xs font-bold text-slate-400 uppercase tracking-wider">가용 재고 (서버)</p>
          <h3 class="text-2xl font-bold text-slate-800 mt-1">{{ kpi.in_stock_servers }} 대</h3>
        </div>
        <div class="h-10 w-10 rounded-md bg-emerald-50 text-emerald-600 flex items-center justify-center">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
        </div>
      </div>

      <!-- Card 2: WAITING projects -->
      <div 
        class="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between cursor-pointer hover:border-blue-500 transition-all"
        @click="goTo('projects', { status: 'WAITING' })"
      >
        <div>
          <p class="text-4xs font-bold text-slate-400 uppercase tracking-wider">대기 중 프로젝트</p>
          <h3 class="text-2xl font-bold text-slate-800 mt-1">{{ kpi.waiting_projects }} 건</h3>
        </div>
        <div class="h-10 w-10 rounded-md bg-amber-50 text-amber-600 flex items-center justify-center">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      </div>

      <!-- Card 3: IN_PROGRESS projects -->
      <div 
        class="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between cursor-pointer hover:border-blue-500 transition-all"
        @click="goTo('projects', { status: 'IN_PROGRESS' })"
      >
        <div>
          <p class="text-4xs font-bold text-slate-400 uppercase tracking-wider">진행 중 프로젝트</p>
          <h3 class="text-2xl font-bold text-slate-800 mt-1">{{ kpi.in_progress_projects }} 건</h3>
        </div>
        <div class="h-10 w-10 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
      </div>

      <!-- Card 4: COMPLETED projects -->
      <div 
        class="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between cursor-pointer hover:border-blue-500 transition-all"
        @click="goTo('projects', { status: 'COMPLETED' })"
      >
        <div>
          <p class="text-4xs font-bold text-slate-400 uppercase tracking-wider">납품 완료 프로젝트</p>
          <h3 class="text-2xl font-bold text-slate-800 mt-1">{{ kpi.completed_projects }} 건</h3>
        </div>
        <div class="h-10 w-10 rounded-md bg-indigo-50 text-indigo-600 flex items-center justify-center">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      </div>
    </div>

    <!-- 2. Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Chart: Customer Delivery Stacked Chart -->
      <div class="bg-white p-5 rounded-lg border border-slate-200 shadow-sm lg:col-span-2 flex flex-col min-h-[320px]">
        <h3 class="text-sm font-semibold text-slate-800 mb-4 select-none">고객사별 납품 현황 (서버 기준)</h3>
        
        <div v-if="customerDeliveries.length === 0" class="flex-1 flex items-center justify-center text-slate-400 text-xs select-none">
          데이터가 존재하지 않습니다.
        </div>
        
        <div v-else class="flex-1 space-y-4">
          <div v-for="item in customerDeliveries" :key="item.customer" class="space-y-1">
            <div class="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>{{ item.customer }}</span>
              <span>총 {{ getDeliveryTotal(item.statuses) }} 대</span>
            </div>
            <!-- Custom Stacked Bar -->
            <div class="h-5 w-full bg-slate-100 rounded overflow-hidden flex shadow-inner">
              <div 
                v-if="item.statuses.IN_STOCK"
                :style="{ width: getPercentage(item.statuses.IN_STOCK, item.statuses) + '%' }" 
                class="bg-emerald-500 hover:opacity-90 transition-opacity flex items-center justify-center text-3xs font-bold text-white"
                title="재고"
              >
                {{ item.statuses.IN_STOCK }}
              </div>
              <div 
                v-if="item.statuses.RESERVED"
                :style="{ width: getPercentage(item.statuses.RESERVED, item.statuses) + '%' }" 
                class="bg-amber-500 hover:opacity-90 transition-opacity flex items-center justify-center text-3xs font-bold text-white"
                title="예약"
              >
                {{ item.statuses.RESERVED }}
              </div>
              <div 
                v-if="item.statuses.DELIVERED"
                :style="{ width: getPercentage(item.statuses.DELIVERED, item.statuses) + '%' }" 
                class="bg-blue-500 hover:opacity-90 transition-opacity flex items-center justify-center text-3xs font-bold text-white"
                title="납품완료"
              >
                {{ item.statuses.DELIVERED }}
              </div>
              <div 
                v-if="item.statuses.RMA"
                :style="{ width: getPercentage(item.statuses.RMA, item.statuses) + '%' }" 
                class="bg-rose-500 hover:opacity-90 transition-opacity flex items-center justify-center text-3xs font-bold text-white"
                title="RMA"
              >
                {{ item.statuses.RMA }}
              </div>
            </div>
          </div>
          <!-- Legend -->
          <div class="flex flex-wrap gap-4 pt-3 border-t border-slate-100 text-3xs font-semibold text-slate-500 select-none">
            <div class="flex items-center gap-1.5">
              <span class="h-2.5 w-2.5 bg-emerald-500 rounded-sm"></span>
              <span>재고 (IN_STOCK)</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-2.5 w-2.5 bg-amber-500 rounded-sm"></span>
              <span>예약 (RESERVED)</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-2.5 w-2.5 bg-blue-500 rounded-sm"></span>
              <span>납품완료 (DELIVERED)</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-2.5 w-2.5 bg-rose-500 rounded-sm"></span>
              <span>RMA</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Chart: Parts Donut Summary -->
      <div class="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col min-h-[320px]">
        <h3 class="text-sm font-semibold text-slate-800 mb-4 select-none">부품(파트) 보유 현황</h3>
        
        <div v-if="parts.length === 0" class="flex-1 flex items-center justify-center text-slate-400 text-xs select-none">
          파트 재고 데이터가 없습니다.
        </div>

        <div v-else class="flex-1 flex flex-col justify-between">
          <div class="flex justify-center py-2 relative">
            <!-- Simulated Donut/Pie Chart with SVG -->
            <svg class="h-32 w-32 transform -rotate-90" viewBox="0 0 32 32">
              <circle cx="16" cy="16" r="14" fill="transparent" stroke="#E2E8F0" stroke-width="4" />
              <template v-for="(part, idx) in partsWithStroke" :key="part.model">
                <circle 
                  cx="16" 
                  cy="16" 
                  r="14" 
                  fill="transparent" 
                  :stroke="colors[idx % colors.length]" 
                  stroke-width="4" 
                  :stroke-dasharray="`${part.strokeDash} ${88 - part.strokeDash}`"
                  :stroke-dashoffset="-part.offset"
                />
              </template>
            </svg>
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <span class="text-xs font-bold text-slate-700">총 파트 수</span>
              <span class="text-sm font-black text-slate-900">{{ partsTotalQty }} 개</span>
            </div>
          </div>
          <!-- Legend list -->
          <div class="mt-4 space-y-1.5 max-h-[120px] overflow-y-auto pr-1">
            <div 
              v-for="(part, idx) in parts" 
              :key="part.model" 
              class="flex items-center justify-between text-xs text-slate-600 font-medium"
            >
              <div class="flex items-center gap-1.5 truncate">
                <span :style="{ backgroundColor: colors[idx % colors.length] }" class="h-2 w-2 rounded-full shrink-0"></span>
                <span class="truncate" :title="part.model">{{ part.model }}</span>
              </div>
              <span class="font-bold text-slate-800 shrink-0">{{ part.qty }} 개</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. Recent Deliveries List -->
    <div class="bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
      <div class="flex items-center justify-between mb-4 select-none">
        <h3 class="text-sm font-semibold text-slate-800">최근 입고/장비 장착 이력</h3>
        <AppButton variant="ghost" class="text-xs" @click="goTo('deliveries')">전체보기</AppButton>
      </div>

      <AppTable 
        :columns="columns" 
        :items="recentDeliveries" 
        :loading="loadingDeliveries"
      >
        <template #status="{ item }">
          <AppBadge :status="item.status" />
        </template>
      </AppTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'
import AppButton from '@/components/common/AppButton.vue'
import AppBadge from '@/components/common/AppBadge.vue'
import AppTable from '@/components/common/AppTable.vue'
import type { ColumnDefinition } from '@/components/common/AppTable.vue'

const router = useRouter()

// KPI data
const kpi = ref({
  in_stock_servers: 0,
  waiting_projects: 0,
  in_progress_projects: 0,
  completed_projects: 0
})

// Chart data
const customerDeliveries = ref<any[]>([])
const parts = ref<any[]>([])

// Recent deliveries table
const recentDeliveries = ref<any[]>([])
const loadingDeliveries = ref(false)

const nowString = ref('')
const colors = ['#2563EB', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#64748B']

const columns: ColumnDefinition[] = [
  { key: 'in_date', label: '입고일자' },
  { key: 'serial_tag', label: '시리얼태그(S/N)' },
  { key: 'model', label: '장비모델' },
  { key: 'status', label: '장비상태' }
]

onMounted(() => {
  updateTime()
  fetchKpi()
  fetchCustomerDeliveries()
  fetchPartsSummary()
  fetchRecentInventory()
})

function updateTime() {
  const d = new Date()
  nowString.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchKpi() {
  try {
    const res = await api.get('/dashboard/kpi')
    kpi.value = res.data.data
  } catch (error) {
    console.error('KPI fetch failed:', error)
  }
}

async function fetchCustomerDeliveries() {
  try {
    const res = await api.get('/dashboard/customer-delivery')
    customerDeliveries.value = res.data.data
  } catch (error) {
    console.error('Customer delivery fetch failed:', error)
  }
}

async function fetchPartsSummary() {
  try {
    const res = await api.get('/dashboard/parts-summary')
    parts.value = res.data.data
  } catch (error) {
    console.error('Parts summary fetch failed:', error)
  }
}

async function fetchRecentInventory() {
  loadingDeliveries.value = true
  try {
    const res = await api.get('/inventory?page=1&limit=5')
    recentDeliveries.value = res.data.data
  } catch (error) {
    console.error('Inventory list failed:', error)
  } finally {
    loadingDeliveries.value = false
  }
}

function goTo(routeName: string, queryParams = {}) {
  router.push({ name: routeName, query: queryParams })
}

// Helpers
function getDeliveryTotal(statuses: any) {
  let sum = 0
  for (const k in statuses) {
    sum += (statuses[k] || 0)
  }
  return sum
}

function getPercentage(val: number, statuses: any) {
  const total = getDeliveryTotal(statuses)
  if (total === 0) return 0
  return Math.round((val / total) * 100)
}

// Parts SVG stroke computations
const partsTotalQty = computed(() => {
  return parts.value.reduce((acc, p) => acc + p.qty, 0)
})

const partsWithStroke = computed(() => {
  const total = partsTotalQty.value
  if (total === 0) return []
  
  let currentOffset = 0
  return parts.value.map(p => {
    const strokeDash = (p.qty / total) * 88 // 88 is the circumference of circle with r=14
    const offset = currentOffset
    currentOffset += strokeDash
    return {
      ...p,
      strokeDash,
      offset
    }
  })
})
</script>
