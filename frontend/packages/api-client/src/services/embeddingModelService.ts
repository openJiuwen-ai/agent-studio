import { apiUtils } from '../client'
import { getApiClient } from '../utils/apiClientFactory'
import type {
  EmbeddingModelConfigResponse,
  EmbeddingModelConfigCreate,
  EmbeddingModelConfigUpdate,
  EmbeddingModelConfigList,
  EmbeddingModelTestRequest,
  EmbeddingModelTestResponse,
  EmbeddingModelConfigQueryParams,
  EmbeddingModelApiError,
} from '../types/embeddingModelTypes'

// 前端使用的 Embedding 模型配置接口
export interface FrontendEmbeddingModelConfig {
  id: string
  name: string // model_name
  provider: string // 协议类型（为了与 LLM 模型兼容，使用 provider 字段名）
  protocol: string // 协议类型（原始字段）
  modelId: string // model_id
  apiKey: string // api_key_masked
  baseUrl: string // api_base
  maxBatchSize: number // max_batch_size
  isActive: boolean // is_active
  tags: string[] // 标签（前端默认为空数组）
  description: string // 描述（前端默认为空）
  createdAt: string
  updatedAt: string
  isSystemModel: boolean // 是否系统预置模型
}

// 数据转换函数：后端到前端
function backendToFrontend(backend: EmbeddingModelConfigResponse): FrontendEmbeddingModelConfig {
  return {
    id: backend.id.toString(),
    name: backend.model_name,
    provider: backend.protocol, // 使用 protocol 作为 provider
    protocol: backend.protocol,
    modelId: backend.model_id,
    apiKey: backend.api_key_masked || '',
    baseUrl: backend.api_base || '',
    maxBatchSize: backend.max_batch_size,
    isActive: backend.is_active,
    tags: [], // 后端不支持 tags，前端默认为空数组
    description: '', // 后端不支持 description，前端默认为空
    createdAt: backend.created_at,
    updatedAt: backend.updated_at,
    isSystemModel: backend.is_system_model ?? false,
  }
}

// 数据转换函数：前端到后端（创建）
function frontendToBackendCreate(frontend: Partial<FrontendEmbeddingModelConfig>, spaceId: string): EmbeddingModelConfigCreate {
  return {
    model_name: frontend.name || '',
    space_id: spaceId,
    protocol: (frontend.protocol || 'openai') as any,
    model_id: frontend.modelId || '',
    api_key: frontend.apiKey || '',
    api_base: frontend.baseUrl || '',
    max_batch_size: frontend.maxBatchSize || 8,
    is_active: frontend.isActive ?? true,
  }
}

// 数据转换函数：前端到后端（更新）
function frontendToBackendUpdate(frontend: Partial<FrontendEmbeddingModelConfig>): EmbeddingModelConfigUpdate {
  const update: EmbeddingModelConfigUpdate = {}

  if (frontend.name !== undefined) update.model_name = frontend.name
  if (frontend.protocol !== undefined) update.protocol = frontend.protocol as any
  if (frontend.modelId !== undefined) update.model_id = frontend.modelId
  if (frontend.apiKey !== undefined && frontend.apiKey !== '') update.api_key = frontend.apiKey
  if (frontend.baseUrl !== undefined) update.api_base = frontend.baseUrl
  if (frontend.maxBatchSize !== undefined) update.max_batch_size = frontend.maxBatchSize
  if (frontend.isActive !== undefined) update.is_active = frontend.isActive

  return update
}

// Embedding 模型管理 API 服务
export class EmbeddingModelService {
  private readonly basePath = '/embedding-models/'

  // 获取 Embedding 模型配置列表
  async getEmbeddingModelConfigs(
    spaceId: string,
    params?: EmbeddingModelConfigQueryParams,
  ): Promise<{ items: FrontendEmbeddingModelConfig[]; total: number; page: number; size: number }> {
    try {
      if (!spaceId) {
        throw new Error('spaceId is required to fetch embedding models')
      }

      const queryString = params && Object.keys(params).length > 0 ? `?${apiUtils.buildQueryString(params)}` : ''

      const apiClient = getApiClient()
      const response = await apiClient.get<{ code: number; message: string; data: EmbeddingModelConfigList }>(`${this.basePath}${spaceId}${queryString}`)

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

  // 获取单个 Embedding 模型配置
  async getEmbeddingModelConfig(configId: string, spaceId: string): Promise<FrontendEmbeddingModelConfig> {
    try {
      const apiClient = getApiClient()
      const requestBody = { config_id: parseInt(configId), space_id: spaceId }
      const response = await apiClient.get<{ code: number; message: string; data: EmbeddingModelConfigResponse }>(`${this.basePath}`, { params: requestBody })
      return backendToFrontend(response.data.data)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 创建 Embedding 模型配置
  async createEmbeddingModelConfig(model: Partial<FrontendEmbeddingModelConfig>, spaceId: string): Promise<FrontendEmbeddingModelConfig> {
    try {
      const backendModel = frontendToBackendCreate(model, spaceId)
      const apiClient = getApiClient()
      const response = await apiClient.post<{ code: number; message: string; data: EmbeddingModelConfigResponse }>(`${this.basePath}`, backendModel)
      return backendToFrontend(response.data.data)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 更新 Embedding 模型配置
  async updateEmbeddingModelConfig(configId: string, model: Partial<FrontendEmbeddingModelConfig>, spaceId: string): Promise<FrontendEmbeddingModelConfig> {
    try {
      const backendModel = frontendToBackendUpdate(model)
      const apiClient = getApiClient()
      const requestBody = {
        config_id: parseInt(configId),
        space_id: spaceId,
        ...backendModel,
      }
      const response = await apiClient.post<{ code: number; message: string; data: EmbeddingModelConfigResponse }>(`${this.basePath}update`, requestBody)
      return backendToFrontend(response.data.data)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 删除 Embedding 模型配置
  async deleteEmbeddingModelConfig(configId: string, spaceId: string): Promise<void> {
    try {
      const apiClient = getApiClient()
      const requestBody = { config_id: parseInt(configId), space_id: spaceId }
      await apiClient.delete(this.basePath, { data: requestBody })
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 切换 Embedding 模型状态
  async toggleEmbeddingModelStatus(configId: string, spaceId: string): Promise<FrontendEmbeddingModelConfig> {
    try {
      const apiClient = getApiClient()
      const requestBody = { config_id: parseInt(configId), space_id: spaceId }
      const response = await apiClient.post<{ code: number; message: string; data: EmbeddingModelConfigResponse }>(`${this.basePath}toggle`, requestBody)
      return backendToFrontend(response.data.data)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 测试 Embedding 模型
  async testEmbeddingModel(configId: string, testRequest: EmbeddingModelTestRequest): Promise<EmbeddingModelTestResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<{ code: number; message: string; data: EmbeddingModelTestResponse }>(
        `${this.basePath}${configId}/test`,
        testRequest,
      )
      return response.data.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  // 错误处理
  private handleError(error: any): EmbeddingModelApiError {
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
export const embeddingModelService = new EmbeddingModelService()

