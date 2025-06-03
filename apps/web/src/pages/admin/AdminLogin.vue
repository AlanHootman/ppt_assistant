<template>
  <div class="admin-login">
    <div class="login-container">
      <div class="login-header">
        <h1 class="login-title">PPT助手管理后台</h1>
        <p class="login-subtitle">请使用管理员账号登录</p>
      </div>

      <el-form 
        ref="loginFormRef" 
        :model="loginForm" 
        :rules="loginRules" 
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            prefix-icon="User"
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            prefix-icon="Lock"
            show-password
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-button"
            :loading="authStore.loading"
            @click="handleLogin"
          >
            {{ authStore.loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>

        <div v-if="authStore.error" class="error-message">
          <el-alert
            :title="authStore.error"
            type="error"
            :closable="false"
            show-icon
          />
        </div>
      </el-form>

      <div class="login-footer">
        <p>PPT助手管理后台</p>
        <el-button link @click="goToHome">
          <el-icon><ArrowLeft /></el-icon>
          返回首页
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import type { LoginRequest } from '../../models/admin'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 表单引用
const loginFormRef = ref<any>()

// 登录表单数据
const loginForm = reactive<LoginRequest>({
  username: '',
  password: ''
})

// 表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度应为6-50个字符', trigger: 'blur' }
  ]
}

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    // 验证表单
    await loginFormRef.value.validate()
    
    // 执行登录
    const success = await authStore.login(loginForm)
    
    if (success) {
      ElMessage.success('登录成功')
      
      // 获取重定向地址，默认到管理后台首页
      const redirectPath = (route.query.redirect as string) || '/admin'
      await router.push(redirectPath)
    }
  } catch (error) {
    console.error('登录失败:', error)
  }
}

// 返回首页
const goToHome = () => {
  router.push('/')
}

// 组件挂载时清除错误信息
onMounted(() => {
  authStore.error = null
})
</script>

<style scoped>
.admin-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.login-container {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  padding: 2.5rem 2rem;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.login-subtitle {
  color: #718096;
  margin: 0;
  font-size: 0.875rem;
}

.login-form {
  margin-bottom: 1.5rem;
}

.login-form .el-form-item {
  margin-bottom: 1.5rem;
}

.login-button {
  width: 100%;
  height: 48px;
  font-size: 1rem;
  font-weight: 500;
}

.error-message {
  margin-top: 1rem;
}

.login-footer {
  text-align: center;
  padding-top: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.login-footer p {
  color: #718096;
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .admin-login {
    padding: 1rem;
  }
  
  .login-container {
    padding: 2rem 1.5rem;
  }
  
  .login-title {
    font-size: 1.5rem;
  }
}
</style> 