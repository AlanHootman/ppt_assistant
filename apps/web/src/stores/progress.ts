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
}

// 预览图片接口
export interface PreviewImage {
  id: string
  url: string
  time: Date
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
    
    // 添加进度消息
    if (data.step_description) {
      const message: ProgressMessage = {
        id: nanoid(),
        time: new Date(),
        step: data.current_step || '处理中',
        message: data.step_description,
        progress: data.progress || 0
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
  }
  
  return { 
    taskStatus, 
    progressMessages, 
    previewImages, 
    isGenerating, 
    updateTaskProgress,
    setTaskStatus,
    setIsGenerating,
    resetProgress
  }
}) 