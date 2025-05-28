import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const userInfo = ref<UserInfo | null>(null)
  const isLoggedIn = computed(() => !!token.value)
  
  async function login(username: string, password: string) {
    // 实现登录逻辑，此处只是示例
    try {
      // const response = await authApi.login(username, password)
      // token.value = response.data.token
      // userInfo.value = response.data.user
      
      // 暂时使用模拟数据
      token.value = 'mock-token'
      userInfo.value = {
        id: 1,
        username,
        role: 'admin'
      }
      
      // 存储到本地存储
      localStorage.setItem('token', token.value)
      localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
      
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }
  
  function logout() {
    token.value = ''
    userInfo.value = null
    
    // 清除本地存储
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }
  
  // 初始化时从本地存储恢复登录状态
  function init() {
    const storedToken = localStorage.getItem('token')
    const storedUserInfo = localStorage.getItem('userInfo')
    
    if (storedToken && storedUserInfo) {
      token.value = storedToken
      userInfo.value = JSON.parse(storedUserInfo)
    }
  }
  
  // 调用初始化
  init()
  
  return { token, userInfo, isLoggedIn, login, logout }
})