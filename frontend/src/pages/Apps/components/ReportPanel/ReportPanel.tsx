/**
 * 报告展示面板组件
 *
 * @description
 * 作为组装者组合各个功能模块：
 * - ReportHeader: 标题栏
 * - ReportView: 内容展示
 */

import React from 'react'
import type { Report } from '@/pages/Apps/types'
import { ReportHeader } from './ReportHeader'
import { ReportView } from './ReportView'

interface ReportPanelProps {
  /** 报告数据 */
  report: Report
  /** 关闭回调 */
  onClose: () => void
  /** 自定义类名 */
  className?: string
}

/**
 * 报告展示面板组件
 */
const ReportPanel: React.FC<ReportPanelProps> = ({ report, onClose, className = '' }) => {
  return (
    <div className={`w-full h-full flex flex-col bg-gradient-to-br from-slate-50 to-blue-50/30 ${className}`}>
      {/* 顶部标题栏 */}
      <ReportHeader report={report} onClose={onClose} />

      {/* 内容区域 */}
      <div className="flex-1 px-2 pb-2 overflow-hidden">
        <ReportView report={report} />
      </div>
    </div>
  )
}

ReportPanel.displayName = 'ReportPanel'

export { ReportPanel }
