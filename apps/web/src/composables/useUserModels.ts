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
    
    console.log('=== currentModels计算 ===')
    console.log('用户选择:', userSelectedModels.value)
    console.log('激活配置:', activeConfigs)
    console.log('可用configs数量:', modelConfigStore.configs.length)
    
    // 如果没有加载到配置数据，使用默认配置
    if (!activeConfigs.llm && !activeConfigs.vision && !activeConfigs.deepthink) {
      console.log('使用默认模型配置')
      return defaultModels
    }
    
    const result: CurrentModels = {}
    
    // LLM和Vision模型使用全局激活的配置
    result.llm = activeConfigs.llm || defaultModels.llm
    result.vision = activeConfigs.vision || defaultModels.vision
    
    // DeepThink模型优先使用用户选择的，否则使用全局激活的
    if (userSelectedModels.value.deepthink) {
      console.log('用户选择了deepthink模型ID:', userSelectedModels.value.deepthink)
      const selectedDeepthinkConfig = modelConfigStore.configs.find(
        config => config.id === userSelectedModels.value.deepthink && config.model_type === 'deepthink'
      )
      console.log('找到的用户选择配置:', selectedDeepthinkConfig?.model_name || '未找到')
      result.deepthink = selectedDeepthinkConfig || activeConfigs.deepthink || defaultModels.deepthink
    } else {
      console.log('用户未选择deepthink模型，使用激活配置')
      result.deepthink = activeConfigs.deepthink || defaultModels.deepthink
    }
    
    console.log('最终deepthink模型:', result.deepthink?.model_name)
    console.log('=== currentModels计算结束 ===')
    
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
    console.log('=== 切换deepthink模型 ===')
    console.log('选择的模型ID:', configId)
    
    const newSelection = {
      ...userSelectedModels.value,
      deepthink: configId
    }
    
    // 首先检查选择的模型是否存在于configs中
    const selectedConfig = modelConfigStore.configs.find(
      config => config.id === configId && config.model_type === 'deepthink'
    )
    
    if (selectedConfig) {
      console.log('找到选择的模型配置:', selectedConfig.model_name)
    } else {
      console.warn('未在configs中找到选择的模型配置，ID:', configId)
      console.log('当前可用configs:', modelConfigStore.configs.filter(c => c.model_type === 'deepthink'))
    }
    
    saveUserSelectedModels(newSelection)
    
    // 输出切换后的状态用于调试
    console.log('切换后的用户选择:', newSelection)
    console.log('localStorage中的数据:', localStorage.getItem(USER_MODELS_KEY))
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