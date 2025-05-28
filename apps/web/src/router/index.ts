import { createRouter, createWebHistory } from 'vue-router'
import homeRoutes from './home.routes'
import adminRoutes from './admin.routes'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...homeRoutes,
    ...adminRoutes,
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/pages/error/NotFound.vue'),
      meta: { title: '页面未找到' }
    }
  ]
})

// 路由守卫 - 管理后台需要登录
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - PPT助手` : 'PPT助手'
  
  // 检查是否需要登录
  if (to.meta.requiresAuth) {
    const authStore = useAuthStore()
    
    if (!authStore.isLoggedIn) {
      // 保存原始跳转URL
      next({
        name: 'admin-login',
        query: { redirect: to.fullPath }
      })
      return
    }
  }
  
  next()
})

export default router 