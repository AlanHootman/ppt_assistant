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
   * 获取WebSocket服务器URL
   */
  private getWebSocketBaseUrl(): string {
    // 使用相对路径，让Nginx正确代理WebSocket请求
    // 这样在Docker环境和开发环境下都能正常工作
    return window.location.protocol === 'https:' 
      ? `wss://${window.location.host}`
      : `ws://${window.location.host}`
  }
  
  /**
   * 连接到WebSocket服务
   * @param taskId 任务ID
   */
  connect(taskId: string) {
    // 如果已经连接到同一个任务，不需要重新连接
    if (this.taskId === taskId && this.isConnected()) {
      console.log('WebSocket already connected to this task')
      return this.socket
    }
    
    this.taskId = taskId
    const clientId = getClientId()
    
    // 构建WebSocket URL
    const baseUrl = this.getWebSocketBaseUrl()
    const wsUrl = `${baseUrl}/api/v1/ws/tasks/${taskId}?client_id=${clientId}`
    
    console.log('Connecting to WebSocket:', wsUrl)
    
    // 关闭现有连接
    this.disconnect()
    
    try {
      // 创建WebSocket连接
      this.socket = new WebSocket(wsUrl)
      
      // 连接打开
      this.socket.onopen = () => {
        console.log('WebSocket connected to:', wsUrl)
        this.reconnectAttempts = 0
      }
      
      // 接收消息
      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('WebSocket message received:', data)
          
          // 过滤连接确认消息和心跳消息
          if (data.type === 'connection_established' || data.type === 'pong') {
            console.log('WebSocket connection established or pong received')
            return
          }
          
          // 只处理包含任务状态或进度信息的消息
          if (data.status || data.step_description || data.progress !== undefined) {
            // 更新进度
            const progressStore = useProgressStore()
            progressStore.updateTaskProgress(data)
          } else {
            console.log('Skipping message without status or progress:', data)
          }
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