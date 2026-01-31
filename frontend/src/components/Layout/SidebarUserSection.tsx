import React, { useState, useRef, useCallback, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronLeft, ChevronRight, Globe, LogOut, ArrowLeft, ArrowRight } from 'lucide-react'
import { Popover, Tooltip } from '@mui/material'
import { useLogout } from '@test-agentstudio/api-client'
import { resolveAvatar } from '../../utils/avatar'
import { useUIStore } from '../../stores/useUIStore'

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

  const logoutMutation = useLogout({ logout: onLogout || (() => {}) })

  const isUCDNew = useUIStore(state => state.isNewDashboard)
  const toggleDashboardVersion = useUIStore(state => state.toggleDashboardVersion)

  const handleVersionSwitch = useCallback(() => {
    toggleDashboardVersion()
  }, [toggleDashboardVersion])

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
      {/* Version switch button - above user section */}
      <Tooltip title={isUCDNew ? t('layout.header.switchToOldVersion') : t('layout.header.switchToNewVersion')} placement="right">
        <button
          onClick={handleVersionSwitch}
          className={`${isCollapsed ? 'justify-center px-2 py-2 mx-1 mb-1' : 'w-full py-2 mb-2'} group flex items-center justify-center gap-2 rounded-lg transition-all duration-200 ${
            isUCDNew
              ? 'bg-gray-100/50 hover:bg-gray-200/50 text-gray-600'
              : 'bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 text-gray-700 border border-blue-200/50'
          }`}
        >
          {isUCDNew ? (
            <>
              <ArrowLeft className="w-4 h-4" />
              {!isCollapsed && <span className="text-[13px] font-semibold">{t('layout.header.switchToOldVersion')}</span>}
            </>
          ) : (
            <>
              {!isCollapsed && <span className="text-[13px] font-semibold">{t('layout.header.switchToNewVersion')}</span>}
              <ArrowRight className="w-4 h-4" />
              {!isCollapsed && (
                <span className="ml-auto px-2 py-0.5 text-[10px] font-bold bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-md shadow-sm">
                  {t('layout.header.beta')}
                </span>
              )}
            </>
          )}
        </button>
      </Tooltip>

      {/* User section - original layout */}
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
            className: 'bg-white rounded-lg border border-gray-200 overflow-hidden min-w-[150px]',
            sx: {
              mt: isCollapsed ? 0 : -0.5,
              ml: isCollapsed ? 0.5 : 0,
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            },
          },
        }}
      >
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
