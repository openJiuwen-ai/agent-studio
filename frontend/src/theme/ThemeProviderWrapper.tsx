import React, { useEffect, useMemo } from 'react'
import { ThemeProvider as MuiThemeProvider, createTheme } from '@mui/material/styles'
import { useUIStore } from '@/stores/useUIStore'
import { lightTheme, darkTheme } from './muiThemes'

type ResolvedTheme = 'light' | 'dark'

function resolveTheme(theme: 'light' | 'dark' | 'auto'): ResolvedTheme {
  if (theme === 'auto') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
}

interface ThemeProviderWrapperProps {
  children: React.ReactNode
}

export const ThemeProviderWrapper: React.FC<ThemeProviderWrapperProps> = ({ children }) => {
  const themePreference = useUIStore(state => state.theme)

  const resolved = useMemo<ResolvedTheme>(() => resolveTheme(themePreference), [themePreference])

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-theme', resolved)
    if (resolved === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [resolved])

  useEffect(() => {
    if (themePreference !== 'auto') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      const next = mq.matches ? 'dark' : 'light'
      document.documentElement.setAttribute('data-theme', next)
      document.documentElement.classList.toggle('dark', next === 'dark')
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [themePreference])

  const muiTheme = useMemo(() => (resolved === 'dark' ? darkTheme : lightTheme), [resolved])

  return <MuiThemeProvider theme={muiTheme}>{children}</MuiThemeProvider>
}

export default ThemeProviderWrapper
