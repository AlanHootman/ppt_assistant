<template>
  <div class="model-config-management">
    <div class="page-header">
      <h1>大模型配置管理</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新增配置
      </el-button>
    </div>

    <!-- 配置列表 -->
    <div class="config-list">
      <!-- 加载状态 -->
      <div v-if="modelConfigStore.loading" class="loading-container">
        <div class="loading-content">
          <el-icon class="is-loading loading-icon"><Loading /></el-icon>
          <p class="loading-text">正在加载配置...</p>
        </div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="modelConfigStore.error" class="error-container">
        <el-alert
          title="加载失败"
          :description="modelConfigStore.error"
          type="error"
          show-icon
          :closable="false"
        >
          <template #default>
            <el-button type="primary" size="small" @click="handleRetry">
              重试
            </el-button>
          </template>
        </el-alert>
      </div>

      <!-- 正常内容 -->
      <div v-else>
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <el-tab-pane label="文本模型(LLM)" name="llm">
            <div v-if="llmConfigs.length === 0" class="empty-container">
              <el-empty description="暂无LLM模型配置">
                <el-button type="primary" @click="handleAddConfig('llm')">
                  添加LLM配置
                </el-button>
              </el-empty>
            </div>
            <ConfigTable 
              v-else
              :configs="llmConfigs" 
              model-type="llm"
              @edit="handleEdit"
              @delete="handleDelete"
              @set-active="handleSetActive"
              @copy="handleCopy"
            />
          </el-tab-pane>
          <el-tab-pane label="视觉模型(Vision)" name="vision">
            <div v-if="visionConfigs.length === 0" class="empty-container">
              <el-empty description="暂无Vision模型配置">
                <el-button type="primary" @click="handleAddConfig('vision')">
                  添加Vision配置
                </el-button>
              </el-empty>
            </div>
            <ConfigTable 
              v-else
              :configs="visionConfigs" 
              model-type="vision"
              @edit="handleEdit"
              @delete="handleDelete"
              @set-active="handleSetActive"
              @copy="handleCopy"
            />
          </el-tab-pane>
          <el-tab-pane label="深度思考(DeepThink)" name="deepthink">
            <div v-if="deepthinkConfigs.length === 0" class="empty-container">
              <el-empty description="暂无DeepThink模型配置">
                <el-button type="primary" @click="handleAddConfig('deepthink')">
                  添加DeepThink配置
                </el-button>
              </el-empty>
            </div>
            <ConfigTable 
              v-else
              :configs="deepthinkConfigs" 
              model-type="deepthink"
              @edit="handleEdit"
              @delete="handleDelete"
              @set-active="handleSetActive"
              @copy="handleCopy"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <ConfigDialog 
      v-model="showCreateDialog"
      :config="editingConfig"
      :model-type="activeTab"
      :mode="dialogMode"
      @success="handleDialogSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Loading } from '@element-plus/icons-vue'
import ConfigTable from '../../components/admin/ConfigTable.vue'
import ConfigDialog from '../../components/admin/ConfigDialog.vue'
import { useModelConfigStore } from '../../stores/modelConfig'
import type { ModelConfig } from '../../types/modelConfig'

const modelConfigStore = useModelConfigStore()

const activeTab = ref<string>('llm')
const showCreateDialog = ref(false)
const editingConfig = ref<ModelConfig | null>(null)
const dialogMode = ref<'create' | 'edit' | 'copy'>('create')

// 计算各类型配置
const llmConfigs = computed(() => 
  modelConfigStore.configs.filter((config: ModelConfig) => config.model_type === 'llm')
)
const visionConfigs = computed(() => 
  modelConfigStore.configs.filter((config: ModelConfig) => config.model_type === 'vision')
)
const deepthinkConfigs = computed(() => 
  modelConfigStore.configs.filter((config: ModelConfig) => config.model_type === 'deepthink')
)

const handleTabChange = (tabName: string) => {
  activeTab.value = tabName
  loadConfigs()
}

const handleAddConfig = (modelType: string) => {
  activeTab.value = modelType
  editingConfig.value = null
  dialogMode.value = 'create'
  showCreateDialog.value = true
}

const handleEdit = (config: ModelConfig) => {
  editingConfig.value = config
  dialogMode.value = 'edit'
  activeTab.value = config.model_type
  showCreateDialog.value = true
}

const handleCopy = (config: ModelConfig) => {
  editingConfig.value = config
  dialogMode.value = 'copy'
  // 复制时允许用户选择目标类型，默认为当前tab
  showCreateDialog.value = true
}

const handleDelete = async (config: ModelConfig) => {
  try {
    const confirmed = window.confirm(`确定要删除配置 "${config.name}" 吗？`)
    if (!confirmed) return
    
    await modelConfigStore.deleteConfig(config.id)
    ElMessage.success('删除成功')
    loadConfigs()
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败')
  }
}

const handleSetActive = async (config: ModelConfig) => {
  try {
    await modelConfigStore.setActiveConfig(config.model_type, config.id)
    ElMessage.success(`已切换到 ${config.name}`)
    loadConfigs()
  } catch (error) {
    console.error('切换失败:', error)
    ElMessage.error('切换失败')
  }
}

const handleDialogSuccess = () => {
  showCreateDialog.value = false
  editingConfig.value = null
  dialogMode.value = 'create'
  loadConfigs()
}

const handleRetry = () => {
  loadConfigs()
}

const loadConfigs = async () => {
  try {
    console.log('开始加载配置，当前tab:', activeTab.value)
    await modelConfigStore.fetchConfigs(activeTab.value)
    console.log('配置加载完成')
  } catch (error) {
    console.error('加载配置异常:', error)
    ElMessage.error('加载配置失败')
  }
}

onMounted(() => {
  console.log('组件挂载，开始加载配置')
  loadConfigs()
})
</script>

<style scoped>
.model-config-management {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.config-list {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.loading-container {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-content {
  text-align: center;
  padding: 40px;
}

.loading-icon {
  font-size: 32px;
  color: #409eff;
}

.loading-text {
  margin-top: 16px;
  color: #666;
  font-size: 14px;
}

.error-container {
  padding: 20px;
}

.empty-container {
  padding: 40px 20px;
  text-align: center;
}
</style> 