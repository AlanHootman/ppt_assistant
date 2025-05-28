declare module 'element-plus' {
  import { Plugin } from 'vue'
  import type { App } from 'vue'
  
  export const ElMessage: {
    success(message: string): void
    warning(message: string): void
    info(message: string): void
    error(message: string): void
  }
  
  const ElementPlus: Plugin
  export default ElementPlus
  export * from 'element-plus'
} 