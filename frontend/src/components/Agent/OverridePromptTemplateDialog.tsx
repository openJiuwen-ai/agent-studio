import React from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Alert, Typography } from '@mui/material'
import { AlertTriangle } from 'lucide-react'
import { useScopedTranslation } from '@/i18n'

interface OverridePromptTemplateDialogProps {
  open: boolean
  onClose: () => void
  onJump: () => void // 不覆盖直接跳转
  onOverwrite: () => void // 覆盖并跳转
}

const OverridePromptTemplateDialog: React.FC<OverridePromptTemplateDialogProps> = ({ open, onClose, onJump, onOverwrite }) => {
  const { t } = useScopedTranslation('agents.agentEditor.systemPrompt')
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-6 h-6 text-orange-500" />
          <span>{t('promptDialog.goToTemplateManagement')}</span>
        </div>
      </DialogTitle>
      <DialogContent>
        <div className="space-y-3">
          <Typography variant="body2">{t('overwritePromptTemplateDialog.description')}</Typography>
          <Alert severity="warning">
            <div className="text-sm">
              <div className="font-medium">{t('overwritePromptTemplateDialog.instructionsTitle')}</div>
              <ul className="list-disc list-inside mt-1">
                <li>{t('overwritePromptTemplateDialog.overwriteAndJump')}</li>
                <li>{t('overwritePromptTemplateDialog.notOverwriteAndJump')}</li>
              </ul>
            </div>
          </Alert>
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('overwritePromptTemplateDialog.cancel')}</Button>
        <Button variant="contained" color="primary" onClick={onJump}>
          {t('overwritePromptTemplateDialog.notOverwriteAndJumpLabel')}
        </Button>
        <Button variant="contained" color="warning" startIcon={<AlertTriangle className="w-4 h-4" />} onClick={onOverwrite}>
          {t('overwritePromptTemplateDialog.overwriteAndJumpLabel')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default OverridePromptTemplateDialog
