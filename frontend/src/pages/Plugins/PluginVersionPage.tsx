import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { PluginService } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { ENV_CONFIG } from '../../config/environment'
import { useCloudPluginForm } from '../../hooks/useCloudPluginForm'
import { useUpdatePlugin, usePluginPublishGet } from '@test-agentstudio/api-client'
import CloudPluginFormDialog from '../../components/Plugins/CloudPluginFormDialog'
import CodePluginConfiguration from './components/CodePluginConfiguration'
import URLPluginConfiguration from './components/URLPluginConfiguration'
import PublishDialog from '../../components/Plugins/PublishDialog'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import { AlertTriangle, ArrowLeft } from 'lucide-react'
import { Typography, Button, CircularProgress, Breadcrumbs, Link, Box } from '@mui/material'

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

const PluginVersionPage: React.FC = () => {
  const { t } = useTranslation()
  const { plugin_id, version } = useParams<{ plugin_id: string; version: string }>()
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

  // Read-only display state
  const [isReadOnly, setIsReadOnly] = useState(true)

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
  const handleIconSelect = useCallback((icon: string) => {
    setConfigForm(prev => ({ ...prev, icon_uri: icon }))
  }, [])

  // Handle name change
  const handleNameChange = useCallback((name: string) => {
    if (name.length <= 128) {
      setConfigForm(prev => ({ ...prev, name }))
    }
  }, [])

  // Edit plugin state
  const [editingPlugin, setEditingPlugin] = useState<Plugin | null>(null)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)

  // Publish dialog state
  const [isPublishDialogOpen, setIsPublishDialogOpen] = useState(false)

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

  // Get plugin version data using hook
  const {
    data: versionDataResponse,
    isLoading: versionLoading,
    error: versionError,
  } = usePluginPublishGet({
    space_id: getDefaultSpaceId(),
    plugin_id: plugin_id || '',
    plugin_version: version || '',
  })

  useEffect(() => {
    if (versionLoading) {
      setLoading(true)
    } else {
      setLoading(false)
    }

    if (versionDataResponse?.code === 200 && versionDataResponse.data) {
      const versionData = versionDataResponse.data
      setPluginConfigData(versionData.plugin_info)

      // Initialize configuration form state with version data
      setConfigForm({
        name: versionData.plugin_info.name || '',
        desc: versionData.plugin_info.desc || '',
        desc_mk: versionData.plugin_info.desc_mk || '',
        icon_uri: versionData.plugin_info.icon_uri || '☁️',
        url: versionData.plugin_info.url || '',
        authMethod: 'none',
        request_params: versionData.plugin_info.request_params || [],
      })

      // Create plugin object from the version data
      const pluginData: Plugin = {
        id: plugin_id,
        plugin_id: plugin_id,
        name: versionData.plugin_info.name || '',
        description: versionData.plugin_info.desc || '',
        icon: versionData.plugin_info.icon_uri || '⚙️',
        category: versionData.plugin_info.plugin_type === 1 ? t('plugins.types.cloud', '云侧插件') : t('plugins.types.ide', '本地代码插件'),
        status: 'active',
        version: versionData.plugin_info.plugin_version || version,
        installDate: new Date().toISOString().split('T')[0],
        lastUpdate: new Date().toISOString().split('T')[0],
        tags: [t('plugins.tags.cloud', '云侧'), t('plugins.tags.custom', '自定义'), t('plugins.tags.api', 'API')],
        dependencies: [],
        config: {
          url: versionData.plugin_info.url || '',
          authMethod: 'none',
        },
        permissions: ['network'],
      }

      setPlugin(pluginData)
    } else if (versionError) {
      console.error(t('plugins.message.getVersionInfoFailed', '获取插件版本信息失败'), versionError)
      showError(t('plugins.message.getVersionInfoFailed', '获取插件版本信息失败，请稍后重试'))
    } else if (versionDataResponse && versionDataResponse.code !== 200) {
      showError(`${t('plugins.message.getVersionInfoFailed', '获取插件版本信息失败')}: ${versionDataResponse.message}`)
    }
  }, [versionDataResponse, versionLoading, versionError, plugin_id, version])

  const handleSaveConfig = useCallback(async () => {
    if (isReadOnly) {
      showError(t('plugins.message.readOnlyMode', '当前为只读模式，不允许编辑插件配置'))
      return
    }

    if (!plugin_id || !pluginConfigData) {
      showError(t('plugins.errors.pluginDataNotLoaded', '插件数据未加载，请刷新页面'))
      return
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
      }

      console.log('Updating plugin version configuration:', updateRequest)

      // Call the API
      const response = await updatePluginApi.mutateAsync(updateRequest)

      if (response.code === 200) {
        showSuccess(t('plugins.message.pluginVersionConfigSaveSuccess', '插件版本配置保存成功'))

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
        showError(t('plugins.errors.saveFailed', '保存失败') + `: ${response.message || t('common.message.unknownError', '未知错误')}`)
      }
    } catch (error: unknown) {
      console.error(t('plugins.errors.savePluginVersionConfigFailed', '保存插件版本配置失败'), error)
      const errorMessage =
        error?.response?.data?.message || error?.message || t('plugins.errors.savePluginVersionConfigFailed', '保存插件版本配置失败，请稍后重试')
      showError(errorMessage)
    }
  }, [
    isReadOnly,
    plugin_id,
    pluginConfigData,
    configForm.name,
    configForm.desc,
    configForm.desc_mk,
    configForm.url,
    configForm.icon_uri,
    getDefaultSpaceId,
    updatePluginApi,
    showSuccess,
    showError,
  ])

  const handlePluginSubmit = useCallback(
    async (isEditing: boolean = false) => {
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
        console.log('Updating plugin version:', updatedPlugin)
        showSuccess(t('plugins.version.updateSuccess', { name: updatedPlugin.name }))
        setIsEditDialogOpen(false)
        setEditingPlugin(null)
      }

      // Reset form
      resetForm()
    },
    [
      validateForm,
      showError,
      editingPlugin,
      cloudPluginForm.name,
      cloudPluginForm.description,
      cloudPluginForm.url,
      cloudPluginForm.authMethod,
      showSuccess,
      resetForm,
    ],
  )

  const handlePublishPlugin = useCallback(
    async (version: string, versionDesc: string) => {
      if (isReadOnly) {
        showError(t('plugins.pluginVersion.readOnlyModePublish', '当前为只读模式，不允许发布插件'))
        return
      }

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

        console.log('Publishing plugin version:', publishRequest)

        const response = await updatePluginApi.mutateAsync(publishRequest)

        if (response.code === 200) {
          showSuccess(t('plugins.pluginVersion.publishSuccess', { name: plugin?.name || plugin_id }))
          setIsPublishDialogOpen(false)

          // Optionally refresh plugin data to get latest publish status
          // The usePluginPublishGet hook will automatically refetch when needed
        } else {
          showError(t('plugins.pluginVersion.publishFailed', '发布插件版本失败') + `: ${response.message || t('common.message.unknownError', '未知错误')}`)
        }
      } catch (error: unknown) {
        console.error(t('plugins.pluginVersion.publishFailed', '发布插件版本失败'), error)
        const errorMessage = error?.response?.data?.message || error?.message || t('plugins.pluginVersion.publishFailed', '发布插件版本失')
        showError(errorMessage)
      }
    },
    [isReadOnly, plugin_id, plugin?.name, getDefaultSpaceId, updatePluginApi, showSuccess, showError],
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <CircularProgress size={48} className="mb-4" />
          <Typography variant="body1" color="text.secondary">
            {t('plugins.pluginVersion.loadingPluginVersion', '正在加载插件版本信息...')}
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
            {t('plugins.pluginVersion.pluginVersionNotFound', '插件版本未找到')}
          </Typography>
          <Typography variant="body2" color="text.secondary" className="mb-4">
            {t('plugins.pluginVersion.checkPluginIdAndVersion', '请检查插件ID和版本号是否正确')}
          </Typography>
          <Button variant="contained" onClick={() => navigate('/dashboard/plugins')}>
            {t('plugins.action.returnToPluginManagement', '返回插件管理')}
          </Button>
        </div>
      </div>
    )
  }

  // Create tools query object from version data for the configuration components
  const createToolsQueryFromVersion = () => {
    if (!pluginConfigData?.tools) {
      return {
        data: {
          data: {
            api_info: [],
            code_info: [],
          },
        },
        isLoading: false,
        error: null,
        refetch: () => {},
      }
    }

    const tools = pluginConfigData.tools || []

    return {
      data: {
        data: {
          api_info: tools, // For URL plugins
          code_info: tools, // For code plugins
        },
      },
      isLoading: false,
      error: null,
      refetch: () => {},
    }
  }

  // Render the appropriate configuration component based on plugin type
  const renderPluginConfiguration = () => {
    const versionToolsQuery = createToolsQueryFromVersion()

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
          toolsQuery={versionToolsQuery}
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
          isReadOnly={isReadOnly}
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
          toolsQuery={versionToolsQuery}
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
          isReadOnly={isReadOnly}
        />
      )
    }
  }

  return (
    <>
      {/* Breadcrumbs */}
      <Box className="px-6 py-4 bg-white border-b border-gray-200">
        <Breadcrumbs aria-label="breadcrumb">
          <Link component="button" variant="body1" onClick={() => navigate('/dashboard/plugins')} className="text-gray-600 hover:text-gray-900">
            {t('plugins.title', '插件管理')}
          </Link>
          <Link component="button" variant="body1" onClick={() => navigate(`/dashboard/plugins/${plugin_id}`)} className="text-gray-600 hover:text-gray-900">
            {plugin?.name}
          </Link>
          <Typography variant="body1" color="text.primary" className="font-medium">
            {t('plugins.categories.version', '版本')} {version}
          </Typography>
        </Breadcrumbs>
      </Box>

      {/* Render the appropriate configuration component */}
      {renderPluginConfiguration()}

      {/* Unified Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />

      {/* Shared Cloud Plugin Form Dialog - Disabled for read-only mode */}
      {/* Commented out - Edit functionality disabled in version pages
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
      */}

      {/* Publish Dialog - Disabled for read-only mode */}
      {/* Commented out - Publish functionality disabled in version pages
      <PublishDialog
        open={isPublishDialogOpen}
        pluginName={plugin?.name || ''}
        pluginId={plugin_id || ''}
        onClose={() => setIsPublishDialogOpen(false)}
        onPublish={handlePublishPlugin}
        loading={updatePluginApi.isLoading}
      />
      */}
    </>
  )
}

export default PluginVersionPage
