import React, { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../../../stores/useAuthStore'
import { ENV_CONFIG } from '../../../config/environment'
import {
  usePluginListCode,
  usePluginCreateCode,
  usePluginDeleteCode,
  useUpdatePlugin,
  type PluginCodeInfo,
  ParamSendMethod,
  Priority,
} from '@test-agentstudio/api-client'
import CodePluginToolFormDialog from '../../../components/Plugins/CodePluginToolFormDialog'
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
} from '@mui/material'
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

interface CodePluginConfigurationProps {
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
  iconOptions: string[]
  setConfigForm: (config: any) => void
  handleSaveConfig: () => void
  handleIconSelect: (icon: string) => void
  handleNameChange: (name: string) => void
  editingPlugin: Plugin | null
  setEditingPlugin: (plugin: Plugin | null) => void
  resetForm: () => void
  isEditDialogOpen: boolean
  setIsEditDialogOpen: (open: boolean) => void
  isPublishDialogOpen: boolean
  setIsPublishDialogOpen: (open: boolean) => void
  toolsQuery?: any
  isReadOnly?: boolean
}

const CodePluginConfiguration: React.FC<CodePluginConfigurationProps> = ({
  plugin,
  pluginConfigData,
  loading,
  plugin_id,
  configForm,
  iconOptions,
  setConfigForm,
  handleSaveConfig,
  handleIconSelect,
  handleNameChange,
  editingPlugin,
  setEditingPlugin,
  resetForm,
  isEditDialogOpen,
  setIsEditDialogOpen,
  isPublishDialogOpen,
  setIsPublishDialogOpen,
  toolsQuery,
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
    input_method: ParamSendMethod.NONE,
    priority: Priority.PLUGIN,
  })

  // API工具列表查询 - only for code plugins, enabled when advanced tab is active and not in read-only mode
  const codeToolsQuery = usePluginListCode(
    {
      space_id: getDefaultSpaceId(),
      plugin_id: plugin_id || '',
      page: 1,
      size: 20,
    },
    { enabled: configTabValue === 'advanced' && !isReadOnly }, // Only enabled when advanced tab is active and not in read-only mode
  )

  // Use the provided toolsQuery in read-only mode, otherwise use the API query
  const currentToolsQuery = isReadOnly && toolsQuery ? toolsQuery : codeToolsQuery

  // Handle tab change
  const handleTabChange = (newValue: string) => {
    setConfigTabValue(newValue)
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

  // Tool creation state for code plugins
  const [isCodePluginToolDialogOpen, setIsCodePluginToolDialogOpen] = useState(false)
  const [isHistoryDialogOpen, setIsHistoryDialogOpen] = useState(false)
  const [isMarkdownPreviewOpen, setIsMarkdownPreviewOpen] = useState(false)
  const [codePluginToolForm, setCodePluginToolForm] = useState({
    name: '',
    description: '',
    runtime: 'python3' as 'python3' | 'nodejs',
    code: '',
    codeLanguage: 'python' as 'javascript' | 'python',
  })

  // Tool creation API
  const createCodeToolApi = usePluginCreateCode()

  // Tool deletion API
  const deleteToolApi = usePluginDeleteCode()

  // Plugin update API
  const updatePluginApi = useUpdatePlugin()

  // Update tools state from React Query data
  const codeTools = useMemo(() => {
    return currentToolsQuery.data?.data?.code_info || []
  }, [currentToolsQuery.data?.data?.code_info])

  const handleCodePluginToolFormChange = (field: keyof typeof codePluginToolForm, value: string) => {
    setCodePluginToolForm(prev => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleCodePluginToolDialogCancel = () => {
    setIsCodePluginToolDialogOpen(false)
    setCodePluginToolForm({
      name: '',
      description: '',
      runtime: 'python3',
      code: '',
      codeLanguage: 'python',
    })
  }

  const handleCodePluginToolSubmit = async () => {
    // Validate form
    if (!codePluginToolForm.name.trim() || !codePluginToolForm.description.trim() || !codePluginToolForm.runtime || !codePluginToolForm.code.trim()) {
      showError(t('plugins.messages.fillRequiredFields', '请填写所有必填字段'))
      return
    }

    try {
      const createRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id: plugin_id || '',
        name: codePluginToolForm.name.trim(),
        desc: codePluginToolForm.description.trim(),
        language: codePluginToolForm.codeLanguage,
        code: codePluginToolForm.code,
      }

      console.log('Creating code plugin tool with API:', createRequest)

      // Call the API
      const response = await createCodeToolApi.mutateAsync(createRequest)

      if (response.code === 200) {
        showSuccess(t('plugins.pluginConfig.toolCreatedSuccess', { name: codePluginToolForm.name.trim() }))
        setIsCodePluginToolDialogOpen(false)

        // Reset form
        setCodePluginToolForm({
          name: '',
          description: '',
          runtime: 'python3',
          code: '',
          codeLanguage: 'python',
        })

        // Refresh tool list after successful creation (only in edit mode)
        if (configTabValue === 'advanced' && !isReadOnly) {
          await codeToolsQuery.refetch()
        }

        // Navigate to tool configuration page
        if (response.data?.tool_id) {
          navigate(`/dashboard/plugins/${plugin_id}/tools/${response.data.tool_id}`, {
            state: {
              source: 'plugin',
              pluginType: 'code',
            },
          })
        }
      } else {
        showError(`${t('plugins.pluginConfig.createFailed')}: ${response.message || t('plugins.messages.unknownError', '未知错误')}`)
      }
    } catch (error: unknown) {
      console.error('创建工具失败:', error)
      const errorMessage = error.response?.data?.message || error.message || t('plugins.pluginConfig.createFailedRetry', '创建工具失败，请稍后重试')
      showError(errorMessage)
    }
  }

  const handleDeleteTool = async (tool: PluginCodeInfo) => {
    if (!plugin_id || !tool?.tool_id) return

    try {
      const deleteRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id,
        tool_id: tool.tool_id,
      }

      const response = await deleteToolApi.mutateAsync(deleteRequest)

      if (response.code === 200) {
        showSuccess(t('plugins.pluginConfig.toolDeletedSuccess', { name: tool.name || t('plugins.pluginConfig.unnamedTool', '未命名工具') }))
        // Refresh the tool list after successful deletion (only in edit mode)
        if (configTabValue === 'advanced' && !isReadOnly) {
          setTimeout(async () => {
            await codeToolsQuery.refetch()
          }, 5) // Small delay to ensure backend processes deletion
        }
      } else {
        showError(t('plugins.pluginConfig.deleteFailed', '删除失败: {{message}}').replace('{{message}}', response.message || '未知错误'))
      }
    } catch (error: unknown) {
      console.error('删除工具失败:', error)
      const errorMessage = error?.response?.data?.message || error?.message || t('plugins.pluginConfig.deleteFailedRetry', '删除工具失败，请稍后重试')
      showError(errorMessage)
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
      1: '字符串',
      2: '数字',
      3: '布尔值',
      4: '字符串数组',
      5: '数字数组',
      6: '布尔数组',
      7: '对象',
    }
    return typeMap[type] || '未知'
  }

  const getInputMethodName = (method: number): string => {
    const methodMap: Record<number, string> = {
      0: '无',
      1: 'Header',
      2: 'Query',
      3: 'Body',
    }
    return methodMap[method] || '未知'
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
        input_method: param.input_method,
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
        input_method: 0,
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
      showError('请输入参数名称')
      return
    }

    const newParam = {
      name: parameterForm.name.trim(),
      desc: parameterForm.desc.trim(),
      type: parameterForm.type,
      is_required: parameterForm.is_required,
      value: parameterForm.value,
      is_runtime: parameterForm.is_runtime,
      input_method: parameterForm.input_method,
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
        showSuccess(editingParameter ? '参数更新成功' : '参数添加成功')
        setIsParameterDialogOpen(false)
        setEditingParameter(null)
      } else {
        showError(`${editingParameter ? '参数更新' : '参数添加'}失败: ${response.message || '未知错误'}`)
      }
    } catch (error: unknown) {
      console.error(`${editingParameter ? '更新参数' : '添加参数'}失败:`, error)
      const errorMessage = error?.response?.data?.message || error?.message || '网络错误，请稍后重试'
      showError(errorMessage)
    }
  }

  const handleDeleteParameter = (index: number) => {
    setConfigForm(prev => ({
      ...prev,
      request_params: prev.request_params.filter((_, i) => i !== index),
    }))
    showSuccess('参数删除成功')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <CircularProgress size={48} className="mb-4" />
          <Typography variant="body1" color="text.secondary">
            {t('plugins.config.loading')}
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
            {t('plugins.pluginConfig.notFound', '插件未找到')}
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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="mb-6 flex items-center justify-between">
            <Button variant="outlined" startIcon={<ArrowLeft className="w-4 h-4" />} onClick={() => navigate('/dashboard/plugins')}>
              {t('plugins.actions.returnToPluginManagement', '返回插件管理')}
            </Button>
            <Button
              variant="outlined"
              startIcon={<History className="w-4 h-4" />}
              onClick={() => setIsHistoryDialogOpen(true)}
              className="text-blue-600 border-blue-600 hover:bg-blue-50"
            >
              {t('plugins.actions.versionHistory', '版本历史')}
            </Button>
          </div>

          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 rounded-lg flex items-center justify-center text-3xl bg-gray-100">{plugin.icon}</div>
            <div>
              {isEditingName ? (
                <div className="flex items-center space-x-2">
                  <TextField
                    value={tempName}
                    onChange={e => setTempName(e.target.value)}
                    onKeyDown={handleNameKeyDown}
                    onBlur={handleNameSubmit}
                    size="small"
                    variant="outlined"
                    placeholder={t('plugins.basicInfo.name', '插件名称')}
                    inputProps={{ maxLength: 128, style: { fontSize: '2rem', fontWeight: 'bold' } }}
                    className="font-bold text-gray-900"
                    autoFocus
                  />
                  <Typography variant="body2" color="text.secondary">
                    ({tempName.length}/128)
                  </Typography>
                </div>
              ) : (
                <div
                  className="cursor-pointer hover:text-blue-600 transition-colors"
                  onClick={handleEditName}
                  title={t('plugins.actions.editPluginName', '点击编辑插件名称')}
                >
                  <Typography variant="h4" className="font-bold text-gray-900 hover:text-blue-600">
                    {configForm.name || plugin.name}
                  </Typography>
                </div>
              )}
              <Typography variant="body1" color="text.secondary">
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
              {t('plugins.basicInfoLabel', '基本信息')}
            </Typography>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <Typography variant="subtitle2" color="text.secondary">
                  {t('plugins.basicInfo.name', '插件名称')}
                </Typography>
                <Typography variant="body1">{plugin.name}</Typography>
              </div>
              <div>
                <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                  {t('plugins.versionHistory.pluginType', '插件类型')}
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
              {t('plugins.pluginConfig.configOptions', '配置选项')}
            </Typography>

            <Tabs value={configTabValue} onChange={(e, newValue) => handleTabChange(newValue)} className="mb-6">
              <Tab label={t('plugins.pluginConfig.basicTab', '基本配置')} value="basic" />
              <Tab label={t('plugins.pluginConfig.toolsTab', '工具设置')} value="advanced" />
              <Tab label="插件参数" value="params" />
            </Tabs>

            {/* Tab Content */}
            {configTabValue === 'basic' && (
              <div className="space-y-6">
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-bold text-gray-800 mb-3">{t('plugins.pluginConfig.pluginDescription', '插件描述')}</label>
                    <TextField
                      fullWidth
                      multiline
                      rows={4}
                      value={configForm.desc}
                      onChange={e => setConfigForm(prev => ({ ...prev, desc: e.target.value }))}
                      placeholder={t('plugins.pluginConfig.descriptionPlaceholder', '详细描述插件的功能、用途和特性...')}
                      helperText={`${t('plugins.pluginConfig.descriptionHelper', '详细描述插件的功能和行为，帮助用户了解插件的作用')} (${configForm.desc.length}/258)`}
                      inputProps={{ maxLength: 258 }}
                      disabled={isReadOnly}
                    />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <label className="block text-sm font-bold text-gray-800">插件详情 (markdown格式)</label>
                      {configForm.desc_mk && (
                        <IconButton
                          size="small"
                          onClick={() => setIsMarkdownPreviewOpen(true)}
                          className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 -ml-1 -mt-1"
                          title="预览Markdown"
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
                      placeholder="支持Markdown格式的详细描述..."
                      helperText={`使用Markdown语法编写富文本描述 (${(configForm.desc_mk || '').length}字符)`}
                      disabled={isReadOnly}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-800 mb-3">{t('plugins.versionHistory.pluginIcon', '插件图标')}</label>

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
                            {t('plugins.pluginConfig.currentSelection', '当前选择')}: <span className="text-2xl ml-2">{configForm.icon_uri || '☁️'}</span>
                          </Typography>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            {configTabValue === 'advanced' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between mb-4">
                  <Typography variant="subtitle2" className="font-medium">
                    {t('plugins.pluginConfig.codeToolsList', '代码工具列表')}
                  </Typography>
                  {currentToolsQuery?.isLoading && <CircularProgress size={20} />}
                </div>

                {codeTools.length === 0 ? (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <Typography variant="body1" color="text.secondary" className="mb-4">
                      {t('plugins.pluginConfig.noToolsConfigured', '暂无工具配置')}
                    </Typography>
                    {!isReadOnly && (
                      <Button variant="contained" startIcon={<Plus className="w-4 h-4" />} onClick={() => setIsCodePluginToolDialogOpen(true)}>
                        {t('plugins.pluginConfig.addCodeTool', '添加代码工具')}
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {codeTools.map((tool: PluginCodeInfo) => (
                      <Card key={tool.tool_id} className="p-4 border border-gray-200">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <Typography variant="subtitle1" className="font-medium mb-1">
                              {tool.name || t('plugins.pluginConfig.unnamedTool', '未命名工具')}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" className="mb-2">
                              {tool.desc || t('plugins.pluginConfig.noDescription', '暂无描述')}
                            </Typography>
                            <div className="flex items-center space-x-4 text-sm text-gray-500">
                              <span>
                                {t('plugins.pluginConfig.language', '语言')}: {tool.language || 'unknown'}
                              </span>
                              <span>{t('plugins.pluginConfig.codeTool', '代码工具')}</span>
                              <Chip label={t('plugins.pluginConfig.enabled', '启用')} size="small" color="success" />
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            {!isReadOnly && (
                              <IconButton
                                size="small"
                                onClick={() => {
                                  navigate(`/dashboard/plugins/${plugin_id}/tools/${tool.tool_id}`, {
                                    state: {
                                      source: 'plugin',
                                      pluginType: 'code',
                                    },
                                  })
                                }}
                                title={t('plugins.pluginConfig.editTool', '编辑工具')}
                              >
                                <Edit className="w-4 h-4" />
                              </IconButton>
                            )}
                            {!isReadOnly && (
                              <IconButton
                                size="small"
                                onClick={() => handleDeleteTool(tool)}
                                title={t('plugins.pluginConfig.deleteTool', '删除工具')}
                                disabled={deleteToolApi.isLoading}
                              >
                                {deleteToolApi.isLoading ? <CircularProgress size={16} /> : <Trash2 className="w-4 h-4 text-red-500 hover:text-red-700" />}
                              </IconButton>
                            )}
                          </div>
                        </div>
                      </Card>
                    ))}
                    {!isReadOnly && (
                      <div className="flex justify-center mt-4">
                        <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={() => setIsCodePluginToolDialogOpen(true)}>
                          {t('plugins.pluginConfig.addNewCodeTool', '添加新代码工具')}
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
                  <Typography variant="h6">输入参数配置</Typography>
                  <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={() => openParameterDialog(null)}>
                    添加输入参数
                  </Button>
                </div>

                {configForm.request_params?.length === 0 ? (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <Typography variant="body1" color="text.secondary">
                      暂无输入参数
                    </Typography>
                    <Typography variant="body2" color="text.secondary" className="mt-1">
                      点击"添加输入参数"开始配置
                    </Typography>
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
                              <Chip label={getInputMethodName(param.input_method)} size="small" variant="outlined" />
                              {param.is_required && <Chip label="必选" size="small" color="error" variant="outlined" />}
                            </div>
                            <Typography variant="body2" color="text.secondary" className="mt-1">
                              {param.desc}
                            </Typography>
                            {param.value && (
                              <Typography variant="caption" color="text.secondary" className="mt-1">
                                默认值: {param.value}
                              </Typography>
                            )}
                          </div>
                          <div className="flex items-center space-x-2">
                            <IconButton size="small" onClick={() => openParameterDialog(param)} title="编辑参数">
                              <Edit className="w-4 h-4" />
                            </IconButton>
                            <IconButton size="small" onClick={() => handleDeleteParameter(index)} title="删除参数">
                              <Trash2 className="w-4 h-4" />
                            </IconButton>
                          </div>
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
              {t('common.actions.cancel', '取消')}
            </Button>
            <Button
              variant="contained"
              color="success"
              onClick={() => setIsPublishDialogOpen(true)}
              startIcon={<Rocket className="w-4 h-4" />}
              className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 mr-3"
            >
              {t('plugins.pluginConfig.publishPlugin', '发布插件')}
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
                  {t('common.actions.saving', '保存中...')}
                </div>
              ) : (
                t('plugins.config.saveConfig', '保存配置')
              )}
            </Button>
          </div>
        )}
      </div>

      {/* Unified Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />

      {/* Code Plugin Tool Form Dialog */}
      <CodePluginToolFormDialog
        open={isCodePluginToolDialogOpen}
        loading={createCodeToolApi.isLoading}
        form={codePluginToolForm}
        onFormChange={handleCodePluginToolFormChange}
        onSubmit={handleCodePluginToolSubmit}
        onCancel={handleCodePluginToolDialogCancel}
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
        <DialogTitle>Markdown预览</DialogTitle>
        <DialogContent dividers>
          <div className="prose prose-sm max-w-none overflow-y-auto" style={{ maxHeight: '60vh' }}>
            <ReactMarkdown>{configForm.desc_mk || ''}</ReactMarkdown>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsMarkdownPreviewOpen(false)}>关闭</Button>
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
        <DialogTitle>{editingParameter ? '编辑参数' : '添加参数'}</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <div>
              <div className="flex items-center justify-between mb-2">
                <Typography variant="subtitle2">
                  参数名称 <span className="text-red-500 ml-1">*</span>
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
                    必选参数
                  </label>
                </div>
              </div>
              <TextField
                fullWidth
                value={parameterForm.name}
                onChange={e => handleParameterFormChange('name', e.target.value)}
                placeholder="请输入参数名称..."
                helperText={`参数名称 (${parameterForm.name.length}/128)`}
                inputProps={{ maxLength: 128 }}
              />
            </div>
            <div>
              <Typography variant="subtitle2" className="mb-2">
                参数描述
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={2}
                value={parameterForm.desc}
                onChange={e => handleParameterFormChange('desc', e.target.value)}
                placeholder="请输入参数描述..."
                helperText={`参数描述 (${parameterForm.desc.length}/256)`}
                inputProps={{ maxLength: 256 }}
              />
            </div>
            <div>
              <Typography variant="subtitle2" className="mb-2">
                参数类型
              </Typography>
              <FormControl fullWidth>
                <Select value={parameterForm.type} onChange={e => handleParameterFormChange('type', e.target.value)}>
                  <MenuItem value={1}>字符串</MenuItem>
                  <MenuItem value={2}>数字</MenuItem>
                  <MenuItem value={3}>布尔值</MenuItem>
                  <MenuItem value={4}>字符串数组</MenuItem>
                  <MenuItem value={5}>数字数组</MenuItem>
                  <MenuItem value={6}>布尔数组</MenuItem>
                  <MenuItem value={7}>对象</MenuItem>
                </Select>
              </FormControl>
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
                  非运行时参数
                </label>
              </div>
              <Typography variant="caption" className="text-gray-500 mt-1 block">
                勾选后需要设置参数默认值
              </Typography>
            </div>
            {!parameterForm.is_runtime && (
              <div>
                <Typography variant="subtitle2" className="mb-2">
                  默认值
                </Typography>
                <TextField
                  fullWidth
                  value={parameterForm.value}
                  onChange={e => handleParameterFormChange('value', e.target.value)}
                  placeholder="请输入默认值..."
                  helperText="非运行时参数的默认值"
                />
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
            取消
          </Button>
          <Button variant="contained" onClick={handleSaveParameter}>
            {editingParameter ? '更新' : '添加'}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}

export default CodePluginConfiguration
