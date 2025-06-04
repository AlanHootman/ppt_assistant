import type { AxiosResponse } from 'axios'
import { get, post, put, del } from './index'
import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate, ActiveModelConfigs } from '../../types/modelConfig'

interface ModelConfigListResponse {
  total: number
  configs: ModelConfig[]
}

export const modelConfigApi = {
  // 获取配置列表
  getConfigs(modelType?: string, page = 1, limit = 100) {
    return get<ModelConfigListResponse>('/model-configs/', {
      model_type: modelType, 
      page, 
      limit
    })
  },

  // 获取激活的配置
  getActiveConfigs() {
    return get<ActiveModelConfigs>('/model-configs/active')
  },

  // 获取单个配置
  getConfig(id: number) {
    return get<ModelConfig>(`/model-configs/${id}`)
  },

  // 创建配置
  createConfig(data: ModelConfigCreate) {
    return post<ModelConfig>('/model-configs/', data)
  },

  // 更新配置
  updateConfig(id: number, data: ModelConfigUpdate) {
    return put<ModelConfig>(`/model-configs/${id}`, data)
  },

  // 删除配置
  deleteConfig(id: number) {
    return del<{ message: string }>(`/model-configs/${id}`)
  },

  // 设置激活配置
  setActiveConfig(modelType: string, configId: number) {
    return post<{ message: string }>('/model-configs/set-active', {
      model_type: modelType,
      config_id: configId
    })
  }
} 