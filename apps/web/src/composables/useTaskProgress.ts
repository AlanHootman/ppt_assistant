import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useProgressStore } from '@/stores/progress'
import { useClientStore } from '@/stores/client'
import WebSocketService from '@/services/websocket'
import * as pptApi from '@/services/api/ppt.api'
import type { TaskStatus } from '@/types/api'

export function useTaskProgress() {
  const progressStore = useProgressStore()
  const clientStore = useClientStore()
  
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // 初始化WebSocket连接
  function initWebSocket(taskId: string) {
    // 如果已经连接到同一个任务，不需要重新连接
    if (WebSocketService.isConnected() && WebSocketService.getTaskId() === taskId) {
      return
    }
    
    // 如果已连接到其他任务，先断开
    if (WebSocketService.isConnected()) {
      WebSocketService.disconnect()
    }
    
    // 连接到新任务
    WebSocketService.connect(taskId)
    
    // 更新当前任务ID
    clientStore.setCurrentTask(taskId)
  }
  
  // 创建PPT生成任务
  async function createPptTask(templateId: number, markdownContent: string) {
    loading.value = true
    error.value = null
    progressStore.resetProgress()
    
    try {
      const response = await pptApi.createPptTask({
        template_id: templateId,
        markdown_content: markdownContent
      })
      
      const taskId = response.data.task_id
      
      // 初始化WebSocket连接
      initWebSocket(taskId)
      
      return taskId
    } catch (err) {
      console.error('创建PPT生成任务失败:', err)
      error.value = '创建PPT生成任务失败'
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 获取任务状态
  async function getTaskStatus(taskId: string) {
    loading.value = true
    error.value = null
    
    try {
      const response = await pptApi.getTaskStatus(taskId)
      // 更新进度状态
      progressStore.updateTaskProgress(response.data)
      return response.data
    } catch (err) {
      console.error('获取任务状态失败:', err)
      error.value = '获取任务状态失败'
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 重试任务
  async function retryTask(taskId: string) {
    loading.value = true
    error.value = null
    
    try {
      const response = await pptApi.retryTask(taskId)
      // 初始化WebSocket连接
      initWebSocket(taskId)
      return response.data
    } catch (err) {
      console.error('重试任务失败:', err)
      error.value = '重试任务失败'
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 取消任务
  async function cancelTask(taskId: string) {
    loading.value = true
    error.value = null
    
    try {
      const response = await pptApi.cancelTask(taskId)
      // 断开WebSocket连接
      WebSocketService.disconnect()
      // 清除当前任务
      clientStore.clearCurrentTask()
      return response.data
    } catch (err) {
      console.error('取消任务失败:', err)
      error.value = '取消任务失败'
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 下载PPT
  function downloadPpt(taskId: string) {
    pptApi.downloadPpt(taskId)
  }
  
  // 计算属性
  const isGenerating = computed(() => progressStore.isGenerating)
  const progressMessages = computed(() => progressStore.progressMessages)
  const previewImages = computed(() => progressStore.previewImages)
  const taskStatus = computed(() => progressStore.taskStatus)
  
  // 组件挂载时，检查是否有未完成的任务
  onMounted(() => {
    const taskId = clientStore.currentTaskId
    if (taskId) {
      // 获取任务状态
      getTaskStatus(taskId).then((status) => {
        if (status && (status.status === 'pending' || status.status === 'processing')) {
          // 如果任务还在进行中，重新连接WebSocket
          initWebSocket(taskId)
        }
      })
    }
  })
  
  // 组件卸载时，断开WebSocket连接
  onUnmounted(() => {
    if (WebSocketService.isConnected()) {
      WebSocketService.disconnect()
    }
  })
  
  return {
    loading,
    error,
    isGenerating,
    progressMessages,
    previewImages,
    taskStatus,
    createPptTask,
    getTaskStatus,
    retryTask,
    cancelTask,
    downloadPpt
  }
} 