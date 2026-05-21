/**
 * 下载格式常量配置
 */

/** 格式选项配置 */
export interface FormatOption {
  value: 'markdown' | 'html' | 'docx'
  labelKey: string
  extension: string
  downloadExtension: string
  mimeType: string
}

/** 格式选项原始配置（不含翻译） */
export const FORMAT_OPTIONS_BASE: readonly FormatOption[] = [
  { value: 'markdown', labelKey: 'markdown', extension: '.md', downloadExtension: '.md', mimeType: 'text/markdown' },
  { value: 'html', labelKey: 'html', extension: '.html', downloadExtension: '_html.zip', mimeType: 'application/zip' },
  { value: 'docx', labelKey: 'wordDocument', extension: '.docx', downloadExtension: '_docx.zip', mimeType: 'application/zip' },
] as const

/**
 * 获取带翻译的格式选项
 * @param t - 翻译函数
 * @returns 格式选项数组
 */
export const getFormatOptions = (t: (key: string) => string): readonly {
  value: 'markdown' | 'html' | 'docx'
  label: string
  extension: string
  downloadExtension: string
  mimeType: string
}[] => {
  return FORMAT_OPTIONS_BASE.map(option => ({
    value: option.value,
    label: t(`apps.download.${option.labelKey}`),
    extension: option.extension,
    downloadExtension: option.downloadExtension,
    mimeType: option.mimeType,
  }))
}