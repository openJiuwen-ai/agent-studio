import { useMutation, useQuery, useQueryClient } from 'react-query'
import { embeddingModelService } from '../services/embeddingModelService'
import type { FrontendEmbeddingModelConfig } from '../services/embeddingModelService'
import type { EmbeddingProtocol, EmbeddingModelTestRequest } from '../types/embeddingModelTypes'

// Embedding 模型管理相关的 React Query hooks

// 获取 Embedding 模型配置列表
export const useEmbeddingModels = (params?: {
  spaceId?: string
  protocol?: EmbeddingProtocol
  is_active?: boolean
  search?: string
  page?: number
  size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}) => {
  const { spaceId, ...queryParams } = params || {}

  return useQuery(['embeddingModels', 'list', spaceId, queryParams], () => embeddingModelService.getEmbeddingModelConfigs(spaceId!, queryParams), {
    enabled: !!spaceId, // 只有当spaceId存在时才执行查询
    // 🎯 禁用缓存，确保搜索、排序、过滤时都重新请求
    staleTime: 0, // 数据立即过期，每次参数改变时都重新请求
    cacheTime: 5 * 60 * 1000, // 保留缓存时间用于内存管理（组件卸载后保留5分钟）
    // 🎯 添加自动刷新机制
    refetchOnMount: true, // 组件挂载时重新获取数据
    refetchOnWindowFocus: false, // 窗口重新聚焦时不重新获取数据
    refetchOnReconnect: true, // 网络重连时重新获取数据
    retry: 2,
    retryDelay: 1000,
    onError: error => {
      console.error('从API获取 Embedding 模型列表失败:', error)
    },
    // 🎯 成功回调，用于调试
    onSuccess: data => {
      console.log(`成功获取 space_id ${spaceId} 的 Embedding 模型列表，共 ${data?.items?.length || 0} 个模型`)
    },
  })
}

// 获取单个 Embedding 模型配置
export const useEmbeddingModel = (configId: string, spaceId: string) => {
  return useQuery(['embeddingModels', 'detail', configId, spaceId], () => embeddingModelService.getEmbeddingModelConfig(configId, spaceId), {
    enabled: !!configId && !!spaceId,
    staleTime: 2 * 60 * 1000,
    cacheTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: 1000,
    onError: error => {
      console.error('获取 Embedding 模型详情失败:', error)
    },
  })
}

// 创建 Embedding 模型配置
export const useCreateEmbeddingModel = () => {
  const queryClient = useQueryClient()

  return useMutation(
    ({ model, spaceId }: { model: Partial<FrontendEmbeddingModelConfig>; spaceId: string }) => embeddingModelService.createEmbeddingModelConfig(model, spaceId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['embeddingModels', 'list'])
      },
      onError: error => {
        console.error('创建 Embedding 模型失败:', error)
      },
    },
  )
}

// 更新 Embedding 模型配置
export const useUpdateEmbeddingModel = () => {
  const queryClient = useQueryClient()

  return useMutation(
    ({ id, model, spaceId }: { id: string; model: Partial<FrontendEmbeddingModelConfig>; spaceId: string }) =>
      embeddingModelService.updateEmbeddingModelConfig(id, model, spaceId),
    {
      onSuccess: updatedModel => {
        queryClient.setQueryData(['embeddingModels', 'detail', updatedModel.id], updatedModel)
        queryClient.invalidateQueries(['embeddingModels', 'list'])
        queryClient.invalidateQueries(['embeddingModels', 'detail', updatedModel.id])
      },
      onError: error => {
        console.error('更新 Embedding 模型失败:', error)
      },
    },
  )
}

// 删除 Embedding 模型配置
export const useDeleteEmbeddingModel = () => {
  const queryClient = useQueryClient()

  return useMutation(({ id, spaceId }: { id: string; spaceId: string }) => embeddingModelService.deleteEmbeddingModelConfig(id, spaceId), {
    onSuccess: (_, variables) => {
      const { id } = variables
      queryClient.removeQueries(['embeddingModels', 'detail', id])
      queryClient.invalidateQueries(['embeddingModels', 'list'])
    },
    onError: error => {
      console.error('删除 Embedding 模型失败:', error)
    },
  })
}

// 切换 Embedding 模型状态
export const useToggleEmbeddingModelStatus = () => {
  const queryClient = useQueryClient()

  return useMutation(({ id, spaceId }: { id: string; spaceId: string }) => embeddingModelService.toggleEmbeddingModelStatus(id, spaceId), {
    onSuccess: updatedModel => {
      queryClient.setQueryData(['embeddingModels', 'detail', updatedModel.id], updatedModel)
      queryClient.invalidateQueries(['embeddingModels', 'list'])
      queryClient.invalidateQueries(['embeddingModels', 'detail', updatedModel.id])
    },
    onError: error => {
      console.error('切换 Embedding 模型状态失败:', error)
    },
  })
}

// 测试 Embedding 模型
export const useTestEmbeddingModel = () => {
  return useMutation(
    ({ id, testRequest }: { id: string; testRequest: EmbeddingModelTestRequest }) => embeddingModelService.testEmbeddingModel(id, testRequest),
    {
      onError: error => {
        console.error('测试 Embedding 模型失败:', error)
      },
    },
  )
}

// 刷新 Embedding 模型列表
export const useRefreshEmbeddingModels = () => {
  const queryClient = useQueryClient()

  return () => {
    queryClient.invalidateQueries(['embeddingModels', 'list'])
  }
}

// 预加载 Embedding 模型详情
export const usePrefetchEmbeddingModel = () => {
  const queryClient = useQueryClient()

  return (configId: string, spaceId: string) => {
    queryClient.prefetchQuery(['embeddingModels', 'detail', configId, spaceId], () => embeddingModelService.getEmbeddingModelConfig(configId, spaceId), {
      staleTime: 2 * 60 * 1000,
      cacheTime: 5 * 60 * 1000,
    })
  }
}

