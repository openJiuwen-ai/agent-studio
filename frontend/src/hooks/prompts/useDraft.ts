import { useCallback, useRef } from 'react'
import { PromptService, type DebugStreamingResponse } from '@test-agentstudio/api-client'
import type { Model, PromptMessage, PromptParameter, DebugTraceInfo, ChatMessage } from '@/types/promptType'
import { extractVariablesFromNonPlaceholderMessages, isValidVariableName } from '@/utils/prompts/promptEditPageUtils'

interface CustomDraftData {
  promptMessages?: PromptMessage[]
  parameters?: PromptParameter[]
  modelConfig?: any
  selectedModel?: Model | null
  templateEngine?: string
  toolsEnabled?: boolean
  tools?: any[]
}

interface UseDraftProps {
  promptId?: string
  isNew?: boolean
  userId?: string
  workspaceId?: string
  // 当前组件状态
  promptMessages: PromptMessage[]
  parameters: PromptParameter[]
  modelConfig: any
  selectedModel: Model | null
  templateEngine: string
  toolsEnabled: boolean
  tools: any[]
  // 依赖的 refs 和状态
  modelsLoadingRef: React.MutableRefObject<boolean>
  loadingRef: React.MutableRefObject<boolean>
  availableModels: Model[]
  promptDraftData?: any
  // 调试上下文相关
  chatMessages: ChatMessage[]
  debugTraceInfo: DebugTraceInfo
  saveDebugContext: (
    messages: Array<{ type: 'user' | 'ai' | 'system'; content: string; timestamp: string; userInput?: string }>,
    currentDebugTraceInfo?: { debug_id?: string; debug_trace_key?: string },
    cost_ms?: number,
    lastResponse?: DebugStreamingResponse,
    customParameters?: any[],
    customTools?: any[],
  ) => Promise<void>
  // 状态更新函数
  setDraftSavedTime: (time: Date | null) => void
  setIsDraftEdited: (edited: boolean) => void
  // triggerAutoSave 相关依赖
  isComparisonMode?: boolean
  isLoadingFromAPI?: boolean
  autoSaveTimerRef?: React.MutableRefObject<NodeJS.Timeout | null>
}

interface UseDraftReturn {
  triggerAutoSave: (customData?: CustomDraftData, forceSave?: boolean) => void
}

