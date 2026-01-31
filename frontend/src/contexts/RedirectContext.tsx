import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { getLoginPagePath } from '@/Common/LoginPage.ts'

interface RedirectContextType {
  currentPath: string
  previousPath: string | null
  isLoginRedirectInProgress: boolean
  updatePath: (path: string) => void
  setLoginRedirectInProgress: (inProgress: boolean) => void
  shouldRedirectToLogin: () => boolean
}

const RedirectContext = createContext<RedirectContextType | undefined>(undefined)

interface RedirectProviderProps {
  children: ReactNode
}

export const RedirectProvider: React.FC<RedirectProviderProps> = ({ children }) => {
  const [currentPath, setCurrentPath] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return window.location.pathname
    }
    return '/'
  })

  const [previousPath, setPreviousPath] = useState<string | null>(null)
  const [isLoginRedirectInProgress, setIsLoginRedirectInProgress] = useState(false)

  const updatePath = (path: string) => {
    if (path !== currentPath) {
      setPreviousPath(currentPath)
      setCurrentPath(path)
    }
  }

  const setLoginRedirectInProgress = (inProgress: boolean) => {
    setIsLoginRedirectInProgress(inProgress)
  }

  const shouldRedirectToLogin = () => {
    // Don't redirect to login if:
    // 1. Already on the login page
    // 2. Currently in a login redirect process
    // 3. Just came from the login page (to prevent loops)

    const isCurrentlyOnLoginPage = currentPath === getLoginPagePath()
    const recentlyOnLoginPage = previousPath === getLoginPagePath()

    if (isCurrentlyOnLoginPage) {
      console.log('🚫 [RedirectContext] Already on login page - skipping redirect')
      return false
    }

    if (isLoginRedirectInProgress) {
      console.log('🚫 [RedirectContext] Login redirect already in progress - skipping redirect')
      return false
    }

    if (recentlyOnLoginPage && currentPath === '/') {
      console.log('🚫 [RedirectContext] Recently on login page and now on root - skipping redirect to prevent loops')
      return false
    }

    console.log(`✅ [RedirectContext] Should redirect to login: current=${currentPath}, previous=${previousPath}`)
    return true
  }

  // Track route changes
  useEffect(() => {
    const handleRouteChange = () => {
      updatePath(window.location.pathname)
    }

    // Listen to browser navigation
    window.addEventListener('popstate', handleRouteChange)

    // Override pushState to catch programmatic navigation
    const originalPushState = history.pushState
    history.pushState = function(...args) {
      originalPushState.apply(history, args)
      handleRouteChange()
    }

    const originalReplaceState = history.replaceState
    history.replaceState = function(...args) {
      originalReplaceState.apply(history, args)
      handleRouteChange()
    }

    return () => {
      window.removeEventListener('popstate', handleRouteChange)
      history.pushState = originalPushState
      history.replaceState = originalReplaceState
    }
  }, [currentPath])

  const value: RedirectContextType = {
    currentPath,
    previousPath,
    isLoginRedirectInProgress,
    updatePath,
    setLoginRedirectInProgress,
    shouldRedirectToLogin,
  }

  return (
    <RedirectContext.Provider value={value}>
      {children}
    </RedirectContext.Provider>
  )
}

export const useRedirectContext = (): RedirectContextType => {
  const context = useContext(RedirectContext)
  if (context === undefined) {
    throw new Error('useRedirectContext must be used within a RedirectProvider')
  }
  return context
}

export default RedirectProvider