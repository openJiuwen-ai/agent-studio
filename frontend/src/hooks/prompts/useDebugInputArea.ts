import { useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  PromptService,
  type DebugStreamingRequest,
  type DebugMessage,
  type DebugMockTool,
  type DebugStreamingResponse,
  type MockContext,
  type MockVariable,
  type MockTool,
  type SaveDebugContextRequest,
  type DebugVariableVal,
} from '@test-agentstudio/api-client'
import type { ChatMessage, PromptMessage } from '@/components/Prompts'
import type { DebugTraceInfo, PromptParameter, Model, ModelConfig } from '@/types/promptType'
import {
  extractDebugErrorMessage,
  generateMessageKey,
  findModelByIdAndFrom,
  processToolCallsIncremental,
  checkValidModel,
} from '@/utils/prompts/promptEditPageUtils'
import { messageId } from '@/utils/prompts/utils'
import { convertFrontendToolsToApiTools } from '@/utils/prompts/toolFormatConverter'

interface UseDebugInputAreaOptions {
  promptId: string
  workspaceId: string
  userId: string
  chatMessages: ChatMessage[]
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
  inputMessage: string
  setInputMessage: React.Dispatch<React.SetStateAction<string>>
  isProcessing: boolean
  setIsProcessing: React.Dispatch<React.SetStateAction<boolean>>
  isStreamingStopped: boolean
  setIsStreamingStopped: React.Dispatch<React.SetStateAction<boolean>>
  debugTraceInfo: DebugTraceInfo
  setDebugTraceInfo: React.Dispatch<React.SetStateAction<DebugTraceInfo>>
  completedMessages: Set<number>
  setCompletedMessages: React.Dispatch<React.SetStateAction<Set<number>>>
  expandedReasoningMessages: Set<number>
  setExpandedReasoningMessages: React.Dispatch<React.SetStateAction<Set<number>>>
  expandedToolCallMessages: Set<number>
  setExpandedToolCallMessages: React.Dispatch<React.SetStateAction<Set<number>>>

  // 辅助函数
  scrollToBottom: () => void
  validateAllPlaceholders: () => boolean
  showSnackbar: (message: string, severity?: 'success' | 'error' | 'warning' | 'info') => void
  enableAutoReadOnly: () => void
  disableAutoReadOnly: () => void

  // 提示词相关
  promptMessages: PromptMessage[]
  messageInputValues: { [key: string]: string }
  parameters: PromptParameter[]
  tools: Array<{
    id: string
    name: string
    description: string
    defaultValue?: string
    fieldType?: 'PlainText' | 'JSON'
    parameters: Array<{
      name: string
      type: string
      description: string
      required: boolean
    }>
  }>

  // 模型相关
  templateEngine: 'normal' | 'jinja2'
  selectedModel: Model | null
  modelConfig: ModelConfig
  availableModels: Model[]
  toolsEnabled: boolean

  // 可选的 AbortController ref（用于停止调试流式请求，参考快捷优化的停止逻辑）
  debugAbortControllerRef?: React.MutableRefObject<AbortController | null>

  // 可选的 AI 思考过程定时器 ref（用于清理定时器）
  reasoningUpdateTimerRef?: React.MutableRefObject<NodeJS.Timeout | null>
}

