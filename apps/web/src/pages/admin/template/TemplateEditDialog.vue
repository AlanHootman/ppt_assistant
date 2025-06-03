<template>
  <el-dialog
    title="编辑模板"
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    width="550px"
    destroy-on-close
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
      v-loading="loading"
    >
      <el-form-item label="模板ID">
        <el-input v-model="templateId" disabled />
      </el-form-item>
      
      <el-form-item label="模板名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入模板名称" />
      </el-form-item>
      
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          rows="3"
          placeholder="请输入模板描述（可选）"
        />
      </el-form-item>
      
      <el-form-item label="标签" prop="tags">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="请选择或创建标签（可选）"
          style="width: 100%"
        >
          <el-option
            v-for="tag in predefinedTags"
            :key="tag"
            :label="tag"
            :value="tag"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="状态">
        <el-tag :type="getStatusType(template?.status)">
          {{ getStatusText(template?.status) }}
        </el-tag>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="$emit('update:visible', false)">取消</el-button>
        <el-button
          type="primary"
          @click="submitForm"
          :loading="saving"
          :disabled="loading"
        >
          {{ saving ? '保存中...' : '保存' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { Template } from '../../../models/admin'
import { adminApi } from '../../../services/api/admin.api'

const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
    default: false
  },
  template: {
    type: Object as () => Template | null,
    required: true,
    default: null
  }
})

const emit = defineEmits(['update:visible', 'updated'])

// 表单引用
const formRef = ref()
const loading = ref(false)
const saving = ref(false)

// 模板ID
const templateId = computed(() => props.template?.id || '')

// 表单数据
const form = ref({
  name: '',
  description: '',
  tags: [] as string[]
})

// 预定义标签
const predefinedTags = [
  '商务',
  '教育',
  '创意',
  '简约',
  '科技',
  '医疗',
  '营销'
]

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入模板名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度应为2-50个字符', trigger: 'blur' }
  ]
}

// 获取状态类型
const getStatusType = (status: string | undefined) => {
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
const getStatusText = (status: string | undefined) => {
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

// 监听模板数据变化，初始化表单
watch(() => props.template, (newVal) => {
  if (newVal) {
    form.value.name = newVal.name || ''
    form.value.description = newVal.description || ''
    form.value.tags = [...(newVal.tags || [])]
  }
}, { immediate: true })

// 提交表单
const submitForm = async () => {
  if (!formRef.value || !props.template) return
  
  try {
    // 表单验证
    await formRef.value.validate()
    
    saving.value = true
    
    // 准备更新数据
    const updateData = {
      name: form.value.name,
      description: form.value.description || undefined,
      tags: form.value.tags.length > 0 ? form.value.tags : undefined
    }
    
    // 模拟API调用
    // const response = await adminApi.updateTemplate(props.template.id, updateData)
    
    setTimeout(() => {
      ElMessage.success('模板信息更新成功')
      emit('update:visible', false)
      emit('updated')
      saving.value = false
    }, 1000)
    
  } catch (error: any) {
    console.error('表单验证失败:', error)
    saving.value = false
  }
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style> 