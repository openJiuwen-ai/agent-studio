import React, { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import PromptTemplateIcon from '@/assets/icons/promptTemplate.svg?react'
import { Plus, Search, Edit, Trash2, Copy, Tag, Key, AlertCircle, RefreshCw, Check, Grid, List, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { IconButton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Tooltip } from '@mui/material'
import { PromptBasicInfoDialog, AssociationsDialog, ConditionalTooltip, DeletePromptDialog, Pagination } from '@/components/Prompts'
import { ApiError, PromptService, type Prompt, type RelationObj } from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore'
import { ENV_CONFIG } from '@/config/environment'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { copyToClipboard, handleRelationObjNavigate } from '@/utils/prompts/utils'

const PromptsPage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const workspaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  const [searchTerm, setSearchTerm] = useState('')
  const [sortOrder, setSortOrder] = useState<{ [key: string]: 'asc' | 'desc' | 'default' }>({})
  const [basicInfoDialogOpen, setBasicInfoDialogOpen] = useState(false)
  const [prompts, setPrompts] = useState<Prompt[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [pageSize, setPageSize] = useState(9)
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card') // 视图模式
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [promptToDelete, setPromptToDelete] = useState<Prompt | null>(null)
  const { snackbar, showSnackbar, showError, closeSnackbar, setSnackbar } = useUnifiedSnackbar()
  const hasInitialLoaded = useRef(false)
  const loadingRef = useRef(false)
  const lastLoadTime = useRef(0)

  // 关联对象对话框状态
  const [associationsDialogOpen, setAssociationsDialogOpen] = useState(false)
  const [selectedAssociations, setSelectedAssociations] = useState<RelationObj[]>([])
  const [selectedPromptName, setSelectedPromptName] = useState('')

  // 获取提示词列表
  const loadPrompts = async (page = 1, size = pageSize, orderBy?: string, asc?: boolean) => {
    // 防止短时间内重复调用（100ms内）
    const now = Date.now()
    if (now - lastLoadTime.current < 100) {
      console.log('Skipping duplicate loadPrompts call - too soon')
      return
    }

    // 防止并发调用
    if (loadingRef.current) {
      console.log('Skipping duplicate loadPrompts call - already loading')
      return
    }

    lastLoadTime.current = now
    loadingRef.current = true
    setLoading(true)
    setError(null)

    const params: any = {
      page,
      pageSize: size,
      search: searchTerm || undefined,
    }

    // 如果用户在搜索框输入了内容，则添加key_word参数
    if (searchTerm && searchTerm.trim()) {
      params.key_word = searchTerm.trim()
    }

    // 添加排序参数
    if (orderBy) {
      params.order_by = orderBy
    }
    if (asc !== undefined) {
      params.asc = asc
    }

    try {
      const response = await PromptService.getPrompts({ ...params, workspaceId })
      setPrompts(response.prompts)
      setTotalCount(response.total)
      setCurrentPage(page)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('common.messages.loadFailed')
      setError(errorMessage)
      console.error('Failed to load prompts:', {
        error: err,
        message: errorMessage,
        params: params,
        stack: err instanceof Error ? err.stack : undefined,
      })

      // 如果是服务器错误，设置空数据避免页面崩溃
      if (errorMessage.includes('服务器内部错误') || errorMessage.includes('Internal server error')) {
        setPrompts([])
        setTotalCount(0)
      }
    } finally {
      setLoading(false)
      loadingRef.current = false
    }
  }

  // 组合初始化和搜索逻辑，避免多次调用
  useEffect(() => {
    // 如果是初次加载
    if (!hasInitialLoaded.current) {
      hasInitialLoaded.current = true
      loadPrompts(1)
      return
    }

    // 搜索词变化时的处理
    const timeoutId = setTimeout(() => {
      // 如果已经在第一页，直接加载
      if (currentPage === 1) {
        loadPrompts(1)
      } else {
        // 如果不在第一页，先设置页码再加载
        setCurrentPage(1)
        loadPrompts(1)
      }
    }, 500) // 防抖

    return () => clearTimeout(timeoutId)
  }, [searchTerm])

  // 页面处理函数
  const handlePageChange = (page: number) => {
    loadPrompts(page)
  }

  // 处理每页条数变化
  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize)
    setCurrentPage(1) // 重置到第一页
    loadPrompts(1, newPageSize)
  }

  // 处理排序按钮点击
  const handleSortClick = (column: string) => {
    const currentOrder = sortOrder[column] || 'default'
    let newOrder: 'asc' | 'desc' | 'default'
    let orderBy: string | undefined
    let asc: boolean | undefined

    // 获取API字段名
    const apiField = columnMapping[column] || column

    switch (currentOrder) {
      case 'default':
        newOrder = 'asc'
        orderBy = apiField
        asc = true
        break
      case 'asc':
        newOrder = 'desc'
        orderBy = apiField
        asc = false
        break
      case 'desc':
        newOrder = 'default'
        orderBy = undefined
        asc = undefined
        break
    }

    // 更新排序状态 - 重置其他列为默认状态，只保留当前列的排序状态
    setSortOrder(prev => {
      const newSortOrder: { [key: string]: 'asc' | 'desc' | 'default' } = {}

      // 将所有列重置为默认状态
      Object.keys(prev).forEach(key => {
        newSortOrder[key] = 'default'
      })

      // 设置当前列的排序状态
      newSortOrder[column] = newOrder

      return newSortOrder
    })

    // 重新加载数据
    loadPrompts(1, pageSize, orderBy, asc)
  }

  // 获取排序图标
  const getSortIcon = (column: string) => {
    const order = sortOrder[column] || 'default'
    switch (order) {
      case 'asc':
        return <ArrowUp className="w-4 h-4" />
      case 'desc':
        return <ArrowDown className="w-4 h-4" />
      default:
        return <ArrowUpDown className="w-4 h-4" />
    }
  }

  // 获取排序按钮提示文字
  const getSortTooltip = (column: string) => {
    const order = sortOrder[column] || 'default'
    switch (order) {
      case 'asc':
        return '点击降序'
      case 'desc':
        return '点击恢复默认排序'
      default:
        return '点击升序'
    }
  }

  // 列名映射到API字段名
  const columnMapping: { [key: string]: string } = {
    prompt_key: 'prompt_key',
    name: 'display_name',
    description: 'description',
    version: 'latest_version',
    created_at: 'created_at',
    updated_at: 'updated_at',
    latest_committed_at: 'latest_committed_at',
  }

  // 打开删除确认弹窗
  const handleOpenDeleteDialog = (prompt: Prompt) => {
    setPromptToDelete(prompt)
    setDeleteDialogOpen(true)
  }

  // 关闭删除确认弹窗
  const handleCloseDeleteDialog = () => {
    setDeleteDialogOpen(false)
    setPromptToDelete(null)
  }

  // 删除成功后的回调
  const handleDeleteSuccess = () => {
    // 重新加载数据
    loadPrompts(currentPage)
  }

  // 复制prompt_key函数
  const handleCopyPromptKey = async (promptKey: string) => {
    try {
      await copyToClipboard(promptKey, setSnackbar, t('common.messages.success'))
      setCopiedKey(promptKey)
      setTimeout(() => setCopiedKey(null), 2000) // 2秒后重置状态
    } catch (error) {
      console.error('复制失败:', error)
      showError(t('common.messages.error'))
    }
  }

  // 处理关联对象对话框
  const handleOpenAssociationsDialog = (associations: RelationObj[], promptName: string) => {
    setSelectedAssociations(associations)
    setSelectedPromptName(promptName)
    setAssociationsDialogOpen(true)
  }

  const handleCloseAssociationsDialog = () => {
    setAssociationsDialogOpen(false)
    setSelectedAssociations([])
    setSelectedPromptName('')
  }

  // 过滤逻辑（保持现有的客户端过滤）
  const filteredPrompts = prompts.filter(prompt => {
    const matchesSearch =
      prompt.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prompt.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prompt.prompt_key.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesSearch
  })

  // 格式化日期显示（包含时分秒）
  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return dateString
    }
  }

  const handleCreatePromptFromDialog = async (basicInfo: { key: string; name: string; description: string; tags: string[]; isPublic: boolean }) => {
    try {
      // 调用API创建提示词
      const response = await PromptService.createPrompt({
        updated_by: user?.id || ENV_CONFIG.DEFAULT_USER_ID,
        prompt_key: basicInfo.key,
        prompt_name: basicInfo.name,
        prompt_description: basicInfo.description,
        workspace_id: workspaceId,
      })

      if (response.code === 0) {
        // 成功创建，存储提示词ID和基本信息
        const promptData = {
          ...basicInfo,
          prompt_id: response.prompt_id,
        }
        localStorage.setItem('newPromptBasicInfo', JSON.stringify(promptData))
        // 导航到编辑页面
        navigate(`/dashboard/prompts/${response.prompt_id}`)
      } else {
        // 处理错误
        console.error('创建提示词失败:', response.msg)
        showSnackbar(`${t('common.messages.error')}: ${response.msg || t('common.messages.unknownError')}`, 'error')
        // 抛出错误，让上层组件知道操作失败
        throw new Error(response.msg || t('common.messages.error'))
      }
    } catch (error: any) {
      console.error('创建提示词时发生错误:', error)

      // 处理 API 错误，显示具体的错误信息
      if (error instanceof ApiError) {
        const errorMsg = error.response?.msg || error.response?.message || error.message || t('common.messages.loadFailed')
        showSnackbar(`${t('common.messages.error')}: ${errorMsg}`, 'error')
      } else if (error instanceof Error) {
        showSnackbar(`${t('common.messages.error')}: ${error.message}`, 'error')
      } else {
        showSnackbar(t('common.messages.networkError'), 'error')
      }

      // 重新抛出错误，让上层组件知道操作失败
      throw error
    }
  }

  // 卡片视图渲染函数
  const renderCardView = (prompt: Prompt, index: number) => (
    <div
      key={prompt.id}
      className="group bg-white rounded-2xl shadow-sm hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-2 border border-gray-100 overflow-hidden cursor-pointer flex flex-col"
      style={{ animationDelay: `${index * 100}ms` }}
      onClick={e => {
        // 如果点击的是按钮或链接区域，不触发卡片点击
        const target = e.target as HTMLElement
        if (target.closest('button') || target.closest('a')) {
          return
        }
        navigate(`/dashboard/prompts/${prompt.id}`)
      }}
    >
      {/* Gradient top border */}
      <div className="h-1 bg-gradient-to-r from-blue-500 to-indigo-600" />

      {/* Prompt header */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 border border-blue-200">
              <PromptTemplateIcon className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <div className="flex items-center space-x-2 mb-1">
                <ConditionalTooltip title={prompt.name}>
                  <h3 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800 truncate cursor-pointer max-w-xs">
                    {prompt.name}
                  </h3>
                </ConditionalTooltip>
                {/* 草稿状态标签 */}
                {prompt.isDraftEdited && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-200">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    {t('common.status.draft')}
                  </span>
                )}
              </div>
              {/* 显示prompt_key */}
              <div className="flex items-center space-x-1 mt-1">
                <Key className="w-3 h-3 text-gray-400" />
                <ConditionalTooltip title={prompt.prompt_key}>
                  <span className="text-xs text-gray-500 font-mono truncate cursor-pointer max-w-32">{prompt.prompt_key}</span>
                </ConditionalTooltip>
                <button
                  onClick={e => {
                    e.stopPropagation() // 防止触发卡片点击
                    handleCopyPromptKey(prompt.prompt_key)
                  }}
                  className="ml-1 p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition-all duration-200"
                  title={t('common.buttons.copy')}
                >
                  {copiedKey === prompt.prompt_key ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Description */}
        <ConditionalTooltip title={prompt.description || ''}>
          <p className="text-sm text-gray-600 mb-3 leading-relaxed min-h-[1.5rem] truncate cursor-pointer">{prompt.description || '\u00A0'}</p>
        </ConditionalTooltip>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-3">
          {prompt.tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 border border-blue-200 hover:from-blue-200 hover:to-indigo-200 transition-all duration-200"
            >
              <Tag className="w-3 h-3 mr-1" />
              {tag}
            </span>
          ))}
          {prompt.tags.length > 3 && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">
              +{prompt.tags.length - 3}
            </span>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 font-medium mb-1">{t('prompts.promptList.creator')}</p>
            <p className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-blue-700">
              {prompt.author || t('common.status.unknown')}
            </p>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 font-medium mb-1">{t('prompts.promptList.createdAt')}</p>
            <p className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-blue-700">{formatDate(prompt.createdAt)}</p>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 font-medium mb-1">{t('prompts.promptList.lastModifier')}</p>
            <p className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-blue-700">
              {prompt.updated_by || t('common.status.unknown')}
            </p>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 font-medium mb-1">{t('prompts.promptList.lastModifiedAt')}</p>
            <p className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-blue-700">{formatDate(prompt.lastModified)}</p>
          </div>
        </div>

        {/* Mock数据区域（版本、使用次数） */}
        <div className="grid grid-cols-2 gap-2 mb-3 pt-2 border-t border-gray-100">
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 font-medium mb-1">{t('prompts.promptList.latestVersion')}</p>
            <p className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-blue-700">{prompt.version || '-'}</p>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 font-medium mb-1">{t('prompts.promptList.lastCommittedAt')}</p>
            <p className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-blue-700">
              {prompt.latest_committed_at ? formatDate(prompt.latest_committed_at) : '-'}
            </p>
          </div>
        </div>

        {/* 关联对象 */}
        {prompt.associations?.relationObjs && prompt.associations.relationObjs.length > 0 && (
          <div className="mb-3 flex items-start gap-2">
            <div className="text-xs text-gray-500 font-medium mt-1">{t('prompts.promptList.associatedObjects')}:</div>
            <div className="flex flex-wrap gap-1 flex-1">
              {prompt.associations.relationObjs.slice(0, 3).map(relationObj => (
                <span
                  key={relationObj.obj_id}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200 cursor-pointer hover:bg-blue-200 transition-colors"
                  onClick={e => {
                    e.stopPropagation()
                    handleRelationObjNavigate(relationObj, workspaceId, navigate)
                  }}
                >
                  {relationObj.obj_type_name}：{relationObj.obj_name}
                </span>
              ))}
              {prompt.associations.relationObjs.length > 3 && (
                <span
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-200 cursor-pointer hover:bg-gray-200 transition-colors"
                  onClick={e => {
                    e.stopPropagation()
                    handleOpenAssociationsDialog(prompt.associations.relationObjs, prompt.name)
                  }}
                >
                  ...
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-4 py-3 bg-gradient-to-r from-gray-50 to-blue-50 border-t border-gray-100 mt-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Link
              to={`/dashboard/prompts/${prompt.id}`}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
              title={t('common.buttons.edit')}
            >
              <Edit className="w-4 h-4" />
            </Link>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={e => {
                e.stopPropagation()
                handleOpenDeleteDialog(prompt)
              }}
              className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200"
              title={t('common.buttons.delete')}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  // 表格视图渲染函数
  const renderTableView = () => (
    <TableContainer component={Paper} className="shadow-sm">
      <Table>
        <TableHead>
          <TableRow className="bg-gradient-to-r from-blue-100 to-indigo-100">
            <TableCell className="text-blue-900 font-semibold">
              <div className="flex items-center space-x-1">
                <strong>{t('prompts.promptList.promptKey')}</strong>
                <button
                  onClick={() => handleSortClick('prompt_key')}
                  className="p-1 hover:bg-blue-200 rounded transition-colors"
                  title={getSortTooltip('prompt_key')}
                >
                  {getSortIcon('prompt_key')}
                </button>
              </div>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <div className="flex items-center space-x-1">
                <strong>{t('prompts.promptList.name')}</strong>
                <button onClick={() => handleSortClick('name')} className="p-1 hover:bg-blue-200 rounded transition-colors" title={getSortTooltip('name')}>
                  {getSortIcon('name')}
                </button>
              </div>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <div className="flex items-center space-x-1">
                <strong>{t('prompts.promptList.description')}</strong>
                <button
                  onClick={() => handleSortClick('description')}
                  className="p-1 hover:bg-blue-200 rounded transition-colors"
                  title={getSortTooltip('description')}
                >
                  {getSortIcon('description')}
                </button>
              </div>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <div className="flex items-center space-x-1">
                <strong>{t('prompts.promptList.latestVersion')}</strong>
                <button
                  onClick={() => handleSortClick('version')}
                  className="p-1 hover:bg-blue-200 rounded transition-colors"
                  title={getSortTooltip('version')}
                >
                  {getSortIcon('version')}
                </button>
              </div>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <strong>{t('prompts.promptList.associatedObjects')}</strong>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <strong>{t('prompts.promptList.creator')}</strong>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <div className="flex items-center space-x-1">
                <strong>{t('prompts.promptList.createdAt')}</strong>
                <button
                  onClick={() => handleSortClick('created_at')}
                  className="p-1 hover:bg-blue-200 rounded transition-colors"
                  title={getSortTooltip('created_at')}
                >
                  {getSortIcon('created_at')}
                </button>
              </div>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <strong>{t('prompts.promptList.lastModifier')}</strong>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <div className="flex items-center space-x-1">
                <strong>{t('prompts.promptList.lastModifiedAt')}</strong>
                <button
                  onClick={() => handleSortClick('updated_at')}
                  className="p-1 hover:bg-blue-200 rounded transition-colors"
                  title={getSortTooltip('updated_at')}
                >
                  {getSortIcon('updated_at')}
                </button>
              </div>
            </TableCell>
            <TableCell className="text-blue-900 font-semibold">
              <div className="flex items-center space-x-1">
                <strong>{t('prompts.promptList.lastCommittedAt')}</strong>
                <button
                  onClick={() => handleSortClick('latest_committed_at')}
                  className="p-1 hover:bg-blue-200 rounded transition-colors"
                  title={getSortTooltip('latest_committed_at')}
                >
                  {getSortIcon('latest_committed_at')}
                </button>
              </div>
            </TableCell>
            <TableCell align="center" className="text-blue-900 font-semibold">
              <strong>{t('prompts.promptList.actions')}</strong>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredPrompts.map(prompt => (
            <TableRow
              key={prompt.id}
              hover
              className="cursor-pointer"
              onClick={e => {
                const target = e.target as HTMLElement
                if (target.closest('button') || target.closest('a')) {
                  return
                }
                navigate(`/dashboard/prompts/${prompt.id}`)
              }}
            >
              <TableCell>
                <div className="flex items-center space-x-1">
                  <ConditionalTooltip title={prompt.prompt_key}>
                    <span className="font-mono text-sm text-gray-600 truncate cursor-pointer max-w-48">{prompt.prompt_key}</span>
                  </ConditionalTooltip>
                  <Tooltip title={t('common.buttons.copy')}>
                    <IconButton
                      size="small"
                      onClick={e => {
                        e.stopPropagation()
                        handleCopyPromptKey(prompt.prompt_key)
                      }}
                      className="ml-1"
                    >
                      {copiedKey === prompt.prompt_key ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
                    </IconButton>
                  </Tooltip>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center space-x-2">
                  <ConditionalTooltip title={prompt.name}>
                    <div className="font-medium text-gray-900 truncate cursor-pointer max-w-48">{prompt.name}</div>
                  </ConditionalTooltip>
                  {/* 草稿状态标签 */}
                  {prompt.isDraftEdited && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-200">
                      <AlertCircle className="w-3 h-3 mr-1" />
                      {t('common.status.draft')}
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <ConditionalTooltip title={prompt.description || ''}>
                  <div className="text-sm text-gray-600 max-w-xs truncate cursor-pointer">{prompt.description || '\u00A0'}</div>
                </ConditionalTooltip>
              </TableCell>
              <TableCell>
                <span className="text-sm text-gray-700">{prompt.version || '-'}</span>
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1 max-w-xs">
                  {prompt.associations?.relationObjs && prompt.associations.relationObjs.length > 0 ? (
                    <>
                      {prompt.associations.relationObjs.slice(0, 3).map(relationObj => (
                        <span
                          key={relationObj.obj_id}
                          className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded cursor-pointer hover:bg-blue-200 transition-colors"
                          onClick={e => {
                            e.stopPropagation()
                            handleRelationObjNavigate(relationObj, workspaceId, navigate)
                          }}
                        >
                          {relationObj.obj_type_name}：{relationObj.obj_name}
                        </span>
                      ))}
                      {prompt.associations.relationObjs.length > 3 && (
                        <span
                          className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded cursor-pointer hover:bg-gray-200 transition-colors"
                          onClick={e => {
                            e.stopPropagation()
                            handleOpenAssociationsDialog(prompt.associations.relationObjs, prompt.name)
                          }}
                        >
                          ...
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="text-xs text-gray-400">暂无关联</span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <span className="text-sm text-gray-700">{prompt.author || '未知'}</span>
              </TableCell>
              <TableCell>
                <span className="text-sm text-gray-600">{formatDate(prompt.createdAt)}</span>
              </TableCell>
              <TableCell>
                <span className="text-sm text-gray-700">{prompt.updated_by || '未知'}</span>
              </TableCell>
              <TableCell>
                <span className="text-sm text-gray-600">{formatDate(prompt.lastModified)}</span>
              </TableCell>
              <TableCell align="center">
                <span className="text-sm text-gray-600">{prompt.latest_committed_at ? formatDate(prompt.latest_committed_at) : '-'}</span>
              </TableCell>
              <TableCell align="center">
                <div className="flex items-center justify-center space-x-1">
                  <Tooltip title={t('common.buttons.edit')}>
                    <IconButton size="small" component={Link} to={`/dashboard/prompts/${prompt.id}`} className="text-gray-400 hover:text-blue-600">
                      <Edit className="w-4 h-4" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title={t('common.buttons.delete')}>
                    <IconButton
                      size="small"
                      onClick={e => {
                        e.stopPropagation()
                        handleOpenDeleteDialog(prompt)
                      }}
                      className="text-gray-400 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </IconButton>
                  </Tooltip>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )

  return (
    <div className="space-y-8 p-6" style={{ minHeight: '93vh' }}>
      {/* Page header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-900 mb-2 p-1">
          {t('prompts.title')}
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-6">{t('prompts.subtitle')}</p>
      </div>

      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row items-center gap-4">
        {/* Search */}
        <div className="flex-1">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-500 transition-colors duration-200" />
            <input
              type="text"
              placeholder={t('prompts.promptList.searchPlaceholder')}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
            />
          </div>
        </div>

        {/* View mode switcher */}
        <div className="flex items-center border border-gray-200 rounded-xl bg-gray-50">
          <button
            onClick={() => setViewMode('card')}
            className={`p-3 rounded-l-xl transition-all duration-200 ${
              viewMode === 'card'
                ? 'bg-gradient-to-r from-purple-500 to-indigo-500 text-white shadow-sm'
                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
            }`}
            title={t('common.buttons.view')}
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-3 rounded-r-xl transition-all duration-200 ${
              viewMode === 'list'
                ? 'bg-gradient-to-r from-purple-500 to-indigo-500 text-white shadow-sm'
                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
            }`}
            title={t('common.buttons.view')}
          >
            <List className="w-4 h-4" />
          </button>
        </div>

        {/* Create Prompt Button */}
        <button
          onClick={() => setBasicInfoDialogOpen(true)}
          className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
        >
          <Plus className="w-5 h-5" />
          <span>{t('prompts.createPrompt')}</span>
        </button>
      </div>

      {/* 错误状态 */}
      {error && (
        <div className="bg-gradient-to-r from-red-50 to-pink-50 border border-red-200 rounded-xl p-6 mb-6 shadow-sm">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-gradient-to-r from-red-500 to-pink-500 rounded-xl flex items-center justify-center mr-3">
              <AlertCircle className="w-5 h-5 text-white" />
            </div>
            <span className="text-red-700 font-medium">{error}</span>
          </div>
          <button
            onClick={() => loadPrompts(currentPage)}
            className="mt-3 px-4 py-2 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-lg font-medium hover:from-red-700 hover:to-pink-700 transition-all duration-200 shadow-sm hover:shadow-xl"
          >
            {t('common.buttons.refresh')}
          </button>
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="w-12 h-12 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-xl flex items-center justify-center mr-3">
            <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
          </div>
          <span className="text-lg text-gray-600 font-medium">{t('common.status.loading')}</span>
        </div>
      )}

      {/* 空状态 */}
      {!loading && !error && filteredPrompts.length === 0 && (
        <div className="text-center py-16">
          <div className="w-24 h-24 bg-gradient-to-r from-blue-100 to-indigo-200 rounded-full flex items-center justify-center mx-auto mb-6">
            <PromptTemplateIcon className="w-12 h-12 text-blue-400" />
          </div>
          <h3 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-blue-900 mb-3">
            {prompts.length === 0 ? t('prompts.promptList.noPrompts') : t('apps.empty.noTemplates')}
          </h3>
          <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
            {searchTerm ? '尝试调整搜索条件来找到您需要的提示词' : '开始创建您的第一个AI提示词模板，构建智能对话体验'}
          </p>
          {!searchTerm && (
            <button
              onClick={() => setBasicInfoDialogOpen(true)}
              className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
            >
              <Plus className="w-5 h-5" />
              <span>{t('prompts.createPrompt')}</span>
            </button>
          )}
        </div>
      )}

      {/* Prompts display */}
      {!loading && !error && filteredPrompts.length > 0 && (
        <>
          {viewMode === 'card' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{filteredPrompts.map((prompt, index) => renderCardView(prompt, index))}</div>
          ) : (
            renderTableView()
          )}
        </>
      )}

      {/* 分页组件 */}
      <Pagination
        pager={{
          total: totalCount,
          currentPage: currentPage,
          pageSize: pageSize,
          pageSizeOptions: [9, 18, 30, 60],
        }}
        loading={loading}
        error={error}
        onPagerChange={(page, pageSize) => {
          handlePageChange(page)
          handlePageSizeChange(pageSize)
        }}
      />

      {/* 基本信息对话框 */}
      <PromptBasicInfoDialog
        open={basicInfoDialogOpen}
        onClose={() => setBasicInfoDialogOpen(false)}
        onConfirm={handleCreatePromptFromDialog}
        keyEditable={true}
        title={t('components.prompts.promptBasicInfoDialog.defaultTitle')}
        buttonText={{
          loading: t('components.prompts.promptBasicInfoDialog.defaultButtonLoading'),
          normal: t('components.prompts.promptBasicInfoDialog.defaultButtonNormal'),
        }}
      />

      {/* 删除确认弹窗 */}
      <DeletePromptDialog
        open={deleteDialogOpen}
        onClose={handleCloseDeleteDialog}
        onDeleteSuccess={handleDeleteSuccess}
        prompt={promptToDelete}
        showSnackbar={showSnackbar}
      />

      {/* 关联对象列表对话框 */}
      <AssociationsDialog
        open={associationsDialogOpen}
        onClose={handleCloseAssociationsDialog}
        associations={selectedAssociations}
        versionName={selectedPromptName}
      />

      {/* 消息提示 */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} anchorOrigin={{ vertical: 'top', horizontal: 'center' }} />
    </div>
  )
}

export default PromptsPage
