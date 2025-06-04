import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

// 创建axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 在发送请求之前做些什么
    // 例如添加token
    const token = localStorage.getItem('admin_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    // 对请求错误做些什么
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    // 对响应数据做点什么
    return response
  },
  (error) => {
    // 对响应错误做点什么
    // 例如，可以统一处理401登录状态失效的情况
    if (error.response && error.response.status === 401) {
      // 清除登录状态
      localStorage.removeItem('admin_token')
      // 跳转到登录页
      // router.push('/login')
    }
    return Promise.reject(error)
  }
)

// 定义接口返回格式
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 封装GET请求
export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return apiClient.get(url, { params, ...config }).then((res: AxiosResponse) => res.data)
}

// 封装POST请求
export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return apiClient.post(url, data, config).then((res: AxiosResponse) => res.data)
}

// 封装PUT请求
export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return apiClient.put(url, data, config).then((res: AxiosResponse) => res.data)
}

// 封装DELETE请求
export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return apiClient.delete(url, config).then((res: AxiosResponse) => res.data)
}

export default {
  get,
  post,
  put,
  del
} 