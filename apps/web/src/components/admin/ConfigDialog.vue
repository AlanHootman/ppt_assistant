<template>
  <el-dialog
    v-model="dialogVisible"
    :title="getDialogTitle()"
    width="600px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
    >
      <el-form-item label="配置名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入配置名称" />
      </el-form-item>

      <el-form-item label="模型类型" prop="model_type">
        <el-select v-model="formData.model_type" :disabled="isEdit && !isCopy" style="width: 100%">
          <el-option label="文本模型(LLM)" value="llm" />
          <el-option label="视觉模型(Vision)" value="vision" />
          <el-option label="深度思考(DeepThink)" value="deepthink" />
        </el-select>
      </el-form-item>

      <el-form-item label="API密钥" prop="api_key">
        <el-input 
          v-model="formData.api_key" 
          type="password" 
          placeholder="请输入API密钥"
          show-password
        />
      </el-form-item>

      <el-form-item label="API地址" prop="api_base">
        <el-input v-model="formData.api_base" placeholder="例如: https://api.openai.com/v1" />
      </el-form-item>

      <el-form-item label="模型名称" prop="model_name">
        <el-input v-model="formData.model_name" placeholder="例如: gpt-4" />
      </el-form-item>

      <el-form-item label="最大Token" prop="max_tokens">
        <el-input-number 
          v-model="formData.max_tokens" 
          :min="1" 
          :max="200000"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="温度参数" prop="temperature">
        <el-input-number 
          v-model="formData.temperature" 
          :min="0" 
          :max="2" 
          :step="0.1"
          :precision="1"
          style="width: 100%"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="loading">
        {{ getSubmitButtonText() }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { ModelConfig } from '../../types/modelConfig'
import { useModelConfigStore } from '../../stores/modelConfig'

interface FormInstance {
  validate: () => Promise<boolean>
  resetFields: () => void
}

interface FormRules {
  [key: string]: Array<{
    required?: boolean
    message?: string
    trigger?: string
    type?: string
    regex?: string
    ge?: number
    le?: number
  }>
}

const props = defineProps<{
  modelValue: boolean
  config?: ModelConfig | null
  modelType: string
  mode?: 'create' | 'edit' | 'copy'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: []
}>()

const modelConfigStore = useModelConfigStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const isEdit = computed(() => props.mode === 'edit')
const isCopy = computed(() => props.mode === 'copy')
const isCreate = computed(() => props.mode === 'create' || !props.mode)

const formData = ref({
  name: '',
  model_type: props.modelType as 'llm' | 'vision' | 'deepthink',
  api_key: '',
  api_base: 'https://api.openai.com/v1',
  model_name: '',
  max_tokens: 128000,
  temperature: 0.7
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  model_type: [{ required: true, message: '请选择模型类型', trigger: 'change' }],
  api_key: [{ required: true, message: '请输入API密钥', trigger: 'blur' }],
  api_base: [{ required: true, message: '请输入API地址', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  max_tokens: [{ required: true, message: '请输入最大Token数', trigger: 'blur' }],
  temperature: [{ required: true, message: '请输入温度参数', trigger: 'blur' }]
}

const getDialogTitle = () => {
  if (isCopy.value) return '复制配置'
  if (isEdit.value) return '编辑配置'
  return '新增配置'
}

const getSubmitButtonText = () => {
  if (isCopy.value) return '复制'
  if (isEdit.value) return '更新'
  return '创建'
}

// 监听props.config变化，填充表单
watch(() => props.config, (config) => {
  if (config) {
    formData.value = {
      name: isCopy.value ? `${config.name}_copy` : config.name,
      model_type: isCopy.value ? (props.modelType as 'llm' | 'vision' | 'deepthink') : config.model_type,
      api_key: config.api_key,
      api_base: config.api_base,
      model_name: config.model_name,
      max_tokens: config.max_tokens,
      temperature: config.temperature
    }
  } else {
    // 重置表单
    formData.value = {
      name: '',
      model_type: props.modelType as 'llm' | 'vision' | 'deepthink',
      api_key: '',
      api_base: 'https://api.openai.com/v1',
      model_name: '',
      max_tokens: 128000,
      temperature: 0.7
    }
  }
}, { immediate: true })

const handleSubmit = async () => {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    if (isEdit.value && props.config) {
      await modelConfigStore.updateConfig(props.config.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      // 创建或复制都使用创建接口
      await modelConfigStore.createConfig(formData.value)
      ElMessage.success(isCopy.value ? '复制成功' : '创建成功')
    }
    emit('success')
  } catch (error) {
    const action = isEdit.value ? '更新' : (isCopy.value ? '复制' : '创建')
    ElMessage.error(`${action}失败`)
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  formRef.value?.resetFields()
  emit('update:modelValue', false)
}
</script>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'ConfigDialog'
})
</script> 