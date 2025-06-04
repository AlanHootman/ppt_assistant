<template>
  <div class="model-config-panel">
    <div class="config-header">
      <span class="config-title">当前模型</span>
      <div class="model-summary">
        <el-tag size="small" type="primary">{{ currentModels.llm?.model_name || 'LLM未配置' }}</el-tag>
        <el-tag size="small" type="success">{{ currentModels.vision?.model_name || 'Vision未配置' }}</el-tag>
        <div class="deepthink-selector">
          <el-tag 
            size="small" 
            type="warning"
            :class="{ 'clickable': deepthinkConfigs.length > 1 }"
            @click="toggleDropdown"
          >
            {{ currentModels.deepthink?.model_name || 'DeepThink未配置' }}
            <el-icon v-if="deepthinkConfigs.length > 1" class="dropdown-icon">
              <ArrowDown />
            </el-icon>
          </el-tag>
          
          <!-- 下拉选择框 -->
          <div v-if="showDropdown && deepthinkConfigs.length > 1" class="dropdown">
            <div 
              v-for="config in deepthinkConfigs" 
              :key="config.id"
              class="dropdown-item"
              :class="{ 'active': currentModels.deepthink?.id === config.id }"
              @click="selectModel(config)"
            >
              <span class="config-name">{{ config.name }}</span>
              <span class="config-model">{{ config.model_name }}</span>
              <el-icon v-if="currentModels.deepthink?.id === config.id" class="check-icon">
                <Check />
              </el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 多模态检测设置 -->
    <div class="setting-row">
      <span class="setting-label">多模态检测修正</span>
      <el-switch
        v-model="enableMultimodalValidation"
        size="small"
        @change="onMultimodalChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, defineOptions } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, Check } from '@element-plus/icons-vue'
import { useUserModels } from '../../composables/useUserModels'
import { useModelConfigStore } from '../../stores/modelConfig'
import type { ModelConfig } from '../../types/modelConfig'

defineOptions({
  name: 'ModelConfigPanel'
})

// Props and Emits
const props = defineProps<{
  enableMultimodalValidation: boolean
}>()

const emit = defineEmits<{
  'update:enableMultimodalValidation': [value: boolean]
}>()

const modelConfigStore = useModelConfigStore()
const { 
  currentModels, 
  deepthinkConfigs, 
  selectDeepthinkModel, 
  initialize 
} = useUserModels()

const showDropdown = ref(false)
const loading = computed(() => modelConfigStore.loading)

// 多模态检测设置
const enableMultimodalValidation = computed({
  get: () => props.enableMultimodalValidation,
  set: (value) => emit('update:enableMultimodalValidation', value)
})

// 切换下拉框显示
function toggleDropdown() {
  if (deepthinkConfigs.value.length > 1) {
    showDropdown.value = !showDropdown.value
  }
}

// 选择模型
function selectModel(config: ModelConfig) {
  selectDeepthinkModel(config.id)
  showDropdown.value = false
  ElMessage.success(`已切换到 ${config.name}`)
}

// 多模态设置变化
function onMultimodalChange(value: boolean) {
  ElMessage.info(value ? '已开启多模态检测修正' : '已关闭多模态检测修正')
}

// 点击外部关闭下拉框
function handleClickOutside(event: Event) {
  const target = event.target as HTMLElement
  if (!target.closest('.model-config-panel')) {
    showDropdown.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  
  try {
    // 尝试初始化模型配置数据
    await initialize()
    console.log('模型配置初始化完成')
    console.log('当前模型:', currentModels.value)
    console.log('DeepThink配置:', deepthinkConfigs.value)
  } catch (error) {
    // 如果是401错误（未认证），这是预期的，因为首页不需要登录
    if (error instanceof Error && error.message.includes('401')) {
      console.info('首页无需认证，使用默认模型配置显示')
    } else {
      console.warn('初始化模型配置失败，使用默认配置:', error)
    }
    // 静默处理错误，不显示错误消息给用户
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.model-config-panel {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

/* 配置头部 */
.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.config-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.model-summary {
  display: flex;
  align-items: center;
  gap: 8px;
}

.deepthink-selector {
  position: relative;
}

.deepthink-selector .el-tag.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
}

.deepthink-selector .el-tag.clickable:hover {
  opacity: 0.8;
  transform: translateY(-1px);
}

.dropdown-icon {
  font-size: 12px;
  margin-left: 4px;
}

.dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-height: 180px;
  overflow-y: auto;
  margin-top: 4px;
  min-width: 200px;
}

.dropdown-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-bottom: 1px solid #f3f4f6;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background-color: #f9fafb;
}

.dropdown-item.active {
  background-color: #eff6ff;
}

.config-name {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  margin-right: 8px;
}

.config-model {
  font-size: 11px;
  color: #6b7280;
  flex: 1;
}

.check-icon {
  color: #10b981;
  font-size: 14px;
}

/* 设置区域 */
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.setting-label {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .model-config-panel {
    padding: 10px 12px;
    margin-bottom: 12px;
  }
  
  .config-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .config-title {
    font-size: 13px;
  }
  
  .model-summary {
    flex-wrap: wrap;
    gap: 6px;
  }
  
  .setting-row {
    padding-top: 10px;
  }
  
  .setting-label {
    font-size: 11px;
  }
}
</style> 