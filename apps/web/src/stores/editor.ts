import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useEditorStore = defineStore('editor', () => {
  // Markdown内容
  const markdownContent = ref(localStorage.getItem('markdown_content') || '')
  
  // 示例Markdown内容
  const exampleMarkdown = `# PPT演示文稿标题
  
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
    markdownContent.value = exampleMarkdown
  }
  
  return { 
    markdownContent,
    exampleMarkdown,
    setMarkdownContent,
    clearMarkdownContent,
    loadExampleContent
  }
})