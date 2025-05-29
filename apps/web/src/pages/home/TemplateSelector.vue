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
  margin-bottom: 20px;
}

.title {
  font-size: 1.2rem;
  margin-bottom: 15px;
  color: #303133;
}

.loading-container,
.error-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  text-align: center;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.loading-icon,
.error-icon,
.empty-icon {
  font-size: 32px;
  margin-bottom: 16px;
  color: #909399;
}

.error-icon {
  color: #f56c6c;
}

.empty-desc {
  color: #909399;
  font-size: 0.9rem;
  margin-top: 8px;
}

.template-list {
  margin-bottom: 20px;
}

.template-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s;
  cursor: pointer;
  margin-bottom: 20px;
  border: 2px solid transparent;
}

.template-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.template-card.active {
  border-color: #409eff;
}

.template-image {
  width: 100%;
  height: 160px;
  overflow: hidden;
}

.template-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.template-card:hover .template-image img {
  transform: scale(1.05);
}

.template-info {
  padding: 10px 15px;
}

.template-name {
  font-size: 1rem;
  margin: 0 0 10px 0;
  color: #303133;
}

.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.tag {
  margin-right: 5px;
}
</style> 