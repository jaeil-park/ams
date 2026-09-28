<template>
  <div class="space-y-6 font-sans">
    <!-- Header Page Banner -->
    <div class="flex items-center justify-between select-none">
      <div>
        <h1 class="text-xl font-bold text-slate-800">납품이력</h1>
        <p class="text-xs text-slate-400 mt-1">납품 완료 장비 히스토리</p>
      </div>
    </div>

    <!-- Stats summary box -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 select-none">
      <div class="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
        <span class="block text-4xs font-bold text-slate-400 uppercase tracking-wider">납품완료 장비</span>
        <h3 class="text-xl font-black text-slate-800 mt-1">{{ totalDelivered }} 대</h3>
      </div>
    </div>

    <!-- Main Data Table -->
    <AppTable :columns="columns" :items="deliveredServers" :loading="loading">
      <template #status="{ item }">
        <AppBadge :status="item.status" />
      </template>
    </AppTable>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/utils/api'
import AppBadge from '@/components/common/AppBadge.vue'
import AppTable from '@/components/common/AppTable.vue'
import type { ColumnDefinition } from '@/components/common/AppTable.vue'

const deliveredServers = ref<any[]>([])
const totalDelivered = ref(0)
const loading = ref(false)

const columns: ColumnDefinition[] = [
  { key: 'in_date', label: '납품완료날짜' },
  { key: 'serial_tag', label: '시리얼태그(S/N)' },
  { key: 'model', label: '모델명' },
  { key: 'status', label: '상태' }
]

onMounted(() => {
  fetchDeliveredItems()
})

async function fetchDeliveredItems() {
  loading.value = true
  try {
    // 상태 필터는 서버에서 건다 — 가져온 뒤 브라우저에서 걸러내면
    // 장비가 limit을 넘어섰을 때 오래된 납품 건이 조용히 누락된다.
    const res = await api.get('/inventory', { params: { status: 'DELIVERED', limit: 1000 } })
    deliveredServers.value = res.data.data
    totalDelivered.value = res.data.meta?.total ?? res.data.data.length
  } catch (error) {
    console.error('Delivered items fetch failed:', error)
  } finally {
    loading.value = false
  }
}
</script>
