import { apiUtils } from '../client'
import { getApiClient } from '../utils/apiClientFactory'
import type {
  ModelConfigResponse,
  ModelConfigCreate,
  ModelConfigUpdate,
  ModelConfigList,
  ModelTestRequest,
  ModelTestResponse,
  ModelConfigQueryParams,
  ModelApiError,
} from '../types/modelTypes'

// 前端ModelsPage.tsx使用的ModelConfig接口
export interface FrontendModelConfig {
  id: string
  name: string
  provider: string
  modelId: string
  apiKey: string
  baseUrl: string
  isActive: boolean
  maxTokens: number
  temperature: number
  topp: number
  timeout: number
  retryCount: number
  enableStreaming: boolean
  enableFunctionCalling: boolean
  usage: {
    totalRequests: number
    totalTokens: number
    successRate: number
    averageResponseTime: number
    lastUsed: string
  }
  tags: string[]
  description: string
  createdAt: string
  updatedAt: string
  isSystemModel: boolean // 是否系统预置模型
}

// 数据转换函数：后端到前端
function backendToFrontend(backend: ModelConfigResponse): FrontendModelConfig {
  return {
    id: backend.id.toString(),
    name: backend.name,
    provider: backend.provider,
    modelId: backend.model_type,
    apiKey: backend.api_key_masked || '',
    baseUrl: backend.base_url || '',
    isActive: backend.is_active,
    maxTokens: backend.parameters.max_tokens,
    temperature: backend.parameters.temperature,
    topp: backend.parameters.top_p ?? 0.9,
    timeout: backend.timeout,
    retryCount: backend.retry_count,
    enableStreaming: backend.enable_streaming,
    enableFunctionCalling: backend.enable_function_calling,
    usage: {
      totalRequests: backend.usage_stats.total_requests,
      totalTokens: backend.usage_stats.total_tokens,
      successRate: backend.usage_stats.success_rate,
      averageResponseTime: backend.usage_stats.avg_response_time,
      lastUsed: backend.usage_stats.last_used || '',
    },
    tags: backend.tags,
    description: backend.description || '',
    createdAt: backend.created_at,
    updatedAt: backend.updated_at,
    isSystemModel: backend.is_system_model ?? false,
  }
}

// 数据转换函数：前端到后端
function frontendToBackend(frontend: Partial<FrontendModelConfig>): ModelConfigCreate | ModelConfigUpdate {
  const backend: any = {
    name: frontend.name,
    provider: frontend.provider as any,
    model_type: frontend.modelId,
    base_url: frontend.baseUrl,
    is_active: frontend.isActive,
    description: frontend.description,
    tags: frontend.tags || [],
    parameters: {
      temperature: frontend.temperature ?? 0.7,
      max_tokens: frontend.maxTokens || 4000,
      top_p: frontend.topp ?? 0.9,
    },
    timeout: frontend.timeout || 3600,
    retry_count: frontend.retryCount || 3,
    enable_streaming: frontend.enableStreaming ?? true,
    enable_function_calling: frontend.enableFunctionCalling ?? false,
  }

  // Only include api_key if it's provided and not empty
  // Also exclude masked keys (containing asterisks, which are masked values from backend)
  if (frontend.apiKey && frontend.apiKey !== '') {
    const isMaskedKey = frontend.apiKey.includes('*')
    if (!isMaskedKey) {
      backend.api_key = frontend.apiKey
    }
    // If it's a masked key, don't include it in the update request to preserve the existing key
  }

  return backend
}

// 模型管理API服务
export class ModelService {
  private readonly basePath = '/models/'

  // 获取模型配置列表
  async getModelConfigs(
    params?: ModelConfigQueryParams & { spaceId?: string },
  ): Promise<{ items: FrontendModelConfig[]; total: number; page: number; size: number }> {
    try {
      // 如果没有spaceId，抛出错误
      if (!params?.spaceId) {
        throw new Error('spaceId is required to fetch models')
      }

      // 构建查询参数，排除spaceId
      const { spaceId, ...queryParams } = params || {}
      const queryString = Object.keys(queryParams).length > 0 ? `?${apiUtils.buildQueryString(queryParams)}` : ''

      const apiClient = getApiClient()
      const response = await apiClient.get<{ code: number; message: string; data: ModelConfigList }>(`${this.basePath}${spaceId}${queryString}`)
      return {
        items: response.data.data.items.map(backendToFrontend),
        total: response.data.data.total,
        page: response.data.data.page,
        size: response.data.data.size,
      }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 获取单个模型配置
  async getModelConfig(id: string, spaceId: string): Promise<FrontendModelConfig> {
    try {
      const apiClient = getApiClient()
      // 构建请求体，包含space_id
      const requestBody = { config_id: id, space_id: spaceId }
      const response = await apiClient.get<{ code: number; message: string; data: ModelConfigResponse }>(`${this.basePath}`, { params: requestBody })
      return backendToFrontend(response.data.data)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 创建模型配置
  async createModelConfig(model: Partial<FrontendModelConfig>, spaceId: string): Promise<FrontendModelConfig> {
    try {
      // 将backendModel类型断言为ModelConfigCreate以支持类型安全的space_id赋值
      const backendModel = frontendToBackend(model) as ModelConfigCreate
      // 添加space_id到请求体
      backendModel.space_id = spaceId
      const apiClient = getApiClient()
      const response = await apiClient.post<{ code: number; message: string; data: ModelConfigResponse }>(`${this.basePath}`, backendModel)
      return backendToFrontend(response.data.data)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 更新模型配置
  async updateModelConfig(id: string, model: Partial<FrontendModelConfig>, spaceId: string): Promise<FrontendModelConfig> {
    try {
      // 将backendModel类型断言为ModelConfigUpdate以支持类型安全
      const backendModel = frontendToBackend(model) as ModelConfigUpdate
      const apiClient = getApiClient()
      // 构建请求体，包含config_id和space_id
      const requestBody = { config_id: id, space_id: spaceId, ...backendModel }
      const response = await apiClient.put<{ code: number; message: string; data: ModelConfigResponse }>(this.basePath, requestBody)
      return backendToFrontend(response.data.data)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 删除模型配置
  async deleteModelConfig(id: string, spaceId: string): Promise<void> {
    try {
      const apiClient = getApiClient()
      // 构建请求体，包含config_id和space_id
      const requestBody = { config_id: id, space_id: spaceId }
      await apiClient.delete(this.basePath, { data: requestBody })
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 切换模型状态
  async toggleModelStatus(id: string, spaceId: string): Promise<FrontendModelConfig> {
    try {
      const apiClient = getApiClient()
      // 构建请求体，包含space_id
      const requestBody = { space_id: spaceId }
      const response = await apiClient.post<{ code: number; message: string; data: ModelConfigResponse }>(`${this.basePath}${id}/toggle`, requestBody)
      return backendToFrontend(response.data.data)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 测试模型
  async testModel(
    id: string,
    prompt: string,
    spaceId: string,
    parameters?: { temperature?: number; top_p?: number; max_tokens?: number }
  ): Promise<{ success: boolean; response?: string; error?: string; latency: number }> {
    try {
      const testRequest: ModelTestRequest = {
        prompt,
        parameters: parameters ? {
          temperature: parameters.temperature ?? 0.7,
          top_p: parameters.top_p ?? 0.9,
          max_tokens: parameters.max_tokens ?? 4096,
        } : undefined,
      }
      const apiClient = getApiClient()
      // 在URL中包含space_id
      const response = await apiClient.post<{ code: number; message: string; data: ModelTestResponse }>(
        `${this.basePath}${id}/test?space_id=${encodeURIComponent(spaceId)}`,
        testRequest,
      )
      return {
        success: response.data.data.success,
        response: response.data.data.response,
        error: response.data.data.error,
        latency: response.data.data.latency,
      }
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 错误处理
  private handleError(error: any): ModelApiError {
    if (error.response?.data) {
      return error.response.data
    }
    return {
      code: 500,
      message: error.message || 'Unknown error occurred',
      error: error.toString(),
    }
  }
}

// 导出单例实例
export const modelService = new ModelService()
