import React, { useState } from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Box, Typography, IconButton } from '@mui/material'
import { X, FileText, Hash, Archive } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface PromptBasicInfoDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: (basicInfo: { key: string; name: string; description: string; tags: string[]; isPublic: boolean }) => void | Promise<void>
  title?: string // 可选的对话框标题
  defaultValues?: {
    key: string
    name: string
    description: string
    tags: string[]
    isPublic: boolean
  } // 可选的默认值
  keyEditable?: boolean // 是否允许编辑key字段，默认为false
  buttonText?: {
    loading: string // 加载中的文本
    normal: string // 正常状态的文本
  } // 按钮文本配置
}

export const PromptBasicInfoDialog: React.FC<PromptBasicInfoDialogProps> = ({
  open,
  onClose,
  onConfirm,
  title,
  defaultValues,
  keyEditable = false,
  buttonText,
}) => {
  const { t } = useTranslation()
  const defaultTitle = title || t('components.prompts.promptBasicInfoDialog.defaultTitle')
  const defaultButtonText = buttonText || {
    loading: t('components.prompts.promptBasicInfoDialog.defaultButtonLoading'),
    normal: t('components.prompts.promptBasicInfoDialog.defaultButtonNormal'),
  }
  const [key, setKey] = useState('')
  const [keyError, setKeyError] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)

  // 当默认值改变时更新表单状态
  React.useEffect(() => {
    if (defaultValues) {
      setKey(defaultValues.key || '')
      setName(defaultValues.name || '')
      setDescription(defaultValues.description || '')
      setKeyError(validateKey(defaultValues.key || ''))
    }
  }, [defaultValues])

  // 验证提示词key的函数（只在创建时使用）
  const validateKey = (value: string): string => {
    if (!value) {
      return t('components.prompts.promptBasicInfoDialog.keyRequired')
    }
    if (!/^[a-zA-Z]/.test(value)) {
      return t('components.prompts.promptBasicInfoDialog.keyMustStartWithLetter')
    }
    if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(value)) {
      return t('components.prompts.promptBasicInfoDialog.keyInvalidChars')
    }
    return ''
  }

  const handleKeyChange = (value: string) => {
    if (keyEditable) {
      setKey(value)
      setKeyError(validateKey(value))
    }
  }

  const handleConfirm = async () => {
    // 如果key可编辑，则需要验证key
    const keyValidationError = keyEditable ? validateKey(key) : ''
    if (!keyValidationError && name.trim()) {
      setLoading(true)
      try {
        await onConfirm({
          key: key.trim(),
          name: name.trim(),
          description: description.trim(),
          tags: [],
          isPublic: false,
        })
        // 只有在操作成功时才重置表单
        setKey('')
        setKeyError('')
        setName('')
        setDescription('')
      } catch (error) {
        console.error('确认操作失败:', error)
        // 操作失败时不重置表单，保持用户输入的内容
      } finally {
        setLoading(false)
      }
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          bgcolor: 'background.paper',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(to right, #eff6ff, #f0f9ff)',
          borderBottom: '1px solid #dbeafe',
          p: 3,
          '.MuiTypography-root': {
            color: 'text.primary',
          },
        }}
        className="dark:!bg-gradient-to-r dark:from-gray-800 dark:to-gray-700 dark:border-gray-600"
      >
        <Box display="flex" alignItems="center" gap={2}>
          <Box
            sx={{
              width: 40,
              height: 40,
              background: 'linear-gradient(to right, #3b82f6, #60a5fa)',
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            className="dark:from-blue-700 dark:to-blue-900"
          >
            <FileText size={24} color="white" />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600 }} className="text-gray-900 dark:text-gray-100">
              {defaultTitle}
            </Typography>
            <Typography variant="caption" sx={{ color: '#6b7280' }} className="dark:text-gray-400">
              {t('components.prompts.promptBasicInfoDialog.subtitle')}
            </Typography>
          </Box>
        </Box>
        <IconButton onClick={onClose} size="small" className="text-gray-600 dark:text-gray-400">
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }} className="dark:bg-gray-800">
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 1 }}>
          {/* 提示词 key */}
          <TextField
            fullWidth
            label={t('components.prompts.promptBasicInfoDialog.keyLabel')}
            placeholder={t('components.prompts.promptBasicInfoDialog.keyPlaceholder')}
            value={key}
            onChange={e => handleKeyChange(e.target.value)}
            required
            autoFocus
            error={!!keyError}
            helperText={
              keyEditable ? keyError || t('components.prompts.promptBasicInfoDialog.keyHelper') : t('components.prompts.promptBasicInfoDialog.keyNotEditable')
            }
            disabled={!keyEditable}
            inputProps={{ maxLength: 100 }}
            sx={{
              '& .MuiOutlinedInput-root': {
                '&:hover fieldset': {
                  borderColor: '#dbeafe',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#3b82f6',
                },
                '&.Mui-disabled': {
                  '& fieldset': {
                    borderColor: '#e5e7eb',
                  },
                  '&:hover fieldset': {
                    borderColor: '#e5e7eb',
                  },
                  backgroundColor: '#f9fafb',
                },
                position: 'relative',
                '& input': {
                  paddingRight: '60px',
                },
              },
              '& .MuiFormHelperText-root': {
                color: '#6b7280',
              },
            }}
            InputProps={{
              endAdornment: (
                <Box sx={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                  <Typography
                    variant="caption"
                    sx={{ color: (key || '').length >= 100 ? '#ef4444' : '#6b7280', fontSize: '0.75rem' }}
                    className="dark:text-gray-400"
                  >
                    {(key || '').length}/100
                  </Typography>
                </Box>
              ),
            }}
          />

          {/* 名称 */}
          <TextField
            fullWidth
            label={t('components.prompts.promptBasicInfoDialog.nameLabel')}
            placeholder={t('components.prompts.promptBasicInfoDialog.namePlaceholder')}
            value={name}
            onChange={e => setName(e.target.value)}
            required
            inputProps={{ maxLength: 100 }}
            sx={{
              '& .MuiOutlinedInput-root': {
                '&:hover fieldset': {
                  borderColor: '#dbeafe',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#3b82f6',
                },
                position: 'relative',
                '& input': {
                  paddingRight: '60px',
                },
              },
              '& .MuiInputLabel-root': {
                color: '#6b7280',
              },
            }}
            InputProps={{
              endAdornment: (
                <Box sx={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                  <Typography
                    variant="caption"
                    sx={{ color: (name || '').length >= 100 ? '#ef4444' : '#6b7280', fontSize: '0.75rem' }}
                    className="dark:text-gray-400"
                  >
                    {(name || '').length}/100
                  </Typography>
                </Box>
              ),
            }}
          />

          {/* 描述 */}
          <TextField
            fullWidth
            label={t('components.prompts.promptBasicInfoDialog.descriptionLabel')}
            placeholder={t('components.prompts.promptBasicInfoDialog.descriptionPlaceholder')}
            value={description}
            onChange={e => setDescription(e.target.value)}
            multiline
            rows={3}
            inputProps={{ maxLength: 500 }}
            sx={{
              '& .MuiOutlinedInput-root': {
                '&:hover fieldset': {
                  borderColor: '#dbeafe',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#3b82f6',
                },
                position: 'relative',
                '& textarea': {
                  paddingRight: '60px',
                  paddingBottom: '24px',
                },
              },
              '& .MuiInputLabel-root': {
                color: '#6b7280',
              },
            }}
            InputProps={{
              endAdornment: (
                <Box sx={{ position: 'absolute', right: 8, bottom: 0, pointerEvents: 'none' }}>
                  <Typography
                    variant="caption"
                    sx={{ color: (description || '').length >= 500 ? '#ef4444' : '#6b7280', fontSize: '0.75rem' }}
                    className="dark:text-gray-400"
                  >
                    {(description || '').length}/500
                  </Typography>
                </Box>
              ),
            }}
          />
        </Box>
      </DialogContent>

      <DialogActions
        sx={{
          px: 3,
          py: 2,
          backgroundColor: 'rgba(255,255,255,0.9)',
          borderTop: '1px solid #dbeafe',
          '.MuiButton-root': {
            color: 'text.primary',
          },
        }}
        className="dark:bg-gray-800 dark:border-gray-600"
      >
        <Button
          onClick={onClose}
          variant="outlined"
          sx={{
            borderColor: '#e5e7eb',
            color: '#6b7280',
            '&:hover': {
              borderColor: '#d1d5db',
              backgroundColor: 'rgba(107, 114, 128, 0.04)',
            },
          }}
          className="dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          {t('components.prompts.promptBasicInfoDialog.cancel')}
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          disabled={!!keyError || !key.trim() || !name.trim() || loading}
          sx={{
            background: 'linear-gradient(to right, #3b82f6, #60a5fa)',
            '&:hover': {
              background: 'linear-gradient(to right, #2563eb, #3b82f6)',
            },
            '&:disabled': {
              background: '#e5e7eb',
            },
          }}
          className="dark:from-blue-700 dark:to-blue-900 dark:hover:from-blue-800 dark:hover:to-blue-900"
        >
          {loading ? defaultButtonText.loading : defaultButtonText.normal}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
