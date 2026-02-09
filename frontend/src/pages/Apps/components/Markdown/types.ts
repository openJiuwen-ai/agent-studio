/**
 * Markdown 组件类型定义
 */

import type { CitationMessages, InferMessage } from '@/pages/Apps/types'

// ============ Markdown 组件 Props 类型 ============

export interface MarkdownProps {
  /** Markdown 内容 */
  content: string
  /** 自定义类名 */
  className?: string
  /** 引用数据 */
  citations?: CitationMessages | null
  /** 实例 ID（用于缓存管理） */
  instanceId?: string | null
  /** 推理图数据 */
  inferMessages?: InferMessage[]
}

/** MermaidChart 组件属性 */
export interface MermaidCodeBlockProps {
  /** Mermaid 图表代码 */
  code: string
  /** 自定义类名 */
  className?: string
}