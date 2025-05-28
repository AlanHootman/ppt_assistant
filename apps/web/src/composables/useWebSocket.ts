import { ref } from 'vue'
import { io, Socket } from 'socket.io-client'
import { getClientId } from '@/utils/clientId'

export function useWebSocket() {
  // WebSocket连接对象
  const socket = ref<Socket | null>(null)
  // 当前连接的任务ID
  const currentTaskId = ref<string | null>(null)
  // 是否已连接
  const isConnected = ref(false)
  
  /**
   * 连接WebSocket
   * @param taskId 任务ID
   * @param onUpdate 更新回调函数
   */
  function connectWebSocket(taskId: string, onUpdate: (data: any) => void) {
    // 如果已经连接到相同的任务，不需要重新连接
    if (isConnected.value && currentTaskId.value === taskId) {
      return
    }
    
    // 如果已经连接到其他任务，先断开连接
    if (socket.value) {
      disconnectWebSocket()
    }
    
    // 创建WebSocket连接
    const clientId = getClientId()
    const wsUrl = getWebSocketUrl(taskId, clientId)
    
    try {
      socket.value = io(wsUrl)
      
      // 连接成功
      socket.value.on('connect', () => {
        isConnected.value = true
        currentTaskId.value = taskId
        console.log('WebSocket连接成功:', taskId)
      })
      
      // 接收任务进度更新
      socket.value.on('task_progress', (data) => {
        console.log('收到任务进度更新:', data)
        onUpdate(data)
      })
      
      // 连接错误
      socket.value.on('connect_error', (error) => {
        console.error('WebSocket连接错误:', error)
        isConnected.value = false
      })
      
      // 连接断开
      socket.value.on('disconnect', () => {
        console.log('WebSocket连接断开')
        isConnected.value = false
      })
    } catch (error) {
      console.error('创建WebSocket连接失败:', error)
    }
  }
  
  /**
   * 断开WebSocket连接
   */
  function disconnectWebSocket() {
    if (socket.value) {
      socket.value.disconnect()
      socket.value = null
    }
    
    isConnected.value = false
    currentTaskId.value = null
  }
  
  /**
   * 获取WebSocket URL
   */
  function getWebSocketUrl(taskId: string, clientId: string) {
    const wsHost = import.meta.env.VITE_WS_HOST || 'localhost:8000'
    const wsPath = import.meta.env.VITE_WS_PATH || '/api/v1/ws'
    return `ws://${wsHost}${wsPath}/tasks/${taskId}?client_id=${clientId}`
  }
  
  return {
    isConnected,
    currentTaskId,
    connectWebSocket,
    disconnectWebSocket
  }
} 