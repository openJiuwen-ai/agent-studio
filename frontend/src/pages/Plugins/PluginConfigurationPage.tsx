import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { PluginService } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { ENV_CONFIG } from '../../config/environment'
import { useCloudPluginForm } from '../../hooks/useCloudPluginForm'
import { useUpdatePlugin, usePluginPublish, usePluginPublishList } from '@test-agentstudio/api-client'
import CloudPluginFormDialog from '../../components/Plugins/CloudPluginFormDialog'
import CodePluginConfiguration from './components/CodePluginConfiguration'
import URLPluginConfiguration from './components/URLPluginConfiguration'
import PublishDialog from '../../components/Plugins/PublishDialog'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import { AlertTriangle, Rocket } from 'lucide-react'
import { Typography, Button, CircularProgress } from '@mui/material'
import { scrollToTop } from '../../utils/scrollUtils'

interface Plugin {
  id: string
  plugin_id?: string
  name: string
  description: string
  icon: string
  category: string
  status: 'active' | 'inactive' | 'error' | 'updating'
  version: string
  author: string
  installDate: string
  lastUpdate: string
  usageCount: number
  rating: number
  downloadCount: number
  tags: string[]
  dependencies: string[]
  config: {
    apiKey?: string
    baseUrl?: string
    timeout?: number
    retryCount?: number
    url?: string
    authMethod?: string
  }
  permissions: string[]
  size: string
}

