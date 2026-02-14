import { getApiClient, stream } from '../utils/apiClientFactory'
import { API_ENDPOINTS } from '../config'
import { PromptModelService } from './promptModelService'
import {
  CreatePromptRequest,
  CreatePromptResponse,
  UpdatePromptRequest,
  EditPromptBasicInfoRequest,
  EditPromptBasicInfoResponse,
  DeletePromptRequest,
  DeletePromptResponse,
  ApiPromptListResponse,
  PromptListResponse,
  GetPromptDetailRequest,
  GetPromptDetailResponse,
  SaveDraftRequest,
  SaveDraftResponse,
  CommitVersionRequest,
  CommitVersionResponse,
  RevertToVersionRequest,
  RevertToVersionResponse,
  GetVersionListRequest,
  GetVersionListResponse,
  DebugStreamingRequest,
  SaveDebugContextRequest,
  GetDebugContextResponse,
  ClonePromptRequest,
  ClonePromptResponse,
  DebugHistoryListRequest,
  DebugHistoryListResponse,
  Prompt,
  ApiPrompt,
  ApiUser,
  RelationObj,
} from '../types/promptTypes'

/**
 * 提示词管理服务类
 * 提供提示词的增删改查、草稿管理、版本管理、调试等功能
 */
export class PromptService {
  /**
   * 将API数据转换为前端展示格式
   * @param apiPrompt API返回的提示词数据
   * @returns 前端展示用的提示词数据
   */
  private static transformApiPromptToPrompt(apiPrompt: ApiPrompt): Prompt {
    try {
      // 添加数据完整性检查
      if (!apiPrompt) {
        throw new Error('API返回的提示词数据为空')
      }

      const { id, prompt_key, prompt_basic, prompt_draft } = apiPrompt

      // 检查必要字段
      if (!id || !prompt_key || !prompt_basic) {
        console.error('API数据结构不完整:', apiPrompt)
        throw new Error('API返回的提示词数据结构不完整')
      }

      // 检查是否有未提交的草稿修改
      const isDraftEdited = prompt_draft?.draft_info?.is_draft_edited || false

      // 计算最后修改时间：取 prompt_basic.updated_at 和 prompt_draft.draft_info.updated_at 中的最大值
      const basicUpdatedAt = prompt_basic.updated_at ? new Date(prompt_basic.updated_at).getTime() : 0
      const draftUpdatedAt = prompt_draft?.draft_info?.updated_at ? new Date(prompt_draft.draft_info.updated_at).getTime() : 0
      const lastModified =
        basicUpdatedAt >= draftUpdatedAt ? prompt_basic.updated_at || '' : prompt_draft?.draft_info?.updated_at || prompt_basic.updated_at || ''

      // 使用API返回的关联对象数据
      const associations = {
        relationObjs: apiPrompt.relation_obj || [],
      }

      return {
        id: id.toString(),
        name: prompt_basic.display_name || '',
        description: prompt_basic.description || '',
        content: '', // 内容需要从详情接口获取
        category: 'default',
        tags: [],
        version: prompt_basic.latest_version || '-',
        usageCount: 0,
        rating: 0,
        isPublic: false,
        author: prompt_basic.created_by_name || prompt_basic.created_by || '',
        createdAt: prompt_basic.created_at || '',
        lastModified,
        prompt_key,
        updated_by: prompt_basic.updated_by_name || prompt_basic.updated_by || '',
        isDraftEdited,
        associations,
        // 添加最近提交时间字段
        latest_committed_at: prompt_basic.latest_committed_at || null,
      }
    } catch (error) {
      console.error('转换提示词数据失败:', error, apiPrompt)
      throw error
    }
  }

