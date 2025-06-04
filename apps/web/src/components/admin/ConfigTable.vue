<template>
  <div class="config-table">
    <div v-if="!configs || configs.length === 0" class="no-data">
      <p>No Data</p>
    </div>
    <el-table v-else :data="configs" style="width: 100%">
      <el-table-column prop="name" label="配置名称" width="200" />
      <el-table-column prop="model_name" label="模型名称" width="200" />
      <el-table-column prop="api_base" label="API地址" width="300" />
      <el-table-column prop="max_tokens" label="最大Token" width="120" />
      <el-table-column prop="temperature" label="温度" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '激活' : '未激活' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button 
            v-if="!row.is_active" 
            type="success" 
            size="small" 
            @click="$emit('set-active', row)"
          >
            激活
          </el-button>
          <el-button size="small" @click="$emit('edit', row)">
            编辑
          </el-button>
          <el-button 
            type="primary" 
            size="small" 
            plain
            @click="$emit('copy', row)"
          >
            复制
          </el-button>
          <el-button 
            v-if="!row.is_active" 
            type="danger" 
            size="small" 
            @click="$emit('delete', row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import type { ModelConfig } from '../../types/modelConfig'

const props = defineProps<{
  configs: ModelConfig[]
  modelType: string
}>()

defineEmits<{
  edit: [config: ModelConfig]
  delete: [config: ModelConfig]
  'set-active': [config: ModelConfig]
  copy: [config: ModelConfig]
}>()

// 添加调试信息
watch(() => props.configs, (newConfigs) => {
  console.log(`ConfigTable收到的${props.modelType}配置:`, newConfigs)
}, { immediate: true })

const formatDate = (dateString: string) => {
  try {
    return new Date(dateString).toLocaleString('zh-CN')
  } catch (error) {
    return dateString
  }
}
</script>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'ConfigTable'
})
</script>

<style scoped>
.config-table {
  width: 100%;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 16px;
}
</style> 