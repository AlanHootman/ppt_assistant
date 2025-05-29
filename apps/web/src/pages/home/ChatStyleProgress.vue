<template>
  <div class="chat-progress">
    <h2 class="title">生成进度</h2>
    
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
        <div v-if="getPreviewForMessage(message.id)" class="preview-container">
          <img 
            :src="getPreviewForMessage(message.id).url" 
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
            <p><strong>错误代码:</strong> {{ taskError.error_code || 'UNKNOWN' }}</p>
            <p><strong>错误描述:</strong> {{ taskError.error_message || '未知错误' }}</p>
            <p v-if="taskError.can_retry"><strong>支持重试:</strong> 是</p>
          </div>
        </div>
        <div class="error-actions" v-if="taskError.can_retry">
          <el-button type="primary" size="small" @click="handleRetry">
            重试
          </el-button>
        </div>
      </div>
      
      <!-- 加载中动画 -->
      <div v-if="isGenerating" class="loading-indicator">
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
import dayjs from 'dayjs'
import { useProgressStore, type ProgressMessage, type PreviewImage } from '../../stores/progress'
import { useTaskProgress } from '../../composables/useTaskProgress'

const progressStore = useProgressStore()
const { createPptTask } = useTaskProgress()

// 消息容器引用
const messagesContainer = ref<HTMLElement>()

// 进度消息列表
const progressMessages = computed(() => progressStore.progressMessages)

// 预览图列表
const previewImages = computed(() => progressStore.previewImages)

// 是否正在生成
const isGenerating = computed(() => progressStore.isGenerating)

// 错误信息
const taskError = computed(() => progressStore.taskError)

// 是否有消息
const hasMessages = computed(() => progressMessages.value.length > 0)

// 是否有错误
const hasError = computed(() => progressStore.taskStatus === 'failed')

// 是否有详细错误信息
const hasDetailedError = computed(() => {
  return hasError.value && taskError.value && taskError.value.has_error
})

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 监听消息变化，自动滚动到底部
watch([progressMessages, isGenerating, hasDetailedError], () => {
  scrollToBottom()
}, { flush: 'post' })

// 格式化时间
function formatTime(time: Date) {
  return dayjs(time).format('HH:mm:ss')
}

// 获取消息对应的预览图片
function getPreviewForMessage(messageId: string): PreviewImage | null {
  // 在实际应用中，需要根据消息ID关联预览图
  // 这里简化为返回最近的预览图
  if (previewImages.value.length === 0) {
    return null
  }
  
  return previewImages.value[previewImages.value.length - 1]
}

// 处理重试
async function handleRetry() {
  if (hasError.value) {
    // 重置进度并重新创建任务
    progressStore.resetProgress()
    await createPptTask()
  }
}
</script>

<style scoped>
.chat-progress {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 12px; /* 减少内边距 */
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 防止整体溢出 */
}

.title {
  font-size: 1.1rem; /* 减小标题字体 */
  margin: 0 0 12px 0; /* 减少底部间距 */
  color: #303133;
  flex-shrink: 0; /* 标题不缩放 */
}

.messages-container {
  flex: 1; /* 占用剩余空间 */
  overflow-y: auto; /* 显示垂直滚动条 */
  padding-right: 5px; /* 为滚动条留出空间 */
  scrollbar-width: thin; /* Firefox滚动条样式 */
  scrollbar-color: #c0c4cc #f5f7fa; /* Firefox滚动条颜色 */
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

.message {
  margin-bottom: 12px; /* 减少间距 */
  padding: 10px 12px; /* 减少内边距 */
  border-radius: 6px;
  max-width: 95%;
  font-size: 0.9rem; /* 稍微减小字体 */
}

.system-message {
  align-self: center;
  background-color: #f0f9ff;
  border-left: 3px solid #409eff; /* 减少边框宽度 */
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

.message-header {
  display: flex;
  margin-bottom: 6px; /* 减少间距 */
  font-size: 0.8rem; /* 减小字体 */
  color: #909399;
}

.step-name {
  font-weight: bold;
  margin-right: 8px;
  color: #303133;
}

.progress-percent {
  margin-right: 8px;
  color: #409eff;
}

.error-indicator {
  margin-right: 8px;
  color: #f56c6c;
}

.message-time {
  margin-left: auto;
}

.message-content {
  line-height: 1.4; /* 减少行高 */
  white-space: pre-line;
}

.preview-container {
  margin-top: 10px; /* 减少间距 */
  width: 100%;
}

.preview-image {
  max-width: 100%;
  max-height: 200px; /* 限制预览图高度 */
  height: auto;
  border-radius: 4px;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.1); /* 减少阴影 */
}

.error-actions {
  margin-top: 10px; /* 减少间距 */
}

.error-details {
  font-family: 'Courier New', monospace;
  background-color: #faf2f2;
  border: 1px solid #fbc4c4;
  border-radius: 4px;
  padding: 8px; /* 减少内边距 */
  margin: 8px 0; /* 减少外边距 */
}

.error-details p {
  margin: 6px 0; /* 减少间距 */
  font-size: 0.85rem; /* 减小字体 */
  line-height: 1.3;
}

.error-details strong {
  color: #f56c6c;
  font-weight: 600;
}

.loading-indicator {
  align-self: center;
  margin-top: 15px; /* 减少间距 */
  padding: 10px 0; /* 减少内边距 */
}

.loading-dots {
  display: flex;
  justify-content: center;
  align-items: center;
}

.loading-dots span {
  display: inline-block;
  width: 8px; /* 减小点的大小 */
  height: 8px;
  margin: 0 4px; /* 减小间距 */
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
  } 40% { 
    transform: scale(1.0);
  }
}
</style> 