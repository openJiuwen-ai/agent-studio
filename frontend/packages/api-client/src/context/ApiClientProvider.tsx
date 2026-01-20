import React, { createContext, useContext, ReactNode, useEffect, useState, useRef } from 'react'
import { TokenProvider, AuthStateUpdater, LanguageProvider } from '../client'
import { setGlobalTokenProvider } from '../utils/apiClientFactory'

// API客户端上下文类型
interface ApiClientContextType {
  tokenProvider: TokenProvider
  authStateUpdater: AuthStateUpdater
  languageProvider?: LanguageProvider
}

// 创建上下文
const ApiClientContext = createContext<ApiClientContextType | null>(null)

// Provider组件属性
interface ApiClientProviderProps {
  children: ReactNode
  tokenProvider: TokenProvider
  authStateUpdater: AuthStateUpdater
  languageProvider?: LanguageProvider
}

// API客户端Provider组件
export const ApiClientProvider: React.FC<ApiClientProviderProps> = ({
  children,
  tokenProvider,
  authStateUpdater,
  languageProvider
}) => {
  // 使用 ref 来追踪初始化状态，避免触发重渲染
  const initializedRef = useRef(false)

  // 使用 lazy initial state 来获取初始 token
  const [lastToken, setLastToken] = useState<string>(() => {
    try {
      const token = tokenProvider() || ''
      // 在初始化 state 时同步设置 global provider
      // 这是安全的，因为它只在组件挂载时执行一次
      setGlobalTokenProvider(tokenProvider, authStateUpdater, languageProvider)
      initializedRef.current = true
      return token
    } catch (error) {
      console.error('ApiClientProvider initialization failed:', error)
      return ''
    }
  })

  // 监听token变化，避免频繁触发
  useEffect(() => {
    const currentToken = tokenProvider()

    // 只有token真正变化时才更新
    if (currentToken !== lastToken) {
      try {
        setGlobalTokenProvider(tokenProvider, authStateUpdater, languageProvider)
        setLastToken(currentToken || '')
      } catch (error) {
        console.error('Failed to update global provider:', error)
      }
    }
  }, [tokenProvider, authStateUpdater, languageProvider, lastToken])

  const contextValue: ApiClientContextType = {
    tokenProvider,
    authStateUpdater,
    languageProvider,
  }

  return <ApiClientContext.Provider value={contextValue}>{children}</ApiClientContext.Provider>
}

// 使用API客户端上下文的Hook
export const useApiClient = () => {
  const context = useContext(ApiClientContext)
  if (!context) {
    throw new Error('useApiClient must be used within an ApiClientProvider')
  }
  return context
}

// 获取token的Hook
export const useToken = () => {
  const { tokenProvider } = useApiClient()
  return tokenProvider()
}
