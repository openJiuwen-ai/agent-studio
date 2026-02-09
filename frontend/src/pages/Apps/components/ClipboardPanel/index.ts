/**
 * ClipboardPanel 模块统一导出
 *
 * @description
 * 剪贴板面板模块 - 处理内容复制功能
 * 可独立使用，不依赖 ReportPanel
 */

// ============ 组件 ============

export { ClipboardButton } from './components/ClipboardButton'

// ============ Hooks ============

export { useClipboard } from './hooks'
export type { UseClipboardReturn } from './hooks/useClipboard'

// ============ 类型 ============

export type { ClipboardButtonProps } from './types'