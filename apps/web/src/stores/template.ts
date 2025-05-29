import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

// 模板接口
export interface Template {
  id: number
  name: string
  preview_url: string
  file_url?: string
  description?: string
  upload_time?: string
  status: string
  tags?: string[]
}

// API响应接口
interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

interface TemplateListResponse {
  total: number
  page: number
  limit: number
  templates: Template[]
}

export const useTemplateStore = defineStore('template', () => {
  // 模板列表
  const templates = ref<Template[]>([])
  // 当前选中的模板
  const currentTemplate = ref<Template | null>(null)
  // API基础URL
  const apiBaseUrl = '/api/v1'
  
  /**
   * 获取模板列表
   */
  async function fetchTemplates(page = 1, limit = 10) {
    try {
      const response = await axios.get<ApiResponse<TemplateListResponse>>(
        `${apiBaseUrl}/templates`,
        { params: { page, limit } }
      )
      
      if (response.data.code === 200) {
        templates.value = response.data.data.templates
        return {
          total: response.data.data.total,
          items: response.data.data.templates
        }
      } else {
        console.error('获取模板列表失败:', response.data.message)
        return {
          total: 0,
          items: []
        }
      }
    } catch (error) {
      console.error('获取模板列表失败:', error)
      return {
        total: 0,
        items: []
      }
    }
  }
  
  /**
   * 获取模板详情
   */
  async function fetchTemplateById(id: number) {
    try {
      const response = await axios.get<ApiResponse<{ template: Template }>>(
        `${apiBaseUrl}/templates/${id}`
      )
      
      if (response.data.code === 200) {
        return response.data.data.template
      } else {
        console.error('获取模板详情失败:', response.data.message)
        return null
      }
    } catch (error) {
      console.error('获取模板详情失败:', error)
      return null
    }
  }
  
  /**
   * 设置当前选中的模板
   */
  function setCurrentTemplate(template: Template) {
    currentTemplate.value = template
    // 不再使用localStorage存储模板ID
  }
  
  /**
   * 选择默认模板
   */
  async function restoreSelectedTemplate() {
    // 如果模板列表为空，先获取模板列表
    if (templates.value.length === 0) {
      const result = await fetchTemplates()
      // 如果获取到了模板，选择第一个
      if (result.items.length > 0) {
        currentTemplate.value = result.items[0]
        return
      }
    } else if (templates.value.length > 0 && !currentTemplate.value) {
      // 如果已有模板列表但未选择模板，选择第一个
      currentTemplate.value = templates.value[0]
    }
  }
  
  return { 
    templates, 
    currentTemplate, 
    fetchTemplates, 
    fetchTemplateById,
    setCurrentTemplate,
    restoreSelectedTemplate
  }
}) 