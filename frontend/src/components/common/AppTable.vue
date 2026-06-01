<template>
  <div class="overflow-x-auto rounded-lg border border-slate-200 shadow-sm bg-white">
    <table class="min-w-full divide-y divide-slate-200 text-sm">
      <thead class="bg-slate-50">
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :class="[
              'px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider',
              col.sortable ? 'cursor-pointer hover:bg-slate-100 select-none' : ''
            ]"
            @click="col.sortable && handleSort(col.key)"
          >
            <div class="flex items-center gap-1">
              <span>{{ col.label }}</span>
              <span v-if="col.sortable" class="text-slate-400">
                <svg v-if="sortKey !== col.key" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                </svg>
                <svg v-else-if="sortOrder === 'asc'" class="h-3 w-3 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
                <svg v-else class="h-3 w-3 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </span>
            </div>
          </th>
        </tr>
      </thead>
      
      <tbody class="divide-y divide-slate-200 bg-white">
        <!-- Loading Skeleton -->
        <template v-if="loading">
          <tr v-for="n in 5" :key="n">
            <td v-for="col in columns" :key="col.key" class="px-6 py-4 whitespace-nowrap">
              <div class="h-4 bg-slate-100 rounded animate-pulse w-2/3"></div>
            </td>
          </tr>
        </template>
        
        <!-- Empty State -->
        <tr v-else-if="items.length === 0">
          <td :colspan="columns.length" class="px-6 py-12 text-center text-slate-400">
            <svg class="mx-auto h-8 w-8 text-slate-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0a2 2 0 01-2 2H6a2 2 0 01-2-2m16 0l-3.5 3.5a2 2 0 01-2.8 0L9 14" />
            </svg>
            조회된 데이터가 없습니다.
          </td>
        </tr>

        <!-- Data Rows -->
        <tr 
          v-else 
          v-for="(item, idx) in items" 
          :key="item.id || idx"
          class="hover:bg-slate-50 transition-colors"
        >
          <td v-for="col in columns" :key="col.key" class="px-6 py-4 whitespace-nowrap text-slate-700">
            <slot :name="col.key" :item="item" :index="idx">
              {{ item[col.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export interface ColumnDefinition {
  key: string
  label: string
  sortable?: boolean
}

interface Props {
  columns: ColumnDefinition[]
  items: any[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  (e: 'sort', payload: { key: string; order: 'asc' | 'desc' }): void
}>()

const sortKey = ref<string | null>(null)
const sortOrder = ref<'asc' | 'desc'>('asc')

function handleSort(key: string) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
  emit('sort', { key, order: sortOrder.value })
}
</script>
