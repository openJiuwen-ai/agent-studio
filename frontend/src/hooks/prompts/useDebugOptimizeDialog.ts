import { useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { FeedbackOptService, type OptimizeBadcaseRequest } from '@test-agentstudio/api-client'
import type { SelectedAiReply, OptimizeStep, OptimizationSource, PromptMessage, ComparisonGroupData, Model, ModelConfig } from '@/types/promptType'
import { buildModelInfo } from '@/utils/prompts/modelInfoBuilder'
import { findModelByIdAndFrom, getFirstSystemMessage } from '@/utils/prompts/promptEditPageUtils'

// Hook 参数接口
interface UseDebugOptimizeDialogProps {
  // 状态
  selectedAiReply: SelectedAiReply | null
  setSelectedAiReply: (reply: SelectedAiReply | null) => void
  humanEvaluation: string
  setHumanEvaluation: (evaluation: string) => void
  aiReplyOptimizeStep: OptimizeStep
  setAiReplyOptimizeStep: (step: OptimizeStep) => void
  optimizedPromptTemplate: string
  setOptimizedPromptTemplate: (template: string) => void
  aiReplyOptimizeDialogOpen: boolean
  setAiReplyOptimizeDialogOpen: (open: boolean) => void

  // Refs
  abortControllerRef: React.MutableRefObject<AbortController | null>
  badcaseOptimizeStreamingRef: React.MutableRefObject<string>

  // 数据
  optimizationSource: OptimizationSource
  promptMessages: PromptMessage[]
  setPromptMessages: React.Dispatch<React.SetStateAction<PromptMessage[]>>
  messageInputValues: { [key: string]: string }
  setMessageInputValues: React.Dispatch<React.SetStateAction<{ [key: string]: string }>>
  comparisonGroupsData: ComparisonGroupData[]
  setComparisonGroupsData: React.Dispatch<React.SetStateAction<ComparisonGroupData[]>>
  selectedModel: Model | null
  modelConfig: ModelConfig
  availableModels: Model[]

  // 辅助函数
  setSnackbar: (snackbar: { open: boolean; message: string; severity: 'success' | 'error' | 'warning' | 'info' }) => void
  handlePromptChange: (field: string, value: any) => void
  setHasUnsavedChanges: (hasChanges: boolean) => void
  triggerAutoSave: (data?: { promptMessages?: PromptMessage[] }) => void
}

// Hook 返回值接口
interface UseDebugOptimizeDialogReturn {
  performAiReplyOptimization: (isRetry: boolean) => Promise<void>
  handleStartAiReplyOptimization: () => Promise<void>
  handleRetryAiReplyOptimization: () => Promise<void>
  handleStopDebugOptimization: () => void
  handleDebugOptimizeClose: () => void
  handleDebugOptimizeStepChange: (step: 'input' | 'optimizing' | 'result') => void
  handleDebugOptimizedTemplateChange: (template: string) => void
  handleDebugHumanEvaluationChange: (evaluation: string) => void
  handleAdoptOptimizedPrompt: () => void
}

export const useDebugOptimizeDialog = (props: UseDebugOptimizeDialogProps): UseDebugOptimizeDialogReturn => {
  const { t } = useTranslation()

  const {
    selectedAiReply,
    setSelectedAiReply,
    humanEvaluation,
    setHumanEvaluation,
    aiReplyOptimizeStep,
    setAiReplyOptimizeStep,
    optimizedPromptTemplate,
    setOptimizedPromptTemplate,
    aiReplyOptimizeDialogOpen,
    setAiReplyOptimizeDialogOpen,
    abortControllerRef,
    badcaseOptimizeStreamingRef,
    optimizationSource,
    promptMessages,
    setPromptMessages,
    messageInputValues,
    setMessageInputValues,
    comparisonGroupsData,
    setComparisonGroupsData,
    selectedModel,
    modelConfig,
    availableModels,
    setSnackbar,
    handlePromptChange,
    setHasUnsavedChanges,
    triggerAutoSave,
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

  // 获取第一个system消息的内容
  const getFirstSystemMessageCallback = useCallback(() => {
    return getFirstSystemMessage(optimizationSource, promptMessages, comparisonGroupsDataRef.current)
  }, [optimizationSource, promptMessages])

  // 执行AI回复优化
  const performAiReplyOptimization = useCallback(
    async (isRetry: boolean = false) => {
      if (!selectedAiReply || !humanEvaluation.trim()) return

      // 取消之前的请求（如果存在）
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }

      // 创建新的AbortController
      abortControllerRef.current = new AbortController()

      setAiReplyOptimizeStep('optimizing')
      if (isRetry) {
        // 重试时清空之前的结果
        setOptimizedPromptTemplate('')
      } else {
        // 首次优化时清空之前的结果
        setOptimizedPromptTemplate('')
      }

      try {
        // 获取原始Prompt模板（第一个system类型的消息）
        const systemPrompt = getFirstSystemMessageCallback()

        // 从 ref 获取最新的模型信息，而不是依赖闭包中的值
        const currentSelectedModelFromRef = selectedModelRef.current
        const latestModelConfigFromRef = modelConfigRef.current

        // 根据优化源获取对应的模型配置
        let currentSelectedModel = currentSelectedModelFromRef
        let currentModelConfig = latestModelConfigFromRef

        // 获取最新的对比组数据
        const latestGroupsData = comparisonGroupsDataRef.current

        // 根据 optimizationSource 获取对应组的模型配置（基准组和对照组的逻辑相同，只是组号不同）
        if (optimizationSource.type === 'base' || (optimizationSource.type === 'control' && optimizationSource.groupId !== undefined)) {
          const groupId = optimizationSource.type === 'base' ? 0 : optimizationSource.groupId!
          const group = latestGroupsData.find(g => g.id === groupId)
          if (group?.modelConfig) {
            currentModelConfig = group.modelConfig
            currentSelectedModel = findModelByIdAndFrom(group.modelConfig.model, group.modelConfig.model_from, availableModels) || currentSelectedModelFromRef
          }
        }
        // 如果 optimizationSource.type === 'main'，使用主页面选中的模型（已在上面初始化）

        // 如果没有选中的模型，尝试从modelConfig中查找
        if (!currentSelectedModel) {
          currentSelectedModel = findModelByIdAndFrom(currentModelConfig.model, currentModelConfig.model_from, availableModels)
        }

        // 如果还是找不到选中的模型，使用第一个可用模型
        if (!currentSelectedModel && availableModels.length > 0) {
          currentSelectedModel = availableModels[0]
        }

        if (!currentSelectedModel) {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.noModelConfigured'), severity: 'error' })
          setAiReplyOptimizeStep('input')
          return
        }

        // 构建对话历史的JSON字符串
        const dialogHistory = [
          {
            role: 'user',
            content: selectedAiReply.userQuestion,
          },
          {
            role: 'assistant',
            content: selectedAiReply.aiResponse,
          },
        ]
        const queryJson = JSON.stringify([dialogHistory])

        // 构建请求参数 - 使用获取到的模型配置
        const modelInfo = buildModelInfo(currentSelectedModel, currentModelConfig)

        const request: OptimizeBadcaseRequest = {
          modelInfo,
          prompt: systemPrompt,
          badcases: [
            {
              query: queryJson,
              label: humanEvaluation,
            },
          ],
          stream: true,
          templateInfo: {},
        }

        // 调用badcase优化API
        // 重置badcase优化流式引用
        badcaseOptimizeStreamingRef.current = ''

        await FeedbackOptService.optimizeBadcase(
          request,
          data => {
            // 使用类似快捷优化的流式处理逻辑
            badcaseOptimizeStreamingRef.current += data
            setOptimizedPromptTemplate(badcaseOptimizeStreamingRef.current)
          },
          error => {
            // 错误处理
            const errorMessage = isRetry ? error || t('components.prompts.promptEditPage.reoptimizeFailed') : error || t('components.prompts.promptEditPage.badcaseOptimizationFailed')
            setSnackbar({ open: true, message: errorMessage, severity: 'error' })
            setAiReplyOptimizeStep('input')
          },
          () => {
            // 完成处理
            setAiReplyOptimizeStep('result')
            // 确保最终结果使用流式累积的完整内容
            setOptimizedPromptTemplate(badcaseOptimizeStreamingRef.current)
            // 清理AbortController
            if (abortControllerRef.current) {
              abortControllerRef.current = null
            }
          },
          abortControllerRef.current || undefined,
        )
      } catch (error) {
        // 检查是否是用户主动取消的请求
        if (error instanceof Error && error.name === 'AbortError') {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.debugOptimizeRequestCancelled'), severity: 'info' })
        } else {
          console.error('根据调试结果优化提示词失败:', error)
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.optimizePromptFromDebugFailed'), severity: 'error' })
        }
        setAiReplyOptimizeStep('input')
        // 清理AbortController
        if (abortControllerRef.current) {
          abortControllerRef.current = null
        }
      }
    },
    [
      selectedAiReply,
      humanEvaluation,
      abortControllerRef,
      setAiReplyOptimizeStep,
      setOptimizedPromptTemplate,
      getFirstSystemMessageCallback,
      optimizationSource,
      availableModels,
      badcaseOptimizeStreamingRef,
      setSnackbar,
      t,
    ],
  )

  // 开始AI回复优化
  const handleStartAiReplyOptimization = useCallback(async () => {
    await performAiReplyOptimization(false)
  }, [performAiReplyOptimization])

  // 重新优化AI回复
  const handleRetryAiReplyOptimization = useCallback(async () => {
    await performAiReplyOptimization(true)
  }, [performAiReplyOptimization])

  // 停止调试优化
  const handleStopDebugOptimization = useCallback(() => {
    // 取消正在进行的流式请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    // 停止优化状态，回到输入状态
    setAiReplyOptimizeStep('input')

    // 将当前的流式内容设置为最终结果（如果有的话）
    const currentContent = badcaseOptimizeStreamingRef.current
    if (currentContent) {
      setOptimizedPromptTemplate(currentContent)
      // 切换到结果状态以显示当前内容
      setAiReplyOptimizeStep('result')
    }
  }, [abortControllerRef, badcaseOptimizeStreamingRef, setAiReplyOptimizeStep, setOptimizedPromptTemplate])

  // 关闭调试优化对话框
  const handleDebugOptimizeClose = useCallback(() => {
    setAiReplyOptimizeDialogOpen(false)
    setSelectedAiReply(null)
    setAiReplyOptimizeStep('input')
    setOptimizedPromptTemplate('')
    setHumanEvaluation('')
  }, [setAiReplyOptimizeDialogOpen, setSelectedAiReply, setAiReplyOptimizeStep, setOptimizedPromptTemplate, setHumanEvaluation])

  // 调试优化步骤变化
  const handleDebugOptimizeStepChange = useCallback(
    (step: 'input' | 'optimizing' | 'result') => {
      setAiReplyOptimizeStep(step)
    },
    [setAiReplyOptimizeStep],
  )

  // 优化后的模板变化
  const handleDebugOptimizedTemplateChange = useCallback(
    (template: string) => {
      setOptimizedPromptTemplate(template)
    },
    [setOptimizedPromptTemplate],
  )

  // 人工评估变化
  const handleDebugHumanEvaluationChange = useCallback(
    (evaluation: string) => {
      setHumanEvaluation(evaluation)
    },
    [setHumanEvaluation],
  )

  // 采纳优化后的Prompt模板
  const handleAdoptOptimizedPrompt = useCallback(() => {
    if (!optimizedPromptTemplate) return

    if (optimizationSource.type === 'main') {
      // 主页面模式：更新主页面的promptMessages
      const newMessages = [...promptMessages]
      const firstSystemIndex = newMessages.findIndex(msg => msg.role === 'system')

      if (firstSystemIndex !== -1 && newMessages[firstSystemIndex]) {
        // 更新第一个system消息的内容
        newMessages[firstSystemIndex] = {
          ...newMessages[firstSystemIndex],
          content: optimizedPromptTemplate,
        }

        // 同时更新messageInputValues以保持编辑状态同步
        setMessageInputValues(prev => ({
          ...prev,
          [newMessages[firstSystemIndex].id]: optimizedPromptTemplate,
        }))

        setPromptMessages(newMessages)

        // 更新组合后的prompt.content
        const combinedContent = newMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
        handlePromptChange('content', combinedContent)

        // 触发自动保存草稿
        setHasUnsavedChanges(true)
        triggerAutoSave({ promptMessages: newMessages })

        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.firstSystemPromptUpdated'), severity: 'success' })
      } else {
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.systemPromptNotFound'), severity: 'error' })
      }
    } else if (optimizationSource.type === 'base') {
      // 基准组模式：更新基准组的messages
      setComparisonGroupsData(prev =>
        prev.map(g => {
          if (g.id !== 0) return g

          const firstSystemIndex = g.messages.findIndex(msg => msg.role === 'system')
          if (firstSystemIndex !== -1 && g.messages[firstSystemIndex]) {
            const updatedMessages = g.messages.map((msg, index) => (index === firstSystemIndex ? { ...msg, content: optimizedPromptTemplate } : msg))

            return {
              ...g,
              messages: updatedMessages,
              messageInputValues: {
                ...g.messageInputValues,
                [g.messages[firstSystemIndex].id]: optimizedPromptTemplate,
              },
            }
          }
          return g
        }),
      )

      // 触发自动保存草稿（基准组不需要保存草稿，但保持一致性）
      setHasUnsavedChanges(true)

      // 使用 ref 获取最新的对比组数据
      const latestGroupsData = comparisonGroupsDataRef.current
      const baseGroup = latestGroupsData.find(g => g.id === 0)
      const hasSystemMessage = baseGroup?.messages.some(msg => msg.role === 'system')

      if (hasSystemMessage) {
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.baseGroupFirstSystemPromptUpdated'), severity: 'success' })
      } else {
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.baseGroupSystemPromptNotFound'), severity: 'error' })
      }
    } else if (optimizationSource.type === 'control' && optimizationSource.groupId) {
      // 对照组模式：更新指定对照组的messages
      const groupId = optimizationSource.groupId
      setComparisonGroupsData(prev =>
        prev.map(group => {
          if (group.id === groupId) {
            const newMessages = [...group.messages]
            const firstSystemIndex = newMessages.findIndex(msg => msg.role === 'system')

            if (firstSystemIndex !== -1 && newMessages[firstSystemIndex]) {
              // 更新第一个system消息的内容
              newMessages[firstSystemIndex] = {
                ...newMessages[firstSystemIndex],
                content: optimizedPromptTemplate,
              }

              // 同时更新messageInputValues以保持编辑状态同步
              const newMessageInputValues = {
                ...group.messageInputValues,
                [newMessages[firstSystemIndex].id]: optimizedPromptTemplate,
              }

              // 触发自动保存草稿（对照组不需要保存草稿，但保持一致性）
              setHasUnsavedChanges(true)

              setSnackbar({
                open: true,
                message: t('components.prompts.promptEditPage.controlGroupFirstSystemPromptUpdated', { groupId }),
                severity: 'success',
              })

              return {
                ...group,
                messages: newMessages,
                messageInputValues: newMessageInputValues,
              }
            } else {
              setSnackbar({
                open: true,
                message: t('components.prompts.promptEditPage.controlGroupSystemPromptNotFound', { groupId }),
                severity: 'error',
              })
              return group
            }
          }
          return group
        }),
      )
    }

    setAiReplyOptimizeDialogOpen(false)
    setSelectedAiReply(null)
  }, [
    optimizedPromptTemplate,
    optimizationSource,
    promptMessages,
    setMessageInputValues,
    setPromptMessages,
    handlePromptChange,
    setHasUnsavedChanges,
    triggerAutoSave,
    setSnackbar,
    t,
    comparisonGroupsData,
    setComparisonGroupsData,
    setAiReplyOptimizeDialogOpen,
    setSelectedAiReply,
  ])

  return {
    performAiReplyOptimization,
    handleStartAiReplyOptimization,
    handleRetryAiReplyOptimization,
    handleStopDebugOptimization,
    handleDebugOptimizeClose,
    handleDebugOptimizeStepChange,
    handleDebugOptimizedTemplateChange,
    handleDebugHumanEvaluationChange,
    handleAdoptOptimizedPrompt,
  }
}
