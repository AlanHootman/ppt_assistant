<template>
  <div class="chat-progress">
    <div class="header">
      <h2 class="title">生成进度</h2>
      <el-tooltip 
        v-if="hasMessages || hasError"
        effect="dark" 
        placement="left"
        content="点击查看与大模型交互内容"
      >
        <el-button
          type="info"
          size="small"
          circle
          @click="openMlflowDashboard"
          class="debug-button"
        >
          <el-icon><Setting /></el-icon>
        </el-button>
      </el-tooltip>
    </div>
    
    <!-- 滚动容器 -->
    <div class="messages-container" ref="messagesContainer">
      <!-- 欢迎消息 -->
      <div class="message system-message" v-if="!hasMessages">
        <div class="message-content">
          欢迎使用PPT助手，选择模板并输入Markdown内容，点击"生成PPT"开始创建。
        </div>
      </div>
      
      <!-- 进度消息列表 -->
      <div 
        v-for="message in progressMessages" 
        :key="message.id"
        class="message"
        :class="{
          'progress-message': !message.isError,
          'error-message': message.isError
        }"
      >
        <div class="message-header">
          <span class="step-name">{{ message.step }}</span>
          <span v-if="!message.isError" class="progress-percent">{{ message.progress }}%</span>
          <span v-else class="error-indicator">错误</span>
          <span class="message-time">{{ formatTime(message.time) }}</span>
        </div>
        <div class="message-content">
          {{ message.message }}
        </div>
        
        <!-- 预览图片 -->
        <div v-if="shouldShowPreview(message)" class="preview-container">
          <img 
            v-for="preview in previewImages" 
            :key="preview.id"
            :src="preview.url" 
            alt="预览" 
            class="preview-image"
          />
        </div>
      </div>
      
      <!-- 详细错误信息 -->
      <div class="message error-message" v-if="hasDetailedError">
        <div class="message-header">
          <span class="step-name">详细错误信息</span>
          <span class="message-time">{{ formatTime(new Date()) }}</span>
        </div>
        <div class="message-content">
          <div class="error-details">
            <p><strong>错误代码:</strong> {{ taskError?.error_code || 'UNKNOWN' }}</p>
            <p><strong>错误描述:</strong> {{ taskError?.error_message || '未知错误' }}</p>
            <p v-if="taskError?.can_retry"><strong>支持重试:</strong> 是</p>
          </div>
        </div>
        <div class="error-actions" v-if="taskError?.can_retry">
          <el-button type="primary" size="small" @click="handleRetry">
            重试
          </el-button>
        </div>
      </div>
      
      <!-- 加载中动画 -->
      <div v-if="isGenerating && taskStatus !== 'completed' && taskStatus !== 'failed'" class="loading-indicator">
        <div class="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { useProgressStore, type ProgressMessage, type PreviewImage } from '../../stores/progress'
import { useTaskProgress } from '../../composables/useTaskProgress'
import { useClientStore } from '../../stores/client'

const progressStore = useProgressStore()
const clientStore = useClientStore()
const { createPptTask } = useTaskProgress()

// 消息容器引用
const messagesContainer = ref<HTMLElement>()

// 计算属性
const progressMessages = computed(() => progressStore.progressMessages)
const previewImages = computed(() => progressStore.previewImages)
const isGenerating = computed(() => progressStore.isGenerating)
const taskError = computed(() => progressStore.taskError)
const taskStatus = computed(() => progressStore.taskStatus)
const hasMessages = computed(() => progressMessages.value.length > 0)
const hasError = computed(() => progressStore.taskStatus === 'failed')
const hasDetailedError = computed(() => {
  return hasError.value && taskError.value && taskError.value.has_error
})

// 获取MLflow服务器URL
function getMlflowUrl(): string {
  // 从当前页面URL获取服务器地址
  const { protocol, hostname } = window.location
  
  // 构建MLflow URL - 使用标准的/mlflow路径
  return `${protocol}//${hostname}/mlflow`
}

// 打开MLflow仪表板
function openMlflowDashboard() {
  const mlflowUrl = getMlflowUrl()
  
  // 在新标签页中打开
  window.open(mlflowUrl, '_blank', 'noopener,noreferrer')
}

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 监听消息变化，自动滚动到底部
watch([progressMessages, isGenerating, hasDetailedError], scrollToBottom, { flush: 'post' })

// 格式化时间
function formatTime(time: Date): string {
  return dayjs(time).format('HH:mm:ss')
}

// 判断是否应该显示预览图
function shouldShowPreview(message: ProgressMessage): boolean {
  const isLastMessage = progressMessages.value[progressMessages.value.length - 1]?.id === message.id
  const isCompleted = progressStore.taskStatus === 'completed'
  const hasPreviewImages = previewImages.value.length > 0
  
  return isLastMessage && isCompleted && !message.isError && hasPreviewImages
}

