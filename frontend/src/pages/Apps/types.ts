/**
 * Apps 页面共享类型定义
 */

/**
 * 单个引用项数据
 */
export interface CitationData {
  id: number
  url: string
  title: string
  content: string
  chunk: string
  source: string
  publish_time: string
  from: string
  score: number
}

/**
 * 引用消息集合
 */
export interface CitationMessages {
  code: number
  msg: string
  data: CitationData[]
}

/**
 * 推理图消息
 */
export interface InferMessage {
  /** base64 编码的 HTML 内容 */
  html_base64: string
  /** 推理过程描述 */
  inference: string
  /** 结论 */
  conclusion: string
  /** 推理图 ID（对应 Markdown 中的 #inference:id） */
  id: number
}

/**
 * DeepSearch 后端返回结果
 */
export interface DeepSearchResult {
  /** 报告内容（Markdown 格式） */
  response_content: string
  /** 引用数据 */
  citation_messages: CitationMessages | null
  /** 推理图谱列表 */
  infer_messages: InferMessage[]
  /** 异常信息 */
  exception_info?: string
}

/**
 * 报告数据结构
 */
export interface Report {
  id: string
  title: string
  content: string
  createdAt: string
  citations?: CitationMessages | null
  /** 推理图谱消息列表（原始数据，保留完整信息） */
  inferMessages?: InferMessage[]
}

/**
 * 消息数据结构
 */
export interface Message {
  id: string
  content: string
  isUser: boolean
  status?: 'sending' | 'sent' | 'failed'
  modelName?: string
  report?: Report
}

