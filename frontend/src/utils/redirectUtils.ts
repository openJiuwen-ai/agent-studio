/**
 * 重定向工具函数 - 智能处理页面跳转，避免不必要的重定向
 */

import { useUIStore } from '@/stores/useUIStore'

// 检查当前是否已经在登录页面
export const isCurrentLoginPage = (): boolean => {
  if (typeof window === 'undefined') return false

  const currentPath = window.location.pathname
  return currentPath === '/login' || currentPath.includes('/login')
}

// 检查是否应该跳转到登录页面
export const shouldRedirectToLogin = (): boolean => {
  // 如果已经在登录页面，不需要再跳转
  if (isCurrentLoginPage()) {
    console.log('🔐 [RedirectUtils] Already on login page, skipping redirect')
    return false
  }

  return true
}

// 智能重定向到登录页面
export const smartRedirectToLogin = (): void => {
  if (shouldRedirectToLogin()) {
    console.log('🔄 [RedirectUtils] Redirecting to login page...')
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  } else {
    console.log('⏭️ [RedirectUtils] Skipping login redirect - already on login page')
  }
}


// 获取 Dashboard 目标路径
const getDashboardTargetPath = (): string => {
  const isNew = useUIStore.getState().isNewDashboard
  return isNew ? '/dashboard/agents' : '/dashboard'
}

// 重定向到 Dashboard（带智能检查）
export const smartRedirectToDashboard = (): void => {
  if (typeof window !== 'undefined') {
    const currentPath = window.location.pathname
    const targetPath = getDashboardTargetPath()

    // 如果已经在目标页面，不需要重定向
    if (currentPath === targetPath || currentPath.startsWith(targetPath + '/')) {
      console.log(`🏠 [RedirectUtils] Already on ${targetPath}, skipping redirect`)
      return
    }

    console.log(`🚀 [RedirectUtils] Redirecting to ${targetPath}...`)
    window.location.href = targetPath
  }
}

// 使用React Router的导航重定向（React组件内部使用）
export const createSmartRedirect = (navigate: (path: string, options?: any) => void) => ({
  toLogin: () => {
    if (shouldRedirectToLogin()) {
      console.log('🔄 [RedirectUtils] React Router: Redirecting to login...')
      navigate('/login', { replace: true })
    } else {
      console.log('⏭️ [RedirectUtils] React Router: Skipping login redirect - already on login page')
    }
  },

  toDashboard: () => {
    if (typeof window !== 'undefined') {
      const currentPath = window.location.pathname
      const targetPath = getDashboardTargetPath()

      if (currentPath === targetPath || currentPath.startsWith(targetPath + '/')) {
        console.log(`🏠 [RedirectUtils] React Router: Already on ${targetPath}, skipping redirect`)
        return
      }

      console.log(`🚀 [RedirectUtils] React Router: Redirecting to ${targetPath}...`)
      navigate(targetPath, { replace: true })
    }
  },
})

// 检查是否在认证相关页面
export const isAuthRelatedPage = (): boolean => {
  if (typeof window === 'undefined') return false

  const currentPath = window.location.pathname
  const authPaths = ['/login', '/register', '/forgot-password']

  return authPaths.some(path => currentPath === path || currentPath.includes(path))
}

// 增强的AuthStateUpdater，包含智能重定向逻辑
export const createEnhancedAuthStateUpdater = (baseAuthStateUpdater: any) => ({
  ...baseAuthStateUpdater,

  logout: () => {
    console.log('🚪 [EnhancedAuth] Logging out...')
    baseAuthStateUpdater.logout()

    // 只有在非登录页面时才重定向
    if (shouldRedirectToLogin()) {
      smartRedirectToLogin()
    }
  },

  forceLogout: () => {
    console.log('💥 [EnhancedAuth] Force logging out...')
    baseAuthStateUpdater.logout()
    // 强制登出总是重定向到登录页面
    smartRedirectToLogin()
  },
})
