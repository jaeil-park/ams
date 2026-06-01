import { ref } from 'vue'
import { defineStore } from 'pinia'

export interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'warning'
}

export const useUiStore = defineStore('ui', () => {
  // 사이드바 상태
  const isSidebarOpen = ref(true)

  // Toast 목록
  const toasts = ref<Toast[]>([])
  let toastId = 0

  function toggleSidebar() {
    isSidebarOpen.value = !isSidebarOpen.value
  }

  function addToast(message: string, type: 'success' | 'error' | 'warning' = 'success', duration = 3000) {
    const id = toastId++
    toasts.value.push({ id, message, type })

    setTimeout(() => {
      removeToast(id)
    }, duration)
  }

  function removeToast(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return {
    isSidebarOpen,
    toasts,
    toggleSidebar,
    addToast,
    removeToast,
  }
})
