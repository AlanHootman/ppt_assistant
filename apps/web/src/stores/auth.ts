import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../services/api/auth.api'
import httpClient from '../services/http'
import type { UserInfo, LoginRequest } from '../models/admin'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref<string>(localStorage.getItem('admin_token') || '')
  const userInfo = ref<UserInfo | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value && !!userInfo.value)

  // 设置axios默认header
  const setAuthHeader = (authToken: string) => {
    if (authToken) {
      // 设置http客户端的Authorization头
      httpClient.defaults.headers.common['Authorization'] = `Bearer ${authToken}`
    }
  }

  // 清除认证信息
  const clearAuth = () => {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_user')
    
    // 清除http客户端的Authorization头
    delete httpClient.defaults.headers.common['Authorization']
  }

  // 登录
  const login = async (credentials: LoginRequest) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await authApi.login(credentials)
      
      if (response.code === 200) {
        token.value = response.data.token
        userInfo.value = response.data.user
        
        // 保存到localStorage
        localStorage.setItem('admin_token', response.data.token)
        localStorage.setItem('admin_user', JSON.stringify(response.data.user))
        
        // 设置axios header
        setAuthHeader(response.data.token)
        
        return true
      } else {
        throw new Error(response.message || '登录失败')
      }
    } catch (err: any) {
      error.value = err.message || '登录失败，请重试'
      return false
    } finally {
      loading.value = false
    }
  }

  // 验证令牌
  const verifyToken = async () => {
    if (!token.value) return false
    
    try {
      setAuthHeader(token.value)
      const response = await authApi.verify()
      
      if (response.code === 200) {
        userInfo.value = response.data.user
        return true
      } else {
        clearAuth()
        return false
      }
    } catch (err) {
      clearAuth()
      return false
    }
  }

  // 退出登录
  const logout = async () => {
    loading.value = true
    
    try {
      if (token.value) {
        await authApi.logout()
      }
    } catch (err) {
      console.error('退出登录请求失败:', err)
    } finally {
      clearAuth()
      loading.value = false
    }
  }

  // 初始化认证状态
  const initAuth = async () => {
    const savedToken = localStorage.getItem('admin_token')
    const savedUser = localStorage.getItem('admin_user')
    
    if (savedToken && savedUser) {
      token.value = savedToken
      userInfo.value = JSON.parse(savedUser)
      
      // 验证令牌是否仍然有效
      const isValid = await verifyToken()
      if (!isValid) {
        clearAuth()
        return false
      }
      
      setAuthHeader(savedToken)
      return true
    }
    
    return false
  }

  return {
    // 状态
    token,
    userInfo,
    loading,
    error,
    
    // 计算属性
    isLoggedIn,
    
    // 方法
    login,
    logout,
    verifyToken,
    initAuth,
    clearAuth
  }
})