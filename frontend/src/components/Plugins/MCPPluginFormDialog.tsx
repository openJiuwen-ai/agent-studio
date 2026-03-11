import React from 'react'
import { useTranslation } from 'react-i18next'
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, CircularProgress, MenuItem } from '@mui/material'
import { Cpu } from 'lucide-react'
import { isFilePathValid } from '../../utils/validationUtils'

interface MCPPluginForm {
  name: string
  description: string
  desc_mk?: string
  url: string
  transport: number
}

export const MCP_TRANSPORT_OPTIONS = [
  { value: 1, labelKey: 'plugins.mcpTransport.stdio' },
  { value: 2, labelKey: 'plugins.mcpTransport.sse' },
  { value: 3, labelKey: 'plugins.mcpTransport.streamableHttp' },
  { value: 4, labelKey: 'plugins.mcpTransport.openapi' },
  { value: 5, labelKey: 'plugins.mcpTransport.playwright' },
]

export const MCP_TRANSPORT_DEFAULT = 2 // SSE

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

interface MCPPluginFormDialogProps {
  open: boolean
  isEditing: boolean
  loading?: boolean
  form: MCPPluginForm
  editingPlugin: Plugin | null
  onFormChange: (_field: string, _value: unknown) => void
  onSubmit: (_isEditing: boolean) => void
  onCancel: () => void
}

const MCPPluginFormDialog: React.FC<MCPPluginFormDialogProps> = ({
  open,
  isEditing,
  loading = false,
  form,
  editingPlugin: _editingPlugin,
  onFormChange,
  onSubmit,
  onCancel,
}) => {
  const { t } = useTranslation()

  // Normalize transport to number to handle cases where it arrives as a string
  const transportNum = Number(form.transport)

  // Determine if transport uses a file path instead of a URL
  const isFilePath = transportNum === 1 /* STDIO */ || transportNum === 4 /* OpenAPI */

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
  const isUrlValid = form.url ? isValidUrl(form.url) : true

  // Determine validity of the url/path field based on transport
  const isUrlFieldValid = isFilePath
    ? (form.url ? isFilePathValid(form.url) : true)
    : isUrlValid && isUrlLengthValid

  const isFormValid = form.name.trim() && form.description.trim() && form.url.trim() && isUrlFieldValid

  // Compute label, placeholder and helper text based on transport
  const urlFieldLabel = isFilePath
    ? transportNum === 4
      ? t('plugins.dialog.mcpPluginForm.openApiFileLabel')
      : t('plugins.dialog.mcpPluginForm.stdioPathLabel')
    : t('plugins.dialog.mcpPluginForm.url')

  const urlFieldPlaceholder = isFilePath
    ? transportNum === 4
      ? t('plugins.dialog.mcpPluginForm.openApiFilePlaceholder')
      : t('plugins.dialog.mcpPluginForm.stdioPathPlaceholder')
    : t('plugins.dialog.mcpPluginForm.urlPlaceholder')

  const urlFieldHelperText = isFilePath
    ? form.url && !isFilePathValid(form.url)
      ? t('plugins.dialog.mcpPluginForm.filePathInvalid')
      : transportNum === 4
        ? t('plugins.dialog.mcpPluginForm.openApiFileHelper')
        : t('plugins.dialog.mcpPluginForm.stdioPathHelper')
    : form.url && !isUrlValid
      ? t('plugins.dialog.cloudPluginForm.urlInvalid')
      : form.url && !isUrlLengthValid
        ? t('plugins.dialog.cloudPluginForm.urlLengthError', { max: MAX_URL_BYTES, current: getUrlByteLength(form.url) })
        : t('plugins.dialog.mcpPluginForm.urlHelper', { current: form.url ? getUrlByteLength(form.url) : 0, max: MAX_URL_BYTES })

  const urlFieldError = isFilePath
    ? Boolean(form.url && !isFilePathValid(form.url))
    : Boolean(form.url && (!isUrlValid || !isUrlLengthValid))

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="md" fullWidth>
      <DialogTitle className="flex items-center space-x-2">
        <Cpu className="w-5 h-5 text-purple-600" />
        <span>{isEditing ? t('plugins.dialog.mcpPluginForm.editTitle') : t('plugins.dialog.mcpPluginForm.createTitle')}</span>
      </DialogTitle>

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
              placeholder={t('plugins.dialog.mcpPluginForm.namePlaceholder')}
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
              placeholder={t('plugins.dialog.mcpPluginForm.descriptionPlaceholder')}
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

          {/* Transport Type — shown before URL field */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.dialog.mcpPluginForm.transport')} <span className="text-red-500 ml-1">*</span>
            </label>
            <TextField
              select
              value={form.transport}
              onChange={e => onFormChange('transport', Number(e.target.value))}
              fullWidth
              helperText={t('plugins.dialog.mcpPluginForm.transportHelper')}
            >
              {MCP_TRANSPORT_OPTIONS.map(opt => (
                <MenuItem key={opt.value} value={opt.value}>
                  {t(opt.labelKey)}
                </MenuItem>
              ))}
            </TextField>
          </div>

          {/* MCP Server URL / OpenAPI file / StdIO path — label and validation depend on transport */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {urlFieldLabel} <span className="text-red-500 ml-1">*</span>
            </label>
            <TextField
              value={form.url}
              onChange={e => onFormChange('url', e.target.value)}
              fullWidth
              required
              placeholder={urlFieldPlaceholder}
              helperText={urlFieldHelperText}
              error={urlFieldError}
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
          disabled={!isFormValid || loading}
          className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        >
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

export default MCPPluginFormDialog
