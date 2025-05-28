import { defineStore } from 'pinia'
import { ref } from 'vue'

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

export const useTemplateStore = defineStore('template', () => {
  // 模板列表
  const templates = ref<Template[]>([])
  // 当前选中的模板
  const currentTemplate = ref<Template | null>(null)
  
  /**
   * 获取模板列表
   */
  async function fetchTemplates(page = 1, limit = 10) {
    try {
      // 这里应该调用API获取模板列表
      // 暂时使用模拟数据
      templates.value = [
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
          upload_time: "2023-06-16T14:30:00Z",
          status: "ready",
          tags: ["教育", "课程", "学习"]
        }
      ]
      
      return {
        total: templates.value.length,
        items: templates.value
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
      // 这里应该调用API获取模板详情
      // 暂时从列表中查找
      const template = templates.value.find(t => t.id === id)
      
      if (template) {
        return template
      }
      
      // 如果列表中没有，模拟API请求
      const mockTemplate = {
        id,
        name: `模板 ${id}`,
        preview_url: `/static/templates/${id}/preview.png`,
        file_url: `/static/templates/${id}/template.pptx`,
        description: "模板描述",
        upload_time: new Date().toISOString(),
        status: "ready",
        tags: ["标签1", "标签2"]
      }
      
      return mockTemplate
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
    // 保存选择到localStorage
    localStorage.setItem('selected_template_id', template.id.toString())
  }
  
  /**
   * 从localStorage恢复选中的模板
   */
  async function restoreSelectedTemplate() {
    const templateId = localStorage.getItem('selected_template_id')
    
    if (templateId) {
      const id = parseInt(templateId)
      const template = await fetchTemplateById(id)
      
      if (template) {
        currentTemplate.value = template
      }
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