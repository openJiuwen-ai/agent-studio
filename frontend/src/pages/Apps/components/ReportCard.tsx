import React, { memo } from 'react'
import { FileText, ChevronRight, Clock } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { Report } from '../types'
import { formatReportDate, getRelativeTime } from '../utils/formatDate'
import { formatReportTitleForDisplay } from '@/utils/reportUtils'

interface ReportCardProps {
  report: Report
  isActive: boolean
  onClick: () => void
}

/**
 * 报告卡片组件
 * 显示报告预览信息，支持点击展开查看详情
 */
const ReportCard: React.FC<ReportCardProps> = memo(({ report, isActive, onClick }) => {
  const { t, i18n } = useTranslation()

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick()
    }
  }

  // Get formatted date strings
  const relativeTime = getRelativeTime(report.createdAt, t, i18n.language)
  const formattedDate = formatReportDate(report.createdAt, i18n.language)

  return (
    <div
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      aria-label={`查看报告: ${report.title}`}
      className={`
        mt-3 p-4 rounded-xl cursor-pointer transition-all duration-300 ease-out
        flex items-center justify-between gap-4 group relative overflow-hidden
        ${isActive
          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 shadow-xl shadow-blue-600/40 scale-[1.02]'
          : 'bg-gradient-to-br from-indigo-50 via-blue-50 to-cyan-50 border-2 border-indigo-200/60 hover:from-indigo-100 hover:via-blue-100 hover:to-cyan-100 hover:border-indigo-400 hover:shadow-xl hover:shadow-indigo-500/20 hover:scale-[1.01]'
        }
      `}
    >
      {/* 装饰性背景图案 */}
      <div className="absolute inset-0 opacity-30 pointer-events-none">
        <div className={`
          absolute -top-8 -right-8 w-32 h-32 rounded-full blur-2xl transition-colors duration-300
          ${isActive ? 'bg-white/40' : 'bg-indigo-400/20 group-hover:bg-indigo-500/30'}
        `} />
        <div className={`
          absolute -bottom-6 -left-6 w-24 h-24 rounded-full blur-xl transition-colors duration-300
          ${isActive ? 'bg-white/30' : 'bg-cyan-400/20 group-hover:bg-cyan-500/30'}
        `} />
      </div>

      {/* 左侧：图标和内容 */}
      <div className="flex items-center gap-3 flex-1 min-w-0 relative z-10">
        {/* 图标容器 */}
        <div className={`
          flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center
          transition-all duration-300 shadow-md
          ${isActive
            ? 'bg-white/25 backdrop-blur-sm shadow-white/20'
            : 'bg-gradient-to-br from-indigo-500 to-blue-600 shadow-indigo-500/30 group-hover:shadow-lg group-hover:shadow-indigo-500/40 group-hover:scale-110'
          }
        `}>
          <FileText className={`
            w-6 h-6 transition-all duration-300
            ${isActive ? 'text-white' : 'text-white'}
          `} />
        </div>

        {/* 文本内容 */}
        <div className="flex-1 min-w-0">
          {/* 标题 */}
          <div className={`
            text-sm font-semibold truncate transition-colors duration-300
            ${isActive ? 'text-white' : 'text-gray-800'}
          `}>
            {formatReportTitleForDisplay(report.title, t)}
          </div>

          {/* 时间信息 */}
          <div className={`
            flex items-center gap-1.5 mt-1.5 text-xs font-medium transition-colors duration-300
            ${isActive ? 'text-blue-100' : 'text-indigo-600/70'}
          `}>
            <Clock className="w-3 h-3" />
            <span>{relativeTime}</span>
            <span className={`text-gray-400 ${isActive ? '!text-blue-200' : ''}`}>·</span>
            <span className="opacity-80">{formattedDate}</span>
          </div>
        </div>
      </div>

      {/* 右侧：箭头图标 */}
      <div className={`
        flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center
        transition-all duration-300 relative z-10 shadow-sm
        ${isActive
          ? 'bg-white/20 backdrop-blur-sm rotate-90 shadow-white/10'
          : 'bg-white/80 backdrop-blur-sm group-hover:bg-white group-hover:rotate-90 group-hover:shadow-md'
        }
      `}>
        <ChevronRight className={`
          w-4 h-4 transition-colors duration-300
          ${isActive ? 'text-white' : 'text-indigo-500 group-hover:text-indigo-600'}
        `} />
      </div>
    </div>
  )
})

ReportCard.displayName = 'ReportCard'

export default ReportCard
