import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useEditorStore = defineStore('editor', () => {
  // Markdown内容
  const markdownContent = ref(localStorage.getItem('markdown_content') || '')
  
  // 监听内容变化，自动保存到localStorage
  watch(markdownContent, (newContent) => {
    localStorage.setItem('markdown_content', newContent)
  })
  
  function setMarkdownContent(content: string) {
    markdownContent.value = content
  }
  
  function clearMarkdownContent() {
    markdownContent.value = ''
    localStorage.removeItem('markdown_content')
  }
  
  return { 
    markdownContent,
    setMarkdownContent,
    clearMarkdownContent
  }
})