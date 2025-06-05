import { ref, computed } from 'vue'
import { useModelConfigStore } from '../stores/modelConfig'
import type { ModelConfig, UserSelectedModels, CurrentModels } from '../types/modelConfig'

const USER_MODELS_KEY = 'user_selected_models'

// 默认模型配置（用于API失败时的回退显示）
const defaultModels: CurrentModels = {
  llm: {
    id: 0,
    name: 'GPT-4',
    model_type: 'llm',
    model_name: 'gpt-4',
    api_key: '',
    api_base: '',
    max_tokens: 4096,
    temperature: 0.7,
    is_active: true,
    created_at: '',
    updated_at: ''
  },
  vision: {
    id: 0,
    name: 'GPT-4 Vision',
    model_type: 'vision', 
    model_name: 'gpt-4-vision-preview',
    api_key: '',
    api_base: '',
    max_tokens: 4096,
    temperature: 0.7,
    is_active: true,
    created_at: '',
    updated_at: ''
  },
  deepthink: {
    id: 0,
    name: 'DeepSeek Chat',
    model_type: 'deepthink',
    model_name: 'deepseek-chat',
    api_key: '',
    api_base: '',
    max_tokens: 4096,
    temperature: 0.7,
    is_active: true,
    created_at: '',
    updated_at: ''
  }
}

export function useUserModels() {
  const modelConfigStore = useModelConfigStore()
  
  // 从localStorage加载用户选择的模型
  const userSelectedModels = ref<UserSelectedModels>(loadUserSelectedModels())
  
  // 计算当前使用的模型
  const currentModels = computed<CurrentModels>(() => {
    const activeConfigs = modelConfigStore.activeConfigs
    
    // 如果没有加载到配置数据，使用默认配置
    if (!activeConfigs.llm && !activeConfigs.vision && !activeConfigs.deepthink) {
      return defaultModels
    }
    
    const result: CurrentModels = {}
    
    // LLM和Vision模型使用全局激活的配置
    result.llm = activeConfigs.llm || defaultModels.llm
    result.vision = activeConfigs.vision || defaultModels.vision
    
    // DeepThink模型优先使用用户选择的，否则使用全局激活的
    if (userSelectedModels.value.deepthink) {
      const selectedDeepthinkConfig = modelConfigStore.configs.find(
        config => config.id === userSelectedModels.value.deepthink && config.model_type === 'deepthink'
      )
      result.deepthink = selectedDeepthinkConfig || activeConfigs.deepthink || defaultModels.deepthink
    } else {
      result.deepthink = activeConfigs.deepthink || defaultModels.deepthink
    }
    
    return result
  })
  
  // 获取所有deepthink模型配置
  const deepthinkConfigs = computed(() => {
    const configs = modelConfigStore.configs.filter(config => config.model_type === 'deepthink')
    // 如果没有配置数据，返回默认配置
    return configs.length > 0 ? configs : [defaultModels.deepthink as ModelConfig]
  })
  
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
    // 只获取deepthink的公共配置，用于切换
    await modelConfigStore.fetchPublicConfigs('deepthink')
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