import { convertApiToolsToFrontendTools } from './toolFormatConverter'
import type { PromptMessage, ComparisonGroupData, OptimizationSource } from '@/types/promptType'
import type { DebugMockTool } from '@test-agentstudio/api-client'
import i18n from '@/i18n'

export const extractDebugErrorMessage = (error: unknown): string => {
  let errorMessage = ''

  // 处理字符串类型错误
  if (typeof error === 'string') {
    const trimmed = error.trim()
    if (trimmed) {
      // 尝试解析 JSON 格式的错误信息
      try {
        const parsed = JSON.parse(trimmed)
        errorMessage = parsed.msg || parsed.message || parsed.error || trimmed
      } catch {
        errorMessage = trimmed
      }
    }
  }

  // 处理对象类型错误
  if (!errorMessage && error && typeof error === 'object') {
    const obj = error as any

    // 直接从错误对象中提取消息
    const message = obj.msg || obj.message || obj.error || obj.detail
    if (typeof message === 'string' && message.trim()) {
      errorMessage = message.trim()
    }

    // 处理嵌套的响应错误（如 axios 错误）
    if (!errorMessage) {
      const responseData = obj.response?.data
      if (responseData) {
        const nestedMessage = responseData.msg || responseData.message || responseData.error
        if (typeof nestedMessage === 'string' && nestedMessage.trim()) {
          errorMessage = nestedMessage.trim()
        }
      }
    }

    // 处理 Error 对象
    if (!errorMessage && obj instanceof Error && obj.message?.trim()) {
      errorMessage = obj.message.trim()
    }
  }

  // 如果没有提取到错误消息，使用默认消息
  if (!errorMessage) {
    errorMessage = i18n.t('utils.prompts.utils.promptEditPageUtils.unknownError')
  }

  // 检查是否需要添加"请求失败"前缀
  const failKeyword = i18n.t('utils.prompts.utils.promptEditPageUtils.failKeyword')
  if (errorMessage.includes(failKeyword) || errorMessage.toLowerCase().includes('fail')) {
    return errorMessage
  }

  return `${i18n.t('utils.prompts.utils.promptEditPageUtils.requestFailed')}: ${errorMessage}`
}

