import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Template } from '@/types/api'

export const useTemplateStore = defineStore('template', () => {
  const templates = ref<Template[]>([])
  const currentTemplate = ref<Template | null>(null)
  
  async function fetchTemplates(page = 1, limit = 10) {
    // 实现获取模板列表的逻辑
    try {
      // 模拟API调用
      const mockTemplates: Template[] = [
        {
          id: 1,
          name: "商务简约风",
          preview_url: "/static/templates/1/preview.png",
          upload_time: "2023-06-15T10:30:00Z",
          status: "ready",
          tags: ["商务", "简约", "专业"]
        },
        {
          id: 2,
          name: "教育主题模板",
          preview_url: "/static/templates/2/preview.png",
          upload_time: "2023-06-20T14:45:00Z",
          status: "ready",
          tags: ["教育", "学术", "简洁"]
        }
      ]
      
      templates.value = mockTemplates
      return mockTemplates
    } catch (error) {
      console.error('Failed to fetch templates:', error)
      return []
    }
  }
  
  async function fetchTemplateById(id: number) {
    // 实现获取模板详情的逻辑
    try {
      // 模拟API调用
      const template = templates.value.find(t => t.id === id) || {
        id: id,
        name: `模板 ${id}`,
        preview_url: `/static/templates/${id}/preview.png`,
        upload_time: new Date().toISOString(),
        status: "ready",
        tags: ["示例"],
        description: "模板描述示例"
      }
      
      currentTemplate.value = template
      return template
    } catch (error) {
      console.error(`Failed to fetch template ${id}:`, error)
      return null
    }
  }
  
  function setCurrentTemplate(template: Template) {
    currentTemplate.value = template
    // 保存选择到localStorage
    localStorage.setItem('selected_template_id', template.id.toString())
  }
  
  // 初始化 - 从localStorage恢复上次选择的模板ID
  function init() {
    const savedTemplateId = localStorage.getItem('selected_template_id')
    if (savedTemplateId) {
      fetchTemplateById(parseInt(savedTemplateId))
    }
  }
  
  // 调用初始化
  init()
  
  return { 
    templates, 
    currentTemplate, 
    fetchTemplates, 
    fetchTemplateById,
    setCurrentTemplate
  }
}) 