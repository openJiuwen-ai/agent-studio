import React from 'react'
import { useTranslation } from 'react-i18next'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Tooltip,
  CircularProgress,
} from '@mui/material'
import { Info, Code, Terminal } from 'lucide-react'

interface IDEPluginForm {
  name: string
  description: string
  desc_mk?: string
  runtime: 'python3' | 'nodejs'
}

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

interface IDEPluginFormDialogProps {
  open: boolean
  isEditing: boolean
  loading?: boolean
  form: IDEPluginForm
  editingPlugin: Plugin | null
  onFormChange: (_field: string, _value: unknown) => void
  onSubmit: (_isEditing: boolean) => void
  onCancel: () => void
}

const runtimeOptions = [
  { value: 'python3', label: 'Python 3', icon: '🐍', description: '适用于数据分析、机器学习、自动化脚本' },
  { value: 'nodejs', label: 'Node.js', icon: '🟢', description: '适用于Web API、实时应用、前端构建工具' },
]

const IDEPluginFormDialog: React.FC<IDEPluginFormDialogProps> = ({
  open,
  isEditing,
  loading = false,
  form,
  _editingPlugin,
  onFormChange,
  onSubmit,
  onCancel,
}) => {
  const { t } = useTranslation()

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="md" fullWidth>
      <DialogTitle className="flex items-center space-x-2">
        <Code className="w-5 h-5 text-blue-600" />
        <span>{isEditing ? t('plugins.dialog.idePlugin.editTitle', '编辑本地代码插件') : t('plugins.dialog.idePlugin.createTitle', '创建本地代码插件')}</span>
      </DialogTitle>

      <DialogContent>
        <div className="space-y-6">
          {/* Plugin Name */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.dialog.cloudPluginForm.name')} <span className="text-red-500 ml-1">*</span>
              <Tooltip title={t('plugins.dialog.idePlugin.nameTooltip')} placement="top">
                <Info className="w-4 h-4 ml-1 text-gray-400 cursor-help" />
              </Tooltip>
            </label>
            <TextField
              value={form.name}
              onChange={e => onFormChange('name', e.target.value)}
              fullWidth
              required
              placeholder={t('plugins.dialog.idePlugin.namePlaceholder', '例如：数据处理器、API调用器、文件转换器')}
              helperText={`${t('plugins.dialog.idePlugin.nameHelperText')} (${form.name.length}/128)`}
              inputProps={{ maxLength: 128 }}
            />
          </div>

          {/* Plugin Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.description')} <span className="text-red-500 ml-1">*</span>
              <Tooltip title={t('plugins.dialog.idePlugin.descriptionTooltip')} placement="top">
                <Info className="w-4 h-4 ml-1 text-gray-400 cursor-help" />
              </Tooltip>
            </label>
            <TextField
              value={form.description}
              onChange={e => onFormChange('description', e.target.value)}
              fullWidth
              required
              multiline
              rows={3}
              placeholder={t('plugins.dialog.idePlugin.descriptionPlaceholder')}
              helperText={`${t('plugins.dialog.idePlugin.descriptionHelperText')} (${form.description.length}/258)`}
              inputProps={{ maxLength: 258 }}
            />
          </div>

          {/* Plugin Markdown Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              插件详情 <span className="text-gray-400 ml-1">(可选)</span>
            </label>
            <TextField
              value={form.desc_mk || ''}
              onChange={e => onFormChange('desc_mk', e.target.value)}
              fullWidth
              multiline
              rows={6}
              placeholder="支持Markdown格式的详细描述..."
              helperText={`使用Markdown语法编写富文本描述 (${(form.desc_mk || '').length}字符)`}
            />
          </div>

          {/* Runtime Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.dialog.idePlugin.runtime')} <span className="text-red-500 ml-1">*</span>
              <Tooltip title={t('plugins.dialog.idePlugin.runtimeTooltip')} placement="top">
                <Info className="w-4 h-4 ml-1 text-gray-400 cursor-help" />
              </Tooltip>
            </label>
            <FormControl fullWidth required>
              <InputLabel>{t('plugins.dialog.idePlugin.runtimeEnvironment')}</InputLabel>
              <Select value={form.runtime} onChange={e => onFormChange('runtime', e.target.value)} label={t('plugins.dialog.idePlugin.runtimeEnvironment')}>
                {runtimeOptions.map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    <div className="flex flex-col space-y-1 py-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">{option.icon}</span>
                        <span className="font-medium">{option.label}</span>
                      </div>
                      <span className="text-xs text-gray-500 ml-8">{option.description}</span>
                    </div>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </div>

          {/* Runtime Information */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <Terminal className="w-5 h-5 text-blue-600 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-blue-900 mb-2">{t('plugins.dialog.idePlugin.runtimeInfoTitle')}</h4>
                <div className="space-y-2 text-sm text-blue-800">
                  <div>
                    <strong>Python 3:</strong> {t('plugins.dialog.idePlugin.python3Desc')}
                  </div>
                  <div>
                    <strong>Node.js:</strong> {t('plugins.dialog.idePlugin.nodejsDesc')}
                  </div>
                  <div className="text-blue-600 text-xs mt-2">{t('plugins.dialog.idePlugin.runtimeHint')}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>

      <DialogActions className="px-6 pb-4">
        <Button onClick={onCancel} variant="outlined" disabled={loading}>
          {t('common.buttons.cancel')}
        </Button>
        <Button
          onClick={() => onSubmit(isEditing)}
          variant="contained"
          color="primary"
          disabled={loading || !form.name.trim() || !form.description.trim() || !form.runtime}
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
        >
          {loading ? (
            <>
              <CircularProgress size={16} className="mr-2" />
              {isEditing ? t('common.status.saving') : t('common.status.creating')}
            </>
          ) : isEditing ? (
            t('plugins.dialog.cloudPluginForm.saveChanges')
          ) : (
            t('plugins.dialog.cloudPluginForm.create')
          )}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default IDEPluginFormDialog
