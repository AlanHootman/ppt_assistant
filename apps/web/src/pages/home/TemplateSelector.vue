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
    <div v-else class="template-grid">
      <div 
        v-for="template in templates" 
        :key="template.id"
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
          <div class="template-tags" v-if="template.tags && template.tags.length > 0">
            <el-tag 
              v-for="tag in template.tags.slice(0, 2)" 
              :key="tag" 
              size="small" 
              class="tag"
            >
              {{ tag }}
            </el-tag>
            <span v-if="template.tags.length > 2" class="more-tags">+{{ template.tags.length - 2 }}</span>
          </div>
        </div>
      </div>
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
/* ==========================================================================
   模板选择器 - 整体布局
   ========================================================================== */

.template-selector {
  margin-bottom: 1rem;
  /* 移除固定高度和滚动条设置，让内容自然展开 */
}

.title {
  font-size: 1.1rem;
  margin-bottom: 1rem;
  color: #303133;
  font-weight: 600;
}

/* ==========================================================================
   状态容器 - 加载、错误、空状态
   ========================================================================== */

.loading-container,
.error-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px dashed #d1d5db;
}

.loading-icon,
.error-icon,
.empty-icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
  color: #909399;
}

.error-icon {
  color: #f56c6c;
}

.empty-desc {
  color: #909399;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

/* ==========================================================================
   模板网格 - 响应式网格布局
   ========================================================================== */

.template-grid {
  display: grid;
  gap: 1rem;
  
  /* 默认：小屏幕单列 */
  grid-template-columns: 1fr;
}

/* 中等屏幕：双列 */
@media (min-width: 480px) {
  .template-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 大屏幕：三列 */
@media (min-width: 768px) {
  .template-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* 超大屏幕：最多四列 */
@media (min-width: 1200px) {
  .template-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1.25rem;
  }
}

/* ==========================================================================
   模板卡片 - 卡片样式和交互
   ========================================================================== */

.template-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
  border: 2px solid transparent;
  position: relative;
}

.template-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border-color: #e1e8ff;
}

.template-card.active {
  border-color: #409eff;
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.2);
}

.template-card.active::before {
  content: '✓';
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background-color: #409eff;
  color: white;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
  z-index: 1;
}

/* ==========================================================================
   模板图片 - 图片容器和样式
   ========================================================================== */

.template-image {
  width: 100%;
  height: 120px;
  overflow: hidden;
  background-color: #f5f7fa;
  position: relative;
}

.template-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.template-card:hover .template-image img {
  transform: scale(1.05);
}

/* ==========================================================================
   模板信息 - 文字内容区域
   ========================================================================== */

.template-info {
  padding: 0.75rem;
}

.template-name {
  font-size: 0.875rem;
  font-weight: 500;
  margin: 0 0 0.5rem 0;
  color: #303133;
  line-height: 1.3;
  /* 限制文字行数，避免过长 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ==========================================================================
   模板标签 - 标签显示和样式
   ========================================================================== */

.template-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

.tag {
  font-size: 0.75rem;
  margin: 0;
  border-radius: 4px;
  padding: 0.125rem 0.5rem;
  background-color: #f0f9ff;
  border-color: #bfdbfe;
  color: #1e40af;
}

.more-tags {
  font-size: 0.75rem;
  color: #6b7280;
  background-color: #f3f4f6;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-weight: 500;
}

/* ==========================================================================
   响应式优化 - 移动端适配
   ========================================================================== */

@media (max-width: 479px) {
  .template-selector {
    margin-bottom: 0.75rem;
  }
  
  .title {
    font-size: 1rem;
    margin-bottom: 0.75rem;
  }
  
  .template-grid {
    gap: 0.75rem;
  }
  
  .template-image {
    height: 100px;
  }
  
  .template-info {
    padding: 0.5rem;
  }
  
  .template-name {
    font-size: 0.8rem;
  }
  
  .loading-container,
  .error-container,
  .empty-container {
    padding: 1.5rem 1rem;
  }
}

/* ==========================================================================
   可访问性和交互增强
   ========================================================================== */

.template-card:focus {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .template-card {
    transition: none;
  }
  
  .template-card:hover {
    transform: none;
  }
  
  .template-image img {
    transition: none;
  }
  
  .template-card:hover .template-image img {
    transform: none;
  }
}
</style> 