import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// UI相关状态类型定义
interface UIState {
  // 插件管理页面显示模式
  pluginViewMode: 'grid' | 'list' // 保留用于旧版页面
  pluginManagementViewMode: 'grid' | 'list' // 插件管理页面（新版）
  pluginMarketViewMode: 'grid' | 'list' // 插件市场页面（新版）
  // 智能体页面显示模式
  agentViewMode: 'grid' | 'table'
  // 工作流页面显示模式
  workflowViewMode: 'grid' | 'table'
  // 提示词页面显示模式
  promptsViewMode: 'grid' | 'list'
  // 知识库管理页面显示模式
  knowledgeBaseViewMode: 'grid' | 'list'
  memoryBaseViewMode: 'grid' | 'list'

  // 其他可以扩展的UI状态
  // 例如：主题模式、侧边栏状态、面板大小等
  theme: 'light' | 'dark' | 'auto'
  sidebarCollapsed: boolean
  mainLayoutSize: number
}

interface UIActions {
  // 插件显示模式操作
  setPluginViewMode: (mode: 'grid' | 'list') => void // 保留用于旧版页面
  setPluginManagementViewMode: (mode: 'grid' | 'list') => void // 插件管理页面（新版）
  setPluginMarketViewMode: (mode: 'grid' | 'list') => void // 插件市场页面（新版）
  // 智能体显示模式操作
  setAgentViewMode: (mode: 'grid' | 'table') => void
  // 工作流显示模式操作
  setWorkflowViewMode: (mode: 'grid' | 'table') => void
  // 提示词显示模式操作
  setPromptsViewMode: (mode: 'grid' | 'list') => void
  // 知识库显示模式操作
  setKnowledgeBaseViewMode: (mode: 'grid' | 'list') => void
  // 知识库显示模式操作
  setMemoryBaseViewMode: (mode: 'grid' | 'list') => void

  // 主题相关操作
  setTheme: (theme: 'light' | 'dark' | 'auto') => void

  // 侧边栏操作
  setSidebarCollapsed: (collapsed: boolean) => void

  // 布局大小操作
  setMainLayoutSize: (size: number) => void

  // 重置所有UI状态
  resetUIState: () => void
}

const initialState: UIState = {
  pluginViewMode: 'grid', // 默认为网格模式（旧版页面）
  pluginManagementViewMode: 'grid', // 默认为网格模式（插件管理页面）
  pluginMarketViewMode: 'grid', // 默认为网格模式（插件市场页面）
  agentViewMode: 'grid', // 默认为网格模式
  workflowViewMode: 'grid', // 默认为网格模式
  promptsViewMode: 'grid', // 默认为网格模式
  knowledgeBaseViewMode: 'grid', // 默认为网格模式
  memoryBaseViewMode: 'grid',
  theme: 'light',
  sidebarCollapsed: false,
  mainLayoutSize: 100,
}

export const useUIStore = create<UIState & UIActions>()(
  persist(
    (set, get) => ({
      ...initialState,

      // 设置插件显示模式（旧版页面）
      setPluginViewMode: (mode: 'grid' | 'list') => {
        console.log(`🎨 [UIStore] Plugin view mode changed to: ${mode}`)
        set({ pluginViewMode: mode })
      },

      // 设置插件管理页面显示模式（新版）
      setPluginManagementViewMode: (mode: 'grid' | 'list') => {
        console.log(`🎨 [UIStore] Plugin management view mode changed to: ${mode}`)
        set({ pluginManagementViewMode: mode })
      },

      // 设置插件市场页面显示模式（新版）
      setPluginMarketViewMode: (mode: 'grid' | 'list') => {
        console.log(`🎨 [UIStore] Plugin market view mode changed to: ${mode}`)
        set({ pluginMarketViewMode: mode })
      },

      // 设置智能体显示模式
      setAgentViewMode: (mode: 'grid' | 'table') => {
        console.log(`🎨 [UIStore] Agent view mode changed to: ${mode}`)
        set({ agentViewMode: mode })
      },

      // 设置工作流显示模式
      setWorkflowViewMode: (mode: 'grid' | 'table') => {
        console.log(`🎨 [UIStore] Workflow view mode changed to: ${mode}`)
        set({ workflowViewMode: mode })
      },

      // 设置提示词显示模式
      setPromptsViewMode: (mode: 'grid' | 'list') => {
        console.log(`🎨 [UIStore] Prompts view mode changed to: ${mode}`)
        set({ promptsViewMode: mode })
      },

      // 设置知识库显示模式
      setKnowledgeBaseViewMode: (mode: 'grid' | 'list') => {
        console.log(`🎨 [UIStore] Knowledge base view mode changed to: ${mode}`)
        set({ knowledgeBaseViewMode: mode })
      },

      // 设置记忆库显示模式
      setMemoryBaseViewMode: (mode: 'grid' | 'list') => {
        console.log(`🎨 [UIStore] Memory base view mode changed to: ${mode}`)
        set({ memoryBaseViewMode: mode })
      },

      // 设置主题
      setTheme: (theme: 'light' | 'dark' | 'auto') => {
        console.log(`🎨 [UIStore] Theme changed to: ${theme}`)
        set({ theme })
      },

      // 设置侧边栏折叠状态
      setSidebarCollapsed: (collapsed: boolean) => {
        console.log(`🎨 [UIStore] Sidebar collapsed changed to: ${collapsed}`)
        set({ sidebarCollapsed: collapsed })
      },

      // 设置主布局大小
      setMainLayoutSize: (size: number) => {
        console.log(`🎨 [UIStore] Main layout size changed to: ${size}%`)
        set({ mainLayoutSize: size })
      },

      // 重置UI状态
      resetUIState: () => {
        console.log('🎨 [UIStore] Resetting all UI state to initial values')
        set(initialState)
      },
    }),
    {
      name: 'ui-storage', // 在localStorage中的键名
      partialize: state => ({
        // 只持久化需要保存的状态
        pluginViewMode: state.pluginViewMode,
        pluginManagementViewMode: state.pluginManagementViewMode,
        pluginMarketViewMode: state.pluginMarketViewMode,
        agentViewMode: state.agentViewMode,
        workflowViewMode: state.workflowViewMode,
        promptsViewMode: state.promptsViewMode,
        knowledgeBaseViewMode: state.knowledgeBaseViewMode,
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        mainLayoutSize: state.mainLayoutSize,
      }),
      version: 1, // 版本号，用于状态迁移
      onRehydrateStorage: () => state => {
        console.log('🎨 [UIStore] UI state rehydrated from storage:', state)
      },
    },
  ),
)

// 便捷的hooks
export const usePluginViewMode = () => {
  const viewMode = useUIStore(state => state.pluginViewMode)
  const setViewMode = useUIStore(state => state.setPluginViewMode)

  return [viewMode, setViewMode] as const
}

export const usePluginManagementViewMode = () => {
  const viewMode = useUIStore(state => state.pluginManagementViewMode)
  const setViewMode = useUIStore(state => state.setPluginManagementViewMode)

  return [viewMode, setViewMode] as const
}

export const usePluginMarketViewMode = () => {
  const viewMode = useUIStore(state => state.pluginMarketViewMode)
  const setViewMode = useUIStore(state => state.setPluginMarketViewMode)

  return [viewMode, setViewMode] as const
}

export const useAgentViewMode = () => {
  const viewMode = useUIStore(state => state.agentViewMode)
  const setViewMode = useUIStore(state => state.setAgentViewMode)

  return [viewMode, setViewMode] as const
}

export const useWorkflowViewMode = () => {
  const viewMode = useUIStore(state => state.workflowViewMode)
  const setViewMode = useUIStore(state => state.setWorkflowViewMode)

  return [viewMode, setViewMode] as const
}

export const usePromptsViewMode = () => {
  const viewMode = useUIStore(state => state.promptsViewMode)
  const setViewMode = useUIStore(state => state.setPromptsViewMode)

  return [viewMode, setViewMode] as const
}

export const useTheme = () => {
  const theme = useUIStore(state => state.theme)
  const setTheme = useUIStore(state => state.setTheme)

  return [theme, setTheme] as const
}

// 默认导出
export default useUIStore
