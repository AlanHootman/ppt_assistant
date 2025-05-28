import { io, Socket } from 'socket.io-client'
import { useProgressStore } from '@/stores/progress'
import { getClientId } from '@/utils/clientId'

class WebSocketService {
  private socket: Socket | null = null
  private taskId: string | null = null
  
  connect(taskId: string) {
    this.taskId = taskId
    const clientId = getClientId()
    
    this.socket = io(`/ws/tasks/${taskId}?client_id=${clientId}`, {
      transports: ['websocket'],
      autoConnect: true
    })
    
    const progressStore = useProgressStore()
    
    this.socket.on('connect', () => {
      console.log('WebSocket connected')
    })
    
    this.socket.on('task_update', (data: any) => {
      progressStore.updateTaskProgress(data)
    })
    
    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
    })
    
    this.socket.on('connect_error', (error: any) => {
      console.error('WebSocket connection error:', error)
    })
    
    return this.socket
  }
  
  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.taskId = null
    }
  }
  
  isConnected(): boolean {
    return this.socket !== null && this.socket.connected
  }
  
  getTaskId(): string | null {
    return this.taskId
  }
}

// 导出单例
export default new WebSocketService() 