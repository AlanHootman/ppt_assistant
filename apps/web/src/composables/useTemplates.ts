import { ref, onMounted } from 'vue'
import { useTemplateStore } from '@/stores/template'
import * as templateApi from '@/services/api/template.api'
import type { Template } from '@/types/api'

export function useTemplates() {
  const templateStore = useTemplateStore()
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // 获取模板列表
  async function fetchTemplates(page = 1, limit = 10) {
    loading.value = true
    error.value = null
    
    try {
      const result = await templateStore.fetchTemplates(page, limit)
      return result
    } catch (err) {
      console.error('获取模板列表失败:', err)
      error.value = '获取模板列表失败'
      return []
    } finally {
      loading.value = false
    }
  }
  
  // 获取模板详情
  async function fetchTemplateById(id: number) {
    loading.value = true
    error.value = null
    
    try {
      const result = await templateStore.fetchTemplateById(id)
      return result
    } catch (err) {
      console.error(`获取模板${id}详情失败:`, err)
      error.value = '获取模板详情失败'
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 设置当前模板
  function setCurrentTemplate(template: Template) {
    templateStore.setCurrentTemplate(template)
  }
  
  // 页面加载时获取模板列表
  onMounted(() => {
    fetchTemplates()
  })
  
  return {
    templates: templateStore.templates,
    currentTemplate: templateStore.currentTemplate,
    loading,
    error,
    fetchTemplates,
    fetchTemplateById,
    setCurrentTemplate
  }
} 