import { defineStore } from 'pinia'
import { ref } from 'vue'
import { nanoid } from 'nanoid'

// 进度消息接口
export interface ProgressMessage {
  id: string
  time: Date
  step: string
  message: string
  progress: number
  isError?: boolean // 添加错误标识
}

// 预览图片接口
export interface PreviewImage {
  id: string
  url: string
  time: Date
}

// 错误信息接口
export interface TaskError {
  has_error: boolean
  error_code?: string
  error_message?: string
  can_retry: boolean
}

// 任务状态类型
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'

export const useProgressStore = defineStore('progress', () => {
  // 任务状态
  const taskStatus = ref<TaskStatus | null>(null)
  // 进度消息列表
  const progressMessages = ref<ProgressMessage[]>([])
  // 预览图片列表
  const previewImages = ref<PreviewImage[]>([])
  // 是否正在生成
  const isGenerating = ref(false)
  // 错误信息
  const taskError = ref<TaskError | null>(null)
  
  /**
   * 更新任务进度
   */
  function updateTaskProgress(progressData: any) {
    // 适配API返回格式
    const data = progressData.data ? progressData.data : progressData
    
    // 更新任务状态
    if (data.status) {
      taskStatus.value = data.status
    }
    
    // 处理错误信息
    if (data.error) {
      taskError.value = data.error
    } else if (data.status === 'failed') {
      // 如果状态为failed但没有error字段，创建默认错误信息
      taskError.value = {
        has_error: true,
        error_code: 'UNKNOWN_ERROR',
        error_message: data.step_description || '任务执行失败',
        can_retry: true
      }
    } else {
      // 非错误状态时清除错误信息
      taskError.value = null
    }
    
    // 添加进度消息
    if (data.step_description) {
      const message: ProgressMessage = {
        id: nanoid(),
        time: new Date(),
        step: data.current_step || '处理中',
        message: data.step_description,
        progress: data.progress || 0,
        isError: data.status === 'failed' // 标记是否为错误消息
      }
      progressMessages.value.push(message)
    }
    
    // 添加预览图片
    if (data.preview_url) {
      const preview: PreviewImage = {
        id: nanoid(),
        url: data.preview_url,
        time: new Date()
      }
      previewImages.value.push(preview)
    }
    
    // 处理多个预览图
    if (data.preview_images && Array.isArray(data.preview_images)) {
      data.preview_images.forEach((img: any) => {
        if (img.preview_url) {
          const preview: PreviewImage = {
            id: nanoid(),
            url: img.preview_url,
            time: new Date()
          }
          // 检查是否已存在相同URL的预览图
          const exists = previewImages.value.some(p => p.url === img.preview_url)
          if (!exists) {
            previewImages.value.push(preview)
          }
        }
      })
    }
  }
  
  /**
   * 设置任务状态
   */
  function setTaskStatus(status: TaskStatus) {
    taskStatus.value = status
  }
  
  /**
   * 设置是否正在生成
   */
  function setIsGenerating(value: boolean) {
    isGenerating.value = value
  }
  
  /**
   * 重置进度状态
   */
  function resetProgress() {
    taskStatus.value = null
    progressMessages.value = []
    previewImages.value = []
    isGenerating.value = false
    taskError.value = null
  }
  
  return { 
    taskStatus, 
    progressMessages, 
    previewImages, 
    isGenerating, 
    taskError,
    updateTaskProgress,
    setTaskStatus,
    setIsGenerating,
    resetProgress
  }
}) 