// 处理重试
async function handleRetry() {
  if (hasError.value) {
    progressStore.resetProgress()
    await createPptTask()
  }
}
</script>

<style scoped>
/* ==========================================================================
   聊天进度组件 - 整体布局
   ========================================================================== */

.chat-progress {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ==========================================================================
   头部区域 - 标题和调试按钮
   ========================================================================== */

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-shrink: 0;
}

.title {
  font-size: 1.1rem;
  margin: 0;
  color: #303133;
  font-weight: 600;
}

.debug-button {
  opacity: 0.7;
  transition: opacity 0.3s ease;
}

.debug-button:hover {
  opacity: 1;
}

/* ==========================================================================
   消息容器 - 滚动区域
   ========================================================================== */

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 0.375rem;
  scrollbar-width: thin;
  scrollbar-color: #c0c4cc #f5f7fa;
  min-height: 0;
}

/* Webkit滚动条样式 */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: #f5f7fa;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: #a4a9b6;
}

/* ==========================================================================
   消息样式 - 不同类型消息的外观
   ========================================================================== */

.message {
  margin-bottom: 0.75rem;
  padding: 0.75rem;
  border-radius: 6px;
  max-width: 95%;
  font-size: 0.875rem;
}

.system-message {
  align-self: center;
  background-color: #f0f9ff;
  border-left: 3px solid #409eff;
  color: #606266;
  width: 100%;
}

.progress-message {
  align-self: flex-start;
  background-color: #f0f9ff;
  border-left: 3px solid #409eff;
}

.error-message {
  align-self: flex-start;
  background-color: #fef0f0;
  border-left: 3px solid #f56c6c;
}

/* ==========================================================================
   消息头部 - 步骤名称、进度和时间
   ========================================================================== */

.message-header {
  display: flex;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  color: #909399;
}

.step-name {
  font-weight: 600;
  margin-right: 0.5rem;
  color: #303133;
}

.progress-percent {
  margin-right: 0.5rem;
  color: #409eff;
  font-weight: 500;
}

.error-indicator {
  margin-right: 0.5rem;
  color: #f56c6c;
  font-weight: 500;
}

.message-time {
  margin-left: auto;
}

/* ==========================================================================
   消息内容 - 文本内容样式
   ========================================================================== */

.message-content {
  line-height: 1.5;
  white-space: pre-line;
}

/* ==========================================================================
   预览图片 - 生成结果预览
   ========================================================================== */

.preview-container {
  margin-top: 0.75rem;
  width: 100%;
}

.preview-image {
  max-width: 100%;
  max-height: 200px;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* ==========================================================================
   错误详情 - 错误信息显示
   ========================================================================== */

.error-details {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  background-color: #faf2f2;
  border: 1px solid #fbc4c4;
  border-radius: 4px;
  padding: 0.5rem;
  margin: 0.5rem 0;
}

.error-details p {
  margin: 0.375rem 0;
  font-size: 0.8rem;
  line-height: 1.4;
}

.error-details strong {
  color: #f56c6c;
  font-weight: 600;
}

.error-actions {
  margin-top: 0.75rem;
}

/* ==========================================================================
   加载动画 - 生成进度指示器
   ========================================================================== */

.loading-indicator {
  align-self: center;
  margin-top: 1rem;
  padding: 0.75rem 0;
}

.loading-dots {
  display: flex;
  justify-content: center;
  align-items: center;
}

.loading-dots span {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin: 0 0.25rem;
  background-color: #409eff;
  border-radius: 50%;
  animation: loading 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes loading {
  0%, 80%, 100% { 
    transform: scale(0);
  } 
  40% { 
    transform: scale(1.0);
  }
}

/* ==========================================================================
   响应式优化 - 移动端适配
   ========================================================================== */

@media (max-width: 767px) {
  .chat-progress {
    padding: 0.75rem;
  }
  
  .header {
    margin-bottom: 0.75rem;
  }
  
  .title {
    font-size: 1rem;
  }
  
  .message {
    padding: 0.5rem;
    font-size: 0.8rem;
  }
  
  .message-header {
    font-size: 0.75rem;
  }
  
  .messages-container {
  }
}

/* 平板端适配 */
@media (min-width: 768px) and (max-width: 1023px) {
  .chat-progress {
    padding: 0.875rem;
  }
  
  .message {
    padding: 0.625rem;
  }
}

/* ==========================================================================
   可访问性优化
   ========================================================================== */

@media (prefers-reduced-motion: reduce) {
  .debug-button {
    transition: none;
  }
  
  .loading-dots span {
    animation: none;
  }
}
</style> 