import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate, ActiveModelConfigs } from '../types/modelConfig'
import { modelConfigApi } from '../services/api/modelConfig.api'

export const useModelConfigStore = defineStore('modelConfig', () => {
  const configs = ref<ModelConfig[]>([])
  const activeConfigs = ref<ActiveModelConfigs>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchConfigs = async (modelType?: string) => {
    loading.value = true
    error.value = null
    try {
      console.log('正在获取配置，模型类型:', modelType)
      const response = await modelConfigApi.getConfigs(modelType)
      console.log('API响应:', response)
      
      // 处理统一的API响应格式 {code, message, data}
      if (response && response.data && response.data.configs && Array.isArray(response.data.configs)) {
        configs.value = response.data.configs
        console.log('成功获取配置:', configs.value)
      } else {
        console.error('API响应数据格式不正确:', response)
        error.value = 'API响应数据格式不正确'
        configs.value = []
      }
    } catch (err) {
      // 对于401错误（未认证），这在首页是预期的，不需要记录错误
      if (err instanceof Error && (err.message.includes('401') || err.message.includes('Unauthorized'))) {
        console.info('未认证访问，使用默认配置')
        configs.value = []
        error.value = null // 清除错误状态
      } else {
        console.error('获取配置失败:', err)
        error.value = err instanceof Error ? err.message : '获取配置失败'
        configs.value = []
      }
    } finally {
      loading.value = false
    }
  }

  const fetchActiveConfigs = async () => {
    try {
      const response = await modelConfigApi.getActiveConfigs()
      console.log('获取激活配置响应:', response)
      if (response && response.data) {
        activeConfigs.value = response.data
      }
    } catch (error) {
      // 对于401错误，静默处理，保持activeConfigs为空对象
      if (error instanceof Error && (error.message.includes('401') || error.message.includes('Unauthorized'))) {
        console.info('未认证访问激活配置，将使用默认配置')
        activeConfigs.value = {}
      } else {
        console.error('获取激活配置失败:', error)
      }
    }
  }

  const fetchPublicConfigs = async (modelType: string) => {
    try {
      const response = await modelConfigApi.getPublicConfigs(modelType)
      console.log(`获取${modelType}公共配置响应:`, response)
      if (response && response.data && response.data.configs && Array.isArray(response.data.configs)) {
        // 将公共配置合并到configs中
        const publicConfigs = response.data.configs
        // 移除已存在的同类型配置，然后添加新的
        configs.value = configs.value.filter(config => config.model_type !== modelType)
        configs.value.push(...publicConfigs)
        console.log(`成功获取${modelType}公共配置:`, publicConfigs)
      }
    } catch (error) {
      console.error(`获取${modelType}公共配置失败:`, error)
    }
  }

  const createConfig = async (configData: ModelConfigCreate) => {
    try {
      const response = await modelConfigApi.createConfig(configData)
      console.log('创建配置响应:', response)
      if (response && response.data) {
        configs.value.push(response.data)
        return response.data
      }
      throw new Error('创建配置响应格式不正确')
    } catch (error) {
      console.error('创建配置失败:', error)
      throw error
    }
  }

  const updateConfig = async (id: number, configData: ModelConfigUpdate) => {
    try {
      const response = await modelConfigApi.updateConfig(id, configData)
      console.log('更新配置响应:', response)
      if (response && response.data) {
        const index = configs.value.findIndex(config => config.id === id)
        if (index !== -1) {
          configs.value[index] = response.data
        }
        return response.data
      }
      throw new Error('更新配置响应格式不正确')
    } catch (error) {
      console.error('更新配置失败:', error)
      throw error
    }
  }

  const deleteConfig = async (id: number) => {
    try {
      await modelConfigApi.deleteConfig(id)
      configs.value = configs.value.filter(config => config.id !== id)
    } catch (error) {
      console.error('删除配置失败:', error)
      throw error
    }
  }

  const setActiveConfig = async (modelType: string, configId: number) => {
    try {
      await modelConfigApi.setActiveConfig(modelType, configId)
      
      // 更新本地状态
      configs.value.forEach(config => {
        if (config.model_type === modelType) {
          config.is_active = config.id === configId
        }
      })
      
      // 重新获取激活配置
      await fetchActiveConfigs()
    } catch (error) {
      console.error('设置激活配置失败:', error)
      throw error
    }
  }

  const getActiveConfigByType = (modelType: string) => {
    return activeConfigs.value[modelType as keyof ActiveModelConfigs]
  }

  return {
    configs,
    activeConfigs,
    loading,
    error,
    fetchConfigs,
    fetchActiveConfigs,
    fetchPublicConfigs,
    createConfig,
    updateConfig,
    deleteConfig,
    setActiveConfig,
    getActiveConfigByType
  }
}) 