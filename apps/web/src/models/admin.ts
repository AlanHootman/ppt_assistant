// 管理后台相关数据模型定义

// 用户认证相关
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  expires_in: number
  user: UserInfo
}

export interface UserInfo {
  id: number
  username: string
  role: string
}

// 模板管理相关
export interface Template {
  id: number
  name: string
  preview_url: string
  upload_time: string
  status: 'ready' | 'analyzing' | 'failed'
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

export interface TemplateUploadRequest {
  file: File
  name: string
  description?: string
  tags?: string[]
}

export interface TemplateUploadResponse {
  template_id: number
  name: string
  status: string
  task_id: string
}

export interface TemplateUpdateRequest {
  name?: string
  description?: string
  tags?: string[]
}

export interface TemplateAnalysisStatus {
  template_id: number
  status: 'analyzing' | 'ready' | 'failed'
  progress: number
  message: string
}

// API响应基础格式
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
  errors?: string[]
} 