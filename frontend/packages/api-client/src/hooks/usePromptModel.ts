import { useQuery, useMutation } from 'react-query'
import { PromptModelService } from '../services/promptModelService'
import { GetModelsListParams } from '../types/promptModelTypes'

// 提示词模型相关的React Query hooks

// 获取模型列表
export const usePromptModelsList = (params?: GetModelsListParams) => {
  return useQuery(
    ['promptModels', 'list', params?.workspaceId, params?.scenario, params?.pageSize, params?.pageToken],
    () => PromptModelService.getModelsList(params),
    {
      enabled: !!params?.workspaceId, // 只有当workspaceId存在时才执行查询
      staleTime: 5 * 60 * 1000, // 5分钟内不重新获取
      cacheTime: 10 * 60 * 1000, // 缓存10分钟
      retry: 2,
      retryDelay: 1000,
      onError: (error: any) => {
        console.error('获取模型列表失败:', error)
      },
    },
  )
}

// 获取模型详情
export const usePromptModelDetail = (modelId?: string, modelFrom?: string, workspaceId?: string) => {
  return useQuery(
    ['promptModels', 'detail', modelId, modelFrom, workspaceId],
    () => PromptModelService.getModelDetail(modelId!, modelFrom, workspaceId),
    {
      enabled: !!modelId, // 只有当modelId存在时才执行查询
    staleTime: 10 * 60 * 1000, // 10分钟内不重新获取
    cacheTime: 30 * 60 * 1000, // 缓存30分钟
    retry: 2,
    retryDelay: 1000,
    onError: (error: any) => {
      console.error('获取模型详情失败:', error)
    },
  })
}

// 刷新模型列表
export const useRefreshPromptModelsList = () => {
  return useMutation((params?: GetModelsListParams) => PromptModelService.getModelsList(params), {
    onSuccess: (_response: any, _params?: any) => {
      console.log('模型列表刷新成功')
    },
    onError: (error: any) => {
      console.error('刷新模型列表失败:', error)
    },
  })
}
