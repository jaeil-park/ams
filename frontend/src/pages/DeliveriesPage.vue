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
import { ref, onMounted, computed } from 'vue'
import api from '@/utils/api'
import AppBadge from '@/components/common/AppBadge.vue'
import AppTable from '@/components/common/AppTable.vue'
import type { ColumnDefinition } from '@/components/common/AppTable.vue'

const deliveredServers = ref<any[]>([])
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
    const res = await api.get('/inventory?limit=100')
    // DELIVERED 상태인 장비만 필터링 노출
    deliveredServers.value = res.data.data.filter((item: any) => item.status === 'DELIVERED')
  } catch (error) {
    console.error('Delivered items fetch failed:', error)
  } finally {
    loading.value = false
  }
}

const totalDelivered = computed(() => deliveredServers.value.length)
</script>
