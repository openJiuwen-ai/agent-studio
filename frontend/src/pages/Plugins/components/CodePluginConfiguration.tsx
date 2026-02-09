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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
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
  const [deletingToolId, setDeletingToolId] = useState<string | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [toolToDelete, setToolToDelete] = useState<PluginCodeInfo | null>(null)

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
      showError(t('plugins.messages.fillRequiredFields'))
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
              publishVersion: pluginConfigData?.plugin_version,
            },
          })
        }
      } else {
        showError(`${t('plugins.pluginConfig.createFailed')}: ${response.message || t('plugins.messages.unknownError')}`)
      }
    } catch (error: unknown) {
      console.error(t('plugins.pluginConfig.createFailed'), error)
      const errorMessage = error.response?.data?.message || error.message || t('plugins.pluginConfig.createFailedRetry')
      showError(errorMessage)
    }
  }

  const handleDeleteTool = async (tool: PluginCodeInfo) => {
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
        showSuccess(t('plugins.pluginConfig.toolDeletedSuccess', { name: tool.name || t('plugins.pluginConfig.unnamedTool') }))
        // Refresh the tool list after successful deletion (only in edit mode)
        if (configTabValue === 'advanced' && !isReadOnly) {
          setTimeout(async () => {
            await codeToolsQuery.refetch()
          }, 5) // Small delay to ensure backend processes deletion
        }
      } else {
        showError(`${t('plugins.pluginConfig.deleteFailed')}: ${response.message || t('plugins.messages.unknownError')}`)
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
            {t('plugins.pluginConfig.notFound')}
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
                    placeholder={t('plugins.basicInfo.name')}
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
                  title={t('plugins.actions.editPluginName')}
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
              {t('plugins.basicInfoLabel')}
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

            <Tabs value={configTabValue} onChange={(e, newValue) => handleTabChange(newValue)} className="mb-6">
              <Tab label={t('plugins.pluginConfig.basicTab')} value="basic" />
              <Tab label={t('plugins.pluginConfig.toolsTab')} value="advanced" />
            </Tabs>

            {/* Tab Content */}
            {configTabValue === 'basic' && (
              <div className="space-y-6">
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-bold text-gray-800 mb-3">{t('plugins.pluginConfig.pluginDescription')}</label>
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
              </div>
            )}

            {configTabValue === 'advanced' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between mb-4">
                  <Typography variant="subtitle2" className="font-medium">
                    {t('plugins.pluginConfig.codeToolsList')}
                  </Typography>
                  {currentToolsQuery?.isLoading && <CircularProgress size={20} />}
                </div>

                {codeTools.length === 0 ? (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <Typography variant="body1" color="text.secondary" className="mb-4">
                      {t('plugins.pluginConfig.noToolsConfigured')}
                    </Typography>
                    {!isReadOnly && (
                      <Button variant="contained" startIcon={<Plus className="w-4 h-4" />} onClick={() => setIsCodePluginToolDialogOpen(true)}>
                        {t('plugins.pluginConfig.addCodeTool')}
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {codeTools.map((tool: PluginCodeInfo) => (
                      <Card
                        key={tool.tool_id}
                        className="p-4 border border-gray-200 hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => {
                          navigate(`/dashboard/plugins/${plugin_id}/tools/${tool.tool_id}`, {
                            state: {
                              source: 'plugin',
                              pluginType: 'code',
                              fromPublishVersion: isReadOnly,
                              publishVersion: pluginConfigData?.plugin_version,
                              toolsData: isReadOnly ? codeTools : undefined,
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
                              <span>{t('plugins.pluginConfig.language')}: {tool.language || 'unknown'}</span>
                              <span>{t('plugins.pluginConfig.codeTool')}</span>
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
                                      pluginType: 'code',
                                      fromPublishVersion: isReadOnly,
                                      publishVersion: pluginConfigData?.plugin_version,
                                      toolsData: isReadOnly ? codeTools : undefined,
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
                                  {t('plugins.pluginConfig.deleting')}
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
                        <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={() => setIsCodePluginToolDialogOpen(true)}>
                          {t('plugins.pluginConfig.addNewCodeTool')}
                        </Button>
                      </div>
                    )}
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

export default CodePluginConfiguration
