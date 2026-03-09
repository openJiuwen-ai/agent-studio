import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { PromptService, PromptModelService, type MockContext } from '@test-agentstudio/api-client'
import type { Model, ModelConfig } from '@/types/promptType'
import { findModelByIdAndFrom, isValidVariableName } from '@/utils/prompts/promptEditPageUtils'
import { convertApiToolsToFrontendTools } from '@/utils/prompts/toolFormatConverter'

interface UseLoadPromptProps {
  // 基本参数（用于 loadPromptDetail）
  id?: string
  isNew?: boolean
  workspaceId?: string
  userId?: string

  // 状态 setter（基础）
  setTemplateEngine: (engine: 'normal' | 'jinja2') => void
  setPromptMessages: (messages: any[]) => void
  setMessageInputValues: (values: { [key: string]: string }) => void
  setParameters: React.Dispatch<React.SetStateAction<any[]>>
  setTools: React.Dispatch<React.SetStateAction<any[]>>
  setToolsEnabled: (enabled: boolean) => void
  setSelectedModel: (model: Model | null) => void
  setModelConfig: React.Dispatch<React.SetStateAction<ModelConfig>>

  // 状态 setter（用于 loadPromptDetail）
  setPrompt?: React.Dispatch<React.SetStateAction<{ key: string; name: string; description: string }>>
  setLatestVersion?: (version: string) => void
  setPromptCommitData?: (data: any) => void
  setPromptDraftData?: (data: any) => void
  setIsDraftEdited?: (edited: boolean) => void
  setDraftSavedTime?: (time: Date | null) => void
  setIsNewPromptScenario?: (isNew: boolean) => void
  setLoading?: (loading: boolean) => void
  setIsLoadingFromAPI?: (loading: boolean) => void
  setSnackbar?: (snackbar: { open: boolean; message: string; severity: 'success' | 'error' | 'warning' | 'info' }) => void

  // 状态 setter（用于 loadModels）
  setAvailableModels?: (models: Model[]) => void
  setModelsLoading?: (loading: boolean) => void

  // 状态 setter（用于 loadDebugContext）
  setChatMessages?: (messages: any[]) => void
  setCompletedMessages?: (messages: Set<number>) => void

  // 依赖数据
  availableModels: Model[]
  selectedModel?: Model | null

  // Refs（用于 loadPromptDetail）
  loadingRef?: React.MutableRefObject<boolean>
  optimizedDataApplied?: React.MutableRefObject<boolean>
  modelsLoadingRef?: React.MutableRefObject<boolean>

  // 回调函数（用于 loadPromptDetail）
  showSnackbar?: (message: string, severity: 'success' | 'error' | 'warning' | 'info') => void
}

export const useLoadPrompt = ({
  // 基本参数
  id,
  isNew,
  workspaceId,
  userId,
  // 基础状态 setters
  setTemplateEngine,
  setPromptMessages,
  setMessageInputValues,
  setParameters,
  setTools,
  setToolsEnabled,
  setSelectedModel,
  setModelConfig,
  // 扩展状态 setters
  setPrompt,
  setLatestVersion,
  setPromptCommitData,
  setPromptDraftData,
  setIsDraftEdited,
  setDraftSavedTime,
  setIsNewPromptScenario,
  setLoading,
  setIsLoadingFromAPI,
  setSnackbar,
  setAvailableModels,
  setModelsLoading,
  setChatMessages,
  setCompletedMessages,
  // 依赖数据
  availableModels,
  selectedModel,
  // Refs
  loadingRef,
  optimizedDataApplied,
  modelsLoadingRef,
  // 回调函数
  showSnackbar,
}: UseLoadPromptProps) => {
  const { t } = useTranslation()

  // 加载调试上下文的独立函数
  const loadDebugContext = useCallback(async () => {
    // 如果没有提供必要的参数，直接返回
    if (!setChatMessages || !setCompletedMessages || !setParameters || !setTools) {
      return
    }

    // 只有在非新建提示词且有ID、workspaceId的情况下才加载
    if (!isNew && id && workspaceId) {
      try {
        const response = await PromptService.getDebugContext(id, workspaceId)

        if (response.code === 0 && response.debug_context) {
          const { debug_core } = response.debug_context

          // 恢复聊天消息
          if (debug_core.mock_contexts && debug_core.mock_contexts.length > 0) {
            const chatMessagesFromContext = debug_core.mock_contexts.map((context: MockContext) => ({
              type: context.role === 'user' ? ('user' as const) : ('ai' as const),
              content: context.content,
              timestamp: context.msg_time || new Date().toLocaleString('zh-CN'), // 使用msg_time字段设置消息时间
              // 保存额外的AI信息用于后续显示
              ...(context.role === 'assistant' && {
                reasoningContent: context.reasoning_content,
                input_tokens: context.input_tokens,
                output_tokens: context.output_tokens,
                cost_ms: context.cost_ms,
                debug_id: context.debug_id,
                // 处理工具调用信息
                ...(context.tool_calls &&
                  Array.isArray(context.tool_calls) && {
                    toolCalls: context.tool_calls.map((toolCallData: any) => ({
                      name: toolCallData.tool_call?.function_call?.name || '',
                      input: toolCallData.tool_call?.function_call?.arguments || '',
                      output: toolCallData.mock_response || '',
                      id: toolCallData.tool_call?.id,
                      index: parseInt(toolCallData.tool_call?.index || '0'),
                    })),
                  }),
              }),
            }))

            setChatMessages(chatMessagesFromContext)

            // 标记所有恢复的消息为已完成，这样它们会显示控制按钮
            const completedIndices = new Set<number>()
            for (let i = 0; i < chatMessagesFromContext.length; i++) {
              completedIndices.add(i)
            }
            setCompletedMessages(completedIndices)
          }

          // 恢复变量值
          if (debug_core.mock_variables && debug_core.mock_variables.length > 0) {
            setTimeout(() => {
              setParameters((prevParams: any) => {
                const updatedParams = [...prevParams]
                debug_core.mock_variables.forEach(variable => {
                  const paramIndex = updatedParams.findIndex(p => p.name === variable.key)
                  if (paramIndex !== -1) {
                    if (variable.type === 'placeholder' && variable.placeholder_messages) {
                      // placeholder类型变量：恢复placeholder_messages
                      updatedParams[paramIndex] = {
                        ...updatedParams[paramIndex],
                        type: 'placeholder',
                        messages: variable.placeholder_messages.map(msg => ({
                          id: msg.id || Date.now().toString() + Math.random().toString(36).substr(2, 5),
                          role: msg.role,
                          content: msg.content,
                        })),
                      }
                    } else {
                      // 普通变量：恢复value
                      updatedParams[paramIndex] = {
                        ...updatedParams[paramIndex],
                        value: variable.value,
                      }
                    }
                  }
                })
                return updatedParams
              })
            }, 100) // 延迟确保参数已经初始化
          }

          // 恢复工具配置
          if (debug_core.mock_tools && debug_core.mock_tools.length > 0) {
            setTimeout(() => {
              setTools((prevTools: any) => {
                const updatedTools = [...prevTools]
                debug_core.mock_tools.forEach(mockTool => {
                  const toolIndex = updatedTools.findIndex(t => t.name === mockTool.name)
                  if (toolIndex !== -1) {
                    updatedTools[toolIndex] = {
                      ...updatedTools[toolIndex],
                      defaultValue: mockTool.mock_response,
                    }
                  }
                })
                return updatedTools
              })
            }, 100) // 延迟确保工具已经初始化
          }

          // 调试配置已移除，不再恢复
        } else if (response.code !== 0) {
          console.warn('⚠️ [DEBUG-CONTEXT] 查询调试上下文失败:', response.msg || '未知错误')
          // 不显示错误提示，因为可能是首次使用，没有调试上下文数据
        }
      } catch (error) {
        console.error('❌ [DEBUG-CONTEXT] 加载调试上下文失败:', error)
        // 不显示错误提示，因为调试上下文是可选的
      }
    }
  }, [id, isNew, userId, setChatMessages, setCompletedMessages, setParameters, setTools])

  // 加载模型列表
  const loadModels = useCallback(async () => {
    // 如果没有提供必要的参数，直接返回
    if (!setAvailableModels || !setModelsLoading || !modelsLoadingRef || !showSnackbar) {
      return
    }

    // 防止重复调用
    if (modelsLoadingRef.current) {
      return
    }

    // 检查工作空间ID是否有效
    if (!workspaceId) {
      return
    }

    modelsLoadingRef.current = true
    setModelsLoading(true)
    try {
      const response = await PromptModelService.getModelsList({ workspaceId: workspaceId })

      setAvailableModels(response.models as any)

      // 如果没有选中的模型，不自动选择模型
    } catch (error) {
      console.error('加载模型列表失败:', error)
      showSnackbar(t('hooks.prompts.useLoadPrompt.loadModelsFailed'), 'error')
    } finally {
      setModelsLoading(false)
      modelsLoadingRef.current = false
    }
  }, [workspaceId, showSnackbar, selectedModel, setAvailableModels, setModelsLoading, modelsLoadingRef, t])

  // 将已有的 prompt detail 数据填充到页面
  const loadPromptDetailToPage = useCallback(
    async (promptDetailData: any, isNewPromptScenario: boolean = false) => {
      // 1. 填充模板类型
      if (promptDetailData.prompt_template?.template_type) {
        setTemplateEngine(promptDetailData.prompt_template.template_type as 'normal' | 'jinja2')
      }

      // 2. 填充提示词内容
      if (promptDetailData.prompt_template?.messages) {
        // 转换消息格式，确保每个消息都有id字段
        const promptMessages = promptDetailData.prompt_template.messages.map((msg: any, index: number) => ({
          id: msg.id || msg.key || `msg_${Date.now()}_${index}`,
          role: msg.role as 'system' | 'user' | 'assistant' | 'placeholder',
          content: msg.content || '',
          placeholderName: msg.role === 'placeholder' ? msg.content : undefined,
        }))
        setPromptMessages(promptMessages)

        // 设置消息输入值
        const inputValues: { [key: string]: string } = {}
        promptMessages.forEach((msg: any) => {
          inputValues[msg.id] = msg.content
        })
        setMessageInputValues(inputValues)
      }

      // 3. 填充变量定义
      if (promptDetailData.prompt_template?.variable_defs) {
        const variableParams = promptDetailData.prompt_template.variable_defs
          .filter((varDef: any) => {
            if (!isValidVariableName(varDef.key)) {
              console.warn(`🚫 [VAR-VALIDATION] 跳过草稿数据中的无效变量名: "${varDef.key}"，不符合格式要求`)
              return false
            }
            return true
          })
          .map((varDef: any) => ({
            name: varDef.key,
            value: '', // 变量值由另外一个API填充
            description: varDef.desc || '',
            type: varDef.type === 'placeholder' ? 'placeholder' : 'text',
            dataType: varDef.type || 'string', // 使用API返回的实际类型
          }))
        setParameters(variableParams)
      }

      // 4. 填充工具设置
      if (promptDetailData.tools) {
        const convertedTools = convertApiToolsToFrontendTools(promptDetailData.tools, 0)
        setTools(convertedTools)
      }

      // 5. 填充工具调用配置
      if (promptDetailData.tool_call_config) {
        const toolChoice = promptDetailData.tool_call_config.tool_choice
        const isToolsEnabled = toolChoice === 'auto'
        setToolsEnabled(isToolsEnabled)
      } else {
        setToolsEnabled(false)
      }

      // 6. 填充模型配置
      // 如果是新建提示词场景，不使用default_config中的模型配置，而是自动选择第一个模型
      if (isNewPromptScenario) {
        // 如果模型列表已加载，选择第一个模型
        if (availableModels.length > 0) {
          const firstModel = availableModels[0]
          setSelectedModel?.(firstModel)
          const defaultParams = PromptModelService.getModelDefaultParams(firstModel)
          setModelConfig(prev => ({
            ...prev,
            model: firstModel.openModel.model_id,
            model_from: firstModel.model_from,
            ...defaultParams,
          }))
        } else {
          // 如果模型列表还未加载，loadModels会在后续自动设置默认模型
        }
      } else if (promptDetailData.prompt_model_config) {
        // 非新建提示词场景，从数据源读取模型配置
        const modelConfig = promptDetailData.prompt_model_config

        // 根据models_id从模型列表中找到对应的模型
        if (modelConfig.models_id) {
          try {
            let targetModel = null

            // 如果模型列表已经加载，先尝试从中查找
            if (availableModels.length > 0) {
              targetModel = findModelByIdAndFrom(modelConfig.models_id, modelConfig.model_from, availableModels)
            }

            // 如果在模型列表中没找到（或列表未加载），调用模型详情API
            if (!targetModel) {
              targetModel = await PromptModelService.getModelDetail(
                modelConfig.models_id,
                modelConfig.model_from,
                workspaceId,
              )
            }

            // 设置选中的模型（如果没找到则设置为null表示未选中）
            setSelectedModel?.(targetModel)
          } catch (error) {
            console.error('获取模型详情失败:', error)
            // 如果获取模型失败（例如模型已被删除），将选中的模型设置为null
            setSelectedModel?.(null)
          }
        }

        // 设置模型参数配置 (temperature、max_tokens、top_p等)
        const newModelConfig: any = {}

        // 处理各个参数，如果实际值为null则使用默认值
        if (selectedModel?.openModel?.param_config?.param_schemas) {
          selectedModel.openModel.param_config.param_schemas.forEach((schema: any) => {
            const paramName = schema.name
            const actualValue = modelConfig[paramName]

            if (actualValue !== null && actualValue !== undefined) {
              // 使用实际值
              newModelConfig[paramName] = actualValue
            } else {
              // 使用默认值
              newModelConfig[paramName] = schema.default_val
            }
          })
        } else {
          // 如果没有模型schema，直接使用非null的值
          Object.keys(modelConfig).forEach(key => {
            if (!['models_id', 'models_name'].includes(key) && modelConfig[key] !== null && modelConfig[key] !== undefined) {
              newModelConfig[key] = modelConfig[key]
            }
          })
        }

        // 合并模型ID和参数配置
        setModelConfig(prev => ({
          ...prev,
          model: modelConfig.models_id || prev.model,
          model_from: modelConfig.model_from || prev.model_from,
          ...newModelConfig,
        }))
      }
    },
    [
      setTemplateEngine,
      setPromptMessages,
      setMessageInputValues,
      setParameters,
      setTools,
      setToolsEnabled,
      setSelectedModel,
      setModelConfig,
      availableModels,
      selectedModel,
    ],
  )

  // 从 API 加载提示词详情数据
  const loadPromptDetail = useCallback(
    async (forceLoad = false) => {
      // 如果没有提供必要的参数，直接返回
      if (!setPrompt || !setLatestVersion || !setPromptCommitData || !setPromptDraftData || 
          !setIsDraftEdited || !setDraftSavedTime || !setIsNewPromptScenario || 
          !setLoading || !setIsLoadingFromAPI || !setSnackbar || 
          !loadingRef || !optimizedDataApplied) {
        return
      }

      // 防止重复调用
      if (loadingRef.current && !forceLoad) {
        return
      }

      // 检查必要的依赖是否准备就绪
      if (!workspaceId) {
        return
      }

      // 如果sessionStorage中有优化数据或覆盖数据，暂时跳过加载以避免覆盖（除非强制加载）
      if (!forceLoad) {
        const optimizedData = sessionStorage.getItem('optimizedPromptData')
        const overrideData = sessionStorage.getItem('promptOverrideData')
        if (optimizedData || overrideData) {
          return
        }

        // 如果优化数据已经应用，也跳过加载以避免覆盖
        if (optimizedDataApplied.current) {
          return
        }
      }

      // 对于新建提示词，如果没有ID则跳过
      if (isNew && !id) {
        return
      }

      // 对于编辑现有提示词，必须有ID
      if (!isNew && !id) {
        return
      }

      try {
        loadingRef.current = true // 设置加载标志
        setLoading(true)
        setIsLoadingFromAPI(true) // 标记开始从API加载

        // 对于新建提示词，我们使用一个特殊的ID来获取默认配置
        // 或者我们可以创建一个专门的API，但目前先使用占位符ID
        const apiId = isNew ? '0' : (id || '0') // 使用'0'作为获取默认配置的特殊ID

        const response = await PromptService.getPromptDetail(apiId, {
          withCommit: true,
          withDraft: true,
          withDefaultConfig: true,
          workspaceId: workspaceId,
        })

        if (response.code !== 0) {
          setSnackbar({
            open: true,
            message: response.msg || t('hooks.prompts.useLoadPrompt.getPromptDetailFailed'),
            severity: 'error',
          })
          return
        }

        const promptDetail = response.prompt && response.prompt.length > 0 ? response.prompt[0] : null

        // 保存prompt_commit数据用于版本对比
        if (promptDetail?.prompt_commit?.detail) {
          setPromptCommitData(promptDetail.prompt_commit.detail)
        } else {
          setPromptCommitData(null)
        }

        // 保存prompt_draft数据并检查是否有未提交的草稿
        if (promptDetail?.prompt_draft) {
          setPromptDraftData(promptDetail.prompt_draft.detail)

          // 检查草稿是否已编辑
          const isDraftEditedValue = promptDetail.prompt_draft.draft_info?.is_draft_edited || false
          setIsDraftEdited(isDraftEditedValue)

          // 设置草稿保存时间
          if (promptDetail.prompt_draft.draft_info?.updated_at) {
            const draftTime = new Date(promptDetail.prompt_draft.draft_info.updated_at)
            setDraftSavedTime(draftTime)
          }
        } else {
          setPromptDraftData(null)
          setIsDraftEdited(false)
          setDraftSavedTime(null)
        }

        // 判断使用哪个数据源：
        // 1. 如果是新建提示词(isNew=true)，使用default_config
        // 2. 如果来自新创建的提示词页面（检查localStorage），使用default_config
        // 3. 否则使用prompt_draft
        const basicInfoStr = localStorage.getItem('newPromptBasicInfo')
        const isFromNewPrompt = basicInfoStr && JSON.parse(basicInfoStr)?.prompt_id?.toString() === id

        let dataSource: any
        let isNewPromptScenarioLocal = false

        if (isNew || isFromNewPrompt) {
          // 新建提示词场景 - 使用default_config
          dataSource = response.default_config
          isNewPromptScenarioLocal = true
          if (isFromNewPrompt) {
            localStorage.removeItem('newPromptBasicInfo') // 清除标记
          }
        } else {
          // 从提示词管理页面进入的编辑场景
          dataSource = promptDetail?.prompt_draft?.detail

          // 如果prompt_draft不存在，尝试使用prompt_commit
          if (!dataSource && promptDetail?.prompt_commit?.detail) {
            dataSource = promptDetail.prompt_commit.detail
          }

          // 如果都不存在，使用default_config作为后备
          if (!dataSource && response.default_config) {
            dataSource = response.default_config
            isNewPromptScenarioLocal = true
          }
        }

        // 设置新建提示词场景状态
        setIsNewPromptScenario(isNewPromptScenarioLocal)

        if (!dataSource) {
          console.warn('未找到可用的数据源，API响应:', response)
          console.warn('尝试的数据源路径:', {
            'response.default_config': response.default_config,
            'promptDetail?.prompt_draft?.detail': promptDetail?.prompt_draft?.detail,
            'promptDetail?.prompt_commit?.detail': promptDetail?.prompt_commit?.detail,
          })
          return
        }

        // 填充基本信息
        if (promptDetail) {
          setPrompt(prev => ({
            ...prev,
            key: promptDetail.prompt_key,
            name: promptDetail.prompt_basic.display_name,
            description: promptDetail.prompt_basic.description,
          }))

          // 提取最新版本号
          if (promptDetail.prompt_basic.latest_version) {
            setLatestVersion(promptDetail.prompt_basic.latest_version)
          }
        }

        // 使用 loadPromptDetailToPage 填充数据到页面
        await loadPromptDetailToPage(dataSource, isNewPromptScenarioLocal)
      } catch (error) {
        console.error('加载提示词详情失败:', error)
        setSnackbar({
          open: true,
          message: t('hooks.prompts.useLoadPrompt.loadPromptDetailFailed'),
          severity: 'error',
        })
      } finally {
        setLoading(false)
        // 延迟清除加载标记，确保所有状态都已设置完成
        setTimeout(async () => {
          setIsLoadingFromAPI(false)
          // 提示词详情加载完成后，立即加载调试上下文
          await loadDebugContext()

          // 清除加载标志
          loadingRef.current = false
        }, 200) // 增加延迟确保状态完全更新
      }
    },
    [
      id,
      isNew,
      workspaceId,
      userId,
      setPrompt,
      setLatestVersion,
      setPromptCommitData,
      setPromptDraftData,
      setIsDraftEdited,
      setDraftSavedTime,
      setIsNewPromptScenario,
      setLoading,
      setIsLoadingFromAPI,
      setSnackbar,
      availableModels,
      loadingRef,
      optimizedDataApplied,
      loadDebugContext,
      setTemplateEngine,
      setPromptMessages,
      setMessageInputValues,
      setParameters,
      setTools,
      setToolsEnabled,
      setSelectedModel,
      setModelConfig,
      t,
    ],
  )

  return {
    loadDebugContext,
    loadModels,
    loadPromptDetailToPage,
    loadPromptDetail,
  }
}

// 为了向后兼容，保留 useLoadPromptDetail 的导出
export const useLoadPromptDetail = useLoadPrompt
