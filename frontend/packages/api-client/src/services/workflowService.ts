import { getApiClient } from '../utils/apiClientFactory'
import { API_ENDPOINTS } from '../config'
import {
  WorkflowListRequest,
  WorkflowListResponse,
  CreateWorkflowResponse,
  WorkflowCanvasRequest,
  WorkflowCanvasResponse,
  WorkflowSaveRequest,
  WorkflowSaveResponse,
  CreateWorkflowRequest,
  DeleteWorkflowRequest,
  DeleteWorkflowResponse,
  UpdateWorkflowRequest,
  WorkflowUpdateResponse,
  CopyWorkflowRequest,
  CopyWorkflowResponse,
  WorkflowSearchRequest,
  WorkflowSearchResponse,
  WorkflowPublishRequest,
  WorkflowPublishResponse,
  WorkflowVersionListRequest,
  WorkflowVersionListResponse,
  ExecutionLogsListRequest,
  ExecutionLogsListResponse,
  ExecutionLogDetailRequest,
  ExecutionLogDetailResponse,
  ExecutionDebugRequest,
  ExecutionDebugResponse,
  GetUploadUrlRequest,
  GetUploadUrlResponse,
  GetDownloadUrlRequest,
  GetDownloadUrlResponse,
} from '../types'

// 工作流服务
export class WorkflowService {
  // 获取工作流列表
  static async getWorkflows(request: WorkflowListRequest): Promise<WorkflowListResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<WorkflowListResponse>(API_ENDPOINTS.WORKFLOWS.LIST, request)
    return response.data
  }

  // 创建工作流
  static async createWorkflow(request: CreateWorkflowRequest): Promise<CreateWorkflowResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<CreateWorkflowResponse>(API_ENDPOINTS.WORKFLOWS.CREATE, request)
    return response.data
  }

  // 获取工作流画布
  static async getWorkflowCanvas(request: WorkflowCanvasRequest): Promise<WorkflowCanvasResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<WorkflowCanvasResponse>(API_ENDPOINTS.WORKFLOWS.CANVAS, request)
    return response.data
  }

  // 保存工作流
  static async saveWorkflow(request: WorkflowSaveRequest): Promise<WorkflowSaveResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<WorkflowSaveResponse>(API_ENDPOINTS.WORKFLOWS.SAVE, request)
    return response.data
  }

  // 删除工作流
  static async deleteWorkflow(request: DeleteWorkflowRequest): Promise<DeleteWorkflowResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<DeleteWorkflowResponse>(API_ENDPOINTS.WORKFLOWS.DELETE, request)
    return response.data
  }

  // 更新工作流
  static async updateWorkflow(request: UpdateWorkflowRequest): Promise<WorkflowUpdateResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<WorkflowUpdateResponse>(API_ENDPOINTS.WORKFLOWS.UPDATE, request)
    return response.data
  }

  // 复制工作流
  static async copyWorkflow(request: CopyWorkflowRequest): Promise<CopyWorkflowResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<CopyWorkflowResponse>(API_ENDPOINTS.WORKFLOWS.COPY, request)
    return response.data
  }

  // 搜索工作流
  static async searchWorkflows(request: WorkflowSearchRequest): Promise<WorkflowSearchResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<WorkflowSearchResponse>(API_ENDPOINTS.WORKFLOWS.SEARCH, request)
    return response.data
  }

  // 获取执行日志列表
  static async getExecutionLogsList(request: ExecutionLogsListRequest): Promise<ExecutionLogsListResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<ExecutionLogsListResponse>(API_ENDPOINTS.WORKFLOWS.EXECUTION_LOGS_LIST, request)
    return response.data
  }

  // 获取执行日志详情
  static async getExecutionLogDetail(request: ExecutionLogDetailRequest): Promise<ExecutionLogDetailResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<ExecutionLogDetailResponse>(API_ENDPOINTS.WORKFLOWS.EXECUTION_LOG_DETAIL, request)
    return response.data
  }

  // 进入执行日志调试模式
  static async enterExecutionDebug(request: ExecutionDebugRequest): Promise<ExecutionDebugResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<ExecutionDebugResponse>(API_ENDPOINTS.WORKFLOWS.ENTER_EXECUTION_DEBUG, request)
    return response.data
  }

  // 发布工作流
  static async publishWorkflow(request: WorkflowPublishRequest): Promise<WorkflowPublishResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<WorkflowPublishResponse>(API_ENDPOINTS.WORKFLOWS.PUBLISH, request)
    return response.data
  }

  // 获取工作流版本列表
  static async getWorkflowVersionList(request: WorkflowVersionListRequest): Promise<WorkflowVersionListResponse> {
    const apiClient = getApiClient()
    const response = await apiClient.post<WorkflowVersionListResponse>(API_ENDPOINTS.WORKFLOWS.VERSION_LIST, request)
    return response.data
  }

  // 删除工作流版本
  static async deleteWorkflowVersion(request: {
    workflow_id: string
    space_id: string
    workflow_version: string
  }): Promise<{ code: number; message: string; data?: any }> {
    const apiClient = getApiClient()
    const response = await apiClient.post(API_ENDPOINTS.WORKFLOWS.DELETE_PUBLISH_VERSION, request)
    return response.data
  }

  // 导出工作流为 Python 脚本
  static async exportWorkflowPy(workflowId: string, spaceId?: string): Promise<{ workflow_id: string; python_code: string }> {
    const apiClient = getApiClient()
    const queryParams = spaceId ? `?space_id=${encodeURIComponent(spaceId)}` : ''
    const response = await apiClient.get<{ code: number; message: string; data: { workflow_id: string; python_code: string } }>(
      `${API_ENDPOINTS.WORKFLOWS.EXPORT_PY}/${workflowId}${queryParams}`
    )
    return response.data.data
  }

  // 获取文件上传URL
  static async getUploadUrl(request: GetUploadUrlRequest): Promise<GetUploadUrlResponse> {
    const apiClient = getApiClient()
    const { object_key, space_id } = request
    const queryParams = space_id ? `?space_id=${encodeURIComponent(space_id)}` : ''
    const response = await apiClient.get<GetUploadUrlResponse>(
      `${API_ENDPOINTS.WORKFLOWS.GET_UPLOAD_URL}/${object_key}${queryParams}`
    )
    return response.data
  }

  // 获取文件下载URL
  static async getDownloadUrl(request: GetDownloadUrlRequest): Promise<GetDownloadUrlResponse> {
    const apiClient = getApiClient()
    const { object_key, space_id } = request
    const queryParams = space_id ? `?space_id=${encodeURIComponent(space_id)}` : ''
    const response = await apiClient.get<GetDownloadUrlResponse>(
      `${API_ENDPOINTS.WORKFLOWS.GET_DOWNLOAD_URL}/${object_key || ''}${queryParams}`
    )
    return response.data
  }

  // 导入工作流
  static async importWorkflow(formData: FormData): Promise<{ code: number; message: string; data?: any }> {
    const apiClient = getApiClient()
    const response = await apiClient.post<{ code: number; message: string; data?: any }>(API_ENDPOINTS.WORKFLOWS.IMPORT, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }
}

// 导出工作流服务实例
export default WorkflowService
