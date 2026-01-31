import { useMutation, useQuery, useQueryClient } from 'react-query'
import { modelService } from '../services/modelService'
import type { FrontendModelConfig } from '../services/modelService'
import { ModelProvider } from '../types/modelTypes'

// 模型管理相关的React Query hooks

// 获取模型配置列表
export const useModels = (params?: {
  spaceId?: string
  provider?: ModelProvider
  isActive?: boolean
  is_active?: boolean // 添加后端API期望的字段名
  search?: string
  page?: number
  size?: number
  sort_by?: 'create_time' | 'update_time' | 'name'
  sort_order?: 'asc' | 'desc'
}) => {
  return useQuery(['models', 'list', params?.spaceId, params], () => modelService.getModelConfigs(params), {
    enabled: !!params?.spaceId, // 只有当spaceId存在时才执行查询
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
      console.error('从API获取模型列表失败:', error)
    },
    // 🎯 成功回调，用于调试
    onSuccess: data => {
      console.log(`成功获取 space_id ${params?.spaceId} 的模型列表，共 ${data?.items?.length || 0} 个模型`)
    },
  })
}

// 获取单个模型配置
export const useModel = (id: string, spaceId: string) => {
  return useQuery(['models', 'detail', id, spaceId], () => modelService.getModelConfig(id, spaceId), {
    enabled: !!id && !!spaceId, // 只有当id和spaceId都存在时才执行查询
    staleTime: 2 * 60 * 1000, // 2分钟内不重新获取
    cacheTime: 5 * 60 * 1000, // 缓存5分钟
    retry: 2,
    retryDelay: 1000,
    onError: error => {
      console.log('获取模型详情失败:', error)
    },
  })
}

// 创建模型配置
export const useCreateModel = () => {
  const queryClient = useQueryClient()

  return useMutation(({ model, spaceId }: { model: Partial<FrontendModelConfig>; spaceId: string }) => modelService.createModelConfig(model, spaceId), {
    onSuccess: newModel => {
      // 使相关查询失效，触发重新获取
      queryClient.invalidateQueries(['models', 'list'])
    },
    onError: error => {
      console.log('创建模型失败:', error)
    },
  })
}

// 更新模型配置
export const useUpdateModel = () => {
  const queryClient = useQueryClient()

  return useMutation(
    ({ id, model, spaceId }: { id: string; model: Partial<FrontendModelConfig>; spaceId: string }) => modelService.updateModelConfig(id, model, spaceId),
    {
      onSuccess: updatedModel => {
        // 更新成功后，更新缓存中的模型数据
        queryClient.setQueryData(['models', 'detail', updatedModel.id], updatedModel)

        // 使相关查询失效
        queryClient.invalidateQueries(['models', 'list'])
        queryClient.invalidateQueries(['models', 'detail', updatedModel.id])
      },
      onError: error => {
        console.log('更新模型失败:', error)
      },
    },
  )
}

// 删除模型配置
export const useDeleteModel = () => {
  const queryClient = useQueryClient()

  return useMutation(({ id, spaceId }: { id: string; spaceId: string }) => modelService.deleteModelConfig(id, spaceId), {
    onSuccess: (_, variables) => {
      const { id } = variables
      // 移除详情缓存
      queryClient.removeQueries(['models', 'detail', id])

      // 使相关查询失效
      queryClient.invalidateQueries(['models', 'list'])
    },
    onError: error => {
      console.log('删除模型失败:', error)
    },
  })
}

// 切换模型状态
export const useToggleModelStatus = () => {
  const queryClient = useQueryClient()

  return useMutation(({ id, spaceId }: { id: string; spaceId: string }) => modelService.toggleModelStatus(id, spaceId), {
    onSuccess: updatedModel => {
      // 更新成功后，更新缓存中的模型数据
      queryClient.setQueryData(['models', 'detail', updatedModel.id], updatedModel)

      // 使相关查询失效
      queryClient.invalidateQueries(['models', 'list'])
      queryClient.invalidateQueries(['models', 'detail', updatedModel.id])
    },
    onError: error => {
      console.log('切换模型状态失败:', error)
    },
  })
}

// 测试模型
export const useTestModel = () => {
  return useMutation(
    ({ id, prompt, spaceId, parameters }: { id: string; prompt: string; spaceId: string; parameters?: { temperature?: number; top_p?: number; max_tokens?: number } }) =>
      modelService.testModel(id, prompt, spaceId, parameters),
    {
      onError: error => {
        console.log('测试模型失败:', error)
      },
    },
  )
}

// 刷新模型列表
export const useRefreshModels = () => {
  const queryClient = useQueryClient()

  return () => {
    queryClient.invalidateQueries(['models', 'list'])
  }
}

// 预加载模型详情
export const usePrefetchModel = () => {
  const queryClient = useQueryClient()

  return (id: string, spaceId: string) => {
    queryClient.prefetchQuery(['models', 'detail', id, spaceId], () => modelService.getModelConfig(id, spaceId), {
      staleTime: 2 * 60 * 1000,
      cacheTime: 5 * 60 * 1000,
    })
  }
}
