import { getApiClient } from '../utils/apiClientFactory'
import { API_ENDPOINTS } from '../config'
import {
  CreateAgentRequest,
  CreateAgentResponse,
  AgentListRequest,
  AgentListResponse,
  AgentDetailRequest,
  AgentDetailResponse,
  SaveAgentRequest,
  SaveAgentResponse,
  DeleteAgentRequest,
  DeleteAgentResponse,
  UpdateAgentRequest,
  UpdateAgentResponse,
  CopyAgentRequest,
  CopyAgentResponse,
  AgentSearchRequest,
  AgentSearchResponse,
  AgentPublishRequest,
  AgentPublishResponse,
  AgentVersionListRequest,
  AgentVersionListResponse,
  AgentExecutionDebugEnterRequest,
  AgentExecutionDebugListResponse,
  AgentExecutionDebugDetailResponse,
} from '../types'

// 智能体服务
export class AgentService {
  // 获取智能体列表
  static async getAgents(request: AgentListRequest): Promise<AgentListResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<AgentListResponse>(API_ENDPOINTS.AGENTS.LIST, request)
      return response.data
    } catch (error) {
      // API调用失败时抛出错误，不再返回mock响应
      console.error('获取智能体列表API调用失败:', error)
      throw error
    }
  }

  // 创建智能体
  static async createAgent(request: CreateAgentRequest): Promise<CreateAgentResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<CreateAgentResponse>(API_ENDPOINTS.AGENTS.CREATE, request)
    return response.data
  }

  // 获取智能体详情
  static async getAgentDetail(request: AgentDetailRequest): Promise<AgentDetailResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<AgentDetailResponse>(API_ENDPOINTS.AGENTS.DETAIL, request)
      return response.data
    } catch (error) {
      // API调用失败时抛出错误，不再返回mock响应
      console.error('获取智能体详情API调用失败:', error)
      throw error
    }
  }

  // 更新智能体
  static async updateAgent(request: UpdateAgentRequest): Promise<UpdateAgentResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<UpdateAgentResponse>(API_ENDPOINTS.AGENTS.UPDATE, request)
    return response.data
  }

  // 删除智能体
  static async deleteAgent(request: DeleteAgentRequest): Promise<DeleteAgentResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<DeleteAgentResponse>(API_ENDPOINTS.AGENTS.DELETE, request)
      // 确保返回的数据符合DeleteAgentResponse格式
      return response.data
    } catch (error) {
      // API调用失败时抛出错误
      console.error('删除智能体API调用失败:', error)
      throw error
    }
  }

  // 执行智能体
  static async executeAgent(request: any): Promise<any> {
    const apiClient = getApiClient()
    const response = await apiClient.post<any>(API_ENDPOINTS.AGENTS.EXECUTE, request)
    return response.data
  }

  // 进入智能体执行日志调试
  static async enterExecutionLogsDebug(request: AgentExecutionDebugEnterRequest): Promise<AgentExecutionDebugListResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<AgentExecutionDebugListResponse>(API_ENDPOINTS.EXECUTION.GET_TRACE_SUMMARY_LIST, request)
    return response.data
  }

  // 获取执行日志详情
  static async getExecutionLogDetail(request: {
    space_id: string
    business_type: string
    business_id: string
    business_version?: string
    trace_id: string
  }): Promise<AgentExecutionDebugDetailResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<AgentExecutionDebugDetailResponse>(API_ENDPOINTS.EXECUTION.GET_TRACE_SUMMARY_BY_TRACE_ID, request)
    return response.data
  }

  // 保存智能体
  static async saveAgent(request: SaveAgentRequest): Promise<SaveAgentResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<SaveAgentResponse>(API_ENDPOINTS.AGENTS.SAVE, request)
      return response.data
    } catch (error) {
      // API调用失败时抛出错误，不再返回mock响应
      console.error('保存智能体API调用失败:', error)
      throw error
    }
  }

  // 复制智能体
  static async copyAgent(request: CopyAgentRequest): Promise<CopyAgentResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<CopyAgentResponse>(API_ENDPOINTS.AGENTS.COPY, request)
      return response.data
    } catch (error) {
      console.error('复制智能体API调用失败:', error)
      throw error
    }
  }

  // 搜索智能体
  static async searchAgents(request: AgentSearchRequest): Promise<AgentSearchResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<AgentSearchResponse>(API_ENDPOINTS.AGENTS.SEARCH, request)
      return response.data
    } catch (error) {
      console.error('搜索智能体API调用失败:', error)
      throw error
    }
  }

  // 发布智能体
  static async publishAgent(request: AgentPublishRequest): Promise<AgentPublishResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<AgentPublishResponse>(API_ENDPOINTS.AGENTS.PUBLISH, request)
      return response.data
    } catch (error) {
      console.error('发布智能体API调用失败:', error)
      throw error
    }
  }

  // 导出智能体
  static async exportAgent(request: {
    space_id: string
    agent_id: string
    agent_version?: string
  }): Promise<any> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post(API_ENDPOINTS.AGENTS.EXPORT, request, {
        responseType: 'blob', // 支持二进制文件下载
      })

      // 检查响应类型
      const contentType = response.headers['content-type']
      if (contentType && contentType.includes('application/json')) {
        // 如果是JSON，读取文本并解析
        const text = await (response.data as Blob).text()
        return JSON.parse(text)
      }

      // 如果是文件流
      let filename = 'agent_export.zip'
      const disposition = response.headers['content-disposition']
      if (disposition) {
        // 优先尝试匹配 filename*= (RFC 5987)
        const filenameStarMatch = disposition.match(/filename\*=UTF-8''(.+)/i)
        if (filenameStarMatch && filenameStarMatch[1]) {
          filename = decodeURIComponent(filenameStarMatch[1])
        } else {
          // 回退匹配 filename=
          const filenameMatch = disposition.match(/filename=(.+)/i)
          if (filenameMatch && filenameMatch[1]) {
             // 去除引号
            filename = filenameMatch[1].replace(/["']/g, '')
          }
        }
      }

      return {
        blob: response.data,
        filename,
        isBlob: true
      }
    } catch (error) {
      console.error('导出智能体API调用失败:', error)
      throw error
    }
  }

  // 导入智能体
  static async importAgent(request: {
    space_id: string
    import_data: any
    overwrite: boolean
  }): Promise<{ code: number; message: string; data: any }> {
    try {
      const apiClient = getApiClient()
      
      // 如果 import_data 是 File 对象，使用 FormData 上传
      if (request.import_data instanceof File || (typeof Blob !== 'undefined' && request.import_data instanceof Blob)) {
        const formData = new FormData()
        formData.append('file', request.import_data)
        formData.append('space_id', request.space_id)
        formData.append('overwrite', String(request.overwrite))
        
        const response = await apiClient.post(API_ENDPOINTS.AGENTS.IMPORT, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
        return response.data
      }

      const response = await apiClient.post(API_ENDPOINTS.AGENTS.IMPORT, request)
      return response.data
    } catch (error) {
      console.error('导入智能体API调用失败:', error)
      throw error
    }
  }

  // 获取智能体版本列表
  static async getAgentVersionList(request: AgentVersionListRequest): Promise<AgentVersionListResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<AgentVersionListResponse>(API_ENDPOINTS.AGENTS.VERSION_LIST, request)
      return response.data
    } catch (error) {
      console.error('获取智能体版本列表API调用失败:', error)
      throw error
    }
  }

  // 删除智能体版本
  static async deleteAgentVersion(request: {
    agent_id: string
    space_id: string
    agent_version: string
  }): Promise<{ code: number; message: string; data?: any }> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post(API_ENDPOINTS.AGENTS.DELETE_PUBLISH_VERSION, request)
      return response.data
    } catch (error) {
      console.error('删除智能体版本API调用失败:', error)
      throw error
    }
  }
}

// 导出智能体服务实例
export default AgentService
