import { defineStore } from 'pinia'
import { ref, watch, onMounted } from 'vue'

// 默认Markdown文件路径
const DEFAULT_MARKDOWN_PATH = '/markdown/技术思维五导教学内容.md'

// 回退的示例Markdown内容，以防文件加载失败
const fallbackMarkdown = `# PPT演示文稿标题
  
## 第一部分
这是第一部分的介绍内容。在这里您可以添加文本描述。

- 要点一
- 要点二
- 要点三

## 第二部分
这是第二部分的内容描述。

### 子主题1
这里是子主题1的详细说明。

### 子主题2
这里是子主题2的详细说明。

## 总结
- 总结要点1
- 总结要点2
- 总结要点3
`

export const useEditorStore = defineStore('editor', () => {
  // Markdown内容
  const markdownContent = ref(localStorage.getItem('markdown_content') || '')
  
  // 示例Markdown内容
  const exampleMarkdown = ref(fallbackMarkdown)
  
  // 加载示例Markdown文件
  async function loadExampleMarkdownFile() {
    try {
      const response = await fetch(DEFAULT_MARKDOWN_PATH)
      
      if (!response.ok) {
        throw new Error(`Failed to load markdown file: ${response.status} ${response.statusText}`)
      }
      
      const content = await response.text()
      exampleMarkdown.value = content
      console.log('Example markdown loaded successfully')
    } catch (error) {
      console.error('Error loading example markdown file:', error)
      console.log('Using fallback markdown content')
      exampleMarkdown.value = fallbackMarkdown
    }
  }
  
  // 组件创建时加载示例Markdown文件
  loadExampleMarkdownFile()
  
  // 监听内容变化，自动保存到localStorage
  watch(markdownContent, (newContent) => {
    localStorage.setItem('markdown_content', newContent)
  })
  
  /**
   * 设置Markdown内容
   */
  function setMarkdownContent(content: string) {
    markdownContent.value = content
  }
  
  /**
   * 清空Markdown内容
   */
  function clearMarkdownContent() {
    markdownContent.value = ''
    localStorage.removeItem('markdown_content')
  }
  
  /**
   * 加载示例内容
   */
  function loadExampleContent() {
    markdownContent.value = exampleMarkdown.value
  }
  
  return { 
    markdownContent,
    exampleMarkdown,
    setMarkdownContent,
    clearMarkdownContent,
    loadExampleContent,
    loadExampleMarkdownFile
  }
})