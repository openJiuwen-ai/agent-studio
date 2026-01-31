import React, { useState, useEffect } from 'react'
import { Typography, Button, IconButton, Badge, Pagination, Box } from '@mui/material'
import { X, Plus, Minus } from 'lucide-react'
import WorkflowService from '../../../../api-client/src/services/workflowService'
import { WorkflowItem } from '../../../../api-client/src/types'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { dragStateManager } from '../../utils/drag-state-manager'
import { useTranslation } from '../../i18n'

interface WorkflowSelectorProps {
  open: boolean
  onClose: () => void
  onConfirm: (selectedWorkflows: WorkflowItem[]) => void
  initialSelected?: string[]
  /**
   * 是否允许重复添加同一个工作流
   * @default false
   */
  allowDuplicate?: boolean
  /**
   * 需要排除的工作流ID，该ID对应的工作流不会在选项中显示
   */
  excludeWorkflowId?: string
}

const WorkflowSelector: React.FC<WorkflowSelectorProps> = ({ open, onClose, onConfirm, initialSelected = [], allowDuplicate = false, excludeWorkflowId }) => {
  const { t } = useTranslation()
  const [workflowList, setWorkflowList] = useState<WorkflowItem[]>([])
  const [workflowLoading, setWorkflowLoading] = useState(false)
  // 如果允许重复添加，使用Map来存储每个工作流的选择次数和对象
  const [selectedWorkflowsMap, setSelectedWorkflowsMap] = useState<Map<string, { count: number; workflow: WorkflowItem }>>(new Map())
  // 兼容原有逻辑，保留selectedWorkflows数组
  const [selectedWorkflows, setSelectedWorkflows] = useState<string[]>(initialSelected)

  // 添加缓存来保存跨页面的工作流选择状态
  const [selectedWorkflowsCache, setSelectedWorkflowsCache] = useState<Map<string, WorkflowItem>>(new Map())

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const [totalWorkflows, setTotalWorkflows] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const pageSize = 10

  // 通知拖拽状态管理器模态框状态变化
  useEffect(() => {
    if (open) {
      dragStateManager.openModal()
    } else {
      dragStateManager.closeModal()
    }

    return () => {
      // Cleanup function to ensure modal is closed if component unmounts
      if (open) {
        dragStateManager.closeModal()
      }
    }
  }, [open])

  useEffect(() => {
    if (open) {
      setCurrentPage(1) // 打开时重置到第一页
      loadWorkflows(1)
    }
  }, [open, excludeWorkflowId, allowDuplicate]) // 移除 initialSelected 依赖，避免重复加载

  // 处理分页变化
  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setCurrentPage(value)
    loadWorkflows(value)
  }

  useEffect(() => {
    // 只在 initialSelected 变化时初始化选择状态
    setSelectedWorkflows(initialSelected)
  }, [initialSelected])

  // 当工作流列表变化时，更新缓存和选择映射
  useEffect(() => {
    if (workflowList.length > 0) {
      // 更新缓存
      setSelectedWorkflowsCache(prev => {
        const newCache = new Map(prev)
        workflowList.forEach(workflow => {
          newCache.set(workflow.workflow_id, workflow)
        })
        return newCache
      })

      // 更新选择映射（保持已有的选择，添加新的工作流数据）
      setSelectedWorkflowsMap(prev => {
        const newMap = new Map(prev)
        workflowList.forEach(workflow => {
          // 如果当前工作流在 selectedWorkflows 中，确保它也在 Map 中
          if (selectedWorkflows.includes(workflow.workflow_id) && !newMap.has(workflow.workflow_id)) {
            newMap.set(workflow.workflow_id, { count: 1, workflow })
          }
        })
        return newMap
      })
    }
  }, [workflowList, selectedWorkflows])

  // 确保初始选择的工作流数据被加载到缓存中
  useEffect(() => {
    if (initialSelected.length > 0 && open) {
      const loadMissingWorkflows = async () => {
        const missingIds = initialSelected.filter(workflowId => !selectedWorkflowsCache.has(workflowId))

        if (missingIds.length > 0) {
          try {
            // 这里可以批量加载缺失的工作流，但为了简化，我们先从第一页开始
            const response = await WorkflowService.getWorkflows({
              space_id: getDefaultSpaceId() || '',
              page: 1,
              page_size: 50, // 使用更大的页面大小来找到更多工作流
            })
            const workflows = response.data?.workflow_list || []

            setSelectedWorkflowsCache(prev => {
              const newCache = new Map(prev)
              workflows.forEach(workflow => {
                if (missingIds.includes(workflow.workflow_id)) {
                  newCache.set(workflow.workflow_id, workflow)
                }
              })
              return newCache
            })
          } catch (error) {
            console.error('Failed to load initial workflows:', error)
          }
        }
      }

      loadMissingWorkflows()
    }
  }, [initialSelected, open])

  const loadWorkflows = async (page: number = 1) => {
    setWorkflowLoading(true)
    try {
      const spaceId = getDefaultSpaceId()
      if (!spaceId) {
        setWorkflowList([])
        setTotalWorkflows(0)
        setTotalPages(1)
        return
      }

      const response = await WorkflowService.getWorkflows({
        space_id: spaceId,
        page,
        page_size: pageSize,
      })

      if (response.code === 200 && Array.isArray(response.data?.workflow_list)) {
        // 首先过滤掉需要排除的工作流ID
        let filteredWorkflows: WorkflowItem[] = response.data.workflow_list
        if (excludeWorkflowId) {
          filteredWorkflows = filteredWorkflows.filter((workflow: WorkflowItem) => workflow.workflow_id !== excludeWorkflowId)
        }

        if (allowDuplicate) {
          // 如果允许重复添加，显示所有工作流（除了被排除的）
          setWorkflowList(filteredWorkflows)
        } else {
          // 如果不允许重复添加，只排除被排除的工作流ID，保留已选择的工作流在列表中显示
          const filteredList = filteredWorkflows.filter((workflow: WorkflowItem) => workflow.workflow_id !== excludeWorkflowId)
          setWorkflowList(filteredList)
        }

        // 设置分页信息
        setTotalWorkflows(response.data?.total || 0)
        setTotalPages(response.data?.total_pages || 1)
      } else {
        setWorkflowList([])
        setTotalWorkflows(0)
        setTotalPages(1)
      }
    } catch (error) {
      console.error('Failed to load workflows:', error)
      setWorkflowList([])
      setTotalWorkflows(0)
      setTotalPages(1)
    } finally {
      setWorkflowLoading(false)
    }
  }

  const handleConfirm = () => {
    if (allowDuplicate) {
      // 如果允许重复添加，将Map中的工作流对象按照数量展开成数组
      const expandedSelectedWorkflows: WorkflowItem[] = []
      selectedWorkflowsMap.forEach((item, id) => {
        for (let i = 0; i < item.count; i++) {
          expandedSelectedWorkflows.push(item.workflow)
        }
      })

      if (expandedSelectedWorkflows.length > 0) {
        onConfirm(expandedSelectedWorkflows)
      } else {
        onClose()
      }
    } else {
      // 非重复模式
      if (selectedWorkflows && selectedWorkflows.length > 0) {
        // 优先从缓存中获取完整的工作流对象，然后从Map中获取
        const selectedWorkflowObjects: WorkflowItem[] = []
        selectedWorkflows.forEach(id => {
          const cachedWorkflow = selectedWorkflowsCache.get(id)
          const mapWorkflow = selectedWorkflowsMap.get(id)?.workflow
          const workflow = cachedWorkflow || mapWorkflow
          if (workflow) {
            selectedWorkflowObjects.push(workflow)
          }
        })

        onConfirm(selectedWorkflowObjects)
      } else {
        onClose()
      }
    }
  }

  const handleCancel = () => {
    setSelectedWorkflows(initialSelected)
    onClose()
  }

  // 处理工作流选择
  const handleWorkflowSelect = (workflowId: string) => {
    // 优先从当前页面查找，然后从缓存中查找
    let workflow = workflowList.find(w => w.workflow_id === workflowId)
    if (!workflow) {
      workflow = selectedWorkflowsCache.get(workflowId)
    }
    if (!workflow) return

    if (allowDuplicate) {
      // 如果允许重复添加，更新Map中的计数和对象
      const newMap = new Map(selectedWorkflowsMap)
      const current = newMap.get(workflowId)
      const currentCount = current?.count || 0

      if (currentCount > 0) {
        // 如果已经选择了，减少计数
        newMap.set(workflowId, { count: currentCount - 1, workflow })
        if (newMap.get(workflowId)?.count === 0) {
          newMap.delete(workflowId)
        }
      } else {
        // 如果还没选择，设置计数为1
        newMap.set(workflowId, { count: 1, workflow })
      }

      setSelectedWorkflowsMap(newMap)

      // 同时更新selectedWorkflows数组以保持兼容性
      const newSelectedWorkflows = Array.from(newMap.keys())
      setSelectedWorkflows(newSelectedWorkflows)

      // 确保工作流在缓存中
      if (!selectedWorkflowsCache.has(workflowId)) {
        setSelectedWorkflowsCache(prev => {
          const newCache = new Map(prev)
          newCache.set(workflowId, workflow)
          return newCache
        })
      }
    } else {
      // 单选模式：只能选择一个工作流
      const isSelected = selectedWorkflows.includes(workflowId)

      if (isSelected) {
        // 如果已经选中，则取消选择
        setSelectedWorkflows([])
        setSelectedWorkflowsMap(new Map())
      } else {
        // 如果未选中，则选择新的工作流（替换之前的选择）
        setSelectedWorkflows([workflowId])
        const newMap = new Map()
        newMap.set(workflowId, { count: 1, workflow })
        setSelectedWorkflowsMap(newMap)
      }

      // 确保工作流在缓存中
      if (!selectedWorkflowsCache.has(workflowId)) {
        setSelectedWorkflowsCache(prev => {
          const newCache = new Map(prev)
          newCache.set(workflowId, workflow)
          return newCache
        })
      }
    }
  }

  // 增加工作流数量
  const handleIncreaseCount = (e: React.MouseEvent, workflowId: string) => {
    e.stopPropagation() // 阻止事件冒泡
    if (allowDuplicate) {
      const newMap = new Map(selectedWorkflowsMap)
      // 优先从当前页面查找，然后从缓存中查找
      let workflow = workflowList.find(w => w.workflow_id === workflowId)
      if (!workflow) {
        workflow = selectedWorkflowsCache.get(workflowId)
      }
      if (!workflow) return

      const current = newMap.get(workflowId)
      const currentCount = current?.count || 0
      newMap.set(workflowId, { count: currentCount + 1, workflow })
      setSelectedWorkflowsMap(newMap)
    }
  }

  // 减少工作流数量
  const handleDecreaseCount = (e: React.MouseEvent, workflowId: string) => {
    e.stopPropagation() // 阻止事件冒泡
    if (allowDuplicate) {
      const newMap = new Map(selectedWorkflowsMap)
      const current = newMap.get(workflowId)
      if (!current) return

      const workflow = current.workflow
      const currentCount = current.count

      if (currentCount > 1) {
        newMap.set(workflowId, { count: currentCount - 1, workflow })
      } else if (currentCount === 1) {
        newMap.delete(workflowId)
      }
      setSelectedWorkflowsMap(newMap)

      // 同时更新selectedWorkflows数组以保持兼容性
      const newSelectedWorkflows = Array.from(newMap.keys())
      setSelectedWorkflows(newSelectedWorkflows)
    }
  }

  if (!open) return null

  return (
    <div
      className="workflow-selector-modal fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 z-[9999]"
      translate="no"
      onMouseDown={e => e.preventDefault()} // 防止鼠标事件冒泡到画布
      onMouseUp={e => e.preventDefault()} // 防止鼠标事件冒泡到画布
      onClick={e => e.preventDefault()} // 防止点击事件冒泡到画布
    >
      <div
        className="bg-white rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col notranslate"
        onMouseDown={e => e.stopPropagation()} // 阻止事件冒泡到遮罩层
        onMouseUp={e => e.stopPropagation()} // 阻止事件冒泡到遮罩层
        onClick={e => e.stopPropagation()} // 阻止事件冒泡到遮罩层
      >
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <Typography variant="h6" className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 font-bold">
            {t('workflowCanvas.workflowSelector.selectWorkflow')}
          </Typography>
          <IconButton onClick={handleCancel} className="text-gray-500 hover:text-gray-700">
            <X className="w-5 h-5" />
          </IconButton>
        </div>

        {workflowLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">{t('workflowCanvas.workflowSelector.loadingWorkflows')}</span>
          </div>
        ) : workflowList.length === 0 ? (
          <div className="text-center py-12 text-gray-500">{t('workflowCanvas.workflowSelector.noAvailableWorkflows')}</div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto">
              <div className="space-y-4 mb-6 p-6">
                {workflowList.map(workflow => (
                  <div
                    key={workflow.workflow_id}
                    className={`p-5 rounded-xl border-2 transition-all duration-300 cursor-pointer ${
                      (allowDuplicate ? selectedWorkflowsMap.has(workflow.workflow_id) : selectedWorkflows.includes(workflow.workflow_id))
                        ? 'border-blue-400 bg-blue-50 shadow-sm'
                        : 'border-gray-200 bg-white'
                    }`}
                    onClick={() => handleWorkflowSelect(workflow.workflow_id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 flex-1">
                        <div
                          className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${
                            (allowDuplicate ? selectedWorkflowsMap.has(workflow.workflow_id) : selectedWorkflows.includes(workflow.workflow_id))
                              ? 'bg-blue-100 text-blue-600'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          <span className="text-xl">{workflow.icon_uri || '📋'}</span>
                        </div>
                        <div className="flex-1 min-w-0 max-w-[280px]">
                          <h4
                            className={`font-semibold text-base ${
                              (allowDuplicate ? selectedWorkflowsMap.has(workflow.workflow_id) : selectedWorkflows.includes(workflow.workflow_id))
                                ? 'text-blue-800'
                                : 'text-gray-800'
                            } overflow-hidden text-ellipsis whitespace-nowrap mb-2`}
                          >
                            {workflow.name}
                          </h4>
                          <p className="text-gray-600 text-sm overflow-hidden text-ellipsis whitespace-nowrap leading-relaxed mb-1">{workflow.desc}</p>
                          <p className="text-xs text-gray-500 overflow-hidden text-ellipsis whitespace-nowrap">
                            {t('workflowCanvas.workflowSelector.createdAt')}: {new Date(workflow.create_time).toLocaleDateString()}
                          </p>
                        </div>
                      </div>

                      {allowDuplicate && selectedWorkflowsMap.has(workflow.workflow_id) ? (
                        <div className="flex items-center space-x-3">
                          <IconButton
                            size="small"
                            onClick={e => handleDecreaseCount(e, workflow.workflow_id)}
                            className="p-1.5 text-gray-600 hover:text-blue-600"
                          >
                            <Minus className="w-4 h-4" />
                          </IconButton>
                          <Badge badgeContent={selectedWorkflowsMap.get(workflow.workflow_id)?.count || 0} color="primary" className="mx-2" />
                          <IconButton
                            size="small"
                            onClick={e => handleIncreaseCount(e, workflow.workflow_id)}
                            className="p-1.5 text-gray-600 hover:text-blue-600"
                          >
                            <Plus className="w-4 h-4" />
                          </IconButton>
                        </div>
                      ) : (
                        !allowDuplicate &&
                        selectedWorkflows.includes(workflow.workflow_id) && (
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                            <span className="text-sm text-blue-700 font-medium">{t('workflowCanvas.workflowSelector.selected')}</span>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* 分页控件 */}
              {totalPages > 1 && (
                <div className="flex justify-center px-6 pb-6">
                  <Box display="flex" justifyContent="center" alignItems="center" gap={2}>
                    <Typography variant="body2" color="textSecondary">
                      {t('workflowCanvas.workflowSelector.pagination', { total: totalWorkflows, current: currentPage, totalPages })}
                    </Typography>
                    <Pagination
                      count={totalPages}
                      page={currentPage}
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

            <div className="flex items-center justify-between pt-4 border-t border-gray-200 p-6">
              <Typography variant="body2" className="text-gray-500 font-medium">
                {t('workflowCanvas.workflowSelector.selectedCount', {
                  count: allowDuplicate ? Array.from(selectedWorkflowsMap.values()).reduce((sum, item) => sum + item.count, 0) : selectedWorkflows.length,
                })}
              </Typography>
              <div className="flex items-center space-x-3">
                <Button variant="outlined" onClick={handleCancel} className="border-2 border-gray-300 text-gray-700 hover:border-gray-500 hover:bg-gray-50">
                  {t('workflowCanvas.workflowSelector.cancel')}
                </Button>
                <Button
                  variant="contained"
                  onClick={handleConfirm}
                  disabled={allowDuplicate ? selectedWorkflowsMap.size === 0 : selectedWorkflows.length === 0}
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                >
                  {t('workflowCanvas.workflowSelector.confirmAdd')}
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default WorkflowSelector
