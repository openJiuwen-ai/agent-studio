import { useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { FeedbackOptService, type QuickOptimizeRequest } from '@test-agentstudio/api-client'
import type { OptimizingTarget, OptimizationSource, PromptMessage, ComparisonGroupData, Model, ModelConfig } from '@/types/promptType'
import { buildModelInfo } from '@/utils/prompts/modelInfoBuilder'
import { findModelByIdAndFrom, checkValidModel } from '@/utils/prompts/promptEditPageUtils'

// Hook 参数接口
interface UseQuickOptimizeDialogProps {
  // 状态
  optimizingTarget: OptimizingTarget | null
  setOptimizingTarget: React.Dispatch<React.SetStateAction<OptimizingTarget | null>>
  optimizationSource: OptimizationSource
  setOptimizationSource: React.Dispatch<React.SetStateAction<OptimizationSource>>
  quickOptimizeStreaming: string
  setQuickOptimizeStreaming: React.Dispatch<React.SetStateAction<string>>
  optimizationResult: string
  setOptimizationResult: React.Dispatch<React.SetStateAction<string>>
  isOptimizing: boolean
  setIsOptimizing: React.Dispatch<React.SetStateAction<boolean>>
  optimizationDialogOpen: boolean
  setOptimizationDialogOpen: React.Dispatch<React.SetStateAction<boolean>>
  showQuickOptimizeDiff: boolean
  setShowQuickOptimizeDiff: React.Dispatch<React.SetStateAction<boolean>>

  // Refs
  abortControllerRef: React.MutableRefObject<AbortController | null>
  quickOptimizeStreamingRef: React.MutableRefObject<string>

  // 数据
  promptMessages: PromptMessage[]
  messageInputValues: { [key: string]: string }
  comparisonGroupsData: ComparisonGroupData[]
  selectedModel: Model | null
  modelConfig: ModelConfig
  availableModels: Model[]

  // 工作空间
  workspaceId: string

  // 辅助函数
  setSnackbar: (snackbar: { open: boolean; message: string; severity: 'success' | 'error' | 'warning' | 'info' }) => void
  setPromptMessages: React.Dispatch<React.SetStateAction<PromptMessage[]>>
  setMessageInputValues: React.Dispatch<React.SetStateAction<{ [key: string]: string }>>
  setComparisonGroupsData: React.Dispatch<React.SetStateAction<ComparisonGroupData[]>>
  setHasUnsavedChanges: (hasChanges: boolean) => void
  triggerAutoSave: (data?: { promptMessages?: PromptMessage[] }) => void
  handlePromptChange: (field: string, value: any) => void
}

// Hook 返回值接口
interface UseQuickOptimizeDialogReturn {
  handleOptimizePrompt: (targetOverride?: { type: 'main' | 'base' | 'control' | 'message'; groupId?: number; messageId?: string }) => Promise<void>
  handleStopQuickOptimization: () => void
  handleApplyQuickOptimization: (content: string, target: { type: 'main' | 'base' | 'control' | 'message'; groupId?: number; messageId?: string }) => void
}

export const useQuickOptimizeDialog = (props: UseQuickOptimizeDialogProps): UseQuickOptimizeDialogReturn => {
  const { t } = useTranslation()

  const {
    optimizingTarget,
    setOptimizingTarget,
    optimizationSource,
    setOptimizationSource,
    quickOptimizeStreaming,
    setQuickOptimizeStreaming,
    optimizationResult,
    setOptimizationResult,
    isOptimizing,
    setIsOptimizing,
    setOptimizationDialogOpen,
    setShowQuickOptimizeDiff,
    abortControllerRef,
    quickOptimizeStreamingRef,
    promptMessages,
    messageInputValues,
    comparisonGroupsData,
    selectedModel,
    modelConfig,
    availableModels,
    setSnackbar,
    setPromptMessages,
    setMessageInputValues,
    setComparisonGroupsData,
    workspaceId,
    setHasUnsavedChanges,
    triggerAutoSave,
    handlePromptChange,
  } = props

  // 使用 ref 存储最新的 selectedModel 和 modelConfig，确保总是获取最新值
  const selectedModelRef = useRef(selectedModel)
  const modelConfigRef = useRef(modelConfig)
  // 使用 ref 存储最新的 comparisonGroupsData，确保在对比模式下总是获取最新的组配置
  const comparisonGroupsDataRef = useRef(comparisonGroupsData)

  // 当 props 更新时，同步更新 ref
  selectedModelRef.current = selectedModel
  modelConfigRef.current = modelConfig
  comparisonGroupsDataRef.current = comparisonGroupsData

  // 使用 ref 跟踪是否已经处理过错误，避免在完成回调中重复显示错误
  const hasErrorRef = useRef(false)

  const handleOptimizePrompt = useCallback(
    async (targetOverride?: { type: 'main' | 'base' | 'control' | 'message'; groupId?: number; messageId?: string }) => {
      // 从 ref 获取最新的模型信息，而不是依赖闭包中的值
      const currentSelectedModel = selectedModelRef.current
      const latestModelConfig = modelConfigRef.current

      // 检查是否配置了有效的模型
      if (!checkValidModel(currentSelectedModel, latestModelConfig, availableModels)) {
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.noModelConfigured'), severity: 'error' })
        return
      }

      // 使用传入的目标或当前状态中的目标
      const currentTarget = targetOverride || optimizingTarget

      // 设置优化来源状态
      if (currentTarget) {
        const newOptimizationSource = {
          type: currentTarget.type as 'main' | 'base' | 'control',
          groupId: currentTarget.groupId,
          messageId: currentTarget.messageId, // 保存messageId，确保使用正确的消息
        }
        setOptimizationSource(newOptimizationSource)
      }

      // 获取最新的对比组数据（使用 ref 确保获取最新值）
      const latestGroupsData = comparisonGroupsDataRef.current

      // 根据优化目标获取对应的提示词内容
      let originalContent = ''
      if (currentTarget?.type === 'main') {
        // 主编辑页面
        // 如果指定了messageId，使用指定的消息；否则使用第一个system消息
        const systemMessage = currentTarget.messageId
          ? promptMessages.find(msg => msg.id === currentTarget.messageId)
          : promptMessages.find(msg => msg.role === 'system')

        // 如果找到了消息，优先使用 messageInputValues 中的值（用户编辑后的内容）
        originalContent = systemMessage
          ? messageInputValues[systemMessage.id] || systemMessage.content || t('components.prompts.quickOptimizeDialog.templateNotFound')
          : t('components.prompts.quickOptimizeDialog.templateNotFound')
      } else if (currentTarget?.type === 'base') {
        // 基准组 - 使用 ref 获取最新的组数据
        const baseGroup = latestGroupsData.find(g => g.id === 0)
        // 如果指定了messageId，使用指定的消息；否则使用第一个system消息
        const systemMessage = currentTarget.messageId
          ? baseGroup?.messages.find(msg => msg.id === currentTarget.messageId)
          : baseGroup?.messages.find(msg => msg.role === 'system')
        // 如果找到了消息，优先使用 messageInputValues 中的值（用户编辑后的内容）
        originalContent = systemMessage
          ? (baseGroup?.messageInputValues || {})[systemMessage.id] || systemMessage.content || t('components.prompts.quickOptimizeDialog.templateNotFoundBase')
          : t('components.prompts.quickOptimizeDialog.templateNotFoundBase')
      } else if (currentTarget?.type === 'control' && currentTarget.groupId) {
        // 对照组 - 使用 ref 获取最新的组数据
        const group = latestGroupsData.find(g => g.id === currentTarget.groupId)
        // 如果指定了messageId，使用指定的消息；否则使用第一个system消息
        const systemMessage = currentTarget.messageId
          ? group?.messages.find(msg => msg.id === currentTarget.messageId)
          : group?.messages.find(msg => msg.role === 'system')
        // 如果找到了消息，优先使用 messageInputValues 中的值（用户编辑后的内容）
        originalContent = systemMessage
          ? group?.messageInputValues[systemMessage.id] || systemMessage.content || t('components.prompts.quickOptimizeDialog.templateNotFoundControl', { groupId: currentTarget.groupId })
          : t('components.prompts.quickOptimizeDialog.templateNotFoundControl', { groupId: currentTarget.groupId })
      } else if (currentTarget?.type === 'message' && currentTarget.messageId) {
        // 特定消息 - 使用 ref 获取最新的组数据
        let message = promptMessages.find(msg => msg.id === currentTarget.messageId)
        if (!message) {
          message = (latestGroupsData.find(g => g.id === 0)?.messages || []).find(msg => msg.id === currentTarget.messageId)
        }
        if (!message) {
          // 在对照组中查找
          for (const group of latestGroupsData) {
            message = group.messages.find(msg => msg.id === currentTarget.messageId)
            if (message) break
          }
        }
        originalContent = message?.content || t('components.prompts.quickOptimizeDialog.messageNotFound')
      } else {
        originalContent = t('components.prompts.quickOptimizeDialog.templateNotFound')
      }

      // 验证内容
      if (originalContent.includes(t('components.prompts.quickOptimizeDialog.notFoundKeyword'))) {
        setSnackbar({
          open: true,
          message: t('components.prompts.promptEditPage.targetPromptEmpty'),
          severity: 'warning',
        })
        return
      }

      // 取消之前的请求（如果存在）
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }

      // 首先重置所有状态
      // 立即重置ref（同步操作）
      quickOptimizeStreamingRef.current = ''
      hasErrorRef.current = false // 重置错误标志

      // 重置React状态（异步操作）
      setQuickOptimizeStreaming('')
      setOptimizationResult('')
      setShowQuickOptimizeDiff(false) // 重置差异对比显示状态
      setIsOptimizing(true)
      setOptimizationDialogOpen(true)

      // 创建新的 AbortController
      abortControllerRef.current = new AbortController()

      // 获取当前选中的模型信息（使用 ref 中的最新值）
      let currentModel = currentSelectedModel
      let currentModelConfig = latestModelConfig

      // 根据优化目标获取对应的模型配置 - 使用 ref 获取最新的组数据（已在上面获取）
      // 基准组和对照组的逻辑相同，只是组号不同（基准组组号为0，对照组组号从currentTarget.groupId获取）
      if (currentTarget?.type === 'base' || (currentTarget?.type === 'control' && currentTarget.groupId)) {
        const groupId = currentTarget.type === 'base' ? 0 : currentTarget.groupId!
        const group = latestGroupsData.find(g => g.id === groupId)
        if (group?.modelConfig) {
          currentModelConfig = group.modelConfig
          currentModel = findModelByIdAndFrom(group.modelConfig.model, group.modelConfig.model_from, availableModels) || currentSelectedModel
        }
      }
      // 如果优化目标是 'main' 类型或 'message' 类型，使用当前主页面选中的模型
      // 使用 ref 确保获取的是最新的模型信息，而不是闭包中可能过时的值

      if (!currentModel) {
        setSnackbar({
          open: true,
          message: t('components.prompts.promptEditPage.noValidModelConfig'),
          severity: 'error',
        })
        setIsOptimizing(false)
        return
      }

      // 构建快捷优化请求
      const modelInfo = buildModelInfo(currentModel, currentModelConfig, 1)

      const quickOptimizeRequest: QuickOptimizeRequest = {
        modelInfo,
        instruct: originalContent,
        stream: true,
      }

      // 确保状态重置完成后再开始API调用
      await new Promise(resolve => setTimeout(resolve, 10))

      // 添加超时检测
      const timeoutId = setTimeout(() => {
        if (isOptimizing) {
          console.error('快捷优化超时：API长时间无响应')
          setSnackbar({
            open: true,
            message: t('components.prompts.promptEditPage.quickOptimizeTimeout'),
            severity: 'error',
          })
          setIsOptimizing(false)
          if (abortControllerRef.current) {
            abortControllerRef.current.abort()
            abortControllerRef.current = null
          }
        }
      }, 300000) // 5分钟超时

      try {
        await FeedbackOptService.quickOptimize(
          quickOptimizeRequest,
          workspaceId,
          (data: string) => {
            // 流式数据回调
            // 注意：错误JSON已经在feedbackOptService中通过onError回调处理，这里只需要累积正常的内容
            quickOptimizeStreamingRef.current += data
            const accumulatedContent = quickOptimizeStreamingRef.current
            setQuickOptimizeStreaming(accumulatedContent)
          },
          (error: string) => {
            // 错误回调
            clearTimeout(timeoutId)
            hasErrorRef.current = true // 标记已处理错误
            console.error('快捷优化失败:', error)
            setSnackbar({
              open: true,
              message: t('components.prompts.promptEditPage.quickOptimizeFailedWithError', { error: error || '' }),
              severity: 'error',
            })
            setIsOptimizing(false)
            if (abortControllerRef.current) {
              abortControllerRef.current.abort() // 取消请求，避免继续处理
              abortControllerRef.current = null
            }
          },
          () => {
            // 完成回调
            clearTimeout(timeoutId)
            setIsOptimizing(false)

            // 如果已经处理过错误，不再显示"无内容返回"的错误
            if (hasErrorRef.current) {
              if (abortControllerRef.current) {
                abortControllerRef.current = null
              }
              return
            }

            // 检查是否有内容返回
            // 注意：错误JSON已经在onError回调中处理，这里只需要检查是否有实际内容
            const finalContent = quickOptimizeStreamingRef.current

            // 如果没有有效内容（为空），显示"无内容返回"的提示
            if (!finalContent || finalContent.trim().length === 0) {
              console.error('快捷优化完成但无内容返回')
              setSnackbar({
                open: true,
                message: t('components.prompts.promptEditPage.quickOptimizeNoContent'),
                severity: 'error',
              })
              setOptimizationResult('')
              setQuickOptimizeStreaming('') // 清空流式内容
              if (abortControllerRef.current) {
                abortControllerRef.current = null
              }
              return
            }

            // 将流式内容设置为最终结果
            setOptimizationResult(finalContent)
            // 清理 AbortController
            abortControllerRef.current = null

            // 延迟显示差异对比
            setTimeout(() => {
              setShowQuickOptimizeDiff(true)
            }, 800)
          },
          abortControllerRef.current,
        )
      } catch (error) {
        clearTimeout(timeoutId)
        // 检查是否是用户主动取消的请求
        if (error instanceof Error && error.name === 'AbortError') {
          return
        }

        console.error('快捷优化请求失败:', error)

        // 检查是否是ApiError，如果是则显示具体的错误信息
        let errorMessage = t('components.prompts.promptEditPage.quickOptimizeRequestFailed')
        if (error instanceof Error) {
          // 尝试从错误信息中提取更详细的错误描述
          if (error.message) {
            errorMessage = t('components.prompts.promptEditPage.quickOptimizeFailedWithError', { error: error.message })
          }
        }

        setSnackbar({
          open: true,
          message: errorMessage,
          severity: 'error',
        })
        setIsOptimizing(false)
        // 清理 AbortController
        abortControllerRef.current = null
      }
    },
    [
      optimizingTarget,
      setOptimizationSource,
      promptMessages,
      messageInputValues,
      comparisonGroupsData,
      abortControllerRef,
      quickOptimizeStreaming,
      quickOptimizeStreamingRef,
      optimizationResult,
      isOptimizing,
      setQuickOptimizeStreaming,
      setOptimizationResult,
      setShowQuickOptimizeDiff,
      setIsOptimizing,
      setOptimizationDialogOpen,
      selectedModel,
      modelConfig,
      availableModels,
      setSnackbar,
      t,
    ],
  )

  // 快捷优化对话框回调函数
  // 停止快捷优化
  const handleStopQuickOptimization = useCallback(() => {
    // 取消正在进行的流式请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    // 停止优化状态
    setIsOptimizing(false)

    // 将当前的流式内容设置为最终结果
    const currentContent = quickOptimizeStreaming || quickOptimizeStreamingRef.current
    if (currentContent) {
      setOptimizationResult(currentContent)
      // 显示差异对比
      setShowQuickOptimizeDiff(true)
    }
  }, [abortControllerRef, setIsOptimizing, quickOptimizeStreaming, quickOptimizeStreamingRef, setOptimizationResult, setShowQuickOptimizeDiff])

  const handleApplyQuickOptimization = useCallback(
    (content: string, target: { type: 'main' | 'base' | 'control' | 'message'; groupId?: number; messageId?: string }) => {
      if (target.type === 'base') {
        // 如果没有messageId，则报错
        if (!target.messageId) {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.messageIdRequired'), severity: 'error' })
          setOptimizingTarget(null)
          setOptimizationResult('')
          setQuickOptimizeStreaming('')
          return
        }

        // 应用到基准组的指定消息
        setComparisonGroupsData(prev =>
          prev.map(g =>
            g.id === 0
              ? {
                  ...g,
                  messages: g.messages.map(msg => {
                    // 如果有messageId，只更新指定的消息
                    return msg.id === target.messageId! ? { ...msg, content } : msg
                  }),
                  messageInputValues: {
                    ...g.messageInputValues,
                    [target.messageId!]: content,
                  },
                }
              : g,
          ),
        )

        // 触发自动保存草稿（基准组不需要保存草稿，但保持一致性）
        setHasUnsavedChanges(true)

        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.baseGroupPromptOptimized'), severity: 'success' })
      } else if (target.type === 'control' && target.groupId) {
        // 如果没有messageId，则报错
        if (!target.messageId) {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.messageIdRequired'), severity: 'error' })
          setOptimizingTarget(null)
          setOptimizationResult('')
          setQuickOptimizeStreaming('')
          return
        }

        // 应用到对照组的指定消息
        setComparisonGroupsData(prevGroups =>
          prevGroups.map(g => {
            if (g.id === target.groupId) {
              return {
                ...g,
                messages: g.messages.map(msg => {
                  // 如果有messageId，只更新指定的消息
                  return msg.id === target.messageId! ? { ...msg, content } : msg
                }),
                messageInputValues: {
                  ...g.messageInputValues,
                  [target.messageId!]: content,
                },
              }
            }
            return g
          }),
        )

        // 触发自动保存草稿（对照组不需要保存草稿，但保持一致性）
        setHasUnsavedChanges(true)

        setSnackbar({
          open: true,
          message: t('components.prompts.promptEditPage.controlGroupPromptOptimized', { groupId: target.groupId }),
          severity: 'success',
        })
      } else {
        // 应用到主编辑页面的消息
        // 如果没有messageId，则报错
        if (!target.messageId) {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.messageIdRequired'), severity: 'error' })
          setOptimizingTarget(null)
          setOptimizationResult('')
          setQuickOptimizeStreaming('')
          return
        }

        // 如果有具体的messageId，则更新指定的消息
        const newMessages = promptMessages.map(msg => (msg.id === target.messageId! ? { ...msg, content } : msg))
        setPromptMessages(newMessages)

        // 同时更新输入值
        setMessageInputValues(prev => ({
          ...prev,
          [target.messageId!]: content,
        }))

        // 更新组合后的prompt.content
        const combinedContent = newMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
        handlePromptChange('content', combinedContent)

        // 触发自动保存草稿
        setHasUnsavedChanges(true)
        triggerAutoSave({ promptMessages: newMessages })

        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.promptOptimized'), severity: 'success' })
      }

      // 清理状态
      setOptimizingTarget(null)
      setOptimizationResult('')
      setQuickOptimizeStreaming('')
    },
    [
      comparisonGroupsData,
      setSnackbar,
      setOptimizingTarget,
      setOptimizationResult,
      setQuickOptimizeStreaming,
      setComparisonGroupsData,
      setHasUnsavedChanges,
      promptMessages,
      setPromptMessages,
      setMessageInputValues,
      handlePromptChange,
      triggerAutoSave,
      t,
    ],
  )

  return {
    handleOptimizePrompt,
    handleStopQuickOptimization,
    handleApplyQuickOptimization,
  }
}
