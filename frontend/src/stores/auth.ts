import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/utils/api'

export interface UserInfo {
  id: number
  email: string
  name: string
  role: 'ADMIN' | 'USER'
  is_active: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<UserInfo | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'ADMIN')

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const formData = new URLSearchParams()
      formData.append('username', email)  // OAuth2PasswordRequestForm
      formData.append('password', password)

      const response = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      })

      const { access_token, refresh_token } = response.data
      token.value = access_token
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      
      await fetchMe()
      return true
    } catch (error) {
      console.error('로그인 에러:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    try {
      const response = await api.get('/auth/me')
      user.value = response.data.data
    } catch (error) {
      console.error('사용자 정보 조회 실패:', error)
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    isAdmin,
    login,
    fetchMe,
    logout,
  }
})
