import React, { useMemo } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import AppWrapper from './components/AppWrapper'
import { ThemeProvider as DarkModeThemeProvider, useTheme } from './contexts/ThemeContext'
import './i18n' // Initialize i18n and attach to window
import './index.css'
import './utils/font-loader'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Create theme factory function that respects dark mode
const createAppTheme = (isDarkMode: boolean) =>
  createTheme({
    palette: {
      mode: isDarkMode ? 'dark' : 'light',
      primary: {
        main: isDarkMode ? '#5B8CFF' : '#3b82f6',
      },
      secondary: {
        main: isDarkMode ? '#7B61FF' : '#64748b',
      },
      background: {
        default: isDarkMode ? '#0F1115' : '#F8F9FC',
        paper: isDarkMode ? '#151922' : '#FFFFFF',
      },
      text: {
        primary: isDarkMode ? '#E6EAF2' : '#1a1a1a',
        secondary: isDarkMode ? '#9AA4B2' : '#666666',
      },
      divider: isDarkMode ? '#2A3245' : '#e0e0e0',
    },
    typography: {
      fontFamily: 'HarmonyOS Sans SC, HarmonyOS Sans, Inter, system-ui, sans-serif',
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            borderRadius: '8px',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: '12px',
            border: isDarkMode ? '1px solid #2A3245' : '1px solid #e0e0e0',
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
          },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: '8px',
          },
          notchedOutline: {
            borderColor: isDarkMode ? '#2A3245' : '#e0e0e0',
          },
        },
      },
    },
  })

// App component that uses theme context
const AppWithTheme: React.FC = () => {
  const { isDarkMode } = useTheme()
  const theme = useMemo(() => createAppTheme(isDarkMode), [isDarkMode])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppWrapper />
    </ThemeProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <DarkModeThemeProvider>
      <BrowserRouter>
        <AppWithTheme />
      </BrowserRouter>
    </DarkModeThemeProvider>
  </QueryClientProvider>,
)
