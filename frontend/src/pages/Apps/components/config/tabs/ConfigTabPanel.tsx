/**
 * Config Tab Panel Component
 * 配置右侧内容面板容器组件
 * 负责渲染当前激活的标签内容
 * 支持淡入动画和响应式布局
 */

import React from 'react'
import { ConfigTabMeta } from '../ConfigRegistry'

export interface ConfigTabPanelProps {
  /** 当前激活的标签元数据 */
  activeTab: ConfigTabMeta
  /** 传递给标签组件的props - 使用 any 以支持不同标签组件的不同 props 类型 */
  tabProps: any
  /** 额外的类名 */
  className?: string
}

/**
 * 配置右侧内容面板组件
 */
export const ConfigTabPanel: React.FC<ConfigTabPanelProps> = ({
  activeTab,
  tabProps,
  className = ''
}) => {
  const Component = activeTab.component

  return (
    <div className={`
      flex-1 overflow-y-auto bg-white
      ${className}
    `}>
      {/* 内容区域 - 添加淡入动画 */}
      <div className="p-4 lg:p-6 xl:p-8 animate-fade-in">
        {/* 标签内容组件 */}
        <Component {...tabProps} />
      </div>
    </div>
  )
}

export default ConfigTabPanel
