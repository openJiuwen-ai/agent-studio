import React, { useRef, useMemo, useCallback } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { X, Database, ShoppingBag } from 'lucide-react'
import { Tooltip } from '@mui/material'
import AgentIcon from '@/assets/icons/agent.svg?react'
import WorkflowIcon from '@/assets/icons/workflow.svg?react'
import PromptTemplateIcon from '@/assets/icons/promptTemplate.svg?react'
import PromptOptimizeIcon from '@/assets/icons/promptOptimze.svg?react'
import ModelIcon from '@/assets/icons/modelManagement.svg?react'
import PluginIcon from '@/assets/icons/plugin.svg?react'
import SidebarUserSection from './SidebarUserSection'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  isCollapsed: boolean
  onToggleCollapse: () => void
  user?: any
  onLogout?: () => void
}

interface NavigationItem {
  name: string
  href: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
}

interface NavigationSection {
  title: string
  items: NavigationItem[]
}

const SidebarNew: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  isCollapsed,
  onToggleCollapse,
  user,
  onLogout,
}) => {
  const { t } = useTranslation()
  const location = useLocation()
  const navRef = useRef<HTMLDivElement>(null)
  const basePath = '/dashboard'

  const navigationSections: NavigationSection[] = useMemo(
    () => [
      {
        title: 'layout.navigation.section.appDevelopment',
        items: [
          { name: t('layout.navigation.agents'), href: `${basePath}/agents`, icon: AgentIcon },
          { name: t('layout.navigation.workflows'), href: `${basePath}/workflows`, icon: WorkflowIcon },
        ],
      },
      {
        title: 'layout.navigation.section.plugins',
        items: [
          { name: t('layout.navigation.pluginManagement'), href: `${basePath}/plugins`, icon: PluginIcon },
          { name: t('layout.navigation.pluginMarket'), href: `${basePath}/plugins/market`, icon: ShoppingBag },
        ],
      },
      {
        title: 'layout.navigation.section.promptEngineering',
        items: [
          { name: t('layout.navigation.promptTemplates'), href: `${basePath}/prompts`, icon: PromptTemplateIcon },
          { name: t('layout.navigation.promptOptimization'), href: `${basePath}/prompts/optimize`, icon: PromptOptimizeIcon },
        ],
      },
      {
        title: 'layout.navigation.section.modelsAndData',
        items: [
          { name: t('layout.navigation.models'), href: `${basePath}/models`, icon: ModelIcon },
          { name: t('layout.navigation.knowledgeBases'), href: `${basePath}/knowledge-bases`, icon: Database },
        ],
      },
    ],
    [t]
  )

  // 获取所有导航项（用于激活状态判断）
  const allNavigationItems = useMemo(
    () => navigationSections.flatMap(section => section.items),
    [navigationSections]
  )

  // 判断菜单项是否激活
  const isActive = useCallback(
    (href: string): boolean => {
      // 精确匹配
      if (location.pathname === href) return true
      // 前缀匹配（用于子路径）
      if (location.pathname.startsWith(href + '/')) {
        // 检查是否有其他更精确的匹配
        const hasMoreSpecificMatch = allNavigationItems.some(
          item => item.href.length > href.length && location.pathname.startsWith(item.href)
        )
        return !hasMoreSpecificMatch
      }
      return false
    },
    [location.pathname, allNavigationItems]
  )

  // 处理导航项点击（移动端自动关闭侧边栏）
  const handleNavItemClick = useCallback(() => {
    if (window.innerWidth < 1024) {
      onClose()
    }
  }, [onClose])

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && <div className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden" onClick={onClose} />}

      {/* Sidebar */}
      <div
        className={`
        fixed inset-0 left-0 z-50 bg-white
        border-r transition-all duration-200
        lg:translate-x-0 lg:static lg:inset-0 flex flex-col h-screen
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        ${isCollapsed ? 'lg:w-14' : 'lg:w-[190px]'}
      `}
      >
        {/* Logo section */}
        <div className={`flex items-center h-12 ${isCollapsed ? 'px-3 justify-center' : 'px-4 justify-between'} shrink-0`}>
          <div className="flex items-center">
            <div className="flex items-center justify-center">
              <img src="/jiuwen-logo.svg" width={20} height={20} alt="Jiuwen Logo" />
            </div>
            <div className={`overflow-hidden transition-all duration-200 ${isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'}`}>
              <span className="text-[16px] font-[800] leading-5 text-common-text-black whitespace-nowrap ml-2">openJiuwen</span>
            </div>
          </div>
          {/* Mobile close button */}
          <button onClick={onClose} className="lg:hidden p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav ref={navRef} className={`flex-1 ${isCollapsed ? 'px-2' : 'px-3'} overflow-y-auto overflow-x-hidden [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-gray-100 [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-gray-400 flex flex-col min-h-0`}>
          {navigationSections.map((section, sectionIndex) => (
            <div key={section.title}>
              {(sectionIndex > 0 || !isCollapsed) && (
                <div className={`${isCollapsed ? 'mb-1 mt-1' : 'mb-1 mt-3'} h-5 flex items-center`}>
                  {isCollapsed ? (
                    <div className="w-full border-t border-gray-200" />
                  ) : (
                    <div>
                      <span className="text-[12px] font-normal menu-section-title whitespace-nowrap block">{t(section.title)}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Section items */}
              <div className="space-y-0.5">
                {section.items.map(item => (
                  <Tooltip
                    key={item.name}
                    title={item.name}
                    placement="right"
                    enterDelay={300}
                    disableHoverListener={!isCollapsed}
                  >
                    <NavLink
                      to={item.href}
                      className={`
                        group flex items-center font-medium rounded-lg transition-colors duration-200 relative min-h-9 menu-item-hover
                        ${isCollapsed ? 'justify-center px-2 py-1.5 mx-1' : 'px-2 py-2 mx-1'}
                        ${isActive(item.href) ? 'menu-item-active' : 'menu-text'}
                      `}
                      onClick={handleNavItemClick}
                    >
                      <item.icon className="h-4 w-4 flex-shrink-0 flex items-center justify-center" />
                      <div className={`overflow-hidden transition-all duration-200 flex items-center ${isCollapsed ? 'w-0 opacity-0 ml-0' : 'w-auto opacity-100 ml-1.5'}`}>
                        <span className="text-[12px] font-medium whitespace-nowrap leading-normal">{item.name}</span>
                      </div>
                    </NavLink>
                  </Tooltip>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* User Section */}
        {user && onLogout && (
          <SidebarUserSection
            user={user}
            isCollapsed={isCollapsed}
            onLogout={onLogout}
            onToggleCollapse={onToggleCollapse}
          />
        )}
      </div>
    </>
  )
}

export default SidebarNew
