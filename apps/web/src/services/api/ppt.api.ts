import { get, post, del } from '../http'
import type { ApiResponse, TaskStatus, GeneratePptRequest } from '@/types/api'

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