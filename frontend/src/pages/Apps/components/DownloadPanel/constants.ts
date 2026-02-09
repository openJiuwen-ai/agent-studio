/**
 * 下载格式常量配置
 */

/** 格式选项配置 */
export interface FormatOption {
  value: 'markdown' | 'html' | 'docx'
  labelKey: string
  extension: string
  mimeType: string
}

/** 格式选项原始配置（不含翻译） */
export const FORMAT_OPTIONS_BASE: readonly FormatOption[] = [
  { value: 'markdown', labelKey: 'markdown', extension: '.md', mimeType: 'text/markdown' },
  { value: 'html', labelKey: 'html', extension: '.html', mimeType: 'text/html' },
  { value: 'docx', labelKey: 'wordDocument', extension: '.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
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
  mimeType: string
}[] => {
  return FORMAT_OPTIONS_BASE.map(option => ({
    value: option.value,
    label: t(`apps.download.${option.labelKey}`),
    extension: option.extension,
    mimeType: option.mimeType,
  }))
}