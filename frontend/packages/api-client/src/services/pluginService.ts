import { getApiClient, getToken } from '../utils/apiClientFactory'
import { API_ENDPOINTS, API_CONFIG } from '../config'
import {
  PluginCreateRequest,
  PluginCreateResponse,
  PluginGetRequest,
  PluginGetResponse,
  PluginDeleteRequest,
  PluginDeleteResponse,
  PluginUpdateRequest,
  PluginUpdateResponse,
  PluginListRequest,
  PluginListResponse,
  PluginCreateApiRequest,
  PluginCreateApiResponse,
  PluginUpdateApiRequest,
  PluginUpdateApiResponse,
  PluginDeleteApiRequest,
  PluginDeleteApiResponse,
  PluginGetApiRequest,
  PluginGetApiResponse,
  PluginListApiRequest,
  PluginListApiResponse,
  PluginExecuteRequest,
  PluginExecutionEvent,
  PluginExecutionEventHandler,
  PluginCreateCodeRequest,
  PluginCreateCodeResponse,
  PluginUpdateCodeRequest,
  PluginUpdateCodeResponse,
  PluginDeleteCodeRequest,
  PluginDeleteCodeResponse,
  PluginGetCodeRequest,
  PluginGetCodeResponse,
  PluginListCodeRequest,
  PluginListCodeResponse,
  PluginPublishRequest,
  PluginPublishResponse,
  PluginPublishGetRequest,
  PluginPublishGetResponse,
  PluginPublishListRequest,
  PluginPublishListResponse,
  PluginPublishDeleteRequest,
  PluginPublishDeleteResponse,
  PluginGetMarketRequest,
  PluginGetMarketResponse,
} from '../types'

// 插件服务
export class PluginService {
  // 创建插件
  static async createPlugin(request: PluginCreateRequest): Promise<PluginCreateResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginCreateResponse>(API_ENDPOINTS.PLUGINS.CREATE, request)
    return response.data
  }

  // 获取插件信息
  static async getPlugin(request: PluginGetRequest): Promise<PluginGetResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginGetResponse>(API_ENDPOINTS.PLUGINS.GET, request)
    return response.data
  }

  // 更新插件
  static async updatePlugin(request: PluginUpdateRequest): Promise<PluginUpdateResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginUpdateResponse>(API_ENDPOINTS.PLUGINS.UPDATE, request)
    return response.data
  }

  // 删除插件
  static async deletePlugin(request: PluginDeleteRequest): Promise<PluginDeleteResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginDeleteResponse>(API_ENDPOINTS.PLUGINS.DELETE, request)
    return response.data
  }

  // 获取插件列表
  static async getPluginList(request: PluginListRequest): Promise<PluginListResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginListResponse>(API_ENDPOINTS.PLUGINS.LIST, request)
    return response.data
  }

  // 创建插件 API
  static async createPluginApi(request: PluginCreateApiRequest): Promise<PluginCreateApiResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginCreateApiResponse>(API_ENDPOINTS.PLUGINS.CREATE_API, request)
    return response.data
  }

  // 更新插件 API
  static async updatePluginApi(request: PluginUpdateApiRequest): Promise<PluginUpdateApiResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginUpdateApiResponse>(API_ENDPOINTS.PLUGINS.UPDATE_API, request)
    return response.data
  }

  // 删除插件 API
  static async deletePluginApi(request: PluginDeleteApiRequest): Promise<PluginDeleteApiResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginDeleteApiResponse>(API_ENDPOINTS.PLUGINS.DELETE_API, request)
    return response.data
  }

  // 获取插件 API
  static async getPluginApi(request: PluginGetApiRequest): Promise<PluginGetApiResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginGetApiResponse>(API_ENDPOINTS.PLUGINS.GET_API, request)
    return response.data
  }

  // 获取插件 API 列表
  static async getPluginApiList(request: PluginListApiRequest): Promise<PluginListApiResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginListApiResponse>(API_ENDPOINTS.PLUGINS.LIST_API, request)
    return response.data
  }

  // 插件 Code 相关服务方法

  // 创建插件 Code
  static async createPluginCode(request: PluginCreateCodeRequest): Promise<PluginCreateCodeResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginCreateCodeResponse>(API_ENDPOINTS.PLUGINS.CREATE_CODE, request)
    return response.data
  }

  // 更新插件 Code
  static async updatePluginCode(request: PluginUpdateCodeRequest): Promise<PluginUpdateCodeResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginUpdateCodeResponse>(API_ENDPOINTS.PLUGINS.UPDATE_CODE, request)
    return response.data
  }

  // 删除插件 Code
  static async deletePluginCode(request: PluginDeleteCodeRequest): Promise<PluginDeleteCodeResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginDeleteCodeResponse>(API_ENDPOINTS.PLUGINS.DELETE_CODE, request)
    return response.data
  }

  // 获取插件 Code
  static async getPluginCode(request: PluginGetCodeRequest): Promise<PluginGetCodeResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginGetCodeResponse>(API_ENDPOINTS.PLUGINS.GET_CODE, request)
    return response.data
  }

  // 获取插件 Code 列表
  static async getPluginCodeList(request: PluginListCodeRequest): Promise<PluginListCodeResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginListCodeResponse>(API_ENDPOINTS.PLUGINS.LIST_CODE, request)
    return response.data
  }

  // Plugin Publish 相关服务方法

  // 发布插件
  static async publishPlugin(request: PluginPublishRequest): Promise<PluginPublishResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginPublishResponse>(API_ENDPOINTS.PLUGINS.PUBLISH, request)
    return response.data
  }

  // 获取插件发布信息
  static async getPluginPublish(request: PluginPublishGetRequest): Promise<PluginPublishGetResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginPublishGetResponse>(API_ENDPOINTS.PLUGINS.PUBLISH_GET, request)
    return response.data
  }

  // 获取插件发布列表
  static async getPluginPublishList(request: PluginPublishListRequest): Promise<PluginPublishListResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginPublishListResponse>(API_ENDPOINTS.PLUGINS.PUBLISH_LIST, request)
    return response.data
  }

  // 获取插件市场数据
  static async getPluginMarket(request: PluginGetMarketRequest): Promise<PluginGetMarketResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginGetMarketResponse>(API_ENDPOINTS.PLUGINS.GET_MARKET, request)
    return response.data
  }

  // 删除插件发布
  static async deletePluginPublish(request: PluginPublishDeleteRequest): Promise<PluginPublishDeleteResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<PluginPublishDeleteResponse>(API_ENDPOINTS.PLUGINS.PUBLISH_DELETE, request)
    return response.data
  }

  // 执行插件 (流式响应)
  static async executePlugin(
    request: PluginExecuteRequest,
    onEvent: PluginExecutionEventHandler,
    onError?: (error: Error) => void,
    onComplete?: (buffer: string) => void,
    timeout?: number,
  ): Promise<() => void> {
    const apiClient = getApiClient()
    const baseURL = apiClient.defaults.baseURL || ''

    try {
      // 创建 AbortController 用于请求取消
      const controller = new AbortController()
      // 移除超时限制，允许插件长时间运行

      // 使用 fetch POST 请求进行 SSE 流式响应
      const response = await fetch(`${baseURL}${API_ENDPOINTS.EXECUTION.PLUGIN}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          'Cache-Control': 'no-cache',
          Authorization: `Bearer ${getToken() || ''}`,
        },
        body: JSON.stringify(request),
        credentials: 'include',
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      if (!response.body) {
        throw new Error('Response body is null')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const processStream = async () => {
        try {
          let isStreaming = true
          while (isStreaming) {
            const { done, value } = await reader.read()

            if (done) {
              console.log(`Plugin execution stream completed: ${buffer}`)
              if (onComplete) onComplete(buffer)
              isStreaming = false
              break
            }

            // 解码数据并添加到缓冲区
            buffer += decoder.decode(value, { stream: true })

            // 处理完整的行
            const lines = buffer.split('\n')
            buffer = lines.pop() || '' // 保留最后一个不完整的行

            for (const line of lines) {
              if (line.trim() === '') continue

              // 解析 SSE 消息
              if (line.startsWith('data: ')) {
                const dataStr = line.substring(6) // 移除 'data: ' 前缀

                try {
                  // 解析完整的 SSE 消息
                  const sseMessage = JSON.parse(dataStr)

                  // 检查 code 是否为 200，只有 200 才继续解析 data 字段
                  if (sseMessage.code !== 200) {
                    // code 不为 200，表示执行错误
                    const errorMessage = `错误 ${sseMessage.code}: ${sseMessage.message || 'Unknown error'}`

                    // 创建错误事件
                    const errorEvent: PluginExecutionEvent = {
                      status: 'error',
                      error: errorMessage,
                      start_time: new Date().toISOString(),
                      end_time: new Date().toISOString(),
                    }
                    onEvent(errorEvent)
                    continue
                  }

                  // code 为 200，继续解析 data 字段
                  const messageData = sseMessage.data

                  if (typeof messageData === 'object' && messageData !== null) {
                    // 创建插件执行事件
                    const executionEvent: PluginExecutionEvent = {
                      id: messageData.id,
                      version: messageData.version,
                      name: messageData.name,
                      description: messageData.description,
                      status: messageData.status || 'running',
                      inputs: messageData.inputs,
                      outputs: messageData.outputs,
                      output_text: messageData.output_text || messageData.result,
                      error: messageData.error,
                      start_time: messageData.start_time,
                      end_time: messageData.end_time,
                      timestamp: messageData.timestamp,
                      parent_id: messageData.parent_id,
                      loop_index: messageData.loop_index,
                    }

                    onEvent(executionEvent)
                  }
                } catch (parseError) {
                  console.error('Failed to parse SSE message:', parseError)
                  console.error('Raw data:', dataStr)
                  if (onError) onError(parseError as Error)
                }
              }
            }
          }
        } catch (err) {
          console.error('Error processing plugin execution stream:', err)
          if (onError) onError(err as Error)
        } finally {
          reader.releaseLock()
        }
      }

      // 开始处理流
      processStream()

      // 返回关闭连接的函数
      return () => {
        clearTimeout(timeoutId)
        controller.abort()
        reader.cancel()
        if (onComplete) onComplete(buffer)
      }
    } catch (error) {
      console.error('Failed to start plugin execution:', error)
      if (onError) onError(error as Error)
      return () => {}
    }
  }
}

// 导出插件服务实例
export default PluginService