export const generateMessageKey = (): string => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-'
  let result = ''
  for (let i = 0; i < 21; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

export const isValidVariableName = (name: string, allowSpaces: boolean = false): boolean => {
  // 检查变量名前后是否有空格
  // 在 Normal 模式下，前后有空格则无效（例如：{{ user_name }} 不应该被识别，只有 {{user_name}} 才应该被识别）
  // 在 Jinja2 模式下，前后有空格是合法的
  if (!allowSpaces && /^\s|\s$/.test(name)) {
    return false
  }

  // 变量名格式：字母、数字、下划线、连字符，且不能以数字开头
  const regex = /^[a-zA-Z_-][a-zA-Z0-9_-]*$/
  const maxLength = 50

  // 检查长度限制（trim 后再检查，因为空格不算在变量名长度内）
  const trimmedName = name.trim()
  if (trimmedName.length > maxLength) {
    return false
  }

  return regex.test(trimmedName)
}

export const validatePlaceholderContentWithMessage = (value: string): { isValid: boolean; hasError: boolean; originalValue: string } => {
  // 如果是空值，直接返回有效
  if (!value) {
    return { isValid: true, hasError: false, originalValue: value }
  }

  const placeholderRegex = /^[a-zA-Z_-][a-zA-Z0-9_-]*$/
  const maxLength = 50

  // 检查长度限制
  if (value.length > maxLength) {
    return {
      isValid: false,
      hasError: true,
      originalValue: value,
    }
  }

  // 检查是否以数字开头
  if (/^[0-9]/.test(value)) {
    return {
      isValid: false,
      hasError: true,
      originalValue: value,
    }
  }

  // 检查是否包含不支持的字符
  if (!/^[a-zA-Z0-9_-]*$/.test(value)) {
    return {
      isValid: false,
      hasError: true,
      originalValue: value,
    }
  }

  // 检查是否符合完整的规则
  if (!placeholderRegex.test(value)) {
    return {
      isValid: false,
      hasError: true,
      originalValue: value,
    }
  }

  return { isValid: true, hasError: false, originalValue: value }
}

/**
 * 从提示词内容中提取变量名（只提取格式有效的变量名）
 * @param content 提示词内容
 * @returns 有效的变量名数组
 */
export const extractVariables = (content: string, templateEngine: 'normal' | 'jinja2' = 'normal'): string[] => {
  const regex = /\{\{([^}]+)\}\}/g
  const variables: string[] = []
  let match

  while ((match = regex.exec(content)) !== null) {
    const rawVariableName = match[1]
    const trimmedName = rawVariableName.trim()

    // 根据模板引擎决定是否允许前后空格
    const allowSpaces = templateEngine === 'jinja2'
    const isValid = isValidVariableName(rawVariableName, allowSpaces)

    if (isValid) {
      // 变量名有效，添加到数组（去重）
      if (!variables.includes(trimmedName)) {
        variables.push(trimmedName)
      }
      // 如果变量名已存在，说明是重复的，静默跳过（不打印错误）
    } else {
      // 变量名无效，提供详细的错误信息
      let errorMessage = i18n.t('utils.prompts.utils.promptEditPageUtils.variableNameFormatError')
      if (trimmedName.length > 50) {
        errorMessage = i18n.t('utils.prompts.utils.promptEditPageUtils.variableNameTooLong', { length: trimmedName.length })
      } else if (/^[0-9]/.test(trimmedName)) {
        errorMessage = i18n.t('utils.prompts.utils.promptEditPageUtils.variableNameCannotStartWithNumber')
      } else if (!/^[a-zA-Z0-9_-]*$/.test(trimmedName)) {
        errorMessage = i18n.t('utils.prompts.utils.promptEditPageUtils.variableNameInvalidCharacters')
      } else if (!allowSpaces && /^\s|\s$/.test(rawVariableName)) {
        errorMessage = i18n.t('utils.prompts.utils.promptEditPageUtils.variableNameNoSpacesInNormalMode')
      }
      // 只在开发环境输出警告，避免生产环境噪音
      if (process.env.NODE_ENV === 'development') {
        console.warn(`🚫 [VAR-VALIDATION] ${i18n.t('utils.prompts.utils.promptEditPageUtils.skipInvalidVariableName', { name: trimmedName, error: errorMessage })}`)
      }
    }
  }

  return variables
}

/**
 * 从非placeholder消息中提取变量（避免重复）
 * @param promptMessages 提示词消息数组
 * @param templateEngine 模板引擎类型，默认为 'normal'
 * @returns 从非placeholder消息中提取的变量名数组
 */
export const extractVariablesFromNonPlaceholderMessages = (
  promptMessages: Array<{ role: string; content: string }>,
  templateEngine: 'normal' | 'jinja2' = 'normal',
): string[] => {
  const variables: string[] = []

  promptMessages.forEach(msg => {
    if (msg.role !== 'placeholder' && msg.content) {
      const msgVariables = extractVariables(msg.content, templateEngine)
      msgVariables.forEach(varName => {
        if (!variables.includes(varName)) {
          variables.push(varName)
        }
      })
    }
  })

  return variables
}

/**
 * 根据模型ID和来源查找模型
 * @param modelId 模型ID
 * @param modelFrom 模型来源
 * @param models 可用模型列表
 * @returns 找到的模型或undefined
 */
export const findModelByIdAndFrom = (modelId: string, modelFrom?: string, models: any[] = []): any | undefined => {
  return models.find(model => model.openModel.model_id === modelId && (!modelFrom || (model as any).model_from === modelFrom))
}

/**
 * 检查是否配置了有效的模型
 * @param selectedModel 选中的模型
 * @param modelConfig 模型配置
 * @param availableModels 可用模型列表
 * @returns 是否有有效的模型
 */
