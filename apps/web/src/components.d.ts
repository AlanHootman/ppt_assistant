// 为Element Plus组件声明全局类型
declare module 'vue' {
  export interface GlobalComponents {
    ElButton: typeof import('element-plus')['ElButton']
    ElInput: typeof import('element-plus')['ElInput']
    ElForm: typeof import('element-plus')['ElForm']
    ElFormItem: typeof import('element-plus')['ElFormItem']
    ElSelect: typeof import('element-plus')['ElSelect']
    ElOption: typeof import('element-plus')['ElOption']
    ElTag: typeof import('element-plus')['ElTag']
    ElMessage: typeof import('element-plus')['ElMessage']
    ElRow: typeof import('element-plus')['ElRow']
    ElCol: typeof import('element-plus')['ElCol']
  }
} 