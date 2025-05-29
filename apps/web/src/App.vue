<template>
  <router-view />
</template>

<script setup lang="ts">
// 根组件
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 16px;
  color: #333;
  line-height: 1.5;
  background-color: #f5f7fa;
  height: 100%;
  overflow: hidden;
}

#app {
  height: 100vh;
  overflow: hidden;
}

a {
  color: #409eff;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 0.8rem;
  height: 100%;
}

.flex-row {
  display: flex;
  flex-direction: row;
  height: 100%;
}

@media (max-width: 768px) {
  .responsive-container {
    flex-direction: column;
  }
}
</style> 