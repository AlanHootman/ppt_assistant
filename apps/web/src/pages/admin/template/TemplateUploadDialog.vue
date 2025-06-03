<template>
  <el-dialog
    title="上传模板"
    v-model="dialogVisible"
    width="550px"
    destroy-on-close
    :close-on-click-modal="false"
    class="template-upload-dialog"
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
          :rows="3"
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
          :show-file-list="true"
          :file-list="fileList"
        >
          <template #trigger>
            <el-button type="primary">
              <el-icon><Upload /></el-icon>
              选择PPTX文件
            </el-button>
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
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
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

// 计算属性处理对话框显示状态
const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value)
})

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

// 文件列表（用于显示选中的文件）
const fileList = ref<any[]>([])

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
    
    // 调用API上传模板
    const response = await adminApi.uploadTemplate(uploadData)
    
    if (response.code === 201) {
      ElMessage.success('模板上传成功，正在进行分析')
      emit('update:visible', false)
      emit('uploaded', response.data)
      resetForm()
    } else {
      ElMessage.error(response.message || '模板上传失败')
    }
    
  } catch (error: any) {
    console.error('上传失败:', error)
    ElMessage.error(error.message || '模板上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  form.value.file = null
  fileList.value = []
}
</script>

<script lang="ts">
export default {
  name: 'TemplateUploadDialog'
}
</script>

<style scoped>
/* 对话框整体样式 */
.template-upload-dialog :deep(.el-dialog) {
  border-radius: 8px;
  overflow: hidden;
}

.template-upload-dialog :deep(.el-dialog__header) {
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  padding: 20px 24px 16px;
}

.template-upload-dialog :deep(.el-dialog__title) {
  color: #2c3e50;
  font-weight: 600;
  font-size: 18px;
}

.template-upload-dialog :deep(.el-dialog__body) {
  padding: 24px;
  background-color: #ffffff;
}

.template-upload-dialog :deep(.el-dialog__footer) {
  background-color: #f8f9fa;
  border-top: 1px solid #e9ecef;
  padding: 16px 24px;
}

/* 表单间距优化 */
:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.template-upload {
  width: 100%;
}

.template-upload :deep(.el-upload__tip) {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 确保label文字清晰可见 */
:deep(.el-form-item__label) {
  color: #2c3e50 !important;
  font-weight: 500;
}

/* 确保输入框背景为浅色 */
:deep(.el-input__wrapper) {
  background-color: #ffffff !important;
  border: 1px solid #dcdfe6;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

:deep(.el-input__wrapper:hover) {
  border-color: #c0c4cc;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff inset;
}

/* 确保输入框内文字清晰 */
:deep(.el-input__inner) {
  background-color: transparent !important;
  color: #2c3e50 !important;
}

/* 文本域样式 */
:deep(.el-textarea__inner) {
  background-color: #ffffff !important;
  border-color: #dcdfe6 !important;
  color: #2c3e50 !important;
}

:deep(.el-textarea__inner:hover) {
  border-color: #c0c4cc;
}

:deep(.el-textarea__inner:focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff inset;
}

/* 选择器样式 */
:deep(.el-select .el-input__wrapper) {
  background-color: #ffffff !important;
}

:deep(.el-select .el-input__inner) {
  background-color: transparent !important;
  color: #2c3e50 !important;
}

/* 标签样式 */
:deep(.el-tag) {
  background-color: #f0f2f5;
  border-color: #d9d9d9;
  color: #2c3e50;
}

/* 上传组件样式 */
:deep(.el-upload) {
  background-color: #ffffff;
}

:deep(.el-upload .el-button) {
  border: 2px dashed #d9d9d9;
  background-color: #fafafa;
  color: #409eff;
  padding: 12px 20px;
  border-radius: 6px;
  transition: all 0.3s;
}

:deep(.el-upload .el-button:hover) {
  border-color: #409eff;
  background-color: #f0f9ff;
}

/* 文件列表样式 */
:deep(.el-upload-list) {
  margin-top: 12px;
}

:deep(.el-upload-list__item) {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 8px 12px;
}

/* 只在真正的深色模式下应用深色样式 */
@media (prefers-color-scheme: dark) {
  .template-upload-dialog :deep(.el-dialog__header) {
    background-color: #1f1f1f;
    border-bottom-color: #3c3c4c;
  }
  
  .template-upload-dialog :deep(.el-dialog__title) {
    color: #e0e0e0;
  }
  
  .template-upload-dialog :deep(.el-dialog__body) {
    background-color: #2c2c2c;
  }
  
  .template-upload-dialog :deep(.el-dialog__footer) {
    background-color: #1f1f1f;
    border-top-color: #3c3c4c;
  }

  :deep(.el-form-item__label) {
    color: #e0e0e0 !important;
  }
  
  :deep(.el-input__wrapper) {
    background-color: #2c2c2c !important;
    border-color: #3c3c4c !important;
  }
  
  :deep(.el-input__inner) {
    background-color: transparent !important;
    color: #e0e0e0 !important;
  }
  
  :deep(.el-textarea__inner) {
    background-color: #2c2c2c !important;
    border-color: #3c3c4c !important;
    color: #e0e0e0 !important;
  }
  
  :deep(.el-select .el-input__wrapper) {
    background-color: #2c2c2c !important;
  }
  
  :deep(.el-select .el-input__inner) {
    color: #e0e0e0 !important;
  }
  
  :deep(.el-upload .el-button) {
    background-color: #2c2c2c;
    border-color: #3c3c4c;
    color: #409eff;
  }
  
  :deep(.el-upload .el-button:hover) {
    background-color: #1e3a5f;
    border-color: #409eff;
  }
  
  :deep(.el-upload-list__item) {
    background-color: #1f1f1f;
    border-color: #3c3c4c;
    color: #e0e0e0;
  }
  
  .template-upload :deep(.el-upload__tip) {
    color: #a0a0a0;
  }
}
</style> 