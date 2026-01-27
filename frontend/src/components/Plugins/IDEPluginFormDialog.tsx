import React from 'react'
import { useTranslation } from 'react-i18next'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Tooltip,
  CircularProgress,
} from '@mui/material'
import { Info, Code } from 'lucide-react'

interface IDEPluginForm {
  name: string
  description: string
  desc_mk?: string
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
        <span>{isEditing ? t('plugins.dialog.idePlugin.editTitle') : t('plugins.dialog.idePlugin.createTitle')}</span>
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
              placeholder={t('plugins.dialog.idePlugin.namePlaceholder')}
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
              helperText={`${t('plugins.dialog.idePlugin.descriptionHelperText')} (${form.description.length}/40)`}
              inputProps={{ maxLength: 40 }}
            />
          </div>

          {/* Plugin Markdown Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.dialog.cloudPluginForm.detailsLabel')} <span className="text-gray-400 ml-1">{t('plugins.dialog.cloudPluginForm.optional')}</span>
            </label>
            <TextField
              value={form.desc_mk || ''}
              onChange={e => onFormChange('desc_mk', e.target.value)}
              fullWidth
              multiline
              rows={6}
              placeholder={t('plugins.dialog.cloudPluginForm.detailsPlaceholder')}
              helperText={t('plugins.dialog.cloudPluginForm.detailsHelperText', { count: (form.desc_mk || '').length })}
            />
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
          disabled={loading || !form.name.trim() || !form.description.trim()}
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
