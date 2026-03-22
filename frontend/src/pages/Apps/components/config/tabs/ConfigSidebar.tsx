/**
 * Config Sidebar Component
 * 配置左侧菜单导航组件
 * Tab 标签页式菜单，支持徽章提示和状态指示
 * 支持响应式布局：桌面端左侧菜单，移动端顶部水平菜单
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
import { ConfigTabMeta, ConfigTabId } from '../ConfigRegistry'
import { RADIUS_BUTTON } from '../../../constants/styles'

/**
 * 根据 tab ID 获取翻译键
 */
function getTabLabelKey(tabId: ConfigTabId): string {
  const keyMap: Record<ConfigTabId, string> = {
    general: 'apps.config.tabs.general',
    search: 'apps.config.tabs.search',
    template: 'apps.config.tabs.template',
    model: 'apps.config.tabs.model'
  }
  return keyMap[tabId] || tabId
}

export interface ConfigSidebarProps {
  /** 配置标签列表 */
  tabs: ConfigTabMeta[]
  /** 当前激活的标签ID */
  activeTab: ConfigTabId
  /** 标签切换回调 */
  onTabChange: (tabId: ConfigTabId) => void
  /** 额外的类名 */
  className?: string
}

/**
 * 配置左侧菜单组件
 * 支持响应式布局：
 * - Desktop (≥768px): 左侧垂直菜单，宽度 240px
 * - Mobile (<768px): 顶部水平菜单，自动换行
 */
export const ConfigSidebar: React.FC<ConfigSidebarProps> = ({
  tabs,
  activeTab,
  onTabChange,
  className = ''
}) => {
  const { t } = useTranslation()
  return (
    <div className={`
      lg:w-60 lg:min-w-60 lg:border-r lg:border-gray-200 lg:bg-gray-50
      w-full border-b border-gray-200 bg-white
      flex flex-col
      ${className}
    `}>
      {/* 菜单列表 */}
      <nav className={`
        overflow-y-auto p-3
        lg:flex-1 lg:space-y-1
        flex flex-row lg:flex-col gap-2 lg:gap-0 overflow-x-auto
      `}>
        {tabs.map(tab => {
          const isActive = activeTab === tab.id
          const label = t(getTabLabelKey(tab.id))

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                flex items-center gap-2 lg:gap-3 px-3 lg:px-4 py-2 lg:py-3
                ${RADIUS_BUTTON}
                text-sm font-medium
                transition-all duration-200
                text-left
                group whitespace-nowrap flex-shrink-0
                ${isActive
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-700 hover:bg-gray-50 lg:hover:bg-white lg:hover:shadow-sm'
                }
              `}
              aria-selected={isActive}
              role="tab"
            >
              {/* 图标 */}
              <div className={`flex-shrink-0 ${isActive ? 'text-blue-600' : 'text-gray-500 group-hover:text-gray-600'}`}>
                {tab.icon}
              </div>

              {/* 标签文字 */}
              <span className={`truncate ${isActive ? 'font-semibold' : ''}`}>{label}</span>

              {/* 徽章 */}
              {tab.badge && tab.badgeText && (
                <span className={`
                  px-2 py-0.5 text-xs rounded-full font-medium flex-shrink-0
                  ${isActive
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-red-100 text-red-600'
                  }
                `}>
                  {tab.badgeText}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      {/* 底部装饰线（仅桌面端显示） */}
      <div className="hidden lg:block h-px bg-gray-200" />
    </div>
  )
}

export default ConfigSidebar
