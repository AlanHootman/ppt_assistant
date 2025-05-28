<template>
  <div class="generation-controls">
    <el-button 
      type="primary" 
      size="large" 
      @click="handleGenerate" 
      :loading="isGenerating"
      :disabled="isGenerating || !canGenerate"
      class="generate-button"
    >
      {{ isGenerating ? '生成中...' : '生成PPT' }}
    </el-button>
    
    <el-button 
      v-if="isGenerating" 
      type="danger" 
      size="large" 
      @click="handleCancel"
      class="cancel-button"
    >
      取消生成
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useProgressStore } from '../../stores/progress'
import { useTemplateStore } from '../../stores/template'
import { useEditorStore } from '../../stores/editor'
import { useTaskProgress } from '../../composables/useTaskProgress'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['generate'])

const progressStore = useProgressStore()
const templateStore = useTemplateStore()
const editorStore = useEditorStore()
const { cancelTask } = useTaskProgress()

// 是否正在生成
const isGenerating = computed(() => progressStore.isGenerating)

// 是否可以生成
const canGenerate = computed(() => {
  return templateStore.currentTemplate !== null && 
         editorStore.markdownContent.trim() !== ''
})

// 处理生成按钮点击
function handleGenerate() {
  if (!canGenerate.value) {
    if (!templateStore.currentTemplate) {
      ElMessage.warning('请先选择一个模板')
    } else if (editorStore.markdownContent.trim() === '') {
      ElMessage.warning('请输入Markdown内容')
    }
    return
  }
  
  emit('generate')
}

// 处理取消按钮点击
async function handleCancel() {
  if (progressStore.taskStatus && ['processing', 'pending'].includes(progressStore.taskStatus)) {
    await cancelTask()
    // 不需要检查返回值，因为 cancelTask 没有返回值
    // cancelTask 内部已经处理了消息提示
  }
}
</script>

<style scoped>
.generation-controls {
  display: flex;
  gap: 15px;
  margin-top: 20px;
}

.generate-button {
  flex: 2;
  height: 48px;
  font-size: 1.1rem;
}

.cancel-button {
  flex: 1;
  height: 48px;
}
</style> 