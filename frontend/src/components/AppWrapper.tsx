import React from 'react'
import { ApiClientProvider } from '@test-agentstudio/api-client'
import { useAuthStore } from '../stores/useAuthStore'
import i18n from '../i18n'
import App from '../App'

const AppWrapper: React.FC = () => {
  const { token, logout } = useAuthStore()
  const [isReady, setIsReady] = React.useState(false)
  const [finalToken, setFinalToken] = React.useState('')
  const [isInitialized, setIsInitialized] = React.useState(false)

  // 同步token状态，避免循环依赖
  React.useEffect(() => {
    const storedToken = localStorage.getItem('access_token')
    const newFinalToken = token || storedToken || ''

    setFinalToken(newFinalToken)

    // 标记为ready，避免组件永远不渲染
    if (!isReady) {
      setIsReady(true)
    }
  }, [token, isReady])

  // 创建稳定的token提供者 - 避免循环依赖
  const tokenProvider = React.useCallback(() => {
    return finalToken
  }, [finalToken])

  // 创建语言提供者
  const languageProvider = React.useCallback(() => {
    return i18n.language || 'zh-CN'
  }, [i18n.language])

  // 创建认证状态更新器
  const authStateUpdater = React.useCallback(
    () => ({
      logout,
      updateToken: (newToken: string) => {
        // Token更新逻辑由上层处理
      },
    }),
    [logout],
  )

  // 防止初始化逻辑重复执行
  React.useEffect(() => {
    if (!isInitialized && isReady) {
      setIsInitialized(true)
    }
  }, [isReady, isInitialized])

  // 等待状态恢复完成后再渲染
  if (!isReady) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }

  return (
    <ApiClientProvider tokenProvider={tokenProvider} authStateUpdater={authStateUpdater()} languageProvider={languageProvider}>
      <App />
    </ApiClientProvider>
  )
}

export default AppWrapper
