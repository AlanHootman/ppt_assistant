<template>
  <div class="deepthink-model-selector">
    <div class="model-info">
      <span class="model-label">深度思考模型:</span>
      
      <!-- 当前选中的模型 -->
      <el-tag 
        v-if="currentModels.deepthink || deepthinkConfigs.length > 0"
        type="warning" 
        size="small"
        :class="{ 'clickable': deepthinkConfigs.length > 1 }"
        @click="toggleDropdown"
      >
        {{ currentModels.deepthink?.name || '未配置' }}
        <el-icon v-if="deepthinkConfigs.length > 1" class="dropdown-icon">
          <ArrowDown />
        </el-icon>
      </el-tag>
      
      <!-- 无配置时的提示 -->
      <el-tag v-else type="info" size="small">
        暂无可用配置
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
          <div class="config-info">
            <div class="config-name">{{ config.name }}</div>
            <div class="config-model">{{ config.model_name }}</div>
          </div>
          <el-icon v-if="currentModels.deepthink?.id === config.id" class="check-icon">
            <Check />
          </el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, Check } from '@element-plus/icons-vue'
import { useUserModels } from '../../composables/useUserModels'
import type { ModelConfig } from '../../types/modelConfig'

const { 
  currentModels, 
  deepthinkConfigs, 
  selectDeepthinkModel, 
  initialize 
} = useUserModels()

const showDropdown = ref(false)

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

// 点击外部关闭下拉框
function handleClickOutside(event: Event) {
  const target = event.target as HTMLElement
  if (!target.closest('.deepthink-model-selector')) {
    showDropdown.value = false
  }
}

onMounted(() => {
  initialize()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.deepthink-model-selector {
  position: relative;
  margin-bottom: 12px;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.model-label {
  color: #6b7280;
  font-weight: 500;
  white-space: nowrap;
}

.clickable {
  cursor: pointer;
  transition: all 0.2s;
}

.clickable:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.dropdown-icon {
  margin-left: 4px;
  font-size: 12px;
  transition: transform 0.2s;
}

.dropdown {
  position: absolute;
  top: 100%;
  left: 90px;
  right: 0;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-height: 200px;
  overflow-y: auto;
  margin-top: 4px;
  min-width: 200px;
}

.dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.dropdown-item:hover {
  background-color: #f8fafc;
}

.dropdown-item.active {
  background-color: #eff6ff;
}

.config-info {
  flex: 1;
}

.config-name {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.config-model {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.check-icon {
  color: #10b981;
  font-size: 14px;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .model-info {
    font-size: 12px;
  }
  
  .dropdown {
    left: 80px;
    min-width: 180px;
  }
}
</style> 