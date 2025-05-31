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
/* ==========================================================================
   编辑器面板 - 整体布局
   ========================================================================== */

.editor-panel {
  margin-bottom: 1rem;
  flex: 1; /* 占用剩余空间 */
  display: flex;
  flex-direction: column;
  min-height: 0; /* 重要：允许flex收缩 */
}

/* ==========================================================================
   编辑器头部 - 标题和操作按钮
   ========================================================================== */

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-shrink: 0; /* 防止头部被压缩 */
}

.title {
  font-size: 1.1rem;
  color: #303133;
  margin: 0;
  font-weight: 600;
}

.editor-actions {
  display: flex;
  gap: 0.5rem;
}

/* ==========================================================================
   Markdown编辑器 - 文本区域样式
   ========================================================================== */

.markdown-editor {
  flex: 1; /* 占用剩余空间 */
  min-height: 0; /* 重要：允许收缩 */
}

.markdown-editor :deep(.el-textarea__inner) {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
  transition: border-color 0.3s ease;
  resize: none; /* 禁用手动调整大小，让它自适应 */
  min-height: 300px; /* 设置最小高度 */
}

.markdown-editor :deep(.el-textarea__inner):focus {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.markdown-editor :deep(.el-textarea__inner):hover {
  border-color: #c0c4cc;
}

/* ==========================================================================
   提示信息 - 底部提示
   ========================================================================== */

.tip {
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: #909399;
  line-height: 1.4;
  flex-shrink: 0; /* 防止提示被压缩 */
  background-color: #f8f9fa;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  border-left: 3px solid #409eff;
}

.tip p {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tip i {
  color: #409eff;
  font-size: 0.875rem;
}

/* ==========================================================================
   响应式优化 - 移动端适配
   ========================================================================== */

@media (max-width: 767px) {
  .editor-panel {
    margin-bottom: 0.75rem;
  }
  
  .editor-header {
    margin-bottom: 0.75rem;
  }
  
  .title {
    font-size: 1rem;
  }
  
  .editor-actions {
    gap: 0.375rem;
  }
  
  .markdown-editor :deep(.el-textarea__inner) {
    font-size: 0.8rem;
    min-height: 250px;
  }
  
  .tip {
    margin-top: 0.5rem;
    padding: 0.375rem 0.5rem;
    font-size: 0.75rem;
  }
}

/* ==========================================================================
   可访问性优化
   ========================================================================== */

@media (prefers-reduced-motion: reduce) {
  .markdown-editor :deep(.el-textarea__inner) {
    transition: none;
  }
}
</style> 