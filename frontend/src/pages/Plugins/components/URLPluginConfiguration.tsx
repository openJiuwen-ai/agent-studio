import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../../../stores/useAuthStore'
import { ENV_CONFIG } from '../../../config/environment'
import {
  usePluginListApi,
  usePluginCreateApi,
  usePluginDeleteApi,
  useUpdatePlugin,
  type PluginApiInfo,
  ParamSendMethod,
  Priority,
} from '@test-agentstudio/api-client'
import CloudPluginFormDialog from '../../../components/Plugins/CloudPluginFormDialog'
import ToolFormDialog from '../../../components/Plugins/ToolFormDialog'
import PluginVersionHistory from '../../../components/Plugins/PluginVersionHistory'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../../Common/UnifiedSnackbar'
import { Settings, ArrowLeft, Info, Code, Edit, Plus, Trash2, Rocket, History, Eye } from 'lucide-react'
import {
  Card,
  Typography,
  Button,
  TextField,
  Chip,
  IconButton,
  Tabs,
  Tab,
  CircularProgress,
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  Select,
  MenuItem,
  Switch,
} from '@mui/material'
import { ParameterTypeSelector } from './ParameterTypeSelector'
import { validateToolPath, validateHttpUrlRealtime, getHttpUrlHelpText } from '../../../utils/validationUtils'
import ReactMarkdown from 'react-markdown'

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

interface URLPluginConfigurationProps {
  plugin: Plugin
  pluginConfigData: Record<string, unknown> | null
  loading: boolean
  plugin_id: string
  configForm: {
    name: string
    desc: string
    desc_mk: string
    icon_uri: string
    url: string
    authMethod: string
  }
  toolsLoading: boolean
  iconOptions: string[]
  toolsQuery: any
  setConfigForm: (config: any) => void
  handleSaveConfig: () => void
  handleIconSelect: (icon: string) => void
  handleNameChange: (name: string) => void
  editingPlugin: Plugin | null
  setEditingPlugin: (plugin: Plugin | null) => void
  resetForm: () => void
  cloudPluginForm: any
  handleCloudPluginFormChange: (field: string, value: string | number) => void
  handleHeaderChange: (index: number, field: string, value: string) => void
  addHeaderRow: () => void
  removeHeaderRow: (index: number) => void
  isEditDialogOpen: boolean
  setIsEditDialogOpen: (open: boolean) => void
  handlePluginSubmit: (isEditing: boolean) => void
  isPublishDialogOpen: boolean
  setIsPublishDialogOpen: (open: boolean) => void
  isReadOnly?: boolean
}

const URLPluginConfiguration: React.FC<URLPluginConfigurationProps> = ({
  plugin,
  pluginConfigData,
  loading,
  plugin_id,
  configForm,
  toolsLoading,
  iconOptions,
  toolsQuery,
  setConfigForm,
  handleSaveConfig,
  handleIconSelect,
  handleNameChange,
  editingPlugin,
  setEditingPlugin,
  resetForm,
  cloudPluginForm,
  handleCloudPluginFormChange,
  handleHeaderChange,
  addHeaderRow,
  removeHeaderRow,
  isEditDialogOpen,
  setIsEditDialogOpen,
  handlePluginSubmit,
  isPublishDialogOpen,
  setIsPublishDialogOpen,
  isReadOnly = false,
}) => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar()
  const { user } = useAuthStore()

  const getDefaultSpaceId = () => {
    return user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  }

  const [configTabValue, setConfigTabValue] = useState('basic')
  const [isEditingName, setIsEditingName] = useState(false)
  const [tempName, setTempName] = useState('')

  // Plugin request params state
  const [isParameterDialogOpen, setIsParameterDialogOpen] = useState(false)
  const [editingParameter, setEditingParameter] = useState<any | null>(null)
  const [parameterForm, setParameterForm] = useState({
    name: '',
    desc: '',
    type: 1,
    is_required: false,
    value: '',
    is_runtime: true,
    method: ParamSendMethod.NONE,
    priority: Priority.PLUGIN,
  })
  // URL validation state
  const [urlError, setUrlError] = useState('')

  // API工具列表查询 - only for URL plugins and not in read-only mode
  const urlToolsQuery = usePluginListApi(
    {
      space_id: getDefaultSpaceId(),
      plugin_id: plugin_id || '',
      page: 1,
      size: 20,
    },
    { enabled: configTabValue === 'advanced' && !isReadOnly },
  )

  // Use the provided toolsQuery in read-only mode, otherwise use the API query
  const currentToolsQuery = isReadOnly && toolsQuery ? toolsQuery : urlToolsQuery

  // Tool creation state for URL plugins
  const [isToolDialogOpen, setIsToolDialogOpen] = useState(false)
  const [isHistoryDialogOpen, setIsHistoryDialogOpen] = useState(false)
  const [isMarkdownPreviewOpen, setIsMarkdownPreviewOpen] = useState(false)
  const [toolForm, setToolForm] = useState({
    name: '',
    description: '',
    path: '',
    method: '',
  })
  const [deletingToolId, setDeletingToolId] = useState<string | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [toolToDelete, setToolToDelete] = useState<PluginApiInfo | null>(null)

  // Tool creation API
  const createToolApi = usePluginCreateApi()

  // Tool deletion API
  const deleteToolApi = usePluginDeleteApi()

  // Plugin update API
  const updatePluginApi = useUpdatePlugin()

  const handleToolFormChange = (field: keyof typeof toolForm, value: string) => {
    setToolForm(prev => ({
      ...prev,
      [field]: value,
    }))
  }

  // Handle URL input change with validation
  const handleUrlChange = (url: string) => {
    setConfigForm(prev => ({ ...prev, url }))

    // Real-time validation
    const error = validateHttpUrlRealtime(url)
    setUrlError(error)
  }

  // Handle name editing
  const handleEditName = () => {
    if (isReadOnly) return
    setTempName(configForm.name || plugin.name)
    setIsEditingName(true)
  }

  const handleNameSubmit = () => {
    if (tempName.trim() && tempName.length <= 128) {
      handleNameChange(tempName.trim())
    }
    setIsEditingName(false)
  }

  const handleNameCancel = () => {
    setTempName(configForm.name || plugin.name)
    setIsEditingName(false)
  }

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleNameSubmit()
    } else if (e.key === 'Escape') {
      handleNameCancel()
    }
  }

  const handleToolDialogCancel = () => {
    setIsToolDialogOpen(false)
    setToolForm({
      name: '',
      description: '',
      path: '',
      method: '',
    })
  }

  const handleToolSubmit = async () => {
    // Validate form
    if (!toolForm.name.trim() || !toolForm.description.trim() || !toolForm.path.trim() || !toolForm.method) {
      showError(t('plugins.tools.fillRequiredFields'))
      return
    }

    // Validate path
    const pathValidation = validateToolPath(toolForm.path.trim())
    if (!pathValidation.isValid) {
      showError(pathValidation.error)
      return
    }

    // Method mapping: 1=GET, 2=POST, 3=PUT, 4=DELETE, 5=PATCH
    const methodMap: Record<string, number> = {
      GET: 1,
      POST: 2,
      PUT: 3,
      DELETE: 4,
      PATCH: 5,
    }

    const methodNumber = methodMap[toolForm.method.toUpperCase()]
    if (!methodNumber) {
      showError(t('plugins.pluginConfig.unsupportedMethod'))
      return
    }

    try {
      const createRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id: plugin_id || '',
        name: toolForm.name.trim(),
        desc: toolForm.description.trim(),
        path: toolForm.path.trim(),
        method: methodNumber,
      }

      console.log('Creating tool with API:', createRequest)

      // Call the API
      const response = await createToolApi.mutateAsync(createRequest)

      if (response.code === 200) {
        showSuccess(t('plugins.pluginConfig.toolCreatedSuccess', { name: toolForm.name.trim() }))
        setIsToolDialogOpen(false)

        // Reset form
        setToolForm({
          name: '',
          description: '',
          path: '',
          method: '',
        })

        // Refresh tool list
        urlToolsQuery.refetch()

        // Navigate to tool configuration page
        if (response.data?.tool_id) {
          navigate(`/dashboard/plugins/${plugin_id}/tools/${response.data.tool_id}`, {
            state: {
              source: 'plugin',
              pluginType: 'api',
              publishVersion: pluginConfigData?.plugin_version,
            },
          })
        }
      } else {
        showError(t('plugins.pluginConfig.createFailed') + `: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (error: unknown) {
      console.error(t('plugins.pluginConfig.createFailed'), error)
      const errorMessage = error.response?.data?.message || error.message || t('plugins.pluginConfig.createFailedRetry')
      showError(errorMessage)
    }
  }

  const handleDeleteTool = async (tool: PluginApiInfo) => {
    if (!plugin_id || !tool?.tool_id) return
    setToolToDelete(tool)
    setDeleteDialogOpen(true)
  }

  const confirmDeleteTool = async () => {
    if (!toolToDelete || !plugin_id || !toolToDelete?.tool_id) return

    try {
      setDeletingToolId(toolToDelete.tool_id)

      const deleteRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id,
        tool_id: toolToDelete.tool_id,
      }

      const response = await deleteToolApi.mutateAsync(deleteRequest)

      if (response.code === 200) {
        showSuccess(t('plugins.pluginConfig.toolDeletedSuccess', { name: toolToDelete.name || t('plugins.pluginConfig.unnamedTool') }))
        // Refresh the tool list after successful deletion
        setTimeout(() => {
          urlToolsQuery.refetch()
        }, 500) // Small delay to ensure backend processes deletion
      } else {
        showError(t('plugins.pluginConfig.deleteFailed') + `: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (error: unknown) {
      console.error(t('plugins.pluginConfig.deleteFailed'), error)
      const errorMessage = error?.response?.data?.message || error?.message || t('plugins.pluginConfig.deleteFailedRetry')
      showError(errorMessage)
    } finally {
      setDeletingToolId(null)
      setDeleteDialogOpen(false)
      setToolToDelete(null)
    }
  }

  const getMethodString = (methodNumber: number): string => {
    const methodMap: Record<number, string> = {
      1: 'GET',
      2: 'POST',
      3: 'PUT',
      4: 'DELETE',
      5: 'PATCH',
    }
    return methodMap[methodNumber] || 'UNKNOWN'
  }

  const getParamTypeName = (type: number): string => {
    const typeMap: Record<number, string> = {
      1: 'String',
      2: 'Int',
      3: 'Float',
      4: 'Boolean',
      5: 'Object',
      6: 'String[]',
      7: 'Int[]',
      8: 'Float[]',
      9: 'Boolean[]',
    }
    return typeMap[type] || t('plugins.pluginConfig.unknown')
  }

  const getInputMethodName = (method: number): string => {
    const methodMap: Record<number, string> = {
      0: 'None',
      1: 'Header',
      2: 'Query',
      3: 'Body',
    }
    return methodMap[method] || t('plugins.pluginConfig.unknown')
  }

  const openParameterDialog = (param: any | null) => {
    if (param) {
      setEditingParameter(param)
      setParameterForm({
        name: param.name,
        desc: param.desc || '',
        type: param.type,
        is_required: param.is_required,
        value: param.value || '',
        is_runtime: param.is_runtime,
        method: param.method ?? ParamSendMethod.NONE,
        priority: param.priority,
      })
    } else {
      setEditingParameter(null)
      setParameterForm({
        name: '',
        desc: '',
        type: 1,
        is_required: false,
        value: '',
        is_runtime: true,
        method: 0,
        priority: Priority.PLUGIN,
      })
    }
    setIsParameterDialogOpen(true)
  }

  const handleParameterFormChange = (field: string, value: any) => {
    setParameterForm(prev => {
      const newState = {
        ...prev,
        [field]: value,
      }
      // When is_runtime is set to true (非运行时参数 unchecked), clear the value
      if (field === 'is_runtime' && value === true) {
        newState.value = ''
      }
      return newState
    })
  }

  const handleSaveParameter = async () => {
    if (!parameterForm.name.trim()) {
      showError(t('plugins.paramConfig.nameRequired'))
      return
    }

    if (!parameterForm.is_runtime && !parameterForm.value.trim()) {
      showError(t('plugins.paramConfig.nonRuntimeValueRequired'))
      return
    }

    const newParam = {
      name: parameterForm.name.trim(),
      desc: parameterForm.desc.trim(),
      type: parameterForm.type,
      is_required: parameterForm.is_required,
      value: parameterForm.value,
      is_runtime: parameterForm.is_runtime,
      method: parameterForm.method,
      priority: parameterForm.priority,
    }

    // Prepare updated request_params array
    const updatedRequestParams = editingParameter
      ? configForm.request_params.map((p, i) => (p === editingParameter ? newParam : p))
      : [...configForm.request_params, newParam]

    try {
      // Call plugin update API immediately
      const updateRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id,
        plugin_version: pluginConfigData?.plugin_version,
        name: configForm.name,
        desc: configForm.desc,
        desc_mk: configForm.desc_mk,
        plugin_type: pluginConfigData?.plugin_type,
        published: pluginConfigData?.published,
        url: configForm.url,
        icon_uri: configForm.icon_uri,
        request_params: updatedRequestParams,
      }

      const response = await updatePluginApi.mutateAsync(updateRequest)

      if (response.code === 200) {
        // Update local state only after successful API call
        setConfigForm(prev => ({
          ...prev,
          request_params: updatedRequestParams,
        }))
        showSuccess(editingParameter ? t('plugins.paramConfig.updateSuccess') : t('plugins.paramConfig.addSuccess'))
        setIsParameterDialogOpen(false)
        setEditingParameter(null)
      } else {
        showError(`${editingParameter ? t('plugins.paramConfig.update') : t('plugins.paramConfig.add')}${t('common.failed')}: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (error: unknown) {
      console.error(`${editingParameter ? t('plugins.paramConfig.update') : t('plugins.paramConfig.add')}${t('common.failed')}:`, error)
      const errorMessage = error?.response?.data?.message || error?.message || t('common.messages.networkError')
      showError(errorMessage)
    }
  }

  const handleDeleteParameter = async (index: number) => {
    const updatedRequestParams = configForm.request_params.filter((_, i) => i !== index)

    try {
      // Call plugin update API immediately
      const updateRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id,
        plugin_version: pluginConfigData?.plugin_version,
        name: configForm.name,
        desc: configForm.desc,
        desc_mk: configForm.desc_mk,
        plugin_type: pluginConfigData?.plugin_type,
        published: pluginConfigData?.published,
        url: configForm.url,
        icon_uri: configForm.icon_uri,
        request_params: updatedRequestParams,
      }

      const response = await updatePluginApi.mutateAsync(updateRequest)

      if (response.code === 200) {
        // Update local state only after successful API call
        setConfigForm(prev => ({
          ...prev,
          request_params: updatedRequestParams,
        }))
        showSuccess(t('plugins.paramConfig.deleteSuccess'))
      } else {
        showError(`${t('plugins.paramConfig.delete')}${t('common.failed')}: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (error: unknown) {
      console.error('删除参数失败:', error)
      const errorMessage = error?.response?.data?.message || error?.message || '网络错误，请稍后重试'
      showError(errorMessage)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <CircularProgress size={48} className="mb-4" />
          <Typography variant="body1" color="text.secondary">
            {t('plugins.pluginConfig.loading')}
          </Typography>
        </div>
      </div>
    )
  }

  if (!plugin) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Code className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
          <Typography variant="h6" className="mb-2">
            {t('plugins.pluginConfig.pluginNotFound')}
          </Typography>
          <Typography variant="body2" color="text.secondary" className="mb-4">
            {t('plugins.pluginConfig.checkPluginId')}
          </Typography>
          <Button variant="contained" onClick={() => navigate('/dashboard/plugins')}>
            {t('plugins.actions.returnToPluginManagement')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="mb-6 flex items-center justify-between">
            <Button variant="outlined" startIcon={<ArrowLeft className="w-4 h-4" />} onClick={() => navigate('/dashboard/plugins')}>
              {t('plugins.actions.returnToPluginManagement')}
            </Button>
            <Button
              variant="outlined"
              startIcon={<History className="w-4 h-4" />}
              onClick={() => setIsHistoryDialogOpen(true)}
              className="text-blue-600 border-blue-600 hover:bg-blue-50"
            >
              {t('plugins.actions.versionHistory')}
            </Button>
          </div>

          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 rounded-lg flex items-center justify-center text-3xl bg-gray-100 flex-shrink-0">{plugin.icon}</div>
            <div className="min-w-0 flex-1">
              {isEditingName ? (
                <div className="flex items-center space-x-2">
                  <TextField
                    value={tempName}
                    onChange={e => setTempName(e.target.value)}
                    onKeyDown={handleNameKeyDown}
                    onBlur={handleNameSubmit}
                    size="small"
                    variant="outlined"
                    placeholder={t('plugins.basicInfo.name')}
                    inputProps={{ maxLength: 20, style: { fontSize: '2rem', fontWeight: 'bold' } }}
                    className="font-bold text-gray-900"
                    autoFocus
                  />
                  <Typography variant="body2" color="text.secondary">
                    ({tempName.length}/20)
                  </Typography>
                </div>
              ) : (
                <div
                  className="cursor-pointer hover:text-blue-600 transition-colors"
                  onClick={handleEditName}
                  title={t('plugins.actions.clickToEditName')}
                >
                  {' '}
                  <Typography variant="h4" className="font-bold text-gray-900 hover:text-blue-600 truncate" title={configForm.name || plugin.name}>
                    {configForm.name || plugin.name}
                  </Typography>
                </div>
              )}
              <Typography variant="body1" color="text.secondary" className="truncate" title={plugin.description}>
                {plugin.description}
              </Typography>
            </div>
          </div>
        </div>

        {/* Configuration Content */}
        <div className="space-y-6">
          {/* Plugin Basic Information */}
          <Card className="p-6">
            <Typography variant="h6" className="mb-4 flex items-center">
              <Info className="w-5 h-5 mr-2 text-blue-600" />
              {t('plugins.basicInfoLabel')}
            </Typography>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="min-w-0">
                <Typography variant="subtitle2" color="text.secondary">
                  {t('plugins.basicInfo.name', '插件名称')}
                </Typography>
                <Typography variant="body1" className="truncate" title={plugin.name}>
                  {plugin.name}
                </Typography>
              </div>
              <div>
                <Typography variant="subtitle2" color="text.secondary">
                  {t('plugins.versionHistory.pluginType')}
                </Typography>
                <Typography variant="div" component="div">
                  <Chip label={plugin.category} size="small" />
                </Typography>
              </div>
            </div>
          </Card>

          {/* Plugin Configuration Tabs */}
          <Card className="p-6">
            <Typography variant="h6" className="mb-4 flex items-center">
              <Settings className="w-5 h-5 mr-2 text-purple-600" />
              {t('plugins.pluginConfig.configOptions')}
            </Typography>

            <Tabs value={configTabValue} onChange={(e, newValue) => setConfigTabValue(newValue)} className="mb-6">
              <Tab label={t('plugins.pluginConfig.basicTab')} value="basic" />
              <Tab label={t('plugins.pluginConfig.toolsTab')} value="advanced" />
              <Tab label={t('plugins.pluginConfig.paramsTab')} value="params" />
            </Tabs>

            {/* Tab Content */}
            {configTabValue === 'basic' && (
              <div className="space-y-6">
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-bold text-gray-800 mb-3">
                      {t('plugins.pluginConfig.pluginDescription')} <span className="text-red-500">*</span>
                    </label>
                    <TextField
                      fullWidth
                      multiline
                      rows={4}
                      value={configForm.desc}
                      onChange={e => setConfigForm(prev => ({ ...prev, desc: e.target.value }))}
                      placeholder={t('plugins.pluginConfig.descriptionPlaceholder')}
                      helperText={`${t('plugins.pluginConfig.descriptionHelper')} (${configForm.desc.length}/258)`}
                      inputProps={{ maxLength: 258 }}
                      disabled={isReadOnly}
                      required
                      error={!configForm.desc.trim()}
                      FormHelperTextProps={{
                        sx: {
                          color: !configForm.desc.trim() ? 'error.main' : 'text.primary'
                        }
                      }}
                    />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <label className="block text-sm font-bold text-gray-800">{t('plugins.pluginConfig.pluginDetailsMarkdown')}</label>
                      {configForm.desc_mk && (
                        <IconButton
                          size="small"
                          onClick={() => setIsMarkdownPreviewOpen(true)}
                          className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 -ml-1 -mt-1"
                          title={t('plugins.pluginConfig.previewMarkdown')}
                        >
                          <Eye className="w-4 h-4" />
                        </IconButton>
                      )}
                    </div>
                    <TextField
                      fullWidth
                      multiline
                      rows={6}
                      value={configForm.desc_mk || ''}
                      onChange={e => setConfigForm(prev => ({ ...prev, desc_mk: e.target.value }))}
                      placeholder={t('plugins.pluginConfig.markdownDetailedDesc')}
                      helperText={t('plugins.pluginConfig.useMarkdownSyntax', { count: (configForm.desc_mk || '').length })}
                      disabled={isReadOnly}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-800 mb-3">{t('plugins.versionHistory.pluginIcon')}</label>

                    {/* Icon selection grid - Hidden in read-only mode */}
                    {!isReadOnly && (
                      <>
                        <div className="grid grid-cols-10 gap-3 p-6 bg-gray-50 rounded-xl border border-gray-200">
                          {iconOptions.map((icon, index) => (
                            <IconButton
                              key={index}
                              onClick={() => handleIconSelect(icon)}
                              className={`w-14 h-14 text-2xl hover:bg-white hover:shadow-sm transition-all duration-200 ${
                                configForm.icon_uri === icon ? 'bg-blue-100 border-2 border-blue-500 shadow-sm scale-110' : 'hover:scale-105'
                              }`}
                            >
                              {icon}
                            </IconButton>
                          ))}
                        </div>

                        {/* Current selection display */}
                        <div className="mt-4 text-center">
                          <Typography variant="body2" className="text-gray-500">
                            {t('plugins.pluginConfig.currentSelection')}: <span className="text-2xl ml-2">{configForm.icon_uri || '☁️'}</span>
                          </Typography>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* API Configuration */}
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <Typography variant="h6" className="mb-4 flex items-center">
                    <Code className="w-5 h-5 mr-2 text-green-600" />
                    {t('plugins.pluginConfig.apiConfig')}
                  </Typography>

                  <div className="space-y-4">
                    <div>
                      <Typography variant="subtitle2" className="mb-2">
                        {t('plugins.pluginConfig.serviceUrl')}
                      </Typography>
                      <TextField
                        fullWidth
                        value={configForm.url}
                        onChange={e => handleUrlChange(e.target.value)}
                        placeholder={t('plugins.pluginConfig.serviceUrlPlaceholder')}
                        helperText={t('plugins.pluginConfig.serviceUrlHelper')}
                        error={!!urlError}
                        disabled={isReadOnly}
                        InputProps={{
                          sx: {
                            '& .MuiInputBase-input': {
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: 'calc(70ch + 20px)',
                            },
                            '&.Mui-error': {
                              borderColor: 'error.main',
                            },
                          },
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {configTabValue === 'advanced' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between mb-4">
                  <Typography variant="subtitle2" className="font-medium">
                    {t('plugins.pluginConfig.apiToolsList')}
                  </Typography>
                  {toolsLoading && <CircularProgress size={20} />}
                </div>

                {currentToolsQuery?.isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <CircularProgress size={24} className="mr-2" />
                    <Typography variant="body2" color="text.secondary">
                      {t('plugins.pluginConfig.loadingTools')}
                    </Typography>
                  </div>
                ) : currentToolsQuery?.isError ? (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                    <Typography variant="body2" color="error">
                      {t('plugins.pluginConfig.loadFailed')}
                    </Typography>
                    {!isReadOnly && (
                      <Button size="small" variant="outlined" onClick={() => urlToolsQuery.refetch()} className="mt-2">
                        {t('common.actions.retry')}
                      </Button>
                    )}
                  </div>
                ) : !currentToolsQuery?.data?.data?.api_info || currentToolsQuery.data?.data?.api_info.length === 0 ? (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <Typography variant="body1" color="text.secondary" className="mb-4">
                      {t('plugins.pluginConfig.noToolsConfig')}
                    </Typography>
                    {!isReadOnly && (
                      <Button variant="contained" startIcon={<Plus className="w-4 h-4" />} onClick={() => setIsToolDialogOpen(true)}>
                        {t('plugins.tools.addTool')}
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {currentToolsQuery.data.data.api_info.map((tool: PluginApiInfo) => (
                      <Card
                        key={tool.tool_id}
                        className="p-4 border border-gray-200 hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => {
                          navigate(`/dashboard/plugins/${plugin_id}/tools/${tool.tool_id}`, {
                            state: {
                              source: 'plugin',
                              pluginType: 'api',
                              fromPublishVersion: isReadOnly,
                              publishVersion: pluginConfigData?.plugin_version,
                              toolsData: isReadOnly ? currentToolsQuery?.data?.data?.api_info : undefined,
                            },
                          })
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <Typography variant="subtitle1" className="font-medium mb-1">
                              {tool.name || t('plugins.pluginConfig.unnamedTool')}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" className="mb-2">
                              {tool.desc || t('plugins.pluginConfig.noDescription')}
                            </Typography>
                            <div className="flex items-center space-x-4 text-sm text-gray-500">
                              <span>
                                {t('plugins.pluginConfig.method')}: {getMethodString(tool.method)}
                              </span>
                              <Typography
                                component="span"
                                sx={{
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                  maxWidth: '70ch',
                                  display: 'inline-block',
                                  verticalAlign: 'middle',
                                }}
                              >
                                {t('plugins.pluginConfig.path')}: {tool.path || '/'}
                              </Typography>
                              <Chip
                                label={tool.available ? t('plugins.actions.enable', '启用') : t('plugins.actions.disable', '禁用')}
                                size="small"
                                color={tool.available ? 'success' : 'default'}
                              />
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            {!isReadOnly && (
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  navigate(`/dashboard/plugins/${plugin_id}/tools/${tool.tool_id}`, {
                                    state: {
                                      source: 'plugin',
                                      pluginType: 'api',
                                      fromPublishVersion: isReadOnly,
                                      publishVersion: pluginConfigData?.plugin_version,
                                      toolsData: isReadOnly ? currentToolsQuery?.data?.data?.api_info : undefined,
                                    },
                                  })
                                }}
                                title={t('plugins.pluginConfig.editTool')}
                              >
                                <Edit className="w-4 h-4" />
                              </IconButton>
                            )}
                            {!isReadOnly &&
                              (deletingToolId === tool.tool_id ? (
                                <Button
                                  size="small"
                                  disabled
                                  startIcon={<CircularProgress size={14} />}
                                  sx={{ minWidth: 'auto', fontSize: '0.75rem', padding: '4px 8px' }}
                                >
                                  {t('common.deleting')}
                                </Button>
                              ) : (
                                <IconButton
                                  size="small"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleDeleteTool(tool)
                                  }}
                                  title={t('plugins.pluginConfig.deleteTool')}
                                >
                                  <Trash2 className="w-4 h-4 text-red-500 hover:text-red-700" />
                                </IconButton>
                              ))}
                          </div>
                        </div>
                      </Card>
                    ))}
                    {!isReadOnly && (
                      <div className="flex justify-center mt-4">
                        <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={() => setIsToolDialogOpen(true)}>
                          {t('plugins.pluginConfig.addNewTool')}
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Input Parameters Tab */}
            {configTabValue === 'params' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <Typography variant="h6">{t('plugins.paramConfig.title')}</Typography>
                  {!isReadOnly && (
                    <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={() => openParameterDialog(null)}>
                      {t('plugins.paramConfig.addInputParam')}
                    </Button>
                  )}
                </div>

                {configForm.request_params?.length === 0 ? (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <Typography variant="body1" color="text.secondary">
                      {t('plugins.paramConfig.noInputParams')}
                    </Typography>
                    {!isReadOnly && (
                      <Typography variant="body2" color="text.secondary" className="mt-1">
                        {t('plugins.paramConfig.clickToAddInputParams')}
                      </Typography>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {configForm.request_params?.map((param, index) => (
                      <Card key={index} className="p-4 border border-gray-200">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-4">
                              <Typography variant="subtitle1" className="font-medium">
                                {param.name}
                              </Typography>
                              <Chip label={getParamTypeName(param.type)} size="small" />
                              <Chip label={getInputMethodName(param.method)} size="small" variant="outlined" />
                              {param.is_required && <Chip label={t('plugins.paramConfig.required')} size="small" color="error" variant="outlined" />}
                            </div>
                            <Typography variant="body2" color="text.secondary" className="mt-1">
                              {param.desc}
                            </Typography>
                            {param.value && (
                              <Typography variant="caption" color="text.secondary" className="mt-1">
                                {t('plugins.paramConfig.defaultValue')}: {param.value}
                              </Typography>
                            )}
                          </div>
                          {!isReadOnly && (
                            <div className="flex items-center space-x-2">
                              <IconButton size="small" onClick={() => openParameterDialog(param)} title={t('plugins.paramConfig.editParam')}>
                                <Edit className="w-4 h-4" />
                              </IconButton>
                              <IconButton size="small" onClick={() => handleDeleteParameter(index)} title={t('plugins.paramConfig.deleteParam')}>
                                <Trash2 className="w-4 h-4" />
                              </IconButton>
                            </div>
                          )}
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>

        {/* Action Buttons - Disabled for read-only mode */}
        {!isReadOnly && (
          <div className="mt-8 flex justify-end space-x-3">
            <Button variant="outlined" onClick={() => navigate('/dashboard/plugins')}>
              {t('common.actions.cancel')}
            </Button>
            <Button
              variant="contained"
              color="success"
              onClick={() => setIsPublishDialogOpen(true)}
              startIcon={<Rocket className="w-4 h-4" />}
              className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 mr-3"
            >
              {t('plugins.pluginConfig.publishPlugin')}
            </Button>
            <Button
              variant="contained"
              onClick={handleSaveConfig}
              disabled={updatePluginApi.isLoading}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            >
              {updatePluginApi.isLoading ? (
                <div className="flex items-center">
                  <CircularProgress size={16} className="mr-2" />
                  {t('common.actions.saving')}
                </div>
              ) : (
                t('plugins.pluginConfig.saveConfig')
              )}
            </Button>
          </div>
        )}
      </div>

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

      {/* Tool Form Dialog */}
      <ToolFormDialog
        open={isToolDialogOpen}
        loading={createToolApi.isLoading}
        form={toolForm}
        onFormChange={handleToolFormChange}
        onSubmit={handleToolSubmit}
        onCancel={handleToolDialogCancel}
      />

      {/* Plugin Version History Dialog */}
      <PluginVersionHistory
        open={isHistoryDialogOpen}
        onClose={() => setIsHistoryDialogOpen(false)}
        pluginId={plugin_id}
        spaceId={getDefaultSpaceId()}
        pluginName={plugin.name}
      />

      {/* Markdown Preview Dialog */}
      <Dialog
        open={isMarkdownPreviewOpen}
        onClose={() => setIsMarkdownPreviewOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: { maxHeight: '80vh' },
        }}
      >
        <DialogTitle>{t('plugins.pluginConfig.markdownPreview')}</DialogTitle>
        <DialogContent dividers>
          <div className="prose prose-sm max-w-none overflow-y-auto" style={{ maxHeight: '60vh' }}>
            <ReactMarkdown>{configForm.desc_mk || ''}</ReactMarkdown>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsMarkdownPreviewOpen(false)}>{t('common.actions.close')}</Button>
        </DialogActions>
      </Dialog>

      {/* Parameter Dialog */}
      <Dialog
        open={isParameterDialogOpen}
        onClose={() => {
          setIsParameterDialogOpen(false)
          setEditingParameter(null)
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{editingParameter ? t('plugins.paramConfig.editParam') : t('plugins.paramConfig.addParam')}</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <div>
              <div className="flex items-center justify-between mb-2">
                <Typography variant="subtitle2">
                  {t('plugins.paramConfig.paramName')} <span className="text-red-500 ml-1">*</span>
                </Typography>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="is_required"
                    checked={parameterForm.is_required}
                    onChange={e => handleParameterFormChange('is_required', e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer"
                  />
                  <label htmlFor="is_required" className="text-sm font-medium text-gray-700 cursor-pointer whitespace-nowrap">
                    {t('plugins.paramConfig.requiredParam')}
                  </label>
                </div>
              </div>
              <TextField
                fullWidth
                value={parameterForm.name}
                onChange={e => handleParameterFormChange('name', e.target.value)}
                placeholder={t('plugins.paramConfig.paramNamePlaceholder')}
                helperText={`${t('plugins.paramConfig.paramName')} (${parameterForm.name.length}/128)`}
                inputProps={{ maxLength: 128 }}
              />
            </div>
            <div>
              <Typography variant="subtitle2" className="mb-2">
                {t('plugins.paramConfig.paramDesc')}
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={2}
                value={parameterForm.desc}
                onChange={e => handleParameterFormChange('desc', e.target.value)}
                placeholder={t('plugins.paramConfig.paramDescPlaceholder')}
                helperText={`${t('plugins.paramConfig.paramDesc')} (${parameterForm.desc.length}/256)`}
                inputProps={{ maxLength: 256 }}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Typography variant="subtitle2" className="mb-2">
                  {t('plugins.paramConfig.paramType')}
                </Typography>
                <ParameterTypeSelector
                  value={parameterForm.type}
                  onChange={(value) => handleParameterFormChange('type', value)}
                  useNumericValues={true}
                />
              </div>
              <div>
                <Typography variant="subtitle2" className="mb-2">
                  {t('plugins.paramConfig.inputMethod')}
                </Typography>
                <FormControl fullWidth>
                  <Select value={parameterForm.method} onChange={e => handleParameterFormChange('method', e.target.value)}>
                    <MenuItem value={1}>{t('plugins.paramConfig.headerParam')}</MenuItem>
                    <MenuItem value={2}>{t('plugins.paramConfig.queryParam')}</MenuItem>
                    <MenuItem value={3}>{t('plugins.paramConfig.bodyParam')}</MenuItem>
                  </Select>
                </FormControl>
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_runtime"
                  checked={!parameterForm.is_runtime}
                  onChange={e => handleParameterFormChange('is_runtime', !e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="is_runtime" className="text-sm font-medium text-gray-700 cursor-pointer">
                  {t('plugins.paramConfig.nonRuntimeParam')}
                </label>
              </div>
              <Typography variant="caption" className="text-gray-500 mt-1 block">
                {t('plugins.paramConfig.nonRuntimeParamDesc')}
              </Typography>
            </div>
            {!parameterForm.is_runtime && (
              <div>
                <Typography variant="subtitle2" className="mb-2">
                  {t('plugins.paramConfig.defaultValue')} <span className="text-red-500 ml-1">*</span>
                </Typography>
                {(() => {
                  const isBooleanType = parameterForm.type === 4
                  return isBooleanType ? (
                    <div className="flex items-center space-x-2">
                      <Typography variant="body2" className="text-gray-600">
                        {parameterForm.value === 'true' || parameterForm.value === true ? 'True' : 'False'}
                      </Typography>
                      <Switch
                        checked={parameterForm.value === 'true' || parameterForm.value === true}
                        onChange={e => handleParameterFormChange('value', e.target.checked ? 'true' : 'false')}
                        color="primary"
                      />
                    </div>
                  ) : (
                    <TextField
                      fullWidth
                      value={parameterForm.value}
                      onChange={e => handleParameterFormChange('value', e.target.value)}
                      placeholder={t('plugins.paramConfig.defaultValuePlaceholder')}
                      helperText={t('plugins.paramConfig.nonRuntimeParamDefaultValue')}
                      required
                    />
                  )
                })()}
              </div>
            )}
          </div>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setIsParameterDialogOpen(false)
              setEditingParameter(null)
            }}
          >
            {t('common.actions.cancel')}
          </Button>
          <Button variant="contained" onClick={handleSaveParameter}>
            {editingParameter ? '更新' : '添加'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('plugins.tools.deleteDialog.title', '确认删除工具')}</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <Typography variant="body1">{t('plugins.tools.deleteDialog.content', { name: toolToDelete?.name || '未命名工具' })}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t('plugins.tools.deleteDialog.warning', '此操作不可撤销，删除后所有相关配置将被永久移除。')}
            </Typography>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleteToolApi.isLoading}>
            {t('common.buttons.cancel', '取消')}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={confirmDeleteTool}
            disabled={deleteToolApi.isLoading}
            startIcon={deleteToolApi.isLoading ? <CircularProgress size={16} /> : <Trash2 className="w-4 h-4" />}
          >
            {deleteToolApi.isLoading ? t('common.buttons.deleting', '删除中...') : t('common.buttons.confirmDelete', '确认删除')}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}

export default URLPluginConfiguration
