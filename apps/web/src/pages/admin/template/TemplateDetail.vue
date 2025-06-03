<template>
  <div class="template-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="goBack" link>
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
        <h1 class="page-title">模板详情</h1>
      </div>
    </div>

    <el-card v-if="loading" class="loading-card">
      <div class="loading-content">
        <el-skeleton :rows="10" animated />
      </div>
    </el-card>

    <el-card v-else-if="template" class="detail-card">
      <div class="template-header">
        <h2 class="template-name">{{ template.name }}</h2>
        <el-tag :type="getStatusType(template.status)">
          {{ getStatusText(template.status) }}
        </el-tag>
      </div>

      <div class="template-preview" v-if="template.preview_url">
        <img :src="template.preview_url" :alt="template.name" class="preview-image" />
      </div>
      <div class="template-preview placeholder" v-else>
        <el-icon><Picture /></el-icon>
        <span>暂无预览图</span>
      </div>

      <div class="template-info">
        <div class="info-item">
          <span class="label">模板ID:</span>
          <span class="value">{{ template.id }}</span>
        </div>
        <div class="info-item">
          <span class="label">上传时间:</span>
          <span class="value">{{ formatTime(template.upload_time) }}</span>
        </div>
        <div class="info-item" v-if="template.tags && template.tags.length > 0">
          <span class="label">标签:</span>
          <div class="value tags">
            <el-tag
              v-for="tag in template.tags"
              :key="tag"
              size="small"
              effect="plain"
              class="tag"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
        <div class="info-item description" v-if="template.description">
          <span class="label">描述:</span>
          <span class="value">{{ template.description }}</span>
        </div>
      </div>

      <div class="template-actions">
        <el-button type="primary" @click="editTemplate" :disabled="template.status !== 'ready'">
          编辑信息
        </el-button>
        <el-button type="danger" @click="deleteTemplate">
          删除模板
        </el-button>
      </div>
    </el-card>

    <el-card v-else class="error-card">
      <el-empty description="模板不存在或已被删除">
        <template #extra>
          <el-button type="primary" @click="goBack">返回列表</el-button>
        </template>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Picture } from '@element-plus/icons-vue'
import type { Template } from '../../../models/admin'
import { adminApi } from '../../../services/api/admin.api'

const router = useRouter()
const route = useRoute()
const templateId = Number(route.params.id)

const loading = ref(true)
const template = ref<Template | null>(null)

// 获取模板详情
const fetchTemplateDetail = async () => {
  loading.value = true
  
  try {
    if (isNaN(templateId)) {
      ElMessage.error('无效的模板ID')
      goBack()
      return
    }
    
    const response = await adminApi.getTemplateById(templateId)
    
    if (response.code === 200 && response.data.template) {
      template.value = response.data.template
    } else {
      ElMessage.error(response.message || '获取模板详情失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '获取模板详情失败')
    template.value = null
  } finally {
    loading.value = false
  }
}

// 返回列表
const goBack = () => {
  router.push('/admin/templates')
}

// 编辑模板
const editTemplate = () => {
  ElMessage.info('模板编辑功能正在开发中')
}

// 删除模板
const deleteTemplate = async () => {
  if (!template.value) return
  
  if (!confirm(`确定要删除模板"${template.value.name}"吗？此操作不可撤销。`)) {
    return
  }
  
  try {
    const response = await adminApi.deleteTemplate(template.value.id)
    
    if (response.code === 200) {
      ElMessage.success('模板删除成功')
      goBack()
    } else {
      ElMessage.error(response.message || '删除模板失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '删除模板失败')
  }
}

// 获取状态类型
const getStatusType = (status: string) => {
  switch (status) {
    case 'ready':
      return 'success'
    case 'analyzing':
      return 'warning'
    case 'failed':
      return 'danger'
    default:
      return 'info'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'ready':
      return '可用'
    case 'analyzing':
      return '分析中'
    case 'failed':
      return '失败'
    default:
      return '未知'
  }
}

// 格式化时间
const formatTime = (timeString: string) => {
  return new Date(timeString).toLocaleString('zh-CN')
}

// 组件挂载时获取模板详情
onMounted(() => {
  fetchTemplateDetail()
})
</script>

<style scoped>
.template-detail {
  max-width: 1000px;
  margin: 0 auto;
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

/* 加载卡片 */
.loading-card {
  margin-bottom: 2rem;
}

.loading-content {
  padding: 1rem;
}

/* 详情卡片 */
.detail-card {
  margin-bottom: 2rem;
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.template-name {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

.template-preview {
  margin-bottom: 2rem;
  border-radius: 8px;
  overflow: hidden;
  background-color: #f8fafc;
  height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.template-preview.placeholder {
  flex-direction: column;
  gap: 1rem;
  color: #9ca3af;
}

.template-preview .el-icon {
  font-size: 3rem;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.template-info {
  margin-bottom: 2rem;
}

.info-item {
  display: flex;
  margin-bottom: 1rem;
  align-items: flex-start;
}

.info-item .label {
  width: 100px;
  font-weight: 500;
  color: #4b5563;
}

.info-item .value {
  flex: 1;
  color: #1f2937;
}

.info-item.description {
  align-items: flex-start;
}

.tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tag {
  margin-right: 0;
}

.template-actions {
  display: flex;
  gap: 1rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

/* 错误卡片 */
.error-card {
  margin-bottom: 2rem;
  padding: 2rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .info-item {
    flex-direction: column;
  }
  
  .info-item .label {
    width: 100%;
    margin-bottom: 0.25rem;
  }
  
  .template-actions {
    flex-direction: column;
  }
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .page-title {
    color: #e0e0e0;
  }
  
  .detail-card :deep(.el-card__body),
  .loading-card :deep(.el-card__body),
  .error-card :deep(.el-card__body) {
    background-color: #282838;
    color: #e0e0e0;
  }
  
  .template-name {
    color: #e0e0e0;
  }
  
  .template-preview {
    background-color: #22222e;
  }
  
  .template-preview.placeholder {
    color: #8888a0;
  }
  
  .info-item .label {
    color: #b0b0c0;
  }
  
  .info-item .value {
    color: #e0e0e0;
  }
  
  .template-actions {
    border-top-color: #3c3c4c;
  }
}
</style> 