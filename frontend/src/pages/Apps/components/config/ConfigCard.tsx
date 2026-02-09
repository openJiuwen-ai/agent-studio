/**
 * Config Card Component
 * 配置卡片容器组件
 * 用于展示配置项的卡片式布局
 */

import React from 'react'
import { RADIUS_CONTAINER } from '../../constants/styles'

export interface ConfigCardProps {
  /** 卡片图标 */
  icon: React.ReactNode
  /** 卡片标题 */
  title: string
  /** 卡片内容 */
  children: React.ReactNode
  /** 额外的类名 */
  className?: string
}

/**
 * 配置卡片组件
 * 采用 Notion/Linear 风格的卡片设计
 */
export const ConfigCard: React.FC<ConfigCardProps> = ({
  icon,
  title,
  children,
  className = ''
}) => {
  return (
    <div className={`
      bg-white ${RADIUS_CONTAINER} shadow-sm border border-gray-200
      hover:shadow-md transition-shadow duration-200
      overflow-hidden flex flex-col
      ${className}
    `}>
      {/* 卡片头部 */}
      <div className="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-100 rounded-xl flex items-center justify-center text-blue-600 flex-shrink-0">
            {icon}
          </div>
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        </div>
      </div>

      {/* 卡片内容 */}
      <div className="p-6 space-y-6 flex-1 overflow-y-auto">
        {children}
      </div>
    </div>
  )
}

export default ConfigCard
