import { getApiClient } from '../utils/apiClientFactory'
import { API_ENDPOINTS } from '../config'
import {
  RuntimeDeployRequest,
  RuntimeDeployResponse,
  RuntimeDetailRequest,
  RuntimeDetailResponse,
  RuntimeRemoveRequest,
  RuntimeRemoveResponse,
  RuntimeResetConversationRequest,
  RuntimeResetConversationResponse,
} from '../types'

// 运行时部署服务
export class RuntimeService {
  // 部署智能体到运行时
  static async deploy(request: RuntimeDeployRequest): Promise<RuntimeDeployResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<RuntimeDeployResponse>(API_ENDPOINTS.RUNTIME.DEPLOY, request)
      return response.data
    } catch (error) {
      console.error('运行时部署API调用失败:', error)
      throw error
    }
  }

  static async detail(request: RuntimeDetailRequest): Promise<RuntimeDetailResponse> {
    try {
      const apiClient = getApiClient()
      const params = new URLSearchParams({
        agent_id: request.agent_id,
        space_id: request.space_id,
      })
      const response = await apiClient.post<RuntimeDetailResponse>(`${API_ENDPOINTS.RUNTIME.DETAIL}?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('查询运行时部署详情API调用失败:', error)
      throw error
    }
  }

  // 下架智能体部署
  static async remove(request: RuntimeRemoveRequest): Promise<RuntimeRemoveResponse> {
    try {
      const apiClient = getApiClient()
      const params = new URLSearchParams({
        agent_id: request.agent_id,
        space_id: request.space_id,
      })
      const response = await apiClient.delete<RuntimeRemoveResponse>(`${API_ENDPOINTS.RUNTIME.REMOVE}?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('下架运行时部署API调用失败:', error)
      throw error
    }
  }

  // 重置会话
  static async resetConversation(request: RuntimeResetConversationRequest): Promise<RuntimeResetConversationResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<RuntimeResetConversationResponse>(API_ENDPOINTS.RUNTIME.RESET_CONVERSATION, {
        target_url: request.target_url,
        space_id: request.space_id,
        conversation_id: request.conversation_id,
      })
      return response.data
    } catch (error) {
      console.error('重置会话API调用失败:', error)
      throw error
    }
  }
}

export default RuntimeService
