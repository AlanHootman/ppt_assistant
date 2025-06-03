import { createRouter, createWebHistory } from 'vue-router'
import homeRoutes from './home.routes'
import adminRoutes from './admin.routes'
import { setupRouterGuards } from './guards'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...homeRoutes,
    ...adminRoutes,
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../pages/error/NotFound.vue'),
      meta: { title: '页面未找到' }
    }
  ]
})

// 设置路由守卫
setupRouterGuards(router)

export default router 