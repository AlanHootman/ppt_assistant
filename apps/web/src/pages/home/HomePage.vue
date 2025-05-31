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
        <div class="content-grid">
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
const taskCompleted = computed(() => 
  progressStore.taskStatus === 'completed' && !progressStore.taskError
)

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
/* ==========================================================================
   页面布局 - 使用现代Flexbox Grid布局
   ========================================================================== */

.home-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f8fafc;
}

/* ==========================================================================
   容器 - 响应式容器，支持不同屏幕尺寸
   ========================================================================== */

.container {
  width: 100%;
  max-width: 1400px; /* 限制最大宽度，避免超大屏幕内容过度拉伸 */
  margin: 0 auto;
  padding: 0 1rem;
}

/* 不同屏幕尺寸的容器调整 */
@media (min-width: 576px) {
  .container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 768px) {
  .container {
    padding: 0 2rem;
  }
}

@media (min-width: 1200px) {
  .container {
    padding: 0 3rem;
  }
}

/* ==========================================================================
   Header - 固定高度头部
   ========================================================================== */

.header {
  background-color: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 1rem 0;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}

.header .container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 1.5rem;
  font-weight: 600;
  color: #409eff;
  margin: 0;
  white-space: nowrap;
}

.nav {
  display: flex;
  align-items: center;
}

/* ==========================================================================
   Main Content - 自适应主内容区域
   ========================================================================== */

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 0;
  min-height: 0; /* 重要：允许flex子元素正确收缩 */
}

.main-content .container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* ==========================================================================
   Content Grid - 响应式网格布局
   ========================================================================== */

.content-grid {
  display: grid;
  gap: 1.5rem;
  flex: 1;
  min-height: 0;
  
  /* 默认单列布局（移动端） */
  grid-template-columns: 1fr;
  grid-template-rows: auto 1fr;
}

/* 平板及以上：双列布局 */
@media (min-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr;
    min-height: 500px; /* 确保最小高度 */
  }
}

/* 大屏幕：优化列宽比例 */
@media (min-width: 1024px) {
  .content-grid {
    grid-template-columns: 1.2fr 0.8fr; /* 左侧稍宽，更适合编辑 */
    gap: 2rem;
    min-height: 600px;
  }
}

/* 超大屏幕：进一步优化 */
@media (min-width: 1400px) {
  .content-grid {
    gap: 2.5rem;
    min-height: 650px;
  }
}

/* ==========================================================================
   Panel Styling - 面板样式
   ========================================================================== */

.editor-panel,
.preview-panel {
  background-color: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden; /* 防止内容溢出 */
}

/* 编辑器面板特殊处理 - 允许内容自然滚动 */
.editor-panel {
  overflow-y: auto; /* 允许垂直滚动 */
  scrollbar-width: thin; /* Firefox 细滚动条 */
  scrollbar-color: #c1c1c1 #f1f1f1; /* Firefox 滚动条颜色 */
}

/* Webkit滚动条样式优化 */
.editor-panel::-webkit-scrollbar {
  width: 6px;
}

.editor-panel::-webkit-scrollbar-track {
  background: transparent;
}

.editor-panel::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.editor-panel::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.3);
}

/* 面板内容布局 */
.editor-panel > *,
.preview-panel > * {
  flex-shrink: 0; /* 防止子元素被压缩 */
}

/* 预览面板特殊处理 - 让生成进度组件充分利用空间 */
.preview-panel {
  /* 确保预览面板内容能够充分利用空间 */
}

.preview-panel > * {
  flex-shrink: 0;
}

/* ChatStyleProgress组件占用大部分空间 */
.preview-panel > *:first-child {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 下载面板保持固定大小 */
.preview-panel > *:last-child:not(:first-child) {
  flex-shrink: 0;
  margin-top: 1rem;
}

/* 大屏幕面板优化 */
@media (min-width: 1024px) {
  .editor-panel,
  .preview-panel {
    padding: 2rem;
  }
}

/* ==========================================================================
   Footer - 固定高度底部
   ========================================================================== */

.footer {
  background-color: #f1f5f9;
  padding: 1rem 0;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
  flex-shrink: 0;
  border-top: 1px solid #e2e8f0;
}

/* ==========================================================================
   移动端适配
   ========================================================================== */

@media (max-width: 767px) {
  .header {
    padding: 0.75rem 0;
  }
  
  .logo {
    font-size: 1.25rem;
  }
  
  .main-content {
    padding: 1rem 0;
  }
  
  .content-grid {
    gap: 1rem;
  }
  
  .editor-panel,
  .preview-panel {
    padding: 1rem;
    border-radius: 8px;
  }
  
  .footer {
    padding: 0.75rem 0;
    font-size: 0.8rem;
  }
}

/* ==========================================================================
   打印和可访问性优化
   ========================================================================== */

@media print {
  .header,
  .footer {
    display: none;
  }
  
  .main-content {
    padding: 0;
  }
}

/* 高对比度模式支持 */
@media (prefers-contrast: high) {
  .editor-panel,
  .preview-panel {
    border: 2px solid #333;
  }
}

/* 减少动画效果（为有需要的用户） */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style> 