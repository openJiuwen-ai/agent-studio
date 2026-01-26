import React, { useState, useEffect, useRef } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Brain, Plus, Search, Edit, Trash2, Copy, ChevronLeft, ChevronRight, AlertCircle, Check, X, Upload, Download, AlertTriangle } from 'lucide-react'
import { AgentService, useAgents, useUpdateAgent, useCopyAgent, useSearchAgents, useModels, AgentSortBy, AgentSortOrder } from '@test-agentstudio/api-client'
import AgentIcon from '@/assets/icons/agent.svg?react'
import { getDefaultSpaceId } from '../../utils/spaceUtils'
import { useAuthStore } from '../../stores/useAuthStore'
import { useQueryClient } from 'react-query'
import DeleteConfirmationDialog from '../../components/Common/DeleteConfirmationDialog'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import { CircularProgress } from '@mui/material'

interface SearchModel {
  model_info: {
    model_name: string
  }
}

interface Agent {
  agent_id: string
  agent_name: string
  description: string
  icon: string
  status: string
  model_name: string
  lastActive: string
  usage_count: number
  tags: string[]
  create_time: number
  api_endpoint: string
  agent_version: string
  agent_type: string
  model?: SearchModel
}

const AgentsPage: React.FC = () => {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [sortBy, setSortBy] = useState<AgentSortBy>(AgentSortBy.update_time)
  const [sortOrder, setSortOrder] = useState<AgentSortOrder>(AgentSortOrder.desc)
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(9)

  // 搜索相关状态
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState<string>('')
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)
  const lastPathnameRef = useRef<string>('')
  const refetchAgentsRef = useRef<(() => void) | null>(null)

  const [error, setError] = useState<string>('')
  const [deleteDialog, setDeleteDialog] = useState({ isOpen: false, agentId: '', agentName: '' })
  const [isDeleting, setIsDeleting] = useState(false)
  const { snackbar, showSuccess, showError, showWarning, closeSnackbar } = useUnifiedSnackbar()

  // 导入导出相关状态
  const [isImporting, setIsImporting] = useState(false)
  const [importConflict, setImportConflict] = useState<{ isOpen: boolean; agentName: string; data: any; isZip?: boolean } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 编辑状态相关
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null)
  const [editingAgentField, setEditingAgentField] = useState<'name' | 'description' | null>(null)
  const [editingAgentName, setEditingAgentName] = useState<string>('')
  const [editingAgentDescription, setEditingAgentDescription] = useState<string>('')
  const [isEditing, setIsEditing] = useState(false)

  // 获取更新智能体的hook
  const { mutate: updateAgent, isLoading: isUpdating } = useUpdateAgent()

  // 获取复制智能体的hook
  const { mutate: copyAgent, isLoading: isCopying } = useCopyAgent()

  // 获取React Query客户端
  const queryClient = useQueryClient()

  // 获取模型列表，用于检查模型是否可用
  const { data: modelsData, isLoading: modelsLoading } = useModels({
    spaceId: user?.spaceId || getDefaultSpaceId(),
    is_active: true,
    size: 100, // 后端限制最大为100
  })

  // 创建可用模型名称集合，用于快速查找
  const availableModelNames = new Set(modelsData?.items?.map(model => model.name) || [])

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
  const {
    data: agentsResponse,
    isLoading: agentsLoading,
    error: agentsError,
    refetch: refetchAgents,
  } = debouncedSearchTerm.trim() !== ''
    ? useSearchAgents({
        space_id: user?.spaceId || getDefaultSpaceId(),
        search_term: debouncedSearchTerm.trim(),
        sort_by: sortBy,
        sort_order: sortOrder,
        page: currentPage,
        page_size: pageSize,
      })
    : useAgents({
        space_id: user?.spaceId || getDefaultSpaceId(),
        page: currentPage,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      })

  // 更新 refetch 函数的引用
  useEffect(() => {
    refetchAgentsRef.current = refetchAgents
  }, [refetchAgents])

  // 当排序条件或搜索词变化时，重置到第一页
  useEffect(() => {
    setCurrentPage(1)
  }, [sortBy, sortOrder, debouncedSearchTerm])

  // 每次进入页面时（组件挂载或路由变化时）自动刷新列表数据
  useEffect(() => {
    // 当路由路径是智能体列表页时，刷新数据
    // 这样可以确保从编辑页返回时自动刷新列表
    if (location.pathname === '/dashboard/agents') {
      // 如果路径发生变化（从其他页面返回）或首次挂载，则刷新数据
      if (lastPathnameRef.current !== location.pathname) {
        // 强制刷新：先使缓存失效（忽略 staleTime），然后调用 refetch
        // 使所有相关的查询缓存失效，确保强制刷新
        queryClient.invalidateQueries(['agents', 'api', 'list'], { exact: false })
        queryClient.invalidateQueries(['agents', 'search'], { exact: false })
        // 调用 refetch 立即刷新数据（使用 ref 避免依赖问题）
        if (refetchAgentsRef.current) {
          refetchAgentsRef.current()
        }
        lastPathnameRef.current = location.pathname
      }
    } else {
      // 离开智能体列表页时，重置跟踪的路径，以便下次进入时能触发刷新
      lastPathnameRef.current = ''
    }
  }, [location.pathname, queryClient])

  // 从响应中派生状态
  const allAgents = agentsResponse?.data?.agent_items || []
  const pagination = agentsResponse?.data?.pagination
  const totalItems = pagination?.total || 0
  const totalPages = pagination?.total_pages || 1

  // 直接使用后端返回的智能体数据，后端已处理分页和排序
  const agents = allAgents
  const paginatedAgents = agents

  // 处理agentsError
  useEffect(() => {
    if (agentsError) {
      const errorMessage = `${t('common.messages.error')}: ${agentsError instanceof Error ? agentsError.message : t('common.messages.unknownError')}`
      showError(errorMessage)
      setError(errorMessage)
    } else {
      setError('')
    }
  }, [agentsError]) // 移除 showError 和 t 依赖，避免无限循环

  // 打开删除确认对话框
  const handleOpenDeleteDialog = (agentId: string, agentName: string) => {
    setDeleteDialog({ isOpen: true, agentId, agentName })
  }

  // 关闭删除确认对话框
  const handleCloseDeleteDialog = () => {
    setDeleteDialog({ isOpen: false, agentId: '', agentName: '' })
  }

  // 删除智能体
  const handleDeleteAgent = async () => {
    if (!deleteDialog.agentId) return

    setIsDeleting(true)
    try {
      // 调用后端API删除智能体
      const response = await AgentService.deleteAgent({
        space_id: getDefaultSpaceId(),
        agent_id: deleteDialog.agentId,
      })

      if (response.code === 200) {
        // 删除成功，通知React Query刷新缓存
        const spaceId = user?.spaceId || getDefaultSpaceId()

        // Invalidate all agent list queries (exact: false to match all queries starting with ['agents', 'api', 'list'])
        await queryClient.invalidateQueries({
          queryKey: ['agents', 'api', 'list'],
          exact: false,
        })

        // Invalidate all agent search queries (exact: false to match all queries starting with ['agents', 'search'])
        await queryClient.invalidateQueries({
          queryKey: ['agents', 'search'],
          exact: false,
        })

        // 使用refetch方法直接刷新数据
        await refetchAgents()

        // 显示成功提示
        showSuccess(t('common.messages.agentDeleteSuccess'))
      } else {
        // API调用失败时显示错误信息
        console.error('删除智能体失败:', response)
        showError(`${t('common.messages.agentDeleteFailed')}: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (err) {
      // API调用异常时显示错误信息
      const error = err as Error
      console.error('删除智能体异常:', error)
      showError(`${t('common.messages.agentDeleteFailed')}: ${error.message || t('common.messages.unknownError')}`)
    } finally {
      setIsDeleting(false)
      handleCloseDeleteDialog()
    }
  }

  // 复制智能体
  const handleCopyAgent = (agentId: string, agentName: string) => {
    copyAgent(
      {
        space_id: getDefaultSpaceId(),
        agent_id: agentId,
      },
      {
        onSuccess: response => {
          if (response.code === 200) {
            // 复制成功，通知React Query刷新缓存
            const spaceId = user?.spaceId || getDefaultSpaceId()
            queryClient.invalidateQueries(['agents', 'api', 'list', spaceId])

            // 使用refetch方法直接刷新数据
            refetchAgents()

            showSuccess(`${t('common.messages.agentCopySuccess')}: "${agentName}"`)
          } else {
            showError(`${t('common.messages.agentCopyFailed')}: ${response.message || t('common.messages.unknownError')}`)
          }
        },
        onError: err => {
          const error = err as Error
          console.error('复制智能体失败:', error)
          showError(`${t('common.messages.agentCopyFailed')}: ${error.message || t('common.messages.unknownError')}`)
        },
      },
    )
  }

  // 导出智能体
  const handleExportAgent = async (agentId: string, agentName: string) => {
    try {
      const response = await AgentService.exportAgent({
        space_id: user?.spaceId || getDefaultSpaceId(),
        agent_id: agentId,
      })

      if (response.isBlob) {
        // 处理二进制文件(ZIP)下载
        const url = window.URL.createObjectURL(response.blob)
        const a = document.createElement('a')
        a.href = url
        a.download = response.filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        showSuccess(t('agents.agentList.messages.exportSuccess'))
      } else if (response.code === 200 && response.data) {
        // 处理JSON下载
        // 格式化时间戳 YYYYMMDDHHmmss
        const now = new Date()
        const timestamp = now.getFullYear().toString() +
          (now.getMonth() + 1).toString().padStart(2, '0') +
          now.getDate().toString().padStart(2, '0') +
          now.getHours().toString().padStart(2, '0') +
          now.getMinutes().toString().padStart(2, '0') +
          now.getSeconds().toString().padStart(2, '0')
        
        const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        // 使用短横线连接，保持一致性
        a.download = `${agentName}-export-${timestamp}.json`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        showSuccess('智能体导出成功')
      } else {
        showError(`导出失败: ${response.message || '未知错误'}`)
      }
    } catch (error) {
      console.error('导出异常:', error)
      showError(`导出异常: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 执行导入操作
  const executeImport = async (importData: any, overwrite: boolean) => {
    try {
      setIsImporting(true)
      const response = await AgentService.importAgent({
        space_id: user?.spaceId || getDefaultSpaceId(),
        import_data: importData,
        overwrite: overwrite,
      })

      if (response.code === 200) {
        // 检查是否有警告信息
        const warnings = response.data?.warnings
        if (warnings && Array.isArray(warnings) && warnings.length > 0) {
          const warningMsg = warnings.join('; ')
          showWarning(`警告: ${warningMsg}`, 10000)
        } else {
          showSuccess(overwrite ? '智能体覆盖导入成功' : '智能体导入成功')
        }
        
        queryClient.invalidateQueries(['agents', 'api', 'list'], { exact: false })
        refetchAgents()
      } else {
        showError(`导入失败: ${response.message || '未知错误'}`)
      }
    } catch (error) {
      console.error('导入异常:', error)
      showError(`导入异常: ${error instanceof Error ? error.message : '文件解析失败'}`)
    } finally {
      setIsImporting(false)
      setImportConflict(null)
    }
  }

  // 触发文件选择
  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  // 处理文件选择导入
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 检查文件类型
    const isZip = file.name.endsWith('.zip') || file.type.includes('zip') || file.type.includes('compressed')
    const isJson = file.name.endsWith('.json') || file.type.includes('json')

    if (!isZip && !isJson) {
      event.target.value = ''
      showError(t('agents.agentList.messages.invalidFile'))
      return
    }

    event.target.value = ''

    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        let importData: any
        
        if (isZip) {
          // 读取ZIP文件中的JSON配置
          const arrayBuffer = e.target?.result as ArrayBuffer
          const zip = new (await import('jszip')).default()
          const zipContent = await zip.loadAsync(arrayBuffer)
          
          // 查找配置文件
          let configFile: any = null
          for (const filename of Object.keys(zipContent.files)) {
            if (filename.endsWith('.json') && filename.includes('-export-')) {
              configFile = zipContent.files[filename]
              break
            }
          }
          
          // 如果没找到带-export-的，找第一个JSON文件
          if (!configFile) {
            for (const filename of Object.keys(zipContent.files)) {
              if (filename.endsWith('.json')) {
                configFile = zipContent.files[filename]
                break
              }
            }
          }
          
          if (!configFile) {
            throw new Error('ZIP文件中未找到配置文件')
          }
          
          const jsonContent = await configFile.async('text')
          importData = JSON.parse(jsonContent)
        } else {
          // JSON文件直接解析
          const content = e.target?.result as string
          importData = JSON.parse(content)
        }

        if (!importData.agent || !importData.dependencies) {
          throw new Error('无效的导入文件格式')
        }

        const agentId = importData.agent.agent_id
        const spaceId = user?.spaceId || getDefaultSpaceId()

        // 检查智能体是否存在
        try {
          const checkRes = await AgentService.getAgentDetail({
            space_id: spaceId,
            agent_id: agentId,
          })

          if (checkRes.code === 200) {
             setImportConflict({
               isOpen: true,
               agentName: importData.agent.agent_name,
               data: isZip ? file : importData,
             })
          } else {
             executeImport(isZip ? file : importData, false)
          }
        } catch (err) {
          executeImport(isZip ? file : importData, false)
        }

      } catch (error) {
        console.error('文件解析异常:', error)
        showError(`文件解析异常: ${error instanceof Error ? error.message : '未知错误'}`)
      }
    }
    
    if (isZip) {
      reader.readAsArrayBuffer(file)
    } else {
      reader.readAsText(file)
    }
  }

  // 处理点击进入编辑状态
  const handleStartEditing = (agent: Agent, field: 'name' | 'description') => {
    setEditingAgentId(agent.agent_id)
    setEditingAgentField(field)
    setEditingAgentName(agent.agent_name)
    setEditingAgentDescription(agent.description)
    setIsEditing(true)

    // 短暂延迟后聚焦到输入框
    setTimeout(() => {
      const inputElement = document.getElementById(`edit-input-${agent.agent_id}-${field}`)
      if (inputElement) {
        inputElement.focus()
        // 全选输入框内容
        if (inputElement instanceof HTMLInputElement || inputElement instanceof HTMLTextAreaElement) {
          inputElement.select()
        }
      }
    }, 100)
  }

  // 处理保存编辑
  const handleSaveEditing = () => {
    if (!editingAgentId || !editingAgentField) return

    const updateData = {
      agent_id: editingAgentId,
      agent_name: editingAgentName,
      space_id: user?.spaceId || getDefaultSpaceId(),
      description: editingAgentDescription,
      icon: agents.find(a => a.agent_id === editingAgentId)?.icon || '',
      agent_type: agents.find(a => a.agent_id === editingAgentId)?.agent_type || '',
    }

    updateAgent(updateData, {
      onSuccess: response => {
        if (response.code === 200) {
          // 更新成功，刷新智能体列表
          const spaceId = user?.spaceId || getDefaultSpaceId()
          queryClient.invalidateQueries(['agents', 'api', 'list', spaceId])

          // 显示成功提示
          showSuccess(t('common.messages.agentUpdateSuccess'))
        } else {
          // API调用失败时显示错误信息
          showError(`${t('common.messages.error')}: ${response.message || t('common.messages.unknownError')}`)
        }
      },
      onError: err => {
        const error = err as Error
        // API调用异常时显示错误信息
        showError(`${t('common.messages.error')}: ${error.message || t('common.messages.unknownError')}`)
      },
      onSettled: () => {
        // 无论成功失败，都退出编辑状态
        setIsEditing(false)
        setEditingAgentId(null)
        setEditingAgentField(null)
      },
    })
  }

  // 处理取消编辑
  const handleCancelEditing = () => {
    setIsEditing(false)
    setEditingAgentId(null)
    setEditingAgentField(null)
  }

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      // 按下Enter键保存编辑，不触发默认行为（表单提交）
      e.preventDefault()
      handleSaveEditing()
    } else if (e.key === 'Escape') {
      // 按下Escape键取消编辑
      handleCancelEditing()
    }
  }

  return (
    <div className="space-y-8 p-6 min-h-full">
      {/* 隐藏的文件输入框 */}
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        accept=".json,.zip"
        onChange={handleFileChange}
      />

      {/* Page header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-900 mb-2">{t('agents.title')}</h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-6">{t('agents.subtitle')}</p>
      </div>

      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row items-center gap-4">
        {/* Search */}
        <div className="flex-1">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-500 transition-colors duration-200" />
            <input
              type="text"
              placeholder={t('agents.agentList.searchPlaceholder')}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-10 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 hover:text-gray-600 transition-colors duration-200"
                title={t('agents.agentList.clearSearch')}
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Sort by */}
        <div className="flex items-center gap-2">
          <div className="sm:w-48">
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as AgentSortBy)}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
            >
              <option value={AgentSortBy.name}>{t('agents.agentList.sortByName')}</option>
              <option value={AgentSortBy.create_time}>{t('agents.agentList.sortByCreated')}</option>
              <option value={AgentSortBy.update_time}>{t('agents.agentList.sortByUpdated')}</option>
            </select>
          </div>

          {/* Sort order toggle */}
          <button
            onClick={() => setSortOrder(sortOrder === AgentSortOrder.asc ? AgentSortOrder.desc : AgentSortOrder.asc)}
            className="p-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white hover:bg-gray-100"
            title={sortOrder === AgentSortOrder.asc ? t('agents.agentList.ascending') : t('agents.agentList.descending')}
          >
            {sortOrder === 'asc' ? <span className="text-lg font-semibold">↑</span> : <span className="text-lg font-semibold">↓</span>}
          </button>
        </div>

        {/* Import Agent Button */}
        <button
          className="inline-flex items-center space-x-2 bg-white text-gray-700 border border-gray-300 px-6 py-3 rounded-xl font-semibold hover:bg-gray-50 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-md"
          onClick={handleImportClick}
          disabled={isImporting}
        >
          {isImporting ? <CircularProgress size={20} /> : <Upload className="w-5 h-5" />}
          <span>导入</span>
        </button>

        {/* Create Agent Button */}
        <button
          className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
          onClick={() => {
            // 添加点击日志来调试
            console.log('顶部创建智能体按钮被点击')
            navigate('/dashboard/agents/new')
          }}
        >
          <Plus className="w-5 h-5" />
          <span>{t('agents.createAgent')}</span>
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
            <span className="text-red-800 font-medium">{error}</span>
          </div>
        </div>
      )}

      {/* Agents grid */}
      {agentsLoading ? (
        <div className="flex flex-col items-center justify-center h-64">
          <CircularProgress />
          <div className="mt-3 text-sm text-gray-600">{t('agents.agentList.loading')}</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {paginatedAgents.map((agent: Agent, index: number) => (
            <div
              key={agent.agent_id}
              className="group bg-white rounded-2xl shadow-sm hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-2 border border-gray-100 overflow-hidden"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              {/* Gradient top border */}
              <div className="h-1 bg-gradient-to-r from-blue-500 to-indigo-600" />

              {/* Agent header */}
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3 w-full">
                    <div className="text-4xl group-hover:scale-110 transition-transform duration-300">{agent.icon}</div>
                    <div className="min-w-0 flex-1 overflow-hidden">
                      {isEditing && editingAgentId === agent.agent_id && editingAgentField === 'name' ? (
                        <div className="relative">
                          <input
                            id={`edit-input-${agent.agent_id}-name`}
                            type="text"
                            value={editingAgentName}
                            onChange={e => setEditingAgentName(e.target.value)}
                            onKeyDown={handleKeyDown}
                            className="w-full px-3 py-1 border-2 border-blue-500 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                            placeholder={t('agents.agentList.editNamePlaceholder')}
                            maxLength={100}
                          />
                          <div className="absolute -bottom-5 right-0 text-xs text-gray-500">
                            {editingAgentName.length}
                            {t('agents.agentList.characterCount.name')}
                          </div>
                          <div className="absolute right-1 top-1/2 transform -translate-y-1/2 flex space-x-1">
                            <button
                              onClick={handleSaveEditing}
                              disabled={isUpdating}
                              className="p-1 text-green-600 hover:bg-green-100 rounded"
                              title={t('common.tooltips.save')}
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button onClick={handleCancelEditing} className="p-1 text-gray-600 hover:bg-gray-100 rounded" title={t('common.tooltips.cancel')}>
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ) : (
                        <h3
                          className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800 cursor-pointer hover:text-blue-600 transition-colors duration-200 overflow-hidden text-ellipsis whitespace-nowrap max-w-[calc(100%-20px)]"
                          onClick={() => handleStartEditing(agent, 'name')}
                          title={t('common.tooltips.clickToEditName')}
                        >
                          {agent.agent_name}
                        </h3>
                      )}
                      <p className="text-sm font-bold text-blue-600">
                        {t('agents.agentList.model')}:{' '}
                        {(() => {
                          const modelName = agent.model_name === 'no model' ? null : agent.model_name || agent.model?.model_info.model_name || null
                          if (!modelName) {
                            return t('agents.agentList.noModel')
                          }
                          if (modelsLoading && !modelsData) {
                            return <span className="text-gray-500">{t('agents.agentList.modelLoading')}</span>
                          }
                          const isModelAvailable = availableModelNames.has(modelName)
                          if (!isModelAvailable) {
                            return (
                              <span className="text-red-600" title={t('agents.agentList.modelDisabledTooltip')}>
                                {modelName} <span className="text-xs">{t('agents.agentList.modelDisabledTag')}</span>
                              </span>
                            )
                          }
                          return modelName
                        })()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Description */}
                {isEditing && editingAgentId === agent.agent_id && editingAgentField === 'description' ? (
                  <div className="relative mb-4">
                    <textarea
                      id={`edit-input-${agent.agent_id}-description`}
                      value={editingAgentDescription}
                      onChange={e => setEditingAgentDescription(e.target.value)}
                      onKeyDown={handleKeyDown}
                      className="w-full px-3 py-2 border-2 border-blue-500 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[60px]"
                      placeholder={t('agents.agentList.editDescriptionPlaceholder')}
                      maxLength={500}
                    />
                    <div className="absolute -bottom-5 right-2 text-xs text-gray-500">
                      {editingAgentDescription.length}
                      {t('agents.agentList.characterCount.description')}
                    </div>
                    <div className="absolute right-2 bottom-2 flex space-x-1">
                      <button
                        onClick={handleSaveEditing}
                        disabled={isUpdating}
                        className="p-1 text-green-600 hover:bg-green-100 rounded"
                        title={t('common.tooltips.save')}
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button onClick={handleCancelEditing} className="p-1 text-gray-600 hover:bg-gray-100 rounded" title={t('common.tooltips.cancel')}>
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <p
                    className="text-sm text-gray-600 mb-4 leading-relaxed cursor-pointer hover:text-blue-600 transition-colors duration-200 overflow-hidden text-ellipsis whitespace-nowrap max-w-[calc(100%-20px)]"
                    onClick={() => handleStartEditing(agent, 'description')}
                    title={t('common.tooltips.clickToEditDescription')}
                  >
                    {agent.description}
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-blue-50 border-t border-gray-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Link
                      to={`/dashboard/agents/${agent.agent_id}`}
                      state={{ botId: agent.agent_id }}
                      className="text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
                      title={t('common.tooltips.editAgent')}
                    >
                      <Edit className="w-4 h-4" />
                    </Link>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
                      title="导出智能体"
                      onClick={() => handleExportAgent(agent.agent_id, agent.agent_name)}
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    <button
                      className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
                      title={t('common.tooltips.copyAgent')}
                      onClick={() => handleCopyAgent(agent.agent_id, agent.agent_name)}
                      disabled={isCopying}
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    <button
                      className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200"
                      onClick={() => handleOpenDeleteDialog(agent.agent_id, agent.agent_name)}
                      title={t('common.tooltips.deleteAgent')}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!agentsLoading && agents.length === 0 && (
        <div className="text-center py-16">
          <div className="w-24 h-24 bg-gradient-to-r from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-6">
            <AgentIcon className="w-12 h-12 text-gray-400" />
          </div>
          <h3 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-gray-900 mb-3">
            {debouncedSearchTerm.trim() ? t('agents.agentList.searchNoAgentsFoundTitle') : t('agents.agentList.noAgentsFound')}
          </h3>
          <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
            {debouncedSearchTerm.trim()
              ? t('agents.agentList.searchNoAgentsFoundDesc', { keyword: debouncedSearchTerm.trim() })
              : t('agents.agentList.createFirstAgent')}
          </p>
          <div className="flex justify-center space-x-4">
            <button
              className="inline-flex items-center space-x-2 bg-white text-gray-700 border border-gray-300 px-6 py-3 rounded-xl font-semibold hover:bg-gray-50 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-md"
              onClick={handleImportClick}
              disabled={isImporting}
            >
              {isImporting ? <CircularProgress size={20} /> : <Upload className="w-5 h-5" />}
              <span>导入</span>
            </button>
            <button
              className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
              onClick={() => {
                console.log('创建智能体按钮被点击，搜索词:', debouncedSearchTerm)
                navigate('/dashboard/agents/new')
              }}
            >
              <Plus className="w-5 h-5" />
              <span>{debouncedSearchTerm.trim() ? '创建新智能体' : t('agents.agentList.createFirst')}</span>
            </button>
          </div>
        </div>
      )}

      {/* Pagination */}
      {agents.length > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">{t('common.pagination.pageSize')}:</span>
            <select
              value={pageSize}
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
            <span className="text-sm text-gray-600">{t('common.pagination.total', { total: totalItems })}</span>
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
                    key={i}
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

            <span className="text-sm text-gray-600 ml-4">{t('common.pagination.page', { current: currentPage, total: totalPages })}</span>
          </div>
        </div>
      )}

      {/* 删除确认对话框 */}
      <DeleteConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={handleCloseDeleteDialog}
        onConfirm={handleDeleteAgent}
        itemType="agent"
        itemName={deleteDialog.agentName}
        isLoading={isDeleting}
      />

      {/* 导入冲突确认对话框 */}
      {importConflict && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={() => setImportConflict(null)} />
          <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 transform transition-all">
             {/* Close */}
             <button onClick={() => setImportConflict(null)} className="absolute top-6 right-6 text-gray-400 hover:text-gray-600">
               <X className="w-6 h-6" />
             </button>
             {/* Icon */}
             <div className="flex justify-center mb-6">
               <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center">
                 <AlertTriangle className="w-8 h-8 text-orange-600" />
               </div>
             </div>
             {/* Content */}
             <div className="text-center mb-8">
               <h3 className="text-2xl font-bold text-gray-900 mb-4">智能体已存在</h3>
               <p className="text-gray-600 text-lg leading-relaxed">
                 当前空间下已存在智能体 "{importConflict.agentName}",
                 <br/>
                 您希望如何处理？
               </p>
             </div>
             {/* Actions */}
             <div className="flex flex-col gap-3">
               <button
                 onClick={() => executeImport(importConflict.data, true)}
                 className="w-full px-6 py-3 bg-orange-600 text-white rounded-xl hover:bg-orange-700 font-medium transition-all"
               >
                 覆盖现有智能体 (Overwrite)
               </button>
               <button
                 onClick={() => executeImport(importConflict.data, false)}
                 className="w-full px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-medium transition-all"
               >
                 创建副本 (Create Copy)
               </button>
               <button
                 onClick={() => setImportConflict(null)}
                 className="w-full px-6 py-3 border-2 border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition-all"
               >
                 取消
               </button>
             </div>
          </div>
        </div>
      )}

      {/* Unified Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </div>
  )
}

export default AgentsPage
