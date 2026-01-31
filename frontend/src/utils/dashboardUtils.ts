import { useUIStore } from '@/stores/useUIStore'

/**
 * 从 Store 中读取 isNew 标记
 * 用于判断当前是否显示新版 UI
 * 注意：这是一个 Hook，只能在组件内部使用
 */
export const useIsNewDashboard = () => {
  return useUIStore(state => state.isNewDashboard)
}
