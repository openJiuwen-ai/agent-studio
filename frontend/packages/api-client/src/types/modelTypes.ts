// 模型管理相关类型定义

// 模型提供商枚举
export enum ModelProvider {
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  DEEPSEEK = 'deepseek',
  QWEN = 'qwen',
  GOOGLE = 'google',
  BAIDU = 'baidu',
  ZHIPU = 'zhipu',
  SILICONFLOW = 'siliconflow',
  CUSTOM = 'custom',
}

// 模型参数配置
export interface ModelParameters {
  temperature: number
  max_tokens: number
  top_p?: number
}

// 模型使用统计
export interface ModelUsageStats {
  total_requests: number
  total_tokens: number
  total_cost: number
  success_rate: number
  avg_response_time: number
  last_used?: string
  daily_requests: number
  daily_tokens: number
  daily_cost: number
  monthly_requests: number
  monthly_tokens: number
  monthly_cost: number
}

// 模型配置基础信息
export interface ModelConfigBase {
  name: string
  provider: ModelProvider
  model_type: string
  base_url?: string
  is_active: boolean
  description?: string
  tags: string[]
  parameters: ModelParameters
  timeout: number
  retry_count: number
  enable_streaming: boolean
  enable_function_calling: boolean
}

// 创建模型配置请求
export interface ModelConfigCreate extends ModelConfigBase {
  api_key?: string
  space_id: string
}

// 更新模型配置请求
export interface ModelConfigUpdate extends Partial<ModelConfigBase> {
  api_key?: string
  space_id?: string
}

// 模型配置响应
export interface ModelConfigResponse extends ModelConfigBase {
  id: number
  created_at: string
  updated_at: string
  usage_stats: ModelUsageStats
  api_key_masked?: string
  is_system_model?: boolean
}

// 模型配置列表响应
export interface ModelConfigList {
  items: ModelConfigResponse[]
  total: number
  page: number
  size: number
}

// 模型测试请求
export interface ModelTestRequest {
  prompt: string
  parameters?: ModelParameters
}

// 模型测试响应
export interface ModelTestResponse {
  success: boolean
  response?: string
  error?: string
  latency: number
  tokens_used?: number
  cost?: number
}

// 模型配置过滤参数
export interface ModelConfigFilter {
  provider?: ModelProvider
  is_active?: boolean
  tags?: string[]
  search?: string
}

// 模型配置查询参数
export interface ModelConfigQueryParams {
  page?: number
  size?: number
  provider?: ModelProvider
  is_active?: boolean
  search?: string
  tags?: string
  spaceId?: string
  sort_by?: 'create_time' | 'update_time' | 'name'
  sort_order?: 'asc' | 'desc'
}

// API响应包装器
export interface ModelApiResponse<T> {
  code: number
  message: string
  data: T
}

// 错误响应
export interface ModelApiError {
  code: number
  message: string
  error?: string
  details?: Record<string, any>
  validationErrors?: ValidationError[]
}

// 验证错误
export interface ValidationError {
  field: string
  message: string
  code: string
  value?: any
}
