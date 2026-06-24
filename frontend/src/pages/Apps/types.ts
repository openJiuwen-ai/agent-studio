import type { CanonicalDocument } from '@/pages/Apps/components/ReportPanel/editor/canonical'

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
  /** 推理图 ID，对应 Markdown 中的 #inference:id */
  id: number
}

/**
 * VLM 图表消息
 */
export interface ChartMessage {
  chart_id: string
  chart_title?: string
  description?: string
  base64?: string
  html_base64?: string
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
  /** VLM 图表结果 */
  chart_messages?: ChartMessage[]
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
  /** VLM 图表结果 */
  chartMessages?: ChartMessage[]
  /** 原始响应内容（未清理，用于 offsets 基线） */
  rawContent?: string
  /** canonical 快照种子（供编辑态初始化使用） */
  canonicalDocument?: CanonicalDocument
}

/** 单条真实性核验记录 */
export interface TruthVerificationEntry {
  selected_text: string
  start_offset: number
  end_offset: number
  user_instruction: string
  /** 核验结论（markdown 文本） */
  content: string
  /**
   * 检索证据说明（markdown 文本），来自 collector_summary。
   * 证据不足时结论往往很简短，详细的检索/未命中说明在这里。
   */
  evidence?: string
}

/** 报告改写/同步操作类型 */
export type ReportRewriteAction = 'expand' | 'polish' | 'shorten' | 'supplementary_search' | 'sync' | 'new_task' | 'truth_verification'

/** 报告改写范围类型 */
export type RewriteScope = 'selected_only' | 'selected_and_related'

/** AI 改写状态类型 */
export type RewriteStatus = 'idle' | 'thinking' | 'writing' | 'error'

/**
 * 报告改写参数
 */
export interface ReportRewriteParams {
  /** 改写操作类型 */
  action: ReportRewriteAction
  /** 改写范围 */
  rewrite_scope?: RewriteScope
  /** 选中的文本（与 offset 同域：raw markdown 切片，发给后端做校验） */
  selectedText: string
  /**
   * 选中文本的可见渲染形态（剥除 Markdown 语法）。
   * 仅 truth_verification 使用：发给后端的是 selectedText（raw 切片），
   * 但存入批注 entry / 供 DOM 高亮搜索的是 displayText。
   */
  displayText?: string
  /** 起始偏移量（code point） */
  startOffset: number
  /** 结束偏移量（code point） */
  endOffset: number
  /** 用户自定义指令 */
  userInstruction?: string
  /** 会话 ID */
  conversationId: string
  /** 正在改写的块 ID（用于动画） */
  blockId?: string
  /** 状态变化回调 */
  onStatusChange?: (status: RewriteStatus) => void
  /** 增量更新回调 */
  onDelta?: (delta: { rewritten_text: string; original_start_offset: number; original_end_offset: number }) => void
  /** 完整快照回调 */
  onSnapshot?: (snapshot: { response_content: string }) => void
  /** 完成回调 */
  onEnd?: () => void
  /** 错误回调 */
  onError?: (error: string) => void
  /** 静默请求：不在聊天流中追加可见用户消息 */
  silent?: boolean
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