export const checkValidModel = (
  selectedModel: any | null,
  modelConfig: { model?: string | number; model_from?: string } | null | undefined,
  availableModels: any[],
): boolean => {
  // 1. 检查是否有选中的模型
  if (selectedModel) {
    return true
  }
  // 2. 如果没有选中的模型，检查 modelConfig 中是否有模型配置，并且能在 availableModels 中找到
  if (modelConfig?.model) {
    // 将 model 转换为字符串，确保能调用 trim 方法
    const modelId = typeof modelConfig.model === 'string' ? modelConfig.model.trim() : String(modelConfig.model).trim()
    if (modelId !== '') {
      const modelFromConfig = findModelByIdAndFrom(modelId, modelConfig.model_from, availableModels)
      if (modelFromConfig) {
        return true
      }
    }
  }
  // 3. 如果以上都不满足，说明没有有效的模型配置
  return false
}

/**
 * 处理从API获取的工具数据
 * @param tools API返回的工具数组
 * @returns 处理后的工具数组
 * @deprecated 请使用 convertApiToolsToFrontendTools 代替
 */
export const processToolsFromAPI = (tools: any[]) => {
  // 使用公共转换函数
  return convertApiToolsToFrontendTools(tools, 0).map(tool => ({
    ...tool,
    defaultValue: '', // 默认模拟值由另外一个API填充
    fieldType: 'PlainText' as const, // 保持向后兼容
  }))
}

/**
 * 验证所有 placeholder 消息
 * @param promptMessages 提示词消息数组
 * @param messageInputValues 消息输入值映射
 * @param t 翻译函数
 * @param showSnackbar 显示提示消息的函数
 * @returns 是否所有 placeholder 都有效
 */
export const validateAllPlaceholders = (
  promptMessages: PromptMessage[],
  messageInputValues: { [key: string]: string },
  t: (key: string) => string,
  showSnackbar: (message: string, severity: 'success' | 'error' | 'warning' | 'info') => void,
): boolean => {
  const invalidPlaceholderMessages: string[] = []
  promptMessages.forEach(msg => {
    if (msg.role === 'placeholder') {
      const content = messageInputValues[msg.id] || msg.content
      // 检查是否为空
      if (!content.trim()) {
        invalidPlaceholderMessages.push(`"${content}" - ${t('components.prompts.promptContentEditor.placeholderCannotBeEmpty')}`)
      } else {
        // 检查格式是否有效
        const validationResult = validatePlaceholderContentWithMessage(content.trim())
        if (!validationResult.isValid) {
          invalidPlaceholderMessages.push(`"${content}" - ${t('components.prompts.promptContentEditor.placeholderValidationError')}`)
        }
      }
    }
  })

  // 如果有无效的 placeholder 变量，显示错误
  if (invalidPlaceholderMessages.length > 0) {
    showSnackbar(t('components.prompts.promptContentEditor.invalidPlaceholderVariables'), 'error')
    return false
  }
  return true
}

/**
 * 验证对比组的 placeholder 消息，返回有效的组ID列表
 * @param comparisonGroupsData 对比组数据数组
 * @param t 翻译函数
 * @param showSnackbar 显示提示消息的函数
 * @returns 有效的组ID列表
 */
export const validateComparisonGroupPlaceholders = (
  comparisonGroupsData: ComparisonGroupData[],
  t: (key: string) => string,
  showSnackbar: (message: string, severity: 'success' | 'error' | 'warning' | 'info') => void,
): number[] => {
  const validGroupIds: number[] = []
  const invalidGroups: { groupId: number; groupName: string; errors: string[] }[] = []

  comparisonGroupsData.forEach(group => {
    const invalidPlaceholderMessages: string[] = []

    group.messages.forEach(msg => {
      if (msg.role === 'placeholder') {
        const content = group.messageInputValues[msg.id] || msg.content
        // 检查是否为空
        if (!content.trim()) {
          invalidPlaceholderMessages.push(`"${content}" - ${t('components.prompts.promptContentEditor.placeholderCannotBeEmpty')}`)
        } else {
          // 检查格式是否有效
          const validationResult = validatePlaceholderContentWithMessage(content.trim())
          if (!validationResult.isValid) {
            invalidPlaceholderMessages.push(`"${content}" - ${t('components.prompts.promptContentEditor.placeholderValidationError')}`)
          }
        }
      }
    })

    if (invalidPlaceholderMessages.length > 0) {
      // 记录有错误的组
      const groupName = group.isBaseGroup ? t('prompts.promptEdit.comparison.baseGroup') : `${t('prompts.promptEdit.comparison.controlGroup')}${group.id}`
      invalidGroups.push({
        groupId: group.id,
        groupName: groupName,
        errors: invalidPlaceholderMessages,
      })
    } else {
      // 记录有效的组
      validGroupIds.push(group.id)
    }
  })

  // 如果有无效的组，显示错误信息
  if (invalidGroups.length > 0) {
    showSnackbar(t('components.prompts.promptContentEditor.invalidPlaceholderVariables'), 'error')
  }

  return validGroupIds
}

