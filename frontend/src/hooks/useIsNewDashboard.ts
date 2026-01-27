import { useUIStore } from '@/stores/useUIStore'

/**
 * 返回是否使用新版 Dashboard UI
 * 从 store 中读取状态，自动持久化
 */
export const useIsNewDashboard = () => {
  return useUIStore(state => state.isNewDashboard)
}

/**
 * 返回切换 Dashboard 版本的函数
 */
export const useToggleDashboard = () => {
  return useUIStore(state => state.toggleDashboardVersion)
}
