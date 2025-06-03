import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

// 创建axios实例
const httpClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器
httpClient.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    const token = localStorage.getItem('admin_token')
    
    // 如果有token则添加到请求头
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
httpClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 直接返回响应数据
    return response
  },
  (error) => {
    // 获取错误状态码
    const status = error.response ? error.response.status : null
    
    // 处理401未授权错误
    if (status === 401) {
      // 清除本地token
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
      
      // 重定向到登录页面
      if (window.location.pathname.startsWith('/admin')) {
        window.location.href = '/admin/login'
      }
    }
    
    // 其他错误处理
    return Promise.reject(error)
  }
)

// 封装GET请求
export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
  return httpClient.get(url, { params, ...config }).then(response => response.data)
}

// 封装POST请求
export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return httpClient.post(url, data, config).then(response => response.data)
}

// 封装PUT请求
export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return httpClient.put(url, data, config).then(response => response.data)
}

// 封装DELETE请求
export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return httpClient.delete(url, config).then(response => response.data)
}

export default httpClient 