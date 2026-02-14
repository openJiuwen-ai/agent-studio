import React, { useState } from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, Typography, Button, IconButton, TextField, Alert, Box } from '@mui/material'
import { Trash2, Plus, Copy, Check, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { PromptService, type Prompt } from '@test-agentstudio/api-client'
import { ApiError } from '@test-agentstudio/api-client'
import { copyToClipboard } from '@/utils/prompts/utils'
import ConditionalTooltip from './ConditionalTooltip'

interface DeletePromptDialogProps {
  open: boolean
  onClose: () => void
  onDeleteSuccess: () => void
  prompt: Prompt | null
  workspaceId: string
  showSnackbar: (message: string, severity: 'success' | 'error' | 'warning' | 'info') => void
}

export const DeletePromptDialog: React.FC<DeletePromptDialogProps> = ({ open, onClose, onDeleteSuccess, prompt, workspaceId, showSnackbar }) => {
  const { t } = useTranslation()
  const [deleteInputValue, setDeleteInputValue] = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [copiedDeleteKey, setCopiedDeleteKey] = useState(false)

  // 复制删除弹窗中的prompt_key
  const handleCopyDeleteKey = async () => {
    if (!prompt) return

    try {
      // 使用统一的 copyToClipboard 函数
      await copyToClipboard(
        prompt.prompt_key,
        snackbar => showSnackbar(snackbar.message, snackbar.severity),
        t('components.prompts.deletePromptDialog.promptKeyCopied'),
      )
      setCopiedDeleteKey(true)
      setTimeout(() => setCopiedDeleteKey(false), 2000)
    } catch (error) {
      console.error('复制失败:', error)
      showSnackbar(t('components.prompts.deletePromptDialog.copyFailed'), 'error')
    }
  }

  // 确认删除
  const handleConfirmDelete = async () => {
    if (!prompt || deleteInputValue !== prompt.prompt_key) {
      return
    }

    setDeleteLoading(true)
    try {
      const response = await PromptService.deletePrompt(prompt.id, workspaceId)

      if (response.code === 0) {
        // 删除成功
        showSnackbar(t('components.prompts.deletePromptDialog.deleteSuccess'), 'success')
        handleClose()
        onDeleteSuccess()
      } else if (response.code === 501) {
        showSnackbar(t('components.prompts.deletePromptDialog.deleteFailedAssociated'), 'error')
      } else {
        showSnackbar(response.msg || t('components.prompts.deletePromptDialog.deleteFailed'), 'error')
      }
    } catch (error) {
      console.error('删除提示词失败:', error)

      // 处理 API 错误，显示具体的错误信息
      if (error instanceof ApiError) {
        // 检查错误码，优先使用 ApiError 的 code 属性
        const errorCode = error.code || error.response?.code
        if (errorCode === 501) {
          showSnackbar(t('components.prompts.deletePromptDialog.deleteFailedAssociated'), 'error')
          return
        }
        const errorMsg = error.response?.msg || error.response?.message || error.message || t('components.prompts.deletePromptDialog.deleteFailed')
        showSnackbar(errorMsg, 'error')
      } else if (error instanceof Error) {
        // 检查错误消息中是否包含关联信息（备用方案）
        if (error.message && error.message.includes('associated with other obj')) {
          showSnackbar(t('components.prompts.deletePromptDialog.deleteFailedAssociated'), 'error')
          return
        }
        showSnackbar(error.message || t('components.prompts.deletePromptDialog.deleteFailedRetry'), 'error')
      } else {
        showSnackbar(t('components.prompts.deletePromptDialog.deleteFailedRetry'), 'error')
      }
    } finally {
      setDeleteLoading(false)
    }
  }

  // 关闭对话框
  const handleClose = () => {
    setDeleteInputValue('')
    setCopiedDeleteKey(false)
    onClose()
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        className: 'bg-gradient-to-br from-red-50/50 to-pink-50/50',
      }}
    >
      <DialogTitle className="bg-white/90 backdrop-blur-sm border-b border-red-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-red-600 to-pink-600 rounded-xl flex items-center justify-center shadow-sm">
              <Trash2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <Typography variant="h6" className="text-gray-800 font-semibold">
                {t('components.prompts.deletePromptDialog.title')}
              </Typography>
              <Typography variant="body2" className="text-gray-600">
                {t('components.prompts.deletePromptDialog.subtitle')}
              </Typography>
            </div>
          </div>
          <IconButton size="small" onClick={handleClose} className="text-gray-500 hover:bg-gray-100">
            <Plus className="w-5 h-5 rotate-45" />
          </IconButton>
        </div>
      </DialogTitle>

      <DialogContent className="p-6">
        {prompt && (
          <div className="space-y-6">
            {/* 警告信息 */}
            <Alert severity="warning" className="mb-4">
              <Typography variant="body2">
                <strong>{t('components.prompts.deletePromptDialog.warning')}</strong>
                {t('components.prompts.deletePromptDialog.warningDescription')}
              </Typography>
            </Alert>

            {/* 提示词信息 */}
            <div className="bg-white/60 p-4 rounded-lg border border-gray-200">
              <Typography variant="subtitle1" className="font-semibold text-gray-800 mb-2">
                {t('components.prompts.deletePromptDialog.promptToDelete')}
              </Typography>
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600 flex-shrink-0">{t('components.prompts.deletePromptDialog.name')}:</span>
                  <ConditionalTooltip title={prompt.name}>
                    <span className="font-medium truncate cursor-pointer max-w-2xl">{prompt.name}</span>
                  </ConditionalTooltip>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600 flex-shrink-0">{t('components.prompts.deletePromptDialog.description')}:</span>
                  <ConditionalTooltip title={prompt.description || ''}>
                    <span className="text-gray-800 truncate cursor-pointer max-w-2xl">{prompt.description || '\u00A0'}</span>
                  </ConditionalTooltip>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600 flex-shrink-0">{t('components.prompts.deletePromptDialog.promptKey')}:</span>
                  <ConditionalTooltip title={prompt.prompt_key}>
                    <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded truncate cursor-pointer max-w-64">{prompt.prompt_key}</span>
                  </ConditionalTooltip>
                  <button
                    onClick={e => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleCopyDeleteKey()
                    }}
                    className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                    title={t('components.prompts.deletePromptDialog.copyPromptKey')}
                  >
                    {copiedDeleteKey ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>

            {/* 输入验证 */}
            <div>
              <Typography variant="body1" className="font-medium text-gray-800 mb-2">
                {t('components.prompts.deletePromptDialog.inputPromptKey')}
              </Typography>
              <TextField
                fullWidth
                value={deleteInputValue}
                onChange={e => setDeleteInputValue(e.target.value)}
                size="small"
                className="bg-white/80"
                InputProps={{
                  className: 'bg-white/60',
                }}
              />
            </div>
          </div>
        )}
      </DialogContent>

      <DialogActions className="bg-gray-50/50 px-6 py-4 border-t border-gray-100">
        <Button onClick={handleClose} variant="outlined" className="border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400">
          {t('components.prompts.deletePromptDialog.cancel')}
        </Button>
        <Button
          onClick={handleConfirmDelete}
          variant="contained"
          className="bg-gradient-to-r from-red-600 to-pink-600 text-white hover:from-red-700 hover:to-pink-700 shadow-sm"
          disabled={!prompt || deleteInputValue !== prompt.prompt_key || deleteLoading}
          startIcon={deleteLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
        >
          {deleteLoading ? t('components.prompts.deletePromptDialog.deleting') : t('components.prompts.deletePromptDialog.confirmDelete')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
