import React, { useRef, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import MarkdownPreview from '@uiw/react-markdown-preview'
import { Button, TextField, Tooltip } from '@mui/material'
import { TestTube, Check, X, Sparkles, RotateCw, Activity, FileText, Code, Copy, Trash2, Edit3, User, Bot, ChevronRight, ChevronDown } from 'lucide-react'

// 工具调用信息接口
export interface ToolCall {
  index: number
  id: string
  function: {
    arguments: string
    name: string
  }
  type: string
}

// 工具调用显示信息接口
export interface ToolCallDisplay {
  name: string
  input: string
  output: string
  id?: string
  index?: number
}

// 消息类型定义
export interface ChatMessage {
  type: 'user' | 'ai' | 'system'
  content: string
  timestamp: string
  userInput?: string
  input_tokens?: string
  output_tokens?: string
  cost_ms?: string
  reasoningContent?: string
  toolCalls?: ToolCallDisplay[]
}

// 简化的组件Props类型定义
export interface ChatMessageAreaProps {
  messages: ChatMessage[]
  onRetryMessage?: (index: number) => void
  onOptimizeReply?: (index: number) => void
  onCopyMessage?: (content: string) => void
  onEditMessage?: (index: number) => void
  onDeleteMessage?: (index: number) => void
  onViewTrace?: (index: number) => void // 新增：查看调试追踪回调
  isProcessing?: boolean
  onStopStreaming?: () => void
  isStreamingStopped?: boolean // 是否已停止流式响应
  className?: string
  // 消息控制状态
  messageFormats: { [key: number]: 'txt' | 'markdown' }
  onToggleMessageFormat: (index: number) => void
  completedMessages: Set<number>
  expandedReasoningMessages: Set<number>
  onToggleReasoningExpanded: (index: number) => void
  expandedToolCallMessages: Set<number>
  onToggleToolCallExpanded: (index: number) => void
  // 编辑状态
  editingMessageIndex?: number | null
  editingContent?: string
  onStartEdit?: (index: number, content: string) => void
  onSaveEdit?: (index: number, content: string) => void
  onCancelEdit?: () => void
  onEditContentChange?: (content: string) => void
  // 容器引用，用于自动滚动
  containerRef?: React.RefObject<HTMLDivElement>
  // 空状态显示
  emptyStateText?: string
  emptyStateSubtext?: string
  readOnly?: boolean
}

const ChatMessageArea: React.FC<ChatMessageAreaProps> = ({
  messages,
  onRetryMessage,
  onOptimizeReply,
  onCopyMessage,
  onEditMessage,
  onDeleteMessage,
  onViewTrace,
  isProcessing = false,
  onStopStreaming,
  isStreamingStopped = false,
  className = '',
  messageFormats,
  onToggleMessageFormat,
  expandedReasoningMessages,
  onToggleReasoningExpanded,
  expandedToolCallMessages,
  onToggleToolCallExpanded,
  editingMessageIndex,
  editingContent,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onEditContentChange,
  containerRef,
  emptyStateText,
  emptyStateSubtext,
  readOnly = false,
}) => {
  const { t } = useTranslation()
  const defaultEmptyStateText = emptyStateText || t('components.prompts.chatMessageArea.emptyStateText')
  const defaultEmptyStateSubtext = emptyStateSubtext || t('components.prompts.chatMessageArea.emptyStateSubtext')
  const internalRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = containerRef || internalRef
  const isReadOnly = !!readOnly

  // 删除确认状态
  const [deleteConfirmIndex, setDeleteConfirmIndex] = React.useState<number | null>(null)
  const [deleteButtonPosition, setDeleteButtonPosition] = React.useState<{ x: number; y: number } | null>(null)
  const deleteButtonRef = useRef<HTMLButtonElement | null>(null)

  // 点击外部关闭删除确认框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (deleteConfirmIndex !== null) {
        const target = event.target as HTMLElement
        if (!target.closest('.delete-confirm-popup') && !target.closest('.delete-button')) {
          setDeleteConfirmIndex(null)
          setDeleteButtonPosition(null)
        }
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [deleteConfirmIndex])

  // 更新删除按钮位置的函数
  const updateDeleteButtonPosition = useCallback(() => {
    if (deleteButtonRef.current && deleteConfirmIndex !== null) {
      const rect = deleteButtonRef.current.getBoundingClientRect()
      setDeleteButtonPosition({
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height + 8,
      })
    }
  }, [deleteConfirmIndex])

  // 监听滚动事件，更新删除按钮位置
  useEffect(() => {
    if (deleteConfirmIndex !== null && chatContainerRef.current) {
      const scrollContainer = chatContainerRef.current

      // 初始更新位置
      updateDeleteButtonPosition()

      // 监听滚动事件
      const handleScroll = () => {
        updateDeleteButtonPosition()
      }

      scrollContainer.addEventListener('scroll', handleScroll)
      window.addEventListener('resize', handleScroll) // 也监听窗口大小变化

      return () => {
        scrollContainer.removeEventListener('scroll', handleScroll)
        window.removeEventListener('resize', handleScroll)
      }
    }
  }, [deleteConfirmIndex, updateDeleteButtonPosition])

  // 只读模式下，关闭删除确认弹窗
  useEffect(() => {
    if (isReadOnly && deleteConfirmIndex !== null) {
      setDeleteConfirmIndex(null)
      setDeleteButtonPosition(null)
    }
  }, [isReadOnly, deleteConfirmIndex])

  // 只读模式下，退出正在进行的编辑状态
  useEffect(() => {
    if (isReadOnly && editingMessageIndex !== null) {
      onCancelEdit?.()
    }
  }, [isReadOnly, editingMessageIndex, onCancelEdit])

  // 滚动到聊天容器底部
  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }

  // 监听消息变化，在新增消息和内容更新时自动滚动到底部
  useEffect(() => {
    if (messages.length > 0) {
      // 延迟滚动，确保DOM已更新
      setTimeout(() => {
        scrollToBottom()
      }, 50)
    }
  }, [messages]) // 监听整个消息数组变化，包括内容更新

  // 计算最后一条AI消息的索引
  const lastAIMessageIndex = React.useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].type === 'ai') {
        return i
      }
    }
    return -1
  }, [messages])

  return (
    <div className={`relative h-full ${className}`}>
      {/* 消息滚动区域 */}
      <div
        ref={chatContainerRef}
        className="overflow-y-auto scrollbar-hide"
        style={{
          height: '100%',
          maxHeight: '100%',
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 'clamp(0.75rem, 2vh, 0.875rem)',
          paddingBottom: isProcessing && !isStreamingStopped && onStopStreaming ? 'clamp(3rem, 8vh, 3.5rem)' : '0px', // 为停止按钮预留空间
        }}
      >
        {messages.length === 0 ? (
          <div className="text-center text-gray-500" style={{ padding: 'clamp(1.5rem, 3vh, 2rem) 0' }}>
            <TestTube 
              className="mx-auto text-gray-300" 
              style={{ 
                width: 'clamp(2rem, 5vw, 2.5rem)', 
                height: 'clamp(2rem, 5vw, 2.5rem)',
                marginBottom: 'clamp(0.5rem, 1.5vh, 0.625rem)'
              }} 
            />
            <p style={{ fontSize: 'clamp(0.875rem, 2vw, 0.9375rem)' }}>{defaultEmptyStateText}</p>
            <p style={{ fontSize: 'clamp(0.75rem, 1.75vw, 0.8125rem)' }}>{defaultEmptyStateSubtext}</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} items-start`} style={{ gap: 'clamp(0.375rem, 1vw, 0.625rem)' }}>
              {/* 头像 - 在左侧显示（AI消息）*/}
              {message.type === 'ai' && (
                <div className="flex-shrink-0" style={{ marginTop: 'clamp(0.75rem, 2vh, 1.25rem)' }}>
                  <div 
                    className="bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center"
                    style={{ 
                      width: 'clamp(1.5rem, 4vw, 1.75rem)', 
                      height: 'clamp(1.5rem, 4vw, 1.75rem)' 
                    }}
                  >
                    <Bot style={{ width: 'clamp(0.75rem, 2vw, 0.875rem)', height: 'clamp(0.75rem, 2vw, 0.875rem)' }} className="text-white" />
                  </div>
                </div>
              )}

              <div className={`max-w-[70%] relative ${message.type === 'user' ? 'order-1' : ''}`}>
                {/* 时间戳显示在对话框上方 */}
                <div 
                  className={`text-gray-500 ${message.type === 'user' ? 'text-right' : ''}`}
                  style={{ 
                    fontSize: 'clamp(0.625rem, 1.5vw, 0.6875rem)',
                    marginBottom: 'clamp(0.125rem, 0.5vh, 0.1875rem)'
                  }}
                >
                  {message.timestamp}
                </div>

                {/* 消息内容气泡 */}
                <div
                  className={`
                ${message.type === 'user' ? 'bg-blue-500 text-white' : 'bg-white border border-gray-200'} 
                rounded-lg relative
              `}
                  style={{ padding: 'clamp(0.5rem, 1.5vw, 0.625rem)' }}
                >
                  {/* AI思考过程显示区域 - 放在最前面 */}
                  {message.type === 'ai' && message.reasoningContent && (
                    <div 
                      className="border-b border-gray-200"
                      style={{ 
                        marginBottom: 'clamp(0.5rem, 1.5vw, 0.625rem)',
                        paddingBottom: 'clamp(0.5rem, 1.5vw, 0.625rem)'
                      }}
                    >
                      <div
                        role="button"
                        tabIndex={isReadOnly ? -1 : 0}
                        aria-disabled={isReadOnly}
                        className={`flex items-center ${isReadOnly ? 'cursor-not-allowed opacity-60 pointer-events-none' : 'cursor-pointer'}`}
                        style={{ marginBottom: 'clamp(0.25rem, 1vw, 0.375rem)' }}
                        onClick={() => {
                          if (isReadOnly) {
                            return
                          }
                          onToggleReasoningExpanded(index)
                        }}
                      >
                        <span 
                          className="font-medium text-gray-700"
                          style={{ fontSize: 'clamp(0.75rem, 1.75vw, 0.8125rem)' }}
                        >
                          {t('components.prompts.chatMessageArea.aiThinking')}
                        </span>
                        <div className="text-gray-500 hover:text-gray-700 transition-colors" style={{ marginLeft: 'clamp(0.125rem, 0.5vw, 0.1875rem)' }}>
                          {expandedReasoningMessages.has(index) ? (
                            <ChevronDown style={{ width: 'clamp(0.75rem, 2vw, 0.875rem)', height: 'clamp(0.75rem, 2vw, 0.875rem)' }} />
                          ) : (
                            <ChevronRight style={{ width: 'clamp(0.75rem, 2vw, 0.875rem)', height: 'clamp(0.75rem, 2vw, 0.875rem)' }} />
                          )}
                        </div>
                      </div>
                      {expandedReasoningMessages.has(index) && (
                        <div 
                          className="text-gray-600 whitespace-pre-wrap bg-gray-50 rounded border"
                          style={{ 
                            fontSize: 'clamp(0.625rem, 1.5vw, 0.6875rem)',
                            padding: 'clamp(0.375rem, 1vw, 0.4375rem)'
                          }}
                        >
                          {/* AI思考过程直接显示，与消息内容保持一致 */}
                          <span>{message.reasoningContent || ''}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 工具调用信息显示区域 - 放在第二位 */}
                  {message.type === 'ai' && message.toolCalls && message.toolCalls.length > 0 && (
                    <div 
                      className="border-b border-gray-200"
                      style={{ 
                        marginBottom: 'clamp(0.5rem, 1.5vw, 0.625rem)',
                        paddingBottom: 'clamp(0.5rem, 1.5vw, 0.625rem)'
                      }}
                    >
                      <div
                        role="button"
                        tabIndex={isReadOnly ? -1 : 0}
                        aria-disabled={isReadOnly}
                        className={`flex items-center ${isReadOnly ? 'cursor-not-allowed opacity-60 pointer-events-none' : 'cursor-pointer'}`}
                        style={{ marginBottom: 'clamp(0.25rem, 1vw, 0.375rem)' }}
                        onClick={() => {
                          if (isReadOnly) {
                            return
                          }
                          onToggleToolCallExpanded(index)
                        }}
                      >
                        <span 
                          className="font-medium text-gray-700"
                          style={{ fontSize: 'clamp(0.75rem, 1.75vw, 0.8125rem)' }}
                        >
                          {t('components.prompts.chatMessageArea.toolCall')}
                        </span>
                        <div className="text-gray-500 hover:text-gray-700 transition-colors" style={{ marginLeft: 'clamp(0.125rem, 0.5vw, 0.1875rem)' }}>
                          {expandedToolCallMessages.has(index) ? (
                            <ChevronDown style={{ width: 'clamp(0.75rem, 2vw, 0.875rem)', height: 'clamp(0.75rem, 2vw, 0.875rem)' }} />
                          ) : (
                            <ChevronRight style={{ width: 'clamp(0.75rem, 2vw, 0.875rem)', height: 'clamp(0.75rem, 2vw, 0.875rem)' }} />
                          )}
                        </div>
                      </div>
                      {expandedToolCallMessages.has(index) && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(0.375rem, 1vw, 0.4375rem)' }}>
                          {message.toolCalls.map((toolCall, toolIndex) => (
                            <div 
                              key={toolIndex} 
                              className="bg-blue-50 border border-blue-100 rounded-md"
                              style={{ padding: 'clamp(0.5rem, 1.5vw, 0.625rem)' }}
                            >
                              <div 
                                className="font-medium text-blue-800"
                                style={{ 
                                  fontSize: 'clamp(0.75rem, 1.75vw, 0.8125rem)',
                                  marginBottom: 'clamp(0.25rem, 1vw, 0.375rem)'
                                }}
                              >
                                {t('components.prompts.chatMessageArea.toolName')}
                                <span style={{ marginLeft: 'clamp(0.125rem, 0.5vw, 0.1875rem)' }}>{toolCall.name}</span>
                              </div>
                              <div 
                                className="text-gray-600"
                                style={{ 
                                  fontSize: 'clamp(0.625rem, 1.5vw, 0.6875rem)',
                                  marginBottom: 'clamp(0.125rem, 0.5vw, 0.1875rem)'
                                }}
                              >
                                <span className="font-medium">{t('components.prompts.chatMessageArea.input')}</span>
                                <pre 
                                  className="font-mono bg-white rounded border whitespace-pre-wrap break-words m-0"
                                  style={{ 
                                    fontSize: 'clamp(0.625rem, 1.5vw, 0.6875rem)',
                                    lineHeight: 'clamp(1rem, 2vw, 1.125rem)',
                                    padding: 'clamp(0.25rem, 0.75vw, 0.3125rem) clamp(0.375rem, 1vw, 0.4375rem)',
                                    marginLeft: 'clamp(0.125rem, 0.5vw, 0.1875rem)'
                                  }}
                                >
                                  {/* 工具调用输入直接显示，如果没有值则显示 "-" */}
                                  {toolCall.input || '-'}
                                </pre>
                              </div>
                              <div 
                                className="text-gray-600"
                                style={{ fontSize: 'clamp(0.625rem, 1.5vw, 0.6875rem)' }}
                              >
                                <span className="font-medium">{t('components.prompts.chatMessageArea.output')}</span>
                                <pre 
                                  className="font-mono bg-green-50 rounded border text-green-800 whitespace-pre-wrap break-words m-0"
                                  style={{ 
                                    fontSize: 'clamp(0.625rem, 1.5vw, 0.6875rem)',
                                    lineHeight: 'clamp(1rem, 2vw, 1.125rem)',
                                    padding: 'clamp(0.25rem, 0.75vw, 0.3125rem) clamp(0.375rem, 1vw, 0.4375rem)',
                                    marginLeft: 'clamp(0.125rem, 0.5vw, 0.1875rem)'
                                  }}
                                >
                                  {/* 工具调用输出直接显示，如果没有值则显示 "-" */}
                                  {toolCall.output || '-'}
                                </pre>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 消息内容 - 放在最后 */}
                  {editingMessageIndex === index ? (
                    // 编辑模式
                    <div className="space-y-2">
                      <TextField
                        fullWidth
                        multiline
                        value={editingContent || ''}
                        onChange={e => {
                          if (isReadOnly) {
                            return
                          }
                          onEditContentChange?.(e.target.value)
                        }}
                        variant="outlined"
                        size="small"
                        disabled={isReadOnly}
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            fontSize: '14px',
                            lineHeight: 1.4,
                            backgroundColor: message.type === 'user' ? 'rgba(255,255,255,0.1)' : 'white',
                          },
                          '& .MuiOutlinedInput-input': {
                            color: message.type === 'user' ? 'white' : 'inherit',
                          },
                          '& .MuiOutlinedInput-notchedOutline': {
                            borderColor: message.type === 'user' ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.23)',
                          },
                        }}
                      />
                      <div className="flex space-x-2">
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<Check className="w-3 h-3" />}
                          onClick={() => {
                            if (isReadOnly) {
                              return
                            }
                            onSaveEdit?.(index, editingContent || '')
                          }}
                          disabled={isReadOnly}
                          sx={{
                            minWidth: 'auto',
                            fontSize: '12px',
                            backgroundColor: '#10b981',
                            '&:hover': { backgroundColor: '#059669' },
                          }}
                        >
                          {t('components.prompts.chatMessageArea.save')}
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<X className="w-3 h-3" />}
                          onClick={() => onCancelEdit?.()}
                          disabled={isReadOnly}
                          sx={{
                            minWidth: 'auto',
                            fontSize: '12px',
                            borderColor: '#d1d5db',
                            color: '#6b7280',
                            backgroundColor: 'white',
                            '&:hover': {
                              backgroundColor: '#f9fafb',
                              borderColor: '#d1d5db',
                            },
                          }}
                        >
                          {t('components.prompts.chatMessageArea.cancel')}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    // 显示模式
                    <div
                      className={`${message.type === 'user' ? 'text-white' : 'text-gray-700'} ${messageFormats[index] === 'markdown' ? '' : 'whitespace-pre-wrap'}`}
                      style={{ fontSize: 'clamp(0.75rem, 1.75vw, 0.8125rem)' }}
                    >
                      {messageFormats[index] === 'markdown' ? (
                        <div
                          className={`markdown-preview ${message.type === 'user' ? 'markdown-preview-dark' : 'markdown-preview-light'}`}
                          data-color-mode={message.type === 'user' ? 'dark' : 'light'}
                          style={{
                            backgroundColor: 'transparent',
                            color: message.type === 'user' ? 'white' : 'inherit',
                            fontSize: 'clamp(0.75rem, 1.75vw, 0.8125rem)',
                            lineHeight: '1.5',
                            wordBreak: 'break-word',
                            overflowWrap: 'break-word',
                          }}
                        >
                          <MarkdownPreview
                            source={message.content}
                            data-color-mode={message.type === 'user' ? 'dark' : 'light'}
                            style={{
                              backgroundColor: 'transparent',
                              color: message.type === 'user' ? 'white' : 'inherit',
                              fontSize: 'clamp(0.75rem, 1.75vw, 0.8125rem)',
                              lineHeight: '1.5',
                              padding: 0,
                              margin: 0,
                              wordBreak: 'break-word',
                              overflowWrap: 'break-word',
                            }}
                            wrapperElement={{
                              'data-color-mode': message.type === 'user' ? 'dark' : 'light',
                            }}
                          />
                        </div>
                      ) : (
                        <div 
                          className={message.content === '......' ? 'animate-pulse text-gray-400' : ''}
                          style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}
                        >
                          {message.content}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Token 和耗时信息 - 只在AI消息显示 */}
                  {false && message.type === 'ai' && (message.cost_ms || message.input_tokens || message.output_tokens) && (
                    <div className="mt-3 pt-2 border-t border-gray-200">
                      <div className="text-xs text-gray-500">
                        {t('components.prompts.chatMessageArea.costTime')}
                        {message.cost_ms ? `${Math.round((parseInt(message.cost_ms || '0') / 1000) * 100) / 100}s` : '0s'}
                        {t('components.prompts.chatMessageArea.inputTokens')}
                        {message.input_tokens || '0'}
                        {t('components.prompts.chatMessageArea.outputTokens')}
                        {message.output_tokens || '0'}
                      </div>
                    </div>
                  )}

                  {/* 消息控制按钮 - 从消息出现即展示（含 AI 输出过程中），编辑时隐藏 */}
                  {editingMessageIndex !== index && (
                    <div
                      className={`flex items-center ${message.type === 'user' ? 'justify-end' : 'justify-start'} border-t ${message.type === 'user' ? 'border-blue-400/30' : 'border-gray-100'}`}
                      style={{ 
                        gap: 'clamp(0.125rem, 0.5vw, 0.1875rem)',
                        padding: 'clamp(0.375rem, 1vw, 0.4375rem) clamp(0.5rem, 1.5vw, 0.625rem) clamp(0.25rem, 0.75vw, 0.4375rem)',
                        marginTop: 'clamp(0.375rem, 1vw, 0.4375rem)'
                      }}
                    >
                      {/* 优化按钮 - 只在AI消息显示 */}
                      {message.type === 'ai' && onOptimizeReply && (
                        <Tooltip title={t('components.prompts.chatMessageArea.optimizeReply')} arrow>
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => {
                              if (isReadOnly) {
                                return
                              }
                              onOptimizeReply(index)
                            }}
                            disabled={isReadOnly}
                            sx={{
                              minWidth: 'clamp(20px, 3vw, 22px)',
                              minHeight: 'clamp(20px, 3vw, 22px)',
                              padding: 'clamp(2px, 0.5vw, 3px)',
                              color: '#9ca3af',
                              '&:hover': { backgroundColor: '#f3f4f6' },
                            }}
                          >
                            <Sparkles style={{ width: 'clamp(0.625rem, 1.5vw, 0.6875rem)', height: 'clamp(0.625rem, 1.5vw, 0.6875rem)' }} />
                          </Button>
                        </Tooltip>
                      )}

                      {/* 重试按钮 - 只在最后一条AI消息显示 */}
                      {message.type === 'ai' && onRetryMessage && index === lastAIMessageIndex && (
                        <Tooltip title={t('components.prompts.chatMessageArea.regenerateReply')} arrow>
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => {
                              if (isReadOnly) {
                                return
                              }
                              onRetryMessage(index)
                            }}
                            disabled={isReadOnly}
                            sx={{
                              minWidth: 'clamp(20px, 3vw, 22px)',
                              minHeight: 'clamp(20px, 3vw, 22px)',
                              padding: 'clamp(2px, 0.5vw, 3px)',
                              color: '#9ca3af',
                              '&:hover': { backgroundColor: '#f3f4f6' },
                            }}
                          >
                            <RotateCw style={{ width: 'clamp(0.625rem, 1.5vw, 0.6875rem)', height: 'clamp(0.625rem, 1.5vw, 0.6875rem)' }} />
                          </Button>
                        </Tooltip>
                      )}

                      {/* Trace按钮 - 只在AI消息显示 */}
                      {false && message.type === 'ai' && onViewTrace && (
                        <Tooltip title={t('components.prompts.chatMessageArea.viewTrace')} arrow>
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => {
                              if (isReadOnly) {
                                return
                              }
                              onViewTrace?.(index)
                            }}
                            disabled={isReadOnly}
                            sx={{
                              minWidth: '24px',
                              minHeight: '24px',
                              padding: '4px',
                              color: '#9ca3af',
                              '&:hover': { backgroundColor: '#f3f4f6' },
                            }}
                          >
                            <Activity className="w-3 h-3" />
                          </Button>
                        </Tooltip>
                      )}

                      {/* Markdown/Text切换按钮 */}
                      <Tooltip
                        title={
                          messageFormats[index] === 'markdown'
                            ? t('components.prompts.chatMessageArea.switchToText')
                            : t('components.prompts.chatMessageArea.switchToMarkdown')
                        }
                        arrow
                      >
                        <Button
                          size="small"
                          variant="text"
                          onClick={() => {
                            if (isReadOnly) {
                              return
                            }
                            onToggleMessageFormat(index)
                          }}
                          disabled={isReadOnly}
                          sx={{
                            minWidth: 'clamp(20px, 3vw, 22px)',
                            minHeight: 'clamp(20px, 3vw, 22px)',
                            padding: 'clamp(2px, 0.5vw, 3px)',
                            color: message.type === 'user' ? 'rgba(255,255,255,0.8)' : '#9ca3af',
                            '&:hover': { backgroundColor: message.type === 'user' ? 'rgba(255,255,255,0.1)' : '#f3f4f6' },
                          }}
                        >
                          {messageFormats[index] === 'markdown' ? (
                            <FileText style={{ width: 'clamp(0.625rem, 1.5vw, 0.6875rem)', height: 'clamp(0.625rem, 1.5vw, 0.6875rem)' }} />
                          ) : (
                            <Code style={{ width: 'clamp(0.625rem, 1.5vw, 0.6875rem)', height: 'clamp(0.625rem, 1.5vw, 0.6875rem)' }} />
                          )}
                        </Button>
                      </Tooltip>

                      {/* 编辑按钮 */}
                      {onStartEdit && editingMessageIndex !== index && (
                        <Tooltip title={t('components.prompts.chatMessageArea.editMessage')} arrow>
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => {
                              if (isReadOnly) {
                                return
                              }
                              onEditMessage?.(index)
                              onStartEdit(index, message.content)
                            }}
                            disabled={isReadOnly}
                            sx={{
                              minWidth: 'clamp(20px, 3vw, 22px)',
                              minHeight: 'clamp(20px, 3vw, 22px)',
                              padding: 'clamp(2px, 0.5vw, 3px)',
                              color: message.type === 'user' ? 'rgba(255,255,255,0.8)' : '#9ca3af',
                              '&:hover': { backgroundColor: message.type === 'user' ? 'rgba(255,255,255,0.1)' : '#f3f4f6' },
                            }}
                          >
                            <Edit3 style={{ width: 'clamp(0.625rem, 1.5vw, 0.6875rem)', height: 'clamp(0.625rem, 1.5vw, 0.6875rem)' }} />
                          </Button>
                        </Tooltip>
                      )}

                      {/* 复制按钮 */}
                      {onCopyMessage && (
                        <Tooltip title={t('components.prompts.chatMessageArea.copyMessage')} arrow>
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => {
                              if (isReadOnly) {
                                return
                              }
                              onCopyMessage(message.content)
                            }}
                            disabled={isReadOnly}
                            sx={{
                              minWidth: 'clamp(20px, 3vw, 22px)',
                              minHeight: 'clamp(20px, 3vw, 22px)',
                              padding: 'clamp(2px, 0.5vw, 3px)',
                              color: message.type === 'user' ? 'rgba(255,255,255,0.8)' : '#9ca3af',
                              '&:hover': { backgroundColor: message.type === 'user' ? 'rgba(255,255,255,0.1)' : '#f3f4f6' },
                            }}
                          >
                            <Copy style={{ width: 'clamp(0.625rem, 1.5vw, 0.6875rem)', height: 'clamp(0.625rem, 1.5vw, 0.6875rem)' }} />
                          </Button>
                        </Tooltip>
                      )}

                      {/* 删除按钮 */}
                      {onDeleteMessage && (
                        <div className="relative flex items-center">
                          <Tooltip title={t('components.prompts.chatMessageArea.deleteMessage')} arrow>
                            <Button
                              ref={deleteConfirmIndex === index ? deleteButtonRef : null}
                              className="delete-button"
                              size="small"
                              variant="text"
                              onClick={() => {
                                if (isReadOnly) {
                                  return
                                }
                                setDeleteConfirmIndex(index)
                              }}
                              disabled={isReadOnly}
                              sx={{
                                minWidth: 'clamp(20px, 3vw, 22px)',
                                minHeight: 'clamp(20px, 3vw, 22px)',
                                padding: 'clamp(2px, 0.5vw, 3px)',
                                color: message.type === 'user' ? 'rgba(255,255,255,0.8)' : '#9ca3af',
                                '&:hover': { backgroundColor: message.type === 'user' ? 'rgba(255,255,255,0.1)' : '#f3f4f6' },
                              }}
                            >
                              <Trash2 style={{ width: 'clamp(0.625rem, 1.5vw, 0.6875rem)', height: 'clamp(0.625rem, 1.5vw, 0.6875rem)' }} />
                            </Button>
                          </Tooltip>

                          {/* 删除确认弹出框 - 使用Portal渲染到body */}
                          {deleteConfirmIndex === index &&
                            deleteButtonPosition &&
                            createPortal(
                              <div
                                className="delete-confirm-popup fixed bg-white border border-red-200 rounded-lg shadow-xl p-3 min-w-[200px]"
                                style={{
                                  zIndex: 9999,
                                  left: `${deleteButtonPosition.x}px`,
                                  top: `${deleteButtonPosition.y}px`,
                                  transform: 'translateX(-50%)',
                                }}
                              >
                                <div className="text-sm text-red-800 mb-3">{t('components.prompts.chatMessageArea.confirmDelete')}</div>
                                <div className="flex space-x-2">
                                  <Button
                                    size="small"
                                    variant="contained"
                                    onClick={() => {
                                      if (isReadOnly) {
                                        return
                                      }
                                      onDeleteMessage(index)
                                      setDeleteConfirmIndex(null)
                                      setDeleteButtonPosition(null)
                                    }}
                                    disabled={isReadOnly}
                                    sx={{
                                      minWidth: 'auto',
                                      fontSize: '12px',
                                      backgroundColor: '#dc2626',
                                      '&:hover': { backgroundColor: '#b91c1c' },
                                    }}
                                  >
                                    {t('components.prompts.chatMessageArea.confirmDeleteButton')}
                                  </Button>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    onClick={() => {
                                      setDeleteConfirmIndex(null)
                                      setDeleteButtonPosition(null)
                                    }}
                                    disabled={isReadOnly}
                                    sx={{
                                      minWidth: 'auto',
                                      fontSize: '12px',
                                      borderColor: '#d1d5db',
                                      color: '#6b7280',
                                    }}
                                  >
                                    {t('components.prompts.chatMessageArea.cancel')}
                                  </Button>
                                </div>
                              </div>,
                              document.body,
                            )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* 头像 - 在右侧显示（用户消息）*/}
              {message.type === 'user' && (
                <div className="flex-shrink-0 order-2" style={{ marginTop: 'clamp(0.75rem, 2vh, 1.25rem)' }}>
                  <div 
                    className="bg-gradient-to-br from-green-500 to-blue-500 rounded-full flex items-center justify-center"
                    style={{ 
                      width: 'clamp(1.5rem, 4vw, 1.75rem)', 
                      height: 'clamp(1.5rem, 4vw, 1.75rem)' 
                    }}
                  >
                    <User style={{ width: 'clamp(0.75rem, 2vw, 0.875rem)', height: 'clamp(0.75rem, 2vw, 0.875rem)' }} className="text-white" />
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* 停止响应按钮 - 固定在聊天区域底部 */}
      {isProcessing && !isStreamingStopped && onStopStreaming && (
        <div className="absolute bottom-0 left-0 right-0 flex justify-center py-3 bg-transparent border-t border-transparent">
          <Tooltip title={t('components.prompts.chatMessageArea.stopResponse')} arrow>
            <Button
              data-readonly-allowed="true"
              size="small"
              variant="outlined"
              onClick={() => {
                onStopStreaming()
              }}
              sx={{
                minWidth: 'auto',
                padding: '6px 12px',
                fontSize: '12px',
                borderColor: '#6b7280',
                color: '#6b7280',
                '&:hover': {
                  backgroundColor: '#f9fafb',
                  borderColor: '#4b5563',
                },
              }}
            >
              <span className="mr-1">{t('components.prompts.chatMessageArea.stopResponse')}</span>
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse" />
            </Button>
          </Tooltip>
        </div>
      )}
    </div>
  )
}

export default ChatMessageArea
