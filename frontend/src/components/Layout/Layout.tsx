import React, { useState, useEffect, useRef } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../../stores/useAuthStore'
import { useUIStore } from '../../stores/useUIStore'
import { useUserSpaces } from '@test-agentstudio/api-client'
import { ENV_CONFIG } from '@/config/environment'
import { CircularProgress } from '@mui/material'
import SidebarNew from './SidebarNew'
import { getLoginPagePath } from '@/Common/LoginPage.ts'

const Layout: React.FC = () => {
  const { t } = useTranslation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // 隐私提示弹窗状态（仅在 VITE_ENABLE_NEW_AUTH 为 true 时启用，首次登录成功后显示）
  const [showPrivacyDialog, setShowPrivacyDialog] = useState(false)

  const sidebarCollapsed = useUIStore(state => state.sidebarCollapsed)
  const setSidebarCollapsed = useUIStore(state => state.setSidebarCollapsed)
  const sidebarRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const { user, updateUser, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [isInitializingSpace, setIsInitializingSpace] = useState(false)
  const initializationRef = useRef(false)

  // 隐私提示弹窗：根据当前用户判断是否需要显示（按用户区分，每个用户首次登录显示一次）
  useEffect(() => {
    if (!ENV_CONFIG.VITE_ENABLE_NEW_AUTH || !user?.email) return
    const key = `privacy_notice_acknowledged_${user.email}`
    if (!localStorage.getItem(key)) {
      setShowPrivacyDialog(true)
    }
  }, [user?.email])

  const handleAcknowledgePrivacy = () => {
    if (user?.email) {
      localStorage.setItem(`privacy_notice_acknowledged_${user.email}`, 'true')
    }
    setShowPrivacyDialog(false)
  }

  // 获取用户空间列表的 hook
  const userSpacesQuery = useUserSpaces({ enabled: false })

  // 初始化 spaceId：如果用户已登录但 spaceId 为空，则获取并设置
  useEffect(() => {
    // 如果用户未登录，重置初始化状态
    if (!user) {
      initializationRef.current = false
      return
    }

    // 如果 spaceId 已存在，不需要初始化
    if (user.spaceId && user.spaceId.trim() !== '') {
      initializationRef.current = true
      return
    }

    // 如果已经初始化过，避免重复调用
    if (initializationRef.current || isInitializingSpace) {
      return
    }

    const initializeSpaceId = async () => {
      initializationRef.current = true
      setIsInitializingSpace(true)

      try {
        // 先检查 localStorage 中是否有保存的 spaceId
        const savedSpaceId = localStorage.getItem('selectedSpaceId')
        if (savedSpaceId && savedSpaceId.trim() !== '') {
          updateUser({ spaceId: savedSpaceId })
        }

        // 调用 API 获取最新空间列表
        const spaceResponse = await userSpacesQuery.refetch()
        const spaceList = spaceResponse.data?.data?.space_list

        if (spaceList && spaceList.length > 0) {
          // 如果之前有保存的 spaceId，检查它是否还在列表中
          const currentSpaceId = user?.spaceId || savedSpaceId
          const isCurrentSpaceValid = currentSpaceId && spaceList.some(s => s.space_id === currentSpaceId)

          let finalSpaceId = ''

          if (isCurrentSpaceValid) {
            finalSpaceId = currentSpaceId
            console.log('Layout: 当前 spaceId 有效:', finalSpaceId)
          } else {
            // 如果无效或没有，使用列表第一个
            finalSpaceId = spaceList[0].space_id
            console.log('Layout: 使用列表第一个 spaceId:', finalSpaceId)
          }

          localStorage.setItem('selectedSpaceId', finalSpaceId)
          updateUser({ spaceId: finalSpaceId })
        } else {
          // 如果没有获取到空间，使用默认值
          const defaultSpaceId = ENV_CONFIG.DEFAULT_SPACE_ID || '0'
          updateUser({ spaceId: defaultSpaceId })
        }
      } catch (spaceError) {
        console.error('Layout: 获取空间列表错误:', spaceError)
        // 即使获取失败，也使用默认值，避免页面无法加载
        const defaultSpaceId = ENV_CONFIG.DEFAULT_SPACE_ID || '0'
        updateUser({ spaceId: defaultSpaceId })
      } finally {
        setIsInitializingSpace(false)
      }
    }

    initializeSpaceId()
  }, [user, user?.id, user?.spaceId, updateUser, userSpacesQuery])
  useEffect(() => {
    const currentPath = location.pathname
    const prevPath = sessionStorage.getItem('kb_prev_pathname') || ''

    // 只有在路径真正变化时才更新
    if (prevPath !== currentPath) {
      sessionStorage.setItem('kb_prev_pathname', currentPath)

      // 如果当前路径不是 knowledge-bases 相关的，更新 kb_last_non_kb_path
      if (currentPath !== '/dashboard/knowledge-bases' && !currentPath.startsWith('/dashboard/knowledge-bases/')) {
        sessionStorage.setItem('kb_last_non_kb_path', currentPath)
      }
    }
  }, [location.pathname])

  // Set CSS custom properties for sidebar state
  useEffect(() => {
    document.documentElement.style.setProperty('--sidebar-collapsed', sidebarCollapsed ? '1' : '0')
    document.documentElement.style.setProperty('--sidebar-width', sidebarCollapsed ? '64px' : '256px')
  }, [sidebarCollapsed])

  // 如果用户未登录，重定向到登录页
  if (!user) {
    navigate(getLoginPagePath())
    return null
  }

  // 如果正在初始化 spaceId，显示加载状态
  if (isInitializingSpace || !user.spaceId || user.spaceId.trim() === '') {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center space-y-4">
          <CircularProgress />
          <div className="text-gray-600">{t('initializing')}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex overflow-hidden bg-gray-50">
      {/* Sidebar - 新版 */}
      <div ref={sidebarRef} className="h-full flex flex-col overflow-hidden">
        <SidebarNew
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => {
            setSidebarCollapsed(!sidebarCollapsed)
          }}
          user={user}
          onLogout={logout}
        />
      </div>

      {/* Main content */}
      <div ref={contentRef} className="flex-1 overflow-hidden flex flex-col transition-all duration-300 ease-in-out h-full relative">
        {/* Page content */}
        <main className="flex-1 overflow-auto bg-[#F8F9FC]">
          <div className="h-full min-w-full">
            <div className="min-w-full h-full">
              <Outlet />
            </div>
          </div>
        </main>

        {/* 隐私提示弹窗 - 仅覆盖主内容区域，不遮挡侧边栏 */}
        {showPrivacyDialog && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4 p-6 animate-in fade-in zoom-in">
              <div className="flex items-center gap-2 mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="text-lg font-semibold text-gray-800">{t('privacy.notice.title', '重要提示')}</h3>
              </div>
              <div className="text-sm text-gray-600 leading-relaxed mb-6">
                <p>
                  {t(
                    'privacy.notice.content',
                    '本平台仅供体验使用，请勿上传真实个人隐私数据。平台会定期清理数据，请善用导出功能及时备份重要数据。'
                  )}
                </p>
              </div>
              <div className="flex justify-end">
                <button
                  onClick={handleAcknowledgePrivacy}
                  className="px-6 py-2 text-sm font-medium text-white rounded-lg btn-login hover:opacity-90 transition-opacity"
                >
                  {t('privacy.notice.acknowledge', '我已了解')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Layout
