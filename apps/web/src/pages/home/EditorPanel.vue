<template>
  <div class="editor-panel">
    <div class="editor-header">
      <h2 class="title">Markdown编辑器</h2>
      <div class="editor-actions">
        <el-button type="info" size="small" @click="loadExampleContent">加载示例</el-button>
        <el-button type="danger" size="small" @click="clearContent">清空</el-button>
      </div>
    </div>
    
    <el-input
      v-model="content"
      type="textarea"
      :rows="12"
      placeholder="请输入Markdown内容或粘贴已有文档..."
      resize="vertical"
      class="markdown-editor"
    />
    
    <div class="tip">
      <p>
        <i class="el-icon-info"></i>
        支持Markdown语法，如#标题，##二级标题，- 列表项等
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useEditorStore } from '../../stores/editor'

const editorStore = useEditorStore()

// 编辑器内容双向绑定
const content = computed({
  get: () => editorStore.markdownContent,
  set: (value) => editorStore.setMarkdownContent(value)
})

// 加载示例内容
function loadExampleContent() {
  editorStore.loadExampleContent()
}

// 清空内容
function clearContent() {
  editorStore.clearMarkdownContent()
}
</script>

<style scoped>
.editor-panel {
  margin-bottom: 15px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.title {
  font-size: 1.1rem;
  color: #303133;
  margin: 0;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.markdown-editor {
  font-family: monospace;
  font-size: 0.85rem;
}

.tip {
  margin-top: 8px;
  font-size: 0.8rem;
  color: #909399;
  line-height: 1.4;
}
</style> 