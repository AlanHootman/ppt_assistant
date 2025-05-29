<template>
  <div class="home-page">
    <header class="header">
      <div class="container">
        <h1 class="logo">PPT助手</h1>
        <div class="nav">
          <el-button type="primary" size="small" @click="navigateToAdmin" disabled title="管理后台功能正在开发中">管理后台</el-button>
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
import { onMounted, computed, getCurrentInstance, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { useProgressStore } from '../../stores/progress'
import { useTaskProgress } from '../../composables/useTaskProgress'

// 导入组件
const TemplateSelector = defineAsyncComponent(() => import('./TemplateSelector.vue'))
const EditorPanel = defineAsyncComponent(() => import('./EditorPanel.vue'))
const GenerationControls = defineAsyncComponent(() => import('./GenerationControls.vue'))
const ChatStyleProgress = defineAsyncComponent(() => import('./ChatStyleProgress.vue'))
const DownloadPanel = defineAsyncComponent(() => import('./DownloadPanel.vue'))

// 获取应用实例
const app = getCurrentInstance()
const ElMessage = app?.appContext.config.globalProperties.$message

const router = useRouter()
const progressStore = useProgressStore()
const { createPptTask, initTaskProgress } = useTaskProgress()

// 计算任务是否完成
const taskCompleted = computed(() => progressStore.taskStatus === 'completed')

// 导航到管理后台
function navigateToAdmin() {
  // 暂时禁用管理后台功能
  ElMessage ? ElMessage.info('管理后台功能正在开发中') : console.log('管理后台功能正在开发中')
  // router.push('/admin')
}

// 开始生成PPT
async function startGeneration() {
  try {
    // 重置进度状态
    progressStore.resetProgress()
    
    // 创建任务
    const taskId = await createPptTask()
    
    if (taskId) {
      // 使用条件方式调用 ElMessage
      ElMessage ? ElMessage.success('开始生成PPT，请稍候...') : console.log('开始生成PPT，请稍候...')
    }
  } catch (error) {
    console.error('生成PPT失败:', error)
    ElMessage ? ElMessage.error('生成PPT失败，请重试') : console.log('生成PPT失败，请重试')
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
  overflow: hidden; /* 避免页面滚动 */
}

.header {
  background-color: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 8px 0; /* 减少顶部和底部的padding */
  flex-shrink: 0; /* 不允许缩放 */
}

.header .container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 1.3rem; /* 稍微减小字体 */
  color: #409eff;
  margin: 0;
}

.main-content {
  flex: 1;
  padding: 15px 0; /* 减少上下padding */
  overflow: hidden; /* 避免主内容区域滚动 */
}

.responsive-container {
  height: 100%; /* 使用全部可用高度 */
}

.editor-panel, .preview-panel {
  padding: 10px; /* 减少内边距 */
  flex: 1;
  height: 100%; /* 使用全部高度 */
  overflow: hidden; /* 避免面板滚动 */
}

.footer {
  background-color: #f5f7fa;
  padding: 8px 0; /* 减少上下padding */
  text-align: center;
  color: #606266;
  font-size: 0.8rem; /* 减小字体 */
  flex-shrink: 0; /* 不允许缩放 */
}

@media (max-width: 768px) {
  .editor-panel, .preview-panel {
    width: 100%;
  }
}
</style> 