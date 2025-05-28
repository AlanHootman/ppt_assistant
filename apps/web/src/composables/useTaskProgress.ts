import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useProgressStore } from '@/stores/progress'
import { useClientStore } from '@/stores/client'
import WebSocketService from '@/services/websocket'
import * as pptApi from '@/services/api/ppt.api'
import type { TaskStatus } from '@/types/api'
import { useWebSocket } from './useWebSocket'
import { getClientId } from '@/utils/clientId'
import { useEditorStore } from '@/stores/editor'
import { useTemplateStore } from '@/stores/template'
import { ElMessage } from 'element-plus'

export function useTaskProgress() {
  const progressStore = useProgressStore()
  const clientStore = useClientStore()
  const editorStore = useEditorStore()
  const templateStore = useTemplateStore()
  const { connectWebSocket, disconnectWebSocket } = useWebSocket()
  
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // 当前任务ID
  const currentTaskId = computed(() => clientStore.currentTaskId)
  
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
  async function createPptTask() {
    const templateId = templateStore.currentTemplate?.id
    const markdownContent = editorStore.markdownContent
    
    if (!templateId) {
      error.value = '请先选择一个模板'
      ElMessage.error(error.value)
      return null
    }
    
    if (!markdownContent.trim()) {
      error.value = '请先输入Markdown内容'
      ElMessage.error(error.value)
      return null
    }
    
    loading.value = true
    error.value = null
    
    try {
      // 调用API创建任务
      const response = await pptApi.createTask({
        template_id: templateId,
        markdown_content: markdownContent,
        client_id: getClientId()
      })
      
      const taskId = response.data.task_id
      
      // 保存任务ID
      clientStore.setCurrentTask(taskId)
      
      // 设置任务状态为处理中
      progressStore.setTaskStatus('processing')
      progressStore.setIsGenerating(true)
      
      // 连接WebSocket获取实时进度
      connectWebSocket(taskId, handleProgressUpdate)
      
      return taskId
    } catch (err: any) {
      error.value = err.message || '创建任务失败'
      ElMessage.error(error.value)
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
      // 这里应该调用API获取任务状态
      // const response = await pptApi.getTaskStatus(taskId)
      
      // 模拟API响应
      const response = {
        data: {
          status: 'processing',
          progress: 30,
          current_step: 'content_planning',
          step_description: '正在进行内容规划'
        }
      }
      
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
      // 这里应该调用API重试任务
      // await pptApi.retryTask(taskId)
      
      // 连接WebSocket获取实时进度
      connectWebSocket(taskId, onTaskUpdate)
      
      return true
    } catch (err) {
      console.error('重试任务失败:', err)
      error.value = '重试任务失败'
      return false
    } finally {
      loading.value = false
    }
  }
  
  // 取消任务
  async function cancelTask() {
    if (!currentTaskId.value) return
    
    try {
      await pptApi.cancelTask(currentTaskId.value)
      
      // 断开WebSocket连接
      disconnectWebSocket()
      
      // 更新状态
      progressStore.setTaskStatus('cancelled')
      progressStore.setIsGenerating(false)
      
      ElMessage.info('任务已取消')
    } catch (err: any) {
      error.value = err.message || '取消任务失败'
      ElMessage.error(error.value)
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
  const taskCompleted = computed(() => progressStore.taskStatus === 'completed')
  
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
  
  /**
   * WebSocket任务更新回调
   */
  function onTaskUpdate(data: any) {
    progressStore.updateTaskProgress(data)
  }
  
  /**
   * 处理进度更新
   */
  function handleProgressUpdate(data: any) {
    // 更新任务状态和进度
    progressStore.updateTaskProgress(data)
    
    // 如果任务完成，断开WebSocket连接
    if (data.status === 'completed') {
      disconnectWebSocket()
      progressStore.setIsGenerating(false)
      ElMessage.success('PPT生成完成！')
    }
    
    // 如果任务失败，断开WebSocket连接
    if (data.status === 'failed') {
      disconnectWebSocket()
      progressStore.setIsGenerating(false)
      error.value = data.message || '任务执行失败'
      ElMessage.error(error.value)
    }
  }
  
  /**
   * 初始化任务进度
   * 如果有未完成的任务，恢复任务状态
   */
  async function initTaskProgress() {
    const taskId = currentTaskId.value
    if (!taskId) return
    
    try {
      // 获取任务详情
      const response = await pptApi.getTaskById(taskId)
      const taskData = response.data
      
      // 如果任务仍在进行中，连接WebSocket获取实时进度
      if (taskData.status === 'processing') {
        progressStore.setTaskStatus('processing')
        progressStore.setIsGenerating(true)
        connectWebSocket(taskId, handleProgressUpdate)
      } else if (taskData.status === 'completed') {
        progressStore.setTaskStatus('completed')
        progressStore.setIsGenerating(false)
      } else {
        // 其他状态（失败、取消等）
        progressStore.setTaskStatus(taskData.status)
        progressStore.setIsGenerating(false)
      }
    } catch (err) {
      // 获取任务失败，可能任务已过期或被删除
      clientStore.clearCurrentTask()
    }
  }
  
  /**
   * 获取任务下载链接
   */
  function getDownloadUrl(taskId: string) {
    return `${import.meta.env.VITE_API_BASE_URL}/tasks/${taskId}/download`
  }
  
  return {
    loading,
    error,
    isGenerating,
    progressMessages,
    previewImages,
    taskStatus,
    taskCompleted,
    createPptTask,
    getTaskStatus,
    retryTask,
    cancelTask,
    downloadPpt,
    getDownloadUrl,
    initTaskProgress
  }
} 