  /**
   * 获取提示词列表
   * @param params 查询参数
   * @returns 提示词列表响应
   */
  static async getPrompts(params?: {
    page?: number
    pageSize?: number
    search?: string
    key_word?: string
    category?: string
    tags?: string[]
    isPublic?: boolean
    workspaceId?: string
    order_by?: string
    asc?: boolean
  }): Promise<PromptListResponse> {
    // 构建API请求参数
    const apiParams: any = {
      workspace_id: params?.workspaceId || '', // 应该从组件传入
      page_num: params?.page || 1,
      page_size: params?.pageSize || 20,
    }

    // 如果提供了搜索关键词，添加到API参数中
    if (params?.key_word) {
      apiParams.key_word = params.key_word
    }

    // 如果提供了排序参数，添加到API参数中
    if (params?.order_by) {
      apiParams.order_by = params.order_by
    }
    if (params?.asc !== undefined) {
      apiParams.asc = params.asc
    }

    // 调用API
    const response = await getApiClient().post<ApiPromptListResponse>(API_ENDPOINTS.PROMPTS.LIST, apiParams)

    const apiResponse = response.data

    // 检查API响应
    if (!apiResponse) {
      throw new Error('API响应为空')
    }

    if (apiResponse.code !== 0) {
      const errorMsg = apiResponse.msg || '获取提示词列表失败'
      console.error('API返回错误:', {
        code: apiResponse.code,
        message: errorMsg,
      })
      throw new Error(errorMsg)
    }

    // 检查提示词数组
    if (!Array.isArray(apiResponse.prompts)) {
      console.error('API返回的prompts不是数组:', apiResponse.prompts)
      throw new Error('API返回的数据格式不正确')
    }

    // 转换数据格式
    const transformedPrompts = apiResponse.prompts.map(apiPrompt => this.transformApiPromptToPrompt(apiPrompt))

    return {
      prompts: transformedPrompts,
      total: apiResponse.total || 0,
      page: params?.page || 1,
      pageSize: params?.pageSize || 20,
    }
  }

  /**
   * 获取提示词详情
   * @param promptId 提示词ID
   * @param options 选项
   * @returns 提示词详情响应
   */
  static async getPromptDetail(
    promptId: string,
    options?: {
      withCommit?: boolean
      withDraft?: boolean
      withDefaultConfig?: boolean
      workspaceId?: string
      commitVersion?: string
    },
  ): Promise<GetPromptDetailResponse> {
    const params: GetPromptDetailRequest = {
      workspace_id: options?.workspaceId || '',
      with_commit: options?.withCommit || false,
      with_draft: options?.withDraft || false,
      with_default_config: options?.withDefaultConfig || false,
      ...(options?.commitVersion && { commit_version: options.commitVersion }),
    }

    const response = await getApiClient().get<GetPromptDetailResponse>(API_ENDPOINTS.PROMPTS.DETAIL.replace(':id', promptId), { params })

    if (response.data.code !== 0) {
      throw new Error(response.data.msg || '获取提示词详情失败')
    }

    return response.data
  }

  /**
   * 创建提示词
   * @param data 创建提示词数据
   * @returns 创建提示词响应
   */
  static async createPrompt(data: CreatePromptRequest): Promise<CreatePromptResponse> {
    const response = await getApiClient().post<CreatePromptResponse>(API_ENDPOINTS.PROMPTS.CREATE, data)

    if (response.data.code !== 0) {
      throw new Error(response.data.msg || '创建提示词失败')
    }

    return response.data
  }

  /**
   * 编辑提示词基本信息
   * @param promptId 提示词ID
   * @param data 编辑数据
   * @returns 编辑响应
   */
  static async editPromptBasicInfo(
    promptId: string,
    data: {
      prompt_name: string
      prompt_description: string
    },
  ): Promise<EditPromptBasicInfoResponse> {
    const requestData: EditPromptBasicInfoRequest = {
      prompt_id: parseInt(promptId),
      prompt_name: data.prompt_name,
      prompt_description: data.prompt_description,
    }

    const response = await getApiClient().put<EditPromptBasicInfoResponse>(API_ENDPOINTS.PROMPTS.UPDATE.replace(':id', promptId), requestData)

    if (response.data.code !== 0) {
      throw new Error(response.data.msg || '编辑提示词基本信息失败')
    }

    return response.data
  }

