import { useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { FeedbackOptService } from '@test-agentstudio/api-client'
import type { OptimizationSource, OptimizationMode, PromptMessage, ComparisonGroupData, Model, ModelConfig } from '@/types/promptType'
import { buildModelInfo } from '@/utils/prompts/modelInfoBuilder'
import { findModelByIdAndFrom, checkValidModel } from '@/utils/prompts/promptEditPageUtils'

// Hook 参数接口
interface UseFeedbackOptimizeDialogProps {
  // 状态
  optimizationSource: OptimizationSource
  setOptimizationSource: React.Dispatch<React.SetStateAction<OptimizationSource>>
  currentOptimizationType: OptimizationMode | null
  setCurrentOptimizationType: (type: OptimizationMode | null) => void
  optimizeDialogOpen: boolean
  setOptimizeDialogOpen: (open: boolean) => void
  optimizeInput: string
  setOptimizeInput: (input: string) => void
  optimizedResult: string
  setOptimizedResult: (result: string) => void
  isOptimizing: boolean
  setIsOptimizing: (isOptimizing: boolean) => void
  selectedText: string
  setSelectedText: (text: string) => void
  selectionIndices: { start: number; end: number } | null
  setSelectionIndices: (indices: { start: number; end: number } | null) => void
  selectionPosition: { x: number; y: number } | null
  setSelectionPosition: (position: { x: number; y: number } | null) => void
  cursorPosition: { messageId: string; position: number } | null
  setCursorPosition: (position: { messageId: string; position: number } | null) => void
  setShowCursorOptimizeButton: (show: boolean) => void
  setCursorOptimizePosition: (position: { x: number; y: number } | null) => void
  regeneratePromptInput: string
  setRegeneratePromptInput: (input: string) => void
  regeneratePromptInputMessageId: string | undefined
  setRegeneratePromptInputMessageId: (messageId: string | undefined) => void
  lastOptimizeInput: string
  setLastOptimizeInput: (input: string) => void
  ignoreTextSelection: boolean
  setIgnoreTextSelection: (ignore: boolean) => void

  // Refs
  clickedOptimizationTypeRef: React.MutableRefObject<OptimizationMode | null>
  fullTextOptimizeMessageIdRef: React.MutableRefObject<string | undefined>
  lastOptimizationSourceMessageIdRef: React.MutableRefObject<string | undefined>
  selectedTextRef: React.MutableRefObject<string>
  selectionIndicesRef: React.MutableRefObject<{ start: number; end: number } | null>
  ignoreTextSelectionRef: React.MutableRefObject<boolean>
  lastClickedSelectOptimizeButtonRef: React.MutableRefObject<number>
  abortControllerRef: React.MutableRefObject<AbortController | null>
  feedbackOptimizeStreamingRef: React.MutableRefObject<string>
  justClickedOutsideRef: React.MutableRefObject<boolean>
  cursorOptimizeTimer: React.MutableRefObject<any>

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
  getPromptContentBySource: (messageId?: string, optimizationSourceOverride?: OptimizationSource) => string
  calculateSelectionIndices: (selectedText: string, promptContent: string) => { start: number; end: number } | null
  setSnackbar: (snackbar: { open: boolean; message: string; severity: 'success' | 'error' | 'warning' | 'info' }) => void
  setPromptMessages: React.Dispatch<React.SetStateAction<PromptMessage[]>>
  setMessageInputValues: React.Dispatch<React.SetStateAction<{ [key: string]: string }>>
  setComparisonGroupsData: React.Dispatch<React.SetStateAction<ComparisonGroupData[]>>
  triggerAutoSave: (data?: { promptMessages?: PromptMessage[] }) => void
}

// Hook 返回值接口
interface UseFeedbackOptimizeDialogReturn {
  handleOptimizeDialogOpen: (optimizationSourceOverride?: OptimizationSource) => void
  handleOptimizeRequest: () => Promise<void>
  handleApplyOptimization: () => void
  closeOptimizationDialog: () => void
  handleStopFeedbackOptimization: () => void
}

export const useFeedbackOptimizeDialog = (props: UseFeedbackOptimizeDialogProps): UseFeedbackOptimizeDialogReturn => {
  const { t } = useTranslation()

  const {
    optimizationSource,
    setOptimizationSource,
    currentOptimizationType,
    setCurrentOptimizationType,
    setOptimizeDialogOpen,
    optimizeInput,
    setOptimizeInput,
    optimizedResult,
    setOptimizedResult,
    isOptimizing,
    setIsOptimizing,
    selectedText,
    setSelectedText,
    selectionIndices,
    setSelectionIndices,
    selectionPosition,
    setSelectionPosition,
    cursorPosition,
    setCursorPosition,
    setShowCursorOptimizeButton,
    setCursorOptimizePosition,
    regeneratePromptInput,
    setRegeneratePromptInput,
    regeneratePromptInputMessageId,
    setRegeneratePromptInputMessageId,
    lastOptimizeInput,
    setLastOptimizeInput,
    ignoreTextSelection,
    setIgnoreTextSelection,
    clickedOptimizationTypeRef,
    fullTextOptimizeMessageIdRef,
    lastOptimizationSourceMessageIdRef,
    selectedTextRef,
    selectionIndicesRef,
    ignoreTextSelectionRef,
    lastClickedSelectOptimizeButtonRef,
    abortControllerRef,
    feedbackOptimizeStreamingRef,
    justClickedOutsideRef,
    cursorOptimizeTimer,
    promptMessages,
    messageInputValues,
    comparisonGroupsData,
    selectedModel,
    modelConfig,
    availableModels,
    workspaceId,
    getPromptContentBySource,
    calculateSelectionIndices,
    setSnackbar,
    setPromptMessages,
    setMessageInputValues,
    setComparisonGroupsData,
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

  // 重置优化对话框状态
  const resetOptimizationDialog = useCallback(() => {
    setOptimizeDialogOpen(false)
    setOptimizedResult('')
    setOptimizeInput('')
    setLastOptimizeInput('')
    setSelectedText('')
    setSelectionPosition(null)
    setSelectionIndices(null)
    setShowCursorOptimizeButton(false)
    setCursorPosition(null)
    setCursorOptimizePosition(null)
    setCurrentOptimizationType('general')
    setRegeneratePromptInput('') // 重置重新生成提示词输入变量
    setRegeneratePromptInputMessageId(undefined) // 重置messageId

    // 恢复忽略标记，确保对话框关闭后可以正常处理光标位置变化事件
    ignoreTextSelectionRef.current = false
    setIgnoreTextSelection(false)
    justClickedOutsideRef.current = false

    // 清除定时器
    if (cursorOptimizeTimer.current) {
      clearTimeout(cursorOptimizeTimer.current)
    }
  }, [
    setOptimizeDialogOpen,
    setOptimizedResult,
    setOptimizeInput,
    setLastOptimizeInput,
    setSelectedText,
    setSelectionPosition,
    setSelectionIndices,
    setShowCursorOptimizeButton,
    setCursorPosition,
    setCursorOptimizePosition,
    setCurrentOptimizationType,
    setRegeneratePromptInput,
    setRegeneratePromptInputMessageId,
    ignoreTextSelectionRef,
    setIgnoreTextSelection,
    justClickedOutsideRef,
    cursorOptimizeTimer,
  ])

  const handleOptimizeDialogOpen = useCallback(
    (optimizationSourceOverride?: OptimizationSource) => {
      // 确定当前使用的 optimizationSource（优先使用 override）
      const currentSource = optimizationSourceOverride || optimizationSource

      // 根据优化源获取对应的模型配置
      let currentModelConfig = modelConfigRef.current
      const latestGroupsData = comparisonGroupsDataRef.current

      // 根据 optimizationSource 获取对应组的模型配置（基准组和对照组的逻辑相同，只是组号不同）
      if (currentSource.type === 'base' || (currentSource.type === 'control' && currentSource.groupId !== undefined)) {
        const groupId = currentSource.type === 'base' ? 0 : currentSource.groupId!
        const group = latestGroupsData.find(g => g.id === groupId)
        if (group?.modelConfig) {
          currentModelConfig = group.modelConfig
        }
      }

      // 检查是否配置了有效的模型
      const currentSelectedModel = selectedModelRef.current
      if (!checkValidModel(currentSelectedModel, currentModelConfig, availableModels)) {
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.noModelConfigured'), severity: 'error' })
        return
      }

      // 确定当前使用的 optimizationSource（优先使用 override）
      let currentOptimizationSource = optimizationSourceOverride || optimizationSource

      // 获取用户点击的按钮类型（最高优先级，直接使用按钮点击时设置的标记）
      const clickedType = clickedOptimizationTypeRef.current
      // 使用完后立即清除标记，避免影响后续判断
      clickedOptimizationTypeRef.current = null

      // 全文反馈优化
      if (clickedType === 'general') {
        const currentMessageId = currentOptimizationSource.messageId
        if (currentMessageId) {
          fullTextOptimizeMessageIdRef.current = currentMessageId
        }

        // 更新 optimizationSource
        setOptimizationSource(prev => {
          if (prev.messageId === currentMessageId && prev.type === currentOptimizationSource.type && prev.groupId === currentOptimizationSource.groupId) {
            return prev
          }
          return {
            ...prev,
            type: currentOptimizationSource.type,
            groupId: currentOptimizationSource.groupId,
            messageId: currentMessageId,
          }
        })

        setCurrentOptimizationType('general')

        // 清除选中文本
        setSelectedText('')
        setSelectionIndices(null)
        selectedTextRef.current = ''
        selectionIndicesRef.current = null
        const selection = window.getSelection()
        if (selection) {
          selection.removeAllRanges()
        }

        // 如果 type 或 groupId 不同，更新状态
        if (currentOptimizationSource.type !== optimizationSource.type || currentOptimizationSource.groupId !== optimizationSource.groupId) {
          setOptimizationSource(currentOptimizationSource)
        }

        // 获取目标提示词内容，如果为空则提示用户并返回
        const targetPromptContent = getPromptContentBySource(currentMessageId, currentOptimizationSource)
        if (!targetPromptContent || targetPromptContent.trim() === '') {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.targetPromptEmpty'), severity: 'warning' })
          return
        }

        // 初始化重新生成提示词输入变量
        if (currentMessageId && (!regeneratePromptInput || regeneratePromptInputMessageId !== currentMessageId)) {
          const originalContent = getPromptContentBySource(currentMessageId, currentOptimizationSource)
          setRegeneratePromptInput(originalContent)
          setRegeneratePromptInputMessageId(currentMessageId)
        }

        setOptimizeDialogOpen(true)
        return
      }

      // 初始化重新生成提示词输入变量的公共函数
      const initializeRegenerateInput = (messageId?: string) => {
        if (messageId && (!regeneratePromptInput || regeneratePromptInputMessageId !== messageId)) {
          const originalContent = getPromptContentBySource(messageId, currentOptimizationSource)
          setRegeneratePromptInput(originalContent)
          setRegeneratePromptInputMessageId(messageId)
        }
      }

      // 设置忽略文本选中标记
      const setIgnoreFlag = () => {
        ignoreTextSelectionRef.current = true
        setIgnoreTextSelection(true)
      }

      // 选中反馈优化
      if (clickedType === 'select') {
        lastClickedSelectOptimizeButtonRef.current = Date.now()

        // 恢复选中文本（优先级：ref > state > window.getSelection()）
        let textToUse = ''
        if (selectedTextRef.current?.trim()) {
          textToUse = selectedTextRef.current.trim()
        } else if (selectedText?.trim()) {
          textToUse = selectedText.trim()
        } else {
          const selection = window.getSelection()
          textToUse = selection ? selection.toString().trim() : ''
        }

        if (textToUse) {
          setSelectedText(textToUse)
          selectedTextRef.current = textToUse
          const messageId = lastOptimizationSourceMessageIdRef.current || currentOptimizationSource.messageId || optimizationSource.messageId
          const promptContent = getPromptContentBySource(messageId, currentOptimizationSource)
          if (promptContent) {
            const indices = calculateSelectionIndices(textToUse, promptContent)
            if (indices) {
              setSelectionIndices(indices)
              selectionIndicesRef.current = indices
            }
          }
        }

        // 如果是选中反馈优化，优先使用 ref 中的 messageId（解决状态更新异步问题）
        if (lastOptimizationSourceMessageIdRef.current && !currentOptimizationSource.messageId) {
          currentOptimizationSource = { ...currentOptimizationSource, messageId: lastOptimizationSourceMessageIdRef.current }
        }

        const currentMessageId = lastOptimizationSourceMessageIdRef.current || currentOptimizationSource.messageId || optimizationSource.messageId
        if (currentMessageId && !currentOptimizationSource.messageId && !optimizationSource.messageId) {
          setOptimizationSource(prev => ({ ...prev, messageId: currentMessageId }))
        }

        // 如果 type 或 groupId 不同，更新状态
        if (currentOptimizationSource.type !== optimizationSource.type || currentOptimizationSource.groupId !== optimizationSource.groupId) {
          setOptimizationSource(currentOptimizationSource)
        }

        // 获取目标提示词内容，如果为空则提示用户并返回
        const targetPromptContent = getPromptContentBySource(currentMessageId, currentOptimizationSource)
        if (!targetPromptContent || targetPromptContent.trim() === '') {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.targetPromptEmpty'), severity: 'warning' })
          return
        }

        initializeRegenerateInput(currentMessageId)
        setCurrentOptimizationType('select')
        setIgnoreFlag()
        setOptimizeDialogOpen(true)
        return
      }

      // 插入反馈优化
      if (clickedType === 'insert') {
        // 如果是插入反馈优化，且没有 messageId，从 cursorPosition 中获取（解决状态更新异步问题）
        if (!currentOptimizationSource.messageId && cursorPosition?.messageId) {
          currentOptimizationSource = { ...currentOptimizationSource, messageId: cursorPosition.messageId }
        }

        // 确保使用正确的 messageId（优先使用 override，然后使用 currentOptimizationSource，最后使用 cursorPosition）
        const finalMessageId = optimizationSourceOverride?.messageId || currentOptimizationSource.messageId || cursorPosition?.messageId
        if (finalMessageId && (!currentOptimizationSource.messageId || currentOptimizationSource.messageId !== finalMessageId)) {
          setOptimizationSource(prev => ({ ...prev, messageId: finalMessageId }))
          currentOptimizationSource = { ...currentOptimizationSource, messageId: finalMessageId }
        }

        // 如果 type 或 groupId 不同，更新状态
        if (currentOptimizationSource.type !== optimizationSource.type || currentOptimizationSource.groupId !== optimizationSource.groupId) {
          setOptimizationSource(currentOptimizationSource)
        }

        // 获取目标提示词内容，如果为空则提示用户并返回
        const targetPromptContent = getPromptContentBySource(finalMessageId, currentOptimizationSource)
        if (!targetPromptContent || targetPromptContent.trim() === '') {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.targetPromptEmpty'), severity: 'warning' })
          return
        }

        initializeRegenerateInput(finalMessageId)
        setCurrentOptimizationType('insert')
        setIgnoreFlag()
        setOptimizeDialogOpen(true)
        return
      }

      // 如果无法确定优化类型，提示错误
      console.warn('🔍 [OPTIMIZE-DIALOG-OPEN] 无法确定优化类型', {
        clickedType,
        optimizationSourceOverride,
      })
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.optimizationTypeNotSet'), severity: 'error' })
    },
    [
      optimizationSource,
      setOptimizationSource,
      currentOptimizationType,
      setCurrentOptimizationType,
      setOptimizeDialogOpen,
      selectedText,
      setSelectedText,
      setSelectionIndices,
      cursorPosition,
      regeneratePromptInput,
      setRegeneratePromptInput,
      regeneratePromptInputMessageId,
      setRegeneratePromptInputMessageId,
      setIgnoreTextSelection,
      clickedOptimizationTypeRef,
      fullTextOptimizeMessageIdRef,
      lastOptimizationSourceMessageIdRef,
      selectedTextRef,
      selectionIndicesRef,
      ignoreTextSelectionRef,
      lastClickedSelectOptimizeButtonRef,
      getPromptContentBySource,
      calculateSelectionIndices,
      setSnackbar,
      t,
    ],
  )

  const handleOptimizeRequest = useCallback(async () => {
    // 修复：优先使用ref中保存的messageId（全文反馈优化时保存的），其次使用optimizationSource.messageId
    const preservedMessageId = fullTextOptimizeMessageIdRef.current || optimizationSource.messageId

    // 使用当前输入或最后保存的输入
    const inputToUse = optimizeInput.trim() || lastOptimizeInput

    if (!inputToUse) {
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.enterOptimizationRequirement'), severity: 'info' })
      return
    }

    // 取消之前的请求（如果存在）
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    // 创建新的AbortController
    abortControllerRef.current = new AbortController()

    // 在清空之前，先保存上一次的优化结果（如果存在）
    const previousOptimizedResult = optimizedResult && optimizedResult.trim() ? optimizedResult : null

    setIsOptimizing(true)
    setOptimizedResult('') // 清空之前的结果

    try {
      // 保存当前使用的优化需求
      if (optimizeInput.trim()) {
        setLastOptimizeInput(optimizeInput.trim())
      }

      // 获取当前的提示词内容
      // 区分"继续优化"和"重新生成"：
      // - 继续优化（optimizeInput 不为空）：使用上一次的优化结果作为输入，并将重新生成提示词输入设置为继续优化的输入
      // - 重新生成（optimizeInput 为空但 lastOptimizeInput 不为空）：使用重新生成提示词输入变量
      // - 第一次优化（optimizeInput 不为空且 previousOptimizedResult 为空）：使用原始内容
      let promptContent = ''
      const isContinueOptimize = optimizeInput.trim() !== '' && previousOptimizedResult !== null // 判断是否是继续优化（有新的输入且有上一次的结果）
      const isRegenerate = optimizeInput.trim() === '' && lastOptimizeInput !== '' // 判断是否是重新生成（没有新的输入但有保存的输入）

      if (isContinueOptimize) {
        // 继续优化：根据优化类型决定使用什么内容
        // - 全文反馈优化（general）：使用上一次的优化结果作为输入
        // - 插入反馈优化（insert）和选中反馈优化（select）：使用原始内容
        if (currentOptimizationType === 'general') {
          // 全文反馈优化：使用上一次的优化结果作为输入
          promptContent = previousOptimizedResult
          // 将重新生成提示词输入设置为继续优化的输入（也就是上一次的优化结果）
          setRegeneratePromptInput(previousOptimizedResult)
          // 更新messageId，确保重新生成时使用正确的消息
          const messageIdForRegenerate = preservedMessageId || optimizationSource.messageId
          setRegeneratePromptInputMessageId(messageIdForRegenerate)
        } else {
          // 插入反馈优化和选中反馈优化：使用原始内容
          // 优先使用 preservedMessageId（全文优化）或 lastOptimizationSourceMessageIdRef（选中优化），最后回退到 optimizationSource.messageId
          let currentMessageId: string | undefined
          if (currentOptimizationType === 'insert' && cursorPosition?.messageId) {
            // 插入优化：优先使用光标位置的 messageId（最准确）
            currentMessageId = cursorPosition.messageId
          } else if (currentOptimizationType === 'select') {
            // 选中优化：优先使用 ref 中保存的 messageId（文本选中时保存的）
            currentMessageId = lastOptimizationSourceMessageIdRef.current || optimizationSource.messageId
          } else {
            // 其他情况：使用 preservedMessageId 或 optimizationSource.messageId
            currentMessageId = preservedMessageId || lastOptimizationSourceMessageIdRef.current || optimizationSource.messageId
          }

          // 如果找到了 messageId，更新 optimizationSource 和 ref，确保状态一致
          if (currentMessageId && lastOptimizationSourceMessageIdRef.current !== currentMessageId) {
            lastOptimizationSourceMessageIdRef.current = currentMessageId
            setOptimizationSource(prev => ({ ...prev, messageId: currentMessageId }))
          }

          // 使用原始内容
          promptContent = getPromptContentBySource(currentMessageId, optimizationSource)

          // 初始化重新生成提示词输入变量为原始内容
          if (!regeneratePromptInput || regeneratePromptInputMessageId !== currentMessageId) {
            setRegeneratePromptInput(promptContent)
            setRegeneratePromptInputMessageId(currentMessageId)
          }
        }
      } else if (isRegenerate) {
        // 重新生成：使用重新生成提示词输入变量
        if (regeneratePromptInput) {
          promptContent = regeneratePromptInput
        } else {
          // 如果重新生成提示词输入变量为空，使用原始内容并初始化它
          // 修复：使用保存的messageId构建优化源，确保messageId不会丢失
          // 优先使用 preservedMessageId（全文优化）或 lastOptimizationSourceMessageIdRef（选中优化），最后回退到 optimizationSource.messageId
          const messageIdForRegenerate = preservedMessageId || lastOptimizationSourceMessageIdRef.current || optimizationSource.messageId
          promptContent = getPromptContentBySource(messageIdForRegenerate)
          setRegeneratePromptInput(promptContent)
          setRegeneratePromptInputMessageId(preservedMessageId || optimizationSource.messageId)
        }
      } else {
        // 第一次优化：使用原始内容，并初始化重新生成提示词输入变量
        // 修复：优先使用保存的messageId（如果存在），避免状态更新异步导致messageId丢失
        // 确保使用正确的 messageId：
        // 1. 对于插入优化：优先使用 cursorPosition.messageId（最准确）
        // 2. 对于全文优化：使用 preservedMessageId（从 fullTextOptimizeMessageIdRef）
        // 3. 对于选中优化：优先使用 lastOptimizationSourceMessageIdRef（文本选中时保存的）
        // 4. 最后回退到 optimizationSource.messageId
        let currentMessageId: string | undefined
        if (currentOptimizationType === 'insert' && cursorPosition?.messageId) {
          // 插入优化：优先使用光标位置的 messageId（最准确）
          currentMessageId = cursorPosition.messageId
        } else if (currentOptimizationType === 'general' && preservedMessageId) {
          // 全文优化：使用 preservedMessageId（从 fullTextOptimizeMessageIdRef）
          currentMessageId = preservedMessageId
        } else if (currentOptimizationType === 'select') {
          // 选中优化：优先使用 ref 中保存的 messageId（文本选中时保存的）
          currentMessageId = lastOptimizationSourceMessageIdRef.current || optimizationSource.messageId
        } else {
          // 其他情况：使用 preservedMessageId 或 optimizationSource.messageId
          currentMessageId = preservedMessageId || optimizationSource.messageId
        }

        // 如果找到了 messageId，更新 optimizationSource 和 ref，确保状态一致
        if (currentMessageId && lastOptimizationSourceMessageIdRef.current !== currentMessageId) {
          lastOptimizationSourceMessageIdRef.current = currentMessageId
          setOptimizationSource(prev => ({ ...prev, messageId: currentMessageId }))
        }

        // 使用保存的messageId获取内容，传递 optimizationSource 确保在对比模式下能正确获取对应组的内容
        promptContent = getPromptContentBySource(currentMessageId, optimizationSource)
        // 初始化重新生成提示词输入变量为原始内容
        if (!regeneratePromptInput || regeneratePromptInputMessageId !== currentMessageId) {
          setRegeneratePromptInput(promptContent)
          setRegeneratePromptInputMessageId(currentMessageId)
        }
      }

      // 从 ref 获取最新的模型信息，而不是依赖闭包中的值
      const currentSelectedModelFromRef = selectedModelRef.current
      const latestModelConfigFromRef = modelConfigRef.current

      // 根据优化源获取对应的模型配置
      let currentSelectedModel = currentSelectedModelFromRef
      let currentModelConfig = latestModelConfigFromRef

      // 获取最新的对比组数据
      const latestGroupsData = comparisonGroupsDataRef.current

      // 根据 optimizationSource 获取对应组的模型配置
      if (optimizationSource.type === 'base') {
        const baseGroupConfig = latestGroupsData.find(g => g.id === 0)?.modelConfig
        if (baseGroupConfig) {
          currentModelConfig = baseGroupConfig
          currentSelectedModel = findModelByIdAndFrom(baseGroupConfig.model, baseGroupConfig.model_from, availableModels) || currentSelectedModelFromRef
        }
      } else if (optimizationSource.type === 'control' && optimizationSource.groupId !== undefined) {
        const group = latestGroupsData.find(g => g.id === optimizationSource.groupId)
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
        setIsOptimizing(false)
        return
      }

      // 构建基础请求参数 - 使用获取到的模型配置
      const modelInfo = buildModelInfo(currentSelectedModel, currentModelConfig)

      const baseRequest = {
        modelInfo,
        prompt: promptContent,
        feedback: inputToUse,
        stream: true,
        templateInfo: {},
      }

      // 根据当前优化类型调用相应的API方法
      // 重置反馈优化流式引用
      feedbackOptimizeStreamingRef.current = ''

      const handleData = (data: string) => {
        // 使用类似快捷优化的流式处理逻辑
        feedbackOptimizeStreamingRef.current += data

        // 实时更新显示的优化结果
        setOptimizedResult(feedbackOptimizeStreamingRef.current)
      }

      const handleError = (error: string) => {
        setSnackbar({ open: true, message: error || t('components.prompts.promptEditPage.optimizationFailed'), severity: 'error' })
      }

      const handleComplete = () => {
        setOptimizeInput('') // 清空输入框，准备下一次优化
        // 确保最终结果使用流式累积的完整内容
        setOptimizedResult(feedbackOptimizeStreamingRef.current)
        // 清理AbortController
        if (abortControllerRef.current) {
          abortControllerRef.current = null
        }
      }

      // 根据优化类型调用不同的方法
      if (!currentOptimizationType) {
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.optimizationTypeNotSet'), severity: 'error' })
        setIsOptimizing(false)
        return
      }

      switch (currentOptimizationType) {
        case 'general':
          // 场景1：反馈优化 - 不传递位置参数
          await FeedbackOptService.optimizeFeedback(
            { ...baseRequest, mode: 'general' },
            workspaceId,
            handleData,
            handleError,
            handleComplete,
            abortControllerRef.current || undefined,
          )
          break

        case 'insert':
          // 场景2：插入优化 - 只传递插入位置
          if (cursorPosition) {
            if (!promptContent || promptContent.trim() === '') {
              const messageIdToUse = cursorPosition.messageId || optimizationSource.messageId
              console.error('❌ [INSERT-OPT] 提示词内容为空', {
                messageIdToUse,
                optimizationSource,
                cursorPosition,
                promptContent,
              })
              setSnackbar({ open: true, message: t('components.prompts.promptEditPage.targetPromptEmpty'), severity: 'error' })
              setIsOptimizing(false)
              return
            }
            await FeedbackOptService.optimizeFeedback(
              { ...baseRequest, mode: 'insert', start_pos: cursorPosition.position },
              workspaceId,
              handleData,
              handleError,
              handleComplete,
              abortControllerRef.current || undefined,
            )
          } else {
            setSnackbar({ open: true, message: t('components.prompts.promptEditPage.cursorPositionNotFoundInsert'), severity: 'error' })
            setIsOptimizing(false)
            return
          }
          break

        case 'select':
          // 场景3：选中优化 - 传递选中位置参数

          if (selectedText && selectionIndices) {
            // 优先使用保存的 messageId（从 ref 或 optimizationSource）
            const messageIdToUse = lastOptimizationSourceMessageIdRef.current || optimizationSource.messageId
            // 使用统一的内容获取函数，确保使用正确的 messageId 和 optimizationSource（对比模式下需要正确的组信息）
            const currentPromptContent = getPromptContentBySource(messageIdToUse, optimizationSource)

            // 改进的内容验证逻辑：支持多种匹配方式
            const validateSelectedContent = (text: string, content: string) => {
              // 1. 直接匹配
              if (content.includes(text)) {
                return { isValid: true, method: 'exact' }
              }

              // 2. 去除首尾空白后匹配
              const trimmedText = text.trim()
              const trimmedContent = content.trim()
              if (trimmedContent.includes(trimmedText)) {
                return { isValid: true, method: 'trimmed', adjustedText: trimmedText }
              }

              // 3. 标准化换行符后匹配
              const normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
              const normalizedContent = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
              if (normalizedContent.includes(normalizedText)) {
                return { isValid: true, method: 'normalized', adjustedText: normalizedText }
              }

              // 4. 同时去除空白和标准化换行符
              const fullyNormalizedText = normalizedText.trim()
              const fullyNormalizedContent = normalizedContent.trim()
              if (fullyNormalizedContent.includes(fullyNormalizedText)) {
                return { isValid: true, method: 'fully_normalized', adjustedText: fullyNormalizedText }
              }

              return { isValid: false, method: 'none' }
            }

            const validation = validateSelectedContent(selectedText, currentPromptContent)

            if (validation.isValid) {
              // 使用调整后的文本重新计算选中位置
              const textToUse = validation.adjustedText || selectedText
              const updatedIndices = calculateSelectionIndices(textToUse, currentPromptContent)

              if (updatedIndices) {
                await FeedbackOptService.optimizeFeedback(
                  { ...baseRequest, mode: 'select', start_pos: updatedIndices.start, end_pos: updatedIndices.end },
                  workspaceId,
                  handleData,
                  handleError,
                  handleComplete,
                  abortControllerRef.current || undefined,
                )
              } else {
                setSnackbar({ open: true, message: t('components.prompts.promptEditPage.selectedPositionNotDetermined'), severity: 'error' })
                setIsOptimizing(false)
                return
              }
            } else {
              setSnackbar({ open: true, message: t('components.prompts.promptEditPage.selectedContentChanged'), severity: 'error' })
              setIsOptimizing(false)
              return
            }
          } else {
            const errorMsg = !selectedText
              ? t('components.prompts.promptEditPage.selectedContentNotFound')
              : t('components.prompts.promptEditPage.selectedPositionNotDetermined')
            console.error('🔍 [SELECT-OPT] 选中优化失败:', errorMsg, {
              selectedText: selectedText,
              selectionIndices: selectionIndices,
            })
            setSnackbar({
              open: true,
              message: t('components.prompts.promptEditPage.selectOptimizationFailedWithReason', { reason: errorMsg }),
              severity: 'error',
            })
            setIsOptimizing(false)
            return
          }
          break

        default:
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.unknownOptimizationType'), severity: 'error' })
          setIsOptimizing(false)
          return
      }
    } catch (error) {
      // 检查是否是用户主动取消的请求
      if (error instanceof Error && error.name === 'AbortError') {
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.feedbackOptimizeRequestCancelled'), severity: 'info' })
      } else {
        console.error('优化失败:', error)
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.optimizationFailed'), severity: 'error' })
      }
    } finally {
      setIsOptimizing(false)
      // 清理AbortController
      if (abortControllerRef.current) {
        abortControllerRef.current = null
      }
    }
  }, [
    fullTextOptimizeMessageIdRef,
    optimizationSource,
    optimizeInput,
    lastOptimizeInput,
    setSnackbar,
    abortControllerRef,
    optimizedResult,
    setIsOptimizing,
    setOptimizedResult,
    setLastOptimizeInput,
    setRegeneratePromptInput,
    setRegeneratePromptInputMessageId,
    currentOptimizationType,
    cursorPosition,
    lastOptimizationSourceMessageIdRef,
    setOptimizationSource,
    getPromptContentBySource,
    optimizationSource,
    availableModels,
    feedbackOptimizeStreamingRef,
    setOptimizeInput,
    selectedText,
    selectionIndices,
    calculateSelectionIndices,
    t,
  ])

  // 场景1：反馈优化应用逻辑 - 完全替换提示词内容
  const handleFeedbackOptimizationApply = useCallback(() => {
    // 优先使用 optimizationSource.messageId，如果没有则使用 fullTextOptimizeMessageIdRef（全文反馈优化时保存的）
    const messageIdToUse = optimizationSource.messageId || fullTextOptimizeMessageIdRef.current
    if (optimizationSource.type === 'main') {
      // 主页面：如果有messageId，使用指定的消息；否则使用第一个system消息
      const targetMessage = messageIdToUse ? promptMessages.find(msg => msg.id === messageIdToUse) : promptMessages.find(msg => msg.role === 'system')

      if (targetMessage) {
        const newMessages = promptMessages.map(msg => {
          if (msg.id === targetMessage.id) {
            return { ...msg, content: optimizedResult }
          }
          return msg
        })
        setPromptMessages(newMessages)
        setMessageInputValues(prev => ({
          ...prev,
          [targetMessage.id]: optimizedResult,
        }))
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.promptFullyReplaced'), severity: 'success' })

        // 使用防抖机制保存草稿
        triggerAutoSave({ promptMessages: newMessages })
      }
    } else if (optimizationSource.type === 'base' || (optimizationSource.type === 'control' && optimizationSource.groupId)) {
      // 基准组和对照组：统一处理逻辑，基准组组号为0，对照组组号从optimizationSource.groupId获取
      const groupId = optimizationSource.type === 'base' ? 0 : optimizationSource.groupId!
      const targetGroup = comparisonGroupsData.find(g => g.id === groupId)
      const targetMessage = messageIdToUse
        ? targetGroup?.messages.find(msg => msg.id === messageIdToUse)
        : targetGroup?.messages.find(msg => msg.role === 'system')

      if (targetMessage && targetGroup) {
        // 确保只更新指定的消息，使用严格的ID匹配
        const targetMessageId = messageIdToUse || targetMessage.id

        setComparisonGroupsData(prev =>
          prev.map(group => {
            if (group.id === groupId) {
              const newMessages = group.messages.map(msg => {
                // 严格匹配：只有当消息ID完全匹配时才更新
                if (msg.id === targetMessageId) {
                  return { ...msg, content: optimizedResult }
                }
                // 确保其他消息保持不变
                return msg
              })

              // 验证：确保只有一条消息被更新
              const updatedCount = newMessages.filter(m => m.content === optimizedResult).length
              if (updatedCount !== 1) {
                console.error('⚠️ [handleFeedbackOptimizationApply] 警告：更新了多条消息', {
                  updatedCount,
                  targetMessageId,
                  allMessages: newMessages.map(m => ({ id: m.id, role: m.role, contentMatches: m.content === optimizedResult })),
                })
              }

              const newMessageInputValues = {
                ...group.messageInputValues,
                [targetMessageId]: optimizedResult,
              }
              return { ...group, messages: newMessages, messageInputValues: newMessageInputValues }
            }
            return group
          }),
        )

        // 根据类型显示不同的成功消息
        const successMessage =
          optimizationSource.type === 'base'
            ? t('components.prompts.promptEditPage.baseGroupPromptFullyReplaced')
            : t('components.prompts.promptEditPage.controlGroupPromptFullyReplaced', { groupId })
        setSnackbar({ open: true, message: successMessage, severity: 'success' })
      }
    }

    // 清理状态
    resetOptimizationDialog()
  }, [
    optimizationSource,
    fullTextOptimizeMessageIdRef,
    promptMessages,
    optimizedResult,
    comparisonGroupsData,
    setPromptMessages,
    setMessageInputValues,
    setComparisonGroupsData,
    setSnackbar,
    resetOptimizationDialog,
    triggerAutoSave,
    t,
  ])

  // 场景2：插入优化应用逻辑 - 在光标位置插入内容
  const handleInsertOptimizationApply = useCallback(() => {
    if (!cursorPosition) {
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.cursorPositionNotFound'), severity: 'error' })
      return
    }

    const { messageId, position } = cursorPosition

    if (optimizationSource.type === 'main') {
      // 主页面：在光标位置插入内容
      const currentContent = messageInputValues[messageId] || ''
      const newContent = currentContent.slice(0, position) + optimizedResult + currentContent.slice(position)

      const newMessages = promptMessages.map(msg => {
        if (msg.id === messageId) {
          return { ...msg, content: newContent }
        }
        return msg
      })
      setPromptMessages(newMessages)
      setMessageInputValues(prev => ({
        ...prev,
        [messageId]: newContent,
      }))
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.contentInsertedAtCursor'), severity: 'success' })

      // 使用防抖机制保存草稿
      triggerAutoSave({ promptMessages: newMessages })
    } else if (optimizationSource.type === 'base' || (optimizationSource.type === 'control' && optimizationSource.groupId)) {
      // 基准组和对照组：统一处理，基准组 groupId 为 0
      const groupId = optimizationSource.type === 'base' ? 0 : optimizationSource.groupId!

      setComparisonGroupsData(prev =>
        prev.map(group => {
          if (group.id === groupId) {
            const currentContent = (group.messageInputValues || {})[messageId] || ''
            const newContent = currentContent.slice(0, position) + optimizedResult + currentContent.slice(position)

            const newMessages = group.messages.map(msg => {
              if (msg.id === messageId) {
                return { ...msg, content: newContent }
              }
              return msg
            })
            const newMessageInputValues = {
              ...(group.messageInputValues || {}),
              [messageId]: newContent,
            }
            return { ...group, messages: newMessages, messageInputValues: newMessageInputValues }
          }
          return group
        }),
      )

      const successMessage =
        optimizationSource.type === 'base'
          ? t('components.prompts.promptEditPage.baseGroupContentInsertedAtCursor')
          : t('components.prompts.promptEditPage.controlGroupContentInsertedAtCursor', { groupId })
      setSnackbar({ open: true, message: successMessage, severity: 'success' })
    }

    // 清理状态
    resetOptimizationDialog()
  }, [
    optimizationSource,
    cursorPosition,
    optimizedResult,
    messageInputValues,
    promptMessages,
    setPromptMessages,
    setMessageInputValues,
    setComparisonGroupsData,
    setSnackbar,
    resetOptimizationDialog,
    triggerAutoSave,
    t,
  ])

  // 场景3：选中优化应用逻辑 - 替换选中的内容
  const handleSelectOptimizationApply = useCallback(() => {
    if (!selectedText) {
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.selectedContentNotFound'), severity: 'error' })
      return
    }

    if (optimizationSource.type === 'main') {
      // 主页面：替换选中的内容
      // 优先使用保存的 messageId（从 ref 或 optimizationSource）
      const messageIdToUse = lastOptimizationSourceMessageIdRef.current || optimizationSource.messageId
      const targetMessage = messageIdToUse ? promptMessages.find(msg => msg.id === messageIdToUse) : promptMessages.find(msg => msg.role === 'system')

      if (targetMessage) {
        const currentContent = messageInputValues[targetMessage.id] || targetMessage.content
        const newContent = currentContent.replace(selectedText, optimizedResult)

        const newMessages = promptMessages.map(msg => {
          if (msg.id === targetMessage.id) {
            return { ...msg, content: newContent }
          }
          return msg
        })
        setPromptMessages(newMessages)
        setMessageInputValues(prev => ({
          ...prev,
          [targetMessage.id]: newContent,
        }))
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.selectedContentReplaced'), severity: 'success' })

        // 使用防抖机制保存草稿
        triggerAutoSave({ promptMessages: newMessages })
      }
    } else if (optimizationSource.type === 'base' || (optimizationSource.type === 'control' && optimizationSource.groupId)) {
      // 基准组和对照组：统一处理，基准组 groupId 为 0
      const groupId = optimizationSource.type === 'base' ? 0 : optimizationSource.groupId!
      // 优先使用保存的 messageId（从 ref 或 optimizationSource）
      const messageIdToUse = lastOptimizationSourceMessageIdRef.current || optimizationSource.messageId

      if (!messageIdToUse) {
        console.error('❌ [handleSelectOptimizationApply] 对比组缺少 messageId', {
          groupId,
          optimizationSource,
          lastOptimizationSourceMessageIdRef: lastOptimizationSourceMessageIdRef.current,
        })
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.messageIdNotFound'), severity: 'error' })
        return
      }

      setComparisonGroupsData(prev =>
        prev.map(group => {
          if (group.id === groupId) {
            const targetMessage = group.messages.find(msg => msg.id === messageIdToUse)
            if (!targetMessage) {
              console.error('❌ [handleSelectOptimizationApply] 对比组未找到目标消息', {
                groupId,
                messageId: messageIdToUse,
                groupMessages: group.messages.map(m => ({ id: m.id, role: m.role })),
              })
              setSnackbar({ open: true, message: t('components.prompts.promptEditPage.messageIdNotFound'), severity: 'error' })
              return group
            }

            const currentContent = (group.messageInputValues || {})[targetMessage.id] || targetMessage.content
            // 直接替换
            const newContent = currentContent.replace(selectedText, optimizedResult)

            const newMessages = group.messages.map(msg => {
              if (msg.id === targetMessage.id) {
                return { ...msg, content: newContent }
              }
              return msg
            })
            const newMessageInputValues = {
              ...(group.messageInputValues || {}),
              [targetMessage.id]: newContent,
            }
            return { ...group, messages: newMessages, messageInputValues: newMessageInputValues }
          }
          return group
        }),
      )

      const successMessage =
        optimizationSource.type === 'base'
          ? t('components.prompts.promptEditPage.baseGroupSelectedContentReplaced')
          : t('components.prompts.promptEditPage.controlGroupSelectedContentReplaced', { groupId })
      setSnackbar({ open: true, message: successMessage, severity: 'success' })
    }

    // 清理状态
    resetOptimizationDialog()
  }, [
    optimizationSource,
    selectedText,
    optimizedResult,
    lastOptimizationSourceMessageIdRef,
    promptMessages,
    messageInputValues,
    setPromptMessages,
    setMessageInputValues,
    setComparisonGroupsData,
    setSnackbar,
    resetOptimizationDialog,
    triggerAutoSave,
    t,
  ])

  // 应用优化结果
  const handleApplyOptimization = useCallback(() => {
    if (!optimizedResult) {
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.noOptimizationResult'), severity: 'info' })
      return
    }

    // 验证优化类型
    if (!currentOptimizationType) {
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.optimizationTypeNotSet'), severity: 'error' })
      return
    }

    // 验证优化类型的前置条件
    if (currentOptimizationType === 'insert' && !cursorPosition) {
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.insertOptimizationNeedsCursor'), severity: 'error' })
      return
    }

    if (currentOptimizationType === 'select' && (!selectedText || !selectionIndices)) {
      const errorMsg = !selectedText ? t('components.prompts.promptEditPage.selectOptimizationNeedsSelectedText') : t('components.prompts.promptEditPage.selectedPositionNotDetermined')
      setSnackbar({ open: true, message: errorMsg, severity: 'error' })
      return
    }

    // 根据优化类型执行不同的应用逻辑
    switch (currentOptimizationType) {
      case 'general':
        // 场景1：反馈优化 - 完全覆盖提示词内容
        handleFeedbackOptimizationApply()
        break

      case 'insert':
        // 场景2：插入优化 - 在光标位置插入内容
        handleInsertOptimizationApply()
        break

      case 'select':
        // 场景3：选中优化 - 替换选中的内容
        handleSelectOptimizationApply()
        break

      default:
        setSnackbar({ open: true, message: t('components.prompts.promptEditPage.unknownOptimizationType'), severity: 'error' })
        return
    }
  }, [
    currentOptimizationType,
    optimizationSource,
    optimizedResult,
    cursorPosition,
    selectedText,
    selectionIndices,
    handleFeedbackOptimizationApply,
    handleInsertOptimizationApply,
    handleSelectOptimizationApply,
    setSnackbar,
    t,
  ])

  // 只关闭优化对话框，保持选中状态
  const closeOptimizationDialog = useCallback(() => {
    // 保存需要保留的选中状态
    const preservedSelectedText = selectedText
    const preservedSelectionPosition = selectionPosition
    const preservedSelectionIndices = selectionIndices

    // 调用 resetOptimizationDialog 做大部分清理工作
    resetOptimizationDialog()

    // 恢复需要保留的选中状态
    if (preservedSelectedText) {
      setSelectedText(preservedSelectedText)
    }
    if (preservedSelectionPosition) {
      setSelectionPosition(preservedSelectionPosition)
    }
    if (preservedSelectionIndices) {
      setSelectionIndices(preservedSelectionIndices)
    }
  }, [selectedText, selectionPosition, selectionIndices, resetOptimizationDialog, setSelectedText, setSelectionPosition, setSelectionIndices])

  // 停止反馈优化
  const handleStopFeedbackOptimization = useCallback(() => {
    // 取消正在进行的流式请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    // 停止优化状态
    setIsOptimizing(false)

    // 将当前的流式内容设置为最终结果
    const currentContent = feedbackOptimizeStreamingRef.current
    if (currentContent) {
      setOptimizedResult(currentContent)
    }
  }, [abortControllerRef, feedbackOptimizeStreamingRef, setIsOptimizing, setOptimizedResult])

  return {
    handleOptimizeDialogOpen,
    handleOptimizeRequest,
    handleApplyOptimization,
    closeOptimizationDialog,
    handleStopFeedbackOptimization,
  }
}
