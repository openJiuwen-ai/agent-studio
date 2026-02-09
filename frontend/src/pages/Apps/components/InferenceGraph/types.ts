/**
 * InferenceGraph 类型定义
 */

import type { InferMessage } from '@/pages/Apps/types'

// ============ 公共类型 ============

/** InferenceGraph 组件属性 */
export interface InferenceGraphProps {
  /** 推理数据列表 */
  inferMessages?: InferMessage[]
  /** 实例唯一标识（必需） */
  instanceId: string
  /** 自定义类名 */
  className?: string
}

/** InferenceLink 组件属性 */
export interface InferenceLinkProps {
  /** 链接地址 */
  href?: string
  /** 子元素 */
  children: React.ReactNode
  /** 实例 ID */
  instanceId?: string
}

// ============ 内部类型 ============

/** GraphModal 组件属性（内部） */
export interface GraphModalProps {
  /** 是否显示 */
  show: boolean
  /** 当前 Blob URL */
  blobUrl: string | null
  /** 关闭按钮 ref */
  closeButtonRef: React.RefObject<HTMLButtonElement | null>
  /** 关闭回调 */
  onClose: () => void
  /** 在新标签页打开回调 */
  onOpenInNewTab: () => void
  /** 自定义样式类名 */
  className?: string
}

/** GraphIframe 组件属性（内部） */
export interface GraphIframeProps {
  /** 推理图谱文件列表 */
  inferFiles: string[]
  /** 自定义样式类名 */
  className?: string
}

/** useGraphModal Hook 返回值（内部） */
export interface UseGraphModalReturn {
  /** 是否打开 */
  isOpen: boolean
  /** Blob URL */
  blobUrl: string | null
  /** 关闭按钮 ref */
  closeButtonRef: React.RefObject<HTMLButtonElement | null>
  /** 打开推理图 */
  open: (htmlBase64: string) => void
  /** 关闭推理图 */
  close: () => void
  /** 在新标签页打开 */
  openInNewTab: () => void
}