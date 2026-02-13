import { getApiClient } from '../utils/apiClientFactory'
import {
  CreateOptimizationJobRequest,
  CreateOptimizationJobResponse,
  GetJobListResponse,
  DeleteJobResponse,
  CaseCheckRequest,
  CaseCheckResponse,
  GetJobDetailResponse,
  SaveJobDraftRequest,
  SaveJobDraftResponse,
  GetJobDraftResponse,
  GetJobHistoryResponse,
} from '../types/selfOptTypes'
import { API_ENDPOINTS } from '../config'

/**
 * 自优化管理服务类
 * 提供优化任务的创建、管理、查询等功能
 */
export class SelfOptService {
  /**
   * 创建优化任务
   * @param data 创建优化任务数据
   * @param workspaceId 工作空间ID
   * @returns 创建优化任务响应
   */
  static async createOptimizationJob(data: CreateOptimizationJobRequest, workspaceId: string): Promise<CreateOptimizationJobResponse> {
    try {
      const url = `${API_ENDPOINTS.SELF_OPTIMIZATION.CREATE_JOB}?workspace_id=${workspaceId}`
      const response = await getApiClient().post<CreateOptimizationJobResponse>(url, data)
      return response.data
    } catch (error: any) {
      // 检查是否是ApiError且包含成功的响应
      if (error.name === 'ApiError' && error.code === 200 && error.response) {
        return error.response as CreateOptimizationJobResponse
      }

      throw error
    }
  }

  /**
   * 查询优化任务列表
   * @param idList 任务ID列表，默认为['*']表示查询所有
   * @param workspaceId 工作空间ID
   * @returns 任务列表响应
   */
  static async getJobList(idList: string[] = ['*'], workspaceId: string): Promise<GetJobListResponse> {
    try {
      const url = `${API_ENDPOINTS.SELF_OPTIMIZATION.GET_JOB_LIST}?workspace_id=${workspaceId}`
      const response = await getApiClient().post<GetJobListResponse>(url, { id_list: idList })
      return response.data
    } catch (error: any) {
      // 检查是否是ApiError且包含成功的响应
      if (error.name === 'ApiError' && error.code === 200 && error.response) {
        return error.response as GetJobListResponse
      }

      throw error
    }
  }

  /**
   * 删除优化任务
   * @param jobId 任务ID
   * @param workspaceId 工作空间ID
   * @param jobType 任务类型，formal表示优化任务，draft表示草稿
   * @returns 删除任务响应
   */
  static async deleteJob(jobId: string, workspaceId: string, jobType: 'formal' | 'draft' = 'formal'): Promise<DeleteJobResponse> {
    try {
      const url = `${API_ENDPOINTS.SELF_OPTIMIZATION.DELETE_JOB.replace(':jobId', jobId)}?workspace_id=${workspaceId}&job_type=${jobType}`
      const response = await getApiClient().delete<DeleteJobResponse>(url)
      return response.data
    } catch (error: any) {
      // 检查是否是ApiError且包含成功的响应
      if (error.name === 'ApiError' && error.code === 200 && error.response) {
        return error.response as DeleteJobResponse
      }

      throw error
    }
  }

  /**
   * 检查用例数据格式
   * @param data 用例检查数据
   * @returns 用例检查响应
   */
  static async checkCaseData(data: CaseCheckRequest): Promise<CaseCheckResponse> {
    try {
      const response = await getApiClient().post<CaseCheckResponse>(API_ENDPOINTS.SELF_OPTIMIZATION.DATA_CHECK, data)
      return response.data
    } catch (error: any) {
      // 检查是否是ApiError且包含成功的响应
      if (error.name === 'ApiError' && error.code === 200 && error.response) {
        return error.response as CaseCheckResponse
      }

      throw error
    }
  }

  /**
   * 查询优化任务详情
   * @param jobId 任务ID
   * @param workspaceId 工作空间ID
   * @returns 任务详情响应
   */
  static async getJobDetail(jobId: string, workspaceId: string): Promise<GetJobDetailResponse> {
    try {
      const baseUrl = API_ENDPOINTS.SELF_OPTIMIZATION.JOB_DETAIL.replace(':jobId', jobId)
      const url = `${baseUrl}?workspace_id=${workspaceId}`
      const response = await getApiClient().get<GetJobDetailResponse>(url)
      return response.data
    } catch (error: any) {
      // 检查是否是ApiError且包含成功的响应
      if (error.name === 'ApiError' && error.code === 200 && error.response) {
        return error.response as GetJobDetailResponse
      }

      throw error
    }
  }

  /**
   * 保存优化任务草稿
   * @param data 保存草稿数据
   * @param workspaceId 工作空间ID
   * @param draftId 草稿ID（可选，用于修改草稿）
   * @returns 保存草稿响应
   */
  static async saveJobDraft(data: SaveJobDraftRequest, workspaceId: string, draftId?: number): Promise<SaveJobDraftResponse> {
    try {
      const url = `${API_ENDPOINTS.SELF_OPTIMIZATION.SAVE_JOB_DRAFT}?workspace_id=${workspaceId}${draftId ? `&draft_id=${draftId}` : ''}`
      const response = await getApiClient().post<SaveJobDraftResponse>(url, data)
      return response.data
    } catch (error: any) {
      // 检查是否是ApiError且包含成功的响应
      if (error.name === 'ApiError' && error.code === 200 && error.response) {
        return error.response as SaveJobDraftResponse
      }

      throw error
    }
  }

  /**
   * 查询草稿详情
   * @param draftId 草稿ID
   * @param workspaceId 工作空间ID
   * @returns 草稿详情响应
   */
  static async getJobDraft(draftId: number, workspaceId: string): Promise<GetJobDraftResponse> {
    try {
      const url = `${API_ENDPOINTS.SELF_OPTIMIZATION.GET_JOB_DRAFT}?workspace_id=${workspaceId}&draft_id=${draftId}`
      const response = await getApiClient().get<GetJobDraftResponse>(url)
      return response.data
    } catch (error: any) {
      // 检查是否是ApiError且包含成功的响应
      if (error.name === 'ApiError' && error.code === 200 && error.response) {
        return error.response as GetJobDraftResponse
      }

      throw error
    }
  }

  /**
   * 查询用例历史记录
   * @param jobId 任务ID
   * @param workspaceId 工作空间ID
   * @param pageNum 第几页
   * @param pageSize 每页多少条数据
   * @param iterationRound 优化轮次
   * @returns 用例历史记录响应
   */
  static async getJobHistory(
    jobId: string,
    workspaceId: string,
    pageNum: number,
    pageSize: number,
    iterationRound: number,
  ): Promise<GetJobHistoryResponse> {
    try {
      const baseUrl = API_ENDPOINTS.SELF_OPTIMIZATION.JOB_HISTORY.replace(':jobId', jobId)
      const url = `${baseUrl}?workspace_id=${workspaceId}&page_num=${pageNum}&page_size=${pageSize}&iteration_round=${iterationRound}`
      const response = await getApiClient().get<GetJobHistoryResponse>(url)
      return response.data
    } catch (error: any) {
      // 检查是否是ApiError且包含响应数据
      if (error.name === 'ApiError' && error.response) {
        // 返回错误响应数据，让调用方可以处理错误信息
        return error.response as GetJobHistoryResponse
      }

      throw error
    }
  }
}
