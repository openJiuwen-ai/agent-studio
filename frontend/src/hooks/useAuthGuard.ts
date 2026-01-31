import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/useAuthStore'
import { AuthService } from '@test-agentstudio/api-client'
import { useRedirectContext } from '../contexts/RedirectContext'
import { getLoginPagePath } from '@/Common/LoginPage.ts'

interface UseAuthGuardOptions {
  redirectTo?: string
  enableSilentValidation?: boolean
  skipAutoRedirect?: boolean
  isLoginPage?: boolean
}

interface UseAuthGuardReturn {
  authStatusResolved: boolean
  shouldShowContent: boolean
  isLoading: boolean
}

/**
 * 认证守卫Hook - 防止认证状态检查时的视觉闪烁
 *
 * 特性：
 * - 预渲染守卫模式，防止认证状态检查时的UI闪烁
 * - 后台静默token验证，不显示加载状态
 * - 自动重定向已认证用户（可配置跳过）
 * - 登录页面感知，防止不必要的重定向
 * - 清理无效认证数据
 *
 * @param options 配置选项
 * @returns 认证状态和UI渲染控制
 */
export const useAuthGuard = (options: UseAuthGuardOptions = {}): UseAuthGuardReturn => {
  const { redirectTo = '/dashboard', enableSilentValidation = true, skipAutoRedirect = false, isLoginPage = false } = options

  const navigate = useNavigate()
  const location = useLocation()
  const { login, isAuthenticated, token } = useAuthStore()
  const { shouldRedirectToLogin, setLoginRedirectInProgress } = useRedirectContext()
  const [authStatusResolved, setAuthStatusResolved] = useState(false)
  const [shouldShowContent, setShouldShowContent] = useState(false)
  const authCheckRef = useRef(false)

  useEffect(() => {
    // 防止重复执行认证检查
    if (authCheckRef.current) {
      return
    }
    authCheckRef.current = true

    const checkAuthentication = async () => {
      console.log('🔐 [AuthGuard] Starting authentication check...', {
        isLoginPage,
        skipAutoRedirect,
        currentPath: location.pathname,
      })

      try {
        // 1. 检查Zustand中的认证状态
        if (isAuthenticated) {
          if (!skipAutoRedirect) {
            console.log('✅ [AuthGuard] Already authenticated via Zustand, redirecting to', redirectTo)

            // 如果不是登录页面，设置重定向状态
            if (!isLoginPage) {
              setLoginRedirectInProgress(true)
            }

            navigate(redirectTo, { replace: true })
            return
          } else {
            console.log('🔐 [AuthGuard] Auto-redirect skipped, showing content')
            setShouldShowContent(true)
            setAuthStatusResolved(true)
            return
          }
        }

        // 2. 检查本地存储的token
        const storedToken = localStorage.getItem('access_token')
        const zustandToken = token
        const currentToken = storedToken || zustandToken

        // 3. 如果没有token，直接显示内容
        if (!currentToken || !enableSilentValidation) {
          console.log('🔐 [AuthGuard] No token found or silent validation disabled, showing content')
          setShouldShowContent(true)
          setAuthStatusResolved(true)
          return
        }

        // 4. 静默验证token（不显示任何UI）
        console.log('🔐 [AuthGuard] Token found, validating silently...')

        try {
          const response = await AuthService.validateToken()

          if (response.data.valid) {
            console.log('✅ [AuthGuard] Token is valid, restoring session and redirecting')

            // 恢复用户会话
            const storedUser = localStorage.getItem('auth-storage')
            if (storedUser) {
              try {
                const authData = JSON.parse(storedUser)
                if (authData.state?.user && authData.state?.token) {
                  login(authData.state.user, authData.state.token, authData.state.refreshToken)

                  // 重启token自动刷新
                  const { startTokenRenewal } = useAuthStore.getState()
                  startTokenRenewal()
                }
              } catch (parseError) {
                console.warn('⚠️ [AuthGuard] Failed to parse stored auth data:', parseError)
              }
            }

            // 如果不是登录页面且没有跳过自动重定向，则跳转
            if (!isLoginPage && !skipAutoRedirect) {
              setLoginRedirectInProgress(true)
              navigate(redirectTo, { replace: true })
            } else {
              console.log('🔐 [AuthGuard] Login page or auto-redirect disabled, showing content')
              setShouldShowContent(true)
              setAuthStatusResolved(true)
            }
          } else {
            console.log('❌ [AuthGuard] Token is invalid, clearing and showing content')

            // 清除无效的认证数据
            clearInvalidAuthData()

            // 只有在非登录页面且允许重定向时才重定向
            if (!isLoginPage && shouldRedirectToLogin()) {
              setLoginRedirectInProgress(true)
              navigate(getLoginPagePath(), { replace: true })
            } else {
              // 显示内容
              setShouldShowContent(true)
              setAuthStatusResolved(true)
            }
          }
        } catch (validationError) {
          console.warn('⚠️ [AuthGuard] Token validation failed:', validationError)

          // 清除无效的认证数据
          clearInvalidAuthData()

          // 只有在非登录页面且允许重定向时才重定向
          if (!isLoginPage && shouldRedirectToLogin()) {
            setLoginRedirectInProgress(true)
            navigate(getLoginPagePath(), { replace: true })
          } else {
            // 显示内容
            setShouldShowContent(true)
            setAuthStatusResolved(true)
          }
        }
      } catch (error) {
        console.error('❌ [AuthGuard] Authentication check failed:', error)
        // 发生错误时显示内容
        setShouldShowContent(true)
        setAuthStatusResolved(true)
      }
    }

    checkAuthentication()
  }, [
    isAuthenticated,
    token,
    login,
    navigate,
    redirectTo,
    enableSilentValidation,
    skipAutoRedirect,
    isLoginPage,
    location.pathname,
    shouldRedirectToLogin,
    setLoginRedirectInProgress,
  ])

  return {
    authStatusResolved,
    shouldShowContent,
    isLoading: !authStatusResolved,
  }
}

/**
 * 清理无效的认证数据
 */
const clearInvalidAuthData = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('token_type')
  localStorage.removeItem('auth-storage')
}

export default useAuthGuard