  /**
   * 删除提示词
   * @param promptId 提示词ID
   * @param workspaceId 工作空间ID（请求体 workspace_id）
   * @returns 删除响应
   */
  static async deletePrompt(promptId: string, workspaceId: string): Promise<DeletePromptResponse> {
    const requestData: DeletePromptRequest = {
      prompt_id: parseInt(promptId),
      workspace_id: workspaceId,
    }

    const response = await getApiClient().delete<DeletePromptResponse>(API_ENDPOINTS.PROMPTS.DELETE.replace(':id', promptId), { data: requestData })

    if (response.data.code !== 0) {
      throw new Error(response.data.msg || '删除提示词失败')
    }

    return response.data
  }

  /**
   * 生成随机键
   * @returns 随机字符串
   */
  private static generateRandomKey(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    let result = ''
    for (let i = 0; i < 21; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    return result
  }

  /**
   * 将前端数据转换为API格式的草稿数据
   * @param editorData 编辑器数据
   * @returns 转换后的草稿请求数据
   */
  private static async transformToApiDraftFormat(editorData: {
    promptMessages: Array<{
      id: string
      role: 'system' | 'user' | 'placeholder' | 'assistant'
      content: string
      placeholderName?: string
    }>
    parameters: Array<{
      name: string
      value: string
      type?: 'text' | 'placeholder'
      dataType?: string
      messages?: Array<{
        id: string
        role: 'system' | 'user' | 'assistant'
        content: string
      }>
    }>
    modelConfig: {
      model: string
      temperature: number
      maxTokens: number
      model_from?: string
      [key: string]: any // 支持动态参数
    }
    selectedModel?: any // 选中的模型信息
    templateEngine: 'normal' | 'jinja2'
    toolsEnabled: boolean
    debugMode?: boolean // 单步调试模式
    tools: Array<{
      id: string
      name: string
      description: string
      defaultValue?: string
      parametersJsonSchema?: string // 完整的 JSON Schema 字符串
      parametersMode?: 'visual' | 'json' // 参数模式：visual（可视化）或 json（JSON配置）
      parameters: Array<{
        name: string
        type: string
        description: string
        required: boolean
        enum?: string[] // 枚举值
      }>
    }>
    spaceId: string
  }): Promise<SaveDraftRequest> {
    // 转换messages
    const messages = editorData.promptMessages.map(msg => ({
      content: msg.content,
      role: msg.role,
      key: this.generateRandomKey(),
    }))

    // 转换variable_defs
    const variable_defs = editorData.parameters.map(param => {
      // 获取变量类型，统一转换为小写
      let variableType = 'string' // 默认类型

      if (param.type === 'placeholder') {
        variableType = 'placeholder'
      } else if (param.dataType) {
        // 使用参数的dataType，转换为小写
        variableType = param.dataType.toLowerCase()
      }

      return {
        key: param.name, // 变量名称
        type: variableType, // 变量类型，统一小写
        desc: '', // 变量描述，统一置为空
      }
    })

    // 转换工具配置
    const tools = editorData.tools.map(tool => {
      let parameters: string = ''

      // 优先使用完整的 JSON Schema（如果存在）
      const toolWithSchema = tool as any

      if (toolWithSchema.parametersJsonSchema && toolWithSchema.parametersJsonSchema.trim()) {
        try {
          // 验证 JSON Schema 是否有效
          JSON.parse(toolWithSchema.parametersJsonSchema)
          // 如果解析成功，直接使用（已经是字符串格式，直接返回）
          parameters = toolWithSchema.parametersJsonSchema
        } catch (error) {
          console.error(`解析工具 ${tool.name} 的 JSON Schema 失败:`, error)
          // 解析失败，回退到从 parameters 构建
        }
      }

      // 如果没有 JSON Schema 或解析失败，使用简单的参数数组构建
      if (!parameters) {
        const properties: any = {}
        const required: string[] = []

        tool.parameters.forEach(param => {
          const paramWithEnum = param as any
          const paramSchema: any = {
            type: param.type.toLowerCase(), // 转换为小写
            description: param.description,
          }

          // 如果有枚举值，添加 enum 属性
          if (paramWithEnum.enum && paramWithEnum.enum.length > 0) {
            paramSchema.enum = paramWithEnum.enum
          }

          properties[param.name] = paramSchema

          if (param.required) {
            required.push(param.name)
          }
        })

        // 构建符合新格式的 parameters 对象，然后序列化为字符串
        const parametersObj = {
          type: 'object' as const,
          properties,
          required,
          additionalProperties: false,
        }
        parameters = JSON.stringify(parametersObj)
      }

      // 获取参数模式，默认为 visual
      const parametersMode = (toolWithSchema.parametersMode || 'visual') as 'visual' | 'json'

      const apiTool = {
        type: 'function' as const,
        function: {
          name: tool.name,
          description: tool.description,
          parameters, // 字符串格式
          parameters_mode: parametersMode, // 参数模式
        },
      }

      return apiTool
    })

    // 构建模型配置
    const modelConfig: any = {
      models_name: editorData.modelConfig.model || '',
      models_id: editorData.modelConfig.model && editorData.modelConfig.model.trim() !== '' ? editorData.modelConfig.model : null,
      temperature: editorData.modelConfig.temperature,
      max_tokens: editorData.modelConfig.maxTokens,
    }

    // 如果有选中的模型，获取模型详情并填充完整信息
    if (editorData.selectedModel) {
      const model = editorData.selectedModel
      modelConfig.models_name = model.openModel.name
      modelConfig.models_id = model.openModel.model_id && model.openModel.model_id.trim() !== '' ? model.openModel.model_id : null
      modelConfig.model_from = model.model_from

      // 填充所有模型参数的当前值
      if (model.openModel.param_config?.param_schemas) {
        model.openModel.param_config.param_schemas.forEach((schema: any) => {
          const currentValue = editorData.modelConfig[schema.name]
          if (currentValue !== undefined) {
            modelConfig[schema.name] = currentValue
          }
        })
      }
    } else if (editorData.modelConfig.model) {
      // 如果没有selectedModel但有models_id，尝试获取模型详情
      try {
        const modelFrom = editorData.modelConfig.model_from
        const model = await PromptModelService.getModelDetail(editorData.modelConfig.model, modelFrom)
        modelConfig.models_name = model.openModel.name
        modelConfig.models_id = model.openModel.model_id && model.openModel.model_id.trim() !== '' ? model.openModel.model_id : null
        modelConfig.model_from = model.model_from

        // 填充所有模型参数的当前值
        if (model.openModel.param_config?.param_schemas) {
          model.openModel.param_config.param_schemas.forEach((schema: any) => {
            const currentValue = editorData.modelConfig[schema.name]
            if (currentValue !== undefined) {
              modelConfig[schema.name] = currentValue
            }
          })
        }
      } catch (error) {
        console.warn('获取模型详情失败，使用基本配置:', error)
      }
    }

    const currentTime = Date.now().toString()

    return {
      prompt_draft: {
        detail: {
          prompt_template: {
            template_type: editorData.templateEngine,
            messages,
            variable_defs,
          },
          prompt_model_config: modelConfig,
          tool_call_config: {
            tool_choice: editorData.toolsEnabled ? 'auto' : 'none',
            debug_mode: editorData.debugMode || false,
          },
          tools,
        },
        draft_info: {
          created_at: currentTime,
          is_modified: true,
          updated_at: currentTime,
          space_id: editorData.spaceId,
          base_version: '', // 暂时为空
        },
      },
    }
  }

  /**
   * 保存草稿
   * @param promptId 提示词ID
   * @param workspaceId 工作空间ID（放在请求体 workspace_id）
   * @param editorData 编辑器数据
   * @returns 保存草稿响应
   */
  static async saveDraft(promptId: string, workspaceId: string, editorData: any): Promise<SaveDraftResponse> {
    try {
      const requestData = await this.transformToApiDraftFormat({
        ...editorData,
        spaceId: workspaceId,
      })

      const url = API_ENDPOINTS.PROMPTS.SAVE_DRAFT.replace(':id', promptId)
      const response = await getApiClient().post<SaveDraftResponse>(url, requestData)

      if (response.data.code !== 0) {
        throw new Error(response.data.msg || '保存草稿失败')
      }

      return response.data
    } catch (error) {
      console.error('saveDraft 方法执行失败:', error)
      throw error
    }
  }

  /**
   * 提交版本
   * @param promptId 提示词ID
   * @param workspaceId 工作空间ID
   * @param data 提交数据
   * @returns 提交版本响应
   */
  static async commitVersion(promptId: string, workspaceId: string, data: CommitVersionRequest): Promise<CommitVersionResponse> {
    const url = API_ENDPOINTS.PROMPTS.COMMIT_DRAFT.replace(':id', promptId) + `?workspace_id=${workspaceId}`
    const response = await getApiClient().post<CommitVersionResponse>(url, data)

    if (response.data.code !== 0) {
      throw new Error(response.data.msg || '提交版本失败')
    }

    return response.data
  }

  /**
   * 还原为指定版本
   * @param promptId 提示词ID
   * @param workspaceId 工作空间ID
   * @param data 还原数据
   * @returns 还原响应
   */
  static async revertToVersion(promptId: string, workspaceId: string, data: RevertToVersionRequest): Promise<RevertToVersionResponse> {
    try {
      const url = API_ENDPOINTS.PROMPTS.REVERT_FROM_COMMIT.replace(':id', promptId) + `?workspace_id=${workspaceId}`
      const response = await getApiClient().post<RevertToVersionResponse>(url, data)

      if (response.data.code !== 0) {
        throw new Error(response.data.msg || '还原版本失败')
      }

      return response.data
    } catch (error) {
      console.error('还原版本失败:', error)
      throw error
    }
  }

  /**
   * 获取版本列表
   * @param promptId 提示词ID
   * @param workspaceId 工作空间ID
   * @param params 查询参数
   * @returns 版本列表响应
   */
  static async getVersionList(promptId: string, workspaceId: string, params?: GetVersionListRequest): Promise<GetVersionListResponse> {
    const queryParams = { ...params, workspace_id: workspaceId }
    const response = await getApiClient().get<GetVersionListResponse>(API_ENDPOINTS.PROMPTS.LIST_COMMITS.replace(':id', promptId), { params: queryParams })

    if (response.data.code !== 0) {
      throw new Error(response.data.msg || '获取版本列表失败')
    }

    return response.data
  }

  /**
   * 克隆提示词
   * @param promptId 提示词ID
   * @param data 克隆数据
   * @returns 克隆响应
   */
  static async clonePrompt(promptId: string, data: ClonePromptRequest): Promise<ClonePromptResponse> {
    try {
      const response = await getApiClient().post<ClonePromptResponse>(API_ENDPOINTS.PROMPTS.CLONE.replace(':id', promptId), data)

      if (response.data.code !== 0) {
        throw new Error(response.data.msg || '克隆提示词失败')
      }

      return response.data
    } catch (error) {
      console.error('❌ 克隆提示词失败:', error)
      throw error
    }
  }

  /**
   * 保存调试上下文
   * @param request 保存请求
   * @returns 保存响应
   */
  static async saveDebugContext(request: SaveDebugContextRequest): Promise<any> {
    try {
      const path = API_ENDPOINTS.PROMPTS.SAVE_DEBUG_CONTEXT.replace(':id', request.prompt_id)
      const response = await getApiClient().post(path, request)
      return response.data
    } catch (error) {
      console.error('❌ 保存调试上下文失败:', error)
      throw error
    }
  }

  /**
   * 获取调试上下文
   * @param promptId 提示词ID
   * @param workspaceId 工作空间ID
   * @returns 调试上下文响应
   */
  static async getDebugContext(promptId: string, workspaceId: string): Promise<GetDebugContextResponse> {
    try {
      const path = API_ENDPOINTS.PROMPTS.GET_DEBUG_CONTEXT.replace(':id', promptId) + `?workspace_id=${workspaceId}`
      const response = await getApiClient().get<GetDebugContextResponse>(path)
      return response.data
    } catch (error) {
      console.error('❌ 查询调试上下文失败:', error)
      throw error
    }
  }

  /**
   * 获取调试历史列表
   * @param params 请求参数
   * @returns Promise<DebugHistoryListResponse>
   */
  static async getDebugHistoryList(params: DebugHistoryListRequest): Promise<DebugHistoryListResponse> {
    try {
      const { prompt_id, workspace_id, page_size, page_token } = params

      // 构建相对路径（apiClient会自动添加baseURL）
      const endpoint = API_ENDPOINTS.PROMPTS.DEBUG_HISTORY_LIST.replace(':id', prompt_id)

      // 构建查询参数
      const queryParams = new URLSearchParams()
      queryParams.append('workspace_id', workspace_id)
      if (page_size) {
        queryParams.append('page_size', page_size.toString())
      }
      if (page_token) {
        queryParams.append('page_token', page_token)
      }

      const url = `${endpoint}?${queryParams.toString()}`

      const response = await getApiClient().get<DebugHistoryListResponse>(url)
      return response.data
    } catch (error) {
      console.error('获取调试历史列表失败:', error)
      throw error
    }
  }

  /**
   * 调试流式请求
   * @param promptId 提示词ID
   * @param data 调试请求数据
   * @param workspaceId 工作空间ID（workspace_id）
   * @param onMessage 消息回调
   * @param onError 错误回调
   * @param onComplete 完成回调
   * @param abortController 可选的 AbortController（用于取消请求）
   */
  static async debugStreaming(
    promptId: string,
    data: DebugStreamingRequest,
    workspaceId: string,
    onMessage: (response: any) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void,
    abortController?: AbortController,
  ): Promise<{ cancel: () => void }> {
    try {
      // 添加时间戳防止缓存，请求体带上 space_id
      const endpoint = API_ENDPOINTS.PROMPTS.DEBUG_STREAMING.replace(':id', promptId)
      const url = `${endpoint}?_t=${Date.now()}&_r=${Math.random()}`
      const requestData = { ...data, workspace_id: workspaceId }

      let messageCount = 0 // 用于跟踪已处理的消息数量
      let isCancelled = false // 取消标志
      const pendingTimeouts: NodeJS.Timeout[] = [] // 跟踪所有pending的timeout
      let currentEventType: string | null = null // 当前SSE事件类型

      // 创建内部的 AbortController（如果外部没有提供）
      const internalAbortController = abortController || new AbortController()

      // 自定义解析函数，处理 SSE 格式
      const parseData = (line: string): any | null => {
        const trimmedLine = line.trim()
        if (!trimmedLine) {
          return null
        }

        // 处理 SSE 事件类型
        if (trimmedLine.startsWith('event:')) {
          currentEventType = trimmedLine.substring('event:'.length).trim() || null
          return null // 事件类型行不返回数据
        }

        // 处理 SSE 数据行
        let jsonData = ''
        const dataPrefix = 'data:'

        if (trimmedLine.startsWith(dataPrefix)) {
          jsonData = trimmedLine.substring(dataPrefix.length).trimStart()
        } else if (trimmedLine.startsWith('{') || trimmedLine.startsWith('[')) {
          // 兼容非SSE纯JSON格式
          jsonData = trimmedLine
        } else {
          // 忽略非 data: 前缀的 SSE 元信息行（如 id: 等）
          return null
        }

        // 尝试解析JSON数据
        const normalizedJsonData = jsonData.trim()
        if (!normalizedJsonData) {
          return null
        }

        try {
          const parsedData = JSON.parse(normalizedJsonData)
          const eventType = currentEventType
          currentEventType = null

          // 如果是错误事件或错误载荷，直接调用错误回调
          if (
            eventType === 'error' ||
            (parsedData &&
              typeof parsedData === 'object' &&
              'code' in parsedData &&
              typeof (parsedData as { code?: unknown }).code === 'number' &&
              (parsedData as { code: number }).code >= 400)
          ) {
            if (onError) {
              const message =
                (parsedData as { msg?: string; message?: string }).msg || (parsedData as { msg?: string; message?: string }).message || normalizedJsonData
              onError(new Error(message))
            }
            return null
          }

          return parsedData
        } catch (e) {
          console.error('❌ 解析调试数据失败:', {
            line: trimmedLine,
            error: e,
            messageCount: messageCount,
          })

          // 即使解析失败，也返回一个错误格式的数据对象
          return {
            delta: { content: trimmedLine },
            debug_id: `parse_error_${messageCount}`,
            debug_trace_key: '',
          }
        }
      }

      // 处理数据的回调，添加延迟逻辑
      const handleData = (parsedData: any) => {
        // 检查是否已取消（包括 AbortController 的状态）- 在添加延迟之前就检查
        if (isCancelled || !parsedData || abortController?.signal.aborted) {
          if (abortController?.signal.aborted && !isCancelled) {
            isCancelled = true
          }
          return
        }

        const currentMessageIndex = messageCount
        messageCount++

        // 添加延迟来实现逐字显示效果，每条消息延迟50ms
        const delay = currentMessageIndex * 50
        const timeoutId = setTimeout(() => {
          // 再次检查是否已取消（在延迟期间可能被取消）
          if (!isCancelled && !abortController?.signal.aborted) {
            try {
              onMessage(parsedData)
            } catch (callbackError) {
              console.error('回调函数执行失败:', callbackError)
            }
          }
          // 从pending列表中移除已完成的timeout
          const index = pendingTimeouts.indexOf(timeoutId)
          if (index > -1) {
            pendingTimeouts.splice(index, 1)
          }
        }, delay)

        // 添加到pending列表
        pendingTimeouts.push(timeoutId)
      }

      // 处理完成的回调
      const handleComplete = () => {
        // 如果已取消，不处理完成回调
        if (isCancelled || abortController?.signal.aborted) {
          // 清理所有剩余的timeout
          pendingTimeouts.forEach(timeoutId => {
            clearTimeout(timeoutId)
          })
          pendingTimeouts.length = 0
          return
        }

        // 等待所有延迟的消息都发送完成
        const maxDelay = Math.max(0, (messageCount - 1) * 50)
        setTimeout(() => {
          // 再次检查是否已取消
          if (isCancelled || abortController?.signal.aborted) {
            return
          }

          // 清理所有剩余的timeout
          pendingTimeouts.forEach(timeoutId => {
            clearTimeout(timeoutId)
          })
          pendingTimeouts.length = 0

          if (onComplete) onComplete()
        }, maxDelay + 100) // 额外100ms缓冲时间
      }

      // 处理错误的回调
      const handleError = (error: string) => {
        console.error('❌ 流式请求错误:', error)
        if (!isCancelled && onError) {
          onError(new Error(error))
        }
      }

      // 返回取消函数（立即返回，不等待流式请求完成）
      const cancelFunction = {
        cancel: () => {
          isCancelled = true

          // 取消 AbortController
          if (!internalAbortController.signal.aborted) {
            internalAbortController.abort()
          }

          // 清理所有pending的timeout
          pendingTimeouts.forEach(timeoutId => {
            clearTimeout(timeoutId)
          })
          pendingTimeouts.length = 0
        },
      }

      // 在后台异步执行流式请求（不等待完成），stream 内部会自动带 Authorization
      stream(url, requestData, {
        onData: handleData,
        onError: handleError,
        onComplete: handleComplete,
        parseData: parseData,
        abortController: internalAbortController,
      })
        .catch(error => {
          // 处理流式请求启动失败的情况
          console.error('❌ 流式请求启动失败:', error)
          if (!isCancelled && onError) {
            onError(error instanceof Error ? error : new Error('调试流式请求失败'))
          }
        })

      return cancelFunction
    } catch (error) {
      console.error('❌ 调试流式请求初始化失败:', error)
      if (onError) {
        onError(error instanceof Error ? error : new Error('调试流式请求失败'))
      }
      return {
        cancel: () => {
          // 空的取消函数
        },
      }
    }
  }
}
