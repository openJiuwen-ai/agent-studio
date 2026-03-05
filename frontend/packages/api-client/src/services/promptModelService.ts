import { API_ENDPOINTS } from '../config'
import { getApiClient } from '../utils/apiClientFactory'
import { GetModelsListRequest, GetModelsListResponse, GetModelDetailResponse, GetModelsListParams, Model, ParamSchema } from '../types/promptModelTypes'

/**
 * 提示词模型管理服务类
 * 提供模型列表查询、详情获取、参数处理等功能
 */
export class PromptModelService {
  /**
   * 获取模型列表
   * @param params 查询参数
   * @returns 模型列表响应
   */
  static async getModelsList(params?: GetModelsListParams): Promise<GetModelsListResponse> {
    const requestData: GetModelsListRequest = {
      workspace_id: params?.workspaceId || '', // 应该从组件传入
      scenario: params?.scenario || 'prompt_debug',
      page_size: params?.pageSize || 100,
      page_token: params?.pageToken || '0',
    }

    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<GetModelsListResponse>(API_ENDPOINTS.PROMPT_MODELS.LIST, requestData)

      const data = response.data

      if (data.code !== 0) {
        throw new Error(data.msg || '获取模型列表失败')
      }

      return data
    } catch (error) {
      console.error('获取模型列表失败:', error)
      throw error
    }
  }

  /**
   * 根据模型ID获取模型详情
   * @param modelId 模型ID
   * @param modelFrom 模型来源
   * @param workspaceId 工作空间ID
   * @returns 模型详情响应
   */
  static async getModelDetail(modelId: string, modelFrom?: string, workspaceId?: string): Promise<Model> {
    const url = API_ENDPOINTS.PROMPT_MODELS.DETAIL.replace(':modelId', modelId)

    try {
      const apiClient = getApiClient()
      const requestData = {
        model_from: modelFrom || '',
        workspace_id: workspaceId || '',
      }
      const response = await apiClient.post<GetModelDetailResponse>(url, requestData)

      const data = response.data

      if (data.code !== 0) {
        throw new Error(data.msg || '获取模型详情失败')
      }

      return data.model
    } catch (error) {
      console.error('获取模型详情失败:', error)
      throw error
    }
  }

  /**
   * 按系列分组模型
   * @param models 模型列表
   * @returns 按系列分组的模型Map
   */
  static groupModelsBySeries(models: Model[]): Map<string, Model[]> {
    const groupedModels = new Map<string, Model[]>()

    models.forEach(model => {
      const seriesKey = `${model.model_from}|${model.series.name}|由${model.series.vendor}提供`

      if (!groupedModels.has(seriesKey)) {
        groupedModels.set(seriesKey, [])
      }

      groupedModels.get(seriesKey)!.push(model)
    })

    return groupedModels
  }

  /**
   * 获取模型的默认参数配置
   * @param model 模型对象
   * @returns 默认参数配置
   */
  static getModelDefaultParams(model: Model): Record<string, any> {
    const defaultParams: Record<string, any> = {}

    model.openModel.param_config.param_schemas.forEach(schema => {
      let defaultValue: any = schema.default_val

      // 根据类型转换默认值
      switch (schema.type) {
        case 'float':
          defaultValue = parseFloat(schema.default_val || '0')
          break
        case 'int':
          defaultValue = parseInt(schema.default_val || '0')
          break
        case 'boolean':
          defaultValue = schema.default_val === 'true'
          break
        default:
          defaultValue = schema.default_val || ''
      }

      defaultParams[schema.name] = defaultValue
    })

    return defaultParams
  }

  /**
   * 验证参数值是否在有效范围内
   * @param schema 参数配置
   * @param value 参数值
   * @returns 是否有效
   */
  static validateParamValue(schema: ParamSchema, value: any): boolean {
    if (schema.type === 'float' || schema.type === 'int') {
      const numValue = typeof value === 'number' ? value : parseFloat(value)

      if (isNaN(numValue)) {
        return false
      }

      if (schema.min !== undefined && numValue < parseFloat(schema.min)) {
        return false
      }

      if (schema.max !== undefined && numValue > parseFloat(schema.max)) {
        return false
      }
    }

    return true
  }
}
