/**
 * DownloadPanel 模块统一导出
 *
 * @description
 * 下载面板模块 - 处理内容下载和格式转换
 * 可独立使用，不依赖 ReportPanel
 */

// ============ 组件 ============

export { DownloadButton } from './components/DownloadButton'
export { FormatMenu } from './components/FormatMenu'

// ============ Hooks ============

export { useDownload } from './hooks'
export type { UseDownloadReturn } from './hooks'

// ============ 服务 ============

export { downloadApiService, DownloadApiService } from './services/downloadApi'

// ============ 常量 ============

export { FORMAT_OPTIONS_BASE, getFormatOptions } from './constants'

// ============ 类型 ============

export type {
  DownloadFormat,
  FormatOption,
  DownloadButtonProps,
} from './types'