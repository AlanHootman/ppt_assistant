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
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="文本模型(LLM)" name="llm">
          <ConfigTable 
            :configs="llmConfigs" 
            model-type="llm"
            @edit="handleEdit"
            @delete="handleDelete"
            @set-active="handleSetActive"
          />
        </el-tab-pane>
        <el-tab-pane label="视觉模型(Vision)" name="vision">
          <ConfigTable 
            :configs="visionConfigs" 
            model-type="vision"
            @edit="handleEdit"
            @delete="handleDelete"
            @set-active="handleSetActive"
          />
        </el-tab-pane>
        <el-tab-pane label="深度思考(DeepThink)" name="deepthink">
          <ConfigTable 
            :configs="deepthinkConfigs" 
            model-type="deepthink"
            @edit="handleEdit"
            @delete="handleDelete"
            @set-active="handleSetActive"
          />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 创建/编辑对话框 -->
    <ConfigDialog 
      v-model="showCreateDialog"
      :config="editingConfig"
      :model-type="activeTab"
      @success="handleDialogSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import ConfigTable from '../../components/admin/ConfigTable.vue'
import ConfigDialog from '../../components/admin/ConfigDialog.vue'
import { useModelConfigStore } from '../../stores/modelConfig'
import type { ModelConfig } from '../../types/modelConfig'

const modelConfigStore = useModelConfigStore()

const activeTab = ref<string>('llm')
const showCreateDialog = ref(false)
const editingConfig = ref<ModelConfig | null>(null)

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

const handleEdit = (config: ModelConfig) => {
  editingConfig.value = config
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
    ElMessage.error('删除失败')
  }
}

const handleSetActive = async (config: ModelConfig) => {
  try {
    await modelConfigStore.setActiveConfig(config.model_type, config.id)
    ElMessage.success(`已切换到 ${config.name}`)
    loadConfigs()
  } catch (error) {
    ElMessage.error('切换失败')
  }
}

const handleDialogSuccess = () => {
  showCreateDialog.value = false
  editingConfig.value = null
  loadConfigs()
}

const loadConfigs = async () => {
  try {
    await modelConfigStore.fetchConfigs(activeTab.value)
  } catch (error) {
    ElMessage.error('加载配置失败')
  }
}

onMounted(() => {
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
</style> 