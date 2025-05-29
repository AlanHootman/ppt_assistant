<template>
  <div class="template-selector">
    <h2 class="title">选择模板</h2>
    
    <!-- 加载中状态 -->
    <div v-if="loading" class="loading-container">
      <el-icon class="loading-icon"><i class="el-icon-loading"></i></el-icon>
      <p>正在加载模板...</p>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="error-container">
      <el-icon class="error-icon"><i class="el-icon-warning"></i></el-icon>
      <p>{{ error }}</p>
      <el-button type="primary" size="small" @click="fetchTemplates">重试</el-button>
    </div>
    
    <!-- 空数据状态 -->
    <div v-else-if="templates.length === 0" class="empty-container">
      <el-icon class="empty-icon"><i class="el-icon-document"></i></el-icon>
      <p>暂无可用模板</p>
      <p class="empty-desc">请联系管理员上传模板或稍后再试</p>
    </div>
    
    <!-- 模板列表 -->
    <div v-else class="template-list">
      <el-row :gutter="20">
        <el-col v-for="template in templates" :key="template.id" :span="8">
          <div 
            class="template-card" 
            :class="{ 'active': isSelected(template) }"
            @click="selectTemplate(template)"
          >
            <div class="template-image">
              <img 
                :src="template.preview_url || DEFAULT_TEMPLATE_IMAGE" 
                :alt="template.name"
                @error="handleImageError"
              />
            </div>
            <div class="template-info">
              <h3 class="template-name">{{ template.name }}</h3>
              <div class="template-tags">
                <el-tag 
                  v-for="tag in template.tags" 
                  :key="tag" 
                  size="small" 
                  class="tag"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useTemplateStore, type Template } from '../../stores/template'

// 默认图片路径常量
const DEFAULT_TEMPLATE_IMAGE = '/images/template-placeholder.svg'

const templateStore = useTemplateStore()
const templates = ref<Template[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// 获取模板列表
async function fetchTemplates() {
  loading.value = true
  error.value = null
  
  try {
    const result = await templateStore.fetchTemplates()
    templates.value = result.items
    
    if (templates.value.length === 0) {
      console.warn('未获取到模板数据')
    }
  } catch (err) {
    console.error('获取模板列表失败:', err)
    error.value = '获取模板列表失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// 选择模板
function selectTemplate(template: Template) {
  templateStore.setCurrentTemplate(template)
}

// 判断模板是否被选中
function isSelected(template: Template) {
  return templateStore.currentTemplate?.id === template.id
}

// 处理图片加载失败
function handleImageError(event: Event) {
  const target = event.target as HTMLImageElement
  target.src = DEFAULT_TEMPLATE_IMAGE
}

// 恢复选中的模板
async function restoreSelectedTemplate() {
  await templateStore.restoreSelectedTemplate()
}

onMounted(async () => {
  await fetchTemplates()
  
  // 如果有模板列表但当前没有选中的模板，选择第一个
  if (templates.value.length > 0 && !templateStore.currentTemplate) {
    templateStore.setCurrentTemplate(templates.value[0])
  }
})
</script>

<style scoped>
.template-selector {
  margin-bottom: 15px;
  max-height: 200px;
  overflow-y: auto;
}

.title {
  font-size: 1.1rem;
  margin-bottom: 10px;
  color: #303133;
}

.loading-container,
.error-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
  text-align: center;
  background-color: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 15px;
}

.loading-icon,
.error-icon,
.empty-icon {
  font-size: 24px;
  margin-bottom: 10px;
  color: #909399;
}

.error-icon {
  color: #f56c6c;
}

.empty-desc {
  color: #909399;
  font-size: 0.85rem;
  margin-top: 6px;
}

.template-list {
  margin-bottom: 15px;
  max-height: 150px;
  overflow-y: auto;
}

.template-card {
  background-color: #fff;
  border-radius: 6px;
  box-shadow: 0 1px 8px 0 rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: all 0.2s;
  cursor: pointer;
  margin-bottom: 12px;
  border: 2px solid transparent;
}

.template-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.1);
}

.template-card.active {
  border-color: #409eff;
}

.template-image {
  width: 100%;
  height: 100px;
  overflow: hidden;
}

.template-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}

.template-card:hover .template-image img {
  transform: scale(1.03);
}

.template-info {
  padding: 8px 12px;
}

.template-name {
  font-size: 0.9rem;
  margin: 0 0 6px 0;
  color: #303133;
  line-height: 1.3;
}

.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}

.tag {
  margin-right: 3px;
  font-size: 0.75rem;
}
</style> 