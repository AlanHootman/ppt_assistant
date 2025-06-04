export interface ModelConfig {
  id: number
  name: string
  model_type: 'llm' | 'vision' | 'deepthink'
  api_key: string
  api_base: string
  model_name: string
  max_tokens: number
  temperature: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by?: number
}

export interface ModelConfigCreate {
  name: string
  model_type: 'llm' | 'vision' | 'deepthink'
  api_key: string
  api_base: string
  model_name: string
  max_tokens: number
  temperature: number
}

export interface ModelConfigUpdate {
  name?: string
  api_key?: string
  api_base?: string
  model_name?: string
  max_tokens?: number
  temperature?: number
}

export interface ActiveModelConfigs {
  llm?: ModelConfig
  vision?: ModelConfig
  deepthink?: ModelConfig
} 