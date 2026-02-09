import { getApiClient } from '../utils/apiClientFactory'
import { API_ENDPOINTS } from '../config'
import {
  CreateMemoryBaseRequest,
  CreateMemoryBaseResponse,
  GetMemoryBasesRequest,
  GetMemoryBasesResponse,
  MemoryBase,
  UpdateMemoryBaseRequest,
  UpdateMemoryBaseResponse,
  DeleteMemoryBaseRequest,
  DeleteMemoryBaseResponse,
  GetMemoryBaseDetailRequest,
  GetMemoryBaseDetailResponse,
  BatchAddMemoriesRequest,
  BatchAddMemoriesResponse,
  GetMemoriesListRequest,
  GetMemoriesListResponse,
  UpdateMemoryRequest,
  UpdateMemoryResponse,
  DeleteMemoriesRequest,
  DeleteMemoriesResponse,
  ProcessMemoriesRequest,
  ProcessMemoriesResponse,
  GetMemoryStatusRequest,
  GetMemoryStatusResponse,
  SearchMemoryBaseRequest,
  SearchMemoryBaseResponse,
  CleanExpiredMemoriesRequest,
  CleanExpiredMemoriesResponse,
  GetDocumentsListRequest,
  GetDocumentsListResponse,
  UpdateDocumentRequest,
  UpdateDocumentResponse,
  DeleteDocumentsRequest,
  DeleteDocumentsResponse,
  ProcessDocumentsRequest,
  ProcessDocumentsResponse,
  GetDocumentStatusRequest,
  GetDocumentStatusResponse,
} from '../types/memoryBase'
// 记忆库服务
export class MemoryBaseService {
  // 创建记忆库 (V2 API)
  static async createMemoryBase(request: CreateMemoryBaseRequest): Promise<CreateMemoryBaseResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<{ code: number; message: string; data: CreateMemoryBaseResponse }>(
        API_ENDPOINTS.MEMORY_BASES.CREATE,
        request
      )
      return response.data.data
    } catch (error: any) {
      const errorMessage = error?.response?.data?.message || error?.message || '创建记忆库失败'
      throw new Error(errorMessage)
    }
  }

  // 获取记忆库列表
  static async getMemoryBases(request: GetMemoryBasesRequest): Promise<GetMemoryBasesResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<GetMemoryBasesResponse>(API_ENDPOINTS.MEMORY_BASES.LIST, request)
      return response.data
    } catch (error) {
      console.error('获取记忆库列表API调用失败:', error)
      throw new Error(`获取记忆库列表失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 获取记忆库详情
  static async getMemoryBaseDetail(request: GetMemoryBaseDetailRequest): Promise<GetMemoryBaseDetailResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<GetMemoryBaseDetailResponse>(
        API_ENDPOINTS.MEMORY_BASES.DETAIL.replace(':id', request.id),
        request
      )
      return response.data
    } catch (error) {
      console.error('获取记忆库详情API调用失败:', error)
      throw new Error(`获取记忆库详情失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 更新记忆库
  static async updateMemoryBase(request: UpdateMemoryBaseRequest): Promise<UpdateMemoryBaseResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<UpdateMemoryBaseResponse>(API_ENDPOINTS.MEMORY_BASES.UPDATE, request)
      return response.data
    } catch (error: any) {
      const errorMessage = error?.response?.data?.message || error?.message || '更新记忆库失败'
      throw new Error(errorMessage)
    }
  }

  // 获取引用记忆库的智能体列表
  static async getReferencingAgents(request: { space_id: string; mb_id: string }): Promise<{ agent_names: string[]; count: number }> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<{ code: number; message: string; data: { agent_names: string[]; count: number } }>(
        API_ENDPOINTS.MEMORY_BASES.GET_REFERENCING_AGENTS,
        request
      )
      if (response.data.code === 200) {
        return response.data.data
      }
      throw new Error(response.data.message || '获取引用智能体列表失败')
    } catch (error) {
      console.error('获取引用智能体列表API调用失败:', error)
      throw new Error(`获取引用智能体列表失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 删除记忆库
  static async deleteMemoryBase(request: DeleteMemoryBaseRequest): Promise<DeleteMemoryBaseResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<DeleteMemoryBaseResponse>(API_ENDPOINTS.MEMORY_BASES.DELETE, request)
      return response.data
    } catch (error) {
      console.error('删除记忆库API调用失败:', error)
      throw new Error(`删除记忆库失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 批量添加记忆条目
  static async batchAddMemories(request: BatchAddMemoriesRequest): Promise<BatchAddMemoriesResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<BatchAddMemoriesResponse>(API_ENDPOINTS.MEMORY_BASES.BATCH_ADD, request)
      return response.data
    } catch (error) {
      console.error('批量添加记忆条目API调用失败:', error)
      throw new Error(`批量添加记忆条目失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 获取记忆条目列表
  static async getMemoriesList(request: GetMemoriesListRequest): Promise<GetMemoriesListResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<GetMemoriesListResponse>(API_ENDPOINTS.MEMORY_BASES.MEMORIES_LIST, request)
      return response.data
    } catch (error) {
      console.error('获取记忆条目列表API调用失败:', error)
      throw new Error(`获取记忆条目列表失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 更新记忆条目
  static async updateMemory(request: UpdateMemoryRequest): Promise<UpdateMemoryResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<UpdateMemoryResponse>('/memory-bases/update', request)
      return response.data
    } catch (error) {
      console.error('更新记忆条目API调用失败:', error)
      throw new Error(`更新记忆条目失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 删除记忆条目
  static async deleteMemories(request: DeleteMemoriesRequest): Promise<DeleteMemoriesResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<DeleteMemoriesResponse>('/memory-bases/delete', request)
      return response.data
    } catch (error) {
      console.error('删除记忆条目API调用失败:', error)
      throw new Error(`删除记忆条目失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 处理记忆条目（解析/分割/索引）
  static async processMemories(request: ProcessMemoriesRequest): Promise<ProcessMemoriesResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<ProcessMemoriesResponse>(API_ENDPOINTS.MEMORY_BASES.PROCESS, request)
      return response.data
    } catch (error) {
      console.error('处理记忆条目API调用失败:', error)
      throw new Error(`处理记忆条目失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 查询记忆条目状态
  static async getMemoryStatus(request: GetMemoryStatusRequest): Promise<GetMemoryStatusResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<GetMemoryStatusResponse>(API_ENDPOINTS.MEMORY_BASES.STATUS, request)
      return response.data
    } catch (error) {
      console.error('查询记忆条目状态API调用失败:', error)
      throw new Error(`查询记忆条目状态失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 搜索记忆库
  static async searchMemoryBase(request: SearchMemoryBaseRequest): Promise<SearchMemoryBaseResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<SearchMemoryBaseResponse>(API_ENDPOINTS.MEMORY_BASES.SEARCH, request)
      return response.data
    } catch (error) {
      console.error('搜索记忆库API调用失败:', error)
      throw new Error(`搜索记忆库失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }
  // 获取文档列表
  static async getDocumentsList(request: GetDocumentsListRequest): Promise<GetDocumentsListResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<GetDocumentsListResponse>(API_ENDPOINTS.KNOWLEDGE_BASES.DOCUMENTS_LIST, request)
      return response.data
    } catch (error) {
      console.error('获取文档列表API调用失败:', error)
      throw new Error(`获取文档列表失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 更新文档
  static async updateDocument(request: UpdateDocumentRequest): Promise<UpdateDocumentResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<UpdateDocumentResponse>('/knowledge-base/documents/update', request)
      return response.data
    } catch (error) {
      console.error('更新文档API调用失败:', error)
      throw new Error(`更新文档失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 删除文档
  static async deleteDocuments(request: DeleteDocumentsRequest): Promise<DeleteDocumentsResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<DeleteDocumentsResponse>('/knowledge-base/documents/delete', request)
      return response.data
    } catch (error) {
      console.error('删除文档API调用失败:', error)
      throw new Error(`删除文档失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 处理文档
  static async processDocuments(request: ProcessDocumentsRequest): Promise<ProcessDocumentsResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<ProcessDocumentsResponse>(API_ENDPOINTS.KNOWLEDGE_BASES.PROCESS, request)
      return response.data
    } catch (error) {
      console.error('处理文档API调用失败:', error)
      throw new Error(`处理文档失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  // 查询文档状态
  static async getDocumentStatus(request: GetDocumentStatusRequest): Promise<GetDocumentStatusResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<GetDocumentStatusResponse>(API_ENDPOINTS.KNOWLEDGE_BASES.STATUS, request)
      return response.data
    } catch (error) {
      console.error('查询文档状态API调用失败:', error)
      throw new Error(`查询文档状态失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }
  // 清理过期记忆条目
  static async cleanExpiredMemories(request: CleanExpiredMemoriesRequest): Promise<CleanExpiredMemoriesResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<CleanExpiredMemoriesResponse>(API_ENDPOINTS.MEMORY_BASES.CLEAN_EXPIRED, request)
      return response.data
    } catch (error) {
      console.error('清理过期记忆条目API调用失败:', error)
      throw new Error(`清理过期记忆条目失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }
}

// 导出记忆库服务实例
export default MemoryBaseService