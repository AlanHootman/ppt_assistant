import { createRouter, createWebHistory } from 'vue-router'
import homeRoutes from './home.routes'
// 暂时注释掉 adminRoutes，防止找不到相关组件
// import adminRoutes from './admin.routes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...homeRoutes,
    // ...adminRoutes // 暂时注释掉管理后台路由
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../pages/error/NotFound.vue'),
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