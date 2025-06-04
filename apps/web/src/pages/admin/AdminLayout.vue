<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="admin-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <h2 v-if="!sidebarCollapsed" class="sidebar-title">管理后台</h2>
        <h2 v-else class="sidebar-title-collapsed">管</h2>
      </div>
      
      <nav class="sidebar-nav">
        <el-menu
          :default-active="activeMenu"
          :collapse="sidebarCollapsed"
          :collapse-transition="false"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409eff"
          router
        >
          <el-menu-item index="/admin" route="/admin">
            <el-icon><House /></el-icon>
            <template #title>仪表盘</template>
          </el-menu-item>
          
          <el-menu-item index="/admin/templates" route="/admin/templates">
            <el-icon><Files /></el-icon>
            <template #title>模板管理</template>
          </el-menu-item>
          
          <el-menu-item index="/admin/model-config" route="/admin/model-config">
            <el-icon><Setting /></el-icon>
            <template #title>模型配置</template>
          </el-menu-item>
        </el-menu>
      </nav>
    </aside>

    <!-- 主内容区域 -->
    <div class="admin-main" :class="{ expanded: sidebarCollapsed }">
      <!-- 顶部头部 -->
      <header class="admin-header">
        <div class="header-left">
          <el-button
            link
            @click="toggleSidebar"
            class="sidebar-toggle"
          >
            <el-icon><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item :to="{ path: '/admin' }">管理后台</el-breadcrumb-item>
            <el-breadcrumb-item v-if="breadcrumbItems.length > 0">
              {{ breadcrumbItems[breadcrumbItems.length - 1] }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-dropdown @command="handleUserAction">
            <span class="user-dropdown">
              <el-icon><User /></el-icon>
              <span class="username">{{ authStore.userInfo?.username }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 主内容 -->
      <main class="admin-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  House, 
  Files, 
  Fold, 
  Expand, 
  User, 
  ArrowDown, 
  SwitchButton,
  Setting
} from '@element-plus/icons-vue'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 侧边栏折叠状态
const sidebarCollapsed = ref(false)

// 当前激活的菜单项
const activeMenu = computed(() => route.path)

// 面包屑导航
const breadcrumbItems = computed(() => {
  const routeName = route.meta.title as string
  if (routeName && routeName !== '管理后台') {
    return [routeName]
  }
  return []
})

// 切换侧边栏
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 处理用户操作
const handleUserAction = async (command: string) => {
  if (command === 'logout') {
    if (confirm('确定要退出登录吗？')) {
      await authStore.logout()
      ElMessage.success('已退出登录')
      router.push('/admin/login')
    }
  }
}

// 监听路由变化，如果用户未登录则跳转到登录页
watch(() => authStore.isLoggedIn, (isLoggedIn) => {
  if (!isLoggedIn) {
    router.push('/admin/login')
  }
}, { immediate: true })
</script>

<style scoped>
.admin-layout {
  display: flex;
  height: 100vh;
  background-color: #f0f2f5;
}

/* ==========================================================================
   侧边栏样式
   ========================================================================== */

.admin-sidebar {
  width: 260px;
  background-color: #304156;
  transition: width 0.3s ease;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
}

.admin-sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #3e4c59;
  background-color: #263445;
}

.sidebar-title {
  color: #ffffff;
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0;
}

.sidebar-title-collapsed {
  color: #ffffff;
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
}

.sidebar-nav .el-menu {
  border-right: none;
}

/* ==========================================================================
   主内容区域样式
   ========================================================================== */

.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 0;
  transition: margin-left 0.3s ease;
}

.admin-main.expanded {
  margin-left: 0;
}

/* 顶部头部 */
.admin-header {
  height: 60px;
  background-color: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  position: relative;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
}

.sidebar-toggle {
  margin-right: 1rem;
  color: #606266;
}

.sidebar-toggle:hover {
  color: #409eff;
}

.breadcrumb {
  font-size: 0.875rem;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.user-dropdown:hover {
  background-color: #f5f7fa;
}

.username {
  margin: 0 0.5rem;
  color: #606266;
  font-size: 0.875rem;
}

/* 主内容 */
.admin-content {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
  background-color: #f0f2f5;
}

/* ==========================================================================
   响应式设计
   ========================================================================== */

@media (max-width: 768px) {
  .admin-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 100;
    height: 100vh;
  }
  
  .admin-sidebar.collapsed {
    left: -260px;
  }
  
  .admin-main {
    margin-left: 0;
  }
  
  .admin-header {
    padding: 0 1rem;
  }
  
  .admin-content {
    padding: 1rem;
  }
  
  .breadcrumb {
    display: none;
  }
}

/* ==========================================================================
   深色主题支持（可选）
   ========================================================================== */

@media (prefers-color-scheme: dark) {
  .admin-layout {
    background-color: #1e1e2e;
  }
  
  .admin-header {
    background-color: #282838;
    border-bottom: 1px solid #3c3c4c;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }
  
  .admin-content {
    background-color: #1e1e2e;
  }
  
  .sidebar-toggle {
    color: #e0e0e0;
  }
  
  .user-dropdown {
    color: #e0e0e0;
  }
  
  .username {
    color: #e0e0e0;
  }
  
  .user-dropdown:hover {
    background-color: #383848;
  }
  
  .breadcrumb :deep(.el-breadcrumb__item) {
    color: #e0e0e0;
  }
  
  .breadcrumb :deep(.el-breadcrumb__inner) {
    color: #e0e0e0;
  }
  
  .breadcrumb :deep(.el-breadcrumb__separator) {
    color: #a0a0a0;
  }
}
</style> 