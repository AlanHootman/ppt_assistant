import { get, post, put, del } from '../http'
import type { ApiResponse, Template, TemplateListResponse } from '@/types/api'

// 获取模板列表
export function getTemplates(page = 1, limit = 10) {
  return get<ApiResponse<TemplateListResponse>>('/templates', { page, limit })
}

// 获取模板详情
export function getTemplateById(id: number) {
  return get<ApiResponse<{ template: Template }>>(`/templates/${id}`)
}

// 上传模板
export function uploadTemplate(formData: FormData) {
  return post<ApiResponse<{ template_id: number, status: string, task_id: string }>>('/templates', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 更新模板信息
export function updateTemplate(id: number, data: { name?: string, description?: string, tags?: string[] }) {
  return put<ApiResponse<{ template: Template }>>(`/templates/${id}`, data)
}

// 删除模板
export function deleteTemplate(id: number) {
  return del<ApiResponse<{}>>(`/templates/${id}`)
}

// 获取模板分析状态
export function getTemplateAnalysisStatus(id: number) {
  return get<ApiResponse<{ template_id: number, status: string, progress: number, message: string }>>(`/templates/${id}/status`)
}