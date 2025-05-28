import { createRouter, createWebHistory } from 'vue-router'
import homeRoutes from './home.routes'
import adminRoutes from './admin.routes'

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

// 路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - PPT助手` : 'PPT助手'
  next()
})

export default router 