// Embedding 模型管理相关类型定义

// Embedding 协议枚举
export enum EmbeddingProtocol {
  OPENAI = 'openai',
}

// Embedding 模型配置基础信息
export interface EmbeddingModelConfigBase {
  model_name: string // 配置名称
  space_id: string // 空间ID
  protocol: EmbeddingProtocol // 协议类型
  model_id: string // 模型ID，如 text-embedding-v3
  api_base: string // API端点URL
  max_batch_size: number // 最大批处理大小
  is_active: boolean // 是否激活
}

// 创建 Embedding 模型配置请求
export interface EmbeddingModelConfigCreate extends EmbeddingModelConfigBase {
  api_key: string // API密钥（必填）
}

// 更新 Embedding 模型配置请求
export interface EmbeddingModelConfigUpdate {
  model_name?: string
  protocol?: EmbeddingProtocol
  model_id?: string
  api_key?: string
  api_base?: string
  max_batch_size?: number
  is_active?: boolean
}

// Embedding 模型配置响应
export interface EmbeddingModelConfigResponse extends EmbeddingModelConfigBase {
  id: number
  created_at: string
  updated_at: string
  api_key_masked?: string // 脱敏的API密钥
  is_system_model?: boolean
}

// Embedding 模型配置列表响应
export interface EmbeddingModelConfigList {
  items: EmbeddingModelConfigResponse[]
  total: number
  page: number
  size: number
}

// Embedding 模型配置请求（用于获取单个、删除、切换状态）
export interface EmbeddingModelConfigRequest {
  config_id: number
  space_id: string
}

// Embedding 模型测试请求
export interface EmbeddingModelTestRequest {
  text?: string // 单文本测试
  texts?: string[] // 批量文本测试
}

// Embedding 模型测试响应
export interface EmbeddingModelTestResponse {
  object: string
  data: Array<{
    object: string
    embedding: number[]
    index: number
  }>
  model: string
  usage: {
    prompt_tokens: number
    total_tokens: number
  }
}

// Embedding 模型配置查询参数
export interface EmbeddingModelConfigQueryParams {
  page?: number
  size?: number
  protocol?: EmbeddingProtocol
  is_active?: boolean
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

// API响应包装器
export interface EmbeddingModelApiResponse<T> {
  code: number
  message: string
  data: T
}

// 错误响应
export interface EmbeddingModelApiError {
  code: number
  message: string
  error?: string
  details?: Record<string, any>
}

