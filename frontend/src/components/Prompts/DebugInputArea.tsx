import React, { useState, useEffect, useRef, useCallback } from 'react'
import { TextField, Button, IconButton, Tooltip } from '@mui/material'
import { Layers, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { handleInputEnterKey } from '@/utils/prompts/utils'

const DEBOUNCE_MS = 150

export interface DebugInputAreaProps {
  inputMessage: string
  onInputChange: (value: string) => void
  /** 发送时可将当前输入值传入，避免依赖父组件 state 导致卡顿 */
  onSend: (value?: string) => void
  onClear: () => void
  onMultiRunClick: () => void
  isProcessing: boolean
  isReadOnlyMode: boolean
}

const DebugInputArea: React.FC<DebugInputAreaProps> = ({ inputMessage, onInputChange, onSend, onClear, onMultiRunClick, isProcessing, isReadOnlyMode }) => {
  const { t } = useTranslation()
  const [inputHeight, setInputHeight] = useState('100px') // 输入框高度
  const [localValue, setLocalValue] = useState(inputMessage)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 仅当父组件清空（如点击清空）时同步到本地，避免覆盖用户正在输入的内容
  useEffect(() => {
    if (inputMessage === '') {
      setLocalValue('')
    }
  }, [inputMessage])

  const flushDebounce = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
  }, [])

  const debouncedOnInputChange = useCallback(
    (value: string) => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = setTimeout(() => {
        debounceTimerRef.current = null
        onInputChange(value)
      }, DEBOUNCE_MS)
    },
    [onInputChange],
  )

  // 输入变化：只更新本地 state，防抖同步到父组件，减少父组件重渲染
  const handleChange = useCallback(
    (value: string) => {
      if (isReadOnlyMode) return
      setLocalValue(value)
      debouncedOnInputChange(value)
    },
    [isReadOnlyMode, debouncedOnInputChange],
  )

  const handleSendClick = useCallback(() => {
    if (isReadOnlyMode) return
    flushDebounce()
    onInputChange(localValue)
    onSend(localValue)
  }, [isReadOnlyMode, localValue, onInputChange, onSend, flushDebounce])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (isReadOnlyMode) return
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        flushDebounce()
        onInputChange(localValue)
        onSend(localValue)
        return
      }
      handleInputEnterKey(isReadOnlyMode, (v: string) => handleChange(v), () => handleSendClick())(e)
    },
    [isReadOnlyMode, localValue, onInputChange, onSend, handleChange, handleSendClick, flushDebounce],
  )

  // 响应式计算输入框高度
  useEffect(() => {
    const updateInputHeight = () => {
      if (window.innerWidth < 640) {
        // 小屏幕：手机等移动设备
        setInputHeight('70px')
      } else if (window.innerWidth < 2000) {
        // 中等屏幕：平板、14寸笔记本等
        setInputHeight('65px')
      } else {
        // 大屏幕：15寸以上笔记本、台式显示器
        setInputHeight('100px')
      }
    }

    updateInputHeight()
    window.addEventListener('resize', updateInputHeight)
    return () => window.removeEventListener('resize', updateInputHeight)
  }, [])

  return (
    <>
      {/* 功能按钮区域 */}
      <div
        className="border-t border-blue-200 bg-white/60 flex-shrink-0 relative z-10"
        style={{
          padding: 'clamp(0.1rem, 0.2vw, 0.25rem) clamp(0.2rem, 0.4vw, 0.4rem)',
        }}
      >
        <div className="flex items-center justify-between">
          <div
            className="flex items-center"
            style={{
              gap: 'clamp(0.25rem, 0.25rem + 1vw, 0.4rem)',
            }}
          >
            <Button
              size="small"
              variant="outlined"
              startIcon={<Layers style={{ width: 'clamp(9px, 10px + 0.3vw, 12px)', height: 'clamp(9px, 10px + 0.3vw, 12px)' }} />}
              onClick={() => {
                if (isReadOnlyMode) {
                  return
                }
                onMultiRunClick()
              }}
              disabled={isReadOnlyMode}
              className="text-blue-600 border-blue-600 hover:bg-blue-50"
              sx={{
                fontSize: 'clamp(0.6rem, 0.65rem + 0.15vw, 0.75rem)',
                padding: 'clamp(0.1rem, 0.15rem + 0.15vw, 0.25rem) clamp(0.25rem, 0.3rem + 0.3vw, 0.5rem)',
              }}
            >
              {t('prompts.promptEdit.promptDebug.multiRun')}
            </Button>
          </div>
          <div
            className="flex items-center"
            style={{
              gap: 'clamp(0.2rem, 0.25rem + 0.5vw, 0.375rem)',
            }}
          >
            <Tooltip title={t('prompts.promptEdit.promptDebug.clearMainChat')}>
              <IconButton
                size="small"
                onClick={() => {
                  if (isReadOnlyMode) {
                    return
                  }
                  onClear()
                }}
                disabled={isReadOnlyMode}
                sx={{
                  color: '#3b82f6',
                  padding: 'clamp(0.2rem, 0.3rem + 0.3vw, 0.375rem)',
                  '&:hover': {
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                  },
                }}
              >
                <Trash2 style={{ width: 'clamp(10px, 12px + 0.5vw, 14px)', height: 'clamp(10px, 12px + 0.5vw, 14px)' }} />
              </IconButton>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* 底部输入框 */}
      <div
        className="border-t border-blue-200 bg-white/80 flex-shrink-0 relative z-10"
        style={{
          padding: 'clamp(0.1rem, 0.2vw, 0.25rem) clamp(0.2rem, 0.4vw, 0.4rem)',
        }}
      >
        <div
          className="flex flex-col"
          style={{
            gap: 'clamp(0.25rem, 0.3vw, 0.375rem)',
          }}
        >
          <TextField
            fullWidth
            multiline
            placeholder={t('prompts.promptEdit.promptDebug.inputPlaceholder')}
            value={localValue}
            onChange={e => handleChange(e.target.value)}
            onKeyDown={handleKeyDown as React.KeyboardEventHandler<HTMLDivElement>}
            disabled={isProcessing || isReadOnlyMode}
            sx={{
              backgroundColor: 'white',
              '& .MuiOutlinedInput-root': {
                height: inputHeight, // 根据屏幕尺寸动态设置
                borderRadius: 'clamp(0.25rem, 0.2rem + 0.2vw, 0.375rem)',
                alignItems: 'flex-start',
                overflow: 'hidden',
                display: 'flex',
                '& fieldset': { borderColor: '#dbeafe' },
                '&:hover fieldset': { borderColor: '#bfdbfe' },
                '&.Mui-focused fieldset': { borderColor: '#3b82f6' },
              },
              '& .MuiInputBase-input': {
                padding: 'clamp(0.15rem, 0.2rem + 0.1vw, 0.3rem)',
                fontSize: 'clamp(0.65rem, 0.7rem + 0.2vw, 0.8rem)',
                lineHeight: 'clamp(1.2, 1.25, 1.3)',
                overflow: 'auto !important',
                height: '100% !important',
                maxHeight: '100% !important',
                boxSizing: 'border-box',
                wordBreak: 'break-word',
                '&::-webkit-scrollbar': { width: 'clamp(2px, 3px + 0.3vw, 5px)' },
                '&::-webkit-scrollbar-track': { background: '#f3f4f6', borderRadius: '3px' },
                '&::-webkit-scrollbar-thumb': {
                  background: '#d1d5db',
                  borderRadius: '3px',
                  '&:hover': { background: '#9ca3af' },
                },
              },
            }}
          />
          <div className="flex justify-end">
            <Button
              size="small"
              variant="contained"
              onClick={handleSendClick}
              disabled={isProcessing || isReadOnlyMode}
              startIcon={
                <svg
                  style={{
                    width: 'clamp(9px, 10px + 0.5vw, 12px)',
                    height: 'clamp(9px, 10px + 0.5vw, 12px)',
                  }}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              }
              sx={{
                borderRadius: 'clamp(0.25rem, 0.2rem + 0.2vw, 0.375rem)',
                px: 'clamp(0.4rem, 0.6rem + 0.6vw, 0.8rem)',
                py: 'clamp(0.15rem, 0.2rem + 0.2vw, 0.3rem)',
                background: 'linear-gradient(to right, #3b82f6, #6366f1)',
                fontSize: 'clamp(0.65rem, 0.7rem + 0.2vw, 0.8rem)',
                '&:hover': {
                  background: 'linear-gradient(to right, #2563eb, #4f46e5)',
                },
              }}
            >
              {t('prompts.promptEdit.promptDebug.send')}
            </Button>
          </div>
        </div>
      </div>
    </>
  )
}

export default DebugInputArea
