<template>
  <div class="home-page">
    <header class="header">
      <div class="container">
        <h1 class="logo">PPT助手</h1>
        <div class="nav">
          <el-button type="primary" size="small" @click="navigateToAdmin">管理后台</el-button>
        </div>
      </div>
    </header>
    
    <main class="main-content">
      <div class="container">
        <div class="flex-row responsive-container">
          <!-- 左侧编辑区域 -->
          <div class="editor-panel">
            <template-selector />
            <editor-panel />
            <generation-controls @generate="startGeneration" />
          </div>
          
          <!-- 右侧预览和任务进度区域 -->
          <div class="preview-panel">
            <chat-style-progress />
            <download-panel v-if="taskCompleted" />
          </div>
        </div>
      </div>
    </main>
    
    <footer class="footer">
      <div class="container">
        <p>PPT助手 © {{ new Date().getFullYear() }}</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useProgressStore } from '@/stores/progress'
import { useTaskProgress } from '@/composables/useTaskProgress'

// 导入组件
import TemplateSelector from './TemplateSelector.vue'
import EditorPanel from './EditorPanel.vue'
import GenerationControls from './GenerationControls.vue'
import ChatStyleProgress from './ChatStyleProgress.vue'
import DownloadPanel from './DownloadPanel.vue'

const router = useRouter()
const progressStore = useProgressStore()
const { createPptTask, initTaskProgress } = useTaskProgress()

// 计算任务是否完成
const taskCompleted = computed(() => progressStore.taskStatus === 'completed')

// 导航到管理后台
function navigateToAdmin() {
  router.push('/admin')
}

// 开始生成PPT
async function startGeneration() {
  try {
    // 重置进度状态
    progressStore.resetProgress()
    
    // 创建任务
    const taskId = await createPptTask()
    
    if (taskId) {
      ElMessage.success('开始生成PPT，请稍候...')
    }
  } catch (error) {
    console.error('生成PPT失败:', error)
    ElMessage.error('生成PPT失败，请重试')
  }
}

// 组件挂载时初始化
onMounted(() => {
  // 检查是否有未完成的任务
  initTaskProgress()
})
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  background-color: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 15px 0;
}

.header .container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 1.5rem;
  color: #409eff;
  margin: 0;
}

.main-content {
  flex: 1;
  padding: 30px 0;
}

.editor-panel, .preview-panel {
  padding: 15px;
  flex: 1;
}

.footer {
  background-color: #f5f7fa;
  padding: 15px 0;
  text-align: center;
  color: #606266;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .editor-panel, .preview-panel {
    width: 100%;
  }
}
</style> 