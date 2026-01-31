import { createApiClient } from './apiClientFactory'
import type { TokenProvider, AuthStateUpdater } from '../client'
import { getLoginPagePath } from '../../../../src/Common/LoginPage'

// 认证状态更新函数类型，增强版
export type EnhancedAuthStateUpdater = AuthStateUpdater & {
  shouldRedirectToLogin?: () => boolean
  setLoginRedirectInProgress?: (inProgress: boolean) => void
}

// 智能重定向到登录页
const smartRedirectToLogin = (authStateUpdater?: EnhancedAuthStateUpdater): boolean => {
  // 检查是否应该重定向到登录页
  if (authStateUpdater?.shouldRedirectToLogin && !authStateUpdater.shouldRedirectToLogin()) {
    console.log('🚫 [EnhancedApiClient] Smart redirect check - skipping login redirect')
    return false
  }

  // 执行重定向
  if (typeof window !== 'undefined') {
    console.log('🔄 [EnhancedApiClient] Redirecting to login page...')

    // 标记重定向开始
    authStateUpdater?.setLoginRedirectInProgress?.(true)
    window.location.href = getLoginPagePath()
    return true
  }

  return false
}

// 创建增强版API客户端实例的工厂函数
export const createEnhancedApiClient = (
  tokenProvider?: TokenProvider,
  authStateUpdater?: EnhancedAuthStateUpdater
) => {
  const client = createApiClient(tokenProvider, authStateUpdater)

  // 覆盖响应拦截器以提供智能重定向
  client.interceptors.response.use(
    (response) => response, // 保持成功响应不变
    async (error) => {
      const originalRequest = error.config

      // 处理401未授权错误
      if (error.response?.status === 401 && !originalRequest._retry) {
        if (authStateUpdater) {
          try {
            // 尝试刷新token（保持原有逻辑）
            const { renewToken } = await import('../client')
            const newToken = await renewToken(authStateUpdater)

            if (newToken) {
              authStateUpdater.updateToken?.(newToken)
              originalRequest.headers.Authorization = `Bearer ${newToken}`
              originalRequest._retry = true
              return client.request(originalRequest)
            }
          } catch (refreshError) {
            console.error('❌ [EnhancedApiClient] Token refresh failed:', refreshError)
          }

          // 刷新失败，清除认证状态
          authStateUpdater.logout()

          // 智能重定向到登录页
          const shouldRedirect = smartRedirectToLogin(authStateUpdater)
          if (!shouldRedirect) {
            console.log('🚫 [EnhancedApiClient] Login redirect prevented by context')
          }
        } else {
          // 没有authStateUpdater时，直接重定向
          smartRedirectToLogin()
        }
      }

      return Promise.reject(error)
    }
  )

  return client
}

// 增强版token刷新函数，支持智能重定向
export const enhancedPerformTokenRenewal = async (authStateUpdater: EnhancedAuthStateUpdater) => {
  try {
    console.log('🔄 [EnhancedTokenRenewal] Starting automatic token refresh...')

    // 直接导入renewToken函数
    const renewToken = async (authStateUpdater: AuthStateUpdater): Promise<string | null> => {
      try {
        // 获取refresh token
        const refreshToken = authStateUpdater.getRefreshToken?.()
        if (!refreshToken) {
          console.warn('⚠️ No refresh token available - logging out')
          return null
        }

        console.debug('🔄 Attempting to refresh access token')

        // 创建不带认证的临时客户端用于刷新token
        const axios = require('axios')
        const { API_CONFIG, API_ENDPOINTS } = require('../config')

        const refreshClient = axios.create({
          baseURL: API_CONFIG.BASE_URL,
          timeout: API_CONFIG.TIMEOUT,
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
        })

        // 发送刷新token请求
        const response = await refreshClient.post(API_ENDPOINTS.AUTH.REFRESH, {
          refreshToken,
        })

        console.debug('✅ Token refresh response:', response.status)

        if (response.data && response.data.success !== false && response.data.data) {
          const newToken = response.data.data.token || response.data.data.access_token
          if (newToken) {
            console.debug('✅ Access token refreshed successfully')
            return newToken
          }
        }

        console.warn('⚠️ Invalid refresh token response format')
        return null
      } catch (error) {
        console.error('❌ Token refresh request failed:', error)
        throw error
      }
    }

    const newToken = await renewToken(authStateUpdater)

    if (newToken) {
      console.log('✅ [EnhancedTokenRenewal] Token refreshed successfully, updating access token')
      authStateUpdater.updateToken?.(newToken)
      console.log('📝 [EnhancedTokenRenewal] Access token updated successfully')
    } else {
      console.warn('⚠️ [EnhancedTokenRenewal] Token refresh failed - no new token returned')

      // 自动登出并智能跳转到登录页
      console.log('🚪 [EnhancedTokenRenewal] Logging out due to token refresh failure')
      authStateUpdater.logout()

      const shouldRedirect = smartRedirectToLogin(authStateUpdater)
      if (!shouldRedirect) {
        console.log('🚫 [EnhancedTokenRenewal] Login redirect prevented by context')
      }
    }
  } catch (error) {
    console.error('❌ [EnhancedTokenRenewal] Automatic token refresh failed:', error)

    // 自动登出并智能跳转到登录页
    console.log('🚪 [EnhancedTokenRenewal] Logging out due to token refresh failure')
    authStateUpdater.logout()

    const shouldRedirect = smartRedirectToLogin(authStateUpdater)
    if (!shouldRedirect) {
      console.log('🚫 [EnhancedTokenRenewal] Login redirect prevented by context')
    }
  }
}

// 增强版启动定时token刷新
export const startEnhancedTokenRenewal = (
  authStateUpdater: EnhancedAuthStateUpdater,
  intervalMs: number = 60000
) => {
  console.log(`🔄 [EnhancedTokenRenewal] Starting automatic token renewal timer (interval: ${intervalMs}ms)`)

  // 清除现有定时器
  const { stopTokenRenewal } = require('../client')
  stopTokenRenewal()

  // 立即执行一次
  enhancedPerformTokenRenewal(authStateUpdater)

  // 设置定时器
  const tokenRenewalTimer = setInterval(() => {
    enhancedPerformTokenRenewal(authStateUpdater)
  }, intervalMs)

  // 返回清除函数
  return () => {
    clearInterval(tokenRenewalTimer)
  }
}

export default {
  createEnhancedApiClient,
  enhancedPerformTokenRenewal,
  startEnhancedTokenRenewal,
  smartRedirectToLogin
}