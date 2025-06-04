<template>
  <div class="generation-controls">
    <!-- DeepThink模型选择器 -->
    <deepthink-model-selector />
    
    <!-- 多模态检测开关 -->
    <div class="multimodal-switch">
      <el-switch
        v-model="enableMultimodalValidation"
        class="switch"
        active-text="多模态大模型检测修正"
        inactive-text="多模态大模型检测修正"
        :width="60"
      />
      <div class="switch-description">
        开启后将使用视觉模型检测和优化幻灯片内容，但会增加生成时间
      </div>
    </div>
    
    <div class="button-group">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineAsyncComponent } from 'vue'
import { useProgressStore } from '../../stores/progress'
import { useTemplateStore } from '../../stores/template'
import { useEditorStore } from '../../stores/editor'
import { useTaskProgress } from '../../composables/useTaskProgress'
import { ElMessage } from 'element-plus'

// 异步加载组件
const DeepThinkModelSelector = defineAsyncComponent(() => import('../../components/home/DeepThinkModelSelector.vue'))

const emit = defineEmits(['generate'])

const progressStore = useProgressStore()
const templateStore = useTemplateStore()
const editorStore = useEditorStore()
const { cancelTask } = useTaskProgress()

// 多模态检测开关状态，默认关闭
const enableMultimodalValidation = ref(false)

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
  
  emit('generate', { enableMultimodalValidation: enableMultimodalValidation.value })
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
/* ==========================================================================
   多模态检测开关样式
   ========================================================================== */

.multimodal-switch {
  margin-bottom: 1rem;
  padding: 1rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.multimodal-switch:hover {
  background-color: #f1f5f9;
  border-color: #cbd5e1;
}

.multimodal-switch .switch {
  margin-bottom: 0.5rem;
}

.switch-description {
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.4;
  margin-top: 0.25rem;
}

/* ==========================================================================
   生成控制面板 - 整体布局
   ========================================================================== */

.generation-controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
  flex-shrink: 0; /* 防止按钮区域被压缩 */
}

/* ==========================================================================
   按钮组布局
   ========================================================================== */

.button-group {
  display: flex;
  gap: 0.75rem;
}

/* ==========================================================================
   生成按钮 - 主要操作按钮
   ========================================================================== */

.generate-button {
  flex: 2;
  height: 42px;
  font-size: 1rem;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.generate-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
}

.generate-button:active:not(:disabled) {
  transform: translateY(0);
}

.generate-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* ==========================================================================
   取消按钮 - 次要操作按钮
   ========================================================================== */

.cancel-button {
  flex: 1;
  height: 42px;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;
  background-color: #f56c6c;
  border-color: #f56c6c;
  box-shadow: 0 2px 8px rgba(245, 108, 108, 0.2);
}

.cancel-button:hover {
  background-color: #f78989;
  border-color: #f78989;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(245, 108, 108, 0.3);
}

.cancel-button:active {
  transform: translateY(0);
}

/* ==========================================================================
   响应式优化 - 移动端适配
   ========================================================================== */

@media (max-width: 767px) {
  .generation-controls {
    gap: 0.75rem;
    margin-top: 0.75rem;
  }
  
  .button-group {
    gap: 0.5rem;
    flex-direction: column; /* 移动端垂直排列 */
  }
  
  .generate-button,
  .cancel-button {
    flex: none;
    width: 100%;
    height: 38px;
    font-size: 0.875rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 479px) {
  .generation-controls {
    gap: 0.375rem;
  }
  
  .generate-button,
  .cancel-button {
    height: 36px;
    font-size: 0.8rem;
  }
}

/* ==========================================================================
   可访问性和交互增强
   ========================================================================== */

.generate-button:focus,
.cancel-button:focus {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .generate-button,
  .cancel-button {
    transition: none;
  }
  
  .generate-button:hover:not(:disabled),
  .cancel-button:hover {
    transform: none;
  }
}

/* ==========================================================================
   加载状态优化
   ========================================================================== */

.generate-button.is-loading {
  position: relative;
}

.generate-button.is-loading::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 1rem;
  width: 1rem;
  height: 1rem;
  margin-top: -0.5rem;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style> 