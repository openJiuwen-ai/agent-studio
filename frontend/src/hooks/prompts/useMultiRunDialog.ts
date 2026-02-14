import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import type { DebugMessage, DebugMockTool, DebugStreamingRequest, DebugStreamingResponse } from '@test-agentstudio/api-client'
import type { ChatMessage } from '@/components/Prompts'
import type { Model, ModelConfig } from '@/types/promptType'
import { extractDebugErrorMessage, processToolCallsIncremental, checkValidModel } from '@/utils/prompts/promptEditPageUtils'
import { PromptService } from '@test-agentstudio/api-client'

interface UseMultiRunDialogOptions {
  // 多实例消息状态
  multiRunChatMessages: Array<ChatMessage[]>
  setMultiRunChatMessages: React.Dispatch<React.SetStateAction<Array<ChatMessage[]>>>

  // 多实例处理状态
  multiRunProcessing: boolean[]
  setMultiRunProcessing: React.Dispatch<React.SetStateAction<boolean[]>>

  // AbortController refs
  multiRunAbortControllerRefs: React.MutableRefObject<Array<AbortController | null>>
  multiRunDebugControllerRefs: React.MutableRefObject<Array<{ cancel: () => void } | null>>

  // 展开状态
  multiRunExpandedToolCallMessages: Set<number>
  setMultiRunExpandedToolCallMessages: React.Dispatch<React.SetStateAction<Set<number>>>
  multiRunExpandedReasoningMessages: Set<number>
  setMultiRunExpandedReasoningMessages: React.Dispatch<React.SetStateAction<Set<number>>>

  // 辅助函数
  validateAllPlaceholders: () => boolean
  buildDebugRequest: (chatMessages: DebugMessage[], userInput: string, promptData: unknown) => DebugStreamingRequest
  executeStreamingDebugRequest: (
    debugRequest: DebugStreamingRequest,
    mockTools: DebugMockTool[],
    options?: Record<string, unknown>,
  ) => Promise<{ cancel: () => void } | null>
  disableAutoReadOnly: () => void

  // 多实例运行相关
  runCount: number
  promptId: string
  workspaceId: string

  // 模型相关
  selectedModel: Model | null
  modelConfig: ModelConfig
  availableModels: Model[]
  showSnackbar: (message: string, severity?: 'success' | 'error' | 'warning' | 'info') => void

  // 主对话相关（用于 handleAdoptConversation）
  chatMessages: ChatMessage[]
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
  setCompletedMessages: React.Dispatch<React.SetStateAction<Set<number>>>
  scrollToBottom: () => void
  saveDebugContext: (
    messages: ChatMessage[],
    debugTraceInfo?: { debug_id?: string; debug_trace_key?: string },
    cost_ms?: number,
    lastResponse?: DebugStreamingResponse,
  ) => Promise<void>
  debugTraceInfo?: { debug_id?: string; debug_trace_key?: string }
  setMultiRunDialogOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export const useMultiRunDialog = (options: UseMultiRunDialogOptions) => {
  const {
    multiRunChatMessages,
    setMultiRunChatMessages,
    multiRunProcessing,
    setMultiRunProcessing,
    multiRunAbortControllerRefs,
    multiRunDebugControllerRefs,
    multiRunExpandedToolCallMessages,
    setMultiRunExpandedToolCallMessages,
    multiRunExpandedReasoningMessages,
    setMultiRunExpandedReasoningMessages,
    validateAllPlaceholders,
    buildDebugRequest,
    executeStreamingDebugRequest,
    disableAutoReadOnly,
    runCount,
    promptId,
    workspaceId,
    selectedModel,
    modelConfig,
    availableModels,
    showSnackbar,
    chatMessages,
    setChatMessages,
    setCompletedMessages,
    scrollToBottom,
    saveDebugContext,
    debugTraceInfo,
  setMultiRunDialogOpen,
} = options

  const { t } = useTranslation()

  // 处理单个多实例的调试接口调用
  const handleMultiRunInstanceCall = useCallback(
    async (instanceIndex: number, userInput: string, promptData: unknown) => {
      // 检查所有 placeholder 消息是否有效
      if (!validateAllPlaceholders()) {
        return
      }

      const startTime = Date.now() // 记录开始时间用于计算耗时
      console.log(`🔥 实例${instanceIndex + 1}开始处理`, new Date().toISOString())

      try {
        // 准备调试请求数据 - 与提示词调试模块保持一致
        // 注意：需要手动添加新的用户消息（如果有），因为 setMultiRunChatMessages 是异步的，multiRunChatMessages 可能还没有更新
        const hasUserInput = userInput.trim() !== ''
        const debugMessages: DebugMessage[] = [
          ...multiRunChatMessages[instanceIndex]
            .filter(msg => {
              // 过滤掉内容为 "......" 或空内容的AI消息（被停止或未完成的消息）
              if (msg.type === 'ai' && (msg.content === '......' || msg.content.trim() === '')) {
                console.log(`🧹 [FILTER-MULTI-${instanceIndex + 1}] 过滤掉不完整的AI消息`, { content: msg.content })
                return false
              }
              return true
            })
            .map(msg => ({
              role: msg.type === 'user' ? ('user' as const) : ('assistant' as const),
              content: msg.content,
              parts: [],
            })),
          // 如果有新的用户输入，手动添加到 debugMessages 中
          ...(hasUserInput
            ? [
                {
                  role: 'user' as const,
                  content: userInput,
                  parts: [],
                },
              ]
            : []),
        ]

        // 创建AI消息占位符，用于流式更新
        const aiMessage = {
          type: 'ai' as const,
          content: '......', // 显示加载指示器
          timestamp: new Date().toLocaleString('zh-CN'),
          userInput: userInput,
        }

        // 计算AI消息的索引（在添加之前，添加后索引会+1）
        const aiMessageIndex = multiRunChatMessages[instanceIndex].length

        // 添加AI消息占位符到对应实例
        setMultiRunChatMessages(prev => {
          const updated = [...prev]
          updated[instanceIndex] = [...updated[instanceIndex], aiMessage]
          return updated
        })

        // 构建调试请求
        const debugRequest = buildDebugRequest(debugMessages, userInput, promptData)
        const mockTools = debugRequest.mock_tools

        // 取消之前的请求（如果存在）- 参考快捷优化的逻辑
        if (multiRunAbortControllerRefs.current[instanceIndex]) {
          console.log(`🛑 [handleMultiRunInstanceCall] 取消实例${instanceIndex + 1}之前的流式请求`)
          multiRunAbortControllerRefs.current[instanceIndex]!.abort()
          multiRunAbortControllerRefs.current[instanceIndex] = null
        }

        // 创建新的 AbortController - 参考快捷优化的逻辑
        const instanceAbortControllerRef: React.MutableRefObject<AbortController | null> = {
          current: null,
        }
        instanceAbortControllerRef.current = new AbortController()
        multiRunAbortControllerRefs.current[instanceIndex] = instanceAbortControllerRef.current
        console.log(`🆕 [handleMultiRunInstanceCall] 为实例${instanceIndex + 1}创建新的 AbortController`)

        // 使用通用函数执行流式调试请求，并保存返回的 debugController
        const debugController = await executeStreamingDebugRequest(debugRequest, mockTools, {
          // 消息管理
          messageIndex: aiMessageIndex,
          messages: multiRunChatMessages[instanceIndex],
          setMessages: (updater: (prev: ChatMessage[]) => ChatMessage[]) => {
            setMultiRunChatMessages(prev => {
              const updated = [...prev]
              updated[instanceIndex] = updater(updated[instanceIndex])
              return updated
            })
          },

          // 处理状态管理
          isProcessing: multiRunProcessing[instanceIndex],
          setIsProcessing: (value: boolean) => {
            setMultiRunProcessing(prev => {
              const updated = [...prev]
              updated[instanceIndex] = value
              return updated
            })
          },

          // 流控制（参考快捷优化的 AbortController 模式）
          abortControllerRef: instanceAbortControllerRef,

          // 其他选项
          userInput: userInput,
          scrollToBottom: false, // 多实例不需要自动滚动
          autoExpandReasoning: false, // 多实例不自动展开
          autoExpandToolCalls: false,
          saveContext: false, // 多实例不保存上下文

          // 错误处理回调
          onError: (error: Error, messageIndex: number) => {
            console.error(`❌ [MULTI-RUN-${instanceIndex + 1}] 流式调试API调用失败:`, error)
            disableAutoReadOnly()

            // 确保错误信息被添加到AI消息中
            setMultiRunChatMessages(prev => {
              const updated = [...prev]
              const instanceMessages = [...updated[instanceIndex]]
              const targetMessage = instanceMessages[messageIndex]

              // 如果目标位置是AI消息，直接更新它
              if (targetMessage && targetMessage.type === 'ai') {
                instanceMessages[messageIndex] = {
                  ...targetMessage,
                  content: extractDebugErrorMessage(error),
                }
              } else {
                // 如果目标位置不是AI消息，尝试找到最后一条AI消息并更新它
                let lastAIMessageIndex = -1
                for (let i = instanceMessages.length - 1; i >= 0; i--) {
                  if (instanceMessages[i].type === 'ai') {
                    lastAIMessageIndex = i
                    break
                  }
                }

                if (lastAIMessageIndex >= 0) {
                  // 更新最后一条AI消息
                  instanceMessages[lastAIMessageIndex] = {
                    ...instanceMessages[lastAIMessageIndex],
                    content: extractDebugErrorMessage(error),
                  }
                } else {
                  // 如果找不到AI消息，创建一个新的AI错误消息
                  const errorMessage = {
                    type: 'ai' as const,
                    content: extractDebugErrorMessage(error),
                    timestamp: new Date().toLocaleString('zh-CN'),
                    userInput: userInput,
                  }
                  instanceMessages.push(errorMessage)
                }
              }

              updated[instanceIndex] = instanceMessages
              return updated
            })

            // 设置该实例为非处理状态
            setMultiRunProcessing(prev => {
              const updated = [...prev]
              updated[instanceIndex] = false
              return updated
            })
          },

          // 自定义流式处理器
          customStreamHandler: (response: DebugStreamingResponse, mockTools?: Array<{ name: string; mock_response: string }>) => {
            // 检查是否已被用户停止（通过 AbortController）- 参考快捷优化的逻辑
            if (instanceAbortControllerRef.current?.signal.aborted) {
              console.log(`🛑 [STREAM-MULTI-${instanceIndex + 1}] 忽略响应，流已被停止（通过 AbortController）`)
              return
            }

            // 处理流式响应
            if (response.delta && (response.delta.content || response.delta.reasoning_content || response.delta.tool_calls)) {
              setMultiRunChatMessages(prev => {
                const updated = [...prev]
                const instanceMessages = [...updated[instanceIndex]]
                const lastMessageIndex = instanceMessages.length - 1
                const lastMessage = instanceMessages[lastMessageIndex]

                if (lastMessage && lastMessage.type === 'ai') {
                  const updates: Record<string, unknown> = {}

                  // 获取当前消息的工具调用状态，用于判断是否处于工具调用阶段
                  const existingToolCalls = (lastMessage as ChatMessage & { toolCalls?: unknown[] }).toolCalls || []
                  const hasNewToolCalls = response.delta?.tool_calls && response.delta.tool_calls.length > 0

                  // 处理工具调用信息（优先处理，因为工具调用可能会影响内容的处理）
                  if (hasNewToolCalls && response.delta && response.delta.tool_calls) {
                    // 转换mockTools类型以匹配processToolCallsIncremental的期望
                    const convertedMockTools: DebugMockTool[] = (mockTools || []).map(tool => ({
                      name: tool.name,
                      mock_value: tool.mock_response,
                      mock_response: tool.mock_response,
                    }))
                    const updatedToolCalls = processToolCallsIncremental(existingToolCalls, response.delta.tool_calls, convertedMockTools)
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
                    const newReasoningContent = (lastMessage as ChatMessage & { reasoningContent?: string }).reasoningContent || ''
                    updates.reasoningContent = newReasoningContent + response.delta.reasoning_content
                  }

                  const updatedMessage = {
                    ...lastMessage,
                    ...updates,
                  }
                  instanceMessages[lastMessageIndex] = updatedMessage
                  updated[instanceIndex] = instanceMessages

                  // 自动展开AI思考过程和工具调用
                  if (updates.reasoningContent && !multiRunExpandedReasoningMessages.has(lastMessageIndex)) {
                    setMultiRunExpandedReasoningMessages(prev => new Set([...prev, lastMessageIndex]))
                  }
                  if (
                    updates.toolCalls &&
                    Array.isArray(updates.toolCalls) &&
                    updates.toolCalls.length > 0 &&
                    !multiRunExpandedToolCallMessages.has(lastMessageIndex)
                  ) {
                    setMultiRunExpandedToolCallMessages(prev => new Set([...prev, lastMessageIndex]))
                  }
                }
                return updated
              })
            }

            // 处理完成信息（token和耗时）
            if (response.delta === null && response.usage) {
              const cost_ms = Date.now() - startTime

              setTimeout(() => {
                setMultiRunChatMessages(prev => {
                  const updated = [...prev]
                  const instanceMessages = [...updated[instanceIndex]]
                  const lastMessageIndex = instanceMessages.length - 1
                  const lastMessage = instanceMessages[lastMessageIndex]

                  if (lastMessage && lastMessage.type === 'ai') {
                    const updatedMessage = {
                      ...lastMessage,
                      input_tokens: response.usage?.input_tokens?.toString() || '0',
                      output_tokens: response.usage?.output_tokens?.toString() || '0',
                      cost_ms: cost_ms.toString(),
                    }
                    instanceMessages[lastMessageIndex] = updatedMessage
                    updated[instanceIndex] = instanceMessages
                  }
                  return updated
                })
              }, 100)
            }
          },
        })

        // 保存 debugController 以便在停止时清理延迟队列
        if (debugController) {
          multiRunDebugControllerRefs.current[instanceIndex] = debugController
          console.log(`💾 [handleMultiRunInstanceCall] 为实例${instanceIndex + 1}保存 debugController`)
        }
      } catch (error) {
        console.error(`实例${instanceIndex + 1}调试请求准备失败:`, error)
        disableAutoReadOnly()

        // 添加错误消息到对应实例
        const errorMessage = {
          type: 'ai' as const,
          content: extractDebugErrorMessage(error),
          timestamp: new Date().toLocaleString('zh-CN'),
          userInput: userInput,
        }

        setMultiRunChatMessages(prev => {
          const updated = [...prev]
          const instanceMessages = [...updated[instanceIndex]]
          if (instanceMessages[instanceMessages.length - 1]?.content === '......') {
            // 如果最后一条是加载消息，替换它
            instanceMessages[instanceMessages.length - 1] = errorMessage
          } else {
            // 否则添加错误消息
            instanceMessages.push(errorMessage)
          }
          updated[instanceIndex] = instanceMessages
          return updated
        })

        // 设置该实例为非处理状态
        setMultiRunProcessing(prev => {
          const updated = [...prev]
          updated[instanceIndex] = false
          return updated
        })

        // 取消流式请求 - 参考快捷优化的逻辑
        if (multiRunAbortControllerRefs.current[instanceIndex]) {
          console.log(`🛑 [handleMultiRunInstanceCall] 取消实例${instanceIndex + 1}的流式请求`)
          multiRunAbortControllerRefs.current[instanceIndex]!.abort()
          multiRunAbortControllerRefs.current[instanceIndex] = null
        }
      }
    },
    [
      validateAllPlaceholders,
      multiRunChatMessages,
      setMultiRunChatMessages,
      multiRunProcessing,
      setMultiRunProcessing,
      multiRunAbortControllerRefs,
      multiRunDebugControllerRefs,
      multiRunExpandedToolCallMessages,
      setMultiRunExpandedToolCallMessages,
      multiRunExpandedReasoningMessages,
      setMultiRunExpandedReasoningMessages,
      buildDebugRequest,
      executeStreamingDebugRequest,
      disableAutoReadOnly,
      runCount,
      promptId,
      workspaceId,
    ],
  )

  // 处理多实例发送消息
  const handleMultiRunSendMessage = useCallback(
    async (message: string) => {
      // 检查所有 placeholder 消息是否有效
      if (!validateAllPlaceholders()) {
        return
      }

      // 检查是否配置了有效的模型
      if (!checkValidModel(selectedModel, modelConfig, availableModels)) {
        showSnackbar(t('hooks.prompts.useMultiRunDialog.configValidModelFirst'), 'error')
        return
      }

      console.log('🚀 [MULTI-RUN] 开始发送消息', {
        message: message.trim(),
        runCount,
      })

      // 如果用户没有在输入框中输入消息，根据最后一条消息类型决定逻辑
      if (!message.trim()) {
        // 检查每个实例的最后一条消息类型
        const instancesWithAIMessages: Array<{ instanceIndex: number; lastAIMessageIndex: number }> = []
        let hasInstanceWithUserMessage = false

        for (let i = 0; i < runCount; i++) {
          const instanceMessages = multiRunChatMessages[i]
          const lastMessage = instanceMessages.length > 0 ? instanceMessages[instanceMessages.length - 1] : null

          // 如果最后一条消息是user消息，标记为有user消息的实例
          if (lastMessage && lastMessage.type === 'user') {
            hasInstanceWithUserMessage = true
          } else {
            // 如果最后一条消息是AI消息或没有消息，查找最后一条AI消息的索引
            let lastAIMessageIndex = -1
            for (let j = instanceMessages.length - 1; j >= 0; j--) {
              if (instanceMessages[j].type === 'ai') {
                lastAIMessageIndex = j
                break
              }
            }

            if (lastAIMessageIndex >= 0) {
              instancesWithAIMessages.push({ instanceIndex: i, lastAIMessageIndex })
            }
          }
        }

        // 如果至少有一个实例的最后一条消息是user消息，则继续执行正常的发送逻辑
        if (hasInstanceWithUserMessage) {
          console.log('📝 [MULTI-RUN] 输入为空但至少有一个实例的最后一条是用户消息，继续执行正常发送逻辑')
          // 继续执行下面的正常逻辑，不执行重试
        } else if (instancesWithAIMessages.length > 0) {
          // 如果所有实例的最后一条消息都是AI消息或没有消息，且有AI消息，执行重试逻辑
          console.log('🔄 [MULTI-RUN] 输入为空，执行重试逻辑', {
            instancesWithAIMessages: instancesWithAIMessages.map(inst => ({
              instanceIndex: inst.instanceIndex,
              lastAIMessageIndex: inst.lastAIMessageIndex,
            })),
          })

          // 检查是否有实例正在处理中
          const isAnyInstanceProcessing = instancesWithAIMessages.some(inst => multiRunProcessing[inst.instanceIndex])
          if (isAnyInstanceProcessing) {
            console.log('⚠️ [MULTI-RUN] 有实例正在处理中，取消重试')
            return
          }

          try {
            // 预先获取提示词详情，所有实例共享这个数据
            const promptDetail = await PromptService.getPromptDetail(promptId, {
              withCommit: true,
              withDraft: true,
              withDefaultConfig: true,
              workspaceId: workspaceId,
            })

            if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
              throw new Error('无法获取提示词详情')
            }

            // 为每个有AI消息的实例执行重试
            const retryPromises = instancesWithAIMessages.map(async ({ instanceIndex, lastAIMessageIndex }) => {
              const messageToRetry = multiRunChatMessages[instanceIndex][lastAIMessageIndex]
              if (!messageToRetry || messageToRetry.type !== 'ai') {
                return
              }

              // 找到对应的用户输入（允许为空，和主聊天的handleSendMessage逻辑一致）
              const userInput = messageToRetry.userInput || ''

              // 设置实例处理状态
              setMultiRunProcessing(prev => {
                const updated = [...prev]
                updated[instanceIndex] = true
                return updated
              })

              try {
                // 重置当前AI消息为加载状态（删除要重试的消息）
                setMultiRunChatMessages(prev => {
                  const updated = [...prev]
                  updated[instanceIndex] = updated[instanceIndex].filter((_, i) => i !== lastAIMessageIndex)
                  return updated
                })

                // 调用 handleMultiRunInstanceCall 进行重试
                // 注意：重试时不添加用户消息，只使用现有的消息历史和userInput来构建请求
                await handleMultiRunInstanceCall(instanceIndex, userInput, promptDetail.prompt[0])
              } catch (error) {
                console.error(`实例${instanceIndex + 1}重试准备失败:`, error)
                setMultiRunProcessing(prev => {
                  const updated = [...prev]
                  updated[instanceIndex] = false
                  return updated
                })

                // 恢复原来的AI消息，显示错误
                setMultiRunChatMessages(prev => {
                  const updated = [...prev]
                  updated[instanceIndex] = [
                    ...updated[instanceIndex],
                    {
                      ...messageToRetry,
                      content: t('hooks.prompts.useMultiRunDialog.retryFailedWithMessage', {
                        message: error instanceof Error ? error.message : t('hooks.prompts.useMultiRunDialog.unknownError'),
                      }),
                    },
                  ]
                  return updated
                })
              }
            })

            // 等待所有重试完成（并行执行）
            await Promise.allSettled(retryPromises)

            console.log('✅ [MULTI-RUN] 所有实例重试完成')
          } catch (error) {
            console.error('❌ [MULTI-RUN] 重试失败:', error)
          }

          return
        } else {
          // 如果没有AI消息，不添加用户消息，但继续执行其他逻辑
          console.log('⚠️ [MULTI-RUN] 输入为空且没有可重试的AI消息，继续执行发送逻辑（不添加用户消息）')
          // 继续执行后面的逻辑，但跳过添加用户消息的部分
        }
      }

      const timestamp = new Date().toLocaleString('zh-CN')
      const currentInput = message.trim() ? message : ''
      const hasUserInput = message.trim() !== ''

      // 只有在消息不为空时才添加用户消息到对话历史
      if (hasUserInput) {
        const userMessage = {
          type: 'user' as const,
          content: message,
          timestamp,
        }

        // 为所有实例添加用户消息
        const newMultiRunChatMessages = multiRunChatMessages.map(messages => [...messages, userMessage])
        setMultiRunChatMessages(newMultiRunChatMessages)
      }

      // 设置所有实例为处理中状态
      setMultiRunProcessing(Array(runCount).fill(true))

      try {
        // 预先获取提示词详情，所有实例共享这个数据
        console.log(`🔍 预先获取提示词详情`, new Date().toISOString())
        const promptDetail = await PromptService.getPromptDetail(promptId, {
          withCommit: true,
          withDraft: true,
          withDefaultConfig: true,
          workspaceId: workspaceId,
        })

        if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
          throw new Error('无法获取提示词详情')
        }

        console.log(`✅ 提示词详情获取完成，开始并发发起${runCount}个调试请求`, new Date().toISOString())

        // 为每个运行实例调用真实的调试接口 - 现在是真正的并发
        for (let i = 0; i < runCount; i++) {
          console.log(`📤 发起实例${i + 1}请求`, new Date().toISOString())
          handleMultiRunInstanceCall(i, currentInput, promptDetail.prompt[0]) // 传递预获取的prompt详情
        }
        console.log(`🚀 所有${runCount}个请求已同时发起`, new Date().toISOString())
      } catch (error) {
        console.error('❌ 获取提示词详情失败:', error)
        // 重置所有实例的处理状态
        setMultiRunProcessing(Array(runCount).fill(false))

        // 取消所有实例的流式请求 - 参考快捷优化的逻辑
        multiRunAbortControllerRefs.current.forEach((controller, index) => {
          if (controller) {
            console.log(`🛑 [handleMultiRunSendMessage] 取消实例${index + 1}的流式请求`)
            controller.abort()
            multiRunAbortControllerRefs.current[index] = null
          }
        })

        // 为所有实例添加错误消息
        const errorMessage = {
          type: 'ai' as const,
          content: t('hooks.prompts.useMultiRunDialog.getPromptDetailFailedWithMessage', {
            message: error instanceof Error ? error.message : t('hooks.prompts.useMultiRunDialog.unknownError'),
          }),
          timestamp: new Date().toLocaleString('zh-CN'),
          userInput: currentInput,
        }

        setMultiRunChatMessages(prev => {
          return prev.map(messages => [...messages, errorMessage])
        })
      }
    },
    [
      validateAllPlaceholders,
      selectedModel,
      modelConfig,
      availableModels,
      checkValidModel,
      showSnackbar,
      runCount,
      multiRunChatMessages,
      setMultiRunChatMessages,
      multiRunProcessing,
      setMultiRunProcessing,
      multiRunAbortControllerRefs,
      promptId,
      workspaceId,
      handleMultiRunInstanceCall,
      t,
    ],
  )

  // 处理多实例重新生成消息
  const handleRegenerateMessage = useCallback(
    async (instanceIndex: number, messageIndex: number) => {
      try {
        // 获取指定实例的消息历史
        const instanceMessages = multiRunChatMessages[instanceIndex]
        if (!instanceMessages || messageIndex < 0 || messageIndex >= instanceMessages.length) {
          console.error('Invalid instance or message index')
          return
        }

        // 确保要重试的是AI消息
        const targetMessage = instanceMessages[messageIndex]
        if (targetMessage.type !== 'ai') {
          console.error('Can only retry AI messages')
          return
        }

        // 获取重试消息前的所有消息历史（不包括要重试的AI消息）
        const messagesBeforeRetry = instanceMessages.slice(0, messageIndex)

        // 获取最后一条用户消息作为重试的输入（如果有的话）
        const lastUserMessage = messagesBeforeRetry.filter(msg => msg.type === 'user').pop()
        const userInput = lastUserMessage ? lastUserMessage.content : ''

        console.log(`🔄 [REGENERATE-MULTI-${instanceIndex + 1}] 找到的用户消息:`, userInput || '(空消息)')

        // 设置该实例为处理状态
        setMultiRunProcessing(prev => {
          const updated = [...prev]
          updated[instanceIndex] = true
          return updated
        })

        // 删除要重试的AI消息，准备重新生成
        setMultiRunChatMessages(prev => {
          const updated = [...prev]
          updated[instanceIndex] = messagesBeforeRetry
          return updated
        })

        // 获取当前的提示词详情
        const promptDetail = await PromptService.getPromptDetail(promptId, {
          withCommit: true,
          withDraft: true,
          withDefaultConfig: true,
          workspaceId: workspaceId,
        })

        if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
          throw new Error('无法获取提示词详情')
        }

        // 为该实例重新调用调试接口
        await handleMultiRunInstanceCall(instanceIndex, userInput, promptDetail.prompt[0])

        console.log(`✅ 实例${instanceIndex + 1}重试成功`)
      } catch (error) {
        console.error(`❌ 实例${instanceIndex + 1}重试失败:`, error)

        // 重试失败时，恢复处理状态
        setMultiRunProcessing(prev => {
          const updated = [...prev]
          updated[instanceIndex] = false
          return updated
        })

        // 取消流式请求 - 参考快捷优化的逻辑
        if (multiRunAbortControllerRefs.current[instanceIndex]) {
          console.log(`🛑 [handleRegenerateMessage] 取消实例${instanceIndex + 1}的流式请求`)
          multiRunAbortControllerRefs.current[instanceIndex]!.abort()
          multiRunAbortControllerRefs.current[instanceIndex] = null
        }

        // 添加错误消息
        const errorMessage = {
          type: 'ai' as const,
          content: t('hooks.prompts.useMultiRunDialog.retryFailedWithMessage', {
            message: error instanceof Error ? error.message : t('hooks.prompts.useMultiRunDialog.unknownError'),
          }),
          timestamp: new Date().toLocaleString('zh-CN'),
        }

        setMultiRunChatMessages(prev => {
          const updated = [...prev]
          updated[instanceIndex] = [...updated[instanceIndex], errorMessage]
          return updated
        })
      }
    },
    [
      multiRunChatMessages,
      setMultiRunChatMessages,
      multiRunProcessing,
      setMultiRunProcessing,
      multiRunAbortControllerRefs,
      promptId,
      workspaceId,
      handleMultiRunInstanceCall,
      t,
    ],
  )

  // 停止多实例运行对比的流式响应 - 参考快捷优化的停止逻辑
  const handleStopMultiRunStreaming = useCallback(
    (instanceIndex?: number) => {
      if (instanceIndex !== undefined) {
        // 停止指定实例
        console.log(`🛑 [PromptEditPage] 用户点击停止实例${instanceIndex + 1}的调试流式响应`)

        // 取消正在进行的流式请求 - 参考快捷优化的逻辑
        if (multiRunAbortControllerRefs.current[instanceIndex]) {
          console.log(`🛑 [PromptEditPage] 取消实例${instanceIndex + 1}的流式请求`)
          multiRunAbortControllerRefs.current[instanceIndex]!.abort()
          multiRunAbortControllerRefs.current[instanceIndex] = null
        }

        // 停止当前调试请求并清理延迟队列 - 修复停止后再发送消息显示上次内容的问题
        if (multiRunDebugControllerRefs.current[instanceIndex]) {
          console.log(`🛑 [PromptEditPage] 调用实例${instanceIndex + 1}的 debugController.cancel() 清理延迟队列`)
          multiRunDebugControllerRefs.current[instanceIndex]!.cancel()
          multiRunDebugControllerRefs.current[instanceIndex] = null
        }

        // 停止处理状态 - 参考快捷优化的逻辑
        setMultiRunProcessing(prev => {
          const updated = [...prev]
          updated[instanceIndex] = false
          return updated
        })

        // 将当前的流式内容设置为最终结果 - 参考快捷优化的逻辑
        setMultiRunChatMessages(prev => {
          const updated = [...prev]
          const instanceMessages = [...updated[instanceIndex]]
          // 找到最后一条AI消息的索引
          let lastAIIndex = -1
          for (let i = instanceMessages.length - 1; i >= 0; i--) {
            if (instanceMessages[i].type === 'ai') {
              lastAIIndex = i
              break
            }
          }

          if (lastAIIndex !== -1) {
            const lastMessage = instanceMessages[lastAIIndex]
            console.log(`📝 [PromptEditPage] 将实例${instanceIndex + 1}的流式内容设为最终结果:`, lastMessage.content?.substring(0, 100) + '...')

            // 如果内容还是 "......"，说明还没有任何输出，清空内容
            if (lastMessage.content === '......') {
              instanceMessages[lastAIIndex] = {
                ...lastMessage,
                content: '',
              }
              console.log(`🛑 [PromptEditPage] 清空实例${instanceIndex + 1}未开始输出的AI消息`)
            }
          }

          updated[instanceIndex] = instanceMessages
          return updated
        })

        // 手动调用 disableAutoReadOnly()，因为 onComplete 回调可能无法正确检测到取消状态
        // 多实例运行每个实例只有1次 enableAutoReadOnly() 调用（在 useDebugInputArea.ts 中）
        disableAutoReadOnly()
        console.log(`✅ [PromptEditPage] 实例${instanceIndex + 1}的调试流式响应已停止`)
      } else {
        // 停止所有实例
        console.log('🛑 [PromptEditPage] 用户点击停止所有实例的调试流式响应')

        // 取消所有流式请求 - 参考快捷优化的逻辑
        multiRunAbortControllerRefs.current.forEach((controller, index) => {
          if (controller) {
            console.log(`🛑 [PromptEditPage] 取消实例${index + 1}的流式请求`)
            controller.abort()
            multiRunAbortControllerRefs.current[index] = null
          }
        })

        // 停止所有调试请求并清理延迟队列 - 修复停止后再发送消息显示上次内容的问题
        multiRunDebugControllerRefs.current.forEach((debugController, index) => {
          if (debugController) {
            console.log(`🛑 [PromptEditPage] 调用实例${index + 1}的 debugController.cancel() 清理延迟队列`)
            debugController.cancel()
            multiRunDebugControllerRefs.current[index] = null
          }
        })

        // 停止所有实例的处理状态 - 参考快捷优化的逻辑
        setMultiRunProcessing(Array(runCount).fill(false))

        // 将当前所有实例的流式内容设置为最终结果
        setMultiRunChatMessages(prev => {
          const updated = [...prev]
          for (let i = 0; i < updated.length; i++) {
            const instanceMessages = [...updated[i]]
            let lastAIIndex = -1
            for (let j = instanceMessages.length - 1; j >= 0; j--) {
              if (instanceMessages[j].type === 'ai') {
                lastAIIndex = j
                break
              }
            }

            if (lastAIIndex !== -1) {
              const lastMessage = instanceMessages[lastAIIndex]
              if (lastMessage.content === '......') {
                instanceMessages[lastAIIndex] = {
                  ...lastMessage,
                  content: '',
                }
              }
            }

            updated[i] = instanceMessages
          }
          return updated
        })

        // 手动调用 disableAutoReadOnly()，因为 onComplete 回调可能无法正确检测到取消状态
        // 为每个正在处理的实例调用一次 disableAutoReadOnly()
        const runningInstancesCount = multiRunProcessing.filter(processing => processing).length
        for (let i = 0; i < runningInstancesCount; i++) {
          disableAutoReadOnly()
        }
        console.log(`✅ [PromptEditPage] 所有实例的调试流式响应已停止，调用了${runningInstancesCount}次 disableAutoReadOnly()`)
      }
    },
    [
      multiRunAbortControllerRefs,
      multiRunDebugControllerRefs,
      setMultiRunProcessing,
      setMultiRunChatMessages,
      multiRunProcessing,
      runCount,
      disableAutoReadOnly,
    ],
  )

  // 清空所有多实例对话
  const handleClearAllMultiRun = useCallback(() => {
    setMultiRunChatMessages(
      Array(runCount)
        .fill(null)
        .map(() => []),
    )
    setMultiRunProcessing(Array(runCount).fill(false))
    // 取消所有实例的流式请求 - 参考快捷优化的逻辑
    multiRunAbortControllerRefs.current.forEach((controller, index) => {
      if (controller) {
        console.log(`🛑 [handleClearAllMultiRun] 取消实例${index + 1}的流式请求`)
        controller.abort()
        multiRunAbortControllerRefs.current[index] = null
      }
    })
    // 清空工具调用和AI思考过程展开状态
    setMultiRunExpandedToolCallMessages(new Set())
    setMultiRunExpandedReasoningMessages(new Set())
  }, [
    runCount,
    setMultiRunChatMessages,
    setMultiRunProcessing,
    multiRunAbortControllerRefs,
    setMultiRunExpandedToolCallMessages,
    setMultiRunExpandedReasoningMessages,
  ])

  // 清空单个实例对话
  const handleClearMultiRunInstance = useCallback(
    (index: number) => {
      const newMessages = [...multiRunChatMessages]
      newMessages[index] = []
      setMultiRunChatMessages(newMessages)

      const newProcessing = [...multiRunProcessing]
      newProcessing[index] = false
      setMultiRunProcessing(newProcessing)

      // 取消并清除 AbortController - 参考快捷优化的逻辑
      if (multiRunAbortControllerRefs.current[index]) {
        console.log(`🛑 [handleClearMultiRunInstance] 取消实例${index + 1}的流式请求`)
        multiRunAbortControllerRefs.current[index]!.abort()
        multiRunAbortControllerRefs.current[index] = null
      }
    },
    [multiRunChatMessages, setMultiRunChatMessages, multiRunProcessing, setMultiRunProcessing, multiRunAbortControllerRefs],
  )

  // 处理多实例删除消息
  const handleDeleteMultiRunMessage = useCallback(
    (instanceIndex: number, messageIndex: number) => {
      const newMessages = [...multiRunChatMessages]
      if (newMessages[instanceIndex]) {
        newMessages[instanceIndex] = newMessages[instanceIndex].filter((_, i) => i !== messageIndex)
        setMultiRunChatMessages(newMessages)
      }
    },
    [multiRunChatMessages, setMultiRunChatMessages],
  )

  // 处理多实例更新消息
  const handleUpdateMultiRunMessage = useCallback(
    (instanceIndex: number, messageIndex: number, content: string) => {
      const newMessages = [...multiRunChatMessages]
      if (newMessages[instanceIndex] && newMessages[instanceIndex][messageIndex]) {
        newMessages[instanceIndex] = [...newMessages[instanceIndex]]
        newMessages[instanceIndex][messageIndex] = {
          ...newMessages[instanceIndex][messageIndex],
          content: content,
        }
        setMultiRunChatMessages(newMessages)
      }
    },
    [multiRunChatMessages, setMultiRunChatMessages],
  )

  // 采纳多实例运行的对话历史
  const handleAdoptConversation = useCallback(
    (instanceIndex: number) => {
      // 获取指定实例的所有消息
      const instanceMessages = multiRunChatMessages[instanceIndex]
      if (!instanceMessages || instanceMessages.length === 0) return

      // 记录采纳前的消息数量，用于设置completedMessages
      const prevMessageCount = chatMessages.length

      // 将实例的消息添加到主对话历史
      setChatMessages(prev => {
        // 直接合并消息，不添加分隔标记
        return [...prev, ...instanceMessages]
      })

      // 标记所有新添加的消息为已完成，这样它们会显示控制按钮
      setCompletedMessages(prev => {
        const newCompleted = new Set(prev)
        const totalNewMessages = instanceMessages.length

        // 为新添加的每条消息设置完成状态
        for (let i = 0; i < totalNewMessages; i++) {
          newCompleted.add(prevMessageCount + i)
        }
        return newCompleted
      })

      // 滚动到底部显示新添加的内容
      setTimeout(scrollToBottom, 100)

      // 保存采纳后的调试上下文
      setTimeout(async () => {
        try {
          // 获取所选实例的最后一条AI消息的token/cost信息
          const selectedInstanceMessages = multiRunChatMessages[instanceIndex]
          let selectedInstanceStats = null

          // 从后往前查找最后一条AI消息的统计信息
          for (let i = selectedInstanceMessages.length - 1; i >= 0; i--) {
            const msg = selectedInstanceMessages[i]
            const msgWithStats = msg as ChatMessage & { cost_ms?: string; input_tokens?: string; output_tokens?: string }
            if (msg.type === 'ai' && (msgWithStats.cost_ms || msgWithStats.input_tokens || msgWithStats.output_tokens)) {
              selectedInstanceStats = {
                cost_ms: parseInt(msgWithStats.cost_ms || '0'),
                input_tokens: msgWithStats.input_tokens || '0',
                output_tokens: msgWithStats.output_tokens || '0',
              }
              break
            }
          }

          // 获取更新后的聊天消息并保存上下文
          setChatMessages(currentMessages => {
            if (currentMessages.length > 0) {
              // 使用选定实例的统计信息保存调试上下文
              const adoptedDebugTraceInfo = selectedInstanceStats
                ? {
                    debug_id: debugTraceInfo?.debug_id,
                    debug_trace_key: debugTraceInfo?.debug_trace_key,
                  }
                : undefined

              saveDebugContext(
                currentMessages,
                adoptedDebugTraceInfo,
                selectedInstanceStats?.cost_ms,
                selectedInstanceStats
                  ? ({
                      usage: {
                        input_tokens: parseInt(selectedInstanceStats.input_tokens),
                        output_tokens: parseInt(selectedInstanceStats.output_tokens),
                      },
                    } as DebugStreamingResponse)
                  : undefined,
              ).catch(error => console.error('❌ 采纳后保存调试上下文失败:', error))
            }
            return currentMessages
          })
          console.log('✅ 采纳对话后保存调试上下文，使用实例', instanceIndex + 1, '的统计信息:', selectedInstanceStats)
        } catch (error) {
          console.error('❌ 采纳后保存调试上下文失败:', error)
        }
      }, 200)

      // 关闭多实例运行对话框
      setMultiRunDialogOpen(false)
    },
    [multiRunChatMessages, chatMessages, setChatMessages, setCompletedMessages, scrollToBottom, saveDebugContext, debugTraceInfo, setMultiRunDialogOpen],
  )

  // 多实例运行工具调用展开状态切换函数
  const handleToggleMultiRunToolCallExpanded = useCallback(
    (index: number) => {
      setMultiRunExpandedToolCallMessages(prev => {
        const newSet = new Set(prev)
        if (newSet.has(index)) {
          newSet.delete(index)
        } else {
          newSet.add(index)
        }
        return newSet
      })
    },
    [setMultiRunExpandedToolCallMessages],
  )

  // 多实例运行AI思考过程展开状态切换函数
  const handleToggleMultiRunReasoningExpanded = useCallback(
    (index: number) => {
      setMultiRunExpandedReasoningMessages(prev => {
        const newSet = new Set(prev)
        if (newSet.has(index)) {
          newSet.delete(index)
        } else {
          newSet.add(index)
        }
        return newSet
      })
    },
    [setMultiRunExpandedReasoningMessages],
  )

  return {
    handleMultiRunSendMessage,
    handleRegenerateMessage,
    handleStopMultiRunStreaming,
    handleClearAllMultiRun,
    handleClearMultiRunInstance,
    handleDeleteMultiRunMessage,
    handleUpdateMultiRunMessage,
    handleAdoptConversation,
    handleToggleMultiRunToolCallExpanded,
    handleToggleMultiRunReasoningExpanded,
  }
}
