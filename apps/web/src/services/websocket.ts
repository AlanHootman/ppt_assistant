import { useProgressStore } from '@/stores/progress'
import { getClientId } from '@/utils/clientId'

class WebSocketService {
  private socket: WebSocket | null = null
  private taskId: string | null = null
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectTimeout: number = 3000 // 重连间隔（毫秒）
  private reconnectTimer: number | null = null
  
  /**
   * 连接到WebSocket服务
   * @param taskId 任务ID
   */
  connect(taskId: string) {
    this.taskId = taskId
    const clientId = getClientId()
    
    // 构建WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = window.location.host
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/ws/tasks/${taskId}?client_id=${clientId}`
    
    // 关闭现有连接
    this.disconnect()
    
    try {
      // 创建WebSocket连接
      this.socket = new WebSocket(wsUrl)
      
      // 连接打开
      this.socket.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
      }
      
      // 接收消息
      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('WebSocket message received:', data)
          
          // 更新进度
          const progressStore = useProgressStore()
          progressStore.updateTaskProgress(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      // 连接关闭
      this.socket.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        this.socket = null
        
        // 尝试重连，除非是主动关闭
        if (this.taskId && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect()
        }
      }
      
      // 连接错误
      this.socket.onerror = (error) => {
        console.error('WebSocket connection error:', error)
      }
      
      return this.socket
    } catch (error) {
      console.error('WebSocket initialization error:', error)
      return null
    }
  }
  
  /**
   * 断开WebSocket连接
   */
  disconnect() {
    // 清除重连定时器
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    
    // 关闭WebSocket连接
    if (this.socket) {
      // 注销所有事件处理器
      this.socket.onopen = null
      this.socket.onmessage = null
      this.socket.onclose = null
      this.socket.onerror = null
      
      // 如果连接还处于打开状态，则关闭
      if (this.socket.readyState === WebSocket.OPEN || 
          this.socket.readyState === WebSocket.CONNECTING) {
        this.socket.close()
      }
      
      this.socket = null
    }
    
    this.taskId = null
    this.reconnectAttempts = 0
  }
  
  /**
   * 安排重新连接
   */
  private scheduleReconnect() {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
    }
    
    this.reconnectAttempts++
    console.log(`Scheduling WebSocket reconnect attempt ${this.reconnectAttempts} of ${this.maxReconnectAttempts}...`)
    
    this.reconnectTimer = window.setTimeout(() => {
      console.log(`Attempting to reconnect WebSocket, attempt ${this.reconnectAttempts}...`)
      if (this.taskId) {
        this.connect(this.taskId)
      }
    }, this.reconnectTimeout)
  }
  
  /**
   * 检查WebSocket是否已连接
   */
  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN
  }
  
  /**
   * 获取当前连接的任务ID
   */
  getTaskId(): string | null {
    return this.taskId
  }
}

// 导出单例
export default new WebSocketService() 