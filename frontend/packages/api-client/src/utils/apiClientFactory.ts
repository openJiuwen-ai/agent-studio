import { createApiClientInstance, TokenProvider, AuthStateUpdater, LanguageProvider } from '../client'
import { AxiosInstance } from 'axios'

// 全局token提供者
let globalTokenProvider: TokenProvider | null = null
let globalAuthStateUpdater: AuthStateUpdater | null = null
let globalLanguageProvider: LanguageProvider | null = null
let globalApiClient: AxiosInstance | null = null
let isInitialized: boolean = false

// 设置全局token提供者
export const setGlobalTokenProvider = (
  tokenProvider: TokenProvider,
  authStateUpdater: AuthStateUpdater,
  languageProvider?: LanguageProvider
) => {
  try {
    const currentToken = tokenProvider()

    // 检查token是否真的变化了
    const previousToken = globalTokenProvider ? globalTokenProvider() : null
    const tokenChanged = previousToken !== currentToken
    const providerChanged = globalTokenProvider !== tokenProvider || globalAuthStateUpdater !== authStateUpdater

    // 更新全局引用
    globalTokenProvider = tokenProvider
    globalAuthStateUpdater = authStateUpdater
    if (languageProvider) {
      globalLanguageProvider = languageProvider
    }

    // 只有在必要时才重新创建API客户端
    if (tokenChanged || !globalApiClient || providerChanged) {
      globalApiClient = createApiClientInstance(globalTokenProvider, globalAuthStateUpdater, globalLanguageProvider || undefined)
      isInitialized = true
    }
  } catch (error) {
    console.error('Failed to set global token provider:', error)
    throw error
  }
}

// 获取带token的API客户端
export const getApiClient = (): AxiosInstance => {
  if (!globalApiClient) {
    if (!globalTokenProvider || !globalAuthStateUpdater) {
      const storedToken = localStorage.getItem('access_token')
      if (storedToken) {
        globalTokenProvider = () => localStorage.getItem('access_token') || ''
        globalAuthStateUpdater = {
          logout: () => {
            localStorage.removeItem('access_token')
            window.location.href = '/login'
          },
          updateToken: (newToken: string) => {
            localStorage.setItem('access_token', newToken)
          },
        }
      } else {
        globalTokenProvider = () => ''
        globalAuthStateUpdater = {
          logout: () => {},
          updateToken: () => {},
        }
      }
    }
    globalApiClient = createApiClientInstance(globalTokenProvider, globalAuthStateUpdater, globalLanguageProvider || undefined)
    isInitialized = true
  }
  return globalApiClient
}

// 检查API客户端是否已初始化
export const isApiClientInitialized = (): boolean => {
  return isInitialized && !!globalApiClient && !!globalTokenProvider && !!globalAuthStateUpdater
}

// 等待API客户端初始化完成
export const waitForApiClientInitialization = (timeout: number = 3000): Promise<void> => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now()

    const checkInitialization = () => {
      if (isApiClientInitialized()) {
        resolve()
      } else if (Date.now() - startTime > timeout) {
        reject(new Error('API client initialization timeout'))
      } else {
        setTimeout(checkInitialization, 50)
      }
    }

    checkInitialization()
  })
}

// 获取token
export const getToken = () => {
  if (!globalTokenProvider) {
    return null
  }
  return globalTokenProvider()
}
