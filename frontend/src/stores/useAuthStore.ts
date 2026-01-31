import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { startTokenRenewal, stopTokenRenewal } from '@test-agentstudio/api-client'

export interface User {
  id: string
  username: string
  email: string
  spaceId: string
  avatar?: string
  role: 'admin' | 'user' | 'developer'
  permissions: string[]
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthActions {
  login: (user: User, token: string, refreshToken?: string) => void
  logout: () => void
  setLoading: (loading: boolean) => void
  updateUser: (user: Partial<User>) => void
  startTokenRenewal: () => void
  stopTokenRenewal: () => void
}

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      login: (user: User, token: string, refreshToken?: string) => {
        console.log('🔑 [AuthStore] Login - Setting initial token: [TOKEN_PRESENT]')
        if (refreshToken) {
          console.log('🔑 [AuthStore] Login - Setting refresh token')
        }
        set({
          user,
          token,
          refreshToken: refreshToken || null,
          isAuthenticated: true,
          isLoading: false,
        })
      },

      logout: () => {
        // 停止 token 刷新
        get().stopTokenRenewal()
        const oldToken = get().token
        const oldRefreshToken = get().refreshToken
        console.log('🔑 [AuthStore] Logout - Clearing tokens')
        console.log('🔑 [AuthStore] Logout - Previous token: [Cleared]')
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
        })
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },

      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user
        if (currentUser) {
          const avatar = userData.avatar
          const isDefaultUnsplash = !!avatar && /unsplash\.com\/photo-1472099645785-5658abf4ff4e/.test(avatar)
          set({
            user: { ...currentUser, ...userData, avatar: isDefaultUnsplash ? undefined : avatar },
          })
        }
      },

      startTokenRenewal: () => {
        const { refreshToken, token } = get()
        if (refreshToken) {
          console.log('🔄 [AuthStore] Starting automatic token renewal...')
          const authStateUpdater = {
            logout: () => get().logout(),
            updateToken: (newToken: string) => {
              const oldToken = get().token
              console.log('✅ [AuthStore] Token refreshed successfully')
              console.log('🔄 [AuthStore] Token updated successfully')
              localStorage.setItem('access_token', newToken)
              set({ token: newToken })
            },
            getRefreshToken: () => refreshToken,
          }
          // 从环境变量获取刷新间隔，如果获取不到则使用默认600秒
          const envRefreshInterval = import.meta.env.VITE_TOKEN_REFRESH_INTERVAL_SECONDS
          console.log(`🔧 [AuthStore] Environment refresh interval: ${envRefreshInterval}`)
          const refreshIntervalSeconds = parseInt(envRefreshInterval || '600', 10)
          const refreshIntervalMs = refreshIntervalSeconds * 1000
          console.log(`⏱️ [AuthStore] Token refresh interval: ${refreshIntervalSeconds} seconds (${refreshIntervalMs}ms)`)
          if (!envRefreshInterval) {
            console.log('ℹ️ [AuthStore] Using default refresh interval (600 seconds) - VITE_TOKEN_REFRESH_INTERVAL_SECONDS not found in environment')
          }
          startTokenRenewal(authStateUpdater, refreshIntervalMs)
        } else {
          console.warn('⚠️ [AuthStore] No refresh token available, cannot start renewal')
        }
      },

      stopTokenRenewal: () => {
        console.log('⏹️ [AuthStore] Stopping automatic token renewal')
        stopTokenRenewal()
      },
    }),
    {
      name: 'auth-storage',
      partialize: state => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      // 🎯 关键修复：添加自动重启定时器的钩子
      onRehydrateStorage: () => (state) => {
        console.log('🔄 [AuthStore] Zustand rehydrated, checking token renewal...')
        console.log('🔍 [AuthStore] Rehydrated state:', state)

        // 延迟启动，确保所有组件都已挂载
        setTimeout(() => {
          // 安全检查：确保state存在且有效
          if (!state) {
            console.warn('⚠️ [AuthStore] No state available after rehydration')
            return
          }

          const { refreshToken, token, isAuthenticated } = state

          console.log('🔍 [AuthStore] Token check after rehydration:', {
            isAuthenticated,
            hasToken: !!token,
            hasRefreshToken: !!refreshToken,
            tokenLength: token?.length,
            refreshTokenLength: refreshToken?.length
          })

          // 更严格的验证：确保token和refreshToken都是有效的非空字符串
          if (isAuthenticated && token && refreshToken && token.length > 0 && refreshToken.length > 0) {
            console.log('✅ [AuthStore] Auto-starting token renewal after rehydration')

            // 创建一个全局的logout处理器和状态更新器
            let logoutHandler: (() => void) | null = null
            let currentToken = token
            let currentRefreshToken = refreshToken

            // 设置处理器函数，这些函数会在后续被调用来更新状态
            const setupHandlers = () => {
              const store = useAuthStore.getState()
              logoutHandler = store.logout
              currentToken = store.token || token
              currentRefreshToken = store.refreshToken || refreshToken
            }

            // 延迟设置处理器，确保store完全初始化
            setTimeout(setupHandlers, 100)

            const authStateUpdater = {
              logout: () => {
                console.log('🔑 [AuthStore] Logout triggered from rehydration timer')
                if (logoutHandler) {
                  logoutHandler()
                } else {
                  console.warn('⚠️ [AuthStore] Logout handler not available, forcing logout')
                  useAuthStore.setState({
                    user: null,
                    token: null,
                    refreshToken: null,
                    isAuthenticated: false,
                    isLoading: false,
                  })
                }
              },
              updateToken: (newToken: string) => {
                console.log('✅ [AuthStore] Token refreshed after rehydration')
                console.log('🔄 [AuthStore] Token updated successfully')
                currentToken = newToken
                useAuthStore.setState({ token: newToken })
              },
              getRefreshToken: () => {
                return currentRefreshToken
              },
            }

            // 从环境变量获取刷新间隔
            const envRefreshInterval = import.meta.env.VITE_TOKEN_REFRESH_INTERVAL_SECONDS
            const refreshIntervalSeconds = parseInt(envRefreshInterval || '600', 10)
            const refreshIntervalMs = refreshIntervalSeconds * 1000

            console.log(`⏱️ [AuthStore] Starting renewal with ${refreshIntervalSeconds}s interval`)

            try {
              startTokenRenewal(authStateUpdater, refreshIntervalMs)
            } catch (error) {
              console.error('❌ [AuthStore] Failed to start token renewal after rehydration:', error)
            }
          } else {
            console.warn('⚠️ [AuthStore] Cannot start token renewal after rehydration:', {
              isAuthenticated,
              hasToken: !!token,
              hasRefreshToken: !!refreshToken,
              tokenValid: token && token.length > 0,
              refreshTokenValid: refreshToken && refreshToken.length > 0
            })
          }
        }, 1000) // 1秒延迟，确保组件完全加载
      }
    },
  ),
)
