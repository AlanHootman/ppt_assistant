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
import { useClientStore } from '@/stores/client'
import { useProgressStore } from '@/stores/progress'
import { useEditorStore } from '@/stores/editor'
import { useTaskProgress } from '@/composables/useTaskProgress'
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
.download-panel {
  background-color: #f0f9eb;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
  border-left: 4px solid #67c23a;
}

.title {
  font-size: 1.2rem;
  margin-top: 0;
  margin-bottom: 15px;
  color: #67c23a;
}

.success-message {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  color: #606266;
}

.success-icon {
  font-size: 24px;
  color: #67c23a;
  margin-right: 10px;
}

.download-actions {
  display: flex;
  gap: 15px;
  margin-top: 20px;
}

.download-button {
  background-color: #67c23a;
  border-color: #67c23a;
}

.download-button:hover {
  background-color: #85ce61;
  border-color: #85ce61;
}
</style> 