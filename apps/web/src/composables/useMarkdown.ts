import MarkdownIt from 'markdown-it'
import { ref, watch } from 'vue'
import { useEditorStore } from '@/stores/editor'

export function useMarkdown() {
  const md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true
  })
  
  const editorStore = useEditorStore()
  const { markdownContent, setMarkdownContent, clearMarkdownContent } = editorStore
  
  // Markdown编辑器值
  const editorValue = ref(markdownContent)
  
  // 监听编辑器值变化，同步到store
  watch(editorValue, (newValue) => {
    setMarkdownContent(newValue)
  })
  
  // HTML输出
  const htmlOutput = ref('')
  
  // 渲染HTML
  function renderMarkdown(text: string): string {
    return md.render(text)
  }
  
  // 更新HTML输出
  function updateOutput() {
    htmlOutput.value = renderMarkdown(editorValue.value)
  }
  
  // 初始化时更新一次输出
  updateOutput()
  
  // 监听Markdown内容变化，更新HTML输出
  watch(editorValue, updateOutput)
  
  // 清空编辑器
  function clearEditor() {
    editorValue.value = ''
    clearMarkdownContent()
    updateOutput()
  }
  
  // 设置编辑器内容
  function setEditorContent(content: string) {
    editorValue.value = content
    setMarkdownContent(content)
    updateOutput()
  }
  
  return {
    editorValue,
    htmlOutput,
    renderMarkdown,
    updateOutput,
    clearEditor,
    setEditorContent
  }
} 