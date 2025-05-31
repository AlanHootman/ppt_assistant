<template>
  <div class="download-panel">
    <h2 class="title">生成完成!</h2>
    
    <div class="success-message">
      <el-icon class="success-icon"><i class="el-icon-check"></i></el-icon>
      <p>您的PPT已经生成完成，可以下载使用</p>
    </div>
    
    <div class="download-actions">
      <el-button 
        type="primary" 
        size="large" 
        @click="handleDownload"
        class="download-button"
      >
        下载PPT文件
      </el-button>
      
      <el-button 
        type="info" 
        size="large" 
        @click="handleNewTask"
      >
        创建新的PPT
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useClientStore } from '../../stores/client'
import { useProgressStore } from '../../stores/progress'
import { useEditorStore } from '../../stores/editor'
import { useTaskProgress } from '../../composables/useTaskProgress'
import { ElMessage } from 'element-plus'

const clientStore = useClientStore()
const progressStore = useProgressStore()
const editorStore = useEditorStore()
const { getDownloadUrl } = useTaskProgress()

// 处理下载
function handleDownload() {
  const taskId = clientStore.currentTaskId
  
  if (!taskId) {
    ElMessage.error('找不到任务ID，无法下载')
    return
  }
  
  // 获取下载链接
  const downloadUrl = getDownloadUrl(taskId)
  
  // 创建一个隐藏的a标签，用于下载
  const a = document.createElement('a')
  a.href = downloadUrl
  a.download = `ppt_${taskId}.pptx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  ElMessage.success('开始下载PPT文件')
}

// 开始新任务
function handleNewTask() {
  // 清除当前任务
  clientStore.clearCurrentTask()
  
  // 重置进度状态
  progressStore.resetProgress()
  
  // 保留编辑器内容，允许用户继续修改
  ElMessage.success('已重置，可以创建新的PPT')
}
</script>

<style scoped>
/* ==========================================================================
   下载面板 - 紧凑式布局
   ========================================================================== */

.download-panel {
  background-color: #f0f9eb;
  border-radius: 8px;
  padding: 1rem;
  border-left: 4px solid #67c23a;
  flex-shrink: 0; /* 防止被压缩 */
}

.title {
  font-size: 1.1rem;
  margin: 0 0 0.75rem 0;
  color: #67c23a;
  font-weight: 600;
}

.success-message {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
  color: #606266;
}

.success-icon {
  font-size: 1.25rem;
  color: #67c23a;
  margin-right: 0.5rem;
  flex-shrink: 0;
}

.success-message p {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.4;
}

.download-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.download-button {
  background-color: #67c23a;
  border-color: #67c23a;
  height: 36px;
  font-size: 0.875rem;
}

.download-button:hover {
  background-color: #85ce61;
  border-color: #85ce61;
}

/* 响应式优化 */
@media (max-width: 767px) {
  .download-panel {
    padding: 0.75rem;
  }
  
  .title {
    font-size: 1rem;
    margin-bottom: 0.5rem;
  }
  
  .success-message {
    margin-bottom: 0.75rem;
  }
  
  .success-message p {
    font-size: 0.8rem;
  }
  
  .download-actions {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .download-actions .el-button {
    width: 100%;
    height: 32px;
    font-size: 0.8rem;
  }
}
</style> 