<template>
  <div class="generation-controls">
    <el-button 
      type="primary" 
      size="default" 
      @click="handleGenerate" 
      :loading="isGenerating && !hasFailed"
      :disabled="isGenerating || !canGenerate"
      class="generate-button"
    >
      {{ getButtonText() }}
    </el-button>
    
    <el-button 
      v-if="showCancelButton" 
      type="danger" 
      size="default" 
      @click="handleCancel"
      class="cancel-button"
    >
      {{ hasFailed ? '重新开始' : '取消生成' }}
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

// 任务是否失败
const hasFailed = computed(() => progressStore.taskStatus === 'failed')

// 是否可以生成
const canGenerate = computed(() => {
  return templateStore.currentTemplate !== null && 
         editorStore.markdownContent.trim() !== ''
})

// 是否显示取消按钮
const showCancelButton = computed(() => {
  // 只在正在生成且未失败，或者已失败时显示
  return (isGenerating.value && !hasFailed.value) || hasFailed.value
})

// 获取按钮文本
function getButtonText() {
  if (hasFailed.value) {
    return '重新生成PPT'
  } else if (isGenerating.value) {
    return '生成中...'
  } else {
    return '生成PPT'
  }
}

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
  if (hasFailed.value) {
    // 失败状态下，重置进度状态
    progressStore.resetProgress()
    ElMessage.info('已重置状态，可以重新生成PPT')
  } else if (progressStore.taskStatus && ['processing', 'pending'].includes(progressStore.taskStatus)) {
    // 正在进行的任务，执行取消操作
    await cancelTask()
  } else {
    // 其他状态，直接重置
    progressStore.resetProgress()
    ElMessage.info('已重置状态')
  }
}
</script>

<style scoped>
.generation-controls {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.generate-button {
  flex: 2;
  height: 36px;
  font-size: 1rem;
}

.cancel-button {
  flex: 1;
  height: 36px;
}
</style> 