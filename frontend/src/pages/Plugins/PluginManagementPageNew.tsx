import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useCreatePlugin, usePluginList, useDeletePlugin, PluginInfo } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { usePluginManagementViewMode } from '../../stores/useUIStore'
import { ENV_CONFIG } from '../../config/environment'
import CloudPluginFormDialog from '../../components/Plugins/CloudPluginFormDialog'
import IDEPluginFormDialog from '../../components/Plugins/IDEPluginFormDialog'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import ReactMarkdown from 'react-markdown'
import {
  Plus,
  Settings,
  Upload,
  Trash2,
  Eye,
  Edit,
  RefreshCw,
  Cloud,
  Code,
} from 'lucide-react'
import { Button, Dialog, DialogTitle, DialogContent, DialogActions, DialogContentText, Typography, CircularProgress } from '@mui/material'
import { CommonPageLayout, SearchInput } from '../../components/Common/common-page'
import type { ViewType } from '../../components/Common/common-page'
import { ConfigCard, type EditingState } from '../../components/Common/common-grid'
import { ConfigTable, type TableColumn } from '../../components/Common/common-table'
import { Empty } from '../../components/Common/Empty'

interface Plugin {
  space_id: string
  plugin_id: string
  plugin_version: string
  name: string
  desc: string
  desc_mk?: string
  plugin_type: number
  published?: boolean
  url?: string
  icon_uri: string
  status?: 'active' | 'inactive' | 'error' | 'updating'
  config?: Record<string, unknown>
}

interface CloudPluginFormState {
  name: string
  description: string
  desc_mk?: string
  url: string
  authMethod: string
}

interface IDEPluginFormState {
  name: string
  description: string
  desc_mk?: string
}

const PluginManagementPageNew: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()
  const { snackbar, showSuccess, showError, showInfo, closeSnackbar } = useUnifiedSnackbar()

  // 视图模式
  const [viewMode, setViewMode] = usePluginManagementViewMode()
  const viewType: ViewType = viewMode === 'grid' ? 'grid' : 'table'

  // 搜索和筛选
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  // 分页
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(20)

  // 对话框状态
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [installDialogOpen, setInstallDialogOpen] = useState(false)
  const [deleteDialog, setDeleteDialog] = useState<{ isOpen: boolean; plugin: Plugin | null }>({
    isOpen: false,
    plugin: null,
  })
  const [cloudPluginDialogOpen, setCloudPluginDialogOpen] = useState(false)
  const [idePluginDialogOpen, setIdePluginDialogOpen] = useState(false)
  const [editingPlugin, setEditingPlugin] = useState<Plugin | null>(null)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)

  // 编辑状态（用于 ConfigCard）
  const [editingState] = useState<EditingState>({
    id: null,
    field: null,
    value: '',
    isEditing: false,
  })

  // API hooks
  const createPluginMutation = useCreatePlugin()
  const deletePluginMutation = useDeletePlugin()

  // 表单状态
  const [cloudPluginForm, setCloudPluginForm] = useState<CloudPluginFormState>({
    name: '',
    description: '',
    url: '',
    authMethod: 'none',
  })
  const [idePluginForm, setIdePluginForm] = useState<IDEPluginFormState>({
    name: '',
    description: '',
  })

  // 表单处理函数
  const handleCloudPluginFormChange = (field: string, value: unknown) => {
    setCloudPluginForm(prev => ({ ...prev, [field]: value }))
  }
  const handleIDEPluginFormChange = (field: string, value: unknown) => {
    setIdePluginForm(prev => ({ ...prev, [field]: value }))
  }
  const resetForm = (plugin?: Plugin | null) => {
    setCloudPluginForm({
      name: plugin?.name || '',
      description: plugin?.desc || '',
      url: plugin?.url || '',
      authMethod: 'none',
    })
  }
  const resetIDEForm = () => {
    setIdePluginForm({ name: '', description: '' })
  }
  const validateForm = () => {
    const errors: string[] = []
    if (!cloudPluginForm.name.trim()) errors.push(t('plugins.dialog.cloudPluginForm.validation.nameRequired'))
    if (!cloudPluginForm.description.trim()) errors.push(t('plugins.dialog.cloudPluginForm.validation.descRequired'))
    if (!cloudPluginForm.url.trim()) errors.push(t('plugins.dialog.cloudPluginForm.validation.urlRequired'))
    return { isValid: errors.length === 0, errors }
  }
  const validateIDEForm = () => {
    const errors: string[] = []
    if (!idePluginForm.name.trim()) errors.push(t('plugins.dialog.idePluginForm.validation.nameRequired'))
    if (!idePluginForm.description.trim()) errors.push(t('plugins.dialog.idePluginForm.validation.descRequired'))
    return { isValid: errors.length === 0, errors }
  }

  const getDefaultSpaceId = () => user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  const currentSpaceId = getDefaultSpaceId()

  // 数据获取
  const hasSearchOrFilter = (searchTerm && searchTerm.trim()) || categoryFilter !== 'all'
  const fetchPageSize = hasSearchOrFilter ? 100 : pageSize
  const fetchPage = hasSearchOrFilter ? 1 : currentPage

  const {
    data: pluginListData,
    isFetching: isPluginListLoading,
    error: pluginListError,
    refetch: refetchPluginList,
  } = usePluginList({
    space_id: currentSpaceId,
    page: fetchPage,
    size: fetchPageSize,
  })

  // 数据转换
  const transformPluginData = (pluginInfo: PluginInfo): Plugin => ({
    space_id: String(pluginInfo.space_id || ''),
    plugin_id: String(pluginInfo.plugin_id || ''),
    plugin_version: String(pluginInfo.plugin_version || ''),
    name: String(pluginInfo.name || ''),
    desc: String(pluginInfo.desc || ''),
    desc_mk: String((pluginInfo as unknown as Record<string, unknown>).desc_mk || ''),
    plugin_type: Number(pluginInfo.plugin_type || 1),
    published: Boolean(pluginInfo.published),
    url: String(pluginInfo.url || ''),
    icon_uri: String(pluginInfo.icon_uri || '📦'),
    status: 'active',
  })

  // 分页信息
  const pagination = (pluginListData?.data as Record<string, unknown>)?.pagination as { total?: number; total_pages?: number } | undefined
  const totalItems = pagination?.total || 0
  const totalPages = pagination?.total_pages || 1

  // 插件列表
  const [plugins, setPlugins] = useState<Plugin[]>([])

  useEffect(() => {
    if (pluginListData?.data?.plugin_infos) {
      setPlugins(pluginListData.data.plugin_infos.map(transformPluginData))
    }
  }, [pluginListData])

  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm, categoryFilter])

  // 插件类型文本
  const getPluginTypeText = (pluginType: number) => {
    switch (pluginType) {
      case 1:
        return t('plugins.types.cloud')
      case 2:
        return t('plugins.types.ide')
      default:
        return t('plugins.types.pluginTypeUnknown', { type: pluginType })
    }
  }

  // 分类选项
  const pluginTypeCategories = [t('plugins.types.cloud'), t('plugins.types.ide')]
  const categories = ['all', ...pluginTypeCategories]

  // 过滤插件
  const filteredPlugins = plugins.filter(plugin => {
    if (!plugin) return false
    const matchesSearch =
      (plugin.name?.toLowerCase() || '').includes((searchTerm || '').toLowerCase()) ||
      (plugin.desc?.toLowerCase() || '').includes((searchTerm || '').toLowerCase())
    const matchesCategory = categoryFilter === 'all' || getPluginTypeText(plugin.plugin_type) === categoryFilter
    return matchesSearch && matchesCategory
  })

  // 显示的插件
  const displayPlugins = hasSearchOrFilter ? filteredPlugins.slice((currentPage - 1) * pageSize, currentPage * pageSize) : filteredPlugins
  const displayTotalPages = hasSearchOrFilter ? Math.max(1, Math.ceil(filteredPlugins.length / pageSize)) : totalPages
  const displayTotalItems = hasSearchOrFilter ? filteredPlugins.length : totalItems

  useEffect(() => {
    if (hasSearchOrFilter && currentPage > displayTotalPages && displayTotalPages > 0) {
      setCurrentPage(1)
    }
  }, [hasSearchOrFilter, filteredPlugins.length, pageSize])

  // 插件图标渲染
  const renderPluginIcon = (icon: string) => {
    const isUrl = typeof icon === 'string' && (icon.startsWith('http://') || icon.startsWith('https://') || icon.startsWith('/') || icon.includes('.'))
    if (isUrl) {
      return (
        <img
          src={icon}
          alt="Plugin icon"
          className="w-full h-full object-cover rounded-lg"
          onError={e => {
            e.currentTarget.style.display = 'none'
          }}
        />
      )
    }
    return icon
  }

  // 插件操作
  const handlePluginAction = (action: string, plugin: Plugin) => {
    switch (action) {
      case 'view':
        setSelectedPlugin(plugin)
        setDetailDialogOpen(true)
        break
      case 'configure':
        if (plugin.plugin_id) {
          navigate(`/dashboard/plugins/${plugin.plugin_id}`)
        } else {
          showInfo(t('plugins.messages.configurationInDevelopment', { name: plugin.name }))
        }
        break
      case 'delete':
        setDeleteDialog({ isOpen: true, plugin })
        break
    }
  }

  const handleEditPlugin = (plugin: Plugin) => {
    setEditingPlugin(plugin)
    setIsEditDialogOpen(true)
    resetForm(plugin)
  }

  const handleDeletePlugin = async () => {
    if (deleteDialog.plugin) {
      try {
        if (deleteDialog.plugin.plugin_id) {
          const response = await deletePluginMutation.mutateAsync({
            space_id: getDefaultSpaceId(),
            plugin_id: deleteDialog.plugin.plugin_id,
            plugin_version: deleteDialog.plugin.plugin_version,
          })
          if (response.code === 200) {
            setDeleteDialog({ isOpen: false, plugin: null })
            refetchPluginList()
            showSuccess(t('plugins.messages.pluginDeleted', { name: deleteDialog.plugin.name }))
            return
          } else {
            showError(t('plugins.messages.deleteFailed') + ': ' + (response.message || t('plugins.errors.unknownError')))
          }
        } else {
          setDeleteDialog({ isOpen: false, plugin: null })
          refetchPluginList()
          showSuccess(t('plugins.messages.pluginDeleted', { name: deleteDialog.plugin.name }))
          return
        }
      } catch (error) {
        console.error(t('plugins.messages.deleteFailed'), error)
        showError(t('plugins.messages.deleteFailed'))
      } finally {
        if (deleteDialog.isOpen) {
          setDeleteDialog({ isOpen: false, plugin: null })
        }
      }
    }
  }

  const handlePluginSubmit = async (isEditing: boolean = false) => {
    const validation = validateForm()
    if (!validation.isValid) {
      showError(validation.errors[0])
      return
    }

    if (isEditing && editingPlugin) {
      refetchPluginList()
      showSuccess(t('plugins.messages.updateSuccess', { name: cloudPluginForm.name.trim() }))
      setIsEditDialogOpen(false)
      setEditingPlugin(null)
    } else {
      try {
        const response = await createPluginMutation.mutateAsync({
          name: cloudPluginForm.name.trim(),
          desc: cloudPluginForm.description.trim(),
          space_id: getDefaultSpaceId(),
          plugin_type: 1,
          url: cloudPluginForm.url.trim(),
          icon_uri: '☁️',
        })
        if (response.code === 200) {
          refetchPluginList()
          showSuccess(t('plugins.messages.cloudPluginInstallSuccess', { name: cloudPluginForm.name.trim() }))
          setCloudPluginDialogOpen(false)
        } else {
          showError(t('plugins.messages.createFailed', { message: response.message || t('plugins.messages.unknownError') }))
        }
      } catch (error) {
        console.error(t('plugins.messages.createPluginFailed'), error)
        showError(t('plugins.messages.createPluginError'))
      }
    }
    resetForm()
  }

  const handleIDEPluginSubmit = async () => {
    const validation = validateIDEForm()
    if (!validation.isValid) {
      showError(validation.errors[0])
      return
    }

    try {
      const pluginResponse = await createPluginMutation.mutateAsync({
        space_id: getDefaultSpaceId(),
        plugin_type: 2,
        name: idePluginForm.name.trim(),
        desc: idePluginForm.description.trim(),
        icon_uri: '💻',
      })
      if (pluginResponse.code === 200) {
        refetchPluginList()
        showSuccess(t('plugins.messages.idePluginCreated', { name: idePluginForm.name.trim() }) + ' ' + t('plugins.messages.ideCreationHint'))
        setIdePluginDialogOpen(false)
        resetIDEForm()
      } else {
        showError(t('plugins.messages.createFailed') + ': ' + (pluginResponse.message || t('plugins.errors.unknownError')))
      }
    } catch (error: any) {
      console.error(t('plugins.messages.ideCreateFailedRetry'), error)
      showError(t('plugins.messages.ideCreateFailedRetry'))
    }
  }

  const handleRefresh = () => {
    refetchPluginList()
  }

  // 刷新插件列表（路由变化时）
  useEffect(() => {
    refetchPluginList()
  }, [location.pathname])

  // 网格视图
  const gridView = useMemo(() => {
    if (displayPlugins.length === 0) {
      return <Empty searchTerm={searchTerm} type="plugins" onCreateClick={() => setInstallDialogOpen(true)} />
    }

    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {displayPlugins.map(plugin => (
          <ConfigCard
            key={plugin.plugin_id}
            id={plugin.plugin_id}
            icon={renderPluginIcon(plugin.icon_uri)}
            iconBgColor="bg-gradient-to-r from-blue-100 to-indigo-100"
            iconTextColor="text-blue-600"
            title={plugin.name}
            description={plugin.desc || t('plugins.noDescription')}
            tags={[
              { label: getPluginTypeText(plugin.plugin_type), color: '#3B82F6' },
            ]}
            editingState={editingState}
            actions={[
              {
                key: 'configure',
                label: t('plugins.actions.configure'),
                icon: <Settings className="w-4 h-4" />,
                onClick: () => handlePluginAction('configure', plugin),
              },
              ...(plugin.plugin_id?.startsWith('cloud_') ? [{
                key: 'edit',
                label: t('plugins.actions.edit'),
                icon: <Edit className="w-4 h-4" />,
                onClick: () => handleEditPlugin(plugin),
              }] : []),
              {
                key: 'delete',
                label: t('plugins.actions.delete'),
                icon: <Trash2 className="w-4 h-4" />,
                onClick: () => handlePluginAction('delete', plugin),
              },
            ]}
            onClick={() => handlePluginAction('configure', plugin)}
            footer={
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handlePluginAction('view', plugin)
                }}
                className="text-xs flex items-center gap-1"
                style={{ color: '#777777' }}
              >
                <Eye className="w-3 h-3" />
                {t('plugins.actions.view')}
              </button>
            }
          />
        ))}
      </div>
    )
  }, [displayPlugins, editingState, t, searchTerm])

  // 表格列定义
  const tableColumns: TableColumn<Plugin>[] = useMemo(
    () => [
      {
        key: 'plugin',
        title: t('plugins.tableView.columns.plugin'),
        dataIndex: 'name',
        width: 400,
        render: ({ row }) => (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center text-xl bg-gradient-to-r from-blue-100 to-indigo-100">
              {renderPluginIcon(row.icon_uri)}
            </div>
            <div className="min-w-0 flex-1">
              <div
                className="font-semibold text-gray-900 cursor-pointer truncate"
                onClick={() => handlePluginAction('configure', row)}
              >
                {row.name}
              </div>
              <div className="mt-1 text-xs text-gray-500 truncate">
                {row.desc || t('plugins.noDescription')}
              </div>
            </div>
          </div>
        ),
      },
      {
        key: 'type',
        title: t('plugins.tableView.columns.type'),
        dataIndex: 'plugin_type',
        width: 150,
        render: ({ row }) => (
          <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
            {getPluginTypeText(row.plugin_type)}
          </span>
        ),
      },
      {
        key: 'actions',
        title: t('plugins.tableView.columns.actions'),
        type: 'operate',
        align: 'right',
        width: 200,
        operations: [
          {
            key: 'view',
            icon: <Eye className="w-4 h-4" />,
            label: t('plugins.actions.view'),
            tooltip: t('plugins.actions.view'),
            onClick: row => handlePluginAction('view', row),
          },
          {
            key: 'configure',
            icon: <Settings className="w-4 h-4" />,
            label: t('plugins.actions.configure'),
            tooltip: t('plugins.actions.configure'),
            onClick: row => handlePluginAction('configure', row),
          },
          {
            key: 'delete',
            icon: <Trash2 className="w-4 h-4" />,
            label: t('plugins.actions.delete'),
            tooltip: t('plugins.actions.delete'),
            onClick: row => handlePluginAction('delete', row),
          },
        ],
      },
    ],
    [t],
  )

  // 列表视图
  const tableView = useMemo(() => {
    const tableData = { columns: tableColumns, rows: displayPlugins }
    return (
      <ConfigTable
        tableData={tableData}
        loading={isPluginListLoading}
        size="small"
        stickyHeader
        emptyState={<Empty searchTerm={searchTerm} type="plugins" onCreateClick={() => setInstallDialogOpen(true)} />}
      />
    )
  }, [tableColumns, displayPlugins, isPluginListLoading, searchTerm])

  // 工具栏左侧
  const toolbarLeft = useMemo(() => (
    <>
      <SearchInput searchTerm={searchTerm} placeholder={t('plugins.searchPlaceholder')} onChange={setSearchTerm} />
      <select
        value={categoryFilter}
        onChange={e => setCategoryFilter(e.target.value)}
        className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm focus:outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6] transition-colors"
      >
        <option value="all">{t('plugins.filters.allCategories')}</option>
        {categories.slice(1).map(category => (
          <option key={category} value={category}>{category}</option>
        ))}
      </select>
    </>
  ), [searchTerm, categoryFilter, categories, t])

  // 工具栏右侧
  const toolbarRight = useMemo(() => (
    <>
      <button
        onClick={handleRefresh}
        className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm font-medium hover:bg-[#f9fafb] hover:border-[#d1d5db] transition-colors flex items-center space-x-2"
      >
        <RefreshCw className="w-4 h-4" />
        <span>{t('plugins.actions.refresh')}</span>
      </button>
      <button
        onClick={() => setInstallDialogOpen(true)}
        className="btn-primary h-8 flex items-center gap-2 text-sm px-4"
      >
        <Plus className="w-4 h-4" />
        <span>{t('plugins.installPlugin')}</span>
      </button>
    </>
  ), [t])

  return (
    <>
      <CommonPageLayout
        title={t('plugins.title')}
        viewType={viewType}
        onViewTypeChange={(type) => setViewMode(type === 'grid' ? 'grid' : 'list')}
        pager={{
          total: displayTotalItems,
          currentPage,
          pageSize,
          pageSizeOptions: [20, 60, 100],
        }}
        onPagerChange={(page, size) => {
          setCurrentPage(page)
          setPageSize(size)
        }}
        loading={isPluginListLoading}
        error={pluginListError ? String(pluginListError) : null}
        gridView={gridView}
        tableView={tableView}
        toolbarLeft={toolbarLeft}
        toolbarRight={toolbarRight}
      />

      {/* 插件详情对话框 */}
      <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="md" fullWidth>
        {selectedPlugin && (
          <>
            <DialogTitle className="flex items-center space-x-3">
              <div className="w-12 h-12 rounded-lg flex items-center justify-center text-3xl bg-gray-100">
                {renderPluginIcon(selectedPlugin.icon_uri)}
              </div>
              <div>
                <Typography variant="h6">{selectedPlugin.name}</Typography>
              </div>
            </DialogTitle>
            <DialogContent>
              <div className="space-y-4">
                <div>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>{t('plugins.description')}</Typography>
                  <Typography variant="body1">{selectedPlugin.desc}</Typography>
                </div>
                {selectedPlugin.desc_mk && (
                  <div>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>{t('plugins.dialog.pluginDetails.basicInfo')}</Typography>
                    <div className="prose prose-sm max-w-none p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <ReactMarkdown>{selectedPlugin.desc_mk}</ReactMarkdown>
                    </div>
                  </div>
                )}
                <div>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>{t('plugins.url')}</Typography>
                  <Typography variant="body1" color="text.primary">{selectedPlugin.url}</Typography>
                </div>
              </div>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailDialogOpen(false)}>{t('common.buttons.close')}</Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* 安装插件对话框 */}
      <Dialog open={installDialogOpen} onClose={() => setInstallDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('plugins.dialog.installNewPlugin')}</DialogTitle>
        <DialogContent>
          <DialogContentText className="mb-4">{t('plugins.dialog.selectInstallMethod')}</DialogContentText>
          <div className="space-y-3">
            <Button
              variant="outlined"
              fullWidth
              disabled
              startIcon={<Upload className="w-4 h-4" />}
              className="justify-start p-3 opacity-60 cursor-not-allowed"
              sx={{ '&.Mui-disabled': { backgroundColor: '#f9fafb', borderColor: '#e5e7eb', color: '#6b7280' } }}
            >
              <div className="text-left">
                <div className="flex items-center justify-between w-full">
                  <Typography variant="subtitle1" className="text-gray-500">{t('plugins.uploadFile')}</Typography>
                  <div className="px-2 py-1 bg-yellow-100 border border-yellow-200 rounded-full">
                    <Typography variant="caption" className="text-yellow-700 font-medium">{t('plugins.comingSoon')}</Typography>
                  </div>
                </div>
                <Typography variant="body2" color="text.secondary" className="text-gray-400">{t('plugins.uploadFileDesc')}</Typography>
              </div>
            </Button>
            <Button
              variant="outlined"
              fullWidth
              startIcon={<Cloud className="w-4 h-4" />}
              onClick={() => { setCloudPluginDialogOpen(true); setInstallDialogOpen(false) }}
              className="justify-start p-3"
            >
              <div className="text-left">
                <Typography variant="subtitle1">{t('plugins.dialog.cloudPluginForm.title')}-{t('plugins.dialog.cloudPluginForm.subtitle')}</Typography>
                <Typography variant="body2" color="text.secondary">{t('plugins.cloudPlugin.createFromServiceDescription')}</Typography>
              </div>
            </Button>
            <Button
              variant="outlined"
              fullWidth
              startIcon={<Code className="w-4 h-4" />}
              onClick={() => { setIdePluginDialogOpen(true); setInstallDialogOpen(false) }}
              className="justify-start p-3"
            >
              <div className="text-left">
                <Typography variant="subtitle1">{t('plugins.types.ide')}-{t('plugins.cloudPlugin.createFromIDE')}</Typography>
                <Typography variant="body2" color="text.secondary">{t('plugins.cloudPlugin.createFromIDEDescription')}</Typography>
              </div>
            </Button>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInstallDialogOpen(false)}>{t('common.buttons.cancel')}</Button>
        </DialogActions>
      </Dialog>

      {/* 云插件表单对话框 */}
      <CloudPluginFormDialog
        open={cloudPluginDialogOpen || isEditDialogOpen}
        isEditing={isEditDialogOpen}
        loading={createPluginMutation.isLoading}
        form={cloudPluginForm}
        editingPlugin={null}
        onFormChange={handleCloudPluginFormChange}
        onSubmit={handlePluginSubmit}
        onCancel={() => {
          if (cloudPluginDialogOpen) setCloudPluginDialogOpen(false)
          if (isEditDialogOpen) { setIsEditDialogOpen(false); setEditingPlugin(null) }
          resetForm()
        }}
      />

      {/* IDE插件表单对话框 */}
      <IDEPluginFormDialog
        open={idePluginDialogOpen}
        isEditing={false}
        loading={createPluginMutation.isLoading}
        form={idePluginForm}
        editingPlugin={null}
        onFormChange={handleIDEPluginFormChange}
        onSubmit={() => handleIDEPluginSubmit()}
        onCancel={() => { setIdePluginDialogOpen(false); resetIDEForm() }}
      />

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialog.isOpen} onClose={() => setDeleteDialog({ isOpen: false, plugin: null })}>
        <DialogTitle>{t('plugins.dialog.confirmDelete')}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t('plugins.dialog.deleteConfirmMessage', { name: deleteDialog.plugin?.name })}</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ isOpen: false, plugin: null })} disabled={deletePluginMutation.isLoading}>
            {t('common.buttons.cancel')}
          </Button>
          <Button
            onClick={handleDeletePlugin}
            color="error"
            variant="contained"
            disabled={deletePluginMutation.isLoading}
            startIcon={deletePluginMutation.isLoading ? <CircularProgress size={16} /> : null}
          >
            {deletePluginMutation.isLoading ? t('common.buttons.deleting') : t('common.buttons.delete')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </>
  )
}

export default PluginManagementPageNew
