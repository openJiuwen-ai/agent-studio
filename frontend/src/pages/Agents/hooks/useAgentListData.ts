import { useState, useEffect, useMemo, useCallback } from 'react'
import { useModels, useAgents, useSearchAgents, AgentSortBy, AgentSortOrder } from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore'
import { useAgentViewMode } from '@/stores/useUIStore'
import { useOptimizedSearch } from '@/hooks/useSearchOptimization'
import type { Agent } from '../components/types'

export interface AgentListDataResult {
  // Data
  modelsData: ReturnType<typeof useModels>['data']
  modelsLoading: boolean
  availableModelNames: Set<string>
  agents: Agent[]
  total: number
  isLoading: boolean
  error: string
  refetch: () => void

  // State
  viewType: 'grid' | 'table'
  sortBy: AgentSortBy | null
  sortOrder: AgentSortOrder | null
  pagerState: { page: number; pageSize: number }

  // Search
  searchTerm: string
  debouncedSearchTerm: string
  setSearchTerm: (term: string) => void

  // Actions
  setViewType: (type: 'grid' | 'table') => void
  setSortBy: (by: AgentSortBy | null) => void
  setSortOrder: (order: AgentSortOrder | null) => void
  setPagerState: (state: { page: number; pageSize: number }) => void
  handleFetchTableData: (params: any) => void
}

export function useAgentListData(): AgentListDataResult {
  const { user } = useAuthStore()

  // ==================== 视图状态 ====================
  const [viewMode, setViewMode] = useAgentViewMode()
  const viewType = viewMode === 'grid' ? 'grid' : 'table'
  const setViewType = (type: 'grid' | 'table') => setViewMode(type === 'grid' ? 'grid' : 'table')

  // ==================== 模型数据 ====================
  const { data: modelsData, isLoading: modelsLoading } = useModels({
    spaceId: user?.spaceId || '',
    is_active: true,
    size: 100,
  })

  const availableModelNames = useMemo(
    () => new Set(modelsData?.items?.map(model => model.name) || []),
    [modelsData],
  )

  // ==================== 列表状态 ====================
  const [sortBy, setSortBy] = useState<AgentSortBy | null>(AgentSortBy.update_time)
  const [sortOrder, setSortOrder] = useState<AgentSortOrder | null>(AgentSortOrder.desc)
  const [pagerState, setPagerState] = useState({ page: 1, pageSize: 20 })
  const [error, setError] = useState<string>('')

  // ==================== 搜索 ====================
  const { searchTerm, debouncedSearchTerm, setSearchTerm } =
    useOptimizedSearch(
      undefined,
      {
        debounceDelay: 300,
        minChars: 0,
        immediateOnEmpty: false,
        respectComposition: false,
      },
    )

  const shouldSearch = debouncedSearchTerm.trim() !== ''

  // ==================== Agent 数据获取 ====================
  const query = shouldSearch
    ? useSearchAgents({
        space_id: user?.spaceId || '',
        page: pagerState.page,
        page_size: pagerState.pageSize,
        search_term: debouncedSearchTerm.trim(),
        ...(sortBy && sortOrder ? { sort_by: sortBy, sort_order: sortOrder } : {}),
      } as any)
    : useAgents({
        space_id: user?.spaceId || '',
        page: pagerState.page,
        page_size: pagerState.pageSize,
        ...(sortBy && sortOrder ? { sort_by: sortBy, sort_order: sortOrder } : {}),
      } as any)

  const agents = (query.data?.data?.agent_items as Agent[]) || []
  const total = query.data?.data?.pagination?.total || 0
  const isLoading = query.isFetching
  const agentsError = query.error
  const refetch = query.refetch

  // ==================== 副作用 ====================
  // 排序或搜索改变时重置页码
  useEffect(() => {
    setPagerState(prev => ({ ...prev, page: 1 }))
  }, [sortBy, sortOrder, debouncedSearchTerm])

  // 错误处理
  useEffect(() => {
    if (agentsError) {
      const errorMessage = `${agentsError instanceof Error ? agentsError.message : 'Unknown error'}`
      setError(errorMessage)
    } else {
      setError('')
    }
  }, [agentsError])

  // ==================== 表格排序处理 ====================
  const handleFetchTableData = useCallback((params: any) => {
    const field = params.field
    const order = params.order

    if (!field || !order) {
      setSortBy(null)
      setSortOrder(null)
      return
    }

    setSortBy(field as AgentSortBy)
    setSortOrder(order as AgentSortOrder)
  }, [])

  // ==================== 视图切换处理 ====================
  const handleSetViewType = useCallback((newViewType: 'grid' | 'table') => {
    setViewType(newViewType)
    setPagerState(prev => ({ ...prev, page: 1 }))
    // 如果切换到 Grid 视图且排序为 null，重置为默认排序
    if (newViewType === 'grid' && sortBy === null) {
      setSortBy(AgentSortBy.update_time)
      setSortOrder(AgentSortOrder.desc)
    }
  }, [sortBy])

  return {
    // Data
    modelsData,
    modelsLoading,
    availableModelNames,
    agents,
    total,
    isLoading,
    error,
    refetch,

    // State
    viewType,
    sortBy,
    sortOrder,
    pagerState,

    // Search
    searchTerm,
    debouncedSearchTerm,
    setSearchTerm,

    // Actions
    setViewType: handleSetViewType,
    setSortBy,
    setSortOrder,
    setPagerState,
    handleFetchTableData,
  }
}
