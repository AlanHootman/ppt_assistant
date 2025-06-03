import type { LoginRequest, LoginResponse, UserInfo, ApiResponse } from '../../models/admin'
import { get, post } from '../http'

export const authApi = {
  /**
   * 用户登录
   */
  login: async (credentials: LoginRequest): Promise<ApiResponse<LoginResponse>> => {
    try {
      return await post(`/auth/login`, credentials)
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '登录失败')
    }
  },

  /**
   * 验证令牌
   */
  verify: async (): Promise<ApiResponse<{ user: UserInfo }>> => {
    try {
      return await get(`/auth/verify`)
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '令牌验证失败')
    }
  },

  /**
   * 退出登录
   */
  logout: async (): Promise<ApiResponse<{}>> => {
    try {
      return await post(`/auth/logout`)
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '退出登录失败')
    }
  }
} 