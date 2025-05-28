<template>
  <div class="not-found">
    <div class="content">
      <h1>404</h1>
      <h2>页面未找到</h2>
      <p>很抱歉，您访问的页面不存在或已被移除。</p>
      <el-button type="primary" @click="goHome">返回首页</el-button>
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
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
  text-align: center;
}

.content {
  max-width: 500px;
  padding: 2rem;
}

h1 {
  font-size: 6rem;
  margin: 0;
  color: #409eff;
}

h2 {
  font-size: 2rem;
  margin: 0 0 1rem;
  color: #303133;
}

p {
  color: #606266;
  margin-bottom: 2rem;
}
</style> 