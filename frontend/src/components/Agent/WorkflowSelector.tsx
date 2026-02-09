import React, { useState, useEffect, useMemo, useRef } from 'react'
import { Typography, Button, Pagination, Box } from '@mui/material'
import { X, Search } from 'lucide-react'
import { WorkflowService, useWorkflows, useSearchWorkflows } from '@test-agentstudio/api-client'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import i18n, { useScopedTranslation } from '@/i18n'
import { WorkflowSelectDetail, WorkflowDetail } from '../../types/agentTypes'
import { useAgentStore } from '@/stores/useAgentStore'
import { mapWorkflow, buildDetails } from '@/hooks/useWorkflowVersions'

interface WorkflowSelectorProps {
  open: boolean
  onClose: () => void
  onConfirm: (selectedWorkflows: string[], selectedWorkflowObjects: WorkflowSelectDetail[]) => void
  initialSelected?: string[]
  excludeWorkflowId?: string
}

const WorkflowSelector: React.FC<WorkflowSelectorProps> = ({ open, onClose, onConfirm, initialSelected = [], excludeWorkflowId }) => {
  const { t } = useScopedTranslation('agents.agentEditor.orchestration.workflowSelector')
  const [selectedWorkflows, setSelectedWorkflows] = useState<string[]>(initialSelected)
  const [selectedWorkflowsCache, setSelectedWorkflowsCache] = useState<Map<string, WorkflowSelectDetail>>(new Map())
  const updateWorkflowDetail = useAgentStore(s => s.updateWorkflowDetail)

  // 搜索相关状态
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState<string>('')
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 10

  const spaceId = useMemo(() => getDefaultSpaceId() || '', [])

  // 防抖处理搜索词
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm)
    }, 300) // 300ms防抖延迟

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [searchTerm])

  // 根据是否有搜索词决定使用哪个hook
  // 使用缓存策略优化选择器场景，避免频繁请求
  const {
    data: workflowData,
    isLoading: workflowLoading,
    error,
  } = debouncedSearchTerm.trim() !== ''
    ? useSearchWorkflows(
        {
          space_id: spaceId,
          search_term: debouncedSearchTerm.trim(),
          page: currentPage,
          page_size: pageSize,
        },
        { staleTime: 10 * 1000 }
      )
    : useWorkflows(
        {
          space_id: spaceId,
          page: currentPage,
          page_size: pageSize,
        },
        { staleTime: 10 * 1000, refetchOnMount: false }
      )

  // 从响应数据中提取工作流列表和分页信息
  const workflowList = useMemo(() => {
    if (workflowData?.code === 200 && Array.isArray(workflowData.data?.workflow_list)) {
      let workflows = workflowData.data.workflow_list.map(mapWorkflow)

      // 过滤掉需要排除的工作流ID
      if (excludeWorkflowId) {
        workflows = workflows.filter(workflow => workflow.id !== excludeWorkflowId)
      }

      return workflows
    }
    return []
  }, [workflowData, excludeWorkflowId])

  // Update cache when workflowList changes (proper side effect handling)
  useEffect(() => {
    if (workflowList.length > 0) {
      setSelectedWorkflowsCache(prev => {
        const newCache = new Map(prev)
        workflowList.forEach(workflow => {
          newCache.set(workflow.id, workflow)
        })
        return newCache
      })
    }
  }, [workflowList])

  // 分页信息
  const paginationInfo = useMemo(() => {
    if (workflowData?.code === 200 && workflowData.data) {
      return {
        total: workflowData.data.total,
        totalPages: workflowData.data.total_pages,
        currentPage: workflowData.data.page,
        pageSize: workflowData.data.page_size,
      }
    }
    return {
      total: 0,
      totalPages: 1,
      currentPage: 1,
      pageSize: pageSize,
    }
  }, [workflowData])

  useEffect(() => {
    setSelectedWorkflows(initialSelected)
  }, [initialSelected])

  // 当页面变化时重置当前页码到第1页，完全保留缓存
  useEffect(() => {
    if (open) {
      setCurrentPage(1)
      setSearchTerm('') // 打开时清空搜索词
      // 完全不重置缓存，保留所有已缓存的工作流数据
      // 这确保了从其他页面选择的工作流不会丢失
    }
  }, [open])

  // 当搜索词变化时，重置到第一页
  useEffect(() => {
    setCurrentPage(1)
  }, [debouncedSearchTerm])

  // 处理分页变化
  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setCurrentPage(value)
  }

  const existingWorkflows = useAgentStore(s => (s.saveAgentRequest as any)?.workflows || [])

  const handleConfirm = async () => {
    if (selectedWorkflows.length > 0) {
      // Use cached workflows first, then fallback to current page workflows
      let selectedWorkflowObjects: WorkflowSelectDetail[] = []
      const missingWorkflowIds: string[] = []

      selectedWorkflows.forEach(workflowId => {
        const cachedWorkflow = selectedWorkflowsCache.get(workflowId)
        if (cachedWorkflow) {
          selectedWorkflowObjects.push(cachedWorkflow)
        } else {
          missingWorkflowIds.push(workflowId)
        }
      })

      // For any workflows not in cache, try to get them from current page
      const currentWorkflowObjects = workflowList.filter(workflow => missingWorkflowIds.includes(workflow.id))

      // Update arrays with found workflows
      selectedWorkflowObjects = [...selectedWorkflowObjects, ...currentWorkflowObjects]

      // Remove found workflows from missing list
      const stillMissingIds = missingWorkflowIds.filter(id => !currentWorkflowObjects.some(w => w.id === id))

      // If there are still missing workflows, fetch them with a more efficient approach
      if (stillMissingIds.length > 0) {
        try {
          // 批量获取所有页面，找到缺失的工作流
          let allWorkflows: any[] = []
          let currentPage = 1
          let hasMore = true

          // 循环获取所有页面直到找到所有缺失的工作流
          while (hasMore && stillMissingIds.some(id => !allWorkflows.some(w => w.workflow_id === id))) {
            const response = await WorkflowService.getWorkflows({
              space_id: spaceId,
              page: currentPage,
              page_size: 10,
            })

            const pageWorkflows = response.data?.workflow_list || []
            allWorkflows = [...allWorkflows, ...pageWorkflows]

            // 检查是否还有更多页面
            const totalPages = response.data?.total_pages || 1
            hasMore = currentPage < totalPages
            currentPage++
          }

          // 从获取的工作流中找到缺失的
          const foundMissingWorkflows = allWorkflows.filter(workflow => stillMissingIds.includes(workflow.workflow_id)).map(workflow => mapWorkflow(workflow))

          const validFetchedWorkflows = foundMissingWorkflows.filter(w => w !== null) as WorkflowSelectDetail[]
          selectedWorkflowObjects = [...selectedWorkflowObjects, ...validFetchedWorkflows]

          // 更新缓存以包含新获取的工作流
          setSelectedWorkflowsCache(prev => {
            const newCache = new Map(prev)
            validFetchedWorkflows.forEach(workflow => {
              newCache.set(workflow.id, workflow)
            })
            return newCache
          })
        } catch (error) {
          console.error('Failed to fetch missing workflows:', error)
        }
      }

      // Ensure we have all selected workflows (filter out any that couldn't be found)
      const finalSelectedObjects = selectedWorkflowObjects.filter(w => selectedWorkflows.includes(w.id))

      const details = await buildDetails(existingWorkflows as WorkflowDetail[], finalSelectedObjects, spaceId)
      updateWorkflowDetail(details)
      const versionMap = new Map(details.map(d => [d.workflow_id, d.workflow_version]))
      const enriched = finalSelectedObjects.map(w => ({ ...w, version: versionMap.get(w.workflow_id) || 'draft' }))

      // Ensure we pass the correct selected workflow IDs (only those we found)
      const finalSelectedIds = finalSelectedObjects.map(w => w.id)
      onConfirm(finalSelectedIds, enriched)
    } else {
      onClose()
    }
  }

  const handleCancel = () => {
    setSelectedWorkflows(initialSelected)
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <Typography variant="h6" className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 font-bold">
            {t('title')}
          </Typography>
          <div onClick={handleCancel} className="text-gray-500 hover:text-gray-700 cursor-pointer p-2 rounded-full hover:bg-gray-100">
            <X className="w-5 h-5" />
          </div>
        </div>

        <div className="px-6 pt-4 pb-2">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-500 transition-colors duration-200" />
            <input
              type="text"
              placeholder={t('searchPlaceholder')}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
            />
            {searchTerm && (
              <button onClick={() => setSearchTerm('')} className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {workflowLoading ? (
          <div className="flex items-center justify-center py-12 flex-1">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">{t('loading')}</span>
          </div>
        ) : error ? (
          <div className="text-center py-12 text-red-500 flex-1">{t('loadFailed')}</div>
        ) : workflowList.length === 0 ? (
          <div className="text-center py-12 text-gray-500 flex-1">{debouncedSearchTerm.trim() ? t('noSearchResults') : t('noWorkflows')}</div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto">
              <div className="p-6 space-y-4">
                {workflowList.map(workflow => (
                  <div
                    key={workflow.id}
                    className={`p-5 rounded-xl border-2 transition-all duration-300 cursor-pointer ${
                      selectedWorkflows.includes(workflow.id) ? 'border-blue-400 bg-blue-50 shadow-sm' : 'border-gray-200 bg-white'
                    }`}
                    onClick={() => {
                      const isSelected = selectedWorkflows.includes(workflow.id)
                      setSelectedWorkflows(prev => (isSelected ? prev.filter(id => id !== workflow.id) : [...prev, workflow.id]))
                    }}
                    aria-selected={selectedWorkflows.includes(workflow.id)}
                    role="option"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 flex-1">
                        <div
                          className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${
                            selectedWorkflows.includes(workflow.id) ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          <span className="text-xl">{workflow.icon}</span>
                        </div>
                        <div className="flex-1 min-w-0 max-w-[280px]">
                          <h4
                            className={`font-semibold text-base ${selectedWorkflows.includes(workflow.id) ? 'text-blue-800' : 'text-gray-800'} overflow-hidden text-ellipsis whitespace-nowrap mb-2`}
                          >
                            {workflow.name}
                          </h4>
                          <p className="text-gray-600 text-sm overflow-hidden text-ellipsis whitespace-nowrap leading-relaxed mb-1">{workflow.description}</p>
                          <p className="text-xs text-gray-500 overflow-hidden text-ellipsis whitespace-nowrap">
                            {t('createdAtLabel')}
                            {workflow.create_time ? new Date(workflow.create_time).toLocaleDateString() : t('unknownDate')}
                          </p>
                        </div>
                      </div>

                      {selectedWorkflows.includes(workflow.id) && (
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          <span className="text-sm text-blue-700 font-medium">{t('selectedTag')}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {paginationInfo.totalPages > 1 && (
                <div className="flex justify-center px-6 pb-6">
                  <Box display="flex" justifyContent="center" alignItems="center" gap={2}>
                    <Typography variant="body2" color="textSecondary">
                      {t('paginationInfo', {
                        total: paginationInfo.total,
                        currentPage: paginationInfo.currentPage,
                        totalPages: paginationInfo.totalPages,
                      })}
                    </Typography>
                    <Pagination
                      count={paginationInfo.totalPages}
                      page={paginationInfo.currentPage}
                      onChange={handlePageChange}
                      color="primary"
                      size="small"
                      showFirstButton
                      showLastButton
                      siblingCount={1}
                      boundaryCount={1}
                    />
                  </Box>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-white">
              <Typography variant="body2" className="text-gray-500 font-medium">
                {t('selectedPrefix')} <span className="text-blue-600 font-bold">{selectedWorkflows.length}</span> {t('selectedSuffix')}
              </Typography>
              <div className="flex items-center space-x-3">
                <Button variant="outlined" onClick={handleCancel} className="border-2 border-gray-300 text-gray-700 hover:border-gray-500 hover:bg-gray-50">
                  {t('cancel')}
                </Button>
                <div
                  onClick={selectedWorkflows.length === 0 ? undefined : handleConfirm}
                  className={`inline-flex items-center justify-center px-4 py-2 rounded-md text-white ${
                    selectedWorkflows.length === 0
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 cursor-pointer'
                  }`}
                >
                  {t('confirmAdd')}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default WorkflowSelector
