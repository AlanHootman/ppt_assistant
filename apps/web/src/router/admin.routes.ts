import type { RouteRecordRaw } from 'vue-router'

const adminRoutes: RouteRecordRaw[] = [
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('../pages/admin/AdminLogin.vue'),
    meta: { 
      title: '管理员登录',
      requiresAuth: false
    }
  },
  {
    path: '/admin',
    component: () => import('../pages/admin/AdminLayout.vue'),
    meta: { 
      requiresAuth: true 
    },
    children: [
      {
        path: '',
        name: 'admin-dashboard',
        component: () => import('../pages/admin/AdminDashboard.vue'),
        meta: { 
          title: '管理后台',
          requiresAuth: true
        }
      },
      {
        path: 'templates',
        name: 'template-management',
        component: () => import('../pages/admin/template/TemplateList.vue'),
        meta: { 
          title: '模板管理',
          requiresAuth: true
        }
      },
      {
        path: 'templates/:id',
        name: 'template-detail',
        component: () => import('../pages/admin/template/TemplateDetail.vue'),
        meta: { 
          title: '模板详情',
          requiresAuth: true
        }
      },
      {
        path: 'model-config',
        name: 'model-config-management',
        component: () => import('../pages/admin/ModelConfigManagement.vue'),
        meta: { 
          title: '模型配置',
          requiresAuth: true
        }
      }
    ]
  }
]

export default adminRoutes 