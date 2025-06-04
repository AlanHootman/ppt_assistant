import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate, ActiveModelConfigs } from '../types/modelConfig'
import { modelConfigApi } from '../services/api/modelConfig.api'

export const useModelConfigStore = defineStore('modelConfig', () => {
  const configs = ref<ModelConfig[]>([])
  const activeConfigs = ref<ActiveModelConfigs>({})
  const loading = ref(false)

  const fetchConfigs = async (modelType?: string) => {
    loading.value = true
    try {
      const response = await modelConfigApi.getConfigs(modelType)
      configs.value = response.data.configs
    } finally {
      loading.value = false
    }
  }

  const fetchActiveConfigs = async () => {
    try {
      const response = await modelConfigApi.getActiveConfigs()
      activeConfigs.value = response.data
    } catch (error) {
      console.error('获取激活配置失败:', error)
    }
  }

  const createConfig = async (configData: ModelConfigCreate) => {
    const response = await modelConfigApi.createConfig(configData)
    configs.value.push(response.data)
    return response.data
  }

  const updateConfig = async (id: number, configData: ModelConfigUpdate) => {
    const response = await modelConfigApi.updateConfig(id, configData)
    const index = configs.value.findIndex(config => config.id === id)
    if (index !== -1) {
      configs.value[index] = response.data
    }
    return response.data
  }

  const deleteConfig = async (id: number) => {
    await modelConfigApi.deleteConfig(id)
    configs.value = configs.value.filter(config => config.id !== id)
  }

  const setActiveConfig = async (modelType: string, configId: number) => {
    await modelConfigApi.setActiveConfig(modelType, configId)
    
    // 更新本地状态
    configs.value.forEach(config => {
      if (config.model_type === modelType) {
        config.is_active = config.id === configId
      }
    })
    
    // 重新获取激活配置
    await fetchActiveConfigs()
  }

  const getActiveConfigByType = (modelType: string) => {
    return activeConfigs.value[modelType as keyof ActiveModelConfigs]
  }

  return {
    configs,
    activeConfigs,
    loading,
    fetchConfigs,
    fetchActiveConfigs,
    createConfig,
    updateConfig,
    deleteConfig,
    setActiveConfig,
    getActiveConfigByType
  }
}) 