import axios from 'axios'

// API基础URL
const apiBaseUrl = '/api/v1'

// PPT任务创建请求参数
export interface CreatePptTaskRequest {
  template_id: number
  markdown_content: string
  client_id: string
  enable_multimodal_validation?: boolean
}

// 标准API响应结构接口
interface ApiResponse<T> {
  code: number
  message: string
  data: T
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
        markdown_content: data.markdown_content,
        enable_multimodal_validation: data.enable_multimodal_validation || false
      })
      
      if (response.data && response.data.code && response.data.data) {
        return response.data
      } else {
        throw new Error(response.data?.message || '创建任务失败')
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
      
      if (response.data && response.data.code && response.data.data) {
        return response.data
      } else {
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
      
      if (response.data && response.data.code && response.data.data) {
        return response.data
      } else {
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