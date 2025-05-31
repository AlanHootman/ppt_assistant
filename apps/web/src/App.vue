<template>
  <router-view />
</template>

<script setup lang="ts">
// 根组件
</script>

<style>
/* 移除重复的全局样式，这些已在main.scss中定义 */
/* 只保留应用级别的特定样式 */

/* 应用根容器 */
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 路由视图容器 */
.router-view {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style> 