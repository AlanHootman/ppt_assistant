<template>
  <div class="template-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">模板管理</h1>
        <p class="page-subtitle">管理PPT模板，上传新模板或编辑现有模板信息</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="handleUploadClick">
          <el-icon><Plus /></el-icon>
          上传模板
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filters">
      <el-input
        v-model="searchQuery"
        placeholder="搜索模板名称..."
        style="width: 300px"
        clearable
        @input="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select
        v-model="statusFilter"
        placeholder="筛选状态"
        style="width: 150px"
        clearable
        @change="handleStatusFilter"
      >
        <el-option label="全部" value="" />
        <el-option label="可用" value="ready" />
        <el-option label="分析中" value="analyzing" />
        <el-option label="失败" value="failed" />
      </el-select>

      <el-button @click="refreshList">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 模板列表 -->
    <div class="template-grid" v-loading="loading">
      <div
        v-for="template in filteredTemplates"
        :key="template.id"
        class="template-card"
        @click="viewTemplate(template)"
      >
        <div class="template-preview">
          <img
            v-if="template.preview_url"
            :src="template.preview_url"
            :alt="template.name"
            class="preview-image"
            @error="handleImageError"
          />
          <div v-else class="preview-placeholder">
            <el-icon><Picture /></el-icon>
            <span>暂无预览</span>
          </div>
        </div>

        <div class="template-info">
          <h3 class="template-name" :title="template.name">{{ template.name }}</h3>
          
          <div class="template-status">
            <el-tag
              :type="getStatusType(template.status)"
              size="small"
            >
              {{ getStatusText(template.status) }}
            </el-tag>
          </div>

          <div class="template-meta">
            <span class="upload-time">{{ formatTime(template.upload_time) }}</span>
          </div>

          <div class="template-tags" v-if="template.tags && template.tags.length > 0">
            <el-tag
              v-for="tag in template.tags.slice(0, 3)"
              :key="tag"
              size="small"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
            <span v-if="template.tags.length > 3" class="more-tags">+{{ template.tags.length - 3 }}</span>
          </div>

          <div class="template-actions" @click.stop>
            <el-button
              size="small"
              type="primary"
              @click="viewTemplate(template)"
            >
              查看
            </el-button>
            <el-button
              size="small"
              @click="editTemplate(template)"
            >
              编辑
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="deleteTemplate(template)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && filteredTemplates.length === 0" class="empty-state">
      <el-icon><Files /></el-icon>
      <h3>暂无模板</h3>
      <p>{{ searchQuery || statusFilter ? '没有找到匹配的模板' : '还没有上传任何模板' }}</p>
      <el-button type="primary" @click="handleUploadClick" v-if="!searchQuery && !statusFilter">
        上传第一个模板
      </el-button>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="totalTemplates > pageSize">
      <el-pagination
        :current-page="currentPage"
        :page-size="pageSize"
        :total="totalTemplates"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 上传对话框 -->
    <TemplateUploadDialog
      :visible="showUploadDialog"
      @update:visible="showUploadDialog = $event"
      @uploaded="handleTemplateUploaded"
    />

    <!-- 编辑对话框 -->  
    <TemplateEditDialog
      :visible="showEditDialog"
      @update:visible="showEditDialog = $event"
      :template="editingTemplate"
      @updated="handleTemplateUpdated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Plus,
  Search,
  Refresh,
  Picture,
  Files
} from '@element-plus/icons-vue'
import { adminApi } from '../../../services/api/admin.api'
import type { Template } from '../../../models/admin'
// 使用命名导入
import * as TemplateUploadDialog from './TemplateUploadDialog.vue'
import * as TemplateEditDialog from './TemplateEditDialog.vue'

const router = useRouter()

// 数据状态
const templates = ref<Template[]>([])
const loading = ref(false)
const totalTemplates = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

// 搜索和筛选
const searchQuery = ref('')
const statusFilter = ref('')

// 对话框状态
const showUploadDialog = ref(false)
const showEditDialog = ref(false)
const editingTemplate = ref<Template | null>(null)

// 获取模板列表
const fetchTemplates = async () => {
  loading.value = true
  try {
    const response = await adminApi.getTemplates(currentPage.value, pageSize.value)
    
    if (response.code === 200) {
      templates.value = response.data.templates
      totalTemplates.value = response.data.total
    } else {
      ElMessage.error(response.message || '获取模板列表失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '获取模板列表失败')
  } finally {
    loading.value = false
  }
}

// 筛选后的模板列表
const filteredTemplates = computed(() => {
  let result = templates.value

  // 按名称搜索
  if (searchQuery.value) {
    result = result.filter(template =>
      template.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }

  // 按状态筛选
  if (statusFilter.value) {
    result = result.filter(template => template.status === statusFilter.value)
  }

  return result
})

// 处理搜索
const handleSearch = () => {
  // 实际项目中可以考虑防抖处理
  // 这里简化为使用computed筛选
}

// 处理状态筛选
const handleStatusFilter = () => {
  // 实际项目中可以调用API进行服务端筛选
}

// 刷新列表
const refreshList = () => {
  fetchTemplates()
}

// 分页处理
const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTemplates()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchTemplates()
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

// 处理图片错误
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

// 查看模板
const viewTemplate = (template: Template) => {
  router.push(`/admin/templates/${template.id}`)
}

// 临时处理上传点击 - 直到组件实现完成
const handleUploadClick = () => {
  ElMessage.info('模板上传功能正在开发中，敬请期待')
}

// 编辑模板
const editTemplate = (template: Template) => {
  // 临时提示 - 直到组件实现完成
  ElMessage.info('模板编辑功能正在开发中，敬请期待')
  // editingTemplate.value = template
  // showEditDialog.value = true
}

// 删除模板
const deleteTemplate = async (template: Template) => {
  if (!confirm(`确定要删除模板"${template.name}"吗？此操作不可撤销。`)) {
    return
  }

  try {
    const response = await adminApi.deleteTemplate(template.id)
    
    if (response.code === 200) {
      ElMessage.success('模板删除成功')
      await fetchTemplates()
    } else {
      ElMessage.error(response.message || '删除模板失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '删除模板失败')
  }
}

// 处理模板上传完成
const handleTemplateUploaded = () => {
  showUploadDialog.value = false
  fetchTemplates()
  ElMessage.success('模板上传成功')
}

// 处理模板更新完成
const handleTemplateUpdated = () => {
  showEditDialog.value = false
  editingTemplate.value = null
  fetchTemplates()
  ElMessage.success('模板信息更新成功')
}

// 组件挂载时获取数据
onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped>
.template-list {
  max-width: 1200px;
  margin: 0 auto;
}

/* ==========================================================================
   页面头部
   ========================================================================== */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  gap: 1rem;
}

.header-content {
  flex: 1;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.page-subtitle {
  color: #718096;
  margin: 0;
  font-size: 1rem;
  line-height: 1.5;
}

.header-actions {
  flex-shrink: 0;
}

/* ==========================================================================
   搜索和筛选
   ========================================================================== */

.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  align-items: center;
  flex-wrap: wrap;
}

/* ==========================================================================
   模板网格
   ========================================================================== */

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.template-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.template-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.template-preview {
  height: 200px;
  background-color: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #9ca3af;
}

.preview-placeholder .el-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.template-info {
  padding: 1rem;
}

.template-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-status {
  margin-bottom: 0.5rem;
}

.template-meta {
  color: #718096;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.template-tags {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 1rem;
}

.more-tags {
  color: #718096;
  font-size: 0.75rem;
}

.template-actions {
  display: flex;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e2e8f0;
}

/* ==========================================================================
   空状态
   ========================================================================== */

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #718096;
}

.empty-state .el-icon {
  font-size: 4rem;
  color: #d1d5db;
  margin-bottom: 1rem;
}

.empty-state h3 {
  font-size: 1.25rem;
  color: #374151;
  margin: 0 0 0.5rem 0;
}

.empty-state p {
  margin: 0 0 1.5rem 0;
}

/* ==========================================================================
   分页
   ========================================================================== */

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 2rem;
}

/* ==========================================================================
   响应式设计
   ========================================================================== */

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .filters {
    flex-direction: column;
    align-items: stretch;
  }

  .template-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .template-actions {
    flex-direction: column;
  }

  .template-actions .el-button {
    width: 100%;
  }
}

/* ==========================================================================
   深色模式支持
   ========================================================================== */

@media (prefers-color-scheme: dark) {
  .page-title {
    color: #e0e0e0;
  }
  
  .page-subtitle {
    color: #b0b0c0;
  }
  
  .template-card {
    background-color: #282838;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
  }
  
  .template-preview {
    background-color: #22222e;
  }
  
  .preview-placeholder {
    color: #8888a0;
  }
  
  .template-name {
    color: #e0e0e0;
  }
  
  .template-meta {
    color: #b0b0c0;
  }
  
  .template-actions {
    border-top-color: #3c3c4c;
  }
  
  .empty-state {
    color: #b0b0c0;
  }
  
  .empty-state .el-icon {
    color: #5a5a6a;
  }
  
  .empty-state h3 {
    color: #e0e0e0;
  }
}
</style> 