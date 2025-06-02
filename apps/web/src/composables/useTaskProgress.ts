import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useProgressStore } from '@/stores/progress'
import { useClientStore } from '@/stores/client'
import WebSocketService from '@/services/websocket'
import { pptApi } from '@/services/api/ppt.api'
import { getClientId } from '@/utils/clientId'
import { useEditorStore } from '@/stores/editor'
import { useTemplateStore } from '@/stores/template'
import { ElMessage } from 'element-plus'

export function useTaskProgress() {
  const progressStore = useProgressStore()
  const clientStore = useClientStore()
  const editorStore = useEditorStore()
  const templateStore = useTemplateStore()
  
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // 当前任务ID
  const currentTaskId = computed(() => clientStore.currentTaskId)
  
  // 连接WebSocket
  function connectWebSocket(taskId: string) {
    WebSocketService.connect(taskId)
  }
  
  // 断开WebSocket连接
  function disconnectWebSocket() {
    WebSocketService.disconnect()
  }
  
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
  async function createPptTask(options: { enableMultimodalValidation: boolean } = { enableMultimodalValidation: false }) {
    const templateId = templateStore.currentTemplate?.id
    const markdownContent = editorStore.markdownContent
    
    if (!templateId) {
      error.value = '请先选择一个模板'
      ElMessage.error('请先选择一个模板')
      return null
    }
    
    if (!markdownContent.trim()) {
      error.value = '请先输入Markdown内容'
      ElMessage.error('请先输入Markdown内容')
      return null
    }
    
    loading.value = true
    error.value = null
    
    try {
      // 调用API创建任务
      const response = await pptApi.createTask({
        template_id: templateId,
        markdown_content: markdownContent,
        client_id: getClientId(),
        enable_multimodal_validation: options.enableMultimodalValidation
      })
      
      // 获取任务ID
      const taskId = response.data.task_id
      
      // 保存任务ID
      clientStore.setCurrentTask(taskId)
      
      // 设置任务状态为处理中
      progressStore.setTaskStatus('processing')
      progressStore.setIsGenerating(true)
      
      // 连接WebSocket获取实时进度
      connectWebSocket(taskId)
      
      return taskId
    } catch (err: any) {
      error.value = err.message || '创建任务失败'
      ElMessage.error(err.message || '创建任务失败')
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
      // 调用API获取任务状态
      const response = await pptApi.getTaskById(taskId)
      const taskData = response.data
      
      // 更新进度状态
      progressStore.updateTaskProgress(taskData)
      
      return taskData
    } catch (err: any) {
      console.error('获取任务状态失败:', err)
      error.value = '获取任务状态失败'
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 取消任务
  async function cancelTask() {
    const taskId = currentTaskId.value
    if (!taskId) return
    
    try {
      await pptApi.cancelTask(taskId)
      
      // 断开WebSocket连接
      disconnectWebSocket()
      
      // 更新状态
      progressStore.setTaskStatus('cancelled')
      progressStore.setIsGenerating(false)
      
      ElMessage.info('任务已取消')
    } catch (err: any) {
      error.value = err.message || '取消任务失败'
      ElMessage.error(err.message || '取消任务失败')
    }
  }
  
  // 下载PPT
  function downloadPpt(taskId: string) {
    window.location.href = pptApi.getTaskDownloadUrl(taskId)
  }
  
  // 计算属性
  const isGenerating = computed(() => progressStore.isGenerating)
  const progressMessages = computed(() => progressStore.progressMessages)
  const previewImages = computed(() => progressStore.previewImages)
  const taskStatus = computed(() => progressStore.taskStatus)
  const taskCompleted = computed(() => progressStore.taskStatus === 'completed')
  
  // 组件挂载时，检查是否有未完成的任务
  onMounted(() => {
    const taskId = currentTaskId.value
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
    
    // 如果任务失败，立即断开WebSocket连接并重置状态
    if (data.status === 'failed') {
      disconnectWebSocket()
      progressStore.setIsGenerating(false)
      
      // 优先使用error字段中的错误信息
      let errorMessage = '任务执行失败'
      if (data.error && data.error.error_message) {
        errorMessage = data.error.error_message
      } else if (data.step_description) {
        errorMessage = data.step_description
      } else if (data.message) {
        errorMessage = data.message
      }
      
      error.value = errorMessage
      ElMessage.error(errorMessage)
      return // 错误状态直接返回，不处理完成逻辑
    }
    
    // 只有在非错误状态下才处理完成逻辑
    if (data.status === 'completed' && progressStore.taskStatus !== 'failed') {
      disconnectWebSocket()
      progressStore.setIsGenerating(false)
      ElMessage.success('PPT生成完成！')
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
      
      // 根据任务状态更新UI
      if (taskData.status === 'processing' || taskData.status === 'pending') {
        progressStore.setTaskStatus(taskData.status)
        progressStore.setIsGenerating(true)
        connectWebSocket(taskId)
      } else if (taskData.status === 'completed') {
        progressStore.setTaskStatus('completed')
        progressStore.setIsGenerating(false)
      } else if (taskData.status === 'failed') {
        progressStore.setTaskStatus('failed')
        progressStore.setIsGenerating(false)
        if (taskData.error && taskData.error.error_message) {
          error.value = taskData.error.error_message
          ElMessage.error(taskData.error.error_message)
        }
      }
      
      // 更新进度数据
      progressStore.updateTaskProgress(taskData)
    } catch (err) {
      console.error('获取任务详情失败:', err)
      // 清除任务ID
      clientStore.clearCurrentTask()
    }
  }
  
  // 获取下载链接
  function getDownloadUrl(taskId: string): string {
    return pptApi.getTaskDownloadUrl(taskId)
  }
  
  return {
    createPptTask,
    getTaskStatus,
    cancelTask,
    downloadPpt,
    initTaskProgress,
    getDownloadUrl,
    loading,
    error,
    isGenerating,
    progressMessages,
    previewImages,
    taskStatus,
    taskCompleted
  }
} 