export const useDraft = ({
  promptId,
  isNew,
  userId,
  workspaceId,
  promptMessages,
  parameters,
  modelConfig,
  selectedModel,
  templateEngine,
  toolsEnabled,
  tools,
  modelsLoadingRef,
  loadingRef,
  availableModels,
  promptDraftData,
  chatMessages,
  debugTraceInfo,
  saveDebugContext,
  setDraftSavedTime,
  setIsDraftEdited,
  isComparisonMode = false,
  isLoadingFromAPI = false,
  autoSaveTimerRef,
}: UseDraftProps): UseDraftReturn => {
  // 如果没有传入 autoSaveTimerRef，创建一个内部的 ref
  const internalTimerRef = useRef<NodeJS.Timeout | null>(null)
  const timerRef = autoSaveTimerRef || internalTimerRef
  // 使用指定数据自动保存草稿函数（如果不传参数，则使用当前组件状态）
  const autoSaveDraftWithData = useCallback(
    async (customData?: CustomDraftData) => {
      if (!promptId || isNew) {
        return
      }

      // 等待模型信息和promptDraftData加载完成
      const currentSelectedModel = customData?.selectedModel || selectedModel
      const currentModelConfig = customData?.modelConfig || modelConfig

      // 如果selectedModel不存在或modelConfig.model为空，等待模型和promptDraftData加载
      if (!currentSelectedModel || !currentModelConfig.model) {
        let retryCount = 0
        const maxRetries = 30 // 最多等待 9 秒 (30 * 300ms)，给更多时间让所有数据加载完成

        while (retryCount < maxRetries) {
          // 由于闭包问题，我们需要通过其他方式检查数据是否已加载
          // 检查模型加载状态：如果加载完成（modelsLoadingRef.current为false）且等待了一段时间
          const modelsLoaded = !modelsLoadingRef.current && retryCount > 3 // 至少等待一段时间让状态更新

          // 由于闭包限制，availableModels 和 promptDraftData 可能是旧值
          // 但我们可以通过检查 loadingRef 来判断 loadPromptDetail 是否完成
          const detailLoaded = !loadingRef.current && retryCount > 3

          // 如果模型加载完成且详情加载完成，应该可以继续了
          if (modelsLoaded && detailLoaded) {
            break
          }

          await new Promise(resolve => setTimeout(resolve, 300))
          retryCount++
        }
      }

      try {
        // 确保使用最新的selectedModel和modelConfig
        // 注意：由于闭包限制，availableModels 可能是旧值，但我们可以通过其他方式获取模型
        let finalSelectedModel = customData?.selectedModel || selectedModel
        const finalModelConfig = customData?.modelConfig || modelConfig

        // 如果selectedModel仍然不存在，尝试从modelConfig中恢复
        if (!finalSelectedModel && finalModelConfig.model) {
          // 尝试从availableModels中查找匹配的模型（即使闭包中是旧值，也可能有数据）
          const matchedModel = availableModels.find(
            m => m.openModel.model_id === finalModelConfig.model && (!finalModelConfig.model_from || m.model_from === finalModelConfig.model_from),
          )
          if (matchedModel) {
            finalSelectedModel = matchedModel
          } else if (availableModels.length > 0) {
            // 如果找不到匹配的，但模型列表有数据，使用第一个
            finalSelectedModel = availableModels[0]
          }
        } else if (!finalSelectedModel && availableModels.length > 0) {
          // 如果selectedModel不存在但模型列表有数据，使用第一个可用模型
          finalSelectedModel = availableModels[0]
        }

        // 如果modelConfig中没有model字段，尝试从多个来源获取
        let finalModelConfigWithId = { ...finalModelConfig }

        // 优先：如果model字段为空，尝试从promptDraftData中获取models_id（即使闭包中是旧的，也可能有值）
        if (!finalModelConfigWithId.model && promptDraftData?.prompt_model_config?.models_id) {
          const draftModelId = promptDraftData.prompt_model_config.models_id
          const draftModelFrom = promptDraftData.prompt_model_config.model_from

          // 尝试从availableModels中查找匹配的模型
          const matchedModel = availableModels.find(m => m.openModel.model_id === draftModelId && (!draftModelFrom || m.model_from === draftModelFrom))

          if (matchedModel) {
            finalSelectedModel = matchedModel
            finalModelConfigWithId = {
              ...finalModelConfigWithId,
              model: matchedModel.openModel.model_id,
              model_from: matchedModel.model_from,
            }
          } else {
            // 如果找不到匹配的模型，至少设置model字段
            finalModelConfigWithId = {
              ...finalModelConfigWithId,
              model: draftModelId,
              model_from: draftModelFrom,
            }
          }
        } else if (finalSelectedModel) {
          // 如果有selectedModel，确保modelConfig包含正确的model字段
          if (!finalModelConfigWithId.model || !finalModelConfigWithId.models_id) {
            finalModelConfigWithId = {
              ...finalModelConfigWithId,
              model: finalSelectedModel.openModel.model_id,
              model_from: finalSelectedModel.model_from,
            }
          }
        } else {
          // 如果既没有selectedModel也没有model字段，尝试从API重新获取prompt详情
          if (!finalModelConfigWithId.model && !finalSelectedModel) {
            try {
              const promptDetailResponse = await PromptService.getPromptDetail(promptId, {
                withDraft: true,
                withDefaultConfig: false,
                withCommit: false,
                workspaceId: workspaceId,
              })

              if (promptDetailResponse.code === 0 && promptDetailResponse.prompt?.[0]?.prompt_draft?.detail?.prompt_model_config) {
                const apiModelConfig = promptDetailResponse.prompt[0].prompt_draft.detail.prompt_model_config
                const apiModelId = apiModelConfig.models_id || apiModelConfig.model_id

                if (apiModelId) {
                  // 尝试从availableModels中查找匹配的模型（即使闭包中是旧的，也可能有数据）
                  const matchedModel = availableModels.find(
                    m => m.openModel.model_id === apiModelId && (!apiModelConfig.model_from || m.model_from === apiModelConfig.model_from),
                  )

                  if (matchedModel) {
                    finalSelectedModel = matchedModel
                    finalModelConfigWithId = {
                      ...finalModelConfigWithId,
                      model: matchedModel.openModel.model_id,
                      model_from: matchedModel.model_from,
                    }
                  } else {
                    // 如果找不到匹配的模型，至少设置model字段，transformToApiDraftFormat会尝试获取模型详情
                    finalModelConfigWithId = {
                      ...finalModelConfigWithId,
                      model: apiModelId,
                      model_from: apiModelConfig.model_from,
                    }
                  }
                }
              }
            } catch (error) {
              // 忽略API获取模型信息错误
            }
          }

          // 最终检查：如果还是没有model字段，尝试使用第一个可用模型
          if (!finalModelConfigWithId.model && !finalSelectedModel && availableModels.length > 0) {
            finalSelectedModel = availableModels[0]
            finalModelConfigWithId = {
              ...finalModelConfigWithId,
              model: availableModels[0].openModel.model_id,
              model_from: availableModels[0].model_from,
            }
          }
        }

        const editorData = {
          promptMessages: customData?.promptMessages || promptMessages,
          parameters: customData?.parameters || parameters,
          modelConfig: finalModelConfigWithId,
          selectedModel: finalSelectedModel,
          templateEngine: customData?.templateEngine || templateEngine,
          toolsEnabled: customData?.toolsEnabled ?? toolsEnabled,
          tools: customData?.tools || tools,
        }

        const response = await PromptService.saveDraft(promptId, workspaceId!, editorData)

        if (response.code === 0) {
          const now = new Date()
          setDraftSavedTime(now)
          setIsDraftEdited(true) // 保存草稿后标记为有未提交的更改

          // 自动保存草稿成功后，统一保存调试上下文（含 mock_variables、mock_tools；无聊天消息时也保存，以便修改变量值/工具默认值时能持久化）
          try {
            const messagesForContext = chatMessages.map(msg => ({
              type: msg.type as 'user' | 'ai' | 'system',
              content: msg.content || '',
              timestamp: msg.timestamp || new Date().toISOString(),
              userInput: (msg as any).userInput,
              ...(msg.type === 'ai' && {
                toolCalls: (msg as any).toolCalls,
                debug_id: (msg as any).debug_id,
                reasoningContent: (msg as any).reasoningContent,
                cost_ms: (msg as any).cost_ms,
                input_tokens: (msg as any).input_tokens,
                output_tokens: (msg as any).output_tokens,
              }),
            }))
            await saveDebugContext(messagesForContext, debugTraceInfo, undefined, undefined, editorData.parameters, editorData.tools)
          } catch (contextError) {
            console.error('❌ 自动保存时保存调试上下文失败:', contextError)
          }
        } else {
          console.error('❌ [AUTO-SAVE-DRAFT] 自动保存失败:', response.msg)
        }
      } catch (error) {
        console.error('❌ [AUTO-SAVE-DRAFT] 自动保存草稿异常:', error)
      }
    },
    [
      promptId,
      isNew,
      userId,
      workspaceId,
      promptMessages,
      parameters,
      modelConfig,
      selectedModel,
      templateEngine,
      toolsEnabled,
      tools,
      modelsLoadingRef,
      loadingRef,
      availableModels,
      promptDraftData,
      chatMessages,
      debugTraceInfo,
      saveDebugContext,
      setDraftSavedTime,
      setIsDraftEdited,
    ],
  )

  // 触发自动保存的函数（带防抖）
  const triggerAutoSave = useCallback(
    (customData?: CustomDraftData, forceSave = false) => {
      console.log('📤 [DRAFT] triggerAutoSave 被调用', {
        hasCustomData: !!customData,
        hasCustomTools: !!customData?.tools,
        customToolsLen: customData?.tools?.length,
        customToolsPreview: customData?.tools?.slice(0, 2).map((t: any) => ({ name: t?.name, defaultValue: t?.defaultValue })),
      })
      // 如果 customData 中有 promptMessages，说明这是用户操作导致的（API 加载时不会传递 customData）
      const isUserOperation = !!customData?.promptMessages

      // 在对比模式下不执行自动保存（除非强制保存）
      if (isComparisonMode && !forceSave) {
        return
      }

      // 如果正在从API加载数据，但这是用户操作（有 customData.promptMessages），则允许保存
      // 否则，如果正在加载数据，不执行自动保存
      if (isLoadingFromAPI && !isUserOperation) {
        return
      }

      // 清除之前的定时器
      if (timerRef.current) {
        console.log('🔄 [DRAFT] 清除之前的自动保存定时器（新一次 triggerAutoSave 调用）', { hasCustomTools: !!customData?.tools })
        clearTimeout(timerRef.current)
        timerRef.current = null
      }

      // 设置新的定时器，1秒后自动保存
      const timer = setTimeout(() => {
        console.log('⏱️ [DRAFT] 防抖定时器执行', {
          hasCustomData: !!customData,
          hasCustomTools: !!customData?.tools,
          customToolsLen: customData?.tools?.length,
        })
        // 在Normal模式下，如果没有提供自定义参数，动态获取最新的参数列表
        // 使用 customData.promptMessages（如果存在）或闭包中的 promptMessages
        const messagesToUse = customData?.promptMessages || promptMessages

        if (templateEngine === 'normal' && !customData?.parameters) {
          const currentVariables = extractVariablesFromNonPlaceholderMessages(messagesToUse, templateEngine)
          const placeholderVars: string[] = []
          messagesToUse.forEach(msg => {
            if (msg.role === 'placeholder' && msg.content.trim()) {
              placeholderVars.push(msg.content.trim())
            }
          })
          const allVariables = [...new Set([...currentVariables, ...placeholderVars])]

          // 生成最新的参数列表
          const latestParameters = allVariables
            .filter(varName => {
              if (!isValidVariableName(varName)) {
                return false
              }
              return true
            })
            .map(varName => {
              const existingParam = parameters.find(p => p.name === varName)
              return (
                existingParam || {
                  name: varName,
                  value: '',
                  desc: `变量 ${varName}`,
                  type: 'string' as const,
                  required: false,
                }
              )
            })

          // 使用最新的参数列表和消息列表进行保存
          autoSaveDraftWithData({
            ...customData,
            promptMessages: messagesToUse,
            parameters: latestParameters,
          })
        } else {
          // 如果有自定义数据则使用，否则使用当前组件状态（不传参数）
          autoSaveDraftWithData(customData)
        }

        // 执行完成后清除引用
        timerRef.current = null
      }, 1000)

      timerRef.current = timer
    },
    [
      autoSaveDraftWithData,
      isComparisonMode,
      isLoadingFromAPI,
      templateEngine,
      extractVariablesFromNonPlaceholderMessages,
      promptMessages,
      parameters,
      isValidVariableName,
      timerRef,
    ],
  )

  return {
    triggerAutoSave,
  }
}
