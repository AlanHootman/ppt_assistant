import { ref } from 'vue'
import { getClientId } from '@/utils/clientId'

export function useWebSocket() {
  // WebSocket连接对象
  const socket = ref<WebSocket | null>(null)
  // 当前连接的任务ID
  const currentTaskId = ref<string | null>(null)
  // 是否已连接
  const isConnected = ref(false)
  // 重连尝试次数
  const reconnectAttempts = ref(0)
  // 最大重连尝试次数
  const maxReconnectAttempts = 5
  // 重连定时器
  let reconnectTimer: number | null = null
  
  /**
   * 获取WebSocket服务器URL
   */
  function getWebSocketBaseUrl(): string {
    // 开发环境：使用后端API服务器地址
    if (import.meta.env.DEV) {
      return 'ws://localhost:8000'
    }
    
    // 生产环境：使用当前域名，但协议改为ws/wss
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}`
  }
  
  /**
   * 连接WebSocket
   * @param taskId 任务ID
   * @param onUpdate 更新回调函数
   */
  function connectWebSocket(taskId: string, onUpdate: (data: any) => void) {
    // 如果已经连接到相同的任务，不需要重新连接
    if (isConnected.value && currentTaskId.value === taskId) {
      console.log('WebSocket already connected to this task')
      return
    }
    
    // 如果已经连接到其他任务，先断开连接
    if (socket.value) {
      disconnectWebSocket()
    }
    
    // 构建WebSocket URL
    const clientId = getClientId()
    const baseUrl = getWebSocketBaseUrl()
    const wsUrl = `${baseUrl}/api/v1/ws/tasks/${taskId}?client_id=${clientId}`
    
    console.log('Connecting to WebSocket:', wsUrl)
    
    try {
      // 创建WebSocket连接
      socket.value = new WebSocket(wsUrl)
      
      // 连接打开
      socket.value.onopen = () => {
        isConnected.value = true
        currentTaskId.value = taskId
        reconnectAttempts.value = 0
        console.log('WebSocket连接成功:', wsUrl)
      }
      
      // 接收消息
      socket.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('收到任务进度更新:', data)
          
          // 过滤连接确认消息
          if (data.type === 'connection_established') {
            console.log('WebSocket连接确认')
            return
          }
          
          onUpdate(data)
        } catch (error) {
          console.error('解析WebSocket消息失败:', error)
        }
      }
      
      // 连接关闭
      socket.value.onclose = (event) => {
        console.log('WebSocket连接断开:', event.code, event.reason)
        isConnected.value = false
        socket.value = null
        
        // 尝试重连，除非是主动关闭
        if (currentTaskId.value && reconnectAttempts.value < maxReconnectAttempts) {
          scheduleReconnect(taskId, onUpdate)
        }
      }
      
      // 连接错误
      socket.value.onerror = (error) => {
        console.error('WebSocket连接错误:', error)
        isConnected.value = false
      }
    } catch (error) {
      console.error('创建WebSocket连接失败:', error)
      isConnected.value = false
      socket.value = null
    }
  }
  
  /**
   * 断开WebSocket连接
   */
  function disconnectWebSocket() {
    // 清除重连定时器
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    // 关闭WebSocket连接
    if (socket.value) {
      // 注销所有事件处理器
      socket.value.onopen = null
      socket.value.onmessage = null
      socket.value.onclose = null
      socket.value.onerror = null
      
      // 如果连接还处于打开状态，则关闭
      if (socket.value.readyState === WebSocket.OPEN || 
          socket.value.readyState === WebSocket.CONNECTING) {
        socket.value.close()
      }
      
      socket.value = null
    }
    
    isConnected.value = false
    currentTaskId.value = null
    reconnectAttempts.value = 0
  }
  
  /**
   * 安排重新连接
   */
  function scheduleReconnect(taskId: string, onUpdate: (data: any) => void) {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
    }
    
    reconnectAttempts.value++
    console.log(`安排WebSocket重连尝试 ${reconnectAttempts.value}/${maxReconnectAttempts}...`)
    
    reconnectTimer = window.setTimeout(() => {
      console.log(`正在尝试重新连接WebSocket，尝试次数: ${reconnectAttempts.value}...`)
      connectWebSocket(taskId, onUpdate)
    }, 3000) // 3秒后重试
  }
  
  return {
    isConnected,
    currentTaskId,
    connectWebSocket,
    disconnectWebSocket
  }
} 