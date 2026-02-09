/**
 * 内容下载 Hook
 *
 * @description
 * 简化的下载 Hook，仅管理下载状态和格式选择。
 * 菜单的显示/隐藏、定位等由 Radix UI DropdownMenu 自动处理。
 */

import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import type { DownloadFormat } from '../types'
import { FORMAT_OPTIONS_BASE } from '../constants'
import { DownloadApiService } from '../services/downloadApi'
import type { UseDownloadReturn } from '../types'
import {
  downloadTextFile,
  downloadBase64File,
  generateTimestampedFilename,
} from '@/pages/Apps/utils/downloadHelper'
import { showNotification } from '@/utils/notifications'

/**
 * 内容下载 Hook
 * 处理内容下载功能，支持 Markdown、HTML、DOCX 格式
 */
export function useDownload(content: string, title: string): UseDownloadReturn {
  const { t } = useTranslation()
  const [downloadFormat, setDownloadFormat] = useState<DownloadFormat>('markdown')
  const [isDownloading, setIsDownloading] = useState(false)

  /**
   * 选择格式并开始下载
   */
  const selectFormat = useCallback(async (format: DownloadFormat) => {
    if (isDownloading) return

    try {
      setIsDownloading(true)
      setDownloadFormat(format)

      const formatOption = FORMAT_OPTIONS_BASE.find(opt => opt.value === format)
      if (!formatOption) {
        throw new Error(t('apps.errors.invalidFormat'))
      }

      const filename = generateTimestampedFilename(title, formatOption.extension)

      if (format === 'markdown') {
        // Markdown 格式直接下载
        downloadTextFile(content, filename, formatOption.mimeType)
        showNotification(t('apps.download.markdownSuccess'), 'success')
      } else {
        // HTML 和 DOCX 需要调用后端转换
        const convertedContent = await DownloadApiService.convertFormat(content, format, t)
        if (convertedContent) {
          downloadBase64File(convertedContent, filename, formatOption.mimeType)
          const formatLabel = t(`apps.download.${formatOption.labelKey}`)
          showNotification(t('apps.download.formatSuccess', { format: formatLabel }), 'success')
        }
      }
    } catch (error) {
      console.error('[useDownload] 下载内容失败:', error)
      showNotification(t('apps.notifications.downloadFailed'), 'error')
    } finally {
      setIsDownloading(false)
    }
  }, [content, isDownloading, title, t])

  return {
    downloadFormat,
    isDownloading,
    selectFormat,
  }
}