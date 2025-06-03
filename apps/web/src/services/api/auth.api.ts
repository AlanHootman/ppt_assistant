import axios from 'axios'
import type { LoginRequest, LoginResponse, UserInfo, ApiResponse } from '../../models/admin'

const API_BASE_URL = '/api/v1'

export const authApi = {
  /**
   * 用户登录
   */
  login: async (credentials: LoginRequest): Promise<ApiResponse<LoginResponse>> => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, credentials)
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '登录失败')
    }
  },

  /**
   * 验证令牌
   */
  verify: async (): Promise<ApiResponse<{ user: UserInfo }>> => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/verify`)
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '令牌验证失败')
    }
  },

  /**
   * 退出登录
   */
  logout: async (): Promise<ApiResponse<{}>> => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/logout`)
      return response.data
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '退出登录失败')
    }
  }
} 