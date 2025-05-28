export default [
  {
    path: '/',
    name: 'home',
    component: () => import('@/pages/home/HomePage.vue'),
    meta: { title: 'PPT自动生成' }
  }
] 