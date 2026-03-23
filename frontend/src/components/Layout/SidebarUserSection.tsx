import React, { useState, useRef, useCallback, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronLeft, ChevronRight, Globe, LogOut, Sun, Moon, Monitor } from 'lucide-react'
import { Popover } from '@mui/material'
import { useLogout } from '@test-agentstudio/api-client'
import { resolveAvatar } from '../../utils/avatar'
import { useTheme } from '@/stores/useUIStore'
interface SidebarUserSectionProps {
  user: any
  isCollapsed: boolean
  onLogout: () => void
  onToggleCollapse: () => void
}

const SidebarUserSection: React.FC<SidebarUserSectionProps> = ({ user, isCollapsed, onLogout, onToggleCollapse }) => {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const userButtonRef = useRef<HTMLButtonElement>(null)
  const [theme, setTheme] = useTheme()
  const showThemeSwitcher = false

  const logoutMutation = useLogout({ logout: onLogout || (() => {}) })

  const handleLanguageChange = useCallback(
    (language: string) => {
      i18n.changeLanguage(language)
      setIsUserMenuOpen(false)
    },
    [i18n],
  )

  const handleLogout = useCallback(async () => {
    try {
      await logoutMutation.mutateAsync()
      onLogout?.()
    } catch (error) {
      console.error('登出失败:', error)
      onLogout?.()
    }
  }, [logoutMutation, onLogout])

  const handleThemeChange = useCallback((value: 'light' | 'dark' | 'auto') => {
    setTheme(value)
    setIsUserMenuOpen(false)
  }, [setTheme])

  const handleToggleMenu = useCallback(() => {
    setIsUserMenuOpen(prev => !prev)
  }, [])

  const handleCloseMenu = useCallback(() => {
    setIsUserMenuOpen(false)
  }, [])

  // 计算头像 URL
  const avatarUrl = useMemo(() => resolveAvatar(user?.avatar, user?.username || user?.email, 128), [user?.avatar, user?.username, user?.email])

  // 计算 Popover 的定位配置
  const popoverAnchorOrigin = useMemo(
    () => ({
      vertical: (isCollapsed ? 'bottom' : 'top') as 'top' | 'bottom',
      horizontal: (isCollapsed ? 'right' : 'left') as 'left' | 'right',
    }),
    [isCollapsed],
  )

  const popoverTransformOrigin = useMemo(
    () => ({
      vertical: 'bottom' as const,
      horizontal: (isCollapsed ? 'left' : 'left') as 'left' | 'right',
    }),
    [isCollapsed],
  )

  return (
    <div className={`shrink-0 pb-3 ${isCollapsed ? 'flex flex-col items-center space-y-0' : 'px-3'}`}>
      {/* User section */}
      <div className={`flex items-center ${isCollapsed ? 'flex-col space-y-0' : 'gap-2'}`}>
        {/* User avatar button */}
        <button
          ref={userButtonRef}
          onClick={handleToggleMenu}
          className={`${isCollapsed ? 'justify-center px-2 py-2 mx-1' : 'flex-1 px-2 py-2'} flex items-center rounded-lg transition-colors duration-200 menu-text menu-item-hover`}
        >
          <img className="rounded-full flex-shrink-0" src={avatarUrl} alt={user?.username} width={20} height={20} />
          {!isCollapsed && <span className="ml-1.5 text-[12px] font-medium truncate">{user?.username}</span>}
        </button>

        {/* Collapse/Expand Button */}
        <button
          onClick={onToggleCollapse}
          className={`flex items-center justify-center font-medium rounded-lg transition-colors duration-200 shrink-0 menu-text menu-item-hover ${
            isCollapsed ? 'justify-center px-2 py-2 mx-1' : 'px-2 py-2'
          }`}
        >
          {isCollapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Dropdown menu */}
      <Popover
        open={isUserMenuOpen}
        onClose={handleCloseMenu}
        anchorEl={userButtonRef.current}
        anchorOrigin={popoverAnchorOrigin}
        transformOrigin={popoverTransformOrigin}
        slotProps={{
          paper: {
            className: 'bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden min-w-[150px]',
            sx: {
              mt: isCollapsed ? 0 : -0.5,
              ml: isCollapsed ? 0.5 : 0,
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            },
          },
        }}
      >
        {/* Theme section */}
        {showThemeSwitcher && (
          <div className="px-2 pt-1 pb-2">
            <div className="text-[10px] menu-section-title px-1 pb-1">{t('layout.header.theme')}</div>
            <div className="space-y-0.5">
              <button
                onClick={() => handleThemeChange('light')}
                className={`w-full flex items-center px-2 py-1 rounded text-[12px] transition-colors menu-item-hover ${
                  theme === 'light' ? 'menu-item-active' : 'menu-text'
                }`}
              >
                <Sun className="w-3 h-3 mr-1.5" />
                <span>{t('layout.header.themeLight')}</span>
              </button>
              <button
                onClick={() => handleThemeChange('dark')}
                className={`w-full flex items-center px-2 py-1 rounded text-[12px] transition-colors menu-item-hover ${
                  theme === 'dark' ? 'menu-item-active' : 'menu-text'
                }`}
              >
                <Moon className="w-3 h-3 mr-1.5" />
                <span>{t('layout.header.themeDark')}</span>
              </button>
              <button
                onClick={() => handleThemeChange('auto')}
                className={`w-full flex items-center px-2 py-1 rounded text-[12px] transition-colors menu-item-hover ${
                  theme === 'auto' ? 'menu-item-active' : 'menu-text'
                }`}
              >
                <Monitor className="w-3 h-3 mr-1.5" />
                <span>{t('layout.header.themeAuto')}</span>
              </button>
            </div>
          </div>
        )}

        {/* Language section */}
        <div className="px-2 pt-1 pb-2">
          <div className="text-[10px] menu-section-title px-1 pb-1">{t('layout.header.language')}</div>
          <div className="space-y-0.5">
            <button
              onClick={() => handleLanguageChange('zh-CN')}
              className={`w-full flex items-center px-2 py-1 rounded text-[12px] transition-colors menu-item-hover ${
                i18n.language === 'zh-CN' ? 'menu-item-active' : 'menu-text'
              }`}
            >
              <Globe className="w-3 h-3 mr-1.5" />
              <span>中文</span>
            </button>
            <button
              onClick={() => handleLanguageChange('en-US')}
              className={`w-full flex items-center px-2 py-1 rounded text-[12px] transition-colors menu-item-hover ${
                i18n.language === 'en-US' ? 'menu-item-active' : 'menu-text'
              }`}
            >
              <Globe className="w-3 h-3 mr-1.5" />
              <span>English</span>
            </button>
          </div>
        </div>

        {/* Actions section */}
        <div className="px-2 py-1 border-t border-gray-100">
          <button onClick={handleLogout} className="w-full flex items-center px-2 py-1 rounded text-[12px] menu-text menu-item-hover transition-colors">
            <LogOut className="w-3 h-3 mr-1.5" />
            <span>{t('layout.header.switchUser')}</span>
          </button>
        </div>
      </Popover>
    </div>
  )
}

export default SidebarUserSection
