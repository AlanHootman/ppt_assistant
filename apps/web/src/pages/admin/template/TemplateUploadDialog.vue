<template>
  <el-dialog
    title="上传模板"
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
    >
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
      
      <el-form-item label="模板文件" prop="file">
        <el-upload
          class="template-upload"
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          :limit="1"
          accept=".pptx"
        >
          <template #trigger>
            <el-button type="primary">选择文件</el-button>
          </template>
          <template #tip>
            <div class="el-upload__tip">
              请上传PPTX格式文件，文件大小不超过10MB
            </div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="$emit('update:visible', false)">取消</el-button>
        <el-button
          type="primary"
          @click="submitForm"
          :loading="uploading"
        >
          {{ uploading ? '上传中...' : '上传' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '../../../services/api/admin.api'

// 定义props和emits
const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'uploaded'])

// 表单引用
const formRef = ref()

// 上传状态
const uploading = ref(false)

// 表单数据
const form = ref({
  name: '',
  description: '',
  tags: [],
  file: null as File | null
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
  ],
  file: [
    { required: true, message: '请选择模板文件', trigger: 'change' }
  ]
}

// 文件变更处理
const handleFileChange = (file: any) => {
  if (file.raw) {
    // 检查文件类型
    if (file.raw.type !== 'application/vnd.openxmlformats-officedocument.presentationml.presentation') {
      ElMessage.error('只能上传PPTX格式文件!')
      form.value.file = null
      return false
    }
    
    // 检查文件大小
    if (file.raw.size / 1024 / 1024 > 10) {
      ElMessage.error('文件大小不能超过10MB!')
      form.value.file = null
      return false
    }
    
    form.value.file = file.raw
  }
}

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    // 表单验证
    await formRef.value.validate()
    
    if (!form.value.file) {
      ElMessage.error('请选择模板文件')
      return
    }
    
    uploading.value = true
    
    // 准备上传数据
    const uploadData = {
      file: form.value.file,
      name: form.value.name,
      description: form.value.description || undefined,
      tags: form.value.tags.length > 0 ? form.value.tags : undefined
    }
    
    // 暂时用假数据模拟上传成功
    // const response = await adminApi.uploadTemplate(uploadData)
    
    setTimeout(() => {
      ElMessage.success('模板上传成功')
      emit('update:visible', false)
      emit('uploaded')
      resetForm()
      uploading.value = false
    }, 2000)
    
  } catch (error: any) {
    console.error('表单验证失败:', error)
  }
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  form.value.file = null
}
</script>

<style scoped>
.template-upload {
  width: 100%;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style> 