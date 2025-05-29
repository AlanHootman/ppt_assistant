import axios from 'axios'

// API基础URL
const apiBaseUrl = '/api/v1'

// PPT任务创建请求参数
export interface CreatePptTaskRequest {
  template_id: number
  markdown_content: string
  client_id: string
}

// 适配不同API响应结构的接口
interface ApiResponse<T> {
  code?: number
  message?: string
  data?: T
  task_id?: string
  status?: string
}

/**
 * PPT API服务
 */
export const pptApi = {
  /**
   * 创建PPT生成任务
   */
  createTask: async (data: CreatePptTaskRequest) => {
    try {
      const response = await axios.post(`${apiBaseUrl}/ppt/generate`, {
        template_id: data.template_id,
        markdown_content: data.markdown_content
      })
      
      // 兼容两种API响应格式
      if (response.data) {
        // 标准格式: {code, message, data: {}}
        if (response.data.code === 200 && response.data.data) {
          return response.data
        } 
        // 直接返回数据格式: {task_id, status, message}
        else if (response.data.task_id) {
          // 转换为前端期望的格式
          return {
            code: 200,
            message: response.data.message || "任务创建成功",
            data: {
              task_id: response.data.task_id,
              status: response.data.status || "pending",
              created_at: new Date().toISOString()
            }
          }
        }
        // 其他错误情况
        else {
          throw new Error(response.data?.message || '创建任务失败')
        }
      } else {
        throw new Error('创建任务失败')
      }
    } catch (error) {
      console.error('创建PPT任务失败:', error)
      throw error
    }
  },

  /**
   * 获取任务详情
   */
  getTaskById: async (taskId: string) => {
    try {
      const response = await axios.get(`${apiBaseUrl}/ppt/tasks/${taskId}`)
      
      // 处理直接返回数据的格式
      if (response.data && !response.data.code && response.data.task_id) {
        return {
          code: 200,
          message: "获取任务成功",
          data: response.data
        }
      }
      // 处理标准格式
      else if (response.data && response.data.code === 200) {
        return response.data
      } 
      else {
        throw new Error(response.data?.message || '获取任务详情失败')
      }
    } catch (error) {
      console.error('获取任务详情失败:', error)
      throw error
    }
  },

  /**
   * 取消任务
   */
  cancelTask: async (taskId: string) => {
    try {
      const response = await axios.delete(`${apiBaseUrl}/ppt/tasks/${taskId}`)
      
      // 处理直接返回数据的格式
      if (response.data && !response.data.code && response.data.message) {
        return {
          code: 200,
          message: response.data.message,
          data: { success: true }
        }
      }
      // 处理标准格式
      else if (response.data && response.data.code === 200) {
        return response.data
      } 
      else {
        throw new Error(response.data?.message || '取消任务失败')
      }
    } catch (error) {
      console.error('取消任务失败:', error)
      throw error
    }
  },

  /**
   * 获取任务下载地址
   */
  getTaskDownloadUrl: (taskId: string): string => {
    return `${apiBaseUrl}/files/ppt/${taskId}/download`
  }
} 