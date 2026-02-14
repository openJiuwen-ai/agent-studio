import { useCallback } from 'react'
import {
  PromptService,
  type DebugStreamingRequest,
  type DebugMessage,
  type DebugMockTool,
  type DebugStreamingResponse,
  type DebugVariableVal,
} from '@test-agentstudio/api-client'
import type { ChatMessage, PromptMessage } from '@/components/Prompts'
import type { ComparisonGroupData, PromptParameter, Model, ModelConfig } from '@/types/promptType'
import {
  extractDebugErrorMessage,
  generateMessageKey,
  findModelByIdAndFrom,
  validateComparisonGroupPlaceholders,
  processToolCallsIncremental,
  checkValidModel,
} from '@/utils/prompts/promptEditPageUtils'
import { messageId } from '@/utils/prompts/utils'
import { convertFrontendToolsToApiTools } from '@/utils/prompts/toolFormatConverter'

interface UseDebugInputAreaGroupOptions {
  // 提示词相关
  promptId: string

  // 对比组相关
  comparisonGroupsData: ComparisonGroupData[]
  setComparisonGroupsData: React.Dispatch<React.SetStateAction<ComparisonGroupData[]>>

  // AbortController refs
  groupAbortControllerRefs: React.MutableRefObject<{ [groupId: number]: AbortController | null }>
  groupDebugControllerRefs: React.MutableRefObject<{ [groupId: number]: { cancel: () => void } | null }>

  // 展开状态
  groupReasoningExpanded: { [groupId: number]: { [messageIndex: number]: boolean } }
  setGroupReasoningExpanded: React.Dispatch<React.SetStateAction<{ [groupId: number]: { [messageIndex: number]: boolean } }>>
  groupToolCallExpanded: { [groupId: number]: { [messageIndex: number]: boolean } }
  setGroupToolCallExpanded: React.Dispatch<React.SetStateAction<{ [groupId: number]: { [messageIndex: number]: boolean } }>>

  // 完成状态
  setGroupCompletedMessages: React.Dispatch<React.SetStateAction<{ [groupId: number]: Set<number> }>>

  // 流式停止状态
  setGroupStreamingStopped: React.Dispatch<React.SetStateAction<{ [groupId: number]: boolean }>>
  groupStreamingStoppedRef: React.MutableRefObject<{ [groupId: number]: boolean }>
  isStreamingStoppedRef: React.MutableRefObject<boolean>

  // 模型相关
  availableModels: Model[]

  // 辅助函数
  enableAutoReadOnly: () => void
  disableAutoReadOnly: () => void

  // 执行流式调试请求的函数（来自 useDebugInputArea）
  executeStreamingDebugRequest: (
    debugRequest: DebugStreamingRequest,
    mockTools: DebugMockTool[],
    options?: {
      messageIndex?: number
      messages?: any[]
      setMessages?: (updater: (prev: any[]) => any[]) => void
      completedMessages?: Set<number>
      setCompletedMessages?: (updater: (prev: Set<number>) => Set<number>) => void
      isProcessing?: boolean
      setIsProcessing?: (value: boolean) => void
      abortControllerRef?: React.MutableRefObject<AbortController | null>
      customStreamHandler?: (response: DebugStreamingResponse, mockTools?: Array<{ name: string; mock_response: string }>) => void
      onStart?: () => void
      onError?: (error: Error, messageIndex: number) => void
      onComplete?: (messageIndex: number, cost_ms: number, lastResponseData?: DebugStreamingResponse) => void
      onStreamingUpdate?: (response: DebugStreamingResponse, messageIndex: number) => void
      onStop?: (messageIndex: number) => void
      isRetry?: boolean
      userInput?: string
      scrollToBottom?: boolean
      autoExpandReasoning?: boolean
      autoExpandToolCalls?: boolean
      saveContext?: boolean
    },
  ) => Promise<{ cancel: () => void }>

  // 输入消息相关
  comparisonInputMessage: string
  setComparisonInputMessage: React.Dispatch<React.SetStateAction<string>>

  // 流式停止状态
  isStreamingStopped: boolean
  setIsStreamingStopped: React.Dispatch<React.SetStateAction<boolean>>

  // 辅助函数
  workspaceId: string
  t: (key: string, options?: Record<string, unknown>) => string
  showSnackbar: (message: string, severity?: 'success' | 'error' | 'warning' | 'info') => void
}

export const useDebugInputAreaGroup = (options: UseDebugInputAreaGroupOptions) => {
  const {
    promptId,
    comparisonGroupsData,
    setComparisonGroupsData,
    groupAbortControllerRefs,
    groupDebugControllerRefs,
    groupReasoningExpanded,
    setGroupReasoningExpanded,
    groupToolCallExpanded,
    setGroupToolCallExpanded,
    setGroupCompletedMessages,
    setGroupStreamingStopped,
    groupStreamingStoppedRef,
    isStreamingStoppedRef,
    availableModels,
    enableAutoReadOnly,
    disableAutoReadOnly,
    executeStreamingDebugRequest,
    comparisonInputMessage,
    setComparisonInputMessage,
    isStreamingStopped,
    setIsStreamingStopped,
    workspaceId,
    t,
    showSnackbar,
  } = options

  // ModelConfig 字段名映射（从驼峰到下划线）
  const modelConfigFieldMapping: { [key: string]: string } = {
    maxTokens: 'max_tokens',
    topP: 'top_p',
    frequencyPenalty: 'frequency_penalty',
    presencePenalty: 'presence_penalty',
  }

  /**
   * 为单个组调用API的通用函数
   */
  const callGroupAPI = useCallback(
    async (
      existingMessages: Array<{ type: 'user' | 'ai'; content: string; timestamp: string; userInput?: string }>,
      userMessage: { type: 'user'; content: string; timestamp: string },
      groupParameters: PromptParameter[],
      groupModelConfig: ModelConfig,
      promptData: any,
      currentInput: string,
      groupPromptMessages: PromptMessage[] | number,
      groupId: number,
      isRetry: boolean = false,
    ) => {
      const isBaseGroup = groupId === 0
      console.log(`🔧 [API-${isBaseGroup ? 'BASE' : 'CONTROL'}] 开始调用API`, {
        groupId,
        isBaseGroup,
        currentInput,
        isStreamingStopped: isStreamingStoppedRef.current,
        existingMessagesLength: existingMessages.length,
      })

      const startTime = Date.now()

      try {
        // 准备调试请求数据
        // 注意：需要手动添加新的用户消息（如果有），因为 setComparisonGroupsData 是异步的，existingMessages 可能还没有更新
        const hasUserInput = currentInput.trim() !== ''

        const promptMessages: DebugMessage[] = [
          ...existingMessages
            .filter(msg => {
              // 过滤掉内容为 "......" 或空内容的AI消息（被停止或未完成的消息）
              if (msg.type === 'ai' && (msg.content === '......' || msg.content.trim() === '')) {
                console.log(`🧹 [FILTER-COMPARISON-${groupId}] 过滤掉不完整的AI消息`, { content: msg.content })
                return false
              }
              return true
            })
            .map(msg => ({
              role: msg.type === 'user' ? ('user' as const) : ('assistant' as const),
              content: msg.content,
              parts: [],
            })),
          // 如果有新的用户输入，且不是重试场景，手动添加到 promptMessages 中
          // 重试时，existingMessages 已经包含了用户消息，所以不应该再添加
          ...(hasUserInput && !isRetry
            ? [
                {
                  role: 'user' as const,
                  content: currentInput,
                  parts: [],
                },
              ]
            : []),
        ]

        // 准备变量值
        const variableVals: DebugVariableVal[] = groupParameters.map(param => {
          if (param.type === 'placeholder' && param.messages) {
            // placeholder类型变量：设置placeholder_messages
            const placeholderMessages = param.messages.map(msg => ({
              id: messageId(), // 调用messageId函数生成唯一ID
              content: msg.content,
              role: msg.role,
              parts: [], // 暂时没有使用，先填[]
            }))

            return {
              key: param.name,
              placeholder_messages: placeholderMessages,
            }
          } else {
            // 普通变量：设置value
            return {
              key: param.name,
              value: param.value || '',
            }
          }
        })

        // 获取组特定的工具配置
        const groupTools = comparisonGroupsData.find(g => g.id === groupId)?.tools || []

        // 准备工具模拟值
        const mockTools: DebugMockTool[] = groupTools.map(tool => ({
          name: tool.name,
          mock_value: tool.defaultValue || '',
          mock_response: tool.defaultValue || '',
        }))

        // 获取组特定的工具启用状态
        const groupToolsEnabled = comparisonGroupsData.find(g => g.id === groupId)?.toolsEnabled ?? true

        // 构建新的API请求格式
        const promptTemplate: any = {
          messages: [],
          template_type: 'normal',
          variable_defs: [],
        }

        // 构建提示词消息
        if (Array.isArray(groupPromptMessages)) {
          promptTemplate.messages = groupPromptMessages.map(msg => ({
            content: msg.content,
            role: msg.role,
            key: generateMessageKey(),
          }))
        }

        // 构建变量定义
        promptTemplate.variable_defs = groupParameters.map(param => ({
          key: param.name,
          type: param.dataType || 'string',
          desc: param.description || '',
        }))

        // 构建工具配置（新格式：JSON Schema 对象）
        // 使用 convertFrontendToolsToApiTools 来确保使用完整的 JSON Schema（包括嵌套对象、数组、enum等）
        // 这个函数会优先使用 tool.parametersJsonSchema（如果存在），保留所有高级特性
        // 返回的是对象格式，不是字符串格式（和主页面保持一致）
        console.log('🔧 [COMPARISON-DEBUG] 转换对比组工具配置，组ID:', groupId, '工具数量:', groupTools.length)
        groupTools.forEach(tool => {
          console.log(`🔧 [COMPARISON-DEBUG] 对比组工具 ${tool.name}:`, {
            hasParametersJsonSchema: !!tool.parametersJsonSchema,
            parametersCount: tool.parameters.length,
          })
        })
        const toolsConfig = convertFrontendToolsToApiTools(groupTools)
        console.log('🔧 [COMPARISON-DEBUG] 转换后的对比组工具配置:', toolsConfig)

        // 从模型列表中查找对应的模型对象
        const selectedModel = findModelByIdAndFrom(groupModelConfig.model, groupModelConfig.model_from, availableModels)

        // 构建模型配置 - 动态包含该模型支持的参数
        const modelConfig: any = {
          models_name: selectedModel?.openModel.name || '',
          models_id: groupModelConfig.model,
          model_from: groupModelConfig.model_from,
        }

        // 根据模型的 param_schemas 动态添加参数
        if (selectedModel?.openModel?.param_config?.param_schemas) {
          selectedModel.openModel.param_config.param_schemas.forEach((schema: any) => {
            const paramName = schema.name

            // 先检查直接匹配的参数名
            if (groupModelConfig[paramName] !== undefined && groupModelConfig[paramName] !== null) {
              modelConfig[paramName] = groupModelConfig[paramName]
            } else {
              // 检查是否需要字段名映射（从驼峰到下划线）
              const camelCaseKey = Object.keys(modelConfigFieldMapping).find(key => modelConfigFieldMapping[key] === paramName)
              if (camelCaseKey && groupModelConfig[camelCaseKey] !== undefined && groupModelConfig[camelCaseKey] !== null) {
                modelConfig[paramName] = groupModelConfig[camelCaseKey]
              }
            }
          })
        } else {
          // 如果没有 param_schemas，则使用默认的常见参数
          if (groupModelConfig.temperature !== undefined) modelConfig.temperature = groupModelConfig.temperature
          if (groupModelConfig.maxTokens !== undefined) modelConfig.max_tokens = groupModelConfig.maxTokens
          if (groupModelConfig.topP !== undefined) modelConfig.top_p = groupModelConfig.topP
        }

        // 构建完整的prompt对象
        const customPromptData = {
          ...promptData,
          prompt_commit: {},
          prompt_draft: {
            draft_info: {},
            detail: {
              prompt_template: promptTemplate,
              tools: toolsConfig,
              tool_call_config: {
                tool_choice: groupToolsEnabled ? 'auto' : 'none',
              },
              prompt_model_config: modelConfig,
            },
          },
        }

        const debugRequest: DebugStreamingRequest = {
          prompt: customPromptData,
          messages: promptMessages,
          variable_vals: variableVals,
          mock_tools: mockTools,
          single_step_debug: false, // 对比模式不使用单步调试
        }

        // 创建AI消息占位符
        const aiMessage = {
          type: 'ai' as const,
          content: '......',
          timestamp: new Date().toLocaleString('zh-CN'),
          userInput: currentInput,
        }

        // 统一处理所有组的AI消息占位符（包括基准组）
        let currentAIMessageIndex = -1
        // 🎯 关键修复：需要使用包含用户消息后的最新状态来计算AI消息索引
        setComparisonGroupsData(prev => {
          const updatedGroups = prev.map(g => {
            if (g.id === groupId) {
              // AI消息的索引应该是当前聊天消息数量（包括已添加的用户消息）
              currentAIMessageIndex = g.chatMessages.length
              console.log(`🤖 [AI-MESSAGE] 为组${groupId}计算AI消息索引:`, {
                groupId,
                isBaseGroup,
                chatMessagesLength: g.chatMessages.length,
                calculatedAIIndex: currentAIMessageIndex,
                explanation: `用户消息在索引${g.chatMessages.length - 1}，AI消息将在索引${currentAIMessageIndex}`,
              })
              return { ...g, chatMessages: [...g.chatMessages, aiMessage] }
            }
            return g
          })
          return updatedGroups
        })

        console.log(`🚀 [API-${isBaseGroup ? 'BASE' : 'CONTROL'}] 即将调用executeStreamingDebugRequest`, {
          groupId,
          isBaseGroup,
          isStreamingStopped: isStreamingStoppedRef.current,
          debugRequestKeys: Object.keys(debugRequest),
          promptId,
          hasPromptData: !!promptData,
          messagesLength: promptMessages.length,
          variablesLength: variableVals.length,
        })

        // 取消之前的请求（如果存在）- 参考快捷优化的逻辑
        if (groupAbortControllerRefs.current[groupId]) {
          console.log(`🛑 [callGroupAPI] 取消组${groupId}之前的流式请求`)
          groupAbortControllerRefs.current[groupId]!.abort()
          groupAbortControllerRefs.current[groupId] = null
        }

        // 创建新的 AbortController - 参考快捷优化的逻辑
        const groupAbortControllerRef: React.MutableRefObject<AbortController | null> = {
          current: null,
        }
        groupAbortControllerRef.current = new AbortController()
        groupAbortControllerRefs.current[groupId] = groupAbortControllerRef.current
        console.log(`🆕 [callGroupAPI] 为组${groupId}创建新的 AbortController`)

        // 使用executeStreamingDebugRequest处理流式响应，并保存返回的 debugController
        const debugController = await executeStreamingDebugRequest(debugRequest, mockTools, {
          abortControllerRef: groupAbortControllerRef, // 传递 AbortController ref（参考快捷优化的停止逻辑）
          customStreamHandler: (response: DebugStreamingResponse) => {
            // 检查是否已被用户停止（通过 AbortController）- 参考快捷优化的逻辑
            if (groupAbortControllerRef.current?.signal.aborted) {
              console.log('🛑 [STREAM] 忽略响应，流已被停止（通过 AbortController）', {
                groupId,
                isBaseGroup,
              })
              return
            }

            // 处理流式响应
            if (response.delta) {
              if (response.delta.content || response.delta.reasoning_content || response.delta.tool_calls) {
                setComparisonGroupsData(prev =>
                  prev.map(g => {
                    if (g.id !== groupId) return g

                    const newChatMessages = [...g.chatMessages]
                    const lastMessageIndex = newChatMessages.length - 1
                    const lastMessage = newChatMessages[lastMessageIndex]
                    if (lastMessage && lastMessage.type === 'ai') {
                      const updates: any = {}

                      // 获取当前消息的工具调用状态，用于判断是否处于工具调用阶段
                      const existingToolCalls = lastMessage.toolCalls || []
                      const hasNewToolCalls = response.delta?.tool_calls && response.delta.tool_calls.length > 0

                      // 处理工具调用信息（优先处理，因为工具调用可能会影响内容的处理）
                      if (hasNewToolCalls && response.delta && response.delta.tool_calls) {
                        const updatedToolCalls = processToolCallsIncremental(existingToolCalls, response.delta.tool_calls, mockTools)
                        updates.toolCalls = updatedToolCalls
                      }

                      // 处理内容更新 - 需要过滤工具调用相关的标记
                      if (response.delta && response.delta.content) {
                        let contentToAdd = response.delta.content

                        // 过滤工具调用相关的标记
                        // 移除 <tool_call> 标记及其周围的空白字符
                        contentToAdd = contentToAdd.replace(/<tool_call>\s*/gi, '')
                        contentToAdd = contentToAdd.replace(/\s*<\/tool_call>/gi, '')
                        contentToAdd = contentToAdd.replace(/<tool_call\/>/gi, '')

                        // 如果当前内容只包含工具调用标记和空白字符，则跳过此次更新
                        const trimmedContent = contentToAdd.trim()
                        if (trimmedContent === '' && response.delta && response.delta.content.trim() !== '') {
                          // 这是工具调用标记，不更新内容
                          console.log('🔧 [DEBUG_STREAM] 过滤工具调用标记:', response.delta.content)
                        } else if (trimmedContent !== '') {
                          // 只有在有实际内容时才更新
                          let newContent = lastMessage.content
                          if (newContent === '......') {
                            newContent = ''
                          }
                          // 如果当前内容末尾已经包含了要添加的内容（防止重复），则跳过
                          if (!newContent.endsWith(contentToAdd)) {
                            updates.content = newContent + contentToAdd
                          }
                        }
                      }

                      // 处理思考过程更新
                      if (response.delta && response.delta.reasoning_content) {
                        const newReasoningContent = lastMessage.reasoningContent || ''
                        updates.reasoningContent = newReasoningContent + response.delta.reasoning_content
                      }

                      // 🎯 自动展开AI思考过程和工具调用 - 在开始输出时展开
                      if (updates.reasoningContent && !groupReasoningExpanded[groupId]?.[lastMessageIndex]) {
                        setGroupReasoningExpanded(prev => ({
                          ...prev,
                          [groupId]: {
                            ...prev[groupId],
                            [lastMessageIndex]: true,
                          },
                        }))
                      }
                      if (updates.toolCalls && updates.toolCalls.length > 0 && !groupToolCallExpanded[groupId]?.[lastMessageIndex]) {
                        setGroupToolCallExpanded(prev => ({
                          ...prev,
                          [groupId]: {
                            ...prev[groupId],
                            [lastMessageIndex]: true,
                          },
                        }))
                      }

                      newChatMessages[lastMessageIndex] = {
                        ...lastMessage,
                        ...updates,
                      }
                    }
                    return { ...g, chatMessages: newChatMessages }
                  }),
                )
              }
            }

            // 处理完成信息（token和耗时）
            if (response.delta === null && response.usage) {
              const cost_ms = Date.now() - startTime

              // 使用之前计算的AI消息索引
              const aiMessageIndex = currentAIMessageIndex

              setTimeout(() => {
                // 统一处理所有组的完成信息（包括基准组）
                if (aiMessageIndex >= 0) {
                  setComparisonGroupsData(prev =>
                    prev.map(g => {
                      if (g.id !== groupId) return g

                      const newChatMessages = [...g.chatMessages]
                      if (newChatMessages[aiMessageIndex] && newChatMessages[aiMessageIndex].type === 'ai') {
                        newChatMessages[aiMessageIndex] = {
                          ...newChatMessages[aiMessageIndex],
                          input_tokens: response.usage?.input_tokens?.toString() || '0',
                          output_tokens: response.usage?.output_tokens?.toString() || '0',
                          cost_ms: cost_ms.toString(),
                        }
                      }
                      return { ...g, chatMessages: newChatMessages }
                    }),
                  )

                  // 🎯 关键：标记AI消息为完成状态，这样才能显示功能按钮
                  setGroupCompletedMessages(prev => {
                    const oldCompleted = prev[groupId] || new Set()
                    const alreadyCompleted = oldCompleted.has(aiMessageIndex)
                    const newCompleted = new Set([...oldCompleted, aiMessageIndex])

                    console.log(`🎯 [COMPLETED-MESSAGES] 组${groupId}完成状态更新:`, {
                      oldCompletedArray: Array.from(oldCompleted),
                      newCompletedArray: Array.from(newCompleted),
                      aiMessageIndex,
                      groupId,
                      isBaseGroup,
                      alreadyCompleted,
                      sizeBefore: oldCompleted.size,
                      sizeAfter: newCompleted.size,
                      shouldShowButtons: newCompleted.has(aiMessageIndex),
                      indexToAdd: aiMessageIndex,
                      wasAlreadyInSet: oldCompleted.has(aiMessageIndex),
                    })

                    if (alreadyCompleted) {
                      console.warn(`⚠️ [DUPLICATE-COMPLETE] 消息${aiMessageIndex}已经在组${groupId}的完成状态中！`)
                    }

                    return {
                      ...prev,
                      [groupId]: newCompleted,
                    }
                  })

                  console.log(`✅ [USAGE-UPDATE] 组${groupId}的AI消息${aiMessageIndex}已标记为完成，应显示功能按钮`)
                }
              }, 100)
            }
          },
          onStart: () => {
            enableAutoReadOnly()
          },
          onError: (error: Error) => {
            console.error(`❌ [ERROR-${isBaseGroup ? 'BASE' : 'CONTROL'}] API调用失败:`, error, {
              groupId,
              isBaseGroup,
              isStreamingStopped: isStreamingStoppedRef.current,
            })
            disableAutoReadOnly()
            // 添加错误消息
            const errorMessage = {
              type: 'ai' as const,
              content: extractDebugErrorMessage(error),
              timestamp: new Date().toLocaleString('zh-CN'),
              userInput: currentInput,
            }

            setComparisonGroupsData(prev =>
              prev.map(g => {
                if (g.id !== groupId) return g

                const newChatMessages = [...g.chatMessages]
                if (newChatMessages.length > 0) {
                  newChatMessages[newChatMessages.length - 1] = errorMessage
                }
                return { ...g, chatMessages: newChatMessages, isProcessing: false }
              }),
            )

            // 重置组的流式停止状态，确保用户能够再次发送消息
            setGroupStreamingStopped(prev => ({
              ...prev,
              [groupId]: false,
            }))
            groupStreamingStoppedRef.current = {
              ...groupStreamingStoppedRef.current,
              [groupId]: false,
            }

            // 标记错误消息为完成
            const targetGroup = comparisonGroupsData.find(g => g.id === groupId)
            if (targetGroup) {
              const errorMessageIndex = targetGroup.chatMessages.length - 1
              setGroupCompletedMessages(prev => ({
                ...prev,
                [groupId]: new Set([...(prev[groupId] || []), errorMessageIndex]),
              }))
            }
          },
          onComplete: () => {
            console.log(`🏁 [COMPLETE-${isBaseGroup ? 'BASE' : 'CONTROL'}] onComplete 回调开始执行`, {
              groupId,
              isBaseGroup,
              timestamp: new Date().toISOString(),
            })

            disableAutoReadOnly()

            // 检查对应组的停止状态
            const groupStopped = groupStreamingStoppedRef.current[groupId] || false

            console.log(`✅ [COMPLETE-${isBaseGroup ? 'BASE' : 'CONTROL'}] 流式响应完成`, {
              groupId,
              isBaseGroup,
              groupStopped,
              mainStopped: isStreamingStoppedRef.current,
            })

            // 调试完成，重置处理状态 - 但如果用户已经手动停止该组，不要重新设置处理状态
            if (!groupStopped) {
              setComparisonGroupsData(prevGroups =>
                prevGroups.map(g =>
                  g.id === groupId
                    ? {
                        ...g,
                        isProcessing: false,
                      }
                    : g,
                ),
              )

              // 🎯 关键：标记当前AI消息索引为完成状态
              // currentAIMessageIndex已经在外部作用域定义
              if (currentAIMessageIndex >= 0) {
                setGroupCompletedMessages(prev => {
                  const oldCompleted = prev[groupId] || new Set()
                  const alreadyCompleted = oldCompleted.has(currentAIMessageIndex)
                  const newCompleted = new Set([...oldCompleted, currentAIMessageIndex])

                  console.log(`🎯 [STREAM-COMPLETE] 流式响应完成，组${groupId}完成状态更新:`, {
                    oldCompletedArray: Array.from(oldCompleted),
                    newCompletedArray: Array.from(newCompleted),
                    currentAIMessageIndex,
                    groupId,
                    isBaseGroup,
                    alreadyCompleted,
                    sizeBefore: oldCompleted.size,
                    sizeAfter: newCompleted.size,
                    indexToAdd: currentAIMessageIndex,
                    wasAlreadyInSet: oldCompleted.has(currentAIMessageIndex),
                  })

                  if (alreadyCompleted) {
                    console.warn(`⚠️ [DUPLICATE-STREAM-COMPLETE] 消息${currentAIMessageIndex}已经在组${groupId}的完成状态中！`)
                  }

                  return {
                    ...prev,
                    [groupId]: newCompleted,
                  }
                })
                console.log(`✅ [COMPLETE-GROUP] 标记组${groupId}的AI消息${currentAIMessageIndex}为完成`)
              } else {
                console.warn(`⚠️ [COMPLETE-GROUP] 无效的AI消息索引: ${currentAIMessageIndex}，无法标记完成状态`)
              }
            } else {
              console.log(`✅ [COMPLETE-GROUP] 组${groupId}已停止，跳过状态重置`)
            }
          },
        })

        // 保存 debugController 以便在停止时清理延迟队列
        if (debugController) {
          groupDebugControllerRefs.current[groupId] = debugController
          console.log(`💾 [callGroupAPI] 为组${groupId}保存 debugController`)
        }
      } catch (error) {
        console.error(`${isBaseGroup ? 'BASE' : 'CONTROL'} API调用准备失败:`, error)
        disableAutoReadOnly()

        // 添加错误消息
        const errorMessage = {
          type: 'ai' as const,
          content: t('hooks.prompts.useDebugInputAreaGroup.requestPrepareFailedWithMessage', {
            message: error instanceof Error ? error.message : t('hooks.prompts.useDebugInputAreaGroup.unknownError'),
          }),
          timestamp: new Date().toLocaleString('zh-CN'),
          userInput: currentInput,
        }

        // 统一处理所有组的错误（包括基准组）
        const targetGroup = comparisonGroupsData.find(g => g.id === groupId)
        const errorMessageIndex = (targetGroup?.chatMessages || []).length

        setComparisonGroupsData(prev =>
          prev.map(g =>
            g.id === groupId
              ? {
                  ...g,
                  chatMessages: [...g.chatMessages, errorMessage],
                  isProcessing: false,
                }
              : g,
          ),
        )

        // 标记组错误消息为完成
        setGroupCompletedMessages(prev => ({
          ...prev,
          [groupId]: new Set([...(prev[groupId] || []), errorMessageIndex]),
        }))
      }
    },
    [
      promptId,
      comparisonGroupsData,
      setComparisonGroupsData,
      groupAbortControllerRefs,
      groupDebugControllerRefs,
      groupReasoningExpanded,
      setGroupReasoningExpanded,
      groupToolCallExpanded,
      setGroupToolCallExpanded,
      setGroupCompletedMessages,
      setGroupStreamingStopped,
      groupStreamingStoppedRef,
      isStreamingStoppedRef,
      availableModels,
      enableAutoReadOnly,
      disableAutoReadOnly,
      executeStreamingDebugRequest,
      modelConfigFieldMapping,
      t,
    ],
  )

  /**
   * 发送对比消息的处理函数
   */
  const handleSendComparisonMessage = useCallback(async () => {
    // 验证所有对比组的 placeholder 变量，获取有效的组ID
    const validGroupIds = validateComparisonGroupPlaceholders(comparisonGroupsData, t, showSnackbar)

    // 如果没有任何有效的组，直接返回
    if (validGroupIds.length === 0) {
      console.log('❌ [COMPARISON] 所有对比组都有无效的placeholder变量，取消发送')
      return
    }

    // 检查所有有效组的模型是否配置
    for (const groupId of validGroupIds) {
      const group = comparisonGroupsData.find(g => g.id === groupId)
      if (!group) continue

      // 检查组的模型配置是否有效（对比模式下没有 selectedModel，所以传入 null）
      if (!checkValidModel(null, group.modelConfig, availableModels)) {
        const groupName = group.isBaseGroup
          ? t('hooks.prompts.useDebugInputAreaGroup.baseGroup')
          : t('hooks.prompts.useDebugInputAreaGroup.controlGroupWithId', { id: groupId })
        showSnackbar(t('hooks.prompts.useDebugInputAreaGroup.groupConfigValidModelFirst', { groupName }), 'error')
        return
      }
    }

    console.log('🚀 [COMPARISON] 开始发送对比消息', {
      comparisonInputMessage: comparisonInputMessage.trim(),
      isBaseGroupProcessing: comparisonGroupsData.find(g => g.id === 0)?.isProcessing || false,
      isStreamingStopped,
      baseGroupChatMessagesLength: (comparisonGroupsData.find(g => g.id === 0)?.chatMessages || []).length,
      controlGroupsCount: comparisonGroupsData.length,
      validGroupIds: validGroupIds,
      invalidGroupCount: comparisonGroupsData.length - validGroupIds.length,
    })

    // 如果用户没有在输入框中输入消息，根据最后一条消息类型决定逻辑
    if (!comparisonInputMessage.trim()) {
      // 检查每个有效组的最后一条消息类型
      const groupsWithAIMessages: Array<{ groupId: number; lastAIMessageIndex: number; group: (typeof comparisonGroupsData)[0] }> = []
      let groupsWithUserMessageCount = 0

      validGroupIds.forEach(groupId => {
        const group = comparisonGroupsData.find(g => g.id === groupId)
        if (!group) return

        const lastMessage = group.chatMessages.length > 0 ? group.chatMessages[group.chatMessages.length - 1] : null

        // 如果最后一条消息是user消息，统计user消息的组数量
        if (lastMessage && lastMessage.type === 'user') {
          groupsWithUserMessageCount++
        } else {
          // 如果最后一条消息是AI消息或没有消息，查找最后一条AI消息的索引
          let lastAIMessageIndex = -1
          for (let i = group.chatMessages.length - 1; i >= 0; i--) {
            if (group.chatMessages[i].type === 'ai') {
              lastAIMessageIndex = i
              break
            }
          }

          if (lastAIMessageIndex >= 0) {
            groupsWithAIMessages.push({ groupId, lastAIMessageIndex, group })
          }
        }
      })

      // 如果所有组的最后一条消息都是user消息，则继续执行正常的发送逻辑
      if (groupsWithUserMessageCount === validGroupIds.length) {
        console.log('📝 [COMPARISON] 输入为空但所有组的最后一条都是用户消息，继续执行正常发送逻辑')
        // 继续执行下面的正常逻辑，不执行重试
      } else if (groupsWithAIMessages.length > 0) {
        // 如果所有组的最后一条消息都是AI消息或没有消息，且有AI消息，执行重试逻辑
        console.log('🔄 [COMPARISON] 输入为空，执行重试逻辑', {
          groupsWithAIMessages: groupsWithAIMessages.map(g => ({ groupId: g.groupId, lastAIMessageIndex: g.lastAIMessageIndex })),
        })

        // 检查是否有组正在处理中
        const isAnyGroupProcessing = groupsWithAIMessages.some(g => g.group.isProcessing)
        if (isAnyGroupProcessing) {
          console.log('⚠️ [COMPARISON] 有组正在处理中，取消重试')
          return
        }

        // 重置停止标志，开始新的流式响应
        setIsStreamingStopped(false)
        isStreamingStoppedRef.current = false

        // 重置所有组的停止标志（包括基准组）
        const resetGroupStops: { [groupId: number]: boolean } = {}
        comparisonGroupsData.forEach(group => {
          resetGroupStops[group.id] = false
        })
        setGroupStreamingStopped(resetGroupStops)
        groupStreamingStoppedRef.current = resetGroupStops

        try {
          // 预先获取提示词详情，所有组共享这个数据
          const promptDetail = await PromptService.getPromptDetail(promptId, {
            with_commit: true,
            with_draft: true,
            with_default_config: true,
            workspaceId: workspaceId,
          })

          if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
            throw new Error('无法获取提示词详情')
          }

          // 为每个有AI消息的组执行重试
          const retryPromises = groupsWithAIMessages.map(async ({ groupId, lastAIMessageIndex, group }) => {
            const messageToRetry = group.chatMessages[lastAIMessageIndex]
            if (!messageToRetry || messageToRetry.type !== 'ai') {
              return
            }

            // 找到对应的用户输入（允许为空，和主聊天的handleSendMessage逻辑一致）
            const userInput = messageToRetry.userInput || ''

            // 设置组处理状态
            setComparisonGroupsData(prevGroups => prevGroups.map(g => (g.id === groupId ? { ...g, isProcessing: true } : g)))

            try {
              // 重置当前AI消息为加载状态（删除要重试的消息）
              setComparisonGroupsData(prev =>
                prev.map(g =>
                  g.id === groupId
                    ? {
                        ...g,
                        chatMessages: g.chatMessages.filter((_, i) => i !== lastAIMessageIndex),
                      }
                    : g,
                ),
              )

              // 重置AI思考过程和工具调用的展开状态
              setGroupReasoningExpanded(prev => {
                const newExpanded = { ...prev }
                if (newExpanded[groupId]) {
                  delete newExpanded[groupId][lastAIMessageIndex]
                }
                return newExpanded
              })
              setGroupToolCallExpanded(prev => {
                const newExpanded = { ...prev }
                if (newExpanded[groupId]) {
                  delete newExpanded[groupId][lastAIMessageIndex]
                }
                return newExpanded
              })

              // 获取该AI消息之前的所有消息（不包括要重试的AI消息）
              // 注意：重试时不添加新的用户消息，只使用现有的消息历史
              const existingMessages = group.chatMessages
                .slice(0, lastAIMessageIndex)
                .filter(msg => msg.type === 'user' || msg.type === 'ai') // 过滤掉 system 类型
                .map(msg => ({
                  type: msg.type as 'user' | 'ai',
                  content: msg.content,
                  timestamp: msg.timestamp,
                  userInput: msg.userInput,
                }))

              // 调用 callGroupAPI
              // 注意：重试时不添加用户消息，只使用现有的消息历史和userInput来构建请求
              await callGroupAPI(
                existingMessages,
                { type: 'user' as const, content: userInput, timestamp: new Date().toLocaleString('zh-CN') },
                group.parameters,
                group.modelConfig,
                promptDetail.prompt[0],
                userInput,
                group.messages,
                groupId,
                true, // isRetry: true
              )
            } catch (error) {
              console.error(`组${groupId}重试准备失败:`, error)
              setComparisonGroupsData(prev => prev.map(g => (g.id === groupId ? { ...g, isProcessing: false } : g)))

              // 恢复原来的AI消息，显示错误
              setComparisonGroupsData(prev => {
                const updatedGroups = prev.map(g => {
                  if (g.id === groupId) {
                    const errorMessageIndex = g.chatMessages.length // 错误消息的索引（在添加之前）
                    const updatedGroup = {
                      ...g,
                      chatMessages: [
                        ...g.chatMessages,
                        {
                          ...messageToRetry,
                          content: t('hooks.prompts.useDebugInputAreaGroup.retryFailedWithMessage', {
                            message: error instanceof Error ? error.message : t('hooks.prompts.useDebugInputAreaGroup.unknownError'),
                          }),
                        },
                      ],
                    }

                    // 标记错误消息为完成
                    setGroupCompletedMessages(prevCompleted => {
                      const newCompleted = { ...prevCompleted }
                      if (!newCompleted[groupId]) {
                        newCompleted[groupId] = new Set()
                      }
                      newCompleted[groupId] = new Set([...newCompleted[groupId], errorMessageIndex])
                      return newCompleted
                    })

                    return updatedGroup
                  }
                  return g
                })
                return updatedGroups
              })
            }
          })

          // 等待所有重试完成（并行执行）
          await Promise.allSettled(retryPromises)

          console.log('✅ [COMPARISON] 所有组重试完成')
        } catch (error) {
          console.error('❌ [COMPARISON] 重试失败:', error)
        }

        return
      } else {
        // 如果没有AI消息，不添加用户消息，但继续执行其他逻辑
        console.log('⚠️ [COMPARISON] 输入为空且没有可重试的AI消息，继续执行发送逻辑（不添加用户消息）')
        // 继续执行后面的逻辑，但跳过添加用户消息的部分
      }
    }

    // 重置停止标志，开始新的流式响应
    setIsStreamingStopped(false)
    isStreamingStoppedRef.current = false

    // 重置所有组的停止标志（包括基准组）
    const resetGroupStops: { [groupId: number]: boolean } = {}
    comparisonGroupsData.forEach(group => {
      resetGroupStops[group.id] = false
    })
    setGroupStreamingStopped(resetGroupStops)
    groupStreamingStoppedRef.current = resetGroupStops

    console.log('🚀 [COMPARISON] 重置所有停止标志为 false', {
      controlGroupIds: comparisonGroupsData.map(g => g.id),
    })

    const currentInput = comparisonInputMessage.trim() ? comparisonInputMessage : ''
    const hasUserInput = comparisonInputMessage.trim() !== ''

    // 只有在消息不为空时才添加用户消息到对话历史
    if (hasUserInput) {
      const userMessage = {
        type: 'user' as const,
        content: comparisonInputMessage,
        timestamp: new Date().toLocaleString('zh-CN'),
      }

      // 添加到所有组的聊天记录并同时标记用户消息为完成
      setComparisonGroupsData(prevGroups =>
        prevGroups.map(group => ({
          ...group,
          chatMessages: [...group.chatMessages, userMessage],
        })),
      )

      // 标记所有组的用户消息为完成
      setGroupCompletedMessages(prev => {
        const newCompleted = { ...prev }
        comparisonGroupsData.forEach(group => {
          // 🎯 关键修复：用户消息的索引是添加后的索引
          const userMessageIndex = group.chatMessages.length // 用户消息添加后的索引
          if (!newCompleted[group.id]) {
            newCompleted[group.id] = new Set()
          }
          newCompleted[group.id] = new Set([...newCompleted[group.id], userMessageIndex])
          console.log(`👤 [USER-MESSAGE] 组${group.id}用户消息标记为完成，索引: ${userMessageIndex}，消息总数: ${group.chatMessages.length + 1}`)
        })
        console.log(
          '👤 [USER-MESSAGES-COMPLETE] 所有组用户消息完成状态:',
          Object.fromEntries(Object.entries(newCompleted).map(([groupId, set]) => [groupId, Array.from(set as Set<number>)])),
        )
        return newCompleted
      })

      // 为无效的组添加错误消息
      const invalidGroupIds = comparisonGroupsData.filter(group => !validGroupIds.includes(group.id)).map(group => group.id)

      if (invalidGroupIds.length > 0) {
        const errorMessage = {
          type: 'ai' as const,
          content: t('components.prompts.promptContentEditor.invalidPlaceholderVariables'),
          timestamp: new Date().toLocaleString('zh-CN'),
          userInput: comparisonInputMessage,
        }

        setComparisonGroupsData(prevGroups =>
          prevGroups.map(group => {
            if (invalidGroupIds.includes(group.id)) {
              return {
                ...group,
                chatMessages: [...group.chatMessages, errorMessage],
              }
            }
            return group
          }),
        )

        // 标记错误消息为完成
        setGroupCompletedMessages(prev => {
          const newCompleted = { ...prev }
          invalidGroupIds.forEach(groupId => {
            const group = comparisonGroupsData.find(g => g.id === groupId)!
            const errorMessageIndex = group.chatMessages.length + 1 // 用户消息后面的索引
            if (!newCompleted[groupId]) {
              newCompleted[groupId] = new Set()
            }
            newCompleted[groupId] = new Set([...newCompleted[groupId], errorMessageIndex])
          })
          return newCompleted
        })
      }
    }

    // 清空输入框（在获取 currentInput 之后）
    setComparisonInputMessage('')

    console.log('🚀 [COMPARISON] 设置所有组处理状态', {
      currentInput,
      isStreamingStopped,
      groupsCount: comparisonGroupsData.length,
    })

    try {
      // 预先获取提示词详情，所有组共享这个数据
      const promptDetail = await PromptService.getPromptDetail(promptId, {
        with_commit: true,
        with_draft: true,
        with_default_config: true,
        workspaceId: workspaceId,
      })

      if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
        throw new Error('无法获取提示词详情')
      }

      // 创建用户消息对象（用于API调用）
      const apiUserMessage = {
        type: 'user' as const,
        content: currentInput,
        timestamp: new Date().toLocaleString('zh-CN'),
      }

      // 只为有效的组设置处理状态
      setComparisonGroupsData(prevGroups =>
        prevGroups.map(group => ({
          ...group,
          isProcessing: validGroupIds.includes(group.id),
        })),
      )

      // 只为有效的组调用API
      const groupPromises = comparisonGroupsData
        .filter(group => validGroupIds.includes(group.id))
        .map(group =>
          callGroupAPI(
            group.chatMessages,
            apiUserMessage,
            group.parameters,
            group.modelConfig,
            promptDetail.prompt[0],
            currentInput,
            group.messages, // 传递组的消息结构用于构建prompt
            group.id,
            false, // isRetry: false (正常发送)
          ),
        )

      // 等待所有API调用完成（并行执行）
      await Promise.allSettled(groupPromises)

      console.log('✅ [COMPARISON] 所有对比组API调用完成', {
        isStreamingStopped,
        baseGroupProcessing: comparisonGroupsData.find(g => g.id === 0)?.isProcessing || false,
      })
    } catch (error) {
      console.error('❌ [COMPARISON] 对比模式API调用失败:', error, {
        isStreamingStopped,
        isProcessing: comparisonGroupsData.find(g => g.id === 0)?.isProcessing || false,
      })
      disableAutoReadOnly()
      // 添加错误处理，重置所有组的处理状态
      setComparisonGroupsData(prev => prev.map(g => (g.id === 0 ? { ...g, isProcessing: false } : g)))
      setComparisonGroupsData(prevGroups =>
        prevGroups.map(group => ({
          ...group,
          isProcessing: false,
        })),
      )
    }
  }, [
    comparisonGroupsData,
    setComparisonGroupsData,
    comparisonInputMessage,
    setComparisonInputMessage,
    isStreamingStopped,
    setIsStreamingStopped,
    isStreamingStoppedRef,
    setGroupStreamingStopped,
    groupStreamingStoppedRef,
    setGroupCompletedMessages,
    setGroupReasoningExpanded,
    setGroupToolCallExpanded,
    availableModels,
    checkValidModel,
    callGroupAPI,
    promptId,
    workspaceId,
    t,
    showSnackbar,
    disableAutoReadOnly,
  ])

  /**
   * 清空对比聊天记录
   */
  const handleClearComparisonChat = useCallback(() => {
    // 清空所有组的聊天记录
    setComparisonGroupsData(prevGroups =>
      prevGroups.map(group => ({
        ...group,
        chatMessages: [],
      })),
    )
    // 清空所有组的完成状态
    setGroupCompletedMessages({})
  }, [setComparisonGroupsData, setGroupCompletedMessages])

  /**
   * 重试组的最后一条消息
   */
  const handleGroupRetryLastMessage = useCallback(
    async (groupId: number, index: number) => {
      const group = comparisonGroupsData.find(g => g.id === groupId)
      if (!group) return

      // 重置组停止标志，开始新的流式响应
      setGroupStreamingStopped(prev => ({
        ...prev,
        [groupId]: false,
      }))

      groupStreamingStoppedRef.current = {
        ...groupStreamingStoppedRef.current,
        [groupId]: false,
      }

      console.log(`🔄 [RETRY-GROUP] 重置组${groupId}停止标志为 false`)

      console.log(`🔄 [RETRY-GROUP] 开始重试组${groupId}(${group.isBaseGroup ? '基准组' : '对照组'})消息`, {
        groupId,
        index,
        isProcessing: group.isProcessing,
        isStreamingStopped: groupStreamingStoppedRef.current[groupId] || false,
        chatMessagesLength: group.chatMessages.length,
      })

      if (group.isProcessing) return

      const messageToRetry = group.chatMessages[index]
      if (!messageToRetry || messageToRetry.type !== 'ai') {
        console.error('无效的重试消息')
        return
      }

      // 找到对应的用户输入（允许为空，和主聊天的handleSendMessage逻辑一致）
      const userInput = messageToRetry.userInput || ''

      // 设置组处理状态
      setComparisonGroupsData(prevGroups => prevGroups.map(g => (g.id === groupId ? { ...g, isProcessing: true } : g)))

      try {
        // 重置当前AI消息为加载状态
        setComparisonGroupsData(prev =>
          prev.map(g =>
            g.id === groupId
              ? {
                  ...g,
                  chatMessages: g.chatMessages.filter((_, i) => i !== index), // 删除要重试的消息
                }
              : g,
          ),
        )

        // 重置AI思考过程和工具调用的展开状态
        setGroupReasoningExpanded(prev => {
          const newExpanded = { ...prev }
          if (newExpanded[groupId]) {
            delete newExpanded[groupId][index]
          }
          return newExpanded
        })
        setGroupToolCallExpanded(prev => {
          const newExpanded = { ...prev }
          if (newExpanded[groupId]) {
            delete newExpanded[groupId][index]
          }
          return newExpanded
        })

        // 获取提示词详情
        const promptDetail = await PromptService.getPromptDetail(promptId, {
          with_commit: true,
          with_draft: true,
          with_default_config: true,
          workspaceId: workspaceId,
        })

        if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
          throw new Error('无法获取提示词详情')
        }

        // 获取该AI消息之前的所有消息（不包括要重试的AI消息）
        // 注意：重试时不添加新的用户消息，只使用现有的消息历史
        const existingMessages = group.chatMessages
          .slice(0, index)
          .filter(msg => msg.type === 'user' || msg.type === 'ai') // 过滤掉 system 类型
          .map(msg => ({
            type: msg.type as 'user' | 'ai',
            content: msg.content,
            timestamp: msg.timestamp,
            userInput: msg.userInput,
          }))

        // 调用 callGroupAPI
        // 注意：重试时不添加用户消息，只使用现有的消息历史和userInput来构建请求
        await callGroupAPI(
          existingMessages,
          { type: 'user' as const, content: userInput, timestamp: new Date().toLocaleString('zh-CN') },
          group.parameters,
          group.modelConfig,
          promptDetail.prompt[0],
          userInput,
          group.messages,
          groupId,
          true, // isRetry: true
        )
      } catch (error) {
        console.error(`组${groupId}重试准备失败:`, error)
        setComparisonGroupsData(prev => prev.map(g => (g.id === groupId ? { ...g, isProcessing: false } : g)))

        // 恢复原来的AI消息，显示错误
        setComparisonGroupsData(prev =>
          prev.map(g =>
            g.id === groupId
              ? {
                  ...g,
                  chatMessages: [
                    ...g.chatMessages,
                    {
                      ...messageToRetry,
                      content: t('hooks.prompts.useDebugInputAreaGroup.retryFailedWithMessage', {
                        message: error instanceof Error ? error.message : t('hooks.prompts.useDebugInputAreaGroup.unknownError'),
                      }),
                    },
                  ],
                }
              : g,
          ),
        )

        // 标记错误消息为完成
        const updatedGroup = comparisonGroupsData.find(g => g.id === groupId)
        if (updatedGroup) {
          setGroupCompletedMessages(prev => ({
            ...prev,
            [groupId]: new Set([...(prev[groupId] || []), updatedGroup.chatMessages.length - 1]),
          }))
        }
      }
    },
    [
      comparisonGroupsData,
      setComparisonGroupsData,
      setGroupStreamingStopped,
      groupStreamingStoppedRef,
      setGroupReasoningExpanded,
      setGroupToolCallExpanded,
      promptId,
      workspaceId,
      callGroupAPI,
      setGroupCompletedMessages,
      t,
    ],
  )

  /**
   * 停止组的流式响应
   */
  const handleStopGroupStreaming = useCallback(
    (groupId: number) => {
      console.log(`🛑 [PromptEditPage] 用户点击停止组${groupId}的调试流式响应`)

      // 取消正在进行的流式请求 - 参考快捷优化的逻辑
      if (groupAbortControllerRefs.current[groupId]) {
        console.log(`🛑 [PromptEditPage] 取消组${groupId}的流式请求`)
        groupAbortControllerRefs.current[groupId]!.abort()
        groupAbortControllerRefs.current[groupId] = null
      }

      // 停止当前调试请求并清理延迟队列 - 修复停止后再发送消息显示上次内容的问题
      if (groupDebugControllerRefs.current[groupId]) {
        console.log(`🛑 [PromptEditPage] 调用组${groupId}的 debugController.cancel() 清理延迟队列`)
        groupDebugControllerRefs.current[groupId]!.cancel()
        groupDebugControllerRefs.current[groupId] = null
      }

      // 停止处理状态 - 参考快捷优化的逻辑
      setComparisonGroupsData(prev =>
        prev.map(g => {
          if (g.id === groupId) {
            return { ...g, isProcessing: false }
          }
          return g
        }),
      )

      // 将当前的流式内容设置为最终结果 - 参考快捷优化的逻辑
      setComparisonGroupsData(prev =>
        prev.map(g => {
          if (g.id !== groupId) return g

          const newChatMessages = [...g.chatMessages]
          // 找到最后一条AI消息的索引
          let lastAIIndex = -1
          for (let i = newChatMessages.length - 1; i >= 0; i--) {
            if (newChatMessages[i].type === 'ai') {
              lastAIIndex = i
              break
            }
          }

          if (lastAIIndex !== -1) {
            const lastMessage = newChatMessages[lastAIIndex]
            console.log(`📝 [PromptEditPage] 将组${groupId}的流式内容设为最终结果:`, lastMessage.content?.substring(0, 100) + '...')

            // 如果内容还是 "......"，说明还没有任何输出，清空内容
            if (lastMessage.content === '......') {
              newChatMessages[lastAIIndex] = {
                ...lastMessage,
                content: '',
              }
              console.log(`🛑 [PromptEditPage] 清空组${groupId}未开始输出的AI消息`)
            }

            // 标记为完成状态
            setGroupCompletedMessages(prevCompleted => {
              const oldCompleted = prevCompleted[groupId] || new Set()
              const newCompleted = new Set([...oldCompleted, lastAIIndex])
              return {
                ...prevCompleted,
                [groupId]: newCompleted,
              }
            })
          }

          return { ...g, chatMessages: newChatMessages }
        }),
      )

      // 手动调用 disableAutoReadOnly()，因为 onComplete 回调可能无法正确检测到取消状态
      // 这是因为局部 abortControllerRef 和全局 groupAbortControllerRefs 的同步问题
      // 每个组调用了2次 enableAutoReadOnly()，所以需要调用2次 disableAutoReadOnly()
      disableAutoReadOnly() // 对应 useDebugInputArea.ts 中的调用
      disableAutoReadOnly() // 对应 callGroupAPI onStart 中的调用

      console.log(`✅ [PromptEditPage] 组${groupId}的调试流式响应已停止`)
    },
    [groupAbortControllerRefs, groupDebugControllerRefs, setComparisonGroupsData, setGroupCompletedMessages, disableAutoReadOnly],
  )

  return {
    handleSendComparisonMessage,
    handleClearComparisonChat,
    handleGroupRetryLastMessage,
    handleStopGroupStreaming,
  }
}
