import type { Router } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export function setupRouterGuards(router: Router) {
  // 路由前置守卫 - 管理后台需要登录
  router.beforeEach(async (to, from, next) => {
    // 设置页面标题
    document.title = to.meta.title ? `${to.meta.title} - PPT助手` : 'PPT助手'
    
    // 检查是否需要登录
    if (to.meta.requiresAuth) {
      const authStore = useAuthStore()
      
      // 如果没有登录状态，尝试从本地存储恢复
      if (!authStore.isLoggedIn) {
        const hasValidAuth = await authStore.initAuth()
        
        if (!hasValidAuth) {
          // 保存原始跳转URL
          next({
            name: 'admin-login',
            query: { redirect: to.fullPath }
          })
          return
        }
      }
    }
    
    // 如果已经登录且访问登录页，重定向到管理后台首页
    if (to.name === 'admin-login') {
      const authStore = useAuthStore()
      if (authStore.isLoggedIn) {
        next({ name: 'admin-dashboard' })
        return
      }
    }
    
    next()
  })
} 