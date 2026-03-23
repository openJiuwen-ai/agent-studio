import React, { Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/useAuthStore'
import { useNavigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout/Layout'

// Import i18n
import './i18n'
import { LanguageProvider } from './contexts/LanguageContext'

// 立即加载的核心页面（用户可能立即访问）- 统一使用新版
import LoginPage from './pages/Auth/LoginPage'
import AppsPage from './pages/Apps/AppsPage'
import AgentsPageNew from './pages/Agents/AgentsPageNew'
import WorkflowsPageNew from './pages/Workflows/WorkflowsPageNew'
import PromptsPageNew from './pages/Prompts/PromptsPageNew'
import KnowledgeBasePageNew from './pages/KnowledgeBase/KnowledgeBasePageNew'
import MemoryBasePageNew from './pages/MemoryBase/MemoryBasePageNew'
import UserLoginPage from '@/pages/Auth/UserLoginPage.tsx'
import PrivacyPolicyPage from '@/pages/Auth/PrivacyPolicyPage.tsx'
import { ENV_CONFIG } from '@/config/environment.ts'
import { getLoginPagePath } from '@/Common/LoginPage.ts'

// 懒加载非核心页面
const AgentCreatePage = React.lazy(() => import('./pages/Agents/AgentCreatePage'))
const AgentEditorEditPage = React.lazy(() => import('./pages/Agents/AgentEditorEditPage'))
const WorkflowCreationPage = React.lazy(() => import('./pages/Workflows/WorkflowCreationPage'))
const PromptEditPage = React.lazy(() => import('./pages/Prompts/PromptEditPage'))
const PromptOptimizePageNew = React.lazy(() => import('./pages/Prompts/PromptOptimizePageNew'))
const PromptOptimizeEditPage = React.lazy(() => import('./pages/Prompts/PromptOptimizeEditPage'))
const ModelsPageNew = React.lazy(() => import('./pages/Models/ModelsPageNew'))
const KnowledgeBaseSettingsPage = React.lazy(() => import('./pages/KnowledgeBase/KnowledgeBaseEditorPage'))
const MemoryBaseSettingsPage = React.lazy(() => import('./pages/MemoryBase/MemoryBaseEditorPage'))
const PluginManagementPageNew = React.lazy(() => import('./pages/Plugins/PluginManagementPageNew'))
const PluginMarketPageNew = React.lazy(() => import('./pages/Plugins/PluginMarketPageNew'))
const PluginConfigurationPage = React.lazy(() => import('./pages/Plugins/PluginConfigurationPage'))
const PluginVersionPage = React.lazy(() => import('./pages/Plugins/PluginVersionPage'))
const ToolConfigurationPage = React.lazy(() => import('./pages/Plugins/ToolConfigurationPage'))
const AgentPublishPage = React.lazy(() => import('./pages/Runtime/AgentPublishPage'))

// 懒加载workflow-canvas组件
const WorkflowCanvas = React.lazy(() => import('@test-agentstudio/workflow-canvas').then(module => ({ default: module.WorkflowCanvas })))

// 工作流编辑器外层容器（新版样式）
const WorkflowCanvasOuter: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <div className="py-6 h-full px-6">{children}</div>
}

// 加载组件
const LoadingFallback = () => (
  <div className="flex items-center justify-center h-64">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
  </div>
)

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to= {getLoginPagePath()} replace />
  }

  return <>{children}</>
}

// Layout 包装器：/dashboard 根路径统一重定向到 /dashboard/agents（新版首页）
const LayoutWrapper: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (location.pathname === '/dashboard') {
      navigate('/dashboard/agents', { replace: true })
    }
  }, [location.pathname, navigate])

  return <Layout />
}

const App: React.FC = () => {
  const { isAuthenticated } = useAuthStore()

  const enable_pwd = ENV_CONFIG.VITE_ENABLE_NEW_AUTH

  const loginRouteConfig = enable_pwd ? { path: '/user_login', element: <UserLoginPage /> } : { path: '/login', element: <LoginPage /> }

  const loginPath = enable_pwd ? '/user_login' : '/login'

  return (
    <div className="h-screen w-full overflow-hidden">
      <LanguageProvider>
        <Routes>
          {/* Public routes - 已登录默认进入新版首页 /dashboard/agents */}
          <Route path="/" element={<Navigate to={isAuthenticated ? '/dashboard/agents' : loginPath} replace />} />
          {/* Dynamic login route*/}
          <Route path={loginRouteConfig.path} element={loginRouteConfig.element} />
          {/* Privacy policy page - 仅在 VITE_ENABLE_NEW_AUTH 为 true 时启用 */}
          {enable_pwd && <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />}
          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <LayoutWrapper />
              </ProtectedRoute>
            }
          >
            {!enable_pwd && <Route path="apps" element={<AppsPage />} />}
            <Route path="agents" element={<AgentsPageNew />} />
            <Route
              path="agents/new"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <AgentCreatePage />
                </Suspense>
              }
            />
            <Route
              path="agents/:id"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <AgentEditorEditPage />
                </Suspense>
              }
            />
            <Route
              path="agents/:id/publish"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <AgentPublishPage />
                </Suspense>
              }
            />
            <Route path="workflows" element={<WorkflowsPageNew />} />
            <Route
              path="workflows/new"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <WorkflowCreationPage />
                </Suspense>
              }
            />
            <Route
              path="workflows/editor/:id"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <WorkflowCanvasOuter>
                    <WorkflowCanvas />
                  </WorkflowCanvasOuter>
                </Suspense>
              }
            />
            <Route path="prompts" element={<PromptsPageNew />} />
            <Route
              path="prompts/:id"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PromptEditPage />
                </Suspense>
              }
            />
            <Route
              path="prompts/new"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PromptEditPage />
                </Suspense>
              }
            />
            <Route
              path="prompts/optimize"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PromptOptimizePageNew />
                </Suspense>
              }
            />
            <Route
              path="prompts/optimize/new"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PromptOptimizeEditPage />
                </Suspense>
              }
            />
            <Route
              path="prompts/optimize/:id"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PromptOptimizeEditPage />
                </Suspense>
              }
            />
            <Route
              path="models"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <ModelsPageNew />
                </Suspense>
              }
            />
            <Route
              path="knowledge-bases/:id/edit"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <KnowledgeBaseSettingsPage />
                </Suspense>
              }
            />
            <Route
              path="knowledge-bases"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <KnowledgeBasePageNew />
                </Suspense>
              }
            />
            <Route
              path="memory-bases/:id/edit"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <MemoryBaseSettingsPage />
                </Suspense>
              }
            />
            <Route
              path="memory-bases"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <MemoryBasePageNew />
                </Suspense>
              }
            />
            <Route
              path="plugins"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PluginManagementPageNew />
                </Suspense>
              }
            />
            <Route
              path="plugins/market"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PluginMarketPageNew />
                </Suspense>
              }
            />
            <Route
              path="plugins/:plugin_id"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PluginConfigurationPage />
                </Suspense>
              }
            />
            <Route
              path="plugins/:plugin_id/:version"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PluginVersionPage />
                </Suspense>
              }
            />
            <Route
              path="plugins/:plugin_id/tools/:tool_id"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <ToolConfigurationPage />
                </Suspense>
              }
            />
          </Route>

          {/* Redirect to dashboard if authenticated, otherwise to login */}
          <Route path="*" element={isAuthenticated ? <Navigate to="/dashboard/agents" replace /> : <Navigate to={loginPath} replace />} />
        </Routes>
      </LanguageProvider>
    </div>
  )
}

export default App
