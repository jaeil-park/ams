<template>
  <header class="h-[55px] px-6 bg-white border-b border-slate-200 flex items-center justify-between z-10 shadow-sm shrink-0">
    <div class="flex items-center gap-4">
      <!-- Toggle Sidebar Button -->
      <button
        type="button"
        class="text-slate-500 hover:text-slate-700 focus:outline-none transition-colors"
        @click="uiStore.toggleSidebar"
      >
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <!-- Breadcrumbs -->
      <div class="flex items-center gap-2 text-xs font-semibold text-slate-500 select-none">
        <span>AMS</span>
        <span>/</span>
        <span class="text-slate-900 capitalize">{{ currentPageLabel }}</span>
      </div>
    </div>

    <!-- Header Actions -->
    <div class="flex items-center gap-3">
      <!-- 전역 검색바 -->
      <div class="relative" ref="searchWrapperEl">
        <div class="flex items-center border border-slate-200 rounded-lg bg-slate-50 px-3 py-1.5 gap-2 w-64 focus-within:border-blue-400 focus-within:bg-white transition-all">
          <svg class="h-3.5 w-3.5 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="S/N, 고객사, 모델명 검색..."
            class="bg-transparent text-xs text-slate-700 placeholder-slate-400 focus:outline-none w-full"
            @input="onSearchInput"
            @focus="showDropdown = !!searchQuery && hasResults"
            @keydown.escape="closeSearch"
          />
          <button v-if="searchQuery" type="button" @click="clearSearch" class="text-slate-400 hover:text-slate-600">
            <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 검색 결과 드롭다운 -->
        <div
          v-if="showDropdown && hasResults"
          class="absolute top-full left-0 mt-1.5 w-96 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden"
        >
          <div v-if="searchLoading" class="px-4 py-4 text-center text-xs text-slate-400">
            검색 중...
          </div>
          <template v-else>
            <!-- 서버 결과 -->
            <div v-if="searchResults.servers?.length">
              <div class="px-3 py-2 bg-slate-50 text-3xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                서버 인벤토리
              </div>
              <button
                v-for="item in searchResults.servers"
                :key="`s-${item.id}`"
                type="button"
                class="w-full text-left px-4 py-2.5 hover:bg-blue-50 transition-colors flex items-center justify-between group"
                @click="navigateTo('inventory', item)"
              >
                <span class="text-xs font-semibold text-slate-800 font-mono">{{ item.serial_tag }}</span>
                <span class="text-3xs text-slate-400 group-hover:text-blue-600 transition-colors">{{ item.model }}</span>
              </button>
            </div>

            <!-- 고객사 결과 -->
            <div v-if="searchResults.customers?.length">
              <div class="px-3 py-2 bg-slate-50 text-3xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                고객사
              </div>
              <button
                v-for="item in searchResults.customers"
                :key="`c-${item.id}`"
                type="button"
                class="w-full text-left px-4 py-2.5 hover:bg-blue-50 transition-colors flex items-center justify-between group"
                @click="navigateTo('customers', item)"
              >
                <span class="text-xs font-semibold text-slate-800">{{ item.name }}</span>
                <span class="text-3xs text-slate-400 font-mono group-hover:text-blue-600 transition-colors">{{ item.code }}</span>
              </button>
            </div>

            <!-- 프로젝트 결과 -->
            <div v-if="searchResults.projects?.length">
              <div class="px-3 py-2 bg-slate-50 text-3xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                프로젝트
              </div>
              <button
                v-for="item in searchResults.projects"
                :key="`p-${item.id}`"
                type="button"
                class="w-full text-left px-4 py-2.5 hover:bg-blue-50 transition-colors flex items-center justify-between group"
                @click="navigateTo('projects', item)"
              >
                <span class="text-xs font-semibold text-slate-800">{{ item.name }}</span>
                <span class="text-3xs text-slate-400 font-mono group-hover:text-blue-600 transition-colors">{{ item.po_number }}</span>
              </button>
            </div>

            <!-- 파트 결과 -->
            <div v-if="searchResults.parts?.length">
              <div class="px-3 py-2 bg-slate-50 text-3xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                파트 재고
              </div>
              <button
                v-for="item in searchResults.parts"
                :key="`pt-${item.id}`"
                type="button"
                class="w-full text-left px-4 py-2.5 hover:bg-blue-50 transition-colors flex items-center justify-between group"
                @click="navigateTo('parts', item)"
              >
                <span class="text-xs font-semibold text-slate-800">{{ item.model }}</span>
                <span class="text-3xs text-slate-400 group-hover:text-blue-600 transition-colors">{{ item.category }} / {{ item.qty }}개</span>
              </button>
            </div>

            <!-- 결과 없음 -->
            <div v-if="!hasResults" class="px-4 py-4 text-center text-xs text-slate-400">
              "{{ searchQuery }}"에 대한 검색 결과가 없습니다.
            </div>
          </template>
        </div>
      </div>

      <!-- System OK badge -->
      <div class="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 rounded-full border border-emerald-200">
        <span class="h-1.5 w-1.5 bg-emerald-500 rounded-full animate-ping"></span>
        <span class="text-3xs font-bold text-emerald-700 tracking-wider">SYSTEM OK</span>
      </div>

      <!-- 승인 대기 알림 (ADMIN only) -->
      <div v-if="authStore.isAdmin" class="relative">
        <button
          type="button"
          class="relative p-1.5 text-slate-500 hover:text-slate-700 focus:outline-none transition-colors"
          @click="goToApprovals"
          title="승인 대기 알림"
        >
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <!-- 배지 -->
          <span
            v-if="pendingCount > 0"
            class="absolute -top-0.5 -right-0.5 h-4 w-4 bg-red-500 text-white text-3xs font-bold rounded-full flex items-center justify-center leading-none"
          >
            {{ pendingCount > 9 ? '9+' : pendingCount }}
          </span>
        </button>
      </div>

      <!-- User avatar & Profile dropdown trigger -->
      <div class="relative">
        <div class="flex items-center gap-2 cursor-pointer" @click="toggleProfileMenu">
          <div class="h-8 w-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs shadow-inner">
            {{ userInitial }}
          </div>
          <div class="hidden md:block text-left">
            <div class="text-xs font-semibold text-slate-800 leading-tight">
              {{ authStore.user?.name || '사용자' }}
            </div>
            <div class="text-4xs font-bold text-slate-400 leading-none">
              {{ authStore.user?.role || 'USER' }}
            </div>
          </div>
        </div>

        <!-- Profile Dropdown Menu -->
        <div
          v-if="isProfileMenuOpen"
          class="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-md shadow-lg py-1 z-30"
        >
          <button
            type="button"
            class="w-full text-left px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 flex items-center gap-2 font-medium"
            @click="handleLogout"
          >
            <svg class="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            로그아웃
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const isProfileMenuOpen = ref(false)

// ─── 전역 검색 ─────────────────────────────────────────
const searchQuery = ref('')
const searchLoading = ref(false)
const showDropdown = ref(false)
const searchResults = ref<any>({ servers: [], customers: [], projects: [], parts: [] })
const searchWrapperEl = ref<HTMLElement | null>(null)
let searchDebounce: ReturnType<typeof setTimeout> | null = null

const hasResults = computed(() => {
  const r = searchResults.value
  return (r.servers?.length || r.customers?.length || r.projects?.length || r.parts?.length)
})

function onSearchInput() {
  if (searchDebounce) clearTimeout(searchDebounce)
  if (!searchQuery.value.trim()) {
    showDropdown.value = false
    searchResults.value = { servers: [], customers: [], projects: [], parts: [] }
    return
  }
  searchDebounce = setTimeout(() => {
    doSearch()
  }, 300)
}

async function doSearch() {
  searchLoading.value = true
  showDropdown.value = true
  try {
    const res = await api.get('/search', { params: { q: searchQuery.value.trim() } })
    searchResults.value = res.data.data || {}
    showDropdown.value = true
  } catch (err) {
    console.error('검색 오류:', err)
  } finally {
    searchLoading.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  showDropdown.value = false
  searchResults.value = { servers: [], customers: [], projects: [], parts: [] }
}

function closeSearch() {
  showDropdown.value = false
}

function navigateTo(page: string, item: any) {
  closeSearch()
  router.push({ name: page })
}

// 외부 클릭 시 드롭다운 닫기
function onOutsideClick(event: MouseEvent) {
  if (searchWrapperEl.value && !searchWrapperEl.value.contains(event.target as Node)) {
    showDropdown.value = false
  }
}

// ─── 승인 대기 배지 ─────────────────────────────────────
const pendingCount = ref(0)
let pendingPollTimer: ReturnType<typeof setInterval> | null = null

async function fetchPendingCount() {
  if (!authStore.isAdmin) return
  try {
    const res = await api.get('/approvals', { params: { status: 'PENDING', limit: 1, page: 1 } })
    pendingCount.value = res.data.meta?.total || 0
  } catch {
    // 조용히 실패
  }
}

function goToApprovals() {
  router.push({ name: 'approvals' })
}

// ─── 페이지 라벨 ─────────────────────────────────────────
const currentPageLabel = computed(() => {
  const name = route.name as string
  const map: Record<string, string> = {
    dashboard: '대시보드',
    customers: '고객사 관리',
    projects: '프로젝트 관리',
    inventory: '납품목록 (서버)',
    parts: '파트재고',
    deliveries: '납품이력',
    addresses: '납품주소',
    approvals: '승인 관리',
    'audit-logs': '감사 로그',
  }
  return map[name] || name || '대시보드'
})

const userInitial = computed(() => {
  const name = authStore.user?.name || 'U'
  return name.charAt(0)
})

function toggleProfileMenu() {
  isProfileMenuOpen.value = !isProfileMenuOpen.value
}

function handleLogout() {
  authStore.logout()
  uiStore.addToast('성공적으로 로그아웃되었습니다.', 'success')
  router.push({ name: 'login' })
}

onMounted(() => {
  document.addEventListener('click', onOutsideClick)
  if (authStore.isAdmin) {
    fetchPendingCount()
    pendingPollTimer = setInterval(fetchPendingCount, 30000)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', onOutsideClick)
  if (pendingPollTimer) clearInterval(pendingPollTimer)
  if (searchDebounce) clearTimeout(searchDebounce)
})
</script>
