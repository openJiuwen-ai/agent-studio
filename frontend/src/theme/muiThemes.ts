import { createTheme } from '@mui/material/styles'

const typography = {
  fontFamily: 'HarmonyOS Sans SC, HarmonyOS Sans, Inter, system-ui, sans-serif',
}

const components = {
  MuiButton: {
    styleOverrides: {
      root: {
        textTransform: 'none',
        borderRadius: '8px',
      },
    },
  },
}

export const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#3b82f6' },
    secondary: { main: '#64748b' },
    background: { default: '#F8F9FC', paper: '#FFFFFF' },
  },
  typography,
  components,
})

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#60a5fa' },
    secondary: { main: '#94a3b8' },
    background: { default: '#0f172a', paper: '#1e293b' },
  },
  typography,
  components,
})
