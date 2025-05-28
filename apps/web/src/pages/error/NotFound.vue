<template>
  <div class="not-found">
    <div class="container">
      <div class="error-content">
        <h1>404</h1>
        <h2>页面未找到</h2>
        <p>抱歉，您访问的页面不存在</p>
        <el-button type="primary" @click="goHome">返回首页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<style scoped>
.not-found {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.error-content {
  max-width: 500px;
  padding: 30px;
}

h1 {
  font-size: 5rem;
  margin: 0;
  color: #409eff;
}

h2 {
  font-size: 2rem;
  margin: 0 0 20px 0;
  color: #303133;
}

p {
  margin-bottom: 30px;
  color: #606266;
}
</style> 