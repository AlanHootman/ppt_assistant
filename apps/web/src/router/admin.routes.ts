export default [
  {
    path: '/admin',
    component: () => import('@/pages/admin/AdminLayout.vue'),
    children: [
      {
        path: '',
        name: 'admin-dashboard',
        component: () => import('@/pages/admin/AdminDashboard.vue'),
        meta: { 
          title: '管理后台',
          requiresAuth: true
        }
      },
      {
        path: 'templates',
        name: 'template-management',
        component: () => import('@/pages/admin/template/TemplateList.vue'),
        meta: { 
          title: '模板管理',
          requiresAuth: true
        }
      }
    ]
  },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('@/pages/admin/AdminLogin.vue'),
    meta: { title: '管理员登录' }
  }
] 