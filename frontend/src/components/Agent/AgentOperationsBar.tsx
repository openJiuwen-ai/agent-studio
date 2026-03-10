import { Button, TextField, Tooltip } from '@mui/material'
import { Play, Square, BrushCleaning } from 'lucide-react'
import { useRef } from 'react'
import { useScopedTranslation } from '@/i18n'

interface AgentOperationsBarProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onCancel?: () => void
  onClearChat?: () => void
  disabled?: boolean
  placeholder?: string
  inputDisabled?: boolean
  isProcessing?: boolean
  onInputFocusChange?: (focused: boolean) => void
}

const AgentOperationsBar = ({
  value,
  onChange,
  onSend,
  onCancel,
  onClearChat,
  disabled = false,
  placeholder,
  inputDisabled = false,
  isProcessing = false,
  onInputFocusChange,
}: AgentOperationsBarProps) => {
  const { t } = useScopedTranslation('agents.agentEditor.previewDebug.operationsBar')
  const inputRef = useRef<HTMLInputElement | null>(null)
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="flex items-center space-x-3">
        <Tooltip title={t('tooltips.clearChat')} placement="top">
          <Button
            variant="text"
            onClick={onClearChat ? onClearChat : undefined}
            size="small"
            sx={{
              borderRadius: '12px',
              textTransform: 'none',
              color: '#6B7280',
              padding: '4px 4px',
              minWidth: 'unset',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              '&:hover': {
                backgroundColor: '#F3F4F6',
                color: '#374151',
              },
              '.dark &:hover': {
                backgroundColor: '#374151',
                color: '#E5E7EB',
              },
            }}
          >
            <BrushCleaning className="w-4 h-4" />
          </Button>
        </Tooltip>

        <TextField
          fullWidth
          value={value}
          onChange={e => {
            // 如果输入被禁用，阻止任何更改
            if (inputDisabled) return
            onChange(e.target.value)
          }}
          placeholder={placeholder || t('placeholders.inputMessage')}
          onFocus={() => onInputFocusChange?.(true)}
          onBlur={() => onInputFocusChange?.(false)}
          onKeyPress={e => {
            if (disabled || inputDisabled) return
            if (e.key === 'Enter') onSend()
          }}
          size="small"
          className="flex-1"
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: '12px',
              backgroundColor: inputDisabled ? '#F5F5F5' : 'white',
              '&.Mui-disabled': {
                backgroundColor: '#F5F5F5',
              },
              '&:hover fieldset': {
                borderColor: '#3B82F6',
              },
              // 当禁用时添加额外的视觉提示
              '&.Mui-disabled fieldset': {
                borderColor: '#D1D5DB',
              },
            },
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: '#E5E7EB',
            },
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: '#3B82F6',
            },
            '& .MuiInputBase-input': {
              color: '#1F2937',
            },
            '& .MuiInputBase-input::placeholder': {
              color: '#9CA3AF',
            },
            '& .Mui-disabled .MuiInputBase-input': {
              color: '#9CA3AF',
              WebkitTextFillColor: '#9CA3AF',
            },
            // Dark mode overrides
            '.dark & .MuiOutlinedInput-root': {
              backgroundColor: inputDisabled ? '#374151' : '#1F2937',
              '&.Mui-disabled': {
                backgroundColor: '#374151',
              },
            },
            '.dark & .MuiOutlinedInput-notchedOutline': {
              borderColor: '#4B5563',
            },
            '.dark &:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: '#5B8CFF',
            },
            '.dark & .MuiInputBase-input': {
              color: '#E5E7EB',
            },
            '.dark & .MuiInputBase-input::placeholder': {
              color: '#6B7280',
            },
            '.dark & .Mui-disabled .MuiInputBase-input': {
              color: '#6B7280',
              WebkitTextFillColor: '#6B7280',
            },
            '.dark & .Mui-disabled fieldset': {
              borderColor: '#4B5563',
            },
          }}
          disabled={inputDisabled}
          InputProps={{
            style: {
              backgroundColor: inputDisabled ? '#F5F5F5' : 'transparent',
              cursor: inputDisabled ? 'not-allowed' : 'text',
            },
            readOnly: inputDisabled, // 使用 readOnly 作为额外的保护
          }}
          inputProps={{ 'data-agent-chat-input': 'true' }}
          inputRef={inputRef}
        />
        {!isProcessing && (
          <Button
            variant="contained"
            startIcon={<Play className="w-4 h-4" />}
            onClick={() => {
              onSend()
              if (!disabled && !inputDisabled) {
                inputRef.current?.focus()
              }
            }}
            disabled={disabled}
            className="btn-primary shadow-sm px-4 rounded-xl"
            size="small"
            sx={{
              borderRadius: '12px',
              textTransform: 'none',
              fontWeight: 600,
            }}
          >
            {t('buttons.send')}
          </Button>
        )}
        {isProcessing && (
          <Button
            variant="contained"
            color="error"
            startIcon={<Square className="w-4 h-4" />}
            onClick={() => {
              onCancel?.()
              if (!inputDisabled) {
                inputRef.current?.focus()
              }
            }}
            disabled={!onCancel}
            className="bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 shadow-sm px-4 rounded-xl"
            size="small"
            sx={{
              borderRadius: '12px',
              textTransform: 'none',
              fontWeight: 600,
            }}
          >
            {t('buttons.cancel')}
          </Button>
        )}
      </div>
    </div>
  )
}

export default AgentOperationsBar
