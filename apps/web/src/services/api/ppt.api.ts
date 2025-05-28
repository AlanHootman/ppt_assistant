import { get, post, del } from './index'
import type { ApiResponse, TaskStatus, GeneratePptRequest } from '@/types/api'

// PPT任务创建请求参数
export interface CreatePptTaskRequest {
  template_id: number
  markdown_content: string
  title?: string
  client_id: string
}

// PPT任务信息
export interface PptTask {
  task_id: string
  template_id: number
  status: string
  created_at: string
  updated_at: string
  output_file_url?: string
  progress?: number
}

// 模板查询参数
export interface TemplateQueryParams {
  page?: number
  limit?: number
  status?: string
  tags?: string[]
}

// 创建PPT生成任务
export function createPptTask(data: GeneratePptRequest) {
  return post<ApiResponse<{ task_id: string, status: string, created_at: string }>>('/ppt/generate', data)
}

// 获取任务状态
export function getTaskStatus(taskId: string) {
  return get<ApiResponse<TaskStatus>>(`/ppt/tasks/${taskId}`)
}

// 重试失败的任务
export function retryTask(taskId: string) {
  return post<ApiResponse<{ task_id: string, status: string, retry_count: number }>>(`/ppt/tasks/${taskId}/retry`)
}

// 获取生成结果
export function getTaskResult(taskId: string) {
  return get<ApiResponse<{
    task_id: string,
    status: string,
    file_url: string,
    preview_url: string,
    preview_images: Array<{ slide_index: number, preview_url: string }>,
    completed_at: string,
    download_expires_at: string
  }>>(`/ppt/tasks/${taskId}/result`)
}

// 取消任务
export function cancelTask(taskId: string) {
  return del<ApiResponse<{ task_id: string, status: string }>>(`/ppt/tasks/${taskId}`)
}

// 获取任务预览图
export function getTaskPreviews(taskId: string) {
  return get<ApiResponse<{
    task_id: string,
    total_slides: number,
    generated_slides: number,
    previews: Array<{ slide_index: number, preview_url: string, generated_at: string }>
  }>>(`/ppt/tasks/${taskId}/previews`)
}

// 下载生成的PPT
export function downloadPpt(taskId: string) {
  window.location.href = `/api/v1/files/ppt/${taskId}/download`
}

/**
 * PPT API服务
 */
export const pptApi = {
  /**
   * 创建PPT生成任务
   */
  createTask: (data: CreatePptTaskRequest) => {
    return post<{ task_id: string }>('/tasks', data)
  },

  /**
   * 获取任务详情
   */
  getTaskById: (taskId: string) => {
    return get<PptTask>(`/tasks/${taskId}`)
  },

  /**
   * 取消任务
   */
  cancelTask: (taskId: string) => {
    return post(`/tasks/${taskId}/cancel`)
  },

  /**
   * 获取任务进度
   */
  getTaskProgress: (taskId: string) => {
    return get(`/tasks/${taskId}/progress`)
  },

  /**
   * 获取任务下载地址
   */
  getTaskDownloadUrl: (taskId: string) => {
    return get<{ download_url: string }>(`/tasks/${taskId}/download`)
  },

  /**
   * 获取模板列表
   */
  getTemplates: (params?: TemplateQueryParams) => {
    return get('/templates', params)
  },

  /**
   * 获取模板详情
   */
  getTemplateById: (templateId: number) => {
    return get(`/templates/${templateId}`)
  }
} 