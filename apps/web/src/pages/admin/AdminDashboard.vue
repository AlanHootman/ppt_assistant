<template>
  <div class="admin-dashboard">
    <div class="dashboard-header">
      <h1 class="page-title">管理后台</h1>
      <p class="page-subtitle">欢迎使用PPT助手管理后台，您可以在这里管理模板和查看系统状态。</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><Files /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ totalTemplates }}</div>
          <div class="stat-label">模板总数</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon ready">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ readyTemplates }}</div>
          <div class="stat-label">可用模板</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon processing">
          <el-icon><Loading /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ analyzingTemplates }}</div>
          <div class="stat-label">分析中</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon error">
          <el-icon><CircleClose /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ failedTemplates }}</div>
          <div class="stat-label">分析失败</div>
        </div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <h2 class="section-title">快捷操作</h2>
      <div class="action-grid">
        <el-card class="action-card" shadow="hover" @click="goToTemplateManagement">
          <div class="action-content">
            <el-icon class="action-icon"><Files /></el-icon>
            <h3>模板管理</h3>
            <p>管理PPT模板，上传新模板或编辑现有模板</p>
          </div>
        </el-card>

        <el-card class="action-card" shadow="hover" @click="goToModelConfig">
          <div class="action-content">
            <el-icon class="action-icon"><Setting /></el-icon>
            <h3>模型配置</h3>
            <p>管理AI模型配置，设置API密钥和模型参数</p>
          </div>
        </el-card>

        <el-card class="action-card" shadow="hover" @click="goToHome">
          <div class="action-content">
            <el-icon class="action-icon"><House /></el-icon>
            <h3>前往首页</h3>
            <p>返回到PPT生成页面，体验模板效果</p>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 系统信息 -->
    <div class="system-info">
      <h2 class="section-title">系统信息</h2>
      <el-card>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">系统版本:</span>
            <span class="info-value">PPT助手 v1.0.0</span>
          </div>
          <div class="info-item">
            <span class="info-label">当前用户:</span>
            <span class="info-value">{{ authStore.userInfo?.username }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">用户角色:</span>
            <span class="info-value">{{ authStore.userInfo?.role }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">登录时间:</span>
            <span class="info-value">{{ currentTime }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Files, 
  CircleCheck, 
  Loading, 
  CircleClose, 
  House,
  Setting
} from '@element-plus/icons-vue'
import { useAuthStore } from '../../stores/auth'
import { adminApi } from '../../services/api/admin.api'

const router = useRouter()
const authStore = useAuthStore()

// 模板统计数据
const totalTemplates = ref(0)
const readyTemplates = ref(0)
const analyzingTemplates = ref(0)
const failedTemplates = ref(0)
const loading = ref(false)

// 当前时间
const currentTime = computed(() => {
  return new Date().toLocaleString('zh-CN')
})

// 获取模板统计数据
const fetchTemplateStats = async () => {
  loading.value = true
  try {
    const response = await adminApi.getTemplates(1, 100) // 获取更多数据用于统计
    
    if (response.code === 200) {
      const templates = response.data.templates
      totalTemplates.value = templates.length
      readyTemplates.value = templates.filter(t => t.status === 'ready').length
      analyzingTemplates.value = templates.filter(t => t.status === 'analyzing').length
      failedTemplates.value = templates.filter(t => t.status === 'failed').length
    }
  } catch (error) {
    console.error('获取模板统计失败:', error)
  } finally {
    loading.value = false
  }
}

// 跳转到模板管理
const goToTemplateManagement = () => {
  router.push('/admin/templates')
}

// 跳转到模型配置
const goToModelConfig = () => {
  router.push('/admin/model-config')
}

// 跳转到首页
const goToHome = () => {
  router.push('/')
}

// 组件挂载时获取数据
onMounted(() => {
  fetchTemplateStats()
})
</script>

<style scoped>
.admin-dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

/* ==========================================================================
   页面头部
   ========================================================================== */

.dashboard-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.page-subtitle {
  color: #718096;
  margin: 0;
  font-size: 1rem;
  line-height: 1.5;
}

/* ==========================================================================
   统计卡片
   ========================================================================== */

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 1rem;
  background-color: #409eff;
  color: white;
  font-size: 1.5rem;
}

.stat-icon.ready {
  background-color: #67c23a;
}

.stat-icon.processing {
  background-color: #e6a23c;
}

.stat-icon.error {
  background-color: #f56c6c;
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 1.75rem;
  font-weight: 600;
  color: #2d3748;
  line-height: 1;
}

.stat-label {
  color: #718096;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

/* ==========================================================================
   快捷操作
   ========================================================================== */

.quick-actions {
  margin-bottom: 3rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 1.5rem 0;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.action-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.action-card:hover {
  transform: translateY(-2px);
}

.action-content {
  text-align: center;
  padding: 1rem;
}

.action-icon {
  font-size: 2.5rem;
  color: #409eff;
  margin-bottom: 1rem;
}

.action-content h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.action-content p {
  color: #718096;
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.4;
}

/* ==========================================================================
   系统信息
   ========================================================================== */

.system-info {
  margin-bottom: 2rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid #e2e8f0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  color: #718096;
  font-size: 0.875rem;
}

.info-value {
  color: #2d3748;
  font-weight: 500;
  font-size: 0.875rem;
}

/* ==========================================================================
   响应式设计
   ========================================================================== */

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .action-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .page-title {
    font-size: 1.5rem;
  }
  
  .stat-card {
    padding: 1rem;
  }
}

/* ==========================================================================
   深色模式支持
   ========================================================================== */

@media (prefers-color-scheme: dark) {
  .page-title {
    color: #e0e0e0;
  }
  
  .page-subtitle {
    color: #b0b0c0;
  }
  
  .section-title {
    color: #e0e0e0;
  }
  
  .stat-card {
    background-color: #282838;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
  }
  
  .stat-number {
    color: #e0e0e0;
  }
  
  .stat-label {
    color: #b0b0c0;
  }
  
  .action-card :deep(.el-card__body) {
    background-color: #282838;
    color: #e0e0e0;
  }
  
  .action-content h3 {
    color: #e0e0e0;
  }
  
  .action-content p {
    color: #b0b0c0;
  }
  
  .system-info :deep(.el-card__body) {
    background-color: #282838;
    color: #e0e0e0;
  }
  
  .info-item {
    border-bottom-color: #3c3c4c;
  }
  
  .info-label {
    color: #b0b0c0;
  }
  
  .info-value {
    color: #e0e0e0;
  }
}
</style> 