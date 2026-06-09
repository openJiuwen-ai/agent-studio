/**
 * 内容下载 Hook
 */

import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { DownloadFormat, UseDownloadReturn } from '../types'
import { FORMAT_OPTIONS_BASE } from '../constants'
import { DownloadApiService } from '../services/downloadApi'
import type { ChartMessage, DeepSearchResult, InferMessage } from '@/pages/Apps/types'
import {
  downloadBase64File,
  downloadMarkdownBundle,
  generateTimestampedFilename,
} from '@/pages/Apps/utils/downloadHelper'
import { showNotification } from '@/utils/notifications'

interface UseDownloadOptions {
  rawContent?: string
  chartMessages?: ChartMessage[] | null
  inferMessages?: InferMessage[] | null
  finalResult?: DeepSearchResult
}

export function useDownload(
  content: string,
  title: string,
  options?: UseDownloadOptions
): UseDownloadReturn {
  const { t } = useTranslation()
  const [downloadFormat, setDownloadFormat] = useState<DownloadFormat>('markdown')
  const [isDownloading, setIsDownloading] = useState(false)

  const selectFormat = useCallback(async (format: DownloadFormat) => {
    if (isDownloading) return

    try {
      setIsDownloading(true)
      setDownloadFormat(format)

      const formatOption = FORMAT_OPTIONS_BASE.find(opt => opt.value === format)
      if (!formatOption) {
        throw new Error(t('apps.errors.invalidFormat'))
      }

      const baseFilename = generateTimestampedFilename(title, '')
      const filename = `${baseFilename}${formatOption.downloadExtension}`

      if (format === 'markdown') {
        await downloadMarkdownBundle({
          content,
          markdownFilename: `${baseFilename}.md`,
          archiveFilename: `${baseFilename}.zip`,
          rawContent: options?.rawContent,
          chartMessages: options?.chartMessages,
          inferMessages: options?.inferMessages,
        })
        showNotification(t('apps.download.markdownSuccess'), 'success')
        return
      }

      if (!options?.finalResult) {
        showNotification(t('apps.errors.reportConvertFailed'), 'error')
        return
      }

      const convertedContent = await DownloadApiService.convertFormat(options.finalResult, format, t)
      if (convertedContent) {
        downloadBase64File(convertedContent, filename, formatOption.mimeType)
        const formatLabel = t(`apps.download.${formatOption.labelKey}`)
        showNotification(t('apps.download.formatSuccess', { format: formatLabel }), 'success')
      }
    } catch (error) {
      console.error('[useDownload] 下载内容失败:', error)
      showNotification(t('apps.notifications.downloadFailed'), 'error')
    } finally {
      setIsDownloading(false)
    }
  }, [content, isDownloading, options?.chartMessages, options?.finalResult, options?.inferMessages, options?.rawContent, t, title])

  return {
    downloadFormat,
    isDownloading,
    selectFormat,
  }
}
