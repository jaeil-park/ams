<template>
  <div class="h-screen w-screen flex bg-slate-50 overflow-hidden font-sans">
    <!-- Sidebar Left -->
    <AppSidebar />

    <!-- Main Container Right -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Upper Header -->
      <AppHeader />

      <!-- Center Main Content -->
      <main class="flex-1 overflow-y-auto p-6 min-h-0">
        <RouterView />
      </main>
    </div>

    <!-- Global Floating Toast Notification Container -->
    <div class="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full">
      <TransitionGroup name="toast">
        <div
          v-for="toast in uiStore.toasts"
          :key="toast.id"
          :class="[
            'p-4 rounded-lg shadow-lg border text-sm font-semibold flex items-center justify-between transition-all duration-300',
            toast.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : '',
            toast.type === 'error' ? 'bg-rose-50 border-rose-200 text-rose-800' : '',
            toast.type === 'warning' ? 'bg-amber-50 border-amber-200 text-amber-800' : ''
          ]"
        >
          <span>{{ toast.message }}</span>
          <button 
            type="button" 
            class="text-slate-400 hover:text-slate-600 focus:outline-none ml-3"
            @click="uiStore.removeToast(toast.id)"
          >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useUiStore } from '@/stores/ui'

const uiStore = useUiStore()
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(30px);
}
.toast-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>
