import React, { useRef, useEffect, useState } from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography, IconButton, CircularProgress } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { RefreshCw, Zap, Square, Maximize, Minimize } from 'lucide-react'
import DiffViewer from './DiffViewer'
import { ModelConfig, OptimizingTarget, PromptMessage as Message, Model, ControlGroupData } from '@/types/promptType'

// 快捷优化对话框属性
export interface QuickOptimizeDialogProps {
  open: boolean
  onClose: () => void
  isOptimizing: boolean
  optimizingTarget: OptimizingTarget | null
  optimizationSource: { type: 'main' | 'base' | 'control'; groupId?: number; messageId?: string }
  optimizationResult: string
  quickOptimizeStreaming: string
  showDiffViewer: boolean
  promptMessages: Message[]
  baseGroupMessages: Message[]
  controlGroupsData: ControlGroupData[]
  selectedModel: Model | null
  availableModels: Model[]
  modelConfig: ModelConfig
  baseGroupModelConfig: ModelConfig
  onOptimizePrompt: (source: { type: 'main' | 'base' | 'control'; groupId?: number; messageId?: string }) => void
  onApplyOptimization: (content: string, target: OptimizingTarget) => void
  onStopOptimization: () => void
  onShowSnackbar: (message: string, severity: 'success' | 'error' | 'warning' | 'info') => void
}

export const QuickOptimizeDialog: React.FC<QuickOptimizeDialogProps> = ({
  open,
  onClose,
  isOptimizing,
  optimizingTarget,
  optimizationSource,
  optimizationResult,
  quickOptimizeStreaming,
  showDiffViewer,
  promptMessages,
  baseGroupMessages,
  controlGroupsData,
  selectedModel,
  availableModels,
  modelConfig,
  baseGroupModelConfig,
  onOptimizePrompt,
  onApplyOptimization,
  onStopOptimization,
  onShowSnackbar,
}) => {
  const { t } = useTranslation()
  const quickOptimizeStreamingRef = useRef('')
  const streamingScrollRef = useRef<HTMLDivElement>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // 跟踪对话框的打开状态，只在从关闭变为打开时重置
  const prevOpenRef = useRef(false)
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      // 对话框从关闭变为打开
      console.log('🔄 [QuickOptimizeDialog] 对话框从关闭变为打开，重置内部ref前:', {
        internalRef: quickOptimizeStreamingRef.current.substring(0, 50) + '...',
        propsQuickOptimizeStreaming: quickOptimizeStreaming.substring(0, 50) + '...',
        propsOptimizationResult: optimizationResult.substring(0, 50) + '...',
      })
      quickOptimizeStreamingRef.current = ''
      console.log('✅ [QuickOptimizeDialog] 对话框打开，内部ref已重置')
    }
    prevOpenRef.current = open
  }, [open, quickOptimizeStreaming, optimizationResult])

  // 获取原始内容
  const getOriginalContent = (): string => {
    // 优先使用 optimizationSource.messageId 或 optimizingTarget.messageId
    const messageId = optimizationSource.messageId || optimizingTarget?.messageId

    if (optimizingTarget?.type === 'main') {
      // 如果指定了messageId，使用指定的消息；否则使用第一个system消息
      if (!promptMessages || !Array.isArray(promptMessages)) {
        return t('components.prompts.quickOptimizeDialog.templateNotFound')
      }
      const systemMessage = messageId ? promptMessages.find(msg => msg.id === messageId) : promptMessages.find(msg => msg.role === 'system')
      return systemMessage?.content || t('components.prompts.quickOptimizeDialog.templateNotFound')
    } else if (optimizingTarget?.type === 'base') {
      // 如果指定了messageId，使用指定的消息；否则使用第一个system消息
      if (!baseGroupMessages || !Array.isArray(baseGroupMessages)) {
        return t('components.prompts.quickOptimizeDialog.templateNotFoundBase')
      }
      const systemMessage = messageId ? baseGroupMessages.find(msg => msg.id === messageId) : baseGroupMessages.find(msg => msg.role === 'system')
      return systemMessage?.content || t('components.prompts.quickOptimizeDialog.templateNotFoundBase')
    } else if (optimizingTarget?.type === 'control' && optimizingTarget.groupId) {
      const group = controlGroupsData?.find(g => g.id === optimizingTarget.groupId)
      if (!group || !group.messages || !Array.isArray(group.messages)) {
        return t('components.prompts.quickOptimizeDialog.templateNotFoundControl', { groupId: optimizingTarget.groupId })
      }
      // 如果指定了messageId，使用指定的消息；否则使用第一个system消息
      const systemMessage = messageId ? group.messages.find(msg => msg.id === messageId) : group.messages.find(msg => msg.role === 'system')
      return systemMessage?.content || t('components.prompts.quickOptimizeDialog.templateNotFoundControl', { groupId: optimizingTarget.groupId })
    } else if (optimizingTarget?.type === 'message' && optimizingTarget.messageId) {
      let message: Message | undefined
      if (promptMessages && Array.isArray(promptMessages)) {
        message = promptMessages.find(msg => msg.id === optimizingTarget.messageId)
      }
      if (!message && baseGroupMessages && Array.isArray(baseGroupMessages)) {
        message = baseGroupMessages.find(msg => msg.id === optimizingTarget.messageId)
      }
      if (!message && controlGroupsData && Array.isArray(controlGroupsData)) {
        for (const group of controlGroupsData) {
          if (group.messages && Array.isArray(group.messages)) {
            message = group.messages.find(msg => msg.id === optimizingTarget.messageId)
            if (message) break
          }
        }
      }
      return message?.content || t('components.prompts.quickOptimizeDialog.messageNotFound')
    }
    return t('components.prompts.quickOptimizeDialog.templateNotFound')
  }

  // 执行优化
  const handleOptimizePrompt = async (targetOverride?: OptimizingTarget) => {
    const currentTarget = targetOverride || optimizingTarget

    // 获取原始内容
    const originalContent = getOriginalContent()

    // 验证内容
    if (originalContent.includes(t('components.prompts.quickOptimizeDialog.notFoundKeyword'))) {
      onShowSnackbar(t('components.prompts.quickOptimizeDialog.noValidContent'), 'warning')
      return
    }

    console.log('🚀 [QuickOptimizeDialog] 重试优化，调用父组件的完整优化流程')

    // 构建优化源信息
    const optimizationSourceToUse = {
      type: (currentTarget?.type || 'main') as 'main' | 'base' | 'control',
      groupId: currentTarget?.groupId,
      messageId: currentTarget?.messageId || optimizationSource.messageId, // 保留messageId
    }

    // 直接调用父组件的优化函数，复用完整的优化流程
    onOptimizePrompt(optimizationSourceToUse)
    console.log('✅ [QuickOptimizeDialog] 已调用父组件的完整优化流程')
  }

  // 停止流式输出
  const handleStopOptimization = () => {
    console.log('🛑 [QuickOptimizeDialog] 用户点击停止响应')
    onStopOptimization()
  }

  // 应用优化结果
  const handleApplyOptimization = () => {
    const contentToApply = optimizationResult || quickOptimizeStreaming
    console.log('🔍 [QuickOptimizeDialog] 应用优化结果', {
      optimizationSource,
      optimizingTarget,
      contentToApply: contentToApply?.substring(0, 100) + '...',
    })
    if (!isOptimizing && contentToApply && optimizingTarget) {
      // 使用optimizingTarget而不是optimizationSource，因为它包含完整的目标信息（包括messageId）
      console.log('🔍 [QuickOptimizeDialog] 调用onApplyOptimization', {
        target: optimizingTarget,
        contentLength: contentToApply.length,
      })
      onApplyOptimization(contentToApply, optimizingTarget)
      onClose()
    }
  }

  // 自动滚动到底部的effect
  useEffect(() => {
    if (quickOptimizeStreaming && streamingScrollRef.current) {
      streamingScrollRef.current.scrollTop = streamingScrollRef.current.scrollHeight
    }
  }, [quickOptimizeStreaming])

  // 切换全屏
  const handleToggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  const originalContent = getOriginalContent()

  // 检查内容是否是错误JSON（优化失败的情况）
  const isErrorContent = (() => {
    const content = optimizationResult || quickOptimizeStreaming
    if (!content || content.trim().length === 0) return false
    try {
      const parsed = JSON.parse(content.trim())
      return !!(parsed.error || (parsed.code && parsed.code !== 200 && parsed.code !== 0))
    } catch (e) {
      // 不是JSON格式，不是错误
      return false
    }
  })()

  // 检查是否优化失败：对话框打开、不在优化中、没有内容、且有优化目标（说明曾经尝试过优化）
  const isOptimizationFailed = open && !isOptimizing && !optimizationResult && !quickOptimizeStreaming && !!optimizingTarget

  // 如果曾经尝试过优化（有内容或正在优化或对话框已打开），即使失败也应该显示分栏布局
  // 对话框打开说明曾经尝试过优化，即使失败了也应该显示分栏布局
  const hasContent = optimizationResult || quickOptimizeStreaming || isOptimizing || open

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={isFullscreen ? false : 'lg'}
      fullWidth
      fullScreen={isFullscreen}
      PaperProps={{
        sx: {
          borderRadius: isFullscreen ? '0px' : '16px',
          background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.95) 100%)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255,255,255,0.2)',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          height: isFullscreen ? '100vh' : 'auto',
          maxHeight: isFullscreen ? '100vh' : '90vh',
        },
      }}
    >
      <DialogTitle className="border-b border-gray-200/60 bg-white/60 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl shadow-sm">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <Typography variant="h6" className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
              {t('components.prompts.quickOptimizeDialog.title')}
            </Typography>
          </div>
          <div className="flex items-center space-x-1">
            <IconButton
              onClick={handleToggleFullscreen}
              size="small"
              title={isFullscreen ? t('components.prompts.quickOptimizeDialog.exitFullscreen') : t('components.prompts.quickOptimizeDialog.enterFullscreen')}
              sx={{
                color: '#6b7280',
                '&:hover': {
                  color: '#3b82f6',
                  backgroundColor: 'rgba(59, 130, 246, 0.1)',
                },
              }}
            >
              {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
            </IconButton>
            <IconButton
              onClick={onClose}
              size="small"
              sx={{
                color: '#6b7280',
                '&:hover': {
                  color: '#ef4444',
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                },
              }}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </IconButton>
          </div>
        </div>
      </DialogTitle>

      <DialogContent className="p-0 bg-white" sx={{ height: isFullscreen ? 'calc(100vh - 140px)' : 'auto' }}>
        {hasContent ? (
          <div className="flex flex-col" style={{ height: isFullscreen ? 'calc(100vh - 140px)' : '600px' }}>
            <div className="bg-gradient-to-r from-gray-50/80 to-blue-50/80 border-b border-gray-200/60 backdrop-blur-sm">
              {/* 标题栏布局参考根据调试结果优化提示词对话框 */}
              <div className="flex">
                <div className="w-1/2 px-4 py-3 border-r border-gray-300/60 flex items-center justify-between">
                  <div className="flex items-center">
                    <Typography variant="subtitle2" className="font-semibold text-gray-700">
                      {t('components.prompts.quickOptimizeDialog.originalTemplate')}
                    </Typography>
                  </div>
                </div>
                <div className="w-1/2 px-4 py-3">
                  <div className="flex items-center">
                    <Typography variant="subtitle2" className="font-semibold text-gray-700">
                      {t('components.prompts.quickOptimizeDialog.optimizedTemplate')}
                    </Typography>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex-1 overflow-auto bg-white">
              {(() => {
                // 如果正在优化中，显示流式内容，否则显示最终结果
                const newContent = isOptimizing ? quickOptimizeStreaming : optimizationResult

                // 只有在父组件允许显示差异对比时才显示DiffViewer
                if (showDiffViewer && optimizationResult) {
                  return (
                    <div className="h-full bg-white">
                      <DiffViewer oldContent={originalContent} newContent={optimizationResult} autoScroll={false} />
                    </div>
                  )
                }

                // 显示分栏布局（参考根据调试结果优化提示词对话框）
                return (
                  <div className="flex h-full">
                    {/* 原提示词模板 - 左侧 */}
                    <div className="flex-1 border-r border-gray-300/60 flex flex-col">
                      <div className="p-4 font-mono text-sm bg-gradient-to-br from-gray-50/50 to-white overflow-y-auto flex-1">
                        <pre className="whitespace-pre-wrap text-gray-700 leading-relaxed">{originalContent}</pre>
                      </div>
                    </div>

                    {/* 优化后Prompt模板 - 右侧 */}
                    <div className="flex-1 flex flex-col">
                      {isOptimizing ? (
                        // 优化中显示流式输出内容
                        quickOptimizeStreaming && !isErrorContent ? (
                          <div ref={streamingScrollRef} className="p-4 font-mono text-sm bg-gradient-to-br from-blue-50/50 to-white overflow-y-auto flex-1">
                            <pre className="whitespace-pre-wrap text-gray-700 leading-relaxed">{quickOptimizeStreaming}</pre>
                          </div>
                        ) : (
                          // 还没有流式内容时显示加载状态
                          <div className="p-4 flex items-center justify-center flex-1 bg-gradient-to-br from-blue-50/80 to-purple-50/80">
                            <div className="text-center">
                              <div className="p-4 bg-white/80 rounded-xl shadow-sm backdrop-blur-sm border border-white/20">
                                <CircularProgress size={40} className="mb-4" sx={{ color: '#3b82f6' }} />
                                <Typography variant="body2" className="text-gray-600 font-medium">
                                  {t('components.prompts.quickOptimizeDialog.generating')}
                                </Typography>
                              </div>
                            </div>
                          </div>
                        )
                      ) : optimizationResult && !showDiffViewer && !isErrorContent ? (
                        // 优化完成但还未显示差异对比时，显示完整的优化结果
                        <div className="p-4 font-mono text-sm bg-gradient-to-br from-emerald-50/50 to-white overflow-y-auto flex-1">
                          <pre className="whitespace-pre-wrap text-gray-700 leading-relaxed">{optimizationResult}</pre>
                          <div className="mt-4 p-3 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 border border-blue-200/60 rounded-lg shadow-sm backdrop-blur-sm">
                            <div className="flex items-center text-blue-600">
                              <CircularProgress size={16} className="mr-2" sx={{ color: '#3b82f6' }} />
                              <Typography variant="caption" className="font-medium">
                                {t('components.prompts.quickOptimizeDialog.preparingDiff')}
                              </Typography>
                            </div>
                          </div>
                        </div>
                      ) : (
                        // 默认状态或优化失败：显示占位符
                        <div className="p-4 flex items-center justify-center flex-1 bg-gradient-to-br from-blue-50/80 to-purple-50/80">
                          <div className="text-center">
                            <div className="p-4 bg-white/80 rounded-xl shadow-sm backdrop-blur-sm border border-white/20">
                              <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center mb-3 mx-auto shadow-sm">
                                <Zap className="w-8 h-8 text-white" />
                              </div>
                              {isErrorContent || isOptimizationFailed ? (
                                // 优化失败时显示错误提示
                                <>
                                  <Typography variant="body2" className="text-gray-600 mb-2 font-medium">
                                    {t('components.prompts.quickOptimizeDialog.optimizationFailed')}
                                  </Typography>
                                  <Typography variant="caption" className="text-gray-500">
                                    {t('components.prompts.quickOptimizeDialog.optimizedContentHere')}
                                  </Typography>
                                </>
                              ) : (
                                // 默认状态
                                <>
                                  <Typography variant="body2" className="text-gray-600 mb-2 font-medium">
                                    {t('components.prompts.quickOptimizeDialog.clickToGenerate')}
                                  </Typography>
                                  <Typography variant="caption" className="text-gray-500">
                                    {t('components.prompts.quickOptimizeDialog.optimizedContentHere')}
                                  </Typography>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })()}
            </div>
          </div>
        ) : (
          <div className="flex flex-col" style={{ height: isFullscreen ? 'calc(100vh - 140px)' : '600px' }}>
            <div className="bg-gradient-to-r from-gray-50/80 to-blue-50/80 border-b border-gray-200/60 backdrop-blur-sm">
              {/* 初始状态标题栏 - 只显示原提示词模板 */}
              <div className="flex">
                <div className="w-full px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center">
                    <Typography variant="subtitle2" className="font-semibold text-gray-700">
                      {t('components.prompts.quickOptimizeDialog.originalTemplate')}
                    </Typography>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex-1 overflow-auto bg-white">
              <div className="h-full">
                <div className="p-4 font-mono text-sm bg-gradient-to-br from-gray-50/50 to-white overflow-y-auto h-full">
                  <pre className="whitespace-pre-wrap text-gray-700 leading-relaxed">
                    {originalContent || t('components.prompts.quickOptimizeDialog.clickToStart')}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}
      </DialogContent>

      <DialogActions className="border-t border-gray-200/60 bg-white/60 backdrop-blur-sm p-4">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-2">
            <IconButton
              size="small"
              onClick={() => handleOptimizePrompt()}
              disabled={isOptimizing}
              title={t('components.prompts.quickOptimizeDialog.retry')}
              sx={{
                color: '#6b7280',
                backgroundColor: 'rgba(255,255,255,0.8)',
                border: '1px solid rgba(229,231,235,0.6)',
                borderRadius: '8px',
                '&:hover': {
                  color: '#f59e0b',
                  backgroundColor: 'rgba(245,158,11,0.1)',
                  borderColor: 'rgba(245,158,11,0.3)',
                },
                '&:disabled': {
                  color: '#d1d5db',
                  backgroundColor: 'rgba(243,244,246,0.5)',
                },
              }}
            >
              <RefreshCw className="w-4 h-4" />
            </IconButton>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              variant="outlined"
              onClick={onClose}
              sx={{
                borderRadius: '10px',
                borderColor: 'rgba(156,163,175,0.5)',
                color: '#6b7280',
                '&:hover': {
                  borderColor: 'rgba(156,163,175,0.8)',
                  backgroundColor: 'rgba(243,244,246,0.5)',
                },
              }}
            >
              {t('components.prompts.quickOptimizeDialog.cancel')}
            </Button>
            {isOptimizing && quickOptimizeStreaming ? (
              // 流式输出时显示停止按钮
              <Button
                variant="contained"
                onClick={handleStopOptimization}
                startIcon={<Square className="w-4 h-4" />}
                sx={{
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  boxShadow: '0 4px 12px rgba(239,68,68,0.4)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
                    boxShadow: '0 6px 16px rgba(239,68,68,0.5)',
                    transform: 'translateY(-1px)',
                  },
                  transition: 'all 0.2s ease-in-out',
                }}
              >
                {t('components.prompts.quickOptimizeDialog.stopResponse')}
              </Button>
            ) : (
              // 非流式输出时显示采纳按钮
              <Button
                variant="contained"
                disabled={isOptimizing || !optimizationResult || isErrorContent}
                onClick={handleApplyOptimization}
                sx={{
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
                  boxShadow: '0 4px 12px rgba(59,130,246,0.4)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)',
                    boxShadow: '0 6px 16px rgba(59,130,246,0.5)',
                    transform: 'translateY(-1px)',
                  },
                  '&:disabled': {
                    background: 'linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%)',
                    boxShadow: 'none',
                  },
                  transition: 'all 0.2s ease-in-out',
                }}
              >
                {t('components.prompts.quickOptimizeDialog.adopt')}
              </Button>
            )}
          </div>
        </div>
      </DialogActions>
    </Dialog>
  )
}

export default QuickOptimizeDialog
