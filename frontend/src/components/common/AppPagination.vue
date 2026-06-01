<template>
  <div class="flex items-center justify-between border-t border-slate-200 bg-white px-4 py-3 sm:px-6 mt-4">
    <div class="flex flex-1 justify-between sm:hidden">
      <AppButton
        variant="secondary"
        :disabled="currentPage <= 1"
        @click="changePage(currentPage - 1)"
      >
        이전
      </AppButton>
      <AppButton
        variant="secondary"
        :disabled="currentPage >= totalPages"
        @click="changePage(currentPage + 1)"
      >
        다음
      </AppButton>
    </div>
    
    <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
      <div>
        <p class="text-xs text-slate-500">
          총 <span class="font-medium text-slate-700">{{ totalItems }}</span>개 중 
          <span class="font-medium text-slate-700">{{ startRange }}</span> - 
          <span class="font-medium text-slate-700">{{ endRange }}</span> 표시
        </p>
      </div>
      <div>
        <nav class="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
          <!-- Previous Button -->
          <button
            :disabled="currentPage <= 1"
            class="relative inline-flex items-center rounded-l-md px-2 py-2 text-slate-400 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="changePage(currentPage - 1)"
          >
            <span class="sr-only">Previous</span>
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.83 10l3.94 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Pages -->
          <button
            v-for="page in visiblePages"
            :key="page"
            :aria-current="currentPage === page ? 'page' : undefined"
            :class="[
              currentPage === page 
                ? 'relative z-10 inline-flex items-center bg-blue-600 px-3 py-2 text-xs font-semibold text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                : 'relative inline-flex items-center px-3 py-2 text-xs font-semibold text-slate-900 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus:z-20 focus:outline-offset-0'
            ]"
            @click="changePage(page)"
          >
            {{ page }}
          </button>

          <!-- Next Button -->
          <button
            :disabled="currentPage >= totalPages"
            class="relative inline-flex items-center rounded-r-md px-2 py-2 text-slate-400 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="changePage(currentPage + 1)"
          >
            <span class="sr-only">Next</span>
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.17 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
            </svg>
          </button>
        </nav>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppButton from '@/components/common/AppButton.vue'

interface Props {
  currentPage: number
  totalPages: number
  totalItems: number
  limit: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'page-change', page: number): void
}>()

const startRange = computed(() => (props.currentPage - 1) * props.limit + 1)
const endRange = computed(() => Math.min(props.currentPage * props.limit, props.totalItems))

const visiblePages = computed(() => {
  const pages: number[] = []
  const maxVisible = 5
  let start = Math.max(1, props.currentPage - Math.floor(maxVisible / 2))
  let end = Math.min(props.totalPages, start + maxVisible - 1)

  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1)
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

function changePage(page: number) {
  if (page >= 1 && page <= props.totalPages) {
    emit('page-change', page)
  }
}
</script>
