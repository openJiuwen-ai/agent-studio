import React, { Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/useAuthStore'
import { useUIStore } from './stores/useUIStore'
import { useNavigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout/Layout'

// Import i18n
import './i18n'
import { LanguageProvider } from './contexts/LanguageContext'

// 立即加载的核心页面（用户可能立即访问）
import LoginPage from './pages/Auth/LoginPage'
import DashboardPage from './pages/Dashboard/DashboardPage'
import AgentsPage from './pages/Agents/AgentsPage'
import AgentsPageNew from './pages/Agents/AgentsPageNew'
import WorkflowsPage from './pages/Workflows/WorkflowsPage'
import WorkflowsPageNew from './pages/Workflows/WorkflowsPageNew'
import PromptsPage from './pages/Prompts/PromptsPage'
import PromptsPageNew from './pages/Prompts/PromptsPageNew'
import KnowledgeBasePageNew from './pages/KnowledgeBase/KnowledgeBasePageNew'

// 懒加载非核心页面
const AgentCreatePage = React.lazy(() => import('./pages/Agents/AgentCreatePage'))
const AgentEditorEditPage = React.lazy(() => import('./pages/Agents/AgentEditorEditPage'))
const WorkflowCreationPage = React.lazy(() => import('./pages/Workflows/WorkflowCreationPage'))
const PromptEditPage = React.lazy(() => import('./pages/Prompts/PromptEditPage'))
const PromptOptimizePage = React.lazy(() => import('./pages/Prompts/PromptOptimizePage'))
const PromptOptimizePageNew = React.lazy(() => import('./pages/Prompts/PromptOptimizePageNew'))
const PromptOptimizeEditPage = React.lazy(() => import('./pages/Prompts/PromptOptimizeEditPage'))
const ModelsPage = React.lazy(() => import('./pages/Models/ModelsPage'))
const ModelsPageNew = React.lazy(() => import('./pages/Models/ModelsPageNew'))
const KnowledgeBasePage = React.lazy(() => import('./pages/KnowledgeBase/KnowledgeBasePage'))
const KnowledgeBaseSettingsPage = React.lazy(() => import('./pages/KnowledgeBase/KnowledgeBaseEditorPage'))
const PluginManagementPage = React.lazy(() => import('./pages/Plugins').then(module => ({ default: module.PluginManagementPage })))
const PluginManagementPageNew = React.lazy(() => import('./pages/Plugins/PluginManagementPageNew'))
const PluginMarketPageNew = React.lazy(() => import('./pages/Plugins/PluginMarketPageNew'))
const PluginConfigurationPage = React.lazy(() => import('./pages/Plugins/PluginConfigurationPage'))
const PluginVersionPage = React.lazy(() => import('./pages/Plugins/PluginVersionPage'))
const ToolConfigurationPage = React.lazy(() => import('./pages/Plugins/ToolConfigurationPage'))

// 懒加载workflow-canvas组件
const WorkflowCanvas = React.lazy(() => import('@test-agentstudio/workflow-canvas').then(module => ({ default: module.WorkflowCanvas })))

// 工作流编辑器外层容器
const WorkflowCanvasOuter: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isNew = useUIStore(state => state.isNewDashboard)
  return <div className={isNew ? 'py-6 h-full px-6' : 'h-full px-6'}>{children}</div>
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
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

// 条件渲染 Agents 页面
const AgentsPageWrapper: React.FC = () => {
  const isNew = useUIStore(state => state.isNewDashboard)
  return isNew ? <AgentsPageNew /> : <AgentsPage />
}

// 条件渲染 Workflows 页面
const WorkflowsPageWrapper: React.FC = () => {
  const isNew = useUIStore(state => state.isNewDashboard)
  return isNew ? <WorkflowsPageNew /> : <WorkflowsPage />
  // return <WorkflowsPage />
}

// 条件渲染 Models 页面
const ModelsPageWrapper: React.FC = () => {
  const isNew = useUIStore(state => state.isNewDashboard)
  return isNew ? <ModelsPageNew /> : <ModelsPage />
  // return <ModelsPage />
}

// 条件渲染 Plugins 页面
const PluginsPageWrapper: React.FC = () => {
  const isNew = useUIStore(state => state.isNewDashboard)
  return isNew ? <PluginManagementPageNew /> : <PluginManagementPage />
}

// 条件渲染 Prompts 页面
const PromptsPageWrapper: React.FC = () => {
  const isNew = useUIStore(state => state.isNewDashboard)
  return isNew ? <PromptsPageNew /> : <PromptsPage />
}

// 条件渲染 KnowledgeBase 页面（新版 CommonPageLayout + 网格/表格；旧版自建布局 + KnowledgeBaseCard）
const KnowledgeBasePageWrapper: React.FC = () => {
  const isNew = useUIStore(state => state.isNewDashboard)
  return isNew ? <KnowledgeBasePageNew /> : <KnowledgeBasePage />
}

// 条件渲染 提示词自优化 页面（新版 CommonPageLayout + 仅表格 + 状态筛选；旧版自建布局 + 统计卡片）
const PromptOptimizePageWrapper: React.FC = () => {
  const isNew = useUIStore(state => state.isNewDashboard)
  return isNew ? <PromptOptimizePageNew /> : <PromptOptimizePage />
}

// Layout 包装器：当切换到新版且在 /dashboard 时，自动跳转到 /dashboard/agents
// 当切换到旧版且在 /dashboard/plugins/market 时，重定向到 /dashboard/plugins
const LayoutWrapper: React.FC = () => {
  const isNew = useUIStore(state => state.isNewDashboard)
  const navigate = useNavigate()
  const location = useLocation()

  // 当切换到新版且在 /dashboard 时，自动跳转到 /dashboard/agents
  useEffect(() => {
    if (isNew && location.pathname === '/dashboard') {
      navigate('/dashboard/agents', { replace: true })
    }
  }, [isNew, location.pathname, navigate])

  // 当切换到旧版且在 /dashboard/plugins/market 时，重定向到 /dashboard/plugins
  useEffect(() => {
    if (!isNew && location.pathname === '/dashboard/plugins/market') {
      navigate('/dashboard/plugins', { replace: true })
    }
  }, [isNew, location.pathname, navigate])

  return <Layout />
}

const App: React.FC = () => {
  const { isAuthenticated } = useAuthStore()
  const isNew = useUIStore(state => state.isNewDashboard)

  return (
    <div className="h-screen w-full overflow-hidden">
      <LanguageProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Navigate to={isAuthenticated ? (isNew ? '/dashboard/agents' : '/dashboard') : '/login'} replace />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <LayoutWrapper />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />

            <Route path="agents" element={<AgentsPageWrapper />} />
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
            <Route path="workflows" element={<WorkflowsPageWrapper />} />
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
            <Route path="prompts" element={<PromptsPageWrapper />} />
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
                  <PromptOptimizePageWrapper />
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
                  <ModelsPageWrapper />
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
                  <KnowledgeBasePageWrapper />
                </Suspense>
              }
            />
            <Route
              path="plugins"
              element={
                <Suspense fallback={<LoadingFallback />}>
                  <PluginsPageWrapper />
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
          <Route path="*" element={isAuthenticated ? <Navigate to={isNew ? '/dashboard/agents' : '/dashboard'} replace /> : <Navigate to="/login" replace />} />
        </Routes>
      </LanguageProvider>
    </div>
  )
}

export default App