const PluginConfigurationPage: React.FC = () => {
  const { t } = useTranslation()
  const { plugin_id } = useParams<{ plugin_id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [plugin, setPlugin] = useState<Plugin | null>(null)
  const [pluginConfigData, setPluginConfigData] = useState<Record<string, unknown> | null>(null)
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar()

  const [configForm, setConfigForm] = useState({
    name: '',
    desc: '',
    desc_mk: '',
    icon_uri: '',
    url: '',
    authMethod: 'none',
    request_params: [] as any[],
  })

  // Icon options for selection - diversified without similar types
  const iconOptions = [
    '☁️',
    '🚀',
    '⚡',
    '🔥',
    '💎',
    '🏆',
    '⭐',
    '🌟',
    '✨',
    '🎨',
    '🎮',
    '🎲',
    '🎸',
    '🏠',
    '🏢',
    '🏭',
    '🏪',
    '🏫',
    '🏥',
    '🌈',
    '🌊',
    '🌍',
    '🌐',
    '🔧',
    '🔨',
    '🔬',
    '🔮',
    '💻',
    '💼',
    '💾',
    '📁',
    '📄',
    '📅',
    '🚗',
    '🚌',
    '🚓',
    '🚑',
    '🛸',
    '✈️',
    '🚁',
    '📡',
    '💡',
    '📱',
    '🖥️',
    '🖱️',
    '📷',
    '🎙️',
    '🎧',
    '💰',
    '🔑',
  ]

  // Handle icon selection
  const handleIconSelect = (icon: string) => {
    setConfigForm(prev => ({ ...prev, icon_uri: icon }))
  }

  // Handle name change
  const handleNameChange = (name: string) => {
    if (name.length <= 128) {
      setConfigForm(prev => ({ ...prev, name }))
    }
  }

  // Edit plugin state
  const [editingPlugin, setEditingPlugin] = useState<Plugin | null>(null)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)

  // Publish dialog state
  const [isPublishDialogOpen, setIsPublishDialogOpen] = useState(false)

  // Tool creation state will be handled by the individual components

  // Form management
  const {
    form: cloudPluginForm,
    handleFormChange: handleCloudPluginFormChange,
    handleHeaderChange,
    addHeaderRow,
    removeHeaderRow,
    resetForm,
    validateForm,
  } = useCloudPluginForm(editingPlugin)

  const { user } = useAuthStore()

  const getDefaultSpaceId = () => {
    return user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  }

  // Plugin update
  const updatePluginApi = useUpdatePlugin()

  // Plugin publish
  const publishPluginApi = usePluginPublish()

  // Plugin publish list - fetch every time dialog opens
  const { data: publishListData, isLoading: isPublishListLoading, refetch: refetchPublishList } = usePluginPublishList(
    {
      space_id: getDefaultSpaceId(),
      plugin_id: plugin_id,
    },
    {
      enabled: !!plugin_id,
    }
  )

  // Extract latest version from publish list data
  const getLatestVersion = (): string => {
    if (!publishListData?.data?.plugin_infos || publishListData.data.plugin_infos.length === 0) {
      return 'v0.0.1'
    }

    // Filter publish infos for the current plugin
    const pluginPublishInfos = publishListData.data.plugin_infos.filter(info => info.plugin_id === plugin_id)

    if (pluginPublishInfos.length === 0) {
      return 'v0.0.1'
    }

    // Sort by version to get the latest (assuming semantic versioning)
    // For simplicity, we'll just take the first one as the API might return them in order
    // In a production environment, you'd want to implement proper version comparison
    const latestPublish = pluginPublishInfos[0]
    return latestPublish.plugin_version || 'v0.0.1'
  }

  // Fetch publish list when dialog opens - force refetch every time
  useEffect(() => {
    if (isPublishDialogOpen && plugin_id) {
      // Force refetch regardless of stale time to get the latest version
      refetchPublishList({ cancelRefetch: false })
    }
  }, [isPublishDialogOpen, plugin_id, refetchPublishList])

  // Reset dialog state when closing to ensure fresh state on next open
  useEffect(() => {
    if (!isPublishDialogOpen) {
      // This ensures that when dialog reopens, it will properly update
      // The PublishDialog will reinitialize with the latest version
    }
  }, [isPublishDialogOpen])

  useEffect(() => {
    if (plugin_id) {
      loadPluginData()
      // Scroll to top when loading new plugin configuration
      scrollToTop()
    }
  }, [plugin_id])

  const loadPluginData = async () => {
    if (!plugin_id) return

    setLoading(true)
    try {
      const request = {
        plugin_id: plugin_id,
        space_id: getDefaultSpaceId(),
      }

      const response = await PluginService.getPlugin(request)

      if (response.code === 200) {
        setPluginConfigData(response.data.plugin_info)

        // Initialize configuration form state
        setConfigForm({
          name: response.data.plugin_info.name || '',
          desc: response.data.plugin_info.desc || '',
          desc_mk: response.data.plugin_info.desc_mk || '',
          icon_uri: response.data.plugin_info.icon_uri || '☁️',
          url: response.data.plugin_info.url || '',
          authMethod: 'none',
          request_params: response.data.plugin_info.request_params || [],
        })

        // Create plugin object from the response data
        const pluginData: Plugin = {
          id: plugin_id,
          plugin_id: plugin_id,
          name: response.data.plugin_info.name || '',
          description: response.data.plugin_info.desc || '',
          icon: response.data.plugin_info.icon_uri || '⚙️',
          category: response.data.plugin_info.plugin_type === 1 ? t('plugins.types.cloud') : t('plugins.types.ide'),
          status: 'active',
          version: 'v1.0.0',
          author: t('plugins.dialog.pluginDetails.author', '云侧创建'),
          installDate: new Date().toISOString().split('T')[0],
          lastUpdate: new Date().toISOString().split('T')[0],
          usageCount: 0,
          rating: 5.0,
          downloadCount: 1,
          tags: [t('plugins.types.cloud'), t('plugins.types.ide'), 'API'],
          dependencies: [],
          config: {
            url: response.data.plugin_info.url || '',
            authMethod: 'none',
          },
          permissions: ['network'],
          size: '0.5MB',
        }

        setPlugin(pluginData)
      } else {
        showError(`${t('plugins.pluginConfig.pluginConfigLoadFailed')}: ${response.message}`)
      }
    } catch (error) {
      console.error(t('plugins.pluginConfig.pluginConfigLoadFailed') + ':', error)
      showError(t('plugins.pluginConfig.pluginConfigLoadFailedRetry'))
    } finally {
      setLoading(false)
    }
  }

  const handleSaveConfig = async () => {
    if (!plugin_id || !pluginConfigData) {
      showError(t('plugins.errors.pluginDataNotLoaded', '插件数据未加载，请刷新页面'))
      return
    }

    // Validate URL if it's a URL plugin (plugin_type === 1)
    if (pluginConfigData.plugin_type === 1) {
      const { validateHttpUrl } = await import('../../utils/validationUtils')
      const urlValidation = validateHttpUrl(configForm.url)
      if (!urlValidation.isValid) {
        showError(`${t('plugins.pluginConfig.serviceUrlFormatError')}: ${urlValidation.error}`)
        return
      }
    }

    try {
      const updateRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id,
        plugin_version: pluginConfigData.plugin_version,
        name: configForm.name,
        desc: configForm.desc,
        desc_mk: configForm.desc_mk,
        plugin_type: pluginConfigData.plugin_type,
        published: pluginConfigData.published,
        url: configForm.url,
        icon_uri: configForm.icon_uri,
        request_params: pluginConfigData.plugin_type === 2 ? [] : configForm.request_params,
      }

      console.log('Updating plugin configuration:', updateRequest)

      // Call the API
      const response = await updatePluginApi.mutateAsync(updateRequest)

      if (response.code === 200) {
        showSuccess(t('plugins.config.saveSuccess', '插件配置保存成功'))

        // Update local state
        setPluginConfigData(prev => ({
          ...prev,
          name: configForm.name,
          desc: configForm.desc,
          desc_mk: configForm.desc_mk,
          url: configForm.url,
          icon_uri: configForm.icon_uri,
        }))

        // Update plugin display
        setPlugin(prev =>
          prev
            ? {
                ...prev,
                name: configForm.name,
                description: configForm.desc,
                icon: configForm.icon_uri || '⚙️',
                config: {
                  ...prev.config,
                  url: configForm.url,
                },
              }
            : null,
        )
      } else {
        showError(`${t('plugins.errors.saveFailed')}: ${response.message || t('plugins.messages.unknownError', '未知错误')}`)
      }
    } catch (error: unknown) {
      console.error(`${t('plugins.errors.savePluginVersionConfigFailed')}:`, error)
      const errorMessage = error?.response?.data?.message || error?.message || t('common.messages.networkError', '网络错误，请稍后重试')
      showError(errorMessage)
    }
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
        description: cloudPluginForm.description.trim(),
        config: {
          ...editingPlugin.config,
          url: cloudPluginForm.url.trim(),
          authMethod: cloudPluginForm.authMethod,
        },
        lastUpdate: new Date().toISOString().split('T')[0],
      }

      // Update plugin state
      setPlugin(updatedPlugin)

      // Here you would typically send the data to your backend API
      console.log('Updating plugin:', updatedPlugin)
      showSuccess(t('plugins.pluginVersion.updateSuccess', { name: updatedPlugin.name }))
      setIsEditDialogOpen(false)
      setEditingPlugin(null)
    }

    // Reset form
    resetForm()
  }

  const handlePublishPlugin = async (version: string, versionDesc: string) => {
    if (!plugin_id) {
      showError(t('plugins.pluginVersion.pluginIdNotFound', '插件ID不存在，无法发布'))
      return
    }

    try {
      const publishRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id,
        plugin_version: version,
        version_desc: versionDesc,
        force: false,
      }

      console.log('Publishing plugin:', publishRequest)

      const response = await publishPluginApi.mutateAsync(publishRequest)

      if (response.code === 200) {
        showSuccess(t('plugins.pluginVersion.publishSuccess', '插件"{{name}}"发布成功！', { name: plugin?.name || plugin_id }))
        setIsPublishDialogOpen(false)

        // Optionally refresh plugin data to get latest publish status
        await loadPluginData()
      } else {
        showError(`${t('plugins.pluginVersion.publishFailed')}: ${response.message || t('plugins.messages.unknownError', '未知错误')}`)
      }
    } catch (error: unknown) {
      console.error(`${t('plugins.pluginVersion.publishFailed')}:`, error)
      const errorMessage = error?.response?.data?.message || error?.message || t('common.messages.networkError', '网络错误，请稍后重试')
      showError(errorMessage)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <CircularProgress size={48} className="mb-4" />
          <Typography variant="body1" color="text.secondary">
            {t('plugins.messages.loading', '正在加载插件配置...')}
          </Typography>
        </div>
      </div>
    )
  }

  if (!plugin) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
          <Typography variant="h6" className="mb-2">
            {t('plugins.pluginConfig.pluginNotFound', '插件未找到')}
          </Typography>
          <Typography variant="body2" color="text.secondary" className="mb-4">
            {t('plugins.pluginConfig.checkPluginId', '请检查插件ID是否正确')}
          </Typography>
          <Button variant="contained" onClick={() => navigate('/dashboard/plugins')}>
            {t('plugins.actions.returnToPluginManagement', '返回插件管理')}
          </Button>
        </div>
      </div>
    )
  }

  // Render the appropriate configuration component based on plugin type
  const renderPluginConfiguration = () => {
    if (pluginConfigData?.plugin_type === 2) {
      // Code Plugin (type 2)
      return (
        <CodePluginConfiguration
          plugin={plugin}
          pluginConfigData={pluginConfigData}
          loading={loading}
          plugin_id={plugin_id}
          configForm={configForm}
          toolsLoading={false}
          iconOptions={iconOptions}
          toolsQuery={null}
          setConfigForm={setConfigForm}
          handleSaveConfig={handleSaveConfig}
          handleIconSelect={handleIconSelect}
          handleNameChange={handleNameChange}
          editingPlugin={editingPlugin}
          setEditingPlugin={setEditingPlugin}
          resetForm={resetForm}
          cloudPluginForm={cloudPluginForm}
          handleCloudPluginFormChange={handleCloudPluginFormChange}
          handleHeaderChange={handleHeaderChange}
          addHeaderRow={addHeaderRow}
          removeHeaderRow={removeHeaderRow}
          isEditDialogOpen={isEditDialogOpen}
          setIsEditDialogOpen={setIsEditDialogOpen}
          handlePluginSubmit={handlePluginSubmit}
          isPublishDialogOpen={isPublishDialogOpen}
          setIsPublishDialogOpen={setIsPublishDialogOpen}
        />
      )
    } else {
      // URL Plugin (type 1 - default)
      return (
        <URLPluginConfiguration
          plugin={plugin}
          pluginConfigData={pluginConfigData}
          loading={loading}
          plugin_id={plugin_id}
          configForm={configForm}
          toolsLoading={false}
          iconOptions={iconOptions}
          toolsQuery={null}
          setConfigForm={setConfigForm}
          handleSaveConfig={handleSaveConfig}
          handleIconSelect={handleIconSelect}
          handleNameChange={handleNameChange}
          editingPlugin={editingPlugin}
          setEditingPlugin={setEditingPlugin}
          resetForm={resetForm}
          cloudPluginForm={cloudPluginForm}
          handleCloudPluginFormChange={handleCloudPluginFormChange}
          handleHeaderChange={handleHeaderChange}
          addHeaderRow={addHeaderRow}
          removeHeaderRow={removeHeaderRow}
          isEditDialogOpen={isEditDialogOpen}
          setIsEditDialogOpen={setIsEditDialogOpen}
          handlePluginSubmit={handlePluginSubmit}
          isPublishDialogOpen={isPublishDialogOpen}
          setIsPublishDialogOpen={setIsPublishDialogOpen}
        />
      )
    }
  }

  return (
    <>
      {/* Render the appropriate configuration component */}
      {renderPluginConfiguration()}

      {/* Unified Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />

      {/* Shared Cloud Plugin Form Dialog */}
      <CloudPluginFormDialog
        open={isEditDialogOpen}
        isEditing={true}
        form={cloudPluginForm}
        editingPlugin={editingPlugin}
        onFormChange={handleCloudPluginFormChange}
        onHeaderChange={handleHeaderChange}
        onAddHeader={addHeaderRow}
        onRemoveHeader={removeHeaderRow}
        onSubmit={handlePluginSubmit}
        onCancel={() => {
          setIsEditDialogOpen(false)
          setEditingPlugin(null)
          resetForm()
        }}
      />

      {/* Publish Dialog */}
      <PublishDialog
        open={isPublishDialogOpen}
        pluginName={plugin?.name || ''}
        pluginId={plugin_id || ''}
        spaceId={getDefaultSpaceId()}
        onClose={() => {
          setIsPublishDialogOpen(false)
        }}
        onPublish={handlePublishPlugin}
        loading={publishPluginApi.isLoading}
        latestVersion={getLatestVersion()}
        configData={configForm}
        updatePluginApi={updatePluginApi}
      />
    </>
  )
}

export default PluginConfigurationPage
