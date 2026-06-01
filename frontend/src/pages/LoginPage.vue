<template>
  <div class="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <!-- Logo banner -->
      <div class="mx-auto h-12 w-12 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-xl shadow-lg">
        A
      </div>
      <h2 class="mt-6 text-center text-xl font-bold tracking-tight text-white select-none">
        AMS ERP 로그인
      </h2>
      <p class="mt-2 text-center text-xs text-slate-400">
        IT 자산 관리 시스템 v1.0.0
      </p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-slate-800 py-8 px-4 shadow-xl border border-slate-700 rounded-lg sm:px-10">
        <form class="space-y-6" @submit.prevent="handleLogin">
          <!-- Error alert -->
          <div v-if="error" class="bg-rose-900/50 border border-rose-500/50 text-rose-200 text-xs px-4 py-2.5 rounded-md">
            {{ error }}
          </div>

          <!-- Email Input -->
          <div>
            <label for="email" class="block text-xs font-semibold text-slate-300">
              이메일 주소
            </label>
            <div class="mt-1">
              <input
                id="email"
                type="email"
                required
                v-model="email"
                placeholder="admin@ams.dev"
                class="block w-full px-3 py-2 text-sm border border-slate-600 rounded-md bg-slate-900 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          <!-- Password Input -->
          <div>
            <label for="password" class="block text-xs font-semibold text-slate-300">
              비밀번호
            </label>
            <div class="mt-1">
              <input
                id="password"
                type="password"
                required
                v-model="password"
                placeholder="••••••••"
                class="block w-full px-3 py-2 text-sm border border-slate-600 rounded-md bg-slate-900 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          <!-- Submit Button -->
          <div>
            <AppButton
              type="submit"
              variant="primary"
              :loading="loading"
              class="w-full flex justify-center py-2"
            >
              로그인
            </AppButton>
          </div>
        </form>

        <!-- Guide banner -->
        <div class="mt-6 border-t border-slate-700 pt-4 text-center">
          <p class="text-3xs font-semibold text-slate-500 uppercase tracking-wider">
            개발 계정 가이드
          </p>
          <p class="mt-1 text-4xs text-slate-400">
            ID: admin@ams.dev | PW: admin
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import AppButton from '@/components/common/AppButton.vue'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

async function handleLogin() {
  error.value = null
  loading.value = true
  try {
    const success = await authStore.login(email.value, password.value)
    if (success) {
      uiStore.addToast('성공적으로 로그인되었습니다.', 'success')
      router.push({ name: 'dashboard' })
    }
  } catch (err: any) {
    console.error(err)
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = '로그인 시도 중 예기치 못한 에러가 발생했습니다.'
    }
    uiStore.addToast('로그인에 실패했습니다.', 'error')
  } finally {
    loading.value = false
  }
}
</script>
