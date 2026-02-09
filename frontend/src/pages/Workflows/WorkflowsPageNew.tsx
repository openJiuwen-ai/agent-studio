import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { Plus } from 'lucide-react'

import {
  useCopyWorkflow,
  useDeleteWorkflow,
  useSearchWorkflows,
  useUpdateWorkflow,
  useWorkflows,
  WorkflowSortBy,
  WorkflowSortOrder,
} from '@test-agentstudio/api-client'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import DeleteConfirmationDialog from '../../components/Common/DeleteConfirmationDialog'
import { ENV_CONFIG } from '../../config/environment'
import { useOptimizedSearch } from '../../hooks/useSearchOptimization'
import { useAuthStore } from '../../stores/useAuthStore'
import { useWorkflowViewMode } from '../../stores/useUIStore'
import { processWorkflowData, Workflow } from '../../utils/workflowUtils'
import { CommonPageLayout, SearchInput } from '../../components/Common/common-page'
import { WorkflowGridView } from './components/WorkflowGridView'
import { WorkflowTableView } from './components/WorkflowTableView'
import { EditingState } from '../../components/Common/common-grid'

type ViewType = 'grid' | 'table'

const WorkflowsPage: React.FC = () => {
  const { t } = useTranslation()
  const { user } = useAuthStore()

  // 视图类型状态（持久化）
  const [viewMode, setViewMode] = useWorkflowViewMode()
  const viewType: ViewType = viewMode === 'grid' ? 'grid' : 'table'
  const setViewType = (type: ViewType) => setViewMode(type === 'grid' ? 'grid' : 'table')

  // 搜索优化 hook
  const searchOptimization = useOptimizedSearch(
    searchTerm => {
      // 搜索回调会自动处理防抖和输入法组合
    },
    {
      debounceDelay: 300,
      minChars: 0,
      respectComposition: true,
    },
  )

  const defaultWorkflowVersion = 'draft'

  const [sortBy, setSortBy] = useState<WorkflowSortBy | null>(WorkflowSortBy.update_time)
  const [sortOrder, setSortOrder] = useState<WorkflowSortOrder | null>(WorkflowSortOrder.desc)
  const [pagerState, setPagerState] = useState({ page: 1, pageSize: 20 })
  const [deleteDialog, setDeleteDialog] = useState<{
    isOpen: boolean
    workflowId: string
    workflowName: string
    workflowVersion?: string
  }>({
    isOpen: false,
    workflowId: '',
    workflowName: '',
    workflowVersion: defaultWorkflowVersion,
  })

  const deleteWorkflow = useDeleteWorkflow()
  const updateWorkflow = useUpdateWorkflow()
  const copyWorkflow = useCopyWorkflow()
  const { snackbar, showSuccess, showError, showInfo, closeSnackbar } = useUnifiedSnackbar()

  // 编辑状态相关
  const [editingState, setEditingState] = useState<EditingState>({
    id: null,
    field: null,
    value: '',
    isEditing: false,
  })
  // 跟踪正在保存的工作流 ID
  const [savingWorkflowId, setSavingWorkflowId] = useState<string | null>(null)

  // 判断是否需要使用搜索API
  const shouldUseSearch = searchOptimization.debouncedSearchTerm.trim() !== ''

  // 使用 ref 跟踪之前的搜索词
  const prevSearchTermRef = useRef<string>('')

  // 当开始搜索时，重置分页到第1页
  useEffect(() => {
    const currentSearchTerm = searchOptimization.debouncedSearchTerm.trim()
    const prevSearchTerm = prevSearchTermRef.current.trim()

    if (currentSearchTerm !== '' && prevSearchTerm === '') {
      setPagerState(prev => ({ ...prev, page: 1 }))
    }

    prevSearchTermRef.current = searchOptimization.debouncedSearchTerm
  }, [searchOptimization.debouncedSearchTerm])

  // 排序或搜索改变时重置页码
  useEffect(() => {
    setPagerState(prev => ({ ...prev, page: 1 }))
  }, [sortBy, sortOrder])

  // 搜索 API
  const {
    data: searchResponse,
    isFetching: isSearchLoading,
    refetch: refetchSearch,
  } = useSearchWorkflows({
    space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
    search_term: searchOptimization.debouncedSearchTerm,
    page: pagerState.page,
    page_size: pagerState.pageSize,
    ...(sortBy && sortOrder ? { sort_by: sortBy, sort_order: sortOrder } : {}),
  })

  // 列表 API
  const {
    data: workflowsResponse,
    isFetching: isWorkflowsLoading,
    error,
    refetch,
  } = useWorkflows({
    space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
    page: pagerState.page,
    page_size: pagerState.pageSize,
    ...(sortBy && sortOrder ? { sort_by: sortBy, sort_order: sortOrder } : {}),
  })

  // 获取工作流数据
  const searchWorkflows = searchResponse?.data?.workflow_list || []
  const workflows = workflowsResponse?.data?.workflow_list || []

  const displayWorkflows = useMemo(() => {
    // 后端已经处理了排序，直接使用返回的数据
    return shouldUseSearch ? searchWorkflows : workflows
  }, [shouldUseSearch, searchWorkflows, workflows])

  const isLoading = isSearchLoading || isWorkflowsLoading

  // 处理工作流数据
  const processedWorkflows = useMemo(() => {
    return processWorkflowData(displayWorkflows)
  }, [displayWorkflows])

  // 获取分页信息
  const response = shouldUseSearch ? searchResponse : workflowsResponse
  const totalItems = response?.data?.total || 0

  // 处理删除
  const handleDeleteWorkflow = (workflowId: string, workflowName: string, workflowVersion?: string) => {
    setDeleteDialog({
      isOpen: true,
      workflowId,
      workflowName,
      workflowVersion,
    })
  }

  const cancelDeleteWorkflow = () => {
    setDeleteDialog({ isOpen: false, workflowId: '', workflowName: '', workflowVersion: defaultWorkflowVersion })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.workflowId && deleteDialog.workflowName) {
      deleteWorkflow.mutate(
        {
          workflow_id: deleteDialog.workflowId,
          space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
          workflow_version: deleteDialog.workflowVersion || defaultWorkflowVersion,
        },
        {
          onSuccess: result => {
            if (result?.code === 200) {
              showSuccess(t('workflows.workflowList.deleteSuccess', { name: deleteDialog.workflowName }))
              refetch()
            } else {
              showError(result?.message || t('workflows.workflowList.deleteFailed', { name: deleteDialog.workflowName }))
            }
          },
          onError: () => {},
        },
      )
      setDeleteDialog({ isOpen: false, workflowId: '', workflowName: '', workflowVersion: defaultWorkflowVersion })
    }
  }

  // 处理编辑
  const handleStartEditing = (workflowId: string, field: 'name' | 'description', value: string) => {
    showInfo(field === 'name' ? t('workflows.workflowList.editNameInfo') : t('workflows.workflowList.editDescriptionInfo'))
    setEditingState({
      id: workflowId,
      field,
      value,
      isEditing: true,
    })
  }

  const handleCancelEditing = () => {
    setEditingState({ id: null, field: null, value: '', isEditing: false })
  }

  const handleUpdateValue = (value: string) => {
    setEditingState(prev => ({ ...prev, value }))
  }

  const isInputValid = (): boolean => {
    if (!editingState.value || editingState.value.trim() === '') {
      return false
    }

    if (editingState.field === 'name') {
      const namePattern = /^[a-zA-Z][a-zA-Z0-9_]*$/
      if (!namePattern.test(editingState.value.trim())) {
        return false
      }
    }

    return true
  }

  const getValidationError = (): string => {
    if (!editingState.value || editingState.value.trim() === '') {
      return editingState.field === 'name' ? '工作流名称不能为空' : '工作流描述不能为空'
    }

    if (editingState.field === 'name') {
      const namePattern = /^[a-zA-Z][a-zA-Z0-9_]*$/
      if (!namePattern.test(editingState.value.trim())) {
        return '工作流名称只能包含字母、数字、下划线，且必须以字母开头'
      }
    }

    return ''
  }

  const handleSaveEditing = () => {
    if (!editingState.id) return

    const errorMessage = getValidationError()
    if (errorMessage) {
      showError(errorMessage)
      return
    }

    const workflow = processedWorkflows.find(w => w.workflow_id === editingState.id)
    if (!workflow) {
      showError('找不到要编辑的工作流')
      return
    }

    const fieldToUpdate = editingState.field === 'name' ? 'name' : 'desc'

    // 设置正在保存的工作流 ID
    setSavingWorkflowId(editingState.id as string)

    updateWorkflow.mutate(
      {
        workflow_id: editingState.id as string,
        space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
        name: workflow.name,
        desc: workflow.desc,
        [fieldToUpdate]: editingState.value,
      },
      {
        onSuccess: result => {
          if (result?.code === 200) {
            showSuccess(t('workflows.workflowList.updateSuccess'))
          } else {
            showError(result?.message || t('workflows.workflowList.updateFailed'))
          }
          // 清除正在保存的状态
          setSavingWorkflowId(null)
          handleCancelEditing()
        },
        onError: (error: any) => {
          let errorMessage = t('workflows.workflowList.updateError')

          if (error?.response?.data?.detail) {
            const detailData = error.response.data.detail
            if (Array.isArray(detailData)) {
              const fieldErrors = detailData.map((errorDetail: any) => {
                if (errorDetail.loc && errorDetail.msg) {
                  const fieldName = errorDetail.loc[1] || '字段'
                  const friendlyMessage = getFriendlyErrorMessage(errorDetail.msg)
                  return `${fieldName}${friendlyMessage}`
                }
                return errorDetail.msg || errorDetail
              })
              errorMessage = fieldErrors.join('; ')
            } else if (typeof detailData === 'string') {
              errorMessage = detailData
            }
          } else if (error?.response?.data?.message) {
            errorMessage = error.response.data.message
          } else if (error?.message) {
            errorMessage = error.message
          }

          showError(errorMessage)
          // 清除正在保存的状态
          setSavingWorkflowId(null)
          handleCancelEditing()
        },
      },
    )
  }

  const getFriendlyErrorMessage = (errorMsg: string): string => {
    if (errorMsg.includes('already exists')) return '已存在'
    if (errorMsg.includes('too long')) return '过长'
    if (errorMsg.includes('too short') || errorMsg.includes('minimum length')) return '过短'
    if (errorMsg.includes('invalid') || errorMsg.includes('format')) return '格式无效'
    if (errorMsg.includes('required') || errorMsg.includes('field required')) return '为必填项'
    if (errorMsg.includes('empty') || errorMsg.includes('blank')) return '不能为空'

    const lengthMatch = errorMsg.match(/(\d+) characters?/)
    if (lengthMatch) {
      return `长度不能超过${lengthMatch[1]}个字符`
    }

    return errorMsg
  }

  const handleCopyWorkflow = (workflowId: string, spaceId: string, workflowName: string) => {
    copyWorkflow.mutate(
      {
        workflow_id: workflowId,
        space_id: spaceId,
      },
      {
        onSuccess: result => {
          if (result?.code === 200) {
            showSuccess(t('workflows.workflowList.copySuccess', { name: workflowName }))
            refetch()
          } else {
            showError(result?.message || t('workflows.workflowList.copyFailed', { name: workflowName }))
          }
        },
        onError: () => {
          showError(t('workflows.workflowList.copyError', { name: workflowName }))
        },
      },
    )
  }

  // 刷新工作流列表
  const location = useLocation()
  useEffect(() => {
    refetch()
  }, [location.pathname])

  // 取消不在列表中的编辑
  useEffect(() => {
    if (editingState.id && processedWorkflows) {
      const editingWorkflow = processedWorkflows.find(w => w.workflow_id === editingState.id)
      if (!editingWorkflow) {
        handleCancelEditing()
      }
    }
  }, [processedWorkflows])

  // 工具栏左侧（搜索 + 排序）
  const toolbarLeft = useMemo(
    () => (
      <>
        <SearchInput
          searchTerm={searchOptimization.searchTerm}
          placeholder={t('workflows.workflowList.searchPlaceholder')}
          onChange={searchOptimization.setSearchTerm}
          onCompositionStart={searchOptimization.handleCompositionStart}
          onCompositionEnd={searchOptimization.handleCompositionEnd}
        />
        {/* 排序选择器 - 仅在网格视图显示 */}
        {viewType === 'grid' && sortBy && sortOrder && (
          <>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as WorkflowSortBy)}
              className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm focus:outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6] transition-colors"
            >
              <option value={WorkflowSortBy.name}>{t('workflows.workflowList.sortByName')}</option>
              <option value={WorkflowSortBy.create_time}>{t('workflows.workflowList.sortByCreateTime')}</option>
              <option value={WorkflowSortBy.update_time}>{t('workflows.workflowList.sortByUpdateTime')}</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === WorkflowSortOrder.asc ? WorkflowSortOrder.desc : WorkflowSortOrder.asc)}
              className="h-8 w-8 bg-white border border-[#e5e7eb] text-[#6b7280] hover:text-[#374151] hover:bg-[#f9fafb] hover:border-[#d1d5db] rounded-[4px] transition-colors flex items-center justify-center"
              title={sortOrder === 'asc' ? t('workflows.workflowList.ascending') : t('workflows.workflowList.descending')}
            >
              {sortOrder === 'asc' ? <span className="text-sm">↑</span> : <span className="text-sm">↓</span>}
            </button>
          </>
        )}
      </>
    ),
    [searchOptimization.searchTerm, searchOptimization.setSearchTerm, searchOptimization.handleCompositionStart, searchOptimization.handleCompositionEnd, viewType, sortBy, sortOrder, t],
  )

  // 工具栏右侧（新建）
  const toolbarRight = useMemo(
    () => (
      <Link
        to="/dashboard/workflows/new"
        className="btn-primary h-8 flex items-center gap-2 text-sm px-4"
      >
        <Plus className="w-4 h-4" />
        <span>{t('workflows.createWorkflow')}</span>
      </Link>
    ),
    [t],
  )

  // 网格视图
  const gridView = useMemo(
    () => (
      <WorkflowGridView
        workflows={processedWorkflows}
        editingState={editingState}
        searchTerm={searchOptimization.debouncedSearchTerm}
        onEdit={handleStartEditing}
        onUpdateValue={handleUpdateValue}
        onSaveEdit={handleSaveEditing}
        onCancelEdit={handleCancelEditing}
        onCopy={handleCopyWorkflow}
        onDelete={handleDeleteWorkflow}
        savingWorkflowId={savingWorkflowId}
      />
    ),
    [processedWorkflows, editingState, savingWorkflowId, searchOptimization.debouncedSearchTerm, handleStartEditing, handleUpdateValue, handleSaveEditing, handleCancelEditing, handleCopyWorkflow, handleDeleteWorkflow],
  )

  // 处理表格数据获取和排序变化
  // 注意：由于使用客户端数据，onFetchData 主要用于处理排序变化
  const handleFetchTableData = useCallback((params: any) => {
    const field = params.field
    const order = params.order

    if (!field || !order) {
      setSortBy(null)
      setSortOrder(null)
      return
    }

    setSortBy(field as WorkflowSortBy)
    setSortOrder(order as WorkflowSortOrder)
  }, [])

  // 表格视图
  const tableView = useMemo(
    () => (
      <WorkflowTableView
        workflows={processedWorkflows}
        loading={isLoading}
        searchTerm={searchOptimization.debouncedSearchTerm}
        onCopy={handleCopyWorkflow}
        onDelete={handleDeleteWorkflow}
        onFetchData={handleFetchTableData}
        onSortChange={handleFetchTableData}
        defaultSort={sortBy && sortOrder ? { field: sortBy, order: sortOrder } : { field: WorkflowSortBy.update_time, order: WorkflowSortOrder.desc }}
      />
    ),
    [processedWorkflows, isLoading, searchOptimization.debouncedSearchTerm, handleCopyWorkflow, handleDeleteWorkflow, handleFetchTableData, sortBy, sortOrder],
  )

  // 处理错误信息
  const errorMessage = useMemo(() => {
    if (!error) return ''
    if (error instanceof Error) return error.message
    return String(error)
  }, [error])

  // 处理视图切换
  const handleViewTypeChange = useCallback((newViewType: ViewType) => {
    setViewType(newViewType)
    setPagerState(prev => ({ ...prev, page: 1 }))
    // 如果切换到 Grid 视图且排序为 null，重置为默认排序
    if (newViewType === 'grid' && sortBy === null) {
      setSortBy(WorkflowSortBy.update_time)
      setSortOrder(WorkflowSortOrder.desc)
    }
  }, [sortBy])

  return (
    <>
      <CommonPageLayout
        title={t('workflows.title')}
        showViewToggle={true}
        viewType={viewType}
        onViewTypeChange={handleViewTypeChange}
        pager={{
          total: totalItems,
          currentPage: pagerState.page,
          pageSize: pagerState.pageSize,
          pageSizeOptions: [20, 60, 100, 200],
        }}
        onPagerChange={(page, pageSize) => {
          setPagerState({ page, pageSize })
        }}
        loading={isLoading}
        error={errorMessage}
        toolbarLeft={toolbarLeft}
        toolbarRight={toolbarRight}
        gridView={gridView}
        tableView={tableView}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={cancelDeleteWorkflow}
        onConfirm={handleDeleteConfirm}
        itemType="workflow"
        itemName={deleteDialog.workflowName}
        isLoading={deleteWorkflow.isLoading}
      />

      {/* Unified Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </>
  )
}

export default WorkflowsPage
