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
        <p>&copy; 2023 PPT助手 - 自动生成精美演示文稿</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProgressStore } from '@/stores/progress'
import { useTemplateStore } from '@/stores/template'
import { useTaskProgress } from '@/composables/useTaskProgress'
import { useEditorStore } from '@/stores/editor'

import TemplateSelector from './TemplateSelector.vue'
import EditorPanel from './EditorPanel.vue'
import GenerationControls from './GenerationControls.vue'
import ChatStyleProgress from './ChatStyleProgress.vue'
import DownloadPanel from './DownloadPanel.vue'

const router = useRouter()
const progressStore = useProgressStore()
const templateStore = useTemplateStore()
const editorStore = useEditorStore()
const { createPptTask } = useTaskProgress()

// 计算任务是否完成
const taskCompleted = computed(() => progressStore.taskStatus === 'completed')

// 开始生成PPT
async function startGeneration() {
  if (!templateStore.currentTemplate) {
    // 提示选择模板
    ElMessage.warning('请先选择一个模板')
    return
  }
  
  if (!editorStore.markdownContent.trim()) {
    // 提示输入内容
    ElMessage.warning('请输入Markdown内容')
    return
  }
  
  // 开始生成任务
  const templateId = templateStore.currentTemplate.id
  const markdownContent = editorStore.markdownContent
  
  const taskId = await createPptTask(templateId, markdownContent)
  
  if (!taskId) {
    ElMessage.error('创建PPT生成任务失败')
  }
}

// 导航到管理后台
function navigateToAdmin() {
  router.push('/admin')
}
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1rem 0;
}

.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.header .container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: #409eff;
  margin: 0;
}

.main-content {
  flex: 1;
  padding: 2rem 0;
  background-color: #f5f7fa;
}

.responsive-container {
  display: flex;
  gap: 2rem;
}

.editor-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.preview-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.footer {
  background-color: #fff;
  padding: 1rem 0;
  text-align: center;
  font-size: 0.9rem;
  color: #606266;
}

@media (max-width: 768px) {
  .responsive-container {
    flex-direction: column;
  }
}
</style> 