import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../../stores/useAuthStore'
import { Menu, ChevronDown, Users } from 'lucide-react'
import { useLogout } from '@test-agentstudio/api-client'
import { resolveAvatar } from '../../utils/avatar'
import LanguageDropdown from '../Common/LanguageDropdown'
import { ENV_CONFIG } from '@/config/environment.ts'
import { getLoginPagePath } from '@/Common/LoginPage.ts'

interface HeaderProps {
  user: any
  onMenuClick: () => void
}

const Header: React.FC<HeaderProps> = ({ user, onMenuClick }) => {
  const { t } = useTranslation()
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  // const notificationsRef = useRef<HTMLDivElement>(null)
  const { logout } = useAuthStore()
  const navigate = useNavigate()

  const enable_pwd = ENV_CONFIG.VITE_ENABLE_NEW_AUTH

  // 使用logout hook，传递认证状态管理器
  const logoutMutation = useLogout({ logout })

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false)
      }
      // if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
      //   setIsNotificationsOpen(false)
      // }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])


  const handleSwitchUser = async () => {
    try {
      // 使用hook进行注销
      await logoutMutation.mutateAsync()
      // 清除本地状态
      logout()
      // 跳转到登录页面，允许切换用户空间
      navigate(getLoginPagePath())
    } catch (error) {
      console.error('切换用户空间失败:', error)
      // 即使API调用失败，也清除本地状态
      logout()
      navigate(getLoginPagePath())
    }
  }

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8">
      {/* Left section */}
      <div className="flex items-center">
        <button onClick={onMenuClick} className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100">
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* Right section */}
      <div className="flex items-center space-x-4">
        <LanguageDropdown />

        {/* User menu */}
        <div className="relative" ref={userMenuRef}>
          <button onClick={() => setIsUserMenuOpen(!isUserMenuOpen)} className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <img className="w-8 h-8 rounded-full" src={resolveAvatar(user?.avatar, user?.username || user?.email, 128)} alt={user?.username} />
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-gray-900">{user?.username}</p>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>

          {/* User dropdown */}
          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-sm border border-gray-200 z-50">
              <div className="py-1">
                <button onClick={handleSwitchUser} className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                  <Users className="w-4 h-4 mr-3" />
                  {t('layout.header.switchUser')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
