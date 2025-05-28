import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getClientId } from '@/utils/clientId'

export const useClientStore = defineStore('client', () => {
  // 从localStorage获取或生成新的客户端ID
  const clientId = ref(getClientId())
  
  // 当前会话关联的任务ID
  const currentTaskId = ref<string | null>(localStorage.getItem('current_task_id'))
  
  function setCurrentTask(taskId: string) {
    currentTaskId.value = taskId
    // 保存到localStorage
    localStorage.setItem('current_task_id', taskId)
  }
  
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