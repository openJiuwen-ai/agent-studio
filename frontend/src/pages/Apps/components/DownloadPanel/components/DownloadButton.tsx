/**
 * 下载按钮组件
 *
 * @description
 * 带格式选择功能的下载按钮组件
 * - 点击打开格式选择菜单
 * - 支持多种下载格式
 * - 加载状态显示
 * - 使用 Radix UI DropdownMenu 自动处理菜单交互
 */

import React from 'react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Download, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { IconButton } from '@test-agentstudio/base-ui'
import { useDownload } from '../hooks'
import { FormatMenu } from './FormatMenu'

/**
 * 下载按钮组件属性
 */
export interface DownloadButtonProps {
  /** 要下载的内容 */
  content: string
  /** 文件标题（用于生成文件名） */
  title: string
  /** 自定义样式类名 */
  className?: string
}

/**
 * 下载按钮组件
 *
 * @example
 * ```tsx
 * <DownloadButton
 *   content={markdownContent}
 *   title="研究报告"
 * />
 * ```
 */
export const DownloadButton: React.FC<DownloadButtonProps> = ({
  content,
  title,
  className = '',
}) => {
  const { t } = useTranslation()
  const download = useDownload(content, title)

  return (
    <DropdownMenu.Root modal={false}>
      {/* 触发按钮 - 使用 asChild 将 Trigger 的行为合并到 IconButton */}
      <DropdownMenu.Trigger asChild>
        <IconButton
          icon={
            download.isDownloading ? (
              // 使用 Loader2 图标（内置旋转动画）
              <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
            ) : (
              <Download className="w-5 h-5" aria-hidden="true" />
            )
          }
          tooltip={download.isDownloading ? t('apps.download.downloading') : t('apps.download.downloadReport')}
          disabled={download.isDownloading}
          aria-label={download.isDownloading ? t('apps.download.downloadingReport') : t('apps.download.downloadReport')}
          aria-busy={download.isDownloading}
          className={className}
        />
      </DropdownMenu.Trigger>

      {/* 格式选择菜单内容 */}
      <FormatMenu
        onSelect={download.selectFormat}
        isDownloading={download.isDownloading}
      />
    </DropdownMenu.Root>
  )
}