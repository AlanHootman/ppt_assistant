import axios from 'axios'
import type { 
  Template, 
  TemplateListResponse, 
  TemplateUploadRequest,
  TemplateUploadResponse,
  TemplateUpdateRequest,
  TemplateAnalysisStatus,
  ApiResponse 
} from '../../models/admin'

const API_BASE_URL = '/api/v1'

export const adminApi = {
  /**
   * 获取模板列表
   */
  getTemplates: async (
    page = 1, 
    limit = 10, 
    statusFilter = 'all'
  ): Promise<ApiResponse<TemplateListResponse>> => {
    try {
      const skip = (page - 1) * limit
      const params: any = { skip, limit }
      
      // 添加状态筛选参数
      if (statusFilter && statusFilter !== 'all') {
        params.status_filter = statusFilter
      } else {
        params.status_filter = 'all'
      }
      
      const response = await axios.get(`${API_BASE_URL}/templates`, {
        params
      })
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '获取模板列表失败')
    }
  },

  /**
   * 获取模板详情
   */
  getTemplateById: async (templateId: number): Promise<ApiResponse<{ template: Template }>> => {
    try {
      const response = await axios.get(`${API_BASE_URL}/templates/${templateId}`)
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '获取模板详情失败')
    }
  },

  /**
   * 上传模板
   */
  uploadTemplate: async (uploadData: TemplateUploadRequest): Promise<ApiResponse<TemplateUploadResponse>> => {
    try {
      const formData = new FormData()
      formData.append('file', uploadData.file)
      formData.append('name', uploadData.name)
      if (uploadData.description) {
        formData.append('description', uploadData.description)
      }
      if (uploadData.tags && uploadData.tags.length > 0) {
        formData.append('tags', JSON.stringify(uploadData.tags))
      }

      const response = await axios.post(`${API_BASE_URL}/templates`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '上传模板失败')
    }
  },

  /**
   * 更新模板信息
   */
  updateTemplate: async (templateId: number, updateData: TemplateUpdateRequest): Promise<ApiResponse<{ template: Template }>> => {
    try {
      const response = await axios.put(`${API_BASE_URL}/templates/${templateId}`, updateData)
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '更新模板信息失败')
    }
  },

  /**
   * 删除模板
   */
  deleteTemplate: async (templateId: number): Promise<ApiResponse<{}>> => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/templates/${templateId}`)
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '删除模板失败')
    }
  },

  /**
   * 获取模板分析状态
   */
  getTemplateAnalysisStatus: async (templateId: number): Promise<ApiResponse<TemplateAnalysisStatus>> => {
    try {
      const response = await axios.get(`${API_BASE_URL}/templates/${templateId}/status`)
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '获取模板分析状态失败')
    }
  }
} 