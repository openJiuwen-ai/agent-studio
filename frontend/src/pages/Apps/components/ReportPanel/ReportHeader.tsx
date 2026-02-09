/**
 * 报告标题栏组件
 *
 * @description
 * 组装各个功能模块，提供统一的标题栏界面
 * - 标题和时间信息展示
 * - 复制功能（ClipboardPanel）
 * - 下载功能（DownloadPanel）
 * - 关闭按钮
 */

import React from 'react'
import { IconButton } from '@test-agentstudio/base-ui'
import { X, FileText, Clock } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { Report } from '@/pages/Apps/types'
import { formatFullDateTime, getAccessibleRelativeTime } from '@/pages/Apps/utils/formatDate'
import { ClipboardButton } from '../ClipboardPanel'
import { DownloadButton } from '../DownloadPanel'

interface ReportHeaderProps {
  /** 报告数据 */
  report: Report
  /** 关闭回调 */
  onClose: () => void
  /** 自定义样式类名 */
  className?: string
}

/**
 * 报告标题栏组件
 */
export const ReportHeader: React.FC<ReportHeaderProps> = ({
  report,
  onClose,
  className = '',
}) => {
  const { t, i18n } = useTranslation()
  // 获取可访问的时间数据
  const { displayText, datetime } = getAccessibleRelativeTime(report.createdAt, t, i18n.language)
  const fullDateTime = formatFullDateTime(report.createdAt, i18n.language)

  return (
    <div className={`flex-shrink-0 flex justify-between items-center border-b border-blue-100/60 bg-white/80 backdrop-blur-sm pb-4 mb-4 px-6 pt-5 shadow-sm ${className}`}>
      {/* 左侧：图标和标题 */}
      <div className="flex items-center gap-2 sm:gap-4 min-w-0">
        {/* 图标容器 */}
        <div className="flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md transition-shadow duration-200 hover:shadow-lg">
          <FileText className="w-5 h-5 sm:w-6 sm:h-6 text-white" aria-hidden="true" />
        </div>

        {/* 标题和时间信息 */}
        <div className="min-w-0 flex-1">
          <h2 className="text-base sm:text-lg font-bold text-gray-900 leading-tight truncate">
            {report.title}
          </h2>
          <div className="flex items-center gap-2 sm:gap-3 mt-1 text-xs">
            {/* 相对时间 - 使用语义化的 time 元素 */}
            <div className="group relative flex items-center gap-1.5 px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full font-medium cursor-help">
              <Clock className="w-3 h-3 flex-shrink-0" aria-hidden="true" />
              <time
                dateTime={datetime}
                aria-label={`${t('apps.report.createdAt')}: ${fullDateTime}`}
                className="truncate"
              >
                {displayText}
              </time>
              {/* Tooltip */}
              <div className="absolute -bottom-8 left-0 hidden group-hover:block bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-50">
                {fullDateTime}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 右侧：操作按钮 */}
      <div
        className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0"
        role="toolbar"
        aria-label={t('apps.report.toolbar')}
      >
        {/* 复制按钮 */}
        <ClipboardButton
          content={report.response_content}
        />

        {/* 下载按钮 */}
        <DownloadButton
          content={report.response_content}
          title={report.title}
        />

        {/* 关闭按钮 */}
        <IconButton
          icon={<X className="w-5 h-5" />}
          tooltip={t('apps.report.closePanel')}
          onClick={onClose}
          aria-label={t('apps.report.closeReportPanel')}
        />
      </div>
    </div>
  )
}
