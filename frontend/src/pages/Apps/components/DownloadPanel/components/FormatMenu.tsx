/**
 * 格式选择菜单组件（使用 Radix UI DropdownMenu）
 *
 * @description
 * 基于 Radix UI 的下拉菜单组件，提供：
 * - 自动定位和边界检测
 * - 完整的键盘导航支持
 * - 自动点击外部关闭
 * - 内置 Portal 渲染
 * - 完整的 ARIA 无障碍支持
 */

import React from 'react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Download, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { getFormatOptions } from '../constants'
import type { DownloadFormat } from '../types'

interface FormatMenuProps {
  /** 格式选择回调 */
  onSelect: (format: DownloadFormat) => Promise<void>
  /** 是否正在下载（禁用菜单选项） */
  isDownloading?: boolean
  /** 是否禁用整个菜单 */
  disabled?: boolean
}

/**
 * 格式图标映射
 */
const FORMAT_ICONS: Record<DownloadFormat, React.ReactNode> = {
  markdown: <span className="text-sm font-mono font-bold">M↓</span>,
  html: <span className="text-sm font-bold">&lt;/&gt;</span>,
  docx: <span className="text-sm font-bold">W</span>,
}

/**
 * 格式选择菜单内容组件（仅包含 DropdownMenu.Portal 和 Content）
 *
 * @description
 * 这个组件只包含菜单的 Portal 和 Content 部分，
 * DropdownMenu.Root 和 Trigger 应该由调用方（通常是 DownloadButton）提供。
 *
 * @example
 * ```tsx
 * <DropdownMenu.Root modal={false}>
 *   <DropdownMenu.Trigger asChild>
 *     <IconButton icon={<Download />} />
 *   </DropdownMenu.Trigger>
 *   <FormatMenu
 *     onSelect={async (format) => await download(format)}
 *     isDownloading={false}
 *   />
 * </DropdownMenu.Root>
 * ```
 */
export const FormatMenu: React.FC<FormatMenuProps> = ({
  onSelect,
  isDownloading = false,
  disabled = false,
}) => {
  const { t } = useTranslation()
  const formatOptions = getFormatOptions(t)

  const handleSelect = async (format: DownloadFormat) => {
    if (!isDownloading) {
      await onSelect(format)
    }
  }

  return (
    <DropdownMenu.Portal>
      <DropdownMenu.Content
        align="end"
        sideOffset={8}
        className="z-[9999] w-48 min-w-[12rem] bg-white/95 backdrop-blur-md rounded-xl shadow-2xl border border-gray-100/50 overflow-hidden"
        side="bottom"
      >
        {/* 标题区域 */}
        <div className="px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 border-b border-blue-600">
          <div className="flex items-center gap-2">
            {isDownloading ? (
              <Loader2 className="w-4 h-4 text-white animate-spin" aria-hidden="true" />
            ) : (
              <Download className="w-4 h-4 text-white" aria-hidden="true" />
            )}
            <span className="text-sm font-bold text-white">
              {isDownloading ? t('apps.download.downloading') : t('apps.download.selectFormat')}
            </span>
          </div>
        </div>

        {/* 选项列表 */}
        <DropdownMenu.Group className="py-1">
          {formatOptions.map((option) => {
            const isOptionDisabled = isDownloading || disabled

            return (
              <DropdownMenu.Item
                key={option.value}
                disabled={isOptionDisabled}
                onSelect={() => handleSelect(option.value)}
                className={`
                  group relative flex items-center justify-between
                  px-4 py-3 text-sm transition-all duration-200
                  cursor-pointer outline-none
                  data-[highlighted]:bg-blue-500
                  data-[highlighted]:text-white
                  ${isOptionDisabled
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-gray-700 hover:bg-blue-500 hover:text-white'
                  }
                `}
              >
                <div className="flex items-center gap-3 flex-1">
                  {/* 格式图标 */}
                  <span
                    className={`
                      transition-colors duration-200
                      ${
                        isOptionDisabled
                          ? 'text-gray-400'
                          : 'text-blue-500 group-hover:text-white'
                      }
                    `}
                    aria-hidden="true"
                  >
                    {FORMAT_ICONS[option.value]}
                  </span>

                  {/* 格式名称 */}
                  <span className="font-medium">{option.label}</span>
                </div>

                {/* 扩展名标签 */}
                <span
                  className={`
                    text-xs px-2 py-0.5 rounded-full font-mono transition-colors duration-200
                    ${isOptionDisabled
                      ? 'bg-gray-100 text-gray-400'
                      : 'bg-gray-100 text-gray-500 group-hover:bg-white/30 group-hover:text-white'
                    }
                  `}
                  aria-hidden="true"
                >
                  {option.extension}
                </span>
              </DropdownMenu.Item>
            )
          })}
        </DropdownMenu.Group>

        {/* 箭头 */}
        <DropdownMenu.Arrow className="fill-white" />
      </DropdownMenu.Content>
    </DropdownMenu.Portal>
  )
}