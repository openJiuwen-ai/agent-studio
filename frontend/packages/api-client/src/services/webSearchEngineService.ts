/**
 * WebSearch Engine Service
 * 搜索引擎配置服务
 */

import { getApiClient } from '../utils/apiClientFactory'

// ==================== 类型定义 ====================

/**
 * 搜索引擎配置
 */
export interface WebSearchEngineConfig {
  web_search_engine_id: number
  search_engine_name: string
  search_url: string
  create_time: string
  extension?: Record<string, any>
  is_active?: boolean
}

/**
 * 搜索引擎列表响应
 */
export interface WebSearchEngineListResponse {
  code: number
  msg: string
  data: WebSearchEngineConfig[]
}

/**
 * 搜索引擎创建请求
 */
export interface WebSearchEngineCreateRequest {
  space_id: string
  search_engine_name: string
  search_api_key: string
  search_url: string
  extension?: Record<string, any>
  is_active?: boolean
}

/**
 * 搜索引擎创建响应
 */
export interface WebSearchEngineCreateResponse {
  code: number
  msg: string
  web_search_engine_id?: number
}

/**
 * 搜索引擎删除响应
 */
export interface WebSearchEngineDeleteResponse {
  code: number
  msg: string
}

/**
 * 搜索引擎更新请求
 */
export interface WebSearchEngineUpdateRequest {
  space_id: string
  web_search_engine_id: number
  search_engine_name: string
  search_api_key: string
  search_url: string
  extension?: Record<string, any>
  is_active?: boolean
}

/**
 * 搜索引擎更新响应
 */
export interface WebSearchEngineUpdateResponse {
  code: number
  msg: string
  web_search_engine_id?: number
}

/**
 * 搜索引擎详情响应
 */
export interface WebSearchEngineGetResponse {
  code: number
  msg: string
  search_engine_name: string
  search_url: string
  extension?: Record<string, any>
  is_active?: boolean
}

/**
 * 搜索引擎测试请求
 */
export interface WebSearchEngineTestRequest {
  query: string
}

/**
 * 搜索引擎测试响应
 */
export interface WebSearchEngineTestResponse {
  code: number
  msg: string
  search_engine_name: string
  datas: Record<string, any>[]
}

// ==================== 搜索引擎服务 ====================

/**
 * 搜索引擎配置服务
 */
export const webSearchEngineService = {
  /**
   * 获取搜索引擎列表
   * @param spaceId - 用户空间ID
   * @returns 搜索引擎列表
   */
  async listEngines(spaceId: string): Promise<WebSearchEngineConfig[]> {
    const client = getApiClient()
    const response = await client.get<WebSearchEngineListResponse>(
      `/agent/deepsearch/web_search/${spaceId}`
    )
    return response.data.data
  },

  /**
   * 创建搜索引擎配置
   * @param spaceId - 用户空间ID
   * @param engineName - 搜索引擎名称
   * @param apiKey - API密钥
   * @param url - 搜索引擎URL
   * @returns 新创建的搜索引擎ID
   */
  async createEngine(
    spaceId: string,
    engineName: string,
    apiKey: string,
    url: string
  ): Promise<number> {
    const client = getApiClient()

    const request: WebSearchEngineCreateRequest = {
      space_id: spaceId,
      search_engine_name: engineName,
      search_api_key: apiKey,
      search_url: url
    }

    const response = await client.post<WebSearchEngineCreateResponse>(
      '/agent/deepsearch/web_search',
      request
    )

    if (response.data.web_search_engine_id === undefined) {
      throw new Error(response.data.msg || '创建搜索引擎失败')
    }

    return response.data.web_search_engine_id
  },

  /**
   * 删除搜索引擎
   * @param spaceId - 用户空间ID
   * @param engineId - 搜索引擎ID
   */
  async deleteEngine(spaceId: string, engineId: number): Promise<void> {
    const client = getApiClient()
    await client.delete<WebSearchEngineDeleteResponse>(
      `/agent/deepsearch/web_search/${spaceId}/${engineId}`
    )
  },

  /**
   * 获取单个搜索引擎详情
   * @param spaceId - 用户空间ID
   * @param engineId - 搜索引擎ID
   * @returns 搜索引擎详情
   */
  async getEngine(spaceId: string, engineId: number): Promise<WebSearchEngineGetResponse> {
    const client = getApiClient()
    const response = await client.get<WebSearchEngineGetResponse>(
      `/agent/deepsearch/web_search/${spaceId}/${engineId}`
    )
    // 后端返回的数据结构
    return response.data
  },

  /**
   * 更新搜索引擎配置
   * @param spaceId - 用户空间ID
   * @param engineId - 搜索引擎ID
   * @param engineName - 搜索引擎名称
   * @param apiKey - API密钥
   * @param url - 搜索引擎URL
   */
  async updateEngine(
    spaceId: string,
    engineId: number,
    engineName: string,
    apiKey: string,
    url: string
  ): Promise<void> {
    const client = getApiClient()

    const request: WebSearchEngineUpdateRequest = {
      space_id: spaceId,
      web_search_engine_id: engineId,
      search_engine_name: engineName,
      search_api_key: apiKey,
      search_url: url
    }

    await client.put<WebSearchEngineUpdateResponse>(
      '/agent/deepsearch/web_search',
      request
    )
  },

  /**
   * 切换搜索引擎启用/禁用状态
   * @param spaceId - 用户空间ID
   * @param engineId - 搜索引擎ID
   * @param isActive - 是否启用
   */
  async toggleEngineStatus(
    spaceId: string,
    engineId: number,
    isActive: boolean
  ): Promise<void> {
    const client = getApiClient()

    const request: WebSearchEngineUpdateRequest = {
      space_id: spaceId,
      web_search_engine_id: engineId,
      is_active: isActive
    }

    await client.put<WebSearchEngineUpdateResponse>(
      '/agent/deepsearch/web_search',
      request
    )
  },

  /**
   * 测试搜索引擎
   * @param spaceId - 用户空间ID
   * @param engineId - 搜索引擎ID
   * @param query - 测试查询
   * @returns 测试结果
   */
  async testEngine(
    spaceId: string,
    engineId: number,
    query: string
  ): Promise<WebSearchEngineTestResponse> {
    const client = getApiClient()

    const request: WebSearchEngineTestRequest = {
      query
    }

    try {
      const response = await client.post<WebSearchEngineTestResponse>(
        `/agent/deepsearch/web_search/${spaceId}/${engineId}`,
        request,
        {
          // 关键：让 axios 不将 4xx/5xx 视为错误，这样就不会触发全局拦截器的 Snackbar
          validateStatus: (status) => status < 600  // 接受所有状态码
        }
      )

      // 检查响应状态码 - 接受所有 2xx 状态码为成功
      if (response.status < 200 || response.status >= 300) {
        // 业务错误（4xx/5xx），返回错误响应对象
        const errorData = response.data as any
        let errorMessage = errorData?.detail || errorData?.msg || errorData?.message || ''

        return {
          code: response.status,
          msg: errorMessage,
          search_engine_name: '',
          datas: []
        }
      }

      return response.data
    } catch (error: any) {
      // 只有真正的网络错误才会进入这里
      console.error('测试搜索引擎失败:', error)
      throw error
    }
  }
}