/**
 * 获取第一个系统消息内容
 * @param optimizationSource 优化源配置
 * @param promptMessages 主提示词消息数组
 * @param comparisonGroupsData 对比组数据数组
 * @returns 第一个系统消息的内容，如果未找到则返回错误提示
 */
export const getFirstSystemMessage = (
  optimizationSource: OptimizationSource,
  promptMessages: PromptMessage[],
  comparisonGroupsData: ComparisonGroupData[],
): string => {
  if (optimizationSource.type === 'main') {
    const systemMessage = promptMessages.find(msg => msg.role === 'system')
    return systemMessage?.content || i18n.t('utils.prompts.utils.promptEditPageUtils.targetMessageNotFound')
  } else if (optimizationSource.type === 'base' || optimizationSource.type === 'control') {
    // 基准组和对照组统一处理：基准组编号为0，对照组使用指定的groupId
    const groupId = optimizationSource.type === 'base' ? 0 : optimizationSource.groupId
    if (groupId === undefined) {
      return i18n.t('utils.prompts.utils.promptEditPageUtils.targetMessageNotFound')
    }
    const group = comparisonGroupsData.find(g => g.id === groupId)
    const systemMessage = group?.messages.find(msg => msg.role === 'system')
    const groupName = optimizationSource.type === 'base' 
      ? i18n.t('utils.prompts.utils.promptEditPageUtils.baseGroup') 
      : i18n.t('utils.prompts.utils.promptEditPageUtils.controlGroup', { id: groupId })
    return systemMessage?.content || i18n.t('utils.prompts.utils.promptEditPageUtils.targetMessageNotFoundInGroup', { groupName })
  }
  return i18n.t('utils.prompts.utils.promptEditPageUtils.targetMessageNotFound')
}

/**
 * 增量处理工具调用
 * @param existingToolCalls 现有的工具调用数组
 * @param deltaToolCalls 增量工具调用数组
 * @param mockTools 模拟工具数组
 * @returns 处理后的工具调用数组
 */
