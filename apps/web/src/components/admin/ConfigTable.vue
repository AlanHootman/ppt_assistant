<template>
  <el-table :data="configs" style="width: 100%">
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
    <el-table-column label="操作" width="200">
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
</template>

<script setup lang="ts">
import type { ModelConfig } from '../../types/modelConfig'

defineProps<{
  configs: ModelConfig[]
  modelType: string
}>()

defineEmits<{
  edit: [config: ModelConfig]
  delete: [config: ModelConfig]
  'set-active': [config: ModelConfig]
}>()

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('zh-CN')
}
</script>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'ConfigTable'
})
</script> 