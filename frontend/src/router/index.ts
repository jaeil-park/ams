import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { guestOnly: true }
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/pages/DashboardPage.vue')
        },
        {
          path: 'customers',
          name: 'customers',
          component: () => import('@/pages/CustomersPage.vue')
        },
        {
          path: 'projects',
          name: 'projects',
          component: () => import('@/pages/ProjectsPage.vue')
        },
        {
          path: 'inventory',
          name: 'inventory',
          component: () => import('@/pages/InventoryPage.vue')
        },
        {
          path: 'parts',
          name: 'parts',
          component: () => import('@/pages/PartsPage.vue')
        },
        {
          path: 'deliveries',
          name: 'deliveries',
          component: () => import('@/pages/DeliveriesPage.vue')
        },
        {
          path: 'addresses',
          name: 'addresses',
          component: () => import('@/pages/AddressesPage.vue')
        },
        {
          path: 'approvals',
          name: 'approvals',
          component: () => import('@/pages/ApprovalsPage.vue')
        },
        {
          path: 'audit-logs',
          name: 'audit-logs',
          component: () => import('@/pages/AuditLogsPage.vue')
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

// Navigation Guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 인증이 필요한 페이지
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      return next({ name: 'login' })
    }
    // 사용자 상세 정보를 아직 받아오지 않았다면 fetch
    if (!authStore.user) {
      await authStore.fetchMe()
    }
    return next()
  }

  // 로그인 상태에서 로그인 페이지 접근 시 대시보드로 이동
  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return next({ name: 'dashboard' })
  }

  next()
})

export default router
