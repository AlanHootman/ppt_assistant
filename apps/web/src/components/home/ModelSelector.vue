<template>
  <div class="model-selector">
    <div class="current-models">
      <h3>当前使用的模型</h3>
      <div class="model-cards">
        <div class="model-card">
          <div class="model-label">文本模型</div>
          <div class="model-info">
            <span class="model-name">{{ activeConfigs.llm?.model_name || '未配置' }}</span>
            <el-button 
              v-if="llmConfigs.length > 1" 
              size="small" 
              @click="showSelector('llm')"
            >
              切换
            </el-button>
          </div>
        </div>
        
        <div class="model-card">
          <div class="model-label">视觉模型</div>
          <div class="model-info">
            <span class="model-name">{{ activeConfigs.vision?.model_name || '未配置' }}</span>
            <el-button 
              v-if="visionConfigs.length > 1" 
              size="small" 
              @click="showSelector('vision')"
            >
              切换
            </el-button>
          </div>
        </div>
        
        <div class="model-card">
          <div class="model-label">深度思考</div>
          <div class="model-info">
            <span class="model-name">{{ activeConfigs.deepthink?.model_name || '未配置' }}</span>
            <el-button 
              v-if="deepthinkConfigs.length > 1" 
              size="small" 
              @click="showSelector('deepthink')"
            >
              切换
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 模型选择弹窗 -->
    <el-dialog 
      v-model="selectorVisible" 
      :title="`选择${getModelTypeLabel(selectedType)}模型`"
      width="500px"
    >
      <div class="model-options">
        <div 
          v-for="config in getCurrentConfigs()" 
          :key="config.id"
          class="model-option"
          :class="{ active: config.is_active }"
          @click="selectModel(config)"
        >
          <div class="option-header">
            <span class="option-name">{{ config.name }}</span>
            <el-tag v-if="config.is_active" type="success" size="small">当前</el-tag>
          </div>
          <div class="option-details">
            <span>{{ config.model_name }}</span>
            <span class="api-base">{{ config.api_base }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useModelConfigStore } from '../../stores/modelConfig'

const modelConfigStore = useModelConfigStore()

const selectorVisible = ref(false)
const selectedType = ref<string>('')

// 获取激活的配置
const activeConfigs = computed(() => modelConfigStore.activeConfigs)

// 各类型配置
const llmConfigs = computed(() => 
  modelConfigStore.configs.filter(config => config.model_type === 'llm')
)
const visionConfigs = computed(() => 
  modelConfigStore.configs.filter(config => config.model_type === 'vision')
)
const deepthinkConfigs = computed(() => 
  modelConfigStore.configs.filter(config => config.model_type === 'deepthink')
)

const showSelector = (modelType: string) => {
  selectedType.value = modelType
  selectorVisible.value = true
}

const getCurrentConfigs = () => {
  switch (selectedType.value) {
    case 'llm': return llmConfigs.value
    case 'vision': return visionConfigs.value
    case 'deepthink': return deepthinkConfigs.value
    default: return []
  }
}

const getModelTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    llm: '文本',
    vision: '视觉',
    deepthink: '深度思考'
  }
  return labels[type] || type
}

const selectModel = async (config: any) => {
  if (config.is_active) {
    selectorVisible.value = false
    return
  }

  try {
    await modelConfigStore.setActiveConfig(config.model_type, config.id)
    ElMessage.success(`已切换到 ${config.name}`)
    selectorVisible.value = false
  } catch (error) {
    ElMessage.error('切换失败')
  }
}

const loadData = async () => {
  await Promise.all([
    modelConfigStore.fetchActiveConfigs(),
    modelConfigStore.fetchConfigs('llm'),
    modelConfigStore.fetchConfigs('vision'),
    modelConfigStore.fetchConfigs('deepthink')
  ])
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.model-selector {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.current-models h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.model-cards {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.model-card {
  flex: 1;
  min-width: 200px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  background: #fafafa;
}

.model-label {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}

.model-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-name {
  font-weight: 500;
  color: #303133;
}

.model-options {
  max-height: 400px;
  overflow-y: auto;
}

.model-option {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.model-option:hover {
  border-color: #409eff;
  background: #f0f9ff;
}

.model-option.active {
  border-color: #67c23a;
  background: #f0f9ff;
}

.option-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.option-name {
  font-weight: 500;
  color: #303133;
}

.option-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.option-details span {
  font-size: 12px;
  color: #606266;
}

.api-base {
  opacity: 0.8;
}
</style> 