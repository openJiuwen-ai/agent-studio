import React, { useState, useEffect } from 'react'
import { useQueryClient } from 'react-query'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useCreatePlugin, usePluginList, useDeletePlugin, usePluginCreateApi, usePluginUpdateApi, PluginInfo } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { usePluginViewMode } from '../../stores/useUIStore'
import { ENV_CONFIG } from '../../config/environment'
import { useCloudPluginForm } from '../../hooks/useCloudPluginForm'
import { useIDEPluginForm } from '../../hooks/useIDEPluginForm'
import CloudPluginFormDialog from '../../components/Plugins/CloudPluginFormDialog'
import IDEPluginFormDialog from '../../components/Plugins/IDEPluginFormDialog'
import MarketPluginList from '../../components/Plugins/MarketPluginList'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import { usePluginMarketConfigs } from '../../hooks/usePluginMarketConfigs'
import ReactMarkdown from 'react-markdown'
import {
  Plug,
  Plus,
  Search,
  Settings,
  Download,
  Upload,
  Trash2,
  AlertTriangle,
  Grid,
  List,
  Eye,
  Edit,
  RefreshCw,
  Cloud,
  Code,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { Button, Menu, MenuItem, Dialog, DialogTitle, DialogContent, DialogActions, DialogContentText, Typography, CircularProgress } from '@mui/material'
import { scrollToTop, resetScrollOnNavigation } from '../../utils/scrollUtils'

interface Plugin extends PluginInfo {
  // Extend PluginInfo with UI-specific fields
  status?: 'active' | 'inactive' | 'error' | 'updating'
  config?: any // Store original configuration data
}

const PluginManagementPage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState(0)
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [viewMode, setViewMode] = usePluginViewMode()
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(9)
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [installDialogOpen, setInstallDialogOpen] = useState(false)
  const [deleteDialog, setDeleteDialog] = useState<{
    isOpen: boolean
    plugin: Plugin | null
  }>({
    isOpen: false,
    plugin: null,
  })
  const { snackbar, showSuccess, showError, showWarning, showInfo, closeSnackbar } = useUnifiedSnackbar()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [loading, setLoading] = useState(false)

  // Use the new market configs hook
  const { marketPlugins, loading: marketLoading, error: marketError, refreshMarketPlugins, marketConfigUrl } = usePluginMarketConfigs()

  // Plugin creation and configuration hooks
  const createPluginMutation = useCreatePlugin()
  const createPluginApiMutation = usePluginCreateApi()
  const updatePluginApiMutation = usePluginUpdateApi()
  const deletePluginMutation = useDeletePlugin()
  const queryClient = useQueryClient()
  const { user } = useAuthStore()

  const getDefaultSpaceId = () => {
    return user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  }

  // Cloud plugin creation dialog state
  const [cloudPluginDialogOpen, setCloudPluginDialogOpen] = useState(false)

  // IDE plugin creation dialog state
  const [idePluginDialogOpen, setIdePluginDialogOpen] = useState(false)

  // Edit plugin state
  const [editingPlugin, setEditingPlugin] = useState<Plugin | null>(null)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)

  // Form management
  const { form: cloudPluginForm, handleFormChange: handleCloudPluginFormChange, resetForm, validateForm } = useCloudPluginForm(editingPlugin)

  // IDE plugin form management
  const { form: idePluginForm, handleFormChange: handleIDEPluginFormChange, resetForm: resetIDEForm, validateForm: validateIDEForm } = useIDEPluginForm()

  // Use the usePluginList hook to fetch plugins for the current space
  const currentSpaceId = getDefaultSpaceId()

  // When searching, fetch all data with a large page size for client-side filtering
  // Otherwise, use normal pagination
  // Note: Backend API has a max pageSize limit of 100
  const hasSearchOrFilter = (searchTerm && searchTerm.trim()) || categoryFilter !== 'all'
  const fetchPageSize = hasSearchOrFilter ? 100 : pageSize
  const fetchPage = hasSearchOrFilter ? 1 : currentPage

  const {
    data: pluginListData,
    isLoading: isPluginListLoading,
    error: pluginListError,
    refetch: refetchPluginList,
  } = usePluginList({
    space_id: currentSpaceId,
    page: fetchPage,
    size: fetchPageSize,
  })

  // Transform API data to Plugin interface
  const transformPluginData = (pluginInfo: Record<string, unknown>): Plugin => {
    return {
      space_id: pluginInfo.space_id || '',
      plugin_id: pluginInfo.plugin_id || '',
      plugin_version: pluginInfo.plugin_version || '',
      name: pluginInfo.name || pluginInfo.plugin_name || '',
      desc: pluginInfo.desc || pluginInfo.description || pluginInfo.plugin_desc || '',
      desc_mk: pluginInfo.desc_mk || '',
      plugin_type: pluginInfo.plugin_type || 1,
      published: pluginInfo.published || false,
      url: pluginInfo.url || '',
      icon_uri: pluginInfo.icon_uri || pluginInfo.plugin_icon || pluginInfo.icon || '📦',
      status: pluginInfo.plugin_status === 'active' ? 'active' : 'inactive',
    }
  }

  // Extract pagination info from API response
  const pagination = pluginListData?.data?.pagination
  const totalItems = pagination?.total || 0
  const totalPages = pagination?.total_pages || 1

  // Installed plugins - use API data or fallback to empty array
  const [plugins, setPlugins] = useState<Plugin[]>(() => {
    if (pluginListData?.data?.plugin_infos) {
      return pluginListData.data.plugin_infos.map(transformPluginData)
    }
    return []
  })

  // Update plugins when API data changes
  useEffect(() => {
    if (pluginListData?.data?.plugin_infos) {
      const transformedPlugins = pluginListData.data.plugin_infos.map(transformPluginData)
      setPlugins(transformedPlugins)
    }
  }, [pluginListData])

  // Reset to first page when search or filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm, categoryFilter])

  // Initialize scroll position when page loads
  useEffect(() => {
    scrollToTop()
  }, [])

  // Helper function to get plugin type text
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

  // Get all plugin type categories - always show all available plugin types regardless of current filters
  const pluginTypeCategories = [t('plugins.types.cloud'), t('plugins.types.ide')]
  const categories = ['all', ...pluginTypeCategories]

  // Filter plugins - Apply search and filter to all fetched plugins
  // When searching, we fetch all data (up to 1000) so we can search across all plugins
  const filteredPlugins = plugins.filter(plugin => {
    if (!plugin) return false
    const matchesSearch =
      (plugin.name?.toLowerCase() || '').includes((searchTerm || '').toLowerCase()) ||
      (plugin.desc?.toLowerCase() || '').includes((searchTerm || '').toLowerCase())
    const matchesCategory = categoryFilter === 'all' || getPluginTypeText(plugin.plugin_type) === categoryFilter
    return matchesSearch && matchesCategory
  })

  // If there's a search term or category filter, use client-side pagination
  // Otherwise, use server-side pagination from API
  const displayPlugins = hasSearchOrFilter ? filteredPlugins.slice((currentPage - 1) * pageSize, currentPage * pageSize) : filteredPlugins
  const displayTotalPages = hasSearchOrFilter ? Math.max(1, Math.ceil(filteredPlugins.length / pageSize)) : totalPages
  const displayTotalItems = hasSearchOrFilter ? filteredPlugins.length : totalItems

  // Reset to first page if current page exceeds total pages after filtering
  useEffect(() => {
    if (hasSearchOrFilter && currentPage > displayTotalPages && displayTotalPages > 0) {
      setCurrentPage(1)
    }
  }, [hasSearchOrFilter, filteredPlugins.length, pageSize])

  // Filter and sort market plugins

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue)
  }

  const handlePluginAction = (action: string, plugin: Plugin) => {
    switch (action) {
      case 'view':
        setSelectedPlugin(plugin)
        setDetailDialogOpen(true)
        break
      case 'configure':
        // For cloud plugins, navigate to configuration page
        if (plugin.plugin_id) {
          // Reset scroll before navigation
          resetScrollOnNavigation()
          navigate(`/dashboard/plugins/${plugin.plugin_id}`)
        } else {
          setSelectedPlugin(plugin)
          showInfo(t('plugins.messages.configurationInDevelopment', { name: plugin.name }))
        }
        break
      case 'toggle': {
        const newStatus = plugin.status === 'active' ? 'inactive' : 'active'
        setPlugins(prev => prev.map(p => (p.plugin_id === plugin.plugin_id ? { ...p, status: newStatus as Plugin['status'] } : p)))
        showSuccess(`${plugin.name} ${newStatus === 'active' ? t('plugins.messages.enabled') : t('plugins.messages.disabled')}`)
        break
      }
      case 'delete':
        setDeleteDialog({ isOpen: true, plugin })
        break
      case 'copy':
        showSuccess(t('plugins.messages.pluginCopied', { name: plugin.name }))
        break
    }
  }

  const handleDeletePlugin = async () => {
    if (deleteDialog.plugin) {
      try {
        // Only call API for cloud plugins (those with plugin_id)
        if (deleteDialog.plugin.plugin_id) {
          const request = {
            space_id: getDefaultSpaceId(),
            plugin_id: deleteDialog.plugin.plugin_id,
            plugin_version: deleteDialog.plugin.plugin_version,
          }

          const response = await deletePluginMutation.mutateAsync(request)

          if (response.code === 200) {
            // Close dialog immediately after successful deletion
            setDeleteDialog({ isOpen: false, plugin: null })
            // Refresh plugin list in background
            queryClient.invalidateQueries({
              queryKey: ['pluginList', currentSpaceId],
              exact: false, // Match all queries starting with ['pluginList', currentSpaceId]
            })
            refetchPluginList()
            showSuccess(t('plugins.messages.pluginDeleted', { name: deleteDialog.plugin.name }))
            return
          } else {
            showError(t('plugins.errors.deleteFailed') + ': ' + (response.message || t('plugins.errors.unknownError')))
          }
        } else {
          // For non-cloud plugins, refresh the list
          // Close dialog immediately
          setDeleteDialog({ isOpen: false, plugin: null })
          // Refresh plugin list in background
          queryClient.invalidateQueries({
            queryKey: ['pluginList', currentSpaceId],
            exact: false, // Match all queries starting with ['pluginList', currentSpaceId]
          })
          refetchPluginList()
          showSuccess(t('plugins.messages.pluginDeleted', { name: deleteDialog.plugin.name }))
          return
        }
      } catch (error) {
        console.error(t('plugins.messages.deleteFailed'), error)
        showError(t('plugins.messages.deleteFailed'))
      } finally {
        // Close dialog in case of error
        if (deleteDialog.isOpen) {
          setDeleteDialog({ isOpen: false, plugin: null })
        }
      }
    }
  }

  // Check if plugin is already installed using both original plugin_id and name for better tracking
  const isPluginAlreadyInstalled = (plugin: Plugin) => {
    return plugins.some(
      p =>
        // Check by plugin_id for API plugins
        p.plugin_id === plugin.plugin_id ||
        // Check by name for market plugins that might have different IDs after installation
        (p.name === plugin.name && p.plugin_type === plugin.plugin_type),
    )
  }

  const handleInstallPlugin = async (plugin: Plugin) => {
    // Check if plugin is already installed
    if (isPluginAlreadyInstalled(plugin)) {
      showWarning(t('plugins.messages.pluginAlreadyInstalled', { name: plugin.name }))
      return
    }

    // If plugin has configuration data, use it for installation
    if (plugin.config) {
      try {
        const request = {
          name: plugin.name.trim(),
          desc: plugin.desc.trim(),
          space_id: getDefaultSpaceId(),
          plugin_type: plugin.plugin_type, // Use plugin_type from config
          url: marketConfigUrl || ENV_CONFIG.PLUGIN_SERVICE_URL, // Use market config URL with fallback
          icon_uri: plugin.icon_uri,
        }

        const response = await createPluginMutation.mutateAsync(request)

        if (response.code === 200) {
          const pluginId = response.data.plugin_id

          // Create APIs based on the plugin configuration
          const apiCreationPromises = plugin.config.tools.map(async (tool: any) => {
            try {
              const apiRequest = {
                space_id: getDefaultSpaceId(),
                plugin_id: pluginId,
                name: tool.name,
                desc: tool.description,
                path: tool.path,
                method: tool.method === 'GET' ? 1 : tool.method === 'POST' ? 2 : 1,
              }

              const apiResponse = await createPluginApiMutation.mutateAsync(apiRequest)

              if (apiResponse.code === 200) {
                const toolId = apiResponse.data.tool_id

                // Transform request parameters for API update
                const requestParams = tool.request_params
                  ? Object.entries(tool.request_params).map(([key, param]: [string, any]) => ({
                      name: key,
                      desc: param.description || key,
                      type: param.type === 'string' ? 1 : param.type === 'integer' ? 2 : param.type === 'boolean' ? 3 : 1,
                      is_required: param.required || false,
                      is_runtime: false,
                      value: '',
                      method: 0,
                      priority: 1,
                    }))
                  : []

                const updateApiRequest = {
                  space_id: getDefaultSpaceId(),
                  plugin_id: pluginId,
                  tool_id: toolId,
                  name: tool.name,
                  desc: tool.description,
                  path: tool.path,
                  method: tool.method === 'GET' ? 1 : tool.method === 'POST' ? 2 : 1,
                  plugin_version: '',
                  request_params: requestParams,
                  response_params: [],
                  headers: [],
                }

                return await updatePluginApiMutation.mutateAsync(updateApiRequest)
              }
              return null
            } catch (error) {
              console.error(`Failed to create API for tool ${tool.name}:`, error)
              return null
            }
          })

          const results = await Promise.allSettled(apiCreationPromises)
          const successCount = results.filter(r => r.status === 'fulfilled' && r.value?.code === 200).length
          const totalTools = plugin.config.tools.length

          // Refresh the plugin list from server to ensure consistency
          // Invalidate all pluginList queries for this space (regardless of page/size)
          await queryClient.invalidateQueries({
            queryKey: ['pluginList', currentSpaceId],
            exact: false, // Match all queries starting with ['pluginList', currentSpaceId]
          })
          // Explicitly refetch to update the UI immediately
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
      }
      return
    }
  }

  const handleEditPlugin = (plugin: Plugin) => {
    setEditingPlugin(plugin)
    setIsEditDialogOpen(true)
    resetForm(plugin)
  }

  const handlePluginSubmit = async (isEditing: boolean = false) => {
    // Validate required fields
    const validation = validateForm()
    if (!validation.isValid) {
      showError(validation.errors[0])
      return
    }

    if (isEditing && editingPlugin) {
      // Update existing plugin
      const updatedPlugin: Plugin = {
        ...editingPlugin,
        name: cloudPluginForm.name.trim(),
        desc: cloudPluginForm.description.trim(),
        url: cloudPluginForm.url.trim(),
      }

      // Here you would typically send the data to your backend API
      console.log('Updating plugin:', updatedPlugin)

      // Refresh the plugin list from server to ensure consistency
      await queryClient.invalidateQueries({
        queryKey: ['pluginList', currentSpaceId],
        exact: false, // Match all queries starting with ['pluginList', currentSpaceId]
      })
      // Explicitly refetch to update the UI immediately
      await refetchPluginList()

      showSuccess(t('plugins.messages.updateSuccess', { name: updatedPlugin.name }))
      setIsEditDialogOpen(false)
      setEditingPlugin(null)
    } else {
      try {
        // Create new plugin using API
        const request = {
          name: cloudPluginForm.name.trim(),
          desc: cloudPluginForm.description.trim(),
          desc_mk: cloudPluginForm.desc_mk?.trim(),
          space_id: getDefaultSpaceId(),
          plugin_type: 1, // Cloud plugin type
          url: cloudPluginForm.url.trim(), // Add URL field from API configuration
          icon_uri: '☁️', // Default icon, can be changed in configuration
        }

        const response = await createPluginMutation.mutateAsync(request)

        if (response.code === 200) {
          // Refresh the plugin list from server to ensure consistency
          await queryClient.invalidateQueries({
            queryKey: ['pluginList', currentSpaceId],
            exact: false, // Match all queries starting with ['pluginList', currentSpaceId]
          })
          // Explicitly refetch to update the UI immediately
          await refetchPluginList()

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

    // Reset form
    resetForm()
  }

  const handleIDEPluginSubmit = async () => {
    // Validate required fields
    const validation = validateIDEForm()
    if (!validation.isValid) {
      showError(validation.errors[0])
      return
    }

    try {
      // Create plugin using the create interface only (no create_code call)
      const pluginRequest = {
        space_id: getDefaultSpaceId(),
        plugin_type: 2, // Code plugin type (IDE plugin)
        name: idePluginForm.name.trim(),
        desc: idePluginForm.description.trim(),
        desc_mk: idePluginForm.desc_mk?.trim(),
        icon_uri: '💻',
      }

      const pluginResponse = await createPluginMutation.mutateAsync(pluginRequest)

      if (pluginResponse.code === 200) {
        const pluginId = pluginResponse.data.plugin_id

        // Refresh the plugin list from server to ensure consistency
        await queryClient.invalidateQueries({
          queryKey: ['pluginList', currentSpaceId],
          exact: false, // Match all queries starting with ['pluginList', currentSpaceId]
        })
        // Explicitly refetch to update the UI immediately
        await refetchPluginList()

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

  const getStatusColor = (status: Plugin['status']) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'inactive':
        return 'default'
      case 'error':
        return 'error'
      case 'updating':
        return 'warning'
      default:
        return 'default'
    }
  }

  const getStatusText = (status: Plugin['status']) => {
    switch (status) {
      case 'active':
        return t('plugins.status.active')
      case 'inactive':
        return t('plugins.status.inactive')
      case 'error':
        return t('plugins.status.error')
      case 'updating':
        return t('plugins.status.updating')
      default:
        return t('plugins.status.unknown')
    }
  }

  // Helper function to render plugin icon (supports both emoji and image URLs)
  const renderPluginIcon = (icon: string, className: string = 'w-12 h-12 rounded-lg flex items-center justify-center text-2xl bg-gray-100') => {
    // Check if the icon is a URL (starts with http:// or https:// or is a relative path)
    const isUrl = typeof icon === 'string' && (icon.startsWith('http://') || icon.startsWith('https://') || icon.startsWith('/') || icon.includes('.'))

    if (isUrl) {
      return (
        <div className={className}>
          <img
            src={icon}
            alt="Plugin icon"
            className="w-full h-full object-cover rounded-lg"
            onError={e => {
              // Fallback to default icon if image fails to load
              e.currentTarget.style.display = 'none'
              const fallback = document.createElement('span')
              fallback.textContent = '📦'
              fallback.className = 'w-full h-full flex items-center justify-center text-2xl'
              e.currentTarget.parentElement?.appendChild(fallback)
            }}
          />
        </div>
      )
    }

    // Default emoji rendering
    return <div className={className}>{icon}</div>
  }

  const renderPluginCard = (plugin: Plugin, index: number = 0) => (
    <div
      key={plugin.plugin_id}
      className="group bg-white rounded-2xl shadow-sm hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-2 border border-gray-100 overflow-hidden"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      {/* Gradient top border - 与智能体和工作流卡片统一 */}
      <div className="h-1 bg-gradient-to-r from-blue-500 to-indigo-600" />

      {/* Plugin header */}
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3 w-full">
            {renderPluginIcon(
              plugin.icon_uri,
              'w-12 h-12 rounded-xl flex items-center justify-center text-2xl bg-gradient-to-r from-blue-100 to-indigo-100 group-hover:scale-110 transition-transform duration-300 border border-blue-200',
            )}
            <div className="min-w-0 flex-1 overflow-hidden">
              <h3
                className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800 overflow-hidden text-ellipsis whitespace-nowrap max-w-[calc(100%-20px)]"
                title={plugin.name}
              >
                {plugin.name}
              </h3>
              <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                {getPluginTypeText(plugin.plugin_type)}
              </span>
            </div>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 mb-4 leading-relaxed overflow-hidden text-ellipsis whitespace-nowrap max-w-full" title={plugin.desc}>
          {plugin.desc || t('plugins.noDescription')}
        </p>

        {/* Error Alert */}
        {plugin.status === 'error' && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl">
            <div className="flex items-center text-red-600 text-sm">
              <AlertTriangle className="w-4 h-4 mr-2" />
              {t('plugins.actions.pluginError')}
            </div>
          </div>
        )}
      </div>

      {/* Actions - 与智能体和工作流卡片统一 */}
      <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-blue-50 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handlePluginAction('view', plugin)}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
              title={t('plugins.actions.view')}
            >
              <Eye className="w-4 h-4" />
            </button>
            <button
              onClick={() => handlePluginAction('configure', plugin)}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
              title={t('plugins.actions.configure')}
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center space-x-2">
            {plugin.plugin_id && plugin.plugin_id.startsWith('cloud_') && (
              <button
                onClick={() => handleEditPlugin(plugin)}
                className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-xl transition-all duration-200"
                title={t('plugins.actions.edit')}
              >
                <Edit className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => handlePluginAction('delete', plugin)}
              className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200"
              title={t('plugins.actions.delete')}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  const renderPluginList = (plugin: Plugin) => (
    <div key={plugin.plugin_id} className="bg-white rounded-xl shadow-sm hover:shadow-sm transition-all duration-300 border border-gray-100 overflow-hidden">
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            {renderPluginIcon(
              plugin.icon_uri,
              'w-12 h-12 rounded-xl flex items-center justify-center text-2xl bg-gradient-to-r from-blue-100 to-indigo-100 border border-blue-200',
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-3 mb-1">
                <h4
                  className="font-bold text-lg text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800 truncate max-w-[300px]"
                  title={plugin.name}
                >
                  {plugin.name}
                </h4>
                <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full flex-shrink-0">
                  {getPluginTypeText(plugin.plugin_type)}
                </span>
              </div>
              <p className="text-gray-600 text-sm leading-relaxed truncate max-w-[500px]" title={plugin.desc}>
                {plugin.desc || t('plugins.noDescription')}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 ml-4">
            <button
              onClick={() => handlePluginAction('view', plugin)}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all duration-200"
              title={t('plugins.actions.view')}
            >
              <Eye className="w-4 h-4" />
            </button>
            <button
              onClick={() => handlePluginAction('configure', plugin)}
              className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded-xl transition-all duration-200"
              title={t('plugins.actions.configure')}
            >
              <Settings className="w-4 h-4" />
            </button>
            {plugin.plugin_id && plugin.plugin_id.startsWith('cloud_') && (
              <button
                onClick={() => handleEditPlugin(plugin)}
                className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-50 rounded-xl transition-all duration-200"
                title={t('plugins.actions.edit')}
              >
                <Edit className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => handlePluginAction('delete', plugin)}
              className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200"
              title={t('plugins.actions.delete')}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {plugin.status === 'error' && (
          <div className="mt-3 pt-3 border-t border-red-200">
            <div className="flex items-center text-red-600 text-sm">
              <AlertTriangle className="w-4 h-4 mr-2" />
              {t('plugins.messages.pluginError')}
            </div>
          </div>
        )}
      </div>
    </div>
  )

  // Market plugin card with install functionality

  return (
    <div className="space-y-8 p-6 min-h-screen">
      {/* Page Header - 与智能体和工作流页面统一 */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-900 mb-2">
          {t('plugins.title')}
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-6">{t('plugins.subtitle')}</p>
      </div>

      {/* Tab Buttons */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-2 bg-gray-100 rounded-xl p-1">
          <button
            onClick={() => setActiveTab(0)}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              activeTab === 0 ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {t('plugins.tabs.installed')}
            <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-600">{totalItems}</span>
          </button>
          <button
            onClick={() => setActiveTab(1)}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              activeTab === 1 ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {t('plugins.tabs.market')}
            <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-600">{marketPlugins.length}</span>
          </button>
        </div>

        {/* Create Plugin Button */}
        <button
          onClick={() => setInstallDialogOpen(true)}
          className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
        >
          <Plus className="w-5 h-5" />
          <span>{t('plugins.installPlugin')}</span>
        </button>
      </div>

      {/* Installed Plugins Tab */}
      {activeTab === 0 && (
        <div className="space-y-6">
          {/* Search and Filters */}
          <div className="flex flex-col sm:flex-row items-center gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-500 transition-colors duration-200" />
                <input
                  type="text"
                  placeholder={t('plugins.searchPlaceholder')}
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
                />
              </div>
            </div>

            {/* Category Filter */}
            <div className="sm:w-48">
              <select
                value={categoryFilter}
                onChange={e => setCategoryFilter(e.target.value)}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
              >
                <option value="all">{t('plugins.filters.allCategories')}</option>
                {categories.slice(1).map(category => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            {/* View Mode & Refresh */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-3 rounded-xl transition-all duration-200 ${
                  viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                }`}
                title={t('plugins.viewMode.grid')}
              >
                <Grid className="w-5 h-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-3 rounded-xl transition-all duration-200 ${
                  viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                }`}
                title={t('plugins.viewMode.list')}
              >
                <List className="w-5 h-5" />
              </button>
              <button
                onClick={async () => {
                  setLoading(true)
                  try {
                    await queryClient.invalidateQueries({
                      queryKey: ['pluginList', currentSpaceId],
                      exact: false,
                    })
                    await refetchPluginList()
                    showSuccess(t('plugins.messages.pluginListRefreshed'))
                  } catch (error) {
                    console.error(t('plugins.messages.refreshPluginListFailed'), error)
                    showError(t('plugins.messages.refreshPluginListError'))
                  } finally {
                    setLoading(false)
                  }
                }}
                disabled={loading}
                className="p-3 bg-gray-50 text-gray-600 hover:bg-gray-100 rounded-xl transition-all duration-200"
                title={t('plugins.actions.refresh')}
              >
                {loading ? <CircularProgress size={20} /> : <RefreshCw className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {/* Plugins Grid/List */}
          {isPluginListLoading ? (
            <div className="text-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">{t('plugins.messages.loading')}</p>
            </div>
          ) : pluginListError ? (
            <div className="text-center py-16">
              <div className="w-24 h-24 bg-gradient-to-r from-red-100 to-red-200 rounded-full flex items-center justify-center mx-auto mb-6">
                <AlertTriangle className="w-12 h-12 text-red-400" />
              </div>
              <h3 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-gray-900 mb-3">
                {t('plugins.messages.loadFailed')}
              </h3>
              <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">{t('plugins.messages.loadPluginsFailedDescription')}</p>
              <button
                onClick={() => window.location.reload()}
                className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
              >
                <RefreshCw className="w-5 h-5" />
                <span>{t('plugins.actions.reload')}</span>
              </button>
            </div>
          ) : filteredPlugins.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-24 h-24 bg-gradient-to-r from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-6">
                <Plug className="w-12 h-12 text-gray-400" />
              </div>
              <h3 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-700 to-gray-900 mb-3">
                {t('plugins.messages.noMatchingPlugins')}
              </h3>
              <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">{t('plugins.messages.tryAdjustFilters')}</p>
              <button
                onClick={() => {
                  setSearchTerm('')
                  setCategoryFilter('all')
                }}
                className="inline-flex items-center space-x-2 border-2 border-gray-300 text-gray-700 px-6 py-3 rounded-xl font-semibold hover:border-blue-500 hover:text-blue-600 transition-all duration-300"
              >
                <span>{t('plugins.actions.clearFilters')}</span>
              </button>
            </div>
          ) : (
            <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-3'}>
              {displayPlugins.map((plugin, index) => (viewMode === 'grid' ? renderPluginCard(plugin, index) : renderPluginList(plugin)))}
            </div>
          )}

          {/* Pagination */}
          {displayPlugins.length > 0 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-600">{t('common.pagination.pageSize')}:</span>
                <select
                  value={pageSize}
                  onChange={e => {
                    setPageSize(Number(e.target.value))
                    setCurrentPage(1)
                  }}
                  className="px-3 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 shadow-sm"
                >
                  <option value={9}>9{t('common.pagination.items')}</option>
                  <option value={18}>18{t('common.pagination.items')}</option>
                  <option value={30}>30{t('common.pagination.items')}</option>
                  <option value={60}>60{t('common.pagination.items')}</option>
                </select>
                <span className="text-sm text-gray-600">{t('common.pagination.total', { total: displayTotalItems })}</span>
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
                  {Array.from({ length: Math.min(5, displayTotalPages) }, (_, i) => {
                    let pageNum: number
                    if (displayTotalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= displayTotalPages - 2) {
                      pageNum = displayTotalPages - 4 + i
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
                  onClick={() => setCurrentPage(Math.min(displayTotalPages, currentPage + 1))}
                  disabled={currentPage === displayTotalPages}
                  className={`p-2 rounded-lg ${currentPage === displayTotalPages ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-100'}`}
                >
                  <ChevronRight className="w-5 h-5" />
                </button>

                <span className="text-sm text-gray-600 ml-4">{t('common.pagination.page', { current: currentPage, total: displayTotalPages })}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Market Plugins Tab */}
      {activeTab === 1 && (
        <MarketPluginList
          activeTab={activeTab}
          marketPlugins={marketPlugins}
          plugins={plugins}
          searchTerm={searchTerm}
          categoryFilter={categoryFilter}
          viewMode={viewMode}
          loading={loading || marketLoading}
          categories={categories}
          onSearchChange={setSearchTerm}
          onCategoryFilterChange={setCategoryFilter}
          onViewModeChange={setViewMode}
          onRefresh={async () => {
            setLoading(true)
            try {
              await refreshMarketPlugins()
              await queryClient.invalidateQueries({
                queryKey: ['pluginList', currentSpaceId],
                exact: false,
              })
              await refetchPluginList()
              showSuccess(t('plugins.messages.marketRefreshed'))
            } catch (error) {
              console.error('Failed to refresh plugin configurations:', error)
              showError(t('plugins.messages.loadFailed'))
            } finally {
              setLoading(false)
            }
          }}
          onPluginAction={handlePluginAction}
          onInstallPlugin={handleInstallPlugin}
          getPluginTypeText={getPluginTypeText}
          marketError={marketError}
          refreshMarketPlugins={refreshMarketPlugins}
        />
      )}

      {/* Plugin Detail Dialog */}
      <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="md" fullWidth>
        {selectedPlugin && (
          <>
            <DialogTitle className="flex items-center space-x-3">
              {renderPluginIcon(selectedPlugin.icon_uri, 'w-12 h-16 rounded-lg flex items-center justify-center text-3xl bg-gray-100')}
              <div>
                <Typography variant="h6">{selectedPlugin.name}</Typography>
              </div>
            </DialogTitle>
            <DialogContent>
              <div className="space-y-4">
                <div>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    {t('plugins.description')}
                  </Typography>
                  <Typography variant="body1">{selectedPlugin.desc}</Typography>
                </div>
                {selectedPlugin.desc_mk && (
                  <div>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      插件详情
                    </Typography>
                    <div className="prose prose-sm max-w-none p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <ReactMarkdown>{selectedPlugin.desc_mk}</ReactMarkdown>
                    </div>
                  </div>
                )}
                <div>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    {t('plugins.url')}
                  </Typography>
                  <Typography
                    variant="body1"
                    component="a"
                    href={selectedPlugin.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{
                      color: 'primary.main',
                      textDecoration: 'none',
                      '&:hover': { textDecoration: 'underline' },
                    }}
                  >
                    {selectedPlugin.url}
                  </Typography>
                </div>
              </div>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailDialogOpen(false)}>{t('common.buttons.close')}</Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Install Plugin Dialog */}
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
              sx={{
                '&.Mui-disabled': {
                  backgroundColor: '#f9fafb',
                  borderColor: '#e5e7eb',
                  color: '#6b7280',
                },
              }}
            >
              <div className="text-left">
                <div className="flex items-center justify-between w-full">
                  <Typography variant="subtitle1" className="text-gray-500">
                    {t('plugins.uploadFile')}
                  </Typography>
                  <div className="px-2 py-1 bg-yellow-100 border border-yellow-200 rounded-full">
                    <Typography variant="caption" className="text-yellow-700 font-medium">
                      {t('plugins.comingSoon')}
                    </Typography>
                  </div>
                </div>
                <Typography variant="body2" color="text.secondary" className="text-gray-400">
                  {t('plugins.uploadFileDesc')}
                </Typography>
              </div>
            </Button>

            <Button
              variant="outlined"
              fullWidth
              startIcon={<Cloud className="w-4 h-4" />}
              onClick={() => {
                setCloudPluginDialogOpen(true)
                setInstallDialogOpen(false)
              }}
              className="justify-start p-3"
            >
              <div className="text-left">
                <Typography variant="subtitle1">
                  {t('plugins.dialog.cloudPluginForm.title')}-{t('plugins.dialog.cloudPluginForm.subtitle')}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('plugins.cloudPlugin.createFromServiceDescription')}
                </Typography>
              </div>
            </Button>

            <Button
              variant="outlined"
              fullWidth
              startIcon={<Code className="w-4 h-4" />}
              onClick={() => {
                setIdePluginDialogOpen(true)
                setInstallDialogOpen(false)
              }}
              className="justify-start p-3"
            >
              <div className="text-left">
                <Typography variant="subtitle1">
                  {t('plugins.types.ide')}-{t('plugins.cloudPlugin.createFromIDE')}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('plugins.cloudPlugin.createFromIDEDescription')}
                </Typography>
              </div>
            </Button>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInstallDialogOpen(false)}>{t('common.buttons.cancel')}</Button>
        </DialogActions>
      </Dialog>

      {/* Shared Cloud Plugin Form Dialog */}
      <CloudPluginFormDialog
        open={cloudPluginDialogOpen || isEditDialogOpen}
        isEditing={isEditDialogOpen}
        loading={createPluginMutation.isLoading}
        form={cloudPluginForm}
        editingPlugin={editingPlugin}
        onFormChange={handleCloudPluginFormChange}
        onSubmit={handlePluginSubmit}
        onCancel={() => {
          if (cloudPluginDialogOpen) {
            setCloudPluginDialogOpen(false)
          }
          if (isEditDialogOpen) {
            setIsEditDialogOpen(false)
            setEditingPlugin(null)
          }
          resetForm()
        }}
      />

      {/* IDE Plugin Form Dialog */}
      <IDEPluginFormDialog
        open={idePluginDialogOpen}
        isEditing={false}
        loading={createPluginMutation.isLoading}
        form={idePluginForm}
        editingPlugin={null}
        onFormChange={handleIDEPluginFormChange}
        onSubmit={() => handleIDEPluginSubmit()}
        onCancel={() => {
          setIdePluginDialogOpen(false)
          resetIDEForm()
        }}
      />

      {/* Delete Confirmation Dialog */}
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
            {deletePluginMutation.isLoading ? t('common.buttons.deleting', '删除中...') : t('common.buttons.delete')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Action Menu */}
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
        {/* Market-specific actions */}
        {activeTab === 1 && selectedPlugin && !plugins.some(p => p.plugin_id === selectedPlugin.plugin_id) && (
          <MenuItem
            onClick={() => {
              setAnchorEl(null)
              if (selectedPlugin) {
                handleInstallPlugin(selectedPlugin)
              }
            }}
          >
            <Download className="w-4 h-4 mr-2" />
            {t('plugins.installPlugin')}
          </MenuItem>
        )}

        {activeTab === 0 && selectedPlugin && (
          <MenuItem
            onClick={() => {
              setAnchorEl(null)
              if (selectedPlugin) {
                setDeleteDialog({ isOpen: true, plugin: selectedPlugin })
              }
            }}
            className="text-red-600"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            {t('common.buttons.delete')}
          </MenuItem>
        )}
      </Menu>

      {/* Unified Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </div>
  )
}

export default PluginManagementPage
