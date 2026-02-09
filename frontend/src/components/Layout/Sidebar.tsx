import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { X, ChevronDown, Lock, Unlock, MessageSquare, Layers, Database, Brain } from 'lucide-react'
import DashboardIcon from '@/assets/icons/dashboard.svg?react'
import AgentIcon from '@/assets/icons/agent.svg?react'
import WorkflowIcon from '@/assets/icons/workflow.svg?react'
import PromptTemplateIcon from '@/assets/icons/promptTemplate.svg?react'
import PromptOptimizeIcon from '@/assets/icons/promptOptimze.svg?react'
import ModelIcon from '@/assets/icons/modelManagement.svg?react'
import PluginIcon from '@/assets/icons/plugin.svg?react'
import packageJson from '@/../package.json'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  isCollapsed: boolean
  onToggleCollapse: () => void
  onMouseLeave?: () => void
  onMouseEnter?: () => void
  isLocked?: boolean
}

interface NavigationItem {
  name: string
  href?: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  children?: NavigationItem[]
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, isCollapsed, onToggleCollapse, onMouseLeave, onMouseEnter, isLocked = false }) => {
  const { t } = useTranslation()
  const location = useLocation()
  const [expandedItems, setExpandedItems] = useState<string[]>([])

  const navigation: NavigationItem[] = [
    { name: t('layout.navigation.dashboard'), href: '/dashboard', icon: DashboardIcon },
    { name: t('layout.navigation.apps'), href: '/dashboard/apps', icon: Layers },
    { name: t('layout.navigation.agents'), href: '/dashboard/agents', icon: AgentIcon },
    { name: t('layout.navigation.workflows'), href: '/dashboard/workflows', icon: WorkflowIcon },
    {
      name: t('layout.navigation.promptManagement'),
      icon: MessageSquare,
      children: [
        { name: t('layout.navigation.promptTemplates'), href: '/dashboard/prompts', icon: PromptTemplateIcon },
        { name: t('layout.navigation.promptOptimization'), href: '/dashboard/prompts/optimize', icon: PromptOptimizeIcon },
      ],
    },
    { name: t('layout.navigation.models'), href: '/dashboard/models', icon: ModelIcon },
    { name: t('layout.navigation.knowledgeBases'), href: '/dashboard/knowledge-bases', icon: Database },
    { name: t('layout.navigation.memoryBase'), href: '/dashboard/memory-bases', icon: Brain },
    { name: t('layout.navigation.plugins'), href: '/dashboard/plugins', icon: PluginIcon },
  ]

  const toggleExpanded = (itemName: string) => {
    setExpandedItems(prev => (prev.includes(itemName) ? prev.filter(name => name !== itemName) : [...prev, itemName]))
  }

  const isChildActive = (item: NavigationItem): boolean => {
    if (item.children) {
      return item.children.some(child => child.href && (location.pathname === child.href || location.pathname.startsWith(child.href)))
    }
    return false
  }

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && <div className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden" onClick={onClose} />}

      {/* Sidebar */}
      <div
        className={`
        fixed inset-0 left-0 z-50 bg-white
        shadow-2xl border-r transform transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]
        lg:translate-x-0 lg:static lg:inset-0 flex flex-col h-screen
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        ${isCollapsed ? 'lg:w-16' : 'lg:w-65'}
      `}
        onMouseLeave={onMouseLeave}
        onMouseEnter={onMouseEnter}
        style={{ cursor: isCollapsed && !isOpen ? 'pointer' : 'default' }}
      >
        <div
          className={`flex items-center justify-between h-16 transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] ${isCollapsed ? 'px-4' : 'px-6'} shrink-0`}
        >
          <div className={`flex items-center space-x-2 transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]`}>
            <div className="w-8 h-8 flex items-center justify-center">
              <img src="/jiuwen-logo.svg" width={32} height={32} alt="Jiuwen Logo" />
            </div>
            <div
              className={`overflow-hidden transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] ${isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'}`}
            >
              <span className="text-xl font-[600] text-[#262626] whitespace-nowrap">openJiuwen</span>
            </div>
          </div>
          {/* Mobile close button only */}
          <button onClick={onClose} className="lg:hidden p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav
          className={`flex-1 py-6 space-y-1 transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] ${isCollapsed ? 'px-2' : 'px-4'} overflow-y-auto overflow-x-hidden [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-gray-100 [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-gray-400 flex flex-col min-h-0`}
        >
          {navigation.map(item => {
            const isActive =
              (item.href && (location.pathname === item.href || (item.href !== '/dashboard' && location.pathname.startsWith(item.href)))) || isChildActive(item)
            const isExpanded = expandedItems.includes(item.name)
            const hasChildren = item.children && item.children.length > 0

            return (
              <React.Fragment key={item.name}>
                <NavLink
                  to={item.href || '#'}
                  className={`
                    group flex items-center font-medium rounded-xl transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]
                    ${isCollapsed ? 'justify-center px-2 py-3 mx-2' : 'px-4 py-3 mx-2'}
                    ${
                      isActive
                        ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-sm shadow-blue-500/25'
                        : 'text-gray-700 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 hover:text-blue-700 hover:shadow-sm'
                    }
                  `}
                  onClick={e => {
                    // 在移动端点击导航项后关闭侧边栏
                    if (window.innerWidth < 1024) {
                      onClose()
                    }
                    // 如果有子项，阻止默认导航行为并切换展开状态
                    if (hasChildren) {
                      e.preventDefault()
                      toggleExpanded(item.name)
                    }
                  }}
                  title={isCollapsed ? item.name : undefined}
                >
                  <item.icon
                    className={`
                      transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]
                      h-5 w-5
                      ${isActive ? 'text-white' : 'text-gray-500 group-hover:text-blue-600'}
                      ${isActive ? 'scale-110' : 'group-hover:scale-105'}
                    `}
                  />
                  <div
                    className={`
                    overflow-hidden transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]
                    ${isCollapsed ? 'w-0 opacity-0 ml-0' : 'w-auto opacity-100 ml-3'}
                    flex items-center justify-between flex-1
                  `}
                  >
                    <span className="text-sm whitespace-nowrap">{item.name}</span>
                    {hasChildren && (
                      <ChevronDown
                        className={`
                          h-4 w-4 transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]
                          ${isExpanded ? 'rotate-180' : ''}
                        `}
                      />
                    )}
                  </div>
                </NavLink>

                {/* 渲染子菜单 */}
                {hasChildren && !isCollapsed && isExpanded && (
                  <div className="pl-10 pr-2 py-1 space-y-1 border-l-2 border-blue-100 ml-3 animate-fadeIn">
                    {item.children?.map(child => {
                      // 判断子菜单项是否激活：精确匹配或确保不是其他子菜单项的前缀
                      const isChildActive =
                        child.href &&
                        (() => {
                          // 先检查精确匹配
                          if (location.pathname === child.href) {
                            return true
                          }
                          // 再检查是否是子路径，但要排除其他子菜单项的路径
                          if (location.pathname.startsWith(child.href + '/')) {
                            // 获取所有其他子菜单项的href
                            const otherChildHrefs = item.children?.filter(c => c.href && c.href !== child.href).map(c => c.href!)
                            // 检查当前路径是否匹配其他子菜单项的路径
                            const matchesOtherChild = otherChildHrefs?.some(href => location.pathname === href || location.pathname.startsWith(href + '/'))
                            // 只有不匹配其他子菜单项时才激活
                            return !matchesOtherChild
                          }
                          return false
                        })()
                      return (
                        <NavLink
                          key={child.name}
                          to={child.href || '#'}
                          className={`
                            flex items-center w-full text-sm font-medium rounded-lg px-3 py-2 transition-all duration-300
                            ${isChildActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-blue-50/50 hover:text-blue-600'}
                          `}
                          onClick={e => {
                            if (window.innerWidth < 1024) {
                              onClose()
                            }
                            // 如果没有href，阻止默认行为
                            if (!child.href) {
                              e.preventDefault()
                            }
                          }}
                        >
                          <child.icon className="h-4 w-4 mr-2" />
                          <span>{child.name}</span>
                        </NavLink>
                      )
                    })}
                  </div>
                )}
              </React.Fragment>
            )
          })}
        </nav>

        {/* Footer */}
        <div
          className={`border-t border-blue-200/50 bg-gradient-to-r from-blue-50/30 to-indigo-50/20 transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] ${isCollapsed ? 'px-2 py-4' : 'px-4 py-4'} shrink-0`}
        >
          <div
            className={`
            overflow-hidden transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]
            ${isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'}
            ${isCollapsed ? 'flex justify-center' : 'flex justify-start'}
          `}
          >
            <span className={`whitespace-nowrap ${isCollapsed ? 'text-blue-600 font-medium' : 'text-gray-500 text-xs'}`}>
              openJiuwen v{packageJson.version} ({t('layout.sidebar.version')})
            </span>
          </div>
        </div>

        {/* Collapse/Expand Button - Always in Bottom Right Corner */}
        <div className="absolute bottom-4 right-4">
          <button
            onClick={onToggleCollapse}
            className={`
                group flex items-center justify-center rounded-lg transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]
                w-10 h-10
                bg-white hover:bg-gray-50
                border border-gray-200 hover:border-gray-300
                text-gray-600 hover:text-gray-800
                shadow-sm hover:shadow-sm
                transform hover:scale-105 active:scale-95
              `}
            title={isCollapsed ? t('layout.sidebar.expand') : t('layout.sidebar.collapse')}
          >
            {isLocked ? (
              <Lock className="w-6 h-6 transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)] group-hover:scale-110" />
            ) : (
              <Unlock className="w-6 h-6 transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)] group-hover:scale-110" />
            )}
          </button>
        </div>
      </div>
    </>
  )
}

export default Sidebar