export const processToolCallsIncremental = (
  existingToolCalls: Array<{ name: string; input: string; output: string; id?: string; index?: number }> = [],
  deltaToolCalls: Array<{
    index?: number // 改为可选，因为某些模型可能不提供 index
    id?: string
    function: {
      arguments?: string
      name?: string
    }
    type?: string // 可选字段，可能是 "function_call" 或 "function"，但不影响解析逻辑
  }>,
  mockTools: DebugMockTool[],
): Array<{ name: string; input: string; output: string; id?: string; index?: number }> => {
  const updatedToolCalls = [...existingToolCalls]

  deltaToolCalls.forEach((deltaCall, arrayIndex) => {
    const { index, function: func } = deltaCall

    // 如果 index 不存在，尝试使用数组索引或根据 id 匹配现有工具调用
    let targetIndex: number
    if (index !== undefined && index !== null && typeof index === 'number') {
      targetIndex = index
    } else {
      // 如果提供了 id，尝试根据 id 匹配现有的工具调用
      if (deltaCall.id) {
        const existingIndex = updatedToolCalls.findIndex(tc => tc.id === deltaCall.id)
        if (existingIndex >= 0) {
          targetIndex = existingIndex
        } else {
          // 如果没有找到匹配的，使用数组索引
          targetIndex = arrayIndex
        }
      } else {
        // 如果没有 id，使用数组索引
        targetIndex = arrayIndex
      }
    }

    // 确保数组有足够的长度
    while (updatedToolCalls.length <= targetIndex) {
      updatedToolCalls.push({ name: '', input: '', output: '', id: undefined, index: undefined })
    }

    const existingCall = updatedToolCalls[targetIndex]

    // 确保 existingCall 存在
    if (!existingCall) {
      console.warn(`⚠️ [PROCESS] ${i18n.t('utils.prompts.utils.promptEditPageUtils.existingCallNotFound', { index: targetIndex })}`)
      return
    }

    // 累积更新工具调用信息
    // 保存ID和index信息
    if (deltaCall.id && !existingCall.id) {
      existingCall.id = deltaCall.id
      existingCall.index = targetIndex
    }

    if (func.name) {
      existingCall.name = func.name
      // 当获得工具名称时，设置输出
      const mockTool = mockTools.find(tool => tool.name === func.name)
      existingCall.output = mockTool?.mock_response || mockTool?.mock_value || ''
    }

    if (func.arguments !== undefined && func.arguments !== null) {
      // 防止重复累积：只有当当前片段与上次添加的完全相同时才跳过
      // 使用更精确的检查，避免误判导致字符丢失
      const currentArguments = func.arguments
      const beforeInput = existingCall.input
      
      // 检查是否是完全重复的片段
      // 只有当整个新片段已经完整存在于末尾时才认为是重复
      const shouldSkip = currentArguments.length > 0 && 
                        beforeInput.length >= currentArguments.length &&
                        beforeInput.endsWith(currentArguments)
      
      if (!shouldSkip) {
        existingCall.input += currentArguments
      }
    }
  })

  // 最后进行一次数据清理，确保没有异常的格式
  const cleanedToolCalls = updatedToolCalls.map(toolCall => ({
    ...toolCall,
    // 清理可能的重复或异常格式
    input: toolCall.input
      .replace(/(\{"\{)/g, '{"')
      .replace(/(\}"\})/g, '"}'),
  }))

  return cleanedToolCalls
}

/**
 * 计算选中文本在提示词内容中的位置索引
 * @param selectedText 选中的文本
 * @param promptContent 提示词内容
 * @returns 选中文本的起始和结束位置，如果未找到则返回null
 */
export const calculateSelectionIndices = (selectedText: string, promptContent: string): { start: number; end: number } | null => {
  if (!selectedText || !promptContent) {
    console.warn(`🔍 [INDICES] ${i18n.t('utils.prompts.utils.promptEditPageUtils.calculateSelectionIndicesFailed')}:`, {
      hasSelectedText: !!selectedText,
      hasPromptContent: !!promptContent,
      selectedTextLength: selectedText?.length,
      promptContentLength: promptContent?.length,
    })
    return null
  }

  // 尝试多种匹配方式
  const findTextIndex = (text: string, content: string) => {
    // 1. 直接匹配
    let startIndex = content.indexOf(text)
    if (startIndex !== -1) {
      return { startIndex, matchedText: text, method: 'exact' }
    }

    // 2. 去除首尾空白后匹配
    const trimmedText = text.trim()
    startIndex = content.indexOf(trimmedText)
    if (startIndex !== -1) {
      return { startIndex, matchedText: trimmedText, method: 'trimmed' }
    }

    // 3. 标准化换行符后匹配
    const normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
    const normalizedContent = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
    startIndex = normalizedContent.indexOf(normalizedText)
    if (startIndex !== -1) {
      // 需要在原始内容中找到对应位置
      const beforeNormalized = content.substring(0, startIndex).replace(/\r\n/g, '\n').replace(/\r/g, '\n')
      const originalStartIndex = beforeNormalized.length
      return { startIndex: originalStartIndex, matchedText: normalizedText, method: 'normalized' }
    }

    // 4. 同时去除空白和标准化换行符
    const fullyNormalizedText = normalizedText.trim()
    startIndex = normalizedContent.indexOf(fullyNormalizedText)
    if (startIndex !== -1) {
      const beforeNormalized = content.substring(0, startIndex).replace(/\r\n/g, '\n').replace(/\r/g, '\n')
      const originalStartIndex = beforeNormalized.length
      return { startIndex: originalStartIndex, matchedText: fullyNormalizedText, method: 'fully_normalized' }
    }

    return null
  }

  const matchResult = findTextIndex(selectedText, promptContent)
  if (!matchResult) {
    return null
  }

  const { startIndex, matchedText } = matchResult
  const endIndex = startIndex + matchedText.length
  return { start: startIndex, end: endIndex }
}
