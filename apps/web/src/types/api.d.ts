// API响应通用接口
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
  errors?: string[]
}

// 用户信息接口
export interface UserInfo {
  id: number
  username: string
  role: string
}

// 认证相关接口
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  expires_in: number
  user: UserInfo
}

// 模板相关接口
export interface Template {
  id: number
  name: string
  preview_url: string
  upload_time: string
  status: 'ready' | 'analyzing' | 'failed' | 'uploading'
  tags: string[]
  description?: string
  file_url?: string
  layout_features?: any
}

export interface TemplateListResponse {
  total: number
  page: number
  limit: number
  templates: Template[]
}

// PPT生成任务相关接口
export interface TaskStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  progress: number
  current_step?: string
  step_description?: string
  created_at: string
  updated_at: string
  preview_images?: PreviewImage[]
  error?: {
    has_error: boolean
    error_code?: string
    error_message?: string
    can_retry: boolean
  }
}

export interface PreviewImage {
  slide_index: number
  preview_url: string
  generated_at?: string
}

export interface GeneratePptRequest {
  template_id: number
  markdown_content: string
  callback_url?: string
} 