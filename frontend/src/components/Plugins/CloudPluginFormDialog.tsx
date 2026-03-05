import React from 'react'
import { useTranslation } from 'react-i18next'
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Tooltip, CircularProgress, Typography } from '@mui/material'
import { Info } from 'lucide-react'

interface CloudPluginForm {
  name: string
  description: string
  desc_mk?: string
  url: string
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

interface CloudPluginFormDialogProps {
  open: boolean
  isEditing: boolean
  loading?: boolean
  form: CloudPluginForm
  editingPlugin: Plugin | null
  onFormChange: (_field: string, _value: unknown) => void
  onSubmit: (_isEditing: boolean) => void
  onCancel: () => void
}

const CloudPluginFormDialog: React.FC<CloudPluginFormDialogProps> = ({
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
  // URL validation function
  const isValidUrl = (url: string): boolean => {
    try {
      const urlObj = new URL(url)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      return false
    }
  }

  // Check URL length (1000 bytes max)
  const MAX_URL_BYTES = 1000
  const getUrlByteLength = (url: string): number => {
    return new Blob([url]).size
  }
  const isUrlLengthValid = form.url ? getUrlByteLength(form.url) <= MAX_URL_BYTES : true

  // Check if URL is valid for UI feedback
  const isUrlValid = form.url ? isValidUrl(form.url) : true

  // Form validation - check if all required fields are valid
  const isFormValid = form.name.trim() && form.description.trim() && form.url.trim() && isUrlValid && isUrlLengthValid
  return (
    <Dialog open={open} onClose={onCancel} maxWidth="md" fullWidth>
      <DialogTitle>{isEditing ? t('plugins.dialog.editPlugin.title') : t('plugins.dialog.cloudPluginForm.create')}</DialogTitle>
      <DialogContent>
        <div className="space-y-6">
          {/* Plugin Name */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.dialog.cloudPluginForm.name')} <span className="text-red-500 ml-1">*</span>
            </label>
            <TextField
              value={form.name}
              onChange={e => onFormChange('name', e.target.value)}
              fullWidth
              required
              placeholder={t('plugins.dialog.cloudPluginForm.namePlaceholder')}
              helperText={`${t('plugins.dialog.cloudPluginForm.nameHelperText')} (${form.name.length}/128)`}
              inputProps={{ maxLength: 128 }}
            />
          </div>

          {/* Plugin Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.dialog.cloudPluginForm.description')} <span className="text-red-500 ml-1">*</span>
            </label>
            <TextField
              value={form.description}
              onChange={e => onFormChange('description', e.target.value)}
              fullWidth
              required
              multiline
              rows={3}
              placeholder={t('plugins.dialog.cloudPluginForm.descriptionPlaceholder')}
              helperText={`${t('plugins.dialog.cloudPluginForm.descriptionHelperText')} (${form.description.length}/258)`}
              inputProps={{ maxLength: 258 }}
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

          {/* Plugin URL */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.dialog.cloudPluginForm.url')} <span className="text-red-500 ml-1">*</span>
            </label>
            <TextField
              value={form.url}
              onChange={e => onFormChange('url', e.target.value)}
              fullWidth
              required
              placeholder={t('plugins.dialog.cloudPluginForm.urlPlaceholder')}
              helperText={
                form.url && !isUrlValid
                  ? t('plugins.dialog.cloudPluginForm.urlInvalid')
                  : form.url && !isUrlLengthValid
                    ? t('plugins.dialog.cloudPluginForm.urlLengthError', { max: MAX_URL_BYTES, current: getUrlByteLength(form.url) })
                    : t('plugins.dialog.cloudPluginForm.urlHelper', { current: form.url ? getUrlByteLength(form.url) : 0, max: MAX_URL_BYTES })
              }
              error={Boolean(form.url && (!isUrlValid || !isUrlLengthValid))}
            />
          </div>
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>{t('common.buttons.cancel')}</Button>
        <Button onClick={() => onSubmit(isEditing)} variant="contained" color="primary" disabled={!isFormValid || loading}>
          {loading ? (
            <>
              <CircularProgress size={16} className="mr-2" />
              {t('plugins.dialog.cloudPluginForm.saving')}
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

export default CloudPluginFormDialog
