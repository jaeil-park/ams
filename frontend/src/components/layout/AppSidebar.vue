<template>
  <aside 
    :class="[
      'bg-slate-900 text-slate-300 transition-all duration-300 flex flex-col z-20 shadow-lg border-r border-slate-800',
      uiStore.isSidebarOpen ? 'w-[240px]' : 'w-[64px]'
    ]"
  >
    <!-- Logo area -->
    <div class="h-[55px] px-4 border-b border-slate-800 flex items-center gap-2 overflow-hidden whitespace-nowrap">
      <div class="h-8 w-8 rounded-md bg-blue-600 flex items-center justify-center text-white font-bold shrink-0">
        A
      </div>
      <span v-if="uiStore.isSidebarOpen" class="font-semibold text-white tracking-wide">
        AMS ERP v1.0
      </span>
    </div>

    <!-- Navigation Menu -->
    <nav class="flex-1 px-2 py-4 overflow-y-auto space-y-6">
      <!-- MAIN SECTION -->
      <div>
        <div v-if="uiStore.isSidebarOpen" class="px-3 text-2xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
          Main
        </div>
        <ul class="space-y-1">
          <li v-for="item in mainItems" :key="item.name">
            <RouterLink 
              :to="item.to"
              :class="[
                'flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors font-medium',
                route.name === item.name 
                  ? 'bg-blue-600 text-white font-semibold' 
                  : 'hover:bg-slate-800 hover:text-white'
              ]"
            >
              <!-- Icon Dynamic Slot or Native SVG -->
              <span class="shrink-0" v-html="item.icon"></span>
              <span v-if="uiStore.isSidebarOpen">{{ item.label }}</span>
            </RouterLink>
          </li>
        </ul>
      </div>

      <!-- OPS SECTION -->
      <div>
        <div v-if="uiStore.isSidebarOpen" class="px-3 text-2xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
          Operations
        </div>
        <ul class="space-y-1">
          <li v-for="item in opsItems" :key="item.name">
            <RouterLink
              :to="item.to"
              :class="[
                'flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors font-medium',
                route.name === item.name
                  ? 'bg-blue-600 text-white font-semibold'
                  : 'hover:bg-slate-800 hover:text-white'
              ]"
            >
              <span class="shrink-0" v-html="item.icon"></span>
              <span v-if="uiStore.isSidebarOpen" class="flex-1">{{ item.label }}</span>
              <!-- Pending count badge -->
              <span
                v-if="uiStore.isSidebarOpen && item.name === 'approvals' && pendingCount > 0"
                class="ml-auto px-1.5 py-0.5 bg-red-500 text-white text-3xs font-bold rounded-full leading-none"
              >
                {{ pendingCount > 9 ? '9+' : pendingCount }}
              </span>
            </RouterLink>
          </li>
        </ul>
      </div>

      <!-- ADMIN SECTION -->
      <div v-if="authStore.isAdmin">
        <div v-if="uiStore.isSidebarOpen" class="px-3 text-2xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
          Admin
        </div>
        <ul class="space-y-1">
          <li v-for="item in adminItems" :key="item.name">
            <RouterLink
              :to="item.to"
              :class="[
                'flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors font-medium',
                route.name === item.name
                  ? 'bg-blue-600 text-white font-semibold'
                  : 'hover:bg-slate-800 hover:text-white'
              ]"
            >
              <span class="shrink-0" v-html="item.icon"></span>
              <span v-if="uiStore.isSidebarOpen">{{ item.label }}</span>
            </RouterLink>
          </li>
        </ul>
      </div>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'

const route = useRoute()
const uiStore = useUiStore()
const authStore = useAuthStore()

// 승인 대기 카운트
const pendingCount = ref(0)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchPendingCount() {
  if (!authStore.isAdmin) return
  try {
    const res = await api.get('/approvals', { params: { status: 'PENDING', limit: 1, page: 1 } })
    pendingCount.value = res.data.meta?.total || 0
  } catch { /* 조용히 실패 */ }
}

onMounted(() => {
  if (authStore.isAdmin) {
    fetchPendingCount()
    pollTimer = setInterval(fetchPendingCount, 30000)
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const mainItems = [
  {
    name: 'dashboard',
    label: '대시보드',
    to: '/',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>`
  },
  {
    name: 'customers',
    label: '고객사 관리',
    to: '/customers',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>`
  },
  {
    name: 'projects',
    label: '프로젝트 관리',
    to: '/projects',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" /></svg>`
  },
  {
    name: 'inventory',
    label: '납품목록 (서버)',
    to: '/inventory',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" /></svg>`
  },
  {
    name: 'parts',
    label: '파트재고',
    to: '/parts',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" /></svg>`
  }
]

const opsItems = [
  {
    name: 'deliveries',
    label: '납품이력',
    to: '/deliveries',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" /></svg>`
  },
  {
    name: 'addresses',
    label: '납품주소',
    to: '/addresses',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" /></svg>`
  },
  {
    name: 'approvals',
    label: '승인 관리',
    to: '/approvals',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`
  }
]

const adminItems = [
  {
    name: 'audit-logs',
    label: '감사 로그',
    to: '/audit-logs',
    icon: `<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>`
  }
]
</script>
