import { ref, computed } from 'vue'
import { useModelConfigStore } from '../stores/modelConfig'
import type { ModelConfig, UserSelectedModels, CurrentModels } from '../types/modelConfig'

const USER_MODELS_KEY = 'user_selected_models'

export function useUserModels() {
  const modelConfigStore = useModelConfigStore()
  
  // 从localStorage加载用户选择的模型
  const userSelectedModels = ref<UserSelectedModels>(loadUserSelectedModels())
  
  // 计算当前使用的模型
  const currentModels = computed<CurrentModels>(() => {
    const activeConfigs = modelConfigStore.activeConfigs
    const result: CurrentModels = {}
    
    // LLM和Vision模型使用全局激活的配置
    result.llm = activeConfigs.llm
    result.vision = activeConfigs.vision
    
    // DeepThink模型优先使用用户选择的，否则使用全局激活的
    if (userSelectedModels.value.deepthink) {
      const selectedDeepthinkConfig = modelConfigStore.configs.find(
        config => config.id === userSelectedModels.value.deepthink && config.model_type === 'deepthink'
      )
      result.deepthink = selectedDeepthinkConfig || activeConfigs.deepthink
    } else {
      result.deepthink = activeConfigs.deepthink
    }
    
    return result
  })
  
  // 获取所有deepthink模型配置
  const deepthinkConfigs = computed(() => 
    modelConfigStore.configs.filter(config => config.model_type === 'deepthink')
  )
  
  // 加载用户选择的模型
  function loadUserSelectedModels(): UserSelectedModels {
    try {
      const stored = localStorage.getItem(USER_MODELS_KEY)
      return stored ? JSON.parse(stored) : {}
    } catch (error) {
      console.warn('加载用户模型选择失败:', error)
      return {}
    }
  }
  
  // 保存用户选择的模型
  function saveUserSelectedModels(models: UserSelectedModels) {
    try {
      localStorage.setItem(USER_MODELS_KEY, JSON.stringify(models))
      userSelectedModels.value = { ...models }
    } catch (error) {
      console.error('保存用户模型选择失败:', error)
    }
  }
  
  // 选择deepthink模型
  function selectDeepthinkModel(configId: number) {
    const newSelection = {
      ...userSelectedModels.value,
      deepthink: configId
    }
    saveUserSelectedModels(newSelection)
  }
  
  // 重置为默认选择
  function resetToDefault() {
    saveUserSelectedModels({})
  }
  
  // 初始化：确保加载了模型配置
  async function initialize() {
    await modelConfigStore.fetchActiveConfigs()
    await modelConfigStore.fetchConfigs()
  }
  
  return {
    currentModels,
    deepthinkConfigs,
    userSelectedModels: computed(() => userSelectedModels.value),
    selectDeepthinkModel,
    resetToDefault,
    initialize
  }
} 