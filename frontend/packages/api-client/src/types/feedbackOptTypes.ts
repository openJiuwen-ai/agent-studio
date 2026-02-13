// 反馈优化相关类型定义

// 模型信息接口
export interface ModelInfo {
  id: number
  model: string
  model_from: string
  headers: {
    temperature?: number
    max_tokens?: number
    top_p?: number
    [key: string]: any
  }
}

// 快捷优化模型信息接口
export interface QuickOptimizeModelInfo {
  id: number
  model: string
  model_from: string
  headers: Record<string, any>
}

// 智能体模型信息接口(优化提示词和智能体对接)
export interface AgentModelInfo {
  model_info: {
    api_key?: string
    api_base?: string
    model_name: string
    model_type: string
    temperature?: number
    top_p?: number
    streaming?: boolean
    max_tokens?: number
    timeout?: number
  }
  model_provider: string
}

// 快捷优化请求接口
export interface QuickOptimizeRequest {
  modelInfo: QuickOptimizeModelInfo | AgentModelInfo
  instruct: string
  stream: boolean
  workspace_id?: string
}

// 优化响应接口（流式响应）- 统一的返回格式
export interface OptimizeResponse {
  content: string
}

// 优化模式枚举
export type OptimizationMode = 'general' | 'select' | 'insert'

// 反馈优化请求接口
export interface OptimizeFeedbackRequest {
  modelInfo: QuickOptimizeModelInfo
  prompt: string
  feedback: string
  mode: OptimizationMode // 优化模式：general(全文反馈优化)、select(选中反馈)、insert(插入反馈)
  start_pos?: number // 起始位置：插入模式时为插入位置，选中模式时为选中起始位置
  end_pos?: number // 结束位置：仅选中模式时使用
  stream: boolean
  templateInfo: Record<string, any>
  workspace_id?: string
}

// Badcase接口
export interface Badcase {
  query: string // JSON字符串格式的对话历史
  label: string // 用户的评估内容
}

// Badcase优化请求接口
export interface OptimizeBadcaseRequest {
  modelInfo: QuickOptimizeModelInfo
  prompt: string
  badcases: Badcase[]
  stream: boolean
  templateInfo: Record<string, any>
  workspace_id?: string
}

// 流式响应回调函数类型
export type StreamDataCallback = (data: string) => void
export type StreamErrorCallback = (error: string) => void
export type StreamCompleteCallback = () => void

// 反馈优化API响应包装器
export interface FeedbackOptApiResponse<T> {
  code: number
  message: string
  data?: T
}

// 错误响应
export interface FeedbackOptApiError {
  code: number
  message: string
  error?: string
  details?: Record<string, any>
}
