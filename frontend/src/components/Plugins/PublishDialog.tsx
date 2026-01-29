import React, { useState, useEffect } from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Typography, Box, CircularProgress } from '@mui/material'
import { Rocket, Upload } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface PluginConfigData {
  name: string
  desc: string
  desc_mk: string
  icon_uri: string
  url: string
  authMethod: string
  request_params?: any[]
}

interface PublishDialogProps {
  open: boolean
  pluginName: string
  pluginId: string
  spaceId: string
  onClose: () => void
  onPublish: (version: string, versionDesc: string) => void
  loading?: boolean
  latestVersion?: string
  configData?: PluginConfigData
  updatePluginApi?: any
}

const PublishDialog: React.FC<PublishDialogProps> = ({
  open,
  pluginName,
  pluginId,
  spaceId,
  onClose,
  onPublish,
  loading = false,
  latestVersion,
  configData,
  updatePluginApi
}) => {
  const { t } = useTranslation()
  const [version, setVersion] = useState(latestVersion || 'v0.0.1')
  const [versionDesc, setVersionDesc] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      // Dialog opened - initialize with latest version
      setVersion(latestVersion || 'v0.0.1')
      setVersionDesc('')
    }
  }, [open, latestVersion])

  const handleSubmit = async () => {
    if (!version.trim()) {
      return
    }

    if (!versionDesc.trim()) {
      return
    }

    // If configData and updatePluginApi are provided, first update the plugin
    if (configData && updatePluginApi) {
      try {
        setIsSaving(true)
        const updateRequest = {
          space_id: spaceId,
          plugin_id: pluginId,
          name: configData.name,
          desc: configData.desc,
          desc_mk: configData.desc_mk,
          icon_uri: configData.icon_uri,
          url: configData.url,
          auth_method: configData.authMethod,
          request_params: configData.request_params || [],
        }

        console.log('Saving plugin configuration before publish:', updateRequest)
        const updateResponse = await updatePluginApi.mutateAsync(updateRequest)

        if (updateResponse.code !== 200) {
          console.error('Failed to save plugin configuration:', updateResponse)
          setIsSaving(false)
          return
        }

        console.log('Plugin configuration saved successfully, now publishing...')
        setIsSaving(false)
      } catch (error) {
        console.error('Error saving plugin configuration:', error)
        setIsSaving(false)
        return
      }
    }

    // Call the publish callback
    onPublish(version.trim(), versionDesc.trim())
  }

  const handleCancel = () => {
    if (!loading) {
      setVersion('v0.0.1')
      setVersionDesc('')
      onClose()
    }
  }

  const isSubmitDisabled = loading || isSaving || !version.trim() || !versionDesc.trim()

  return (
    <Dialog open={open} onClose={handleCancel} maxWidth="sm" fullWidth>
      <DialogTitle className="flex items-center space-x-2">
        <Rocket className="w-5 h-5 text-blue-600" />
        <span>{t('plugins.pluginConfig.publishPlugin', '发布插件')}</span>
      </DialogTitle>

      <DialogContent>
        <Box className="space-y-4">
          {/* Plugin Info */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <Typography variant="subtitle2" color="text.secondary" className="mb-1">
              {t('plugins.basicInfo.name', '插件名称')}
            </Typography>
            <Typography variant="body1" className="font-medium">
              {pluginName}
            </Typography>
            <Typography variant="subtitle2" color="text.secondary" className="mb-1 mt-2">
              {t('plugins.dialog.publishPlugin.pluginId', '插件ID')}
            </Typography>
            <Typography variant="body2" color="text.secondary" className="font-mono">
              {pluginId}
            </Typography>
          </div>

          {/* Version Input */}
          <div>
            <TextField
              fullWidth
              label={t('plugins.dialog.publishPlugin.versionNumber', '版本号')}
              placeholder={t('plugins.dialog.publishPlugin.versionPlaceholder', '例如: v1.0.0')}
              value={version}
              onChange={e => setVersion(e.target.value)}
              disabled={loading}
              helperText={t('plugins.dialog.publishPlugin.versionHelperText', '请输入版本号，推荐使用语义化版本格式 (如 v1.0.0)')}
              className="mb-2"
            />
          </div>

          {/* Version Description */}
          <div>
            <TextField
              fullWidth
              label={t('plugins.dialog.publishPlugin.versionDescription', '版本描述')}
              placeholder={t('plugins.dialog.publishPlugin.versionDescPlaceholder', '描述此版本的更新内容...')}
              value={versionDesc}
              onChange={e => setVersionDesc(e.target.value)}
              disabled={loading}
              multiline
              rows={3}
              helperText={`${t('plugins.dialog.publishPlugin.versionDescHelperText', '请详细描述此版本的更新内容、新功能或修复的问题')} (${versionDesc.length}/256)`}
              inputProps={{ maxLength: 256 }}
            />
          </div>
        </Box>
      </DialogContent>

      <DialogActions className="p-6">
        <Button onClick={handleCancel} disabled={loading} variant="outlined">
          {t('common.buttons.cancel', '取消')}
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={isSubmitDisabled}
          variant="contained"
          startIcon={loading || isSaving ? <CircularProgress size={16} /> : <Upload className="w-4 h-4" />}
          className="bg-blue-600 hover:bg-blue-700"
        >
          {loading
            ? t('common.publishing', '发布中...')
            : isSaving
              ? t('common.actions.saving', '保存中...')
              : t('common.confirmPublish', '确认发布')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default PublishDialog
