import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import PromptTemplateIcon from '@/assets/icons/promptTemplate.svg?react'
import { Plus, Edit, Trash2, AlertCircle, Check, Clock, Key, Link2 } from 'lucide-react'
import { Tooltip, Menu, MenuItem, MenuList, Box } from '@mui/material'
import { PromptBasicInfoDialog, AssociationsDialog, DeletePromptDialog } from '@/components/Prompts'
import { ApiError, PromptService, type Prompt, type RelationObj } from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore'
import { usePromptsViewMode } from '@/stores/useUIStore'
import { ENV_CONFIG } from '@/config/environment'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { copyToClipboard, handleRelationObjNavigate } from '@/utils/prompts/utils'
import { CommonPageLayout, SearchInput } from '@/components/Common/common-page'
import type { ViewType } from '@/components/Common/common-page'
import { ConfigCard, CardFooterRow, type ConfigCardTag, type EditingState } from '@/components/Common/common-grid'
import { ConfigTable, type TableColumn, type SortState } from '@/components/Common/common-table'
import { Empty } from '@/components/Common/Empty'
import { useOptimizedSearch } from '@/hooks/useSearchOptimization'

/** +n 区域与间距预留 px；多标签时每标签最大宽 = (containerWidth - ASSOCIATIONS_RESERVE_PX) / tagCount */
const ASSOCIATIONS_RESERVE_PX = 40

/** 列表模式最多展示的关联对象数量 */
const LIST_VIEW_MAX_ASSOCIATIONS = 2

interface AssociationTagProps {
  relationObj: RelationObj
  containerWidth: number
  tagCount: number
  onNavigate: (e?: React.MouseEvent) => void
}

/** 单个关联标签：多标签时均分最大宽度，避免被拉得过宽；溢出时 Tooltip 显示全文 */
function AssociationTag({ relationObj, containerWidth, tagCount, onNavigate }: AssociationTagProps) {
  const spanRef = useRef<HTMLSpanElement>(null)
  const [isOverflow, setIsOverflow] = useState(false)
  const { obj_type_name, obj_name } = relationObj

  useEffect(() => {
    if (!spanRef.current) return
    const check = () => {
      if (spanRef.current) {
        setIsOverflow(spanRef.current.scrollWidth > spanRef.current.clientWidth)
      }
    }
    check()
    const ro = new ResizeObserver(check)
    ro.observe(spanRef.current)
    return () => ro.disconnect()
  }, [])

  const maxWidth = tagCount > 1 && containerWidth > 0 ? (containerWidth - ASSOCIATIONS_RESERVE_PX) / tagCount : undefined

  const content = (
    <span
      ref={spanRef}
      className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded cursor-pointer hover:bg-blue-200 transition-colors truncate"
      style={{
        flex: '0 1 auto',
        minWidth: 0,
        maxWidth,
      }}
      onClick={e => {
        e.stopPropagation()
        onNavigate(e)
      }}
    >
      {obj_type_name}：{obj_name}
    </span>
  )

  return isOverflow ? (
    <Tooltip title={`${obj_type_name}：${obj_name}`} disableInteractive placement="top">
      {content}
    </Tooltip>
  ) : (
    content
  )
}

interface AssociationsCellProps {
  row: Prompt
  workspaceId: string
  navigate: ReturnType<typeof useNavigate>
  onOpenAssociations: (objs: RelationObj[], name: string, e?: React.MouseEvent) => void
  t: ReturnType<typeof useTranslation>['t']
}

/** 关联对象列内容：最多展示 3 个标签 + 溢出时 +n；多标签时均分宽度，避免单个被拉得过宽 */
function AssociationsCell({ row, workspaceId, navigate, onOpenAssociations, t }: AssociationsCellProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(0)
  const objs = row.associations?.relationObjs?.slice(0, LIST_VIEW_MAX_ASSOCIATIONS) ?? []
  const totalCount = row.associations?.relationObjs?.length ?? 0
  const hasOverflow = totalCount > LIST_VIEW_MAX_ASSOCIATIONS
  const tagCount = objs.length

  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) setContainerWidth(entry.contentRect.width)
    })
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  return (
    <div ref={containerRef} className="flex items-center gap-1 min-w-0 overflow-hidden">
      {row.associations?.relationObjs && row.associations.relationObjs.length > 0 ? (
        <>
          {objs.map(relationObj => (
            <AssociationTag
              key={relationObj.obj_id}
              relationObj={relationObj}
              containerWidth={containerWidth}
              tagCount={tagCount}
              onNavigate={() => handleRelationObjNavigate(relationObj, workspaceId, navigate)}
            />
          ))}
          {hasOverflow && (
            <span
              className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded cursor-pointer hover:bg-gray-200 transition-colors flex-shrink-0"
              onClick={e => onOpenAssociations(row.associations!.relationObjs || [], row.name, e)}
            >
              +{totalCount - LIST_VIEW_MAX_ASSOCIATIONS}
            </span>
          )}
        </>
      ) : (
        <span className="text-xs text-gray-400">{t('prompts.promptList.noAssociations')}</span>
      )}
    </div>
  )
}

/** 关联对象下拉：头部固定，仅下方 item 列表区域滚动 */
const AssociationMenuListWrapper = React.forwardRef<HTMLUListElement, React.ComponentProps<typeof MenuList> & { children?: React.ReactNode }>(
  function AssociationMenuListWrapper(props, ref) {
    const { children, sx, ...listSlotProps } = props
    const arr = React.Children.toArray(children)
    const header = arr[0]
    const items = arr.slice(1)
    return (
      <div className="flex flex-col overflow-hidden max-h-[320px]">
        <div className="flex-shrink-0">{header}</div>
        <MenuList
          ref={ref}
          {...listSlotProps}
          sx={{
            ...(typeof sx === 'object' && sx !== null ? sx : {}),
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            overflowX: 'hidden',
            py: 0,
          }}
        >
          {items}
        </MenuList>
      </div>
    )
  },
)

const PromptsPageNew: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const workspaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID

  // 视图模式
  const [viewMode, setViewMode] = usePromptsViewMode()
  const viewType: ViewType = viewMode === 'grid' ? 'grid' : 'table'

  // 搜索和排序 - 使用防抖搜索
  const { searchTerm, debouncedSearchTerm, setSearchTerm } = useOptimizedSearch(undefined, {
    debounceDelay: 300,
    minChars: 0,
    immediateOnEmpty: false,
    respectComposition: false,
  })
  const [sortState, setSortState] = useState<SortState>({ field: 'updated_at', order: 'desc' })

  // 数据状态
  const [prompts, setPrompts] = useState<Prompt[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 分页
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [pageSize, setPageSize] = useState(20)

  // 复制状态
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  // 对话框状态
  const [basicInfoDialogOpen, setBasicInfoDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [promptToDelete, setPromptToDelete] = useState<Prompt | null>(null)
  const [associationsDialogOpen, setAssociationsDialogOpen] = useState(false)
  const [selectedAssociations, setSelectedAssociations] = useState<RelationObj[]>([])
  const [selectedPromptName, setSelectedPromptName] = useState('')

  // 网格卡片内「关联对象」下拉的锚点与当前 prompt
  const [associationMenuAnchor, setAssociationMenuAnchor] = useState<HTMLElement | null>(null)
  const [associationMenuPrompt, setAssociationMenuPrompt] = useState<Prompt | null>(null)

  // Snackbar
  const { snackbar, showSnackbar, showError, closeSnackbar, setSnackbar } = useUnifiedSnackbar()

  // 防止重复加载
  const hasInitialLoaded = useRef(false)
  const loadingRef = useRef(false)
  const lastLoadTime = useRef(0)

  // 编辑状态（ConfigCard 需要）
  const [editingState] = useState<EditingState>({
    id: null,
    field: null,
    value: '',
    isEditing: false,
  })

  // 列名映射到 API 字段名
  const columnMapping: { [key: string]: string } = useMemo(
    () => ({
      prompt_key: 'prompt_key',
      name: 'display_name',
      description: 'description',
      version: 'latest_version',
      created_at: 'created_at',
      updated_at: 'updated_at',
      latest_committed_at: 'latest_committed_at',
    }),
    [],
  )

  // 获取提示词列表
  const loadPrompts = useCallback(
    async (page = 1, size = pageSize, orderBy?: string, asc?: boolean) => {
      const now = Date.now()
      if (now - lastLoadTime.current < 100) {
        return
      }

      if (loadingRef.current) {
        return
      }

      lastLoadTime.current = now
      loadingRef.current = true
      setLoading(true)
      setError(null)

      const params: any = {
        page,
        pageSize: size,
      }

      if (debouncedSearchTerm && debouncedSearchTerm.trim()) {
        params.key_word = debouncedSearchTerm.trim()
      }

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
        console.error('Failed to load prompts:', err)

        if (errorMessage.includes('服务器内部错误') || errorMessage.includes('Internal server error')) {
          setPrompts([])
          setTotalCount(0)
        }
      } finally {
        setLoading(false)
        loadingRef.current = false
      }
    },
    [pageSize, debouncedSearchTerm, workspaceId, t],
  )

  // 初始化和搜索/排序逻辑：
  // - Grid 默认按更新时间 desc
  // - Table 允许“取消排序”（不传 order_by/asc），但切回 Grid 会恢复默认
  // - 搜索或排序变化时由本 effect 统一拉数
  useEffect(() => {
    const isGrid = viewType === 'grid'
    const orderBy = sortState.field ? columnMapping[sortState.field] || sortState.field : isGrid ? 'updated_at' : undefined
    const asc = sortState.field ? sortState.order === 'asc' : isGrid ? false : undefined

    if (!hasInitialLoaded.current) {
      hasInitialLoaded.current = true
      loadPrompts(1, pageSize, orderBy, asc)
      return
    }
    setCurrentPage(1)
    loadPrompts(1, pageSize, orderBy, asc)
  }, [debouncedSearchTerm, sortState, loadPrompts, pageSize, columnMapping, viewType])

  // 处理排序变化（表格/网格共用，由 effect 根据 sortState 触发加载）
  const handleSortChange = useCallback((sort: SortState) => {
    setSortState(sort)
  }, [])

  // 处理分页变化（带上当前排序；Table 若取消排序则不传 order_by/asc）
  const handlePagerChange = useCallback(
    (page: number, size: number) => {
      const isGrid = viewType === 'grid'
      const orderBy = sortState.field ? columnMapping[sortState.field] || sortState.field : isGrid ? 'updated_at' : undefined
      const asc = sortState.field ? sortState.order === 'asc' : isGrid ? false : undefined
      if (size !== pageSize) {
        setPageSize(size)
        setCurrentPage(1)
        loadPrompts(1, size, orderBy, asc)
      } else if (page !== currentPage) {
        loadPrompts(page, size, orderBy, asc)
      }
    },
    [pageSize, currentPage, loadPrompts, sortState, columnMapping, viewType],
  )

  // 格式化日期
  const formatDate = useCallback((dateString: string) => {
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
  }, [])

  // 格式化相对时间（用于卡片显示）
  const formatRelativeTime = useCallback(
    (dateString: string): string => {
      try {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMs / 3600000)
        const diffDays = Math.floor(diffMs / 86400000)

        if (diffMins < 1) return t('common.messages.relativeTime.justNow')
        if (diffMins < 60) return t('common.messages.relativeTime.minutesAgo', { count: diffMins })
        if (diffHours < 24) return t('common.messages.relativeTime.hoursAgo', { count: diffHours })
        if (diffDays < 7) return t('common.messages.relativeTime.daysAgo', { count: diffDays })

        return date.toLocaleDateString()
      } catch {
        return dateString
      }
    },
    [t],
  )

  // 复制 prompt_key
  const handleCopyPromptKey = useCallback(
    async (promptKey: string, e?: React.MouseEvent) => {
      e?.stopPropagation()
      try {
        await copyToClipboard(promptKey, setSnackbar)
        setCopiedKey(promptKey)
        setTimeout(() => setCopiedKey(null), 2000)
      } catch (error) {
        console.error('复制失败:', error)
        showError(t('common.messages.error'))
      }
    },
    [setSnackbar, showError, t],
  )

  // 删除对话框
  const handleOpenDeleteDialog = useCallback((prompt: Prompt, e?: React.MouseEvent) => {
    e?.stopPropagation()
    setPromptToDelete(prompt)
    setDeleteDialogOpen(true)
  }, [])

  const handleCloseDeleteDialog = useCallback(() => {
    setDeleteDialogOpen(false)
    setPromptToDelete(null)
  }, [])

  const handleDeleteSuccess = useCallback(() => {
    loadPrompts(currentPage, pageSize)
  }, [loadPrompts, currentPage, pageSize])

  // 关联对象对话框
  const handleOpenAssociationsDialog = useCallback((associations: RelationObj[], promptName: string, e?: React.MouseEvent) => {
    e?.stopPropagation()
    setSelectedAssociations(associations)
    setSelectedPromptName(promptName)
    setAssociationsDialogOpen(true)
  }, [])

  const handleCloseAssociationsDialog = useCallback(() => {
    setAssociationsDialogOpen(false)
    setSelectedAssociations([])
    setSelectedPromptName('')
  }, [])

  const handleOpenAssociationMenu = useCallback((e: React.MouseEvent<HTMLElement>, prompt: Prompt) => {
    e.stopPropagation()
    setAssociationMenuAnchor(e.currentTarget as HTMLElement)
    setAssociationMenuPrompt(prompt)
  }, [])

  const handleCloseAssociationMenu = useCallback(() => {
    setAssociationMenuAnchor(null)
    setAssociationMenuPrompt(null)
  }, [])

  const handleAssociationItemNavigate = useCallback(
    (obj: RelationObj) => {
      handleRelationObjNavigate(obj, workspaceId, navigate)
      handleCloseAssociationMenu()
    },
    [workspaceId, navigate, handleCloseAssociationMenu],
  )

  // 创建提示词
  const handleCreatePromptFromDialog = useCallback(
    async (basicInfo: { key: string; name: string; description: string; tags: string[]; isPublic: boolean }) => {
      try {
        const response = await PromptService.createPrompt({
          updated_by: user?.id || ENV_CONFIG.DEFAULT_USER_ID,
          prompt_key: basicInfo.key,
          prompt_name: basicInfo.name,
          prompt_description: basicInfo.description,
          workspace_id: workspaceId,
        })

        if (response.code === 0) {
          const promptData = {
            ...basicInfo,
            prompt_id: response.prompt_id,
          }
          localStorage.setItem('newPromptBasicInfo', JSON.stringify(promptData))
          navigate(`/dashboard/prompts/${response.prompt_id}`)
        } else {
          console.error('创建提示词失败:', response.msg)
          showSnackbar(`${t('common.messages.error')}: ${response.msg || t('common.messages.unknownError')}`, 'error')
          throw new Error(response.msg || t('common.messages.error'))
        }
      } catch (error: any) {
        console.error('创建提示词时发生错误:', error)

        if (error instanceof ApiError) {
          const errorMsg = error.response?.msg || error.response?.message || error.message || t('common.messages.loadFailed')
          showSnackbar(`${t('common.messages.error')}: ${errorMsg}`, 'error')
        } else if (error instanceof Error) {
          showSnackbar(`${t('common.messages.error')}: ${error.message}`, 'error')
        } else {
          showSnackbar(t('common.messages.networkError'), 'error')
        }

        throw error
      }
    },
    [user, workspaceId, navigate, showSnackbar, t],
  )

  // 表格列定义
  const tableColumns: TableColumn<Prompt>[] = useMemo(
    () => [
      {
        key: 'prompt',
        title: t('prompts.promptList.name'),
        dataIndex: 'name',
        width: 300,
        sortable: true,
        sortField: 'name',
        render: ({ row }) => (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center text-xl bg-gradient-to-r from-blue-100 to-indigo-100">
              <PromptTemplateIcon className="w-5 h-5 text-blue-600" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900 cursor-pointer truncate" onClick={() => navigate(`/dashboard/prompts/${row.id}`)}>
                  {row.name}
                </span>
                {row.isDraftEdited && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-200 flex-shrink-0">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    {t('common.status.draft')}
                  </span>
                )}
                <Tooltip title={row.prompt_key} placement="top">
                  <button
                    onClick={e => handleCopyPromptKey(row.prompt_key, e)}
                    className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors flex-shrink-0"
                  >
                    {copiedKey === row.prompt_key ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Key className="w-3.5 h-3.5" />}
                  </button>
                </Tooltip>
              </div>
              <div className="mt-1 text-xs text-gray-500 truncate">{row.description || '-'}</div>
            </div>
          </div>
        ),
      },
      {
        key: 'version',
        title: t('prompts.promptList.latestVersion'),
        dataIndex: 'version',
        width: 100,
        render: ({ row }) => {
          const hasVersion = row.version && row.version !== '-'
          return <span className="text-sm text-gray-700">{hasVersion ? row.version : t('common.status.draft')}</span>
        },
      },
      {
        key: 'associations',
        title: t('prompts.promptList.associatedObjects'),
        width: 200,
        render: ({ row }) => (
          <AssociationsCell row={row} workspaceId={workspaceId} navigate={navigate} onOpenAssociations={handleOpenAssociationsDialog} t={t} />
        ),
      },
      {
        key: 'updated_at',
        title: t('prompts.promptList.updatedAt'),
        dataIndex: 'lastModified',
        width: 160,
        sortable: true,
        sortField: 'updated_at',
        render: ({ row }) => <span className="text-sm text-gray-600">{formatDate(row.lastModified)}</span>,
      },
      {
        key: 'created_at',
        title: t('prompts.promptList.createdAt'),
        dataIndex: 'createdAt',
        width: 160,
        sortable: true,
        sortField: 'created_at',
        render: ({ row }) => <span className="text-sm text-gray-600">{formatDate(row.createdAt)}</span>,
      },
      {
        key: 'actions',
        title: t('prompts.promptList.actions'),
        type: 'operate',
        align: 'center',
        width: 100,
        operations: [
          {
            key: 'edit',
            icon: <Edit className="w-4 h-4" />,
            label: t('common.buttons.edit'),
            tooltip: t('common.buttons.edit'),
            onClick: row => navigate(`/dashboard/prompts/${row.id}`),
          },
          {
            key: 'delete',
            icon: <Trash2 className="w-4 h-4" />,
            label: t('common.buttons.delete'),
            tooltip: t('common.buttons.delete'),
            onClick: row => handleOpenDeleteDialog(row),
          },
        ],
      },
    ],
    [t, copiedKey, handleCopyPromptKey, formatDate, workspaceId, navigate, handleOpenDeleteDialog, handleOpenAssociationsDialog],
  )

  // 网格视图
  const gridView = useMemo(() => {
    if (prompts.length === 0) {
      return <Empty searchTerm={debouncedSearchTerm} type="prompts" onCreateClick={() => setBasicInfoDialogOpen(true)} />
    }

    return (
      <div className="grid grid-cols-3 lg:grid-cols-3 lg:grid-cols-4 gap-4">
        {prompts.map(prompt => {
          const hasVersion = prompt.version && prompt.version !== '-'
          const tags: ConfigCardTag[] = hasVersion
            ? [{ label: String(prompt.version), color: '#3B82F6' }]
            : [{ label: t('common.status.draft'), variant: 'warning' }]

          // 准备操作
          const actions = [
            {
              key: 'edit',
              label: t('common.buttons.edit'),
              icon: <Edit className="w-4 h-4" />,
              onClick: () => navigate(`/dashboard/prompts/${prompt.id}`),
            },
            {
              key: 'delete',
              label: t('common.buttons.delete'),
              icon: <Trash2 className="w-4 h-4" />,
              onClick: () => handleOpenDeleteDialog(prompt),
            },
          ]

          // Title 右侧的复制key按钮
          const titleExtra = (
            <Tooltip title={prompt.prompt_key} placement="top">
              <button
                onClick={e => handleCopyPromptKey(prompt.prompt_key, e)}
                className="p-0.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors flex-shrink-0"
              >
                {copiedKey === prompt.prompt_key ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Key className="w-3.5 h-3.5" />}
              </button>
            </Tooltip>
          )

          // Footer：关联对象（图标+数量）| 编辑于 xxx
          const relationObjs = prompt.associations?.relationObjs ?? []
          const relationCount = relationObjs.length
          const timeDisplay = formatRelativeTime(prompt.lastModified)
          const footer = (
            <CardFooterRow>
              <div className="flex items-center gap-1.5 text-[11px] text-[#9CA3AF]">
                <div className="flex items-center">
                  <Clock className="w-3 h-3 mr-1 flex-shrink-0" />
                  <span>
                    {t('common.card.editedAgo')} {timeDisplay}
                  </span>
                </div>
                <span className="text-[#E5E7EB]">|</span>
                <button
                  type="button"
                  onClick={e => handleOpenAssociationMenu(e, prompt)}
                  className="flex items-center gap-0.5 hover:text-[#6B7280] hover:bg-gray-100 rounded px-0.5 -mx-0.5 transition-colors"
                  title={t('prompts.promptList.associatedObjects')}
                >
                  <Link2 className="w-3 h-3 flex-shrink-0" />
                  <span>{relationCount}</span>
                </button>
              </div>
            </CardFooterRow>
          )

          return (
            <ConfigCard
              key={prompt.id}
              id={prompt.id}
              icon={<PromptTemplateIcon className="w-6 h-6" />}
              iconBgColor="bg-gradient-to-r from-blue-100 to-indigo-100"
              iconTextColor="text-blue-600"
              title={prompt.name}
              titleExtra={titleExtra}
              description={prompt.description || ''}
              tags={tags}
              editingState={editingState}
              actions={actions}
              onClick={() => navigate(`/dashboard/prompts/${prompt.id}`)}
              footer={footer}
            />
          )
        })}
      </div>
    )
  }, [
    prompts,
    debouncedSearchTerm,
    t,
    editingState,
    navigate,
    handleOpenDeleteDialog,
    handleOpenAssociationMenu,
    formatRelativeTime,
    copiedKey,
    handleCopyPromptKey,
  ])

  // 表格视图
  const tableView = useMemo(() => {
    const tableData = { columns: tableColumns, rows: prompts }
    return (
      <ConfigTable
        tableData={tableData}
        loading={loading}
        size="small"
        stickyHeader
        defaultSort={sortState.field ? sortState : undefined}
        onSortChange={handleSortChange}
        remoteSort
        emptyState={<Empty searchTerm={debouncedSearchTerm} type="prompts" onCreateClick={() => setBasicInfoDialogOpen(true)} />}
      />
    )
  }, [tableColumns, prompts, loading, sortState, handleSortChange, debouncedSearchTerm])

  // 工具栏左侧（搜索 + 网格下排序：名称 / 创建时间 / 更新时间，默认更新时间 desc）
  const toolbarLeft = useMemo(
    () => (
      <>
        <SearchInput searchTerm={searchTerm} placeholder={t('prompts.promptList.searchPlaceholder')} onChange={setSearchTerm} />
        {viewType === 'grid' && (
          <>
            <select
              value={sortState.field || 'updated_at'}
              onChange={e =>
                handleSortChange({
                  field: e.target.value as 'name' | 'created_at' | 'updated_at',
                  order: sortState.order || 'desc',
                })
              }
              className="h-8 px-3 bg-white dark:bg-gray-800 border border-[#e5e7eb] dark:border-gray-600 text-[#1f2937] dark:text-gray-200 rounded-[4px] text-sm focus:outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6] transition-colors"
            >
              <option value="name">{t('prompts.promptList.sortByName')}</option>
              <option value="created_at">{t('prompts.promptList.sortByCreated')}</option>
              <option value="updated_at">{t('prompts.promptList.sortByUpdated')}</option>
            </select>
            <button
              type="button"
              onClick={() =>
                handleSortChange({
                  field: (sortState.field || 'updated_at') as 'name' | 'created_at' | 'updated_at',
                  order: sortState.order === 'asc' ? 'desc' : 'asc',
                })
              }
              className="h-8 w-8 bg-white dark:bg-gray-800 border border-[#e5e7eb] dark:border-gray-600 text-[#6b7280] dark:text-gray-300 hover:text-[#374151] dark:hover:text-gray-100 hover:bg-[#f9fafb] dark:hover:bg-gray-700 hover:border-[#d1d5db] dark:hover:border-gray-500 rounded-[4px] transition-colors flex items-center justify-center"
              aria-label={sortState.order === 'asc' ? 'asc' : 'desc'}
            >
              {sortState.order === 'asc' ? <span className="text-sm">↑</span> : <span className="text-sm">↓</span>}
            </button>
          </>
        )}
      </>
    ),
    [searchTerm, t, viewType, sortState, handleSortChange],
  )

  // 工具栏右侧
  const toolbarRight = useMemo(
    () => (
      <button onClick={() => setBasicInfoDialogOpen(true)} className="btn-primary h-8 flex items-center gap-2 text-sm px-4">
        <Plus className="w-4 h-4" />
        <span>{t('prompts.createPrompt')}</span>
      </button>
    ),
    [t],
  )

  const handleViewTypeChange = useCallback(
    (type: ViewType) => {
      // 切回 Grid 时，如果在表格里取消了排序，则恢复默认排序 updated_at desc
      if (type === 'grid' && !sortState.field) {
        setSortState({ field: 'updated_at', order: 'desc' })
      }
      setViewMode(type === 'grid' ? 'grid' : 'list')
    },
    [setViewMode, sortState.field],
  )

  return (
    <>
      <CommonPageLayout
        title={t('prompts.title')}
        viewType={viewType}
        onViewTypeChange={handleViewTypeChange}
        pager={{
          total: totalCount,
          currentPage,
          pageSize,
          pageSizeOptions: [20, 60, 100, 200],
        }}
        onPagerChange={handlePagerChange}
        loading={loading}
        error={error}
        gridView={gridView}
        tableView={tableView}
        toolbarLeft={toolbarLeft}
        toolbarRight={toolbarRight}
      />

      {/* 网格卡片内「关联对象」下拉：头部固定，仅 item 区域滚动，最多 5 条高；关闭时无退出动画 */}
      <Menu
        anchorEl={associationMenuAnchor}
        open={Boolean(associationMenuAnchor)}
        onClose={handleCloseAssociationMenu}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        transitionDuration={{ enter: 200, exit: 0 }}
        slots={{ list: AssociationMenuListWrapper }}
        slotProps={{
          paper: {
            sx: {
              maxWidth: 300,
              minWidth: 300,
              maxHeight: 320,
            },
          },
          list: {
            sx: { maxHeight: 250 },
          },
        }}
      >
        <Box
          component="div"
          sx={{
            fontSize: 12,
            color: '#777777',
            borderBottom: 1,
            borderColor: 'divider',
            py: 1,
            px: 1.5,
            maxWidth: 300,
          }}
        >
          {associationMenuPrompt?.associations?.relationObjs?.length
            ? t('prompts.promptList.associatedCount', {
                count: associationMenuPrompt.associations.relationObjs.length,
              })
            : t('prompts.promptList.noAssociations')}
        </Box>
        {associationMenuPrompt?.associations?.relationObjs?.length
          ? associationMenuPrompt.associations.relationObjs.map(obj => (
              <MenuItem
                key={obj.obj_id}
                onClick={() => handleAssociationItemNavigate(obj)}
                sx={{
                  display: 'block',
                  whiteSpace: 'normal',
                  py: 0.75,
                  px: 1.5,
                  maxWidth: 300,
                  boxSizing: 'border-box',
                }}
              >
                <div className="text-gray-900 text-[12px] truncate min-w-0" title={`${obj.obj_type_name}：${obj.obj_name}`}>
                  {obj.obj_type_name}：{obj.obj_name}
                </div>
                <div className="text-gray-500 text-[11px] truncate min-w-0 mt-0.5" title={`${obj.obj_version || '-'} | ${obj.obj_id}`}>
                  {obj.obj_version || '-'}{' '}
                  <span className="text-gray-400 shrink-0 opacity-70" aria-hidden>
                    {' '}
                    ｜{' '}
                  </span>{' '}
                  {obj.obj_id}
                </div>
              </MenuItem>
            ))
          : null}
      </Menu>

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
        workspaceId={workspaceId}
        showSnackbar={showSnackbar}
      />

      {/* 关联对象列表对话框 */}
      <AssociationsDialog
        open={associationsDialogOpen}
        onClose={handleCloseAssociationsDialog}
        associations={selectedAssociations}
        versionName={selectedPromptName}
        workspaceId={workspaceId}
      />

      {/* 消息提示 */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} anchorOrigin={{ vertical: 'top', horizontal: 'center' }} />
    </>
  )
}

export default PromptsPageNew
