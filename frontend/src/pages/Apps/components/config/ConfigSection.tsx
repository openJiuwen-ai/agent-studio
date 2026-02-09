/**
 * Config Section Component
 * 配置分组组件
 * 用于将配置项按功能分组展示
 */

import React from 'react'

export interface ConfigSectionProps {
  /** 分组标题 */
  title: string
  /** 分组内容 */
  children: React.ReactNode
  /** 额外的类名 */
  className?: string
  /** 右侧操作按钮（可选） */
  action?: React.ReactNode
}

/**
 * 配置分组组件
 */
export const ConfigSection: React.FC<ConfigSectionProps> = ({
  title,
  children,
  className = '',
  action
}) => {
  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-900">
          {title}
        </h4>
        {action && <div className="flex items-center">{action}</div>}
      </div>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  )
}

export default ConfigSection