export const useDebugInputArea = (options: UseDebugInputAreaOptions) => {
  const { t } = useTranslation()
  const isStreamingStoppedRef = useRef<boolean>(false)
  const debugControllerRef = useRef<{ cancel: () => void } | null>(null) // 用于管理 debugController

  // ModelConfig 字段名映射（从驼峰到下划线）
  const modelConfigFieldMapping: { [key: string]: string } = {
    maxTokens: 'max_tokens',
    topP: 'top_p',
    frequencyPenalty: 'frequency_penalty',
    presencePenalty: 'presence_penalty',
  }

  const {
    promptId,
    workspaceId,
    userId,
    chatMessages,
    setChatMessages,
    inputMessage,
    setInputMessage,
    isProcessing,
    setIsProcessing,
    isStreamingStopped,
    setIsStreamingStopped,
    debugTraceInfo,
    setDebugTraceInfo,
    completedMessages,
    setCompletedMessages,
    expandedReasoningMessages,
    setExpandedReasoningMessages,
    expandedToolCallMessages,
    setExpandedToolCallMessages,
    scrollToBottom,
    validateAllPlaceholders,
    enableAutoReadOnly,
    disableAutoReadOnly,
    showSnackbar,
    promptMessages,
    messageInputValues,
    parameters,
    tools,
    templateEngine,
    selectedModel,
    modelConfig,
    availableModels,
    toolsEnabled,
    debugAbortControllerRef,
    reasoningUpdateTimerRef,
  } = options

  /**
   * 更新调试跟踪信息的辅助函数
   */
  const updateDebugTraceInfo = useCallback(
    (debug_id?: string, debug_trace_key?: string) => {
      setDebugTraceInfo({
        debug_id,
        debug_trace_key,
      })
    },
    [setDebugTraceInfo],
  )

  /**
   * 转换工具格式为新的 JSON Schema 格式
   * @param tools 工具数组（可能是旧格式或新格式）
   * @returns 转换后的工具数组（新格式）
   */
  const convertToolsToNewFormat = useCallback((tools: any[]): any[] => {
    if (!tools || !Array.isArray(tools)) {
      return []
    }

    return tools.map(tool => {
      // 如果已经是新格式（有 type: 'object' 和 properties），直接返回
      if (
        tool.function?.parameters &&
        typeof tool.function.parameters === 'object' &&
        tool.function.parameters.type === 'object' &&
        tool.function.parameters.properties
      ) {
        return tool
      }

      // 处理旧格式：parameters 可能是字符串或对象
      let parsedParams: any
      if (typeof tool.function?.parameters === 'string') {
        try {
          parsedParams = JSON.parse(tool.function.parameters)
        } catch (error) {
          console.error('解析工具参数失败:', error)
          parsedParams = {}
        }
      } else if (tool.function?.parameters && typeof tool.function.parameters === 'object') {
        parsedParams = tool.function.parameters
      } else {
        parsedParams = {}
      }

      // 判断是旧格式的参数对象还是已经是新格式
      if (parsedParams.type === 'object' && parsedParams.properties) {
        // 已经是新格式
        return {
          type: 'function' as const,
          function: {
            name: tool.function?.name || '',
            description: tool.function?.description || '',
            parameters: parsedParams,
          },
        }
      } else {
        // 旧格式：需要转换
        const properties: any = {}
        const required: string[] = []

        Object.entries(parsedParams).forEach(([paramName, paramConfig]: [string, any]) => {
          properties[paramName] = {
            type: (paramConfig.type || 'string').toLowerCase(),
            description: paramConfig.description || '',
          }
          // 检查是否必填
          if (paramConfig.required === 'true' || paramConfig.required === true) {
            required.push(paramName)
          }
        })

        return {
          type: 'function' as const,
          function: {
            name: tool.function?.name || '',
            description: tool.function?.description || '',
            parameters: {
              type: 'object' as const,
              properties,
              required,
              additionalProperties: false,
            },
          },
        }
      }
    })
  }, [])

  /**
   * 构建调试请求的函数 - 从 PromptEditPage 移动过来并改造成 hooks 形式
   */
  const buildDebugRequest = useCallback(
    (chatMessages: DebugMessage[], userInput: string, promptData: any): DebugStreamingRequest => {
      // 准备变量值
      const variableVals: DebugVariableVal[] = parameters.map(param => {
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

      // 准备工具模拟值
      const mockTools: DebugMockTool[] = tools.map(tool => ({
        name: tool.name,
        mock_value: tool.defaultValue || '',
        mock_response: tool.defaultValue || '',
      }))

      // 构建新的API请求格式 - 从页面获取数据
      const promptTemplate: any = {
        messages: [],
        template_type: templateEngine,
        variable_defs: [],
      }

      // 构建提示词消息 - 添加key字段（从编辑器的promptMessages状态获取）
      promptTemplate.messages = promptMessages.map(msg => ({
        content: messageInputValues[msg.id] || msg.content,
        role: msg.role as 'system' | 'user' | 'placeholder' | 'assistant',
        key: generateMessageKey(), // 生成21位随机字符串
      }))

      // 构建变量定义
      promptTemplate.variable_defs = parameters.map(param => ({
        key: param.name,
        type: param.dataType || 'string',
        desc: param.description || '',
      }))

      // 构建工具配置（新格式：JSON Schema 对象）
      // 使用 convertFrontendToolsToApiTools 来确保使用完整的 JSON Schema（包括嵌套对象、数组、enum等）
      // 这个函数会优先使用 tool.parametersJsonSchema（如果存在），保留所有高级特性
      const toolsConfig = convertFrontendToolsToApiTools(tools)

      // 优先使用已选中的模型，如果没有则从模型列表中查找
      let currentSelectedModel = selectedModel

      // 如果没有选中的模型，尝试从modelConfig中查找
      if (!currentSelectedModel && modelConfig?.model && modelConfig.model.trim() !== '') {
        currentSelectedModel = findModelByIdAndFrom(modelConfig.model, (modelConfig as any).model_from, availableModels)
      }

      // 如果还是找不到选中的模型，使用第一个可用模型
      if (!currentSelectedModel && availableModels.length > 0) {
        currentSelectedModel = availableModels[0]
      }

      // 如果没有有效的模型，抛出错误
      if (!currentSelectedModel) {
        throw new Error(t('hooks.prompts.useDebugInputArea.configValidModelFirst'))
      }

      // 构建模型配置 - 动态包含该模型支持的参数
      const modelConfigForApi: any = {
        models_name: currentSelectedModel.openModel.name || '',
        models_id: currentSelectedModel.openModel.model_id || modelConfig?.model || null,
        model_from: (currentSelectedModel as any)?.model_from || (modelConfig as any)?.model_from || '',
      }

      // 根据模型的 param_schemas 动态添加参数
      if (currentSelectedModel?.openModel?.param_config?.param_schemas) {
        currentSelectedModel.openModel.param_config.param_schemas.forEach((schema: any) => {
          const paramName = schema.name

          // 先检查直接匹配的参数名
          if (modelConfig?.[paramName] !== undefined && modelConfig[paramName] !== null) {
            modelConfigForApi[paramName] = modelConfig[paramName]
          } else {
            // 检查是否需要字段名映射（从驼峰到下划线）
            const camelCaseKey = Object.keys(modelConfigFieldMapping).find(key => modelConfigFieldMapping[key] === paramName)
            if (camelCaseKey && modelConfig?.[camelCaseKey] !== undefined && modelConfig[camelCaseKey] !== null) {
              modelConfigForApi[paramName] = modelConfig[camelCaseKey]
            }
          }
        })
      } else {
        // 如果没有 param_schemas，则使用默认的常见参数
        if (modelConfig?.temperature !== undefined) modelConfigForApi.temperature = modelConfig.temperature
        if (modelConfig?.maxTokens !== undefined) modelConfigForApi.max_tokens = modelConfig.maxTokens
        if (modelConfig?.topP !== undefined) modelConfigForApi.top_p = modelConfig.topP
      }

      // 构建完整的prompt对象 - 直接从页面数据构建
      const customPromptData: any = {
        ...promptData, // 保留基础信息
        prompt_draft: {
          draft_info: promptData.prompt_draft?.draft_info || {},
          detail: {
            prompt_template: promptTemplate,
            tools: toolsConfig,
            tool_call_config: {
              tool_choice: toolsEnabled ? 'auto' : 'none',
            },
            prompt_model_config: modelConfigForApi,
          },
        },
      }

      // 如果存在 prompt_commit，也需要转换其 tools 格式
      if (promptData.prompt_commit?.detail?.tools) {
        customPromptData.prompt_commit = {
          ...promptData.prompt_commit,
          detail: {
            ...promptData.prompt_commit.detail,
            tools: convertToolsToNewFormat(promptData.prompt_commit.detail.tools),
          },
        }
      }

      return {
        prompt_id: promptId,
        user_id: '', // 暂时使用空字符串
        prompt: customPromptData,
        messages: chatMessages,
        variable_vals: variableVals,
        mock_tools: mockTools,
        single_step_debug: false,
      }
    },
    [
      parameters,
      tools,
      templateEngine,
      promptMessages,
      messageInputValues,
      selectedModel,
      modelConfig,
      availableModels,
      modelConfigFieldMapping,
      toolsEnabled,
      promptId,
      convertToolsToNewFormat,
      t,
    ],
  )

  /**
   * 停止当前的调试流式请求 - 清理所有延迟的消息队列
   */
  const stopCurrentDebugRequest = useCallback(() => {
    // 调用 debugController 的 cancel 方法来清理延迟队列
    if (debugControllerRef.current) {
      debugControllerRef.current.cancel()
      debugControllerRef.current = null
    }
  }, [])

  /**
   * 通用的流式调试请求处理函数 - 从 PromptEditPage 移动过来并改造成 hooks 形式
   * 停止逻辑参考快捷优化的实现：使用 AbortController 模式，停止时保存当前流式内容
   */
  const executeStreamingDebugRequest = useCallback(
    async (
      debugRequest: DebugStreamingRequest, // 直接接收构建好的调试请求
      mockTools: DebugMockTool[], // 从调试请求中提取的工具模拟值
      options: {
        // 消息管理
        messageIndex?: number // 要更新的消息索引，不提供则自动计算
        messages?: any[] // 消息数组（用于多实例或对比模式）
        setMessages?: (updater: (prev: any[]) => any[]) => void // 更新消息的函数

        // 完成状态管理
        completedMessages?: Set<number> // 已完成消息集合
        setCompletedMessages?: (updater: (prev: Set<number>) => Set<number>) => void // 更新完成状态的函数

        // 处理状态管理
        isProcessing?: boolean // 当前处理状态
        setIsProcessing?: (value: boolean) => void // 更新处理状态的函数

        // 流控制（参考快捷优化的 AbortController 模式）
        abortControllerRef?: React.MutableRefObject<AbortController | null> // AbortController 引用（用于停止请求）

        // 自定义处理
        customStreamHandler?: (response: DebugStreamingResponse, mockTools?: Array<{ name: string; mock_response: string }>) => void // 自定义流式响应处理器

        // 生命周期回调
        onStart?: () => void // 开始处理时的回调
        onError?: (error: Error, messageIndex: number) => void // 错误处理回调
        onComplete?: (messageIndex: number, cost_ms: number, lastResponseData?: DebugStreamingResponse) => void // 完成处理回调
        onStreamingUpdate?: (response: DebugStreamingResponse, messageIndex: number) => void // 流式更新回调
        onStop?: (messageIndex: number) => void // 停止回调（可选，用于自定义停止处理）

        // 其他选项
        isRetry?: boolean // 是否为重试操作
        userInput?: string // 用户输入（用于错误消息）
        scrollToBottom?: boolean // 是否自动滚动到底部
        autoExpandReasoning?: boolean // 是否自动展开推理过程
        autoExpandToolCalls?: boolean // 是否自动展开工具调用
        saveContext?: boolean // 是否保存调试上下文
      } = {},
    ) => {
      // 解构选项并设置默认值
      const {
        messageIndex,
        messages = chatMessages,
        setMessages = setChatMessages,
        completedMessages,
        setCompletedMessages: setCompletedMessagesFunc = setCompletedMessages,
        isProcessing,
        setIsProcessing: setIsProcessingFunc = options.setIsProcessing,
        abortControllerRef, // AbortController 引用（用于停止请求）
        customStreamHandler,
        onStart,
        onError,
        onComplete,
        onStreamingUpdate,
        onStop, // 新增：停止回调
        isRetry = false,
        userInput = '',
        scrollToBottom: shouldScrollToBottom = true,
        autoExpandReasoning = true,
        autoExpandToolCalls = true,
        saveContext = true,
      } = options
      const startTime = Date.now()
      let lastResponseData: DebugStreamingResponse | undefined = undefined
      let debugController: { cancel: () => void } | null = null // 调试流式请求的控制器

      // 确定要更新的消息索引
      const targetMessageIndex = messageIndex ?? messages.length - 1

      // 取消之前的请求（如果存在）- 参考快捷优化的逻辑
      if (abortControllerRef?.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }

      // 创建新的 AbortController - 参考快捷优化的逻辑
      if (abortControllerRef) {
        abortControllerRef.current = new AbortController()
      }

      // 处理状态设置
      if (setIsProcessingFunc) {
        setIsProcessingFunc(true)
      }

      // 开始回调
      enableAutoReadOnly()
      onStart?.()

      try {
        // 调用调试流式API - 传递 space_id、abortController 参数（参考快捷优化的逻辑）
        const controllerPromise = PromptService.debugStreaming(
          promptId,
          debugRequest,
          workspaceId,
          (response: DebugStreamingResponse) => {
            // 检查是否已被用户停止（通过 AbortController）- 参考快捷优化的逻辑
            if (abortControllerRef?.current?.signal.aborted) {
              return
            }

            lastResponseData = response

            // 如果有自定义流式处理器，使用它
            if (customStreamHandler) {
              // 检查是否已被用户停止（通过 AbortController）
              if (abortControllerRef?.current?.signal.aborted) {
                return
              }
              customStreamHandler(
                response,
                mockTools.map(tool => ({ name: tool.name, mock_response: tool.mock_response || tool.mock_value || '' })),
              )
              return
            }

            // 再次检查是否已被用户停止（在处理流式响应之前）
            if (abortControllerRef?.current?.signal.aborted) {
              return
            }

            // 触发流式更新回调
            onStreamingUpdate?.(response, targetMessageIndex)

            // 处理流式响应
            if (response.delta && (response.delta.content || response.delta.reasoning_content || response.delta.tool_calls)) {
              setMessages((prev: any[]) => {
                // 在状态更新函数内部也检查（虽然已经在外层检查过，但为了安全）
                if (abortControllerRef?.current?.signal.aborted) {
                  return prev // 如果已取消，返回原状态
                }

                const newMessages = [...prev]
                const currentMessage = newMessages[targetMessageIndex]
                if (currentMessage && currentMessage.type === 'ai') {
                  const updates: any = {}

                  // 获取当前消息的工具调用状态，用于判断是否处于工具调用阶段
                  const existingToolCalls = currentMessage.toolCalls || []
                  const hasNewToolCalls = response.delta?.tool_calls && response.delta.tool_calls.length > 0

                  // 处理工具调用信息（优先处理，因为工具调用可能会影响内容的处理）
                  if (hasNewToolCalls && response.delta && response.delta.tool_calls) {
                    const updatedToolCalls = processToolCallsIncremental(existingToolCalls, response.delta.tool_calls, mockTools)
                    updates.toolCalls = updatedToolCalls
                  }

                  // 处理内容更新 - 需要过滤工具调用相关的标记
                  if (response.delta?.content) {
                    let contentToAdd = response.delta.content

                    // 过滤工具调用相关的标记
                    // 移除 <tool_call> 标记及其周围的空白字符
                    contentToAdd = contentToAdd.replace(/<tool_call>\s*/gi, '')
                    contentToAdd = contentToAdd.replace(/\s*<\/tool_call>/gi, '')
                    contentToAdd = contentToAdd.replace(/<tool_call\/>/gi, '')

                    // 如果当前内容只包含工具调用标记和空白字符，则跳过此次更新
                    const trimmedContent = contentToAdd.trim()
                    const originalTrimmedContent = response.delta.content.trim()
                    if (trimmedContent === '' && originalTrimmedContent !== '') {
                      // 这是工具调用标记（移除标记后只剩空白字符），不更新内容
                    } else {
                      // 允许更新内容（包括只有空白字符的情况，如换行符）
                      // 注意：这里不再检查 trimmedContent，因为换行符等空白字符也应该被保留
                      let newContent = currentMessage.content
                      // 如果当前内容是加载指示器，替换为空字符串
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
                  if (response.delta?.reasoning_content) {
                    const newReasoningContent = currentMessage.reasoningContent || ''
                    updates.reasoningContent = newReasoningContent + response.delta.reasoning_content
                  }

                  const updatedMessage = {
                    ...currentMessage,
                    ...updates,
                  }
                  newMessages[targetMessageIndex] = updatedMessage

                  // 自动展开AI思考过程和工具调用（仅在主聊天区域）
                  if (autoExpandReasoning && updates.reasoningContent && messages === chatMessages && !expandedReasoningMessages.has(targetMessageIndex)) {
                    setExpandedReasoningMessages(prev => new Set([...prev, targetMessageIndex]))
                  }
                  if (
                    autoExpandToolCalls &&
                    updates.toolCalls &&
                    updates.toolCalls.length > 0 &&
                    messages === chatMessages &&
                    !expandedToolCallMessages.has(targetMessageIndex)
                  ) {
                    setExpandedToolCallMessages(prev => new Set([...prev, targetMessageIndex]))
                  }
                }
                return newMessages
              })

              // 自动滚动到底部
              if (shouldScrollToBottom) {
                requestAnimationFrame(() => {
                  scrollToBottom()
                })
              }
            }

            // 处理完成信息（token和耗时）
            if (response.delta === null && response.usage) {
              // 检查是否已被用户停止（通过 AbortController）
              if (abortControllerRef?.current?.signal.aborted) {
                return
              }

              const cost_ms = Date.now() - startTime

              setTimeout(() => {
                // 再次检查是否已取消（在延迟期间可能被取消）
                if (abortControllerRef?.current?.signal.aborted) {
                  return
                }

                setMessages((prev: any[]) => {
                  const newMessages = [...prev]
                  const currentMessage = newMessages[targetMessageIndex]
                  if (currentMessage && currentMessage.type === 'ai') {
                    const updatedMessage = {
                      ...currentMessage,
                      input_tokens: response.usage?.input_tokens?.toString() || '0',
                      output_tokens: response.usage?.output_tokens?.toString() || '0',
                      cost_ms: cost_ms.toString(),
                    }
                    newMessages[targetMessageIndex] = updatedMessage
                  }
                  return newMessages
                })
              }, 100)
            }

            // 保存调试跟踪信息（仅在主聊天区域）
            if ((response.debug_id || response.debug_trace_key) && messages === chatMessages) {
              // 检查是否已被用户停止（通过 AbortController）
              if (abortControllerRef?.current?.signal.aborted) {
                return
              }

              updateDebugTraceInfo(response.debug_id, response.debug_trace_key)

              // 同时将debug_id保存到当前AI消息对象中
              if (response.debug_id) {
                setMessages((prev: any[]) => {
                  const newMessages = [...prev]
                  const currentMessage = newMessages[targetMessageIndex]
                  if (currentMessage && currentMessage.type === 'ai') {
                    const updatedMessage = {
                      ...currentMessage,
                      debug_id: response.debug_id,
                    }
                    newMessages[targetMessageIndex] = updatedMessage
                  }
                  return newMessages
                })
              }
            }
          },
          (error: Error) => {
            console.error('流式调试API调用失败:', error)
            disableAutoReadOnly()

            // 更新状态
            if (setIsProcessingFunc) {
              setIsProcessingFunc(false)
            }

            // 清理 AbortController - 参考快捷优化的逻辑
            if (abortControllerRef?.current) {
              abortControllerRef.current = null
            }

            // 检查是否是用户主动取消的请求（AbortError）- 参考快捷优化的逻辑
            if (error instanceof Error && error.name === 'AbortError') {
              // 将当前的流式内容设置为最终结果
              setMessages((prev: any[]) => {
                const newMessages = [...prev]
                const currentMessage = newMessages[targetMessageIndex]
                if (currentMessage && currentMessage.type === 'ai') {
                  // 当前消息内容已经是最终的流式内容，保持不变
                  // 标记消息为完成
                  if (setCompletedMessagesFunc) {
                    setTimeout(() => {
                      setCompletedMessagesFunc(prevCompleted => new Set([...prevCompleted, targetMessageIndex]))
                    }, 0)
                  }
                }
                return newMessages
              })

              // 触发停止回调
              onStop?.(targetMessageIndex)
              return
            }

            if (onError) {
              onError(error, targetMessageIndex)
            } else {
              // 默认错误处理：更新消息内容为错误信息（只更新AI消息）
              setMessages((prev: any[]) => {
                const newMessages = [...prev]
                const currentMessage = newMessages[targetMessageIndex]
                // 确保只更新AI消息，避免错误信息被放到用户消息中
                if (currentMessage && currentMessage.type === 'ai') {
                  newMessages[targetMessageIndex] = {
                    ...currentMessage,
                    content: extractDebugErrorMessage(error),
                  }
                } else {
                  // 如果目标位置不是AI消息，尝试找到最后一条AI消息并更新它
                  let lastAIMessageIndex = -1
                  for (let i = newMessages.length - 1; i >= 0; i--) {
                    if (newMessages[i].type === 'ai') {
                      lastAIMessageIndex = i
                      break
                    }
                  }
                  if (lastAIMessageIndex >= 0) {
                    newMessages[lastAIMessageIndex] = {
                      ...newMessages[lastAIMessageIndex],
                      content: extractDebugErrorMessage(error),
                    }
                  } else {
                    // 如果找不到AI消息，创建一个新的AI错误消息
                    const errorMessage = {
                      type: 'ai' as const,
                      content: extractDebugErrorMessage(error),
                      timestamp: new Date().toLocaleString('zh-CN'),
                      userInput: userInput || '',
                    }
                    newMessages.push(errorMessage)
                  }
                }
                return newMessages
              })

              // 标记消息为完成
              if (setCompletedMessagesFunc) {
                setCompletedMessagesFunc(prev => new Set([...prev, targetMessageIndex]))
              }
            }
          },
          async () => {
            // 检查是否已被用户停止（通过 AbortController）- 参考快捷优化的停止逻辑
            // 如果 AbortController 已被设置为 null，说明请求已被取消
            if (!abortControllerRef?.current) {
              disableAutoReadOnly()
              return
            }

            // 检查是否被 AbortController 取消
            const wasAborted = abortControllerRef?.current?.signal.aborted || false

            // 如果已被取消，直接返回，不执行后续逻辑
            if (wasAborted) {
              disableAutoReadOnly()
              // 清理状态
              if (setIsProcessingFunc) {
                setIsProcessingFunc(false)
              }
              // 清理 AbortController
              abortControllerRef.current = null
              return
            }

            disableAutoReadOnly()

            // 计算响应时间
            const cost_ms = Date.now() - startTime

            // 更新状态
            if (setIsProcessingFunc) {
              setIsProcessingFunc(false)
            }

            // 只有在未被取消的情况下才标记为完成
            if (!wasAborted && setCompletedMessagesFunc) {
              setCompletedMessagesFunc(prev => new Set([...prev, targetMessageIndex]))
            }

            // 清理 AbortController - 参考快捷优化的逻辑
            if (abortControllerRef?.current) {
              abortControllerRef.current = null
            }

            // 触发完成回调（只有在未被取消的情况下）
            if (onComplete && !wasAborted) {
              onComplete(targetMessageIndex, cost_ms, lastResponseData)
            }

            // 自动滚动（如果启用）
            if (shouldScrollToBottom) {
              setTimeout(scrollToBottom, 100)
            }
          },
          abortControllerRef?.current || undefined, // 传递 AbortController 参数（参考快捷优化的逻辑）
        )

        // 等待controller
        const controller = await controllerPromise
        debugController = controller
        debugControllerRef.current = controller // 保存到 ref 中以便外部访问

        // 检查在异步操作期间用户是否已经停止了响应（通过 AbortController）
        if (abortControllerRef?.current?.signal.aborted) {
          controller.cancel()
          disableAutoReadOnly()

          // 将当前的流式内容设置为最终结果 - 参考快捷优化的逻辑
          setMessages((prev: any[]) => {
            const newMessages = [...prev]
            const currentMessage = newMessages[targetMessageIndex]
            if (currentMessage && currentMessage.type === 'ai') {
              // 当前消息内容已经是最终的流式内容，保持不变
              // 标记消息为完成
              if (setCompletedMessagesFunc) {
                setTimeout(() => {
                  setCompletedMessagesFunc(prevCompleted => new Set([...prevCompleted, targetMessageIndex]))
                }, 0)
              }
            }
            return newMessages
          })

          // 触发停止回调
          onStop?.(targetMessageIndex)

          return controller
        }

        // 返回控制器，供调用方使用
        return controller
      } catch (error) {
        console.error('调试请求失败:', error)
        disableAutoReadOnly()

        // 清理状态
        if (setIsProcessingFunc) {
          setIsProcessingFunc(false)
        }

        // 清理 AbortController - 参考快捷优化的逻辑
        if (abortControllerRef?.current) {
          abortControllerRef.current = null
        }

        // 检查是否是用户主动取消的请求（AbortError）- 参考快捷优化的逻辑
        if (error instanceof Error && error.name === 'AbortError') {
          // 将当前的流式内容设置为最终结果
          setMessages((prev: any[]) => {
            const newMessages = [...prev]
            const currentMessage = newMessages[targetMessageIndex]
            if (currentMessage && currentMessage.type === 'ai') {
              // 当前消息内容已经是最终的流式内容，保持不变
              // 标记消息为完成
              if (setCompletedMessagesFunc) {
                setTimeout(() => {
                  setCompletedMessagesFunc(prevCompleted => new Set([...prevCompleted, targetMessageIndex]))
                }, 0)
              }
            }
            return newMessages
          })

          // 触发停止回调
          onStop?.(targetMessageIndex)

          // 不抛出错误，因为这是用户主动取消
          return debugController || { cancel: () => {} }
        }

        // 触发错误回调或默认处理
        if (onError) {
          onError(error as Error, targetMessageIndex)
        } else {
          // 默认错误处理：更新消息内容
          setMessages((prev: any[]) => {
            const newMessages = [...prev]
            newMessages[targetMessageIndex] = {
              ...newMessages[targetMessageIndex],
              content: extractDebugErrorMessage(error),
            }
            return newMessages
          })

          // 标记消息为完成
          if (setCompletedMessagesFunc) {
            setCompletedMessagesFunc(prev => new Set([...prev, targetMessageIndex]))
          }
        }

        throw error // 重新抛出错误，让调用方可以处理
      }
    },
    [
      chatMessages,
      setChatMessages,
      setCompletedMessages,
      updateDebugTraceInfo,
      isStreamingStoppedRef,
      enableAutoReadOnly,
      disableAutoReadOnly,
      promptId,
      expandedReasoningMessages,
      setExpandedReasoningMessages,
      expandedToolCallMessages,
      setExpandedToolCallMessages,
      scrollToBottom,
    ],
  )

  /**
   * 保存调试上下文的辅助函数 - 从 PromptEditPage 移动过来并改造成 hooks 形式
   */
  const saveDebugContext = useCallback(
    async (
      messages: Array<{ type: 'user' | 'ai' | 'system'; content: string; timestamp: string; userInput?: string }>,
      currentDebugTraceInfo?: { debug_id?: string; debug_trace_key?: string },
      cost_ms?: number,
      lastResponse?: DebugStreamingResponse,
      customParameters?: any[], // 使用 any[] 以兼容 Parameter 类型
      customTools?: any[], // 可选：覆盖闭包中的 tools，避免自动保存时使用到上次的 tools 状态
    ) => {
      try {
        // 过滤掉系统类型消息，只保留用户和AI消息
        const filteredMessages = messages.filter(msg => msg.type === 'user' || msg.type === 'ai')

        // 构建mock_contexts
        const mockContexts: MockContext[] = filteredMessages.map((msg, index) => {
          const context: MockContext = {
            content: msg.content,
            role: msg.type === 'user' ? 'user' : 'assistant',
            msg_time: msg.timestamp || new Date().toLocaleString('zh-CN'), // 直接使用消息的时间戳，如果没有则使用当前时间
            variable_vals: [],
            mock_tools: [],
          }

          // 如果是AI消息，添加AI特有的字段
          if (msg.type === 'ai') {
            // 处理debug_id：从消息对象中获取debug_id（无论是历史消息还是当前会话产生的消息）
            if ((msg as any).debug_id) {
              context.debug_id = (msg as any).debug_id
            }

            // 从消息对象获取reasoning_content
            context.reasoning_content = (msg as any).reasoningContent || null

            // 优先从消息对象获取token和耗时数据，其次从参数获取
            context.cost_ms = (msg as any).cost_ms || cost_ms?.toString() || '0'
            context.input_tokens = (msg as any).input_tokens || lastResponse?.usage?.input_tokens?.toString() || '0'
            context.output_tokens = (msg as any).output_tokens || lastResponse?.usage?.output_tokens?.toString() || '0'

            // 处理工具调用信息
            if ((msg as any).toolCalls && Array.isArray((msg as any).toolCalls)) {
              const toolCalls = (msg as any).toolCalls
              context.tool_calls = toolCalls.map((toolCall: any, arrayIndex: number) => ({
                tool_call: {
                  index: (toolCall.index !== undefined ? toolCall.index : arrayIndex).toString(),
                  id: toolCall.id || `call_${Date.now()}_${arrayIndex}`, // 使用真实ID或生成ID
                  function_call: {
                    name: toolCall.name || '',
                    arguments: toolCall.input || '',
                  },
                  type: 'function',
                },
                mock_response: toolCall.output || '',
                debug_trace_key: currentDebugTraceInfo?.debug_trace_key || '',
              }))
            }
          }

          return context
        })

        // 构建mock_variables - 使用传入的最新参数或当前状态参数
        const currentParameters = customParameters || parameters
        const mockVariables: MockVariable[] = currentParameters.map((param: any) => {
          if (param.type === 'placeholder' && param.messages) {
            // placeholder 类型变量：type 固定为 'placeholder'
            const placeholderMessages = param.messages.map((msg: any) => ({
              id: Date.now().toString() + Math.random().toString(36).substr(2, 5), // 生成唯一ID
              content: msg.content,
              role: msg.role,
              parts: [],
            }))

            return {
              key: param.name,
              type: 'placeholder', // placeholder 类型固定为 'placeholder'
              desc: param.description || '',
              value: '', // placeholder 类型也需要 value 字段
              placeholder_messages: placeholderMessages,
            }
          } else {
            // 普通变量：使用 dataType 作为 type，使用 value 字段
            const variableType = param.dataType || 'string'

            return {
              key: param.name,
              type: variableType, // 普通变量使用 dataType
              desc: param.description || '',
              value: param.value || '',
            }
          }
        })

        // 构建mock_tools - 优先使用传入的 customTools（避免自动保存时闭包中的 tools 尚未更新）
        const toolsToUse = customTools ?? tools
        console.log('🔍 [DEBUG-CONTEXT] saveDebugContext 构建 mock_tools', {
          customToolsProvided: customTools !== undefined && customTools !== null,
          customToolsLen: customTools?.length,
          closureToolsLen: tools?.length,
          toolsToUseLen: toolsToUse?.length,
          toolsToUsePreview: toolsToUse?.slice(0, 3).map((t: any) => ({ name: t?.name, defaultValue: t?.defaultValue, mock_response: t?.defaultValue ?? '' })),
        })
        const mockTools: MockTool[] = toolsToUse.map((tool: any) => ({
          name: tool.name,
          mock_response: tool.defaultValue ?? '',
        }))

        // 构建保存请求
        const saveRequest: SaveDebugContextRequest = {
          prompt_id: promptId,
          workspace_id: workspaceId,
          debug_context: {
            debug_core: {
              mock_contexts: mockContexts,
              mock_variables: mockVariables,
              mock_tools: mockTools,
            },
            debug_config: {
              single_step_debug: false,
            },
          },
        }

        const response = await PromptService.saveDebugContext(saveRequest)

        if (response.code !== 0) {
          console.error('❌ 保存调试上下文失败:', response.msg || '保存调试上下文失败')
        }
      } catch (error) {
        console.error('❌ 保存调试上下文失败:', error)
      }
    },
    [promptId, workspaceId, userId, parameters, tools],
  )

  /**
   * 处理发送消息
   * @param currentValue 可选，由输入框传入的当前值，避免因父组件 state 未及时更新导致使用旧值
   */
  const handleSendMessage = useCallback(async (currentValue?: string) => {
    const message = currentValue !== undefined ? currentValue : inputMessage

    // 检查所有 placeholder 消息是否有效
    if (!validateAllPlaceholders()) {
      return
    }

    // 检查是否配置了有效的模型
    if (!checkValidModel(selectedModel, modelConfig, availableModels)) {
      showSnackbar(t('hooks.prompts.useDebugInputArea.configValidModelFirst'), 'error')
      return
    }

    // 如果用户没有在输入框中输入消息，根据最后一条消息类型决定逻辑
    if (!message.trim()) {
      // 检查最后一条消息的类型
      const lastMessage = chatMessages.length > 0 ? chatMessages[chatMessages.length - 1] : null

      // 如果最后一条消息是user消息，则相当于用户发送了一条空消息，走下面正常的逻辑
      if (lastMessage && lastMessage.type === 'user') {
        // 继续执行下面的正常逻辑，不执行重试
      } else {
        // 如果最后一条消息是AI消息或没有消息，执行重试逻辑
        // 找到最后一条AI消息的索引
        let lastAIMessageIndex = -1
        for (let i = chatMessages.length - 1; i >= 0; i--) {
          if (chatMessages[i].type === 'ai') {
            lastAIMessageIndex = i
            break
          }
        }

        // 如果找到了AI消息，执行重试逻辑
        if (lastAIMessageIndex >= 0) {
          if (isProcessing) return

          // 找到触发当前AI回复的用户消息（如果有的话）
          let lastUserMessage = ''
          for (let i = lastAIMessageIndex - 1; i >= 0; i--) {
            if (chatMessages[i].type === 'user') {
              lastUserMessage = chatMessages[i].content
              break
            }
          }

          // 如果没有找到用户消息，使用空字符串（与handleSendMessage的逻辑一致）
          // 准备调试请求数据（不包括要重试的AI消息）
          const debugMessages: DebugMessage[] = chatMessages
            .slice(0, lastAIMessageIndex) // 只取该AI消息之前的消息
            .map(msg => ({
              role: msg.type === 'user' ? ('user' as const) : ('assistant' as const),
              content: msg.content,
              parts: [],
            }))

          try {
            // 获取提示词数据
            const promptDetail = await PromptService.getPromptDetail(promptId, {
              withCommit: true,
              withDraft: true,
              withDefaultConfig: true,
              workspaceId: workspaceId,
            })

            if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
              throw new Error('无法获取提示词详情')
            }

            // 构建调试请求
            const debugRequest = buildDebugRequest(debugMessages, lastUserMessage, promptDetail.prompt[0])
            const mockTools = debugRequest.mock_tools

            // 重置当前AI消息为加载状态
            setChatMessages(prev => {
              const newMessages = [...prev]
              newMessages[lastAIMessageIndex] = {
                ...newMessages[lastAIMessageIndex],
                content: '......',
                input_tokens: undefined,
                output_tokens: undefined,
                cost_ms: undefined,
                reasoningContent: undefined,
                toolCalls: undefined,
              }
              return newMessages
            })

            // 移除该消息的完成状态
            setCompletedMessages(prev => {
              const newCompleted = new Set(prev)
              newCompleted.delete(lastAIMessageIndex)
              return newCompleted
            })

            // 重置AI思考过程和工具调用的展开状态
            setExpandedReasoningMessages(prev => {
              const newExpanded = new Set(prev)
              newExpanded.add(lastAIMessageIndex)
              return newExpanded
            })
            setExpandedToolCallMessages(prev => {
              const newExpanded = new Set(prev)
              newExpanded.add(lastAIMessageIndex)
              return newExpanded
            })

            // 使用通用函数执行流式调试请求
            await executeStreamingDebugRequest(debugRequest, mockTools, {
              messageIndex: lastAIMessageIndex,
              isRetry: true,
              userInput: lastUserMessage,
              abortControllerRef: debugAbortControllerRef,
              setIsProcessing,
              onComplete: (_targetMessageIndex: number, cost_ms: number, lastResponseData?: DebugStreamingResponse) => {
                // 保存调试上下文
                setTimeout(async () => {
                  try {
                    setChatMessages(currentMessages => {
                      saveDebugContext(currentMessages, debugTraceInfo, cost_ms, lastResponseData).catch(error =>
                        console.error('❌ 重试后保存调试上下文失败:', error),
                      )
                      return currentMessages
                    })
                  } catch (error) {
                    console.error('❌ 重试后保存调试上下文失败:', error)
                  }
                }, 300)
              },
            })
          } catch (error) {
            console.error('❌ [SEND-RETRY] 重试消息失败:', error)
            showSnackbar(extractDebugErrorMessage(error), 'error')
          }

          return
        } else {
          // 如果没有AI消息，不添加用户消息，但继续执行其他逻辑
          // 继续执行后面的逻辑，但跳过添加用户消息的部分
        }
      }
    }

    // 重置停止状态，开始新的流式响应
    setIsStreamingStopped(false)
    isStreamingStoppedRef.current = false

    let userMessageIndex = chatMessages.length
    const currentInput = message.trim() ? message : ''
    const hasUserInput = message.trim() !== ''

    // 只有在消息不为空时才添加用户消息到对话历史
    if (hasUserInput) {
      const userMessage: ChatMessage = {
        type: 'user' as const,
        content: message,
        timestamp: new Date().toLocaleString('zh-CN'),
      }

      setChatMessages(prev => [...prev, userMessage])
      // 用户消息立即标记为完成
      setCompletedMessages(prev => new Set([...prev, userMessageIndex]))
      userMessageIndex = chatMessages.length // 更新索引，因为添加了用户消息
    }

    setInputMessage('')

    // 滚动到底部
    setTimeout(scrollToBottom, 100)

    // 预先计算AI消息索引
    const aiMessageIndex = hasUserInput ? chatMessages.length + 1 : chatMessages.length

    // 准备调试请求数据 - 过滤掉不完整的AI消息
    // 注意：需要手动添加新的用户消息（如果有），因为 setChatMessages 是异步的，chatMessages 可能还没有更新
    const debugMessages: DebugMessage[] = [
      ...chatMessages
        .filter(msg => {
          // 过滤掉内容为 "......" 或空内容的AI消息（被停止或未完成的消息）
          if (msg.type === 'ai' && (msg.content === '......' || msg.content.trim() === '')) {
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
              content: currentInput,
              parts: [],
            },
          ]
        : []),
    ]

    // 创建AI消息占位符，用于流式更新
    const aiMessage: ChatMessage = {
      type: 'ai' as const,
      content: '......', // 显示加载指示器
      timestamp: new Date().toLocaleString('zh-CN'),
      userInput: currentInput,
    }
    setChatMessages(prev => [...prev, aiMessage])

    // 保存调试上下文 - 调用提示词调试接口之后立即保存用户输入（如果有的话）
    if (hasUserInput) {
      const debugUserMessage: ChatMessage = {
        type: 'user' as const,
        content: currentInput,
        timestamp: new Date().toLocaleString('zh-CN'),
      }
      await saveDebugContext([...chatMessages, debugUserMessage])
    } else {
      // 如果没有用户输入，只保存当前对话历史
      await saveDebugContext(chatMessages)
    }

    try {
      // 获取提示词数据
      const promptDetail = await PromptService.getPromptDetail(promptId, {
        withCommit: true,
        withDraft: true,
        withDefaultConfig: true,
        workspaceId: workspaceId,
      })

      if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
        throw new Error('无法获取提示词详情')
      }

      // 构建调试请求
      const debugRequest = buildDebugRequest(debugMessages, currentInput, promptDetail.prompt[0])
      const mockTools = debugRequest.mock_tools

      // 使用通用函数执行流式调试请求
      await executeStreamingDebugRequest(debugRequest, mockTools, {
        messageIndex: aiMessageIndex,
        userInput: currentInput,
        abortControllerRef: debugAbortControllerRef, // 传递 AbortController ref（参考快捷优化的停止逻辑）
        setIsProcessing,
        onComplete: (_targetMessageIndex: number, cost_ms: number, lastResponseData?: DebugStreamingResponse) => {
          // 保存调试上下文 - 流式输出完成之后保存完整对话记录
          // 注意：不检查 AbortController，因为它在 executeStreamingDebugRequest 的完成回调中可能已被清理
          // 只要 onComplete 被调用，说明请求正常完成，应该保存调试上下文
          setTimeout(async () => {
            try {
              setChatMessages(currentMessages => {
                // 构建包含最新debug_id的调试跟踪信息
                const currentDebugTraceInfo = {
                  debug_id: lastResponseData?.debug_id || debugTraceInfo?.debug_id,
                  debug_trace_key: lastResponseData?.debug_trace_key || debugTraceInfo?.debug_trace_key,
                }

                // 在状态更新中进行保存，确保获取到最新的消息内容
                saveDebugContext(currentMessages, currentDebugTraceInfo, cost_ms, lastResponseData).catch(error =>
                  console.error('❌ 完成后保存调试上下文失败:', error),
                )
                return currentMessages // 返回原状态，不做修改
              })
            } catch (error) {
              console.error('❌ 完成后保存调试上下文失败:', error)
            }
          }, 300) // 增加延迟确保消息完全更新
        },
      })
    } catch (error) {
      console.error('❌ [SEND] 发送消息失败:', error)
      showSnackbar(extractDebugErrorMessage(error), 'error')
    }
  }, [
    validateAllPlaceholders,
    selectedModel,
    modelConfig,
    availableModels,
    checkValidModel,
    showSnackbar,
    inputMessage,
    isProcessing,
    chatMessages,
    setChatMessages,
    setInputMessage,
    setCompletedMessages,
    scrollToBottom,
    saveDebugContext,
    promptId,
    workspaceId,
    buildDebugRequest,
    executeStreamingDebugRequest,
    debugTraceInfo,
    showSnackbar,
    parameters,
    tools,
    setIsProcessing,
    debugAbortControllerRef,
    setExpandedReasoningMessages,
    setExpandedToolCallMessages,
    t,
  ])

  /**
   * 处理重试最后一条消息
   */
  const handleRetryLastMessage = useCallback(
    async (messageIndex: number) => {
      if (isProcessing) return

      // 找到触发当前AI回复的用户消息（如果有的话）
      let lastUserMessage = ''
      for (let i = messageIndex - 1; i >= 0; i--) {
        if (chatMessages[i].type === 'user') {
          lastUserMessage = chatMessages[i].content
          break
        }
      }

      // 如果没有找到用户消息，使用空字符串（与handleSendMessage的逻辑一致）
      // 在重置AI消息为加载状态之前，先检查模型是否有效
      if (!checkValidModel(selectedModel, modelConfig, availableModels)) {
        showSnackbar(t('hooks.prompts.useDebugInputArea.configValidModelFirst'), 'error')
        return
      }

      // 准备调试请求数据（不包括要重试的AI消息）
      const debugMessages: DebugMessage[] = chatMessages
        .slice(0, messageIndex) // 只取该AI消息之前的消息
        .map(msg => ({
          role: msg.type === 'user' ? ('user' as const) : ('assistant' as const),
          content: msg.content,
          parts: [],
        }))

      try {
        // 获取提示词数据
        const promptDetail = await PromptService.getPromptDetail(promptId, {
          withCommit: true,
          withDraft: true,
          withDefaultConfig: true,
          workspaceId: workspaceId,
        })

        if (!promptDetail.prompt || promptDetail.prompt.length === 0) {
          throw new Error('无法获取提示词详情')
        }

        // 构建调试请求
        const debugRequest = buildDebugRequest(debugMessages, lastUserMessage, promptDetail.prompt[0])
        const mockTools = debugRequest.mock_tools

        // 重置当前AI消息为加载状态
        setChatMessages(prev => {
          const newMessages = [...prev]
          newMessages[messageIndex] = {
            ...newMessages[messageIndex],
            content: '......',
            input_tokens: undefined,
            output_tokens: undefined,
            cost_ms: undefined,
            reasoningContent: undefined,
            toolCalls: undefined,
          }
          return newMessages
        })

        // 移除该消息的完成状态
        setCompletedMessages(prev => {
          const newCompleted = new Set(prev)
          newCompleted.delete(messageIndex)
          return newCompleted
        })

        // 重置AI思考过程和工具调用的展开状态
        setExpandedReasoningMessages(prev => {
          const newExpanded = new Set(prev)
          newExpanded.add(messageIndex)
          return newExpanded
        })
        setExpandedToolCallMessages(prev => {
          const newExpanded = new Set(prev)
          newExpanded.add(messageIndex)
          return newExpanded
        })

        // 重置停止状态，使重试时也显示停止响应按钮
        setIsStreamingStopped(false)
        isStreamingStoppedRef.current = false

        // 使用通用函数执行流式调试请求
        await executeStreamingDebugRequest(debugRequest, mockTools, {
          messageIndex,
          isRetry: true,
          userInput: lastUserMessage,
          abortControllerRef: debugAbortControllerRef, // 传递 AbortController ref（参考快捷优化的停止逻辑）
          setIsProcessing,
          onComplete: (_targetMessageIndex: number, cost_ms: number, lastResponseData?: DebugStreamingResponse) => {
            // 保存调试上下文
            setTimeout(async () => {
              try {
                setChatMessages(currentMessages => {
                  saveDebugContext(currentMessages, debugTraceInfo, cost_ms, lastResponseData).catch(error =>
                    console.error('❌ 重试后保存调试上下文失败:', error),
                  )
                  return currentMessages
                })
              } catch (error) {
                console.error('❌ 重试后保存调试上下文失败:', error)
              }
            }, 300)
          },
        })
      } catch (error) {
        console.error('❌ [RETRY] 重试消息失败:', error)
        showSnackbar(extractDebugErrorMessage(error), 'error')
      }
    },
    [
      isProcessing,
      selectedModel,
      modelConfig,
      availableModels,
      checkValidModel,
      showSnackbar,
      chatMessages,
      promptId,
      workspaceId,
      buildDebugRequest,
      setChatMessages,
      setCompletedMessages,
      setExpandedReasoningMessages,
      setExpandedToolCallMessages,
      executeStreamingDebugRequest,
      debugTraceInfo,
      saveDebugContext,
      setIsProcessing,
      setIsStreamingStopped,
      isStreamingStoppedRef,
      debugAbortControllerRef,
      t,
    ],
  )

  /**
   * 停止流式响应 - 从 PromptEditPage 移动过来并改造成 hooks 形式
   */
  const handleStopStreaming = useCallback(() => {
    // 取消正在进行的流式请求 - 参考快捷优化的逻辑
    if (debugAbortControllerRef?.current) {
      debugAbortControllerRef.current.abort()
      debugAbortControllerRef.current = null
    }

    // 停止当前调试请求并清理延迟队列 - 修复停止后再发送消息显示上次内容的问题
    stopCurrentDebugRequest()

    // 停止处理状态 - 参考快捷优化的逻辑
    setIsProcessing(false)
    setIsStreamingStopped(true)
    isStreamingStoppedRef.current = true

    // 清理AI思考过程定时器
    if (reasoningUpdateTimerRef?.current) {
      clearTimeout(reasoningUpdateTimerRef.current)
      reasoningUpdateTimerRef.current = null
    }

    // 将当前的流式内容设置为最终结果 - 参考快捷优化的逻辑
    setChatMessages(prev => {
      const newMessages = [...prev]

      // 找到最后一条AI消息的索引
      let lastAIIndex = -1
      for (let i = newMessages.length - 1; i >= 0; i--) {
        if (newMessages[i].type === 'ai') {
          lastAIIndex = i
          break
        }
      }

      if (lastAIIndex !== -1) {
        const lastMessage = newMessages[lastAIIndex]

        // 如果内容还是 "......"，说明还没有任何输出，清空内容
        if (lastMessage.content === '......') {
          newMessages[lastAIIndex] = {
            ...lastMessage,
            content: '',
          }
        }
        // 如果有部分内容，保留已输出的内容（已经是最终结果）

        // 标记为完成状态
        setCompletedMessages(prevCompleted => new Set([...prevCompleted, lastAIIndex]))
      }
      return newMessages
    })

    disableAutoReadOnly()
  }, [
    isProcessing,
    debugAbortControllerRef,
    isStreamingStopped,
    chatMessages.length,
    stopCurrentDebugRequest,
    setIsProcessing,
    setIsStreamingStopped,
    isStreamingStoppedRef,
    reasoningUpdateTimerRef,
    setChatMessages,
    setCompletedMessages,
    disableAutoReadOnly,
  ])

  /**
   * 清空主对话
   */
  const handleClearMainChat = useCallback(async () => {
    try {
      // 清空聊天消息
      setChatMessages([])

      // 清空完成状态
      setCompletedMessages(new Set())

      // 清空AI思考过程和工具调用展开状态
      setExpandedReasoningMessages(new Set())
      setExpandedToolCallMessages(new Set())

      // 保存清空后的调试上下文（空的对话记录）
      await saveDebugContext([], debugTraceInfo)
    } catch (error) {
      console.error('❌ [CLEAR_CHAT] 清空主对话时保存调试上下文失败:', error)
      // 即使保存失败，也要清空聊天消息
      setChatMessages([])
      setCompletedMessages(new Set())
      setExpandedReasoningMessages(new Set())
      setExpandedToolCallMessages(new Set())
    }
  }, [setChatMessages, setCompletedMessages, setExpandedReasoningMessages, setExpandedToolCallMessages, saveDebugContext, debugTraceInfo])

  return {
    handleSendMessage,
    handleRetryLastMessage,
    saveDebugContext,
    buildDebugRequest,
    executeStreamingDebugRequest,
    handleStopStreaming, // 暴露停止流式响应方法
    handleClearMainChat,
  }
}
