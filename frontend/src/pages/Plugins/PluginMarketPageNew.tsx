import React, { useState, useEffect, useMemo } from 'react'
import { useQueryClient } from 'react-query'
import { useTranslation } from 'react-i18next'
import { useCreatePlugin, usePluginList, usePluginCreateApi, usePluginUpdateApi, PluginInfo } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { usePluginMarketViewMode } from '../../stores/useUIStore'
import { ENV_CONFIG } from '../../config/environment'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import { usePluginMarketConfigs } from '../../hooks/usePluginMarketConfigs'
import ReactMarkdown from 'react-markdown'
import {
  Eye,
  Download,
  Check,
  RefreshCw,
} from 'lucide-react'
import { Button, Dialog, DialogTitle, DialogContent, DialogActions, Typography, CircularProgress, IconButton, Tooltip } from '@mui/material'
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
  tags?: string[]
}

const PluginMarketPageNew: React.FC = () => {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const { snackbar, showSuccess, showError, showWarning, closeSnackbar } = useUnifiedSnackbar()

  // 视图模式
  const [viewMode, setViewMode] = usePluginMarketViewMode()
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
  const [loading, setLoading] = useState(false)
  const [installingPluginId, setInstallingPluginId] = useState<string | null>(null)

  // 编辑状态（ConfigCard 需要但不会在市场页面使用）
  const editingState: EditingState = {
    id: null,
    field: null,
    value: '',
    isEditing: false,
  }

  // 市场插件配置
  const { marketPlugins, loading: marketLoading, error: marketError, refreshMarketPlugins, marketConfigUrl } = usePluginMarketConfigs()

  // API hooks
  const createPluginMutation = useCreatePlugin()
  const createPluginApiMutation = usePluginCreateApi()
  const updatePluginApiMutation = usePluginUpdateApi()

  const getDefaultSpaceId = () => user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  const currentSpaceId = getDefaultSpaceId()

  // 获取已安装插件列表（用于检查安装状态）
  const { data: pluginListData, isLoading: pluginListLoading, refetch: refetchPluginList } = usePluginList({
    space_id: currentSpaceId,
    page: 1,
    size: 100,
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

  // 已安装插件
  const [installedPlugins, setInstalledPlugins] = useState<Plugin[]>([])

  useEffect(() => {
    if (pluginListData?.data?.plugin_infos) {
      setInstalledPlugins(pluginListData.data.plugin_infos.map(transformPluginData))
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

  // 过滤市场插件
  const filteredMarketPlugins = (marketPlugins || []).filter(plugin => {
    if (!plugin) return false
    const matchesSearch =
      (plugin.name?.toLowerCase() || '').includes((searchTerm || '').toLowerCase()) ||
      (plugin.desc?.toLowerCase() || '').includes((searchTerm || '').toLowerCase()) ||
      (plugin.tags || []).some(tag => tag?.toLowerCase().includes((searchTerm || '').toLowerCase()))
    const matchesCategory = categoryFilter === 'all' || getPluginTypeText(plugin.plugin_type) === categoryFilter
    return matchesSearch && matchesCategory
  })

  // 分页后的插件
  const displayPlugins = filteredMarketPlugins.slice((currentPage - 1) * pageSize, currentPage * pageSize)
  const displayTotalItems = filteredMarketPlugins.length

  useEffect(() => {
    const displayTotalPages = Math.max(1, Math.ceil(filteredMarketPlugins.length / pageSize))
    if (currentPage > displayTotalPages && displayTotalPages > 0) {
      setCurrentPage(1)
    }
  }, [filteredMarketPlugins.length, pageSize])

  // 检查插件是否已安装
  const isPluginInstalled = (plugin: Plugin) => {
    if (!plugin) return false
    return installedPlugins.some(
      p =>
        p.plugin_id === plugin.plugin_id ||
        (p.name === plugin.name && p.plugin_type === plugin.plugin_type),
    )
  }

  // 安装插件
  const handleInstallPlugin = async (plugin: Plugin) => {
    if (isPluginInstalled(plugin)) {
      showWarning(t('plugins.messages.pluginAlreadyInstalled', { name: plugin.name }))
      return
    }

    setInstallingPluginId(plugin.plugin_id)

    if (plugin.config) {
      try {
        const request = {
          name: plugin.name.trim(),
          desc: plugin.desc.trim(),
          space_id: getDefaultSpaceId(),
          plugin_type: plugin.plugin_type,
          url: marketConfigUrl || ENV_CONFIG.PLUGIN_SERVICE_URL,
          icon_uri: plugin.icon_uri,
        }

        const response = await createPluginMutation.mutateAsync(request)

        if (response.code === 200) {
          const pluginId = response.data.plugin_id

          // 创建 API
          const tools = (plugin.config as { tools?: Array<Record<string, unknown>> })?.tools || []
          const apiCreationPromises = tools.map(async (tool: Record<string, unknown>) => {
            try {
              const toolName = String(tool.name || '')
              const toolDesc = String(tool.description || '')
              const toolPath = String(tool.path || '')
              const toolMethod = String(tool.method || 'GET')
              const apiRequest = {
                space_id: getDefaultSpaceId(),
                plugin_id: pluginId,
                name: toolName,
                desc: toolDesc,
                path: toolPath,
                method: toolMethod === 'GET' ? 1 : toolMethod === 'POST' ? 2 : 1,
              }

              const apiResponse = await createPluginApiMutation.mutateAsync(apiRequest)

              if (apiResponse.code === 200) {
                const toolId = apiResponse.data.tool_id

                const requestParams = tool.request_params
                  ? Object.entries(tool.request_params as Record<string, unknown>).map(([key, param]) => {
                      const p = param as Record<string, unknown>
                      return {
                        name: key,
                        desc: String(p.description || key),
                        type: p.type === 'string' ? 1 : p.type === 'integer' ? 2 : p.type === 'boolean' ? 3 : 1,
                        is_required: Boolean(p.required),
                        is_runtime: false,
                        value: '',
                        method: 0,
                        priority: 1,
                      }
                    })
                  : []

                const updateApiRequest = {
                  space_id: getDefaultSpaceId(),
                  plugin_id: pluginId,
                  tool_id: toolId,
                  name: toolName,
                  desc: toolDesc,
                  path: toolPath,
                  method: toolMethod === 'GET' ? 1 : toolMethod === 'POST' ? 2 : 1,
                  plugin_version: '',
                  request_params: requestParams,
                  response_params: [],
                  headers: [],
                }

                return await updatePluginApiMutation.mutateAsync(updateApiRequest)
              }
              return null
            } catch (error) {
              console.error(`Failed to create API for tool ${String(tool.name || '')}:`, error)
              return null
            }
          })

          const results = await Promise.allSettled(apiCreationPromises)
          const successCount = results.filter(r => r.status === 'fulfilled' && (r as PromiseFulfilledResult<{ code?: number } | null>).value?.code === 200).length
          const totalTools = tools.length

          await queryClient.invalidateQueries({ queryKey: ['pluginList', currentSpaceId], exact: false })
          await refetchPluginList()

          if (successCount === totalTools) {
            showSuccess(t('plugins.messages.pluginInstalled', { name: plugin.name }) + ' ' + t('plugins.messages.allApisConfigured', { count: totalTools }))
          } else if (successCount > 0) {
            showWarning(
              t('plugins.messages.pluginInstalled', { name: plugin.name }) +
                ' ' +
                t('plugins.messages.partialApisConfigured', { success: successCount, total: totalTools }),
            )
          } else {
            showError(t('plugins.messages.cloudPluginCreated', { name: plugin.name }) + ' ' + t('plugins.messages.allApisFailed'))
          }
        } else {
          showError(t('plugins.messages.installFailed') + ': ' + (response.message || t('plugins.errors.unknownError')))
        }
      } catch (error) {
        console.error(t('plugins.messages.installFailed'), error)
        showError(t('plugins.messages.installFailed'))
      } finally {
        setInstallingPluginId(null)
      }
    }
  }

  // 查看插件详情
  const handleViewPlugin = (plugin: Plugin) => {
    setSelectedPlugin(plugin)
    setDetailDialogOpen(true)
  }

  // 刷新
  const handleRefresh = async () => {
    setLoading(true)
    try {
      await refreshMarketPlugins()
      await queryClient.invalidateQueries({ queryKey: ['pluginList', currentSpaceId], exact: false })
      await refetchPluginList()
      showSuccess(t('plugins.messages.marketRefreshed'))
    } catch (error) {
      console.error('Failed to refresh plugin configurations:', error)
      showError(t('plugins.messages.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  // 插件图标渲染
  const renderPluginIcon = (icon: string | undefined) => {
    if (!icon) return '📦'
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

  // 网格视图
  const gridView = useMemo(() => {
    if (displayPlugins.length === 0) {
      return <Empty searchTerm={searchTerm} type="plugins" />
    }

    return (
      <div className="grid grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {displayPlugins
          .filter(plugin => plugin && plugin.plugin_id)
          .map(plugin => {
            const installed = isPluginInstalled(plugin)
            const isInstalling = installingPluginId === plugin.plugin_id
            const checkingInstall = pluginListLoading

            return (
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
                actions={[]}
                onClick={() => handleViewPlugin(plugin)}
                footer={
                  <div className="flex items-center justify-between w-full">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleViewPlugin(plugin)
                      }}
                      className="text-xs flex items-center gap-1"
                      style={{ color: '#777777' }}
                    >
                      <Eye className="w-3 h-3" />
                      {t('plugins.actions.view')}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (!installed && !isInstalling && !checkingInstall) {
                          handleInstallPlugin(plugin)
                        }
                      }}
                      disabled={installed || isInstalling || checkingInstall}
                      className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1 ${
                        installed
                          ? 'bg-green-100 text-green-700 cursor-default'
                          : isInstalling
                            ? 'bg-gray-100 text-gray-500 cursor-wait'
                            : checkingInstall
                              ? 'bg-gray-100 text-gray-500 cursor-wait'
                              : 'bg-blue-500 text-white hover:bg-blue-600'
                      }`}
                    >
                      {checkingInstall ? (
                        <>
                          <CircularProgress size={12} sx={{ color: 'inherit' }} />
                          {t('plugins.loading')}
                        </>
                      ) : isInstalling ? (
                        <>
                          <CircularProgress size={12} sx={{ color: 'inherit' }} />
                          {t('plugins.messages.installing')}
                        </>
                      ) : installed ? (
                        <>
                          <Check className="w-3 h-3" />
                          {t('plugins.actions.installed')}
                        </>
                      ) : (
                        <>
                          <Download className="w-3 h-3" />
                          {t('plugins.actions.install')}
                        </>
                      )}
                    </button>
                  </div>
                }
              />
            )
          })}
      </div>
    )
  }, [displayPlugins, editingState, t, searchTerm, installedPlugins, installingPluginId, pluginListLoading])

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
                onClick={() => handleViewPlugin(row)}
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
        align: 'left',
        width: 200,
        render: ({ row }) => {
          const installed = isPluginInstalled(row)
          const isInstalling = installingPluginId === row.plugin_id
          const checkingInstall = pluginListLoading
          return (
            <div className="flex items-center justify-start gap-2">
              <Tooltip title={t('plugins.actions.view')}>
                <IconButton
                  size="small"
                  onClick={() => handleViewPlugin(row)}
                  sx={{ color: '#777777' }}
                >
                  <Eye className="w-4 h-4" />
                </IconButton>
              </Tooltip>
              <button
                onClick={() => !installed && !isInstalling && !checkingInstall && handleInstallPlugin(row)}
                disabled={installed || isInstalling || checkingInstall}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1 ${
                  installed
                    ? 'bg-green-100 text-green-700 cursor-default'
                    : isInstalling
                      ? 'bg-gray-100 text-gray-500 cursor-wait'
                      : checkingInstall
                        ? 'bg-gray-100 text-gray-500 cursor-wait'
                        : 'bg-blue-500 text-white hover:bg-blue-600'
                }`}
              >
                {checkingInstall ? (
                  <>
                    <CircularProgress size={12} sx={{ color: 'inherit' }} />
                    {t('plugins.loading')}
                  </>
                ) : isInstalling ? (
                  <>
                    <CircularProgress size={12} sx={{ color: 'inherit' }} />
                    {t('plugins.messages.installing')}
                  </>
                ) : installed ? (
                  <>
                    <Check className="w-3 h-3" />
                    {t('plugins.actions.installed')}
                  </>
                ) : (
                  <>
                    <Download className="w-3 h-3" />
                    {t('plugins.actions.install')}
                  </>
                )}
              </button>
            </div>
          )
        },
      },
    ],
    [t, installedPlugins, installingPluginId, pluginListLoading],
  )

  // 列表视图
  const tableView = useMemo(() => {
    const tableData = { columns: tableColumns, rows: displayPlugins }
    return (
      <ConfigTable
        tableData={tableData}
        loading={marketLoading}
        size="small"
        stickyHeader
        emptyState={<Empty searchTerm={searchTerm} type="plugins" />}
      />
    )
  }, [tableColumns, displayPlugins, marketLoading, searchTerm])

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
    <button
      onClick={handleRefresh}
      disabled={loading || marketLoading}
      className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm font-medium hover:bg-[#f9fafb] hover:border-[#d1d5db] transition-colors flex items-center space-x-2"
    >
      {loading || marketLoading ? <CircularProgress size={16} /> : <RefreshCw className="w-4 h-4" />}
      <span>{t('plugins.actions.refresh')}</span>
    </button>
  ), [loading, marketLoading, t])

  return (
    <>
      <CommonPageLayout
        title={t('plugins.tabs.market')}
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
        loading={marketLoading}
        error={marketError || null}
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
                {selectedPlugin.tags && selectedPlugin.tags.length > 0 && (
                  <div>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>{t('plugins.dialog.pluginDetails.tags')}</Typography>
                    <div className="flex flex-wrap gap-2">
                      {selectedPlugin.tags.map(tag => (
                        <span key={tag} className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">{tag}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailDialogOpen(false)}>{t('common.buttons.close')}</Button>
              {pluginListLoading ? (
                <Button disabled variant="contained" startIcon={<CircularProgress size={16} sx={{ color: 'inherit' }} />}>
                  {t('plugins.loading')}
                </Button>
              ) : !isPluginInstalled(selectedPlugin) ? (
                <Button
                  onClick={() => {
                    handleInstallPlugin(selectedPlugin)
                    setDetailDialogOpen(false)
                  }}
                  variant="contained"
                  startIcon={<Download className="w-4 h-4" />}
                >
                  {t('plugins.actions.install')}
                </Button>
              ) : null}
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </>
  )
}

export default PluginMarketPageNew
