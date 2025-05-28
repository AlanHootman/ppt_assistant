import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getClientId } from '@/utils/clientId'

export const useClientStore = defineStore('client', () => {
  // 客户端ID
  const clientId = ref(getClientId())
  
  // 当前会话关联的任务ID
  const currentTaskId = ref<string | null>(
    localStorage.getItem('current_task_id')
  )
  
  /**
   * 设置当前任务
   */
  function setCurrentTask(taskId: string) {
    currentTaskId.value = taskId
    // 保存到localStorage
    localStorage.setItem('current_task_id', taskId)
  }
  
  /**
   * 清除当前任务
   */
  function clearCurrentTask() {
    currentTaskId.value = null
    localStorage.removeItem('current_task_id')
  }
  
  return { 
    clientId, 
    currentTaskId, 
    setCurrentTask, 
    clearCurrentTask 
  }
}) 