import { AlertCircle, Check, Copy, Edit, Plus, Search, Trash2, Upload, X } from 'lucide-react'
import WorkflowIcon from '@/assets/icons/workflow.svg?react'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'

import {
  useCopyWorkflow,
  useDeleteWorkflow,
  useSearchWorkflows,
  useUpdateWorkflow,
  useWorkflows,
  WorkflowSortBy,
  WorkflowSortOrder,
} from '@test-agentstudio/api-client'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import DeleteConfirmationDialog from '../../components/Common/DeleteConfirmationDialog'
import ImportWorkflowDialog from '../../components/Workflows/ImportWorkflowDialog'
import { ENV_CONFIG } from '../../config/environment'
import { useOptimizedSearch } from '../../hooks/useSearchOptimization'
import { useAuthStore } from '../../stores/useAuthStore'
import { processWorkflowData } from '../../utils/workflowUtils'

const WorkflowsPage: React.FC = () => {
  const { t } = useTranslation()
  const { user } = useAuthStore()

  // 搜索优化 hook
  const searchOptimization = useOptimizedSearch(
    searchTerm => {
      // 搜索回调会自动处理防抖和输入法组合
      // 这里不需要额外的逻辑，hook 会处理
    },
    {
      debounceDelay: 300,
      minChars: 0, // 允许空搜索
      respectComposition: true, // 启用输入法组合检测
    },
  )

  const defaultWorkflowVersion = 'draft'

  const [sortBy, setSortBy] = useState<WorkflowSortBy>(WorkflowSortBy.update_time)
  const [sortOrder, setSortOrder] = useState<WorkflowSortOrder>(WorkflowSortOrder.desc)
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [page_size, setPageSize] = useState<number>(9)
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
  const [editingWorkflowId, setEditingWorkflowId] = useState<string | null>(null)
  const [editingField, setEditingField] = useState<'name' | 'desc' | null>(null)
  const [editingValue, setEditingValue] = useState<string>('')
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  // 导入工作流状态
  const [importDialogOpen, setImportDialogOpen] = useState(false)

  // 判断是否需要使用搜索API - 有搜索词时使用搜索API
  const shouldUseSearch = searchOptimization.debouncedSearchTerm.trim() !== ''

  // 使用 ref 跟踪之前的搜索词，用于检测搜索状态变化
  const prevSearchTermRef = useRef<string>('')

  // 当开始搜索时，重置分页到第1页
  useEffect(() => {
    const currentSearchTerm = searchOptimization.debouncedSearchTerm.trim()
    const prevSearchTerm = prevSearchTermRef.current.trim()

    // 从无搜索词变为有搜索词时，重置到第1页
    if (currentSearchTerm !== '' && prevSearchTerm === '') {
      setCurrentPage(1)
    }

    // 更新 ref 的值
    prevSearchTermRef.current = searchOptimization.debouncedSearchTerm
  }, [searchOptimization.debouncedSearchTerm])

  // 根据条件选择使用搜索API或原有的list API
  const {
    data: searchResponse,
    isLoading: isSearchLoading,
    refetch: refetchSearch,
  } = useSearchWorkflows({
    space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
    search_term: searchOptimization.debouncedSearchTerm,
    sort_by: sortBy,
    sort_order: sortOrder,
    page: currentPage,
    page_size: page_size,
  })

  // 保持原有的workflows query用于非搜索状态
  const {
    data: workflowsResponse,
    isLoading: isWorkflowsLoading,
    error,
    refetch,
  } = useWorkflows(
    {
      space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
      page: currentPage,
      page_size: page_size,
      sort_by: sortBy,
      sort_order: sortOrder,
    },
    {
      enabled: !shouldUseSearch, // 只在没有搜索条件时才启用list API
    },
  )

  // 根据状态获取工作流数据
  const searchWorkflows = searchResponse?.data?.workflow_list || []
  const workflows = workflowsResponse?.data?.workflow_list || []

  // 使用useMemo避免频繁切换导致的数据丢失
  const displayWorkflows = useMemo(() => {
    return shouldUseSearch ? searchWorkflows : workflows
  }, [shouldUseSearch, searchWorkflows, workflows])

  // 搜索时使用搜索结果，非搜索时使用全部工作流
  const isLoading = isSearchLoading || isWorkflowsLoading

  // 为显示的工作流生成模拟数据 - 使用useMemo避免无限重新计算
  const processedDisplayWorkflows = useMemo(() => {
    return processWorkflowData(displayWorkflows)
  }, [displayWorkflows])

  // 由于现在后端支持过滤和排序，前端只需要直接使用后端返回的结果
  // 搜索和非搜索都已经由后端处理了分页、过滤和排序
  const paginatedWorkflows = processedDisplayWorkflows

  // 获取分页信息 - 根据使用的是搜索还是列表API来获取不同的分页数据
  const response = shouldUseSearch ? searchResponse : workflowsResponse
  const totalItems = response?.data?.total || 0
  const totalPages = response?.data?.total_pages || 1

  // Refresh workflows list
  const refreshWorkflows = () => {
    refetch()
  }

  // Handle successful import
  const handleImportSuccess = () => {
    showSuccess(t('workflows.import.success'))
    refetch() // Refresh workflow list
    setImportDialogOpen(false)
  }

  // Handle workflow deletion
  const handleDeleteWorkflow = (workflowId: string, workflowName: string, workflowVersion?: string) => {
    setDeleteDialog({
      isOpen: true,
      workflowId,
      workflowName,
      workflowVersion,
    })
  }

  // Cancel workflow deletion
  const cancelDeleteWorkflow = () => {
    setDeleteDialog({ isOpen: false, workflowId: '', workflowName: '', workflowVersion: defaultWorkflowVersion })
  }

  // Handle workflow deletion with loading state
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
              // 立即刷新数据
              refetch()
            } else {
              showError(result?.message || t('workflows.workflowList.deleteFailed', { name: deleteDialog.workflowName }))
            }
          },
          onError: (error: any) => {},
        },
      )
      setDeleteDialog({ isOpen: false, workflowId: '', workflowName: '', workflowVersion: defaultWorkflowVersion })
    }
  }

  // 处理开始编辑
  const handleStartEditing = (workflowId: string, field: 'name' | 'desc', value: string) => {
    console.log('[handleStartEditing] 开始编辑', { workflowId, field, value })

    showInfo(field === 'name' ? t('workflows.workflowList.editNameInfo') : t('workflows.workflowList.editDescriptionInfo'))

    setEditingWorkflowId(workflowId)
    setEditingField(field)
    setEditingValue(value)
    setEditingIndex(null) // 不再需要索引
  }

  // 处理取消编辑
  const handleCancelEditing = () => {
    setEditingWorkflowId(null)
    setEditingField(null)
    setEditingValue('')
    setEditingIndex(null)
  }

  // 处理输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    // 根据字段类型限制字符长度
    const maxLength = editingField === 'name' ? 100 : 500
    const value = e.target.value.substring(0, maxLength)
    setEditingValue(value)
  }

  // 验证输入是否有效（不显示错误，只返回验证结果）
  const isInputValid = (): boolean => {
    if (!editingValue || editingValue.trim() === '') {
      return false
    }

    // 如果编辑的是名称，需要验证格式
    if (editingField === 'name') {
      // 工作流名称只能包含字母、数字、下划线，且必须以字母开头
      const namePattern = /^[a-zA-Z][a-zA-Z0-9_]*$/
      if (!namePattern.test(editingValue.trim())) {
        return false
      }
    }

    return true
  }

  // 获取验证错误信息
  const getValidationError = (): string => {
    if (!editingValue || editingValue.trim() === '') {
      return editingField === 'name' ? t('workflows.workflowList.workflowNameEmpty') : t('workflows.workflowList.workflowDescEmpty')
    }

    // 如果编辑的是名称，需要验证格式
    if (editingField === 'name') {
      // 工作流名称只能包含字母、数字、下划线，且必须以字母开头
      const namePattern = /^[a-zA-Z][a-zA-Z0-9_]*$/
      if (!namePattern.test(editingValue.trim())) {
        return t('workflows.workflowList.workflowNameInvalid')
      }
    }

    return ''
  }

  // 处理保存编辑
  const handleSaveEditing = () => {
    if (!editingWorkflowId || editingField === null) return

    // 验证输入是否有效
    const errorMessage = getValidationError()
    if (errorMessage) {
      showError(errorMessage)
      return
    }

    // 使用 workflowId 查找工作流，而不是依赖索引
    const workflow = paginatedWorkflows.find(w => w.workflow_id === editingWorkflowId)
    if (!workflow) {
      showError(t('workflows.workflowList.workflowNotFound'))
      return
    }

    console.log('[DFX:WorkflowsPage] 保存编辑', {
      editingIndex,
      editingField,
      editingValue,
      workflowId: workflow.workflow_id,
      workflowName: workflow.name,
      workflowDesc: workflow.desc,
    })

    // 调用更新工作流的API
    updateWorkflow.mutate(
      {
        workflow_id: editingWorkflowId,
        space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
        name: workflow.name,
        desc: workflow.desc,
        [editingField]: editingValue,
      },
      {
        onSuccess: result => {
          // 检查响应状态码，Code == 200 代表更新成功
          if (result?.code === 200) {
            // 显示成功提示
            showSuccess(t('workflows.workflowList.updateSuccess'))
            // 立即刷新数据 - 根据是否在搜索状态来决定刷新哪个查询
            if (shouldUseSearch) {
              refetchSearch()
            } else {
              refetch()
            }
          } else {
            // 显示失败提示
            showError(result?.message || t('workflows.workflowList.updateFailed'))
          }
          // 重置编辑状态
          handleCancelEditing()
        },
        onError: (error: any) => {
          console.error('更新工作流失败 - 完整错误对象:', error)
          console.error('更新工作流失败 - error的keys:', Object.keys(error || {}))
          console.error('更新工作流失败 - error?.response:', error?.response)
          console.error('更新工作流失败 - error.response的keys:', error?.response ? Object.keys(error.response) : 'undefined')
          console.error('更新工作流失败 - error?.response?.data:', error?.response?.data)
          console.error('更新工作流失败 - error.response.data的keys:', error?.response?.data ? Object.keys(error.response.data) : 'undefined')

          let errorMessage = t('workflows.workflowList.updateError')

          // 尝试多种访问路径来获取detail数据
          let detailData = null

          // 路径1: error?.response?.data?.detail
          if (error?.response?.data?.detail) {
            detailData = error.response.data.detail
            console.log('通过路径1找到detail数据:', detailData)
          }
          // 路径2: error?.response?.data // 检查data是否直接包含detail
          else if (error?.response?.data && Object.keys(error.response.data).includes('detail')) {
            detailData = error.response.data.detail
            console.log('通过路径2找到detail数据:', detailData)
          }
          // 路径3: error?.data // 检查error是否直接包含data
          else if (error?.data?.detail) {
            detailData = error.data.detail
            console.log('通过路径3找到detail数据:', detailData)
          }
          // 路径4: 检查error本身是否有detail属性
          else if ((error as any)?.detail) {
            detailData = (error as any).detail
            console.log('通过路径4找到detail数据:', detailData)
          }

          // 解析后端详细错误信息
          if (detailData) {
            console.log('最终找到detail数据:', detailData)

            if (Array.isArray(detailData)) {
              console.log('detail是数组，长度:', detailData.length)
              // 处理字段验证错误数组
              const fieldErrors = detailData.map((errorDetail: any) => {
                // 处理字段验证错误
                if (errorDetail.loc && errorDetail.msg) {
                  const fieldName = errorDetail.loc[1] || '字段'
                  const friendlyMessage = getFriendlyErrorMessage(errorDetail.msg)
                  return `${fieldName}${friendlyMessage}`
                }
                return errorDetail.msg || errorDetail
              })
              errorMessage = fieldErrors.join('; ')
            } else if (typeof detailData === 'string') {
              // 处理简单的字符串错误
              errorMessage = detailData
            }
          } else if (error?.response?.data?.message) {
            errorMessage = error.response.data.message
          } else if (error?.message) {
            errorMessage = error.message
          }

          // 显示失败提示
          showError(errorMessage)
          // 重置编辑状态
          handleCancelEditing()
        },
      },
    )
  }

  // 获取友好的错误信息
  const getFriendlyErrorMessage = (errorMsg: string): string => {
    const fieldMap: Record<string, string> = {
      name: t('workflows.workflowList.fieldNameName'),
      desc: t('workflows.workflowList.fieldNameDesc'),
    }

    // 检查常见的错误模式
    if (errorMsg.includes('already exists')) {
      return t('workflows.workflowList.errorAlreadyExists')
    }
    if (errorMsg.includes('too long')) {
      return t('workflows.workflowList.errorTooLong')
    }
    if (errorMsg.includes('too short') || errorMsg.includes('minimum length')) {
      return t('workflows.workflowList.errorTooShort')
    }
    if (errorMsg.includes('invalid') || errorMsg.includes('format')) {
      return t('workflows.workflowList.errorInvalidFormat')
    }
    if (errorMsg.includes('required') || errorMsg.includes('field required')) {
      return t('workflows.workflowList.errorRequired')
    }
    if (errorMsg.includes('empty') || errorMsg.includes('blank')) {
      return t('workflows.workflowList.errorEmpty')
    }

    // 字符长度限制信息
    const lengthMatch = errorMsg.match(/(\d+) characters?/)
    if (lengthMatch) {
      return t('workflows.workflowList.errorLengthExceeded', { count: lengthMatch[1] })
    }

    return errorMsg
  }

  // 处理复制工作流
  const handleCopyWorkflow = (workflowId: string, spaceId: string, workflowName: string) => {
    copyWorkflow.mutate(
      {
        workflow_id: workflowId,
        space_id: spaceId,
      },
      {
        onSuccess: result => {
          // 检查响应状态码，Code == 200 代表复制成功
          if (result?.code === 200) {
            // 显示成功提示
            showSuccess(t('workflows.workflowList.copySuccess', { name: workflowName }))
            // 立即刷新数据
            refetch()
          } else {
            // 显示失败提示
            showError(result?.message || t('workflows.workflowList.copyFailed', { name: workflowName }))
          }
        },
        onError: () => {
          // 显示失败提示
          showError(t('workflows.workflowList.copyError', { name: workflowName }))
        },
      },
    )
  }

  // 处理回车键保存
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      // 只有在输入有效时才保存
      if (isInputValid()) {
        handleSaveEditing()
      } else {
        e.preventDefault() // 阻止默认行为
      }
    } else if (e.key === 'Escape') {
      handleCancelEditing()
    }
  }

  // Refresh workflows when returning from canvas
  const location = useLocation()
  useEffect(() => {
    refreshWorkflows()
  }, [location.pathname])

  // 如果编辑中的工作流不在当前列表中，取消编辑状态
  useEffect(() => {
    if (editingWorkflowId && paginatedWorkflows) {
      const editingWorkflow = paginatedWorkflows.find(w => w.workflow_id === editingWorkflowId)
      if (!editingWorkflow) {
        console.log('[useEffect] 编辑的工作流不存在，取消编辑', editingWorkflowId)
        handleCancelEditing()
      }
    }
  }, [paginatedWorkflows]) // 移除 editingWorkflowId 依赖，避免无限循环

  return (
    <div className="space-y-8 p-6 min-h-screen">
      {/* Page header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-900 mb-2">
          {t('workflows.title')}
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-6">{t('workflows.subtitle')}</p>
      </div>

      {/* Search and filters */}
      <div className="flex flex-col lg:flex-row items-start gap-4">
        <div className="flex flex-col sm:flex-row items-center gap-4 flex-1">
          {/* Search */}
          <div className="flex-1">
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-500 transition-colors duration-200" />
              <input
                type="text"
                placeholder={t('workflows.workflowList.searchPlaceholder')}
                value={searchOptimization.searchTerm}
                onChange={e => searchOptimization.setSearchTerm(e.target.value)}
                onCompositionStart={searchOptimization.handleCompositionStart}
                onCompositionEnd={searchOptimization.handleCompositionEnd}
                className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
              />
            </div>
          </div>

          {/* Sort by */}
          <div className="flex items-center gap-2">
            <div className="sm:w-48">
              <select
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
              >
                <option value="name">{t('workflows.workflowList.sortByName')}</option>
                <option value="create_time">{t('workflows.workflowList.sortByCreateTime')}</option>
                <option value="update_time">{t('workflows.workflowList.sortByUpdateTime')}</option>
              </select>
            </div>
            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="p-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white hover:bg-gray-100"
              title={sortOrder === 'asc' ? t('workflows.workflowList.ascending') : t('workflows.workflowList.descending')}
            >
              {sortOrder === 'asc' ? <span className="text-lg font-semibold">↑</span> : <span className="text-lg font-semibold">↓</span>}
            </button>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row items-center gap-4">
          {/* Create Workflow Button */}
          <Link
            to="/dashboard/workflows/new"
            className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
          >
            <Plus className="w-5 h-5" />
            <span>{t('workflows.createWorkflow')}</span>
          </Link>

          {/* Import Workflow Button */}
          <button
            onClick={() => setImportDialogOpen(true)}
            className="inline-flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
          >
            <Upload className="w-5 h-5" />
            <span>{t('workflows.importWorkflow')}</span>
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t('workflows.workflowList.loading')}</p>
        </div>
      )}

      {/* Error state */}
      {error ? (
        <div className="text-center py-12">
          <AlertCircle className="w-16 h-16 text-red-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-900 mb-2">{t('workflows.workflowList.loadFailed')}</h3>
          <p className="text-red-600 mb-6">{t('workflows.workflowList.tryAdjustFilters')}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center space-x-2 bg-red-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-red-700 transform hover:scale-105 transition-all duration-300"
          >
            {t('workflows.workflowList.retry')}
          </button>
        </div>
      ) : null}

      {/* Workflows grid */}
      {!isLoading && !error && paginatedWorkflows && paginatedWorkflows.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {paginatedWorkflows.map((workflow, index) => {
            // 确保workflow对象存在
            if (!workflow || !workflow.workflow_id) {
              return null
            }

            return (
              <div
                key={workflow.workflow_id}
                className="group bg-white rounded-2xl shadow-sm hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-2 border border-gray-100 overflow-hidden"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {/* Gradient top border */}
                <div className="h-1 bg-gradient-to-r from-blue-500 to-indigo-600" />

                {/* Workflow header */}
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3 overflow-hidden max-w-[calc(100%-20px)]">
                      <div className="w-12 h-12 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 border border-blue-200">
                        <WorkflowIcon className="w-6 h-6 text-blue-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        {editingWorkflowId === workflow.workflow_id && editingField === 'name' ? (
                          <div className="space-y-1">
                            <div className="flex items-center gap-1">
                              <input
                                type="text"
                                value={editingValue}
                                onChange={handleInputChange}
                                onKeyDown={handleKeyDown}
                                className={`flex-1 px-3 py-1 border-2 rounded-lg focus:outline-none focus:ring-1 ${
                                  editingValue && !isInputValid() ? 'border-red-500 focus:ring-red-500' : 'border-blue-500 focus:ring-blue-500'
                                }`}
                                placeholder={t('workflows.workflowList.editNamePlaceholder')}
                                maxLength={120}
                              />
                              <button
                                onClick={handleSaveEditing}
                                disabled={!isInputValid()}
                                className={`p-1.5 rounded flex items-center justify-center ${
                                  isInputValid() ? 'text-green-600 hover:bg-green-100' : 'text-gray-300 cursor-not-allowed'
                                }`}
                                title={t('common.tooltips.save')}
                              >
                                <Check className="w-4 h-4 flex-shrink-0" />
                              </button>
                              <button
                                onClick={handleCancelEditing}
                                className="p-1.5 text-red-600 hover:bg-gray-100 rounded flex items-center justify-center"
                                title={t('common.tooltips.cancel')}
                              >
                                <X className="w-4 h-4 flex-shrink-0" />
                              </button>
                            </div>
                            <div className="flex justify-between items-center">
                              <div className={`text-xs ${editingValue && !isInputValid() ? 'text-red-500' : 'text-gray-500'}`}>
                                {editingValue && !isInputValid()
                                  ? t('workflows.workflowList.formatError')
                                  : t('workflows.workflowList.formatHint')}
                              </div>
                              <div className="text-xs text-gray-500 text-right">{editingValue.length}/100</div>
                            </div>
                          </div>
                        ) : (
                          <h3
                            className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800 cursor-pointer hover:text-blue-700 transition-colors duration-200 overflow-hidden text-ellipsis whitespace-nowrap"
                            onClick={() => handleStartEditing(workflow.workflow_id, 'name', workflow.name)}
                            title={workflow.name}
                          >
                            {workflow.name}
                          </h3>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  {editingWorkflowId === workflow.workflow_id && editingField === 'desc' ? (
                    <div className="mb-4 space-y-2">
                      <div className="relative">
                        <textarea
                          value={editingValue}
                          onChange={handleInputChange}
                          onKeyDown={handleKeyDown}
                          className="w-full px-3 py-2 pr-20 border-2 border-blue-500 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[60px] resize-none"
                          placeholder={t('workflows.workflowList.editDescriptionPlaceholder')}
                          maxLength={500}
                        />
                        <div className="absolute right-2 bottom-2 flex space-x-1">
                          <button
                            onClick={handleSaveEditing}
                            disabled={!isInputValid()}
                            className={`p-1.5 rounded flex items-center justify-center ${
                              isInputValid() ? 'text-green-600 hover:bg-green-100' : 'text-gray-300 cursor-not-allowed'
                            }`}
                            title={t('common.tooltips.save')}
                          >
                            <Check className="w-4 h-4 flex-shrink-0" />
                          </button>
                          <button
                            onClick={handleCancelEditing}
                            className="p-1.5 text-gray-600 hover:bg-gray-100 rounded hover:text-red-600 flex items-center justify-center"
                            title={t('common.tooltips.cancel')}
                          >
                            <X className="w-4 h-4 flex-shrink-0" />
                          </button>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 text-right">{editingValue.length}/500</div>
                    </div>
                  ) : (
                    <p
                      className="text-sm text-gray-600 mb-4 leading-relaxed cursor-pointer hover:text-blue-700 transition-colors duration-200 overflow-hidden text-ellipsis whitespace-nowrap max-w-[200px]"
                      onClick={() => handleStartEditing(workflow.workflow_id, 'desc', workflow.desc)}
                      title={workflow.desc}
                    >
                      {workflow.desc}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-blue-50 border-t border-gray-100">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Link
                        to={`/dashboard/workflows/editor/${workflow.workflow_id}?spaceId=${workflow.space_id || ENV_CONFIG.DEFAULT_SPACE_ID}`}
                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
                        title={t('workflows.workflowList.editWorkflow')}
                      >
                        <Edit className="w-4 h-4" />
                      </Link>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
                        title={t('workflows.workflowList.copyWorkflow')}
                        onClick={() => handleCopyWorkflow(workflow.workflow_id, workflow.space_id, workflow.name)}
                        disabled={copyWorkflow.isLoading}
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200"
                        onClick={() => handleDeleteWorkflow(workflow.workflow_id, workflow.name, workflow.workflow_version)}
                        title={t('workflows.workflowList.deleteWorkflow')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && paginatedWorkflows && paginatedWorkflows.length === 0 && (
        <div className="text-center py-16">
          <div className="w-24 h-24 bg-gradient-to-r from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-6">
            <WorkflowIcon className="w-12 h-12 text-gray-400" />
          </div>
          <h3 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-gray-900 mb-3">
            {t('workflows.workflowList.noWorkflowsFound')}
          </h3>
          <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
            {searchOptimization.searchTerm ? t('workflows.workflowList.tryAdjustFilters') : t('workflows.workflowList.createFirstWorkflow')}
          </p>
          {!searchOptimization.searchTerm && (
            <Link
              to="/dashboard/workflows/new"
              className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
            >
              <Plus className="w-5 h-5" />
              <span>{t('workflows.createWorkflow')}</span>
            </Link>
          )}
        </div>
      )}

      {/* Pagination */}
      {paginatedWorkflows && paginatedWorkflows.length > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">{t('workflows.workflowList.showPerPage')}:</span>
            <select
              value={page_size}
              onChange={e => {
                setPageSize(Number(e.target.value))
                setCurrentPage(1) // 重置到第一页
              }}
              className="px-3 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 shadow-sm pagination-select"
            >
              <option value={9}>9{t('common.pagination.items')}</option>
              <option value={18}>18{t('common.pagination.items')}</option>
              <option value={30}>30{t('common.pagination.items')}</option>
              <option value={60}>60{t('common.pagination.items')}</option>
            </select>
            <span className="text-sm text-gray-600">{t('workflows.workflowList.totalRecords', { total: totalItems })}</span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className={`p-2 rounded-lg ${currentPage === 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-100'}`}
            >
              <ChevronLeft className="w-5 h-5" />
            </button>

            <div className="flex items-center space-x-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                // 计算要显示的页码
                let pageNum: number
                if (totalPages <= 5) {
                  pageNum = i + 1
                } else if (currentPage <= 3) {
                  pageNum = i + 1
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i
                } else {
                  pageNum = currentPage - 2 + i
                }

                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`w-10 h-10 rounded-lg ${currentPage === pageNum ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>

            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className={`p-2 rounded-lg ${currentPage === totalPages ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-100'}`}
            >
              <ChevronRight className="w-5 h-5" />
            </button>

            <span className="text-sm text-gray-600 ml-4">{t('workflows.workflowList.pageInfo', { current: currentPage, total: totalPages })}</span>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={cancelDeleteWorkflow}
        onConfirm={handleDeleteConfirm}
        itemType="workflow"
        itemName={deleteDialog.workflowName}
        isLoading={deleteWorkflow.isLoading}
      />

      {/* Import Workflow Dialog */}
      <ImportWorkflowDialog
        isOpen={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
        onSuccess={handleImportSuccess}
        spaceId={user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID}
      />

      {/* Unified Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </div>
  )
}

export default WorkflowsPage
