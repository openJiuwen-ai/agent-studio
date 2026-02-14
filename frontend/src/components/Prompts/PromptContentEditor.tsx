import React, { useLayoutEffect, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import { Button, FormControl, Select, MenuItem, IconButton, Tooltip, TextField, Typography } from '@mui/material'
import { Plus, Settings, Code, GripVertical, Zap, Wrench, Copy, Trash2 } from 'lucide-react'
import FormattedPromptEditor from './AdvancedCodeMirrorEditor'
import { PromptMessage } from '@/types/promptType'

export interface PromptContentEditorProps {
  // 模板引擎相关
  templateEngine: 'normal' | 'jinja2'
  onTemplateEngineChange: (engine: 'normal' | 'jinja2') => void
  readOnly?: boolean

  // 消息相关
  promptMessages: PromptMessage[]
  onPromptMessagesChange: (messages: PromptMessage[]) => void
  messageInputValues: Record<string, string>
  onMessageInputValuesChange: (values: Record<string, string>) => void

  // 验证错误相关
  externalValidationErrors?: Record<string, string | { type?: string; loc?: any; msg?: string; input?: any; message?: string }>
  onValidationErrorsChange?: (errors: Record<string, string>) => void

  // 优化来源配置
  optimizationSource?: { type: 'main' | 'base' | 'control'; groupId?: number }

  // 当前活跃的消息ID（用于插入和选中文本反馈优化）
  currentMessageId?: string

  // 文本选择和优化相关
  selectedText?: string
  selectionPosition?: { x: number; y: number }
  isSelecting?: boolean
  showCursorOptimizeButton?: boolean
  cursorOptimizePosition?: { x: number; y: number }
  onTextSelection?: (text: string, position: { x: number; y: number }, messageId?: string) => void
  onCursorPositionChange?: (messageId: string) => (position: { x: number; y: number }, cursorPos: number) => void
  onOptimizeDialogOpen?: (optimizationSourceOverride?: any) => void
  onOptimizeInput?: (input: string) => void
  onSelectedTextChange?: (text: string) => void
  onSelectionIndicesChange?: (indices: any) => void
  onOptimizationSourceChange?: (source: any) => void
  onCurrentOptimizationTypeChange?: (type: string) => void
  onSetClickedOptimizationType?: (type: 'general' | 'select' | 'insert' | null) => void
  onOptimizingTargetChange?: (target: any) => void
  onIgnoreTextSelectionChange?: (ignore: boolean) => void
  onIgnoreTextSelectionRefChange?: (ignore: boolean) => void

  // 拖拽相关
  draggedMessageId?: string | null
  onDragStart?: (e: React.DragEvent, messageId: string) => void
  onDragEnd?: () => void
  onDragOver?: (e: React.DragEvent) => void
  onDrop?: (e: React.DragEvent, index: number) => void

  // 中文输入状态
  compositionState: Record<string, boolean>
  onCompositionStateChange: (state: Record<string, boolean>) => void

  // 其他回调
  onPromptChange?: (field: string, value: any) => void
  onCopyToClipboard?: (content: string) => Promise<void>
  onValidatePlaceholderContent?: (content: string, currentValue: string) => { isValid: boolean; hasError: boolean; originalValue: string }
  onDebouncedUpdatePlaceholderContent?: (messageId: string, index: number, content: string) => void
  onOptimizePrompt?: (target: any) => void
}

const PromptContentEditor: React.FC<PromptContentEditorProps> = ({
  templateEngine,
  onTemplateEngineChange,
  readOnly = false,
  promptMessages,
  onPromptMessagesChange,
  messageInputValues,
  onMessageInputValuesChange,
  externalValidationErrors,
  onValidationErrorsChange,
  optimizationSource = { type: 'main' },
  currentMessageId,
  selectedText,
  selectionPosition,
  isSelecting,
  showCursorOptimizeButton,
  cursorOptimizePosition,
  onTextSelection,
  onCursorPositionChange,
  onOptimizeDialogOpen,
  onOptimizeInput,
  onSelectedTextChange,
  onSelectionIndicesChange,
  onOptimizationSourceChange,
  onCurrentOptimizationTypeChange,
  onSetClickedOptimizationType,
  onOptimizingTargetChange,
  onIgnoreTextSelectionChange,
  onIgnoreTextSelectionRefChange,
  draggedMessageId,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  compositionState,
  onCompositionStateChange,
  onPromptChange,
  onCopyToClipboard,
  onValidatePlaceholderContent,
  onDebouncedUpdatePlaceholderContent,
  onOptimizePrompt,
}) => {
  const { t } = useTranslation()
  const isReadOnly = !!readOnly
  const cursorButtonRef = useRef<HTMLDivElement | null>(null)
  const selectionButtonRef = useRef<HTMLDivElement | null>(null)

  // 添加防抖定时器引用，用于非 placeholder 消息
  const normalMessageUpdateTimers = useRef<Record<string, NodeJS.Timeout>>({})

  // 为 placeholder 消息使用本地状态，避免每次输入都触发父组件重新渲染
  const [localPlaceholderValues, setLocalPlaceholderValues] = React.useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {}
    promptMessages.forEach(msg => {
      if (msg.role === 'placeholder') {
        initial[msg.id] = messageInputValues[msg.id] || msg.content
      }
    })
    return initial
  })

  // 同步外部 messageInputValues 到本地状态（当外部值变化时，比如从其他地方更新）
  React.useEffect(() => {
    const updated: Record<string, string> = {}
    let hasChanges = false
    promptMessages.forEach(msg => {
      if (msg.role === 'placeholder') {
        const externalValue = messageInputValues[msg.id] || msg.content
        const localValue = localPlaceholderValues[msg.id]
        if (externalValue !== localValue) {
          updated[msg.id] = externalValue
          hasChanges = true
        } else {
          updated[msg.id] = localValue
        }
      }
    })
    if (hasChanges) {
      setLocalPlaceholderValues(updated)
    }
  }, [messageInputValues, promptMessages])

  // 添加防抖定时器引用，用于 placeholder 消息的更新（每个消息独立的防抖定时器）
  const placeholderUpdateTimers = useRef<Record<string, NodeJS.Timeout>>({})
  
  // 添加防抖定时器引用，用于 messageInputValues 的更新（减少父组件渲染）
  const messageInputValuesUpdateTimer = useRef<NodeJS.Timeout | null>(null)
  // 用于保存防抖期间最新的 messageInputValues 值
  const pendingMessageInputValuesRef = useRef<Record<string, string>>(messageInputValues)

  // 添加防抖定时器引用，用于光标位置变化的更新（减少父组件渲染）
  const cursorPositionUpdateTimer = useRef<NodeJS.Timeout | null>(null)

  // 响应式消息列表最大高度
  const [messageListMaxHeight, setMessageListMaxHeight] = React.useState('calc(100vh - 350px)')

  // 同步 messageInputValues 到 pendingMessageInputValuesRef（当外部值变化时）
  React.useEffect(() => {
    pendingMessageInputValuesRef.current = messageInputValues
  }, [messageInputValues])

  // 响应式调整消息列表最大高度
  useEffect(() => {
    const updateMessageListMaxHeight = () => {
      if (window.innerWidth < 640) {
        // 小屏幕
        setMessageListMaxHeight('calc(100vh - 280px)')
      } else if (window.innerWidth < 2000) {
        // 中屏幕
        setMessageListMaxHeight('calc(100vh - 290px)')
      } else {
        // 大屏幕
        setMessageListMaxHeight('calc(100vh - 390px)')
      }
    }

    updateMessageListMaxHeight()
    window.addEventListener('resize', updateMessageListMaxHeight)
    return () => window.removeEventListener('resize', updateMessageListMaxHeight)
  }, [])

  // 添加验证错误状态
  const [internalValidationErrors, setInternalValidationErrors] = React.useState<Record<string, string>>({})

  // 合并内部和外部的验证错误
  const validationErrors = React.useMemo(() => {
    return { ...internalValidationErrors, ...externalValidationErrors }
  }, [internalValidationErrors, externalValidationErrors])

  // 初始化时检查placeholder消息是否为空
  React.useEffect(() => {
    const newErrors: Record<string, string> = {}
    promptMessages.forEach(message => {
      if (message.role === 'placeholder') {
        const value = messageInputValues[message.id] || message.content
        if (!value.trim()) {
          newErrors[message.id] = t('components.prompts.promptContentEditor.placeholderCannotBeEmpty')
        }
      }
    })
    if (Object.keys(newErrors).length > 0) {
      setInternalValidationErrors(prev => ({ ...prev, ...newErrors }))
    }
  }, []) // 只在组件挂载时执行一次

  // 清理定时器
  useEffect(() => {
    return () => {
      // 清理所有防抖定时器
      Object.values(normalMessageUpdateTimers.current).forEach(timer => {
        clearTimeout(timer)
      })
      normalMessageUpdateTimers.current = {}
      // 清理 messageInputValues 更新定时器
      if (messageInputValuesUpdateTimer.current) {
        clearTimeout(messageInputValuesUpdateTimer.current)
        messageInputValuesUpdateTimer.current = null
      }
      // 清理光标位置更新定时器
      if (cursorPositionUpdateTimer.current) {
        clearTimeout(cursorPositionUpdateTimer.current)
        cursorPositionUpdateTimer.current = null
      }
    }
  }, [])

  // 使用 useLayoutEffect 确保按钮位置正确
  useLayoutEffect(() => {
    if (!isReadOnly && showCursorOptimizeButton && cursorOptimizePosition && cursorButtonRef.current) {
      // 重置可能影响位置的样式
      cursorButtonRef.current.style.setProperty('margin-left', '0px', 'important')
      cursorButtonRef.current.style.setProperty('margin-right', '0px', 'important')
    }
  }, [isReadOnly, showCursorOptimizeButton, cursorOptimizePosition, selectedText, selectionPosition])

  // 使用 useLayoutEffect 在 DOM 更新前调整选中反馈按钮位置
  useLayoutEffect(() => {
    if (!isReadOnly && selectedText && selectionPosition && selectionButtonRef.current) {
      const buttonRef = selectionButtonRef.current

      // 使用 selectionPosition 中已经计算好的第一行起始位置
      const firstLineStartX = selectionPosition.x

      // 获取当前容器位置
      const containerRect = buttonRef.getBoundingClientRect()
      const containerLeft = containerRect.left
      const horizontalDiff = containerLeft - firstLineStartX

      // 无论差距大小，都进行调整，确保按钮对齐到第一行起始位置
      if (Math.abs(horizontalDiff) > 1) {
        const computedStyle = window.getComputedStyle(buttonRef)
        const currentMarginLeft = parseFloat(computedStyle.marginLeft) || 0
        const targetMarginLeft = currentMarginLeft - horizontalDiff

        buttonRef.style.setProperty('margin-left', `${targetMarginLeft}px`, 'important')
      }
    }
  }, [isReadOnly, selectedText, selectionPosition])

  // 额外的 useEffect 作为备用方案，确保选中反馈按钮位置调整能执行
  useEffect(() => {
    if (!isReadOnly && selectedText && selectionPosition && selectionButtonRef.current) {
      const adjustSelectionButtonPosition = () => {
        const buttonRef = selectionButtonRef.current
        if (!buttonRef) return

        // 使用 selectionPosition 中已经计算好的第一行起始位置
        const firstLineStartX = selectionPosition.x

        const containerRect = buttonRef.getBoundingClientRect()
        const containerLeft = containerRect.left
        const horizontalDiff = containerLeft - firstLineStartX

        // 无论差距大小，都进行调整，确保按钮对齐到第一行起始位置
        if (Math.abs(horizontalDiff) > 1) {
          const computedStyle = window.getComputedStyle(buttonRef)
          const currentMarginLeft = parseFloat(computedStyle.marginLeft) || 0
          const targetMarginLeft = currentMarginLeft - horizontalDiff

          buttonRef.style.setProperty('margin-left', `${targetMarginLeft}px`, 'important')
        }
      }

      // 延迟调整，确保 DOM 已完全渲染
      setTimeout(() => {
        adjustSelectionButtonPosition()
      }, 0)

      // 使用 requestAnimationFrame 确保在下一帧再调整一次
      requestAnimationFrame(() => {
        adjustSelectionButtonPosition()
      })
    }
  }, [isReadOnly, selectedText, selectionPosition])

  const getRoleStyles = (role: string) => {
    switch (role) {
      case 'system':
        return {
          bg: 'from-blue-500 to-cyan-500',
          text: 'text-blue-700',
          border: 'border-blue-200',
          lightBg: 'bg-blue-50',
        }
      case 'user':
        return {
          bg: 'from-purple-500 to-indigo-500',
          text: 'text-purple-700',
          border: 'border-purple-200',
          lightBg: 'bg-purple-50',
        }
      case 'placeholder':
        return {
          bg: 'from-green-500 to-emerald-500',
          text: 'text-green-700',
          border: 'border-green-200',
          lightBg: 'bg-green-50',
        }
      case 'assistant':
        return {
          bg: 'from-orange-500 to-red-500',
          text: 'text-orange-700',
          border: 'border-orange-200',
          lightBg: 'bg-orange-50',
        }
      default:
        return {
          bg: 'from-gray-500 to-gray-600',
          text: 'text-gray-700',
          border: 'border-gray-200',
          lightBg: 'bg-gray-50',
        }
    }
  }

  const handleAddMessage = () => {
    if (isReadOnly) return
    const newMessage: PromptMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: '',
    }
    const newMessages = [...promptMessages, newMessage]
    onPromptMessagesChange(newMessages)
    const newValues = {
      ...messageInputValues,
      [newMessage.id]: '',
    }
    pendingMessageInputValuesRef.current = newValues
    // 立即更新父组件（添加消息操作不需要防抖）
    onMessageInputValuesChange(newValues)

    // 更新prompt.content为所有消息的组合
    const combinedContent = newMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
    onPromptChange?.('content', combinedContent)

    // 添加消息后自动滚动到最下面
    setTimeout(() => {
      const messagesContainer = document.querySelector('.messages-container')
      if (messagesContainer) {
        messagesContainer.scrollTo({
          top: messagesContainer.scrollHeight,
          behavior: 'smooth',
        })
      }
    }, 100)
  }

  const handleMessageRoleChange = (index: number, newRole: PromptMessage['role']) => {
    if (isReadOnly) return

    // 确保创建新的数组和对象引用，触发 React 重新渲染
    const newMessages = promptMessages.map((msg, i) => (i === index ? { ...msg, role: newRole } : { ...msg }))

    onPromptMessagesChange(newMessages)
    // 更新prompt.content为所有消息的组合
    const combinedContent = newMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
    onPromptChange?.('content', combinedContent)
  }

  const handleMessageDelete = (messageId: string) => {
    if (isReadOnly) return
    const newMessages = promptMessages.filter(m => m.id !== messageId)
    onPromptMessagesChange(newMessages)
    // 更新prompt.content
    const combinedContent = newMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
    onPromptChange?.('content', combinedContent)
    // 清理对应的输入值
    const newInputValues = { ...messageInputValues }
    delete newInputValues[messageId]
    pendingMessageInputValuesRef.current = newInputValues
    // 立即更新父组件（删除操作不需要防抖）
    onMessageInputValuesChange(newInputValues)
  }

  const handleMessageContentChange = (messageId: string, index: number, newValue: string, message: PromptMessage) => {
    if (isReadOnly) return

    // 对 placeholder 类型的消息，使用本地状态和防抖更新
    if (message.role === 'placeholder') {
      // 立即更新本地状态（不会触发父组件重新渲染）
      setLocalPlaceholderValues(prev => ({
        ...prev,
        [messageId]: newValue,
      }))

      // 验证逻辑
      if (!newValue.trim()) {
        const emptyErrorMessage = t('components.prompts.promptContentEditor.placeholderCannotBeEmpty')
        setInternalValidationErrors(prev => {
          if (prev[messageId] === emptyErrorMessage) return prev
          return { ...prev, [messageId]: emptyErrorMessage }
        })
      } else {
        const currentValue = localPlaceholderValues[messageId] || message.content
        const validationResult = onValidatePlaceholderContent?.(newValue, currentValue)
        if (validationResult) {
          if (validationResult.isValid) {
            setInternalValidationErrors(prev => {
              if (!prev[messageId]) return prev
              const newErrors = { ...prev }
              delete newErrors[messageId]
              return newErrors
            })
          } else if (validationResult.hasError) {
            const errorMessage = t('components.prompts.promptContentEditor.placeholderValidationError')
            setInternalValidationErrors(prev => {
              if (prev[messageId] === errorMessage) return prev
              return { ...prev, [messageId]: errorMessage }
            })
          }
        }
      }

      // 清除之前的防抖定时器
      if (placeholderUpdateTimers.current[messageId]) {
        clearTimeout(placeholderUpdateTimers.current[messageId])
      }

      // 设置防抖定时器，延迟更新父组件和触发参数生成
      placeholderUpdateTimers.current[messageId] = setTimeout(() => {
        // 更新父组件的 messageInputValues（防抖后）
        const updatedValues = {
          ...messageInputValues,
          [messageId]: newValue,
        }
        onMessageInputValuesChange(updatedValues)

        // 触发参数生成（防抖后）
        if (!compositionState[messageId]) {
          onDebouncedUpdatePlaceholderContent?.(messageId, index, newValue)
        }

        // 清理定时器引用
        delete placeholderUpdateTimers.current[messageId]
      }, 500) // 500ms 防抖，平衡响应性和性能

      return
    }

    // 非 placeholder 消息的处理逻辑（保持原有逻辑）
    const currentValue = messageInputValues[messageId] || message.content
    if (currentValue !== newValue) {
      pendingMessageInputValuesRef.current = {
        ...pendingMessageInputValuesRef.current,
        [messageId]: newValue,
      }

      if (messageInputValuesUpdateTimer.current) {
        clearTimeout(messageInputValuesUpdateTimer.current)
      }

      messageInputValuesUpdateTimer.current = setTimeout(() => {
        onMessageInputValuesChange({
          ...pendingMessageInputValuesRef.current,
        })
        messageInputValuesUpdateTimer.current = null
      }, 1000)
    }

    // 如果不在输入中文，使用防抖更新
    if (!compositionState[messageId]) {
      if (normalMessageUpdateTimers.current[messageId]) {
        clearTimeout(normalMessageUpdateTimers.current[messageId])
      }

      normalMessageUpdateTimers.current[messageId] = setTimeout(() => {
        const newMessages = [...promptMessages]
        newMessages[index].content = newValue
        onPromptMessagesChange(newMessages)
        const combinedContent = newMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
        onPromptChange?.('content', combinedContent)
        delete normalMessageUpdateTimers.current[messageId]
      }, 300)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(0.375rem, 1.5vh, 1rem)' }}>
      <div className="flex flex-col">
        <div 
          className="flex items-center justify-between"
          style={{
            marginBottom: 'clamp(0.1875rem, 0.75vh, 0.5rem)',
          }}
        >
          <label 
            className="block font-medium text-gray-700"
            style={{
              fontSize: 'clamp(0.625rem, 1.2vw, 0.875rem)',
            }}
          >
            {t('components.prompts.promptContentEditor.promptContent')}
          </label>
          <div 
            className="flex items-center"
            style={{
              gap: 'clamp(0.1875rem, 0.75vw, 0.5rem)',
            }}
          >
            <span 
              className="font-medium text-gray-700"
              style={{
                fontSize: 'clamp(0.625rem, 1.2vw, 0.875rem)',
              }}
            >
              {t('components.prompts.promptContentEditor.promptTemplate')}:
            </span>
            <FormControl 
              size="small" 
              disabled={isReadOnly}
              sx={{
                minWidth: 'clamp(1.75rem, 10vw, 6rem)',
              }}
            >
              <Select
                value={templateEngine}
                onChange={e => onTemplateEngineChange(e.target.value as 'normal' | 'jinja2')}
                disabled={isReadOnly}
                renderValue={value => (value === 'normal' ? 'Normal' : 'Jinja2')}
                className="bg-white/80"
                sx={{
                  height: 'clamp(1.375rem, 3.5vh, 2rem)',
                  fontSize: 'clamp(0.6875rem, 1.3vw, 0.9375rem)',
                  '& .MuiSelect-select': {
                    padding: 'clamp(0.125rem, 0.5vh, 0.375rem) clamp(0.4375rem, 1.25vw, 0.875rem)',
                    fontSize: 'clamp(0.6875rem, 1.3vw, 0.9375rem)',
                  },
                }}
                MenuProps={{
                  PaperProps: {
                    sx: {
                      '& .MuiMenuItem-root': {
                        fontSize: 'clamp(0.5625rem, 1.1vw, 0.75rem)',
                        padding: 'clamp(0.125rem, 0.5vh, 0.375rem) clamp(0.5625rem, 1.5vw, 1rem)',
                        minHeight: 'auto',
                      },
                    },
                  },
                }}
              >
                <MenuItem value="normal">
                  <div 
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.1875rem, 0.75vw, 0.5rem)',
                    }}
                  >
                    <Code 
                      className="text-blue-600"
                      style={{
                        width: 'clamp(0.5625rem, 1.5vw, 1rem)',
                        height: 'clamp(0.5625rem, 1.5vw, 1rem)',
                      }}
                    />
                    <div>
                      <div 
                        className="font-medium"
                        style={{ 
                          fontSize: 'clamp(0.5625rem, 1.1vw, 0.75rem)',
                        }}
                      >
                        {t('components.prompts.promptContentEditor.normalTemplateEngine')}
                      </div>
                      <div 
                        className="text-xs text-gray-500"
                        style={{ 
                          fontSize: 'clamp(0.4375rem, 0.9vw, 0.625rem)',
                        }}
                      >
                        {t('components.prompts.promptContentEditor.normalTemplateDescription')}
                      </div>
                    </div>
                  </div>
                </MenuItem>
                <MenuItem value="jinja2">
                  <div 
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.1875rem, 0.75vw, 0.5rem)',
                    }}
                  >
                    <Settings 
                      className="text-green-600"
                      style={{
                        width: 'clamp(0.5625rem, 1.5vw, 1rem)',
                        height: 'clamp(0.5625rem, 1.5vw, 1rem)',
                      }}
                    />
                    <div>
                      <div 
                        className="font-medium"
                        style={{ 
                          fontSize: 'clamp(0.5625rem, 1.1vw, 0.75rem)',
                        }}
                      >
                        {t('components.prompts.promptContentEditor.jinja2TemplateEngine')}
                      </div>
                      <div 
                        className="text-xs text-gray-500"
                        style={{ 
                          fontSize: 'clamp(0.4375rem, 0.9vw, 0.625rem)',
                        }}
                      >
                        {t('components.prompts.promptContentEditor.jinja2TemplateDescription')}
                      </div>
                    </div>
                  </div>
                </MenuItem>
              </Select>
            </FormControl>
          </div>
        </div>

        {/* 悬浮的优化按钮 - 选中反馈优化 */}
        {!isReadOnly && selectedText && selectionPosition && !isSelecting && (
          <div
            ref={el => {
              if (el) {
                selectionButtonRef.current = el
              }
            }}
            className="fixed z-[1600]"
            style={{
              left: `${selectionPosition.x}px`,
              // 上移约 3 行（66px），使按钮出现在选中文本上方 1 行（position 可能受容器/滚动影响偏下）
              top: `${selectionPosition.y - 80}px`,
              transform: 'translate(0, -100%)', // 按钮底部对齐该 top
              marginLeft: '0', // 初始值，会被动态调整覆盖
              marginRight: '0',
              padding: '0',
            }}
            onMouseEnter={() => {
              // 当鼠标悬停时，再次尝试调整位置（作为备用方案）
              if (selectionButtonRef.current && selectionPosition) {
                // 使用 selectionPosition 中已经计算好的第一行起始位置
                const firstLineStartX = selectionPosition.x
                const containerRect = selectionButtonRef.current.getBoundingClientRect()
                const horizontalDiff = containerRect.left - firstLineStartX

                if (Math.abs(horizontalDiff) > 1) {
                  const computedStyle = window.getComputedStyle(selectionButtonRef.current)
                  const currentMarginLeft = parseFloat(computedStyle.marginLeft) || 0
                  const targetMarginLeft = currentMarginLeft - horizontalDiff
                  selectionButtonRef.current.style.setProperty('margin-left', `${targetMarginLeft}px`, 'important')
                }
              }
            }}
          >
            <Tooltip title={t('components.prompts.promptContentEditor.selectedTextOptimize')} placement="top" arrow>
              <IconButton
                size="small"
                data-testid="selection-optimize-button"
                disabled={isReadOnly}
                onMouseDown={e => {
                  e.preventDefault()
                  e.stopPropagation() // 阻止事件冒泡，防止全局点击事件清除选中文本
                  if (isReadOnly) {
                    return
                  }
                  // 设置按钮点击标记（最高优先级）
                  onSetClickedOptimizationType?.('select')
                  // 参考插入反馈优化按钮的逻辑：先设置优化源和打开对话框，最后设置优化类型
                  const selection = window.getSelection()
                  const currentSelectedText = selection ? selection.toString().trim() : ''
                  if (currentSelectedText) {
                    // 先设置选中文本，确保在打开对话框时能检测到
                    onSelectedTextChange?.(currentSelectedText)
                  }
                  // 先设置优化类型为 'select'，确保对话框打开时能正确识别
                  onCurrentOptimizationTypeChange?.('select')
                  // 不传递 optimizationSourceOverride，让 handleOptimizeDialogOpen 使用全局的 optimizationSource state
                  // 全局 state 已经在文本选中处理器中被正确设置了
                  onOptimizeDialogOpen?.(undefined)
                  onOptimizeInput?.('')
                }}
                className="bg-gradient-to-r from-orange-500 to-red-500 text-white hover:from-orange-600 hover:to-red-600 shadow-sm"
                sx={{
                  background: 'linear-gradient(to right, #f97316, #ef4444)',
                  color: 'white',
                  width: 'clamp(1.5rem, 3vw, 1rem)',
                  height: 'clamp(1.5rem, 3vw, 1rem)',
                  '&:hover': {
                    background: 'linear-gradient(to right, #ea580c, #dc2626)',
                  },
                }}
              >
                <Zap 
                  style={{
                    width: 'clamp(0.75rem, 1.5vw, 0.8rem)',
                    height: 'clamp(0.75rem, 1.5vw, 0.8rem)',
                  }}
                />
              </IconButton>
            </Tooltip>
          </div>
        )}

        {/* 插入反馈优化按钮 */}
        {!isReadOnly &&
          showCursorOptimizeButton &&
          cursorOptimizePosition &&
          !selectedText &&
          createPortal(
            <div
              ref={cursorButtonRef}
              className="fixed z-[1600]"
              style={{
                left: `${cursorOptimizePosition.x}px`,
                top: `${cursorOptimizePosition.y}px`,
                transform: 'translate(-50%, 0)',
              }}
            >
              <Tooltip title={t('components.prompts.promptContentEditor.insertFeedbackOptimize')} placement="top" arrow>
                <IconButton
                  size="small"
                  disabled={isReadOnly}
                  onClick={() => {
                    if (isReadOnly) return
                    // 设置按钮点击标记（最高优先级）
                    onSetClickedOptimizationType?.('insert')
                    // 注意：在对比模式下，所有组共享同一个按钮状态，所以可能有多个按钮重叠显示
                    // 我们需要确保使用正确的 optimizationSource
                    // 不要使用 props 中的 optimizationSource，因为它可能属于错误的组
                    // 而是传递 undefined，让 handleOptimizeDialogOpen 使用全局的 optimizationSource state
                    // 不传递 optimizationSourceOverride，让 handleOptimizeDialogOpen 使用全局的 optimizationSource state
                    onOptimizeDialogOpen?.(undefined)
                    onOptimizeInput?.('')
                    onSelectedTextChange?.('')
                    onSelectionIndicesChange?.(null)
                    onCurrentOptimizationTypeChange?.('insert')
                  }}
                  className="bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600 shadow-sm"
                  sx={{
                    background: 'linear-gradient(to right, #10b981, #059669)',
                    color: 'white',
                    width: 'clamp(1.5rem, 3vw, 1rem)',
                    height: 'clamp(1.5rem, 3vw, 1rem)',
                    '&:hover': {
                      background: 'linear-gradient(to right, #059669, #047857)',
                    },
                  }}
                >
                  <Zap 
                    style={{
                      width: 'clamp(0.75rem, 1.5vw, 0.8rem)',
                      height: 'clamp(0.75rem, 1.5vw, 0.8rem)',
                    }}
                  />
                </IconButton>
              </Tooltip>
            </div>,
            document.body,
          )}

        {/* 消息列表 */}
        <div 
          className="overflow-y-auto overflow-x-hidden relative message-list-container scrollbar-hide messages-container"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'clamp(0.25rem, 1vh, 0.75rem)',
            minHeight: 'auto',
            maxHeight: messageListMaxHeight,
          }}
        >
          {promptMessages.map((message, index) => {
            const roleStyles = getRoleStyles(message.role)

            return (
              <div
                key={message.id}
                className={`bg-white/80 border ${roleStyles.border} rounded-lg shadow-sm hover:shadow-sm transition-shadow ${draggedMessageId === message.id ? 'opacity-50' : ''}`}
                draggable={false}
                onDragOver={isReadOnly ? undefined : onDragOver}
                onDrop={isReadOnly ? undefined : e => onDrop?.(e, index)}
                style={{
                  padding: 'clamp(0.1875rem, 0.75vh, 0.5rem)',
                  width: '100%',
                  boxSizing: 'border-box',
                }}
              >
                <div 
                  className="flex items-center justify-between"
                  style={{
                    marginBottom: 'clamp(0.1875rem, 0.75vh, 0.5rem)',
                  }}
                >
                  <div 
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.25rem, 1vw, 0.75rem)',
                    }}
                  >
                    <div
                      className={`${isReadOnly ? 'cursor-not-allowed text-gray-300' : 'cursor-move text-gray-400 hover:text-gray-600'} drag-handle`}
                      draggable={!isReadOnly}
                      onDragStart={isReadOnly ? undefined : e => onDragStart?.(e, message.id)}
                      onDragEnd={isReadOnly ? undefined : onDragEnd}
                    >
                      <GripVertical 
                        style={{
                          width: 'clamp(0.75rem, 2vw, 1.25rem)',
                          height: 'clamp(0.75rem, 2vw, 1.25rem)',
                        }}
                      />
                    </div>
                    <FormControl 
                      size="small" 
                      disabled={isReadOnly}
                      sx={{
                        minWidth: 'clamp(3.5rem, 9vw, 6rem)',
                      }}
                    >
                      <Select
                        value={message.role}
                        onChange={e => handleMessageRoleChange(index, e.target.value as PromptMessage['role'])}
                        disabled={isReadOnly}
                        renderValue={value => {
                          const roleLabels: Record<string, string> = {
                            system: 'System',
                            user: 'User',
                            placeholder: 'Placeholder',
                            assistant: 'Assistant',
                          }
                          return roleLabels[value] || value
                        }}
                        className={`${roleStyles.lightBg} ${roleStyles.text} font-medium`}
                        sx={{
                          '& .MuiOutlinedInput-notchedOutline': {
                            borderColor: roleStyles.border.replace('border-', ''),
                          },
                          '&:hover .MuiOutlinedInput-notchedOutline': {
                            borderColor: roleStyles.text.replace('text-', ''),
                          },
                          height: 'clamp(1.125rem, 2.75vh, 1.5625rem)',
                          fontSize: 'clamp(0.6875rem, 1.3vw, 0.9375rem)',
                          '& .MuiSelect-select': {
                            padding: 'clamp(0.09375rem, 0.375vh, 0.25rem) clamp(0.25rem, 0.75vw, 0.5rem)',
                            fontSize: 'clamp(0.6875rem, 1.3vw, 0.9375rem)',
                          },
                        }}
                        MenuProps={{
                          PaperProps: {
                            sx: {
                              maxHeight: 140,
                              '& .MuiMenuItem-root': {
                                fontSize: 'clamp(0.5625rem, 1.1vw, 0.75rem)',
                                padding: 'clamp(0.125rem, 0.5vh, 0.375rem) clamp(0.5625rem, 1.5vw, 1rem)',
                                minHeight: 'auto',
                              },
                            },
                          },
                        }}
                      >
                        <MenuItem value="system">
                          <span style={{ fontSize: 'clamp(0.5625rem, 1.1vw, 0.75rem)' }}>System</span>
                        </MenuItem>
                        <MenuItem value="user">
                          <span style={{ fontSize: 'clamp(0.5625rem, 1.1vw, 0.75rem)' }}>User</span>
                        </MenuItem>
                        <MenuItem value="assistant">
                          <span style={{ fontSize: 'clamp(0.5625rem, 1.1vw, 0.75rem)' }}>Assistant</span>
                        </MenuItem>
                        <MenuItem value="placeholder">
                          <span style={{ fontSize: 'clamp(0.5625rem, 1.1vw, 0.75rem)' }}>Placeholder</span>
                        </MenuItem>
                      </Select>
                    </FormControl>
                  </div>

                  <div 
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.0625rem, 0.25vw, 0.25rem)',
                    }}
                  >
                    {message.role === 'system' && (
                      <>
                        <IconButton
                          size="small"
                          disabled={isReadOnly}
                          onClick={() => {
                            if (isReadOnly) {
                              return
                            }
                            // 创建包含当前消息ID的优化目标
                            // 确保使用当前消息的ID，不继承optimizationSource中可能存在的旧messageId
                            const targetWithMessageId = {
                              type: optimizationSource?.type || 'main',
                              groupId: optimizationSource?.groupId,
                              messageId: message.id, // 明确使用当前消息的ID
                            }
                            onOptimizingTargetChange?.(targetWithMessageId)
                            onOptimizePrompt?.(targetWithMessageId)
                          }}
                          className="text-orange-500 hover:bg-orange-50 transition-colors"
                          title={t('components.prompts.promptContentEditor.quickOptimize')}
                        >
                          <Zap className="w-4 h-4 text-blue-500 hover:bg-blue-50 transition-colors" />
                        </IconButton>

                        {/* 全文反馈优化按钮 */}
                        <IconButton
                          size="small"
                          disabled={isReadOnly}
                          onClick={e => {
                            if (isReadOnly) {
                              return
                            }
                            // 阻止事件冒泡，防止触发其他事件
                            e.stopPropagation()
                            e.preventDefault()

                            // 设置按钮点击标记（最高优先级，必须在最前面）
                            onSetClickedOptimizationType?.('general')

                            // 立即设置忽略文本选中事件标记，防止后续干扰
                            onIgnoreTextSelectionRefChange?.(true) // 立即生效的ref标记
                            onIgnoreTextSelectionChange?.(true) // React状态标记

                            // 清除选中文本和选择索引，确保是全文优化
                            onSelectedTextChange?.('')
                            onSelectionIndicesChange?.(null)
                            // 清除浏览器中的选中文本，防止被误判为选中反馈优化
                            const selection = window.getSelection()
                            if (selection) {
                              selection.removeAllRanges()
                            }

                            // 先强制设置为全文反馈优化（必须在打开对话框之前）
                            onCurrentOptimizationTypeChange?.('general')

                            // 传递包含当前消息ID的优化源信息
                            // 注意：在对比模式下，props 中的 optimizationSource 可能属于错误的组
                            // 所以我们只使用它的 type 和 groupId（这些是固定的），然后添加 messageId
                            const newOptimizationSource = { ...optimizationSource, messageId: message.id }
                            onOptimizationSourceChange?.(newOptimizationSource)

                            // 最后打开对话框和清空输入
                            onOptimizeInput?.('')
                            // 传递新的优化源信息作为参数，解决状态更新延迟问题
                            onOptimizeDialogOpen?.(newOptimizationSource)

                            // 延迟后恢复文本选中事件监听（延长恢复时间，确保对话框打开后光标位置变化事件也被忽略）
                            setTimeout(() => {
                              onIgnoreTextSelectionRefChange?.(false) // 恢复ref标记
                              onIgnoreTextSelectionChange?.(false) // 恢复React状态标记
                            }, 1000) // 延长到1000ms，确保对话框完全打开后光标位置变化事件也被忽略
                          }}
                          className="text-purple-500 hover:bg-purple-50 transition-colors"
                          title={t('components.prompts.promptContentEditor.fullTextFeedbackOptimize')}
                        >
                          <Wrench className="w-4 h-4" />
                        </IconButton>
                      </>
                    )}

                    <IconButton
                      size="small"
                      disabled={isReadOnly}
                      onClick={async () => {
                        if (isReadOnly) {
                          return
                        }
                        const content = messageInputValues[message.id] || message.content
                        try {
                          await onCopyToClipboard?.(content)
                        } catch (error) {
                          console.error(t('components.prompts.promptContentEditor.copyFailed'), error)
                        }
                      }}
                      className="text-blue-500 hover:bg-blue-50 transition-colors"
                      title={t('components.prompts.promptContentEditor.copyContent')}
                    >
                      <Copy className="w-4 h-4" />
                    </IconButton>

                    <IconButton
                      size="small"
                      disabled={isReadOnly}
                      onClick={() => {
                        if (isReadOnly) {
                          return
                        }
                        handleMessageDelete(message.id)
                      }}
                      className="text-red-500 hover:bg-red-50 transition-colors"
                      title={t('components.prompts.promptContentEditor.deleteMessage')}
                    >
                      <Trash2 className="w-4 h-4" />
                    </IconButton>
                  </div>
                </div>

                {message.role === 'placeholder' ? (
                  <TextField
                    fullWidth
                    value={localPlaceholderValues[message.id] ?? message.content}
                    onChange={e => handleMessageContentChange(message.id, index, e.target.value, message)}
                    placeholder={t('components.prompts.promptContentEditor.placeholderPlaceholder')}
                    disabled={isReadOnly}
                    error={!!validationErrors[message.id]}
                    size="small"
                    inputProps={{ maxLength: 50 }}
                    helperText={
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                        {(() => {
                          const error = validationErrors[message.id]
                          const errorText = error ? (
                            typeof error === 'string' ? error :
                            typeof error === 'object' && error !== null ? 
                              (error as { msg?: string; message?: string }).msg || (error as { msg?: string; message?: string }).message || '验证错误' :
                            '验证错误'
                          ) : null
                          return errorText ? <span>{errorText}</span> : <span />
                        })()}
                        <Typography
                          variant="caption"
                          sx={{
                            color: (localPlaceholderValues[message.id] ?? message.content).length >= 50 ? '#ef4444' : '#6b7280',
                            fontSize: '0.75rem',
                            marginLeft: 'auto',
                          }}
                        >
                          {(localPlaceholderValues[message.id] ?? message.content).length}/50
                        </Typography>
                      </div>
                    }
                    FormHelperTextProps={{
                      component: 'div',
                      sx: {
                        margin: 0,
                        marginTop: '4px',
                      },
                    }}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        backgroundColor: 'rgba(255, 255, 255, 0.6)',
                        position: 'relative',
                        fontSize: 'clamp(0.3rem, 0.75vw, 0.875rem)',
                        '& input': {
                          paddingRight: '8px',
                          fontSize: 'clamp(0.3rem, 0.75vw, 0.875rem)',
                        },
                        '& input::placeholder': {
                          fontSize: 'clamp(0.3rem, 0.75vw, 0.875rem)',
                        },
                        '& fieldset': {
                          borderColor: validationErrors[message.id] ? '#ef4444' : roleStyles.border.replace('border-', ''),
                        },
                        '&:hover fieldset': {
                          borderColor: validationErrors[message.id] ? '#ef4444' : roleStyles.text.replace('text-', ''),
                        },
                        '&.Mui-focused fieldset': {
                          borderColor: validationErrors[message.id] ? '#ef4444' : roleStyles.text.replace('text-', ''),
                        },
                      },
                    }}
                    InputProps={{
                      endAdornment: undefined,
                    }}
                  />
                ) : (
                  <div style={{ width: '100%', overflow: 'hidden' }}>
                    <FormattedPromptEditor
                      fullWidth
                      minRows={message.role === 'system' ? 20 : 1}
                      maxRows={message.role === 'system' ? 25 : undefined}
                      value={messageInputValues[message.id] || message.content}
                      messageId={message.id}
                      disabled={isReadOnly}
                      templateEngine={templateEngine}
                      optimizationSourceType={optimizationSource.type}
                      onTextSelection={
                        message.role === 'system'
                          ? (selectedText: string, position: { x: number; y: number }, messageId?: string) => {
                              // 设置正确的优化来源
                              onOptimizationSourceChange?.(optimizationSource)
                              // 调用原始的文本选择处理，传递消息ID
                              onTextSelection?.(selectedText, position, messageId || message.id)
                            }
                          : undefined
                      }
                      onCursorPositionChange={
                        message.role === 'system'
                          ? (position: { x: number; y: number }, cursorPos: number) => {
                              // 如果正在输入中文，跳过光标位置更新，避免频繁渲染
                              if (compositionState[message.id]) {
                                return
                              }

                              // 使用防抖更新光标位置（50ms 防抖）
                              if (cursorPositionUpdateTimer.current) {
                                clearTimeout(cursorPositionUpdateTimer.current)
                              }

                              cursorPositionUpdateTimer.current = setTimeout(() => {
                                // 设置正确的优化来源
                                onOptimizationSourceChange?.(optimizationSource)
                                // 调用原始的光标位置处理，传递完整的参数
                                onCursorPositionChange?.(message.id)?.(position, cursorPos)
                                cursorPositionUpdateTimer.current = null
                              }, 50)
                            }
                          : undefined
                      }
                      onChange={newValue => handleMessageContentChange(message.id, index, newValue, message)}
                      placeholder={t('components.prompts.promptContentEditor.messagePlaceholder', { role: message.role })}
                      className={`${roleStyles.lightBg}`}
                      InputProps={{
                        className: 'bg-white/60',
                        sx: {
                          '& .MuiOutlinedInput-notchedOutline': {
                            borderColor: roleStyles.border.replace('border-', ''),
                          },
                          '&:hover .MuiOutlinedInput-notchedOutline': {
                            borderColor: roleStyles.text.replace('text-', ''),
                          },
                          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                            borderColor: roleStyles.text.replace('text-', ''),
                          },
                          '& textarea': {
                            resize: 'none',
                            overflow: 'auto !important',
                            maxHeight: message.role === 'system' ? '600px' : 'none',
                          },
                        },
                      }}
                    />
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* 添加消息按钮 */}
        <Button
          variant="outlined"
          startIcon={<Plus className="w-4 h-4" />}
          onClick={() => {
            if (isReadOnly) {
              return
            }
            handleAddMessage()
          }}
          className="mt-3 border-blue-300 text-blue-600 hover:bg-blue-50"
          disabled={isReadOnly}
        >
          {t('components.prompts.promptContentEditor.addMessage')}
        </Button>
      </div>
    </div>
  )
}

export default React.memo(PromptContentEditor)
