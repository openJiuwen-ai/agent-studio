/**
 * DownloadPanel 类型定义
 */

/**
 * 下载格式类型
 */
export type DownloadFormat = 'markdown' | 'html' | 'docx'

/**
 * 格式选项配置
 */
export interface FormatOption {
  value: DownloadFormat
  label: string
  extension: string
  mimeType: string
}

/**
 * 下载 Hook 返回值
 */
export interface UseDownloadReturn {
  /** 当前选中的下载格式 */
  downloadFormat: DownloadFormat
  /** 是否正在下载 */
  isDownloading: boolean
  /** 选择格式 */
  selectFormat: (format: DownloadFormat) => Promise<void>
}

/**
 * 重新导出组件类型（从各自组件文件中导出）
 */
export type { DownloadButtonProps } from './components/DownloadButton'