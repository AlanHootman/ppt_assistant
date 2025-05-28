import { defineStore } from 'pinia'
import { ref } from 'vue'
import { nanoid } from 'nanoid'

// 进度消息接口
interface ProgressMessage {
  id: string
  time: Date
  step: string
  message: string
  progress: number
}

// 预览图片接口
interface PreviewImage {
  id: string
  url: string
  time: Date
}

// 任务状态枚举
type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | null

export const useProgressStore = defineStore('progress', () => {
  const taskStatus = ref<TaskStatus>(null)
  const progressMessages = ref<ProgressMessage[]>([])
  const previewImages = ref<PreviewImage[]>([])
  const isGenerating = ref(false)
  
  function updateTaskProgress(progressData: any) {
    // 更新任务状态
    if (progressData.status) {
      taskStatus.value = progressData.status
    }
    
    // 添加新的进度消息
    if (progressData.step_description) {
      progressMessages.value.push({
        id: nanoid(),
        time: new Date(),
        step: progressData.current_step,
        message: progressData.step_description,
        progress: progressData.progress
      })
    }
    
    // 更新预览图
    if (progressData.preview_data && progressData.preview_data.images) {
      previewImages.value = [
        ...previewImages.value,
        ...progressData.preview_data.images.map((img: string) => ({
          id: nanoid(),
          url: img,
          time: new Date()
        }))
      ]
    }
    
    // 更新生成状态
    isGenerating.value = progressData.status === 'processing'
  }
  
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
    resetProgress
  }
}) 