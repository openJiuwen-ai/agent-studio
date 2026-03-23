import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import CssBaseline from '@mui/material/CssBaseline'
import { ThemeProviderWrapper } from './theme'
import AppWrapper from './components/AppWrapper'
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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <ThemeProviderWrapper>
      <CssBaseline />
      <BrowserRouter>
        <AppWrapper />
      </BrowserRouter>
    </ThemeProviderWrapper>
  </QueryClientProvider>,
)
