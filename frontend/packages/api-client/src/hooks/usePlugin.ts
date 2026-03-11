import { useMutation, useQuery, useQueryClient } from 'react-query'
import PluginService from '../services/pluginService'
import { getErrorMessage, getErrorResponse } from '../utils/errorHandling'
import {
  PluginCreateRequest,
  PluginGetRequest,
  PluginDeleteRequest,
  PluginUpdateRequest,
  PluginListRequest,
  PluginCreateApiRequest,
  PluginUpdateApiRequest,
  PluginDeleteApiRequest,
  PluginGetApiRequest,
  PluginListApiRequest,
  PluginExecuteRequest,
  PluginExecutionEventHandler,
  PluginCreateCodeRequest,
  PluginUpdateCodeRequest,
  PluginDeleteCodeRequest,
  PluginGetCodeRequest,
  PluginListCodeRequest,
  PluginCreateCodeResponse,
  PluginUpdateCodeResponse,
  PluginDeleteCodeResponse,
  PluginGetCodeResponse,
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
  PluginListMcpToolsRequest,
  PluginMcpInfoResponse,
  PluginDiscoverMcpToolsRequest,
  PluginDiscoverMcpToolsResponse,
} from '../types'

// 插件相关的React Query hooks

// 创建插件
export const useCreatePlugin = () => {
  return useMutation((request: PluginCreateRequest) => PluginService.createPlugin(request), {
    onSuccess: response => {
      if (response.code === 200) {
        // 创建成功后，使相关缓存失效
        console.log('插件创建成功')
      }
    },
    onError: error => {
      console.error('创建插件失败:', error)
    },
  })
}

// 获取插件信息
export const usePlugin = (request: PluginGetRequest) => {
  return useQuery(
    ['plugin', request.plugin_id, request.space_id],
    async () => {
      // Add a small delay to ensure API client is initialized
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPlugin(request)
    },
    {
      enabled: !!request.plugin_id && !!request.space_id, // 只有当plugin_id和space_id都存在时才执行查询

      // 优化缓存策略
      staleTime: 30 * 1000, // 30秒内数据视为新鲜
      cacheTime: 5 * 60 * 1000, // 缓存5分钟

      // 添加自动刷新机制
      refetchOnMount: true, // 组件挂载时重新获取数据
      refetchOnWindowFocus: true, // 窗口重新聚焦时重新获取数据
      refetchOnReconnect: true, // 网络重连时重新获取数据

      // 重试策略
      retry: (failureCount, error) => {
        // Don't retry on API client initialization errors
        if (error?.message?.includes('API client not initialized')) {
          console.warn('API client not initialized, skipping retry for plugin:', request.plugin_id)
          return false
        }
        // 只对网络错误重试，最多重试3次
        if (failureCount >= 3) return false
        const errorMessage = getErrorMessage(error)
        return errorMessage.includes('Network Error') || errorMessage.includes('timeout')
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000), // 指数退避

      // 错误处理
      onError: error => {
        console.error('获取插件信息失败:', error)

        // 添加错误日志记录，便于调试
        const errorResponse = getErrorResponse(error)
        if (errorResponse?.status === 404) {
          console.warn(`插件 ${request.plugin_id} 不存在或已被删除`)
        } else if (errorResponse?.status === 403) {
          console.warn(`没有权限访问插件 ${request.plugin_id}`)
        }
      },
    },
  )
}

// 获取插件列表
export const usePluginList = (request: PluginListRequest, options?: { enabled?: boolean }) => {
  return useQuery(
    ['pluginList', request.space_id, request.page, request.size],
    async () => {
      // Add a small delay to ensure API client is initialized
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginList(request)
    },
    {
      enabled: options?.enabled !== false && !!request.space_id, // 只有当space_id存在时才执行查询，允许外部控制
      retry: (failureCount, error) => {
        // Don't retry on API client initialization errors
        if (error?.message?.includes('API client not initialized')) {
          return false
        }
        // Only retry on network errors, max 3 times
        if (failureCount >= 3) return false
        const errorMessage = getErrorMessage(error)
        return errorMessage.includes('Network Error') || errorMessage.includes('timeout')
      },

      // 🎯 禁用缓存，确保搜索、排序、过滤时都重新请求
      staleTime: 0, // 数据立即过期，每次参数改变时都重新请求
      cacheTime: 5 * 60 * 1000, // 保留缓存时间用于内存管理（组件卸载后保留5分钟）

      // 🎯 添加自动刷新机制
      refetchOnMount: true, // 组件挂载时重新获取数据
      refetchOnWindowFocus: false, // 窗口重新聚焦时不重新获取数据
      refetchOnReconnect: true, // 网络重连时重新获取数据

      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000), // 指数退避

      // 错误处理
      onError: error => {
        console.error('获取插件列表失败:', error)

        // 添加错误日志记录，便于调试
        const errorResponse = getErrorResponse(error)
        if (errorResponse?.status === 403) {
          console.warn(`没有权限访问空间 ${request.space_id} 的插件列表`)
        }
      },
    },
  )
}

// 刷新插件信息
export const useRefreshPlugin = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginGetRequest) => PluginService.getPlugin(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 刷新成功后，更新缓存
        queryClient.invalidateQueries(['plugin', variables.plugin_id, variables.space_id])
        console.log('插件信息刷新成功')
      }
    },
    onError: error => {
      console.error('刷新插件信息失败:', error)
    },
  })
}

// 更新插件
export const useUpdatePlugin = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginUpdateRequest) => PluginService.updatePlugin(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 更新成功后，使相关缓存失效
        queryClient.invalidateQueries(['plugin', variables.plugin_id, variables.space_id])
        queryClient.invalidateQueries(['pluginList', variables.space_id])
        console.log('插件更新成功')
      }
    },
    onError: error => {
      console.error('更新插件失败:', error)
    },
  })
}

// 删除插件
export const useDeletePlugin = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginDeleteRequest) => PluginService.deletePlugin(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 删除成功后，使插件缓存失效
        queryClient.removeQueries(['plugin', variables.plugin_id, variables.space_id])
        console.log('插件删除成功')
      }
    },
    onError: error => {
      console.error('删除插件失败:', error)
    },
  })
}

// 插件 API 相关的 React Query hooks

// 创建插件 API
export const usePluginCreateApi = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginCreateApiRequest) => PluginService.createPluginApi(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 创建成功后，使相关缓存失效
        queryClient.invalidateQueries(['pluginApiList', variables.space_id, variables.plugin_id])
        console.log('插件 API 创建成功')
      }
    },
    onError: error => {
      console.error('创建插件 API 失败:', error)
    },
  })
}

// 更新插件 API
export const usePluginUpdateApi = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginUpdateApiRequest) => PluginService.updatePluginApi(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 更新成功后，使相关缓存失效
        queryClient.invalidateQueries(['pluginApi', variables.space_id, variables.plugin_id, variables.tool_id])
        queryClient.invalidateQueries(['pluginApiList', variables.space_id, variables.plugin_id])
        console.log('插件 API 更新成功')
      }
    },
    onError: error => {
      console.error('更新插件 API 失败:', error)
    },
  })
}

// 删除插件 API
export const usePluginDeleteApi = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginDeleteApiRequest) => PluginService.deletePluginApi(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 删除成功后，使相关缓存失效
        queryClient.removeQueries(['pluginApi', variables.space_id, variables.plugin_id, variables.tool_id])
        queryClient.invalidateQueries(['pluginApiList', variables.space_id, variables.plugin_id])
        console.log('插件 API 删除成功')
      }
    },
    onError: error => {
      console.error('删除插件 API 失败:', error)
    },
  })
}

// 获取插件 API
export const usePluginGetApi = (request: PluginGetApiRequest) => {
  return useQuery(
    ['pluginApi', request.space_id, request.plugin_id, request.tool_id],
    async () => {
      // Add a small delay to ensure API client is initialized
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginApi(request)
    },
    {
      enabled: !!request.space_id && !!request.plugin_id && !!request.tool_id,

      // 优化缓存策略
      staleTime: 30 * 1000, // 30秒内数据视为新鲜
      cacheTime: 5 * 60 * 1000, // 缓存5分钟

      // 添加自动刷新机制
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,

      // 重试策略
      retry: (failureCount, error) => {
        // Don't retry on API client initialization errors
        if (error?.message?.includes('API client not initialized')) {
          console.warn('API client not initialized, skipping retry for plugin API:', request.tool_id)
          return false
        }
        if (failureCount >= 3) return false
        return error?.message?.includes('Network Error') || error?.message?.includes('timeout')
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),

      // 错误处理
      onError: error => {
        console.error('获取插件 API 失败:', error)
        const errorResponse = getErrorResponse(error)
        if (errorResponse?.status === 404) {
          console.warn(`插件 API ${request.tool_id} 不存在或已被删除`)
        } else if (errorResponse?.status === 403) {
          console.warn(`没有权限访问插件 API ${request.tool_id}`)
        }
      },
    },
  )
}

// 获取插件 API 列表
export const usePluginListApi = (request: PluginListApiRequest, options?: { enabled?: boolean }) => {
  return useQuery(
    ['pluginApiList', request.space_id, request.plugin_id, request.page, request.size],
    async () => {
      // Add a small delay to ensure API client is initialized
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginApiList(request)
    },
    {
      enabled: (options?.enabled !== false) && !!request.space_id && !!request.plugin_id,

      // 优化缓存策略
      staleTime: 30 * 1000, // 30秒内数据视为新鲜
      cacheTime: 5 * 60 * 1000, // 缓存5分钟

      // 添加自动刷新机制
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,

      // 重试策略
      retry: (failureCount, error) => {
        // Don't retry on API client initialization errors
        if (error?.message?.includes('API client not initialized')) {
          console.warn('API client not initialized, skipping retry for plugin API list:', request.plugin_id)
          return false
        }
        if (failureCount >= 3) return false
        return error?.message?.includes('Network Error') || error?.message?.includes('timeout')
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),

      // 错误处理
      onError: error => {
        console.error('获取插件 API 列表失败:', error)
        if (error?.response?.status === 403) {
          console.warn(`没有权限访问插件 ${request.plugin_id} 的 API 列表`)
        }
      },
    },
  )
}

// 获取插件 MCP 工具列表
export const usePluginListMcpTools = (request: PluginListMcpToolsRequest, options?: { enabled?: boolean }) => {
  return useQuery(
    ['pluginMcpToolsList', request.space_id, request.plugin_id, request.page, request.size],
    async () => {
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginMcpToolsList(request)
    },
    {
      enabled: (options?.enabled !== false) && !!request.space_id && !!request.plugin_id,
      staleTime: 30 * 1000,
      cacheTime: 5 * 60 * 1000,
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      retry: (failureCount, error) => {
        if ((error as any)?.message?.includes('API client not initialized')) return false
        if (failureCount >= 3) return false
        return (error as any)?.message?.includes('Network Error') || (error as any)?.message?.includes('timeout')
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      onError: (error: any) => {
        console.error('获取插件 MCP 工具列表失败:', error)
      },
    },
  )
}

// 获取单个插件 MCP 工具
export const usePluginGetMcpTool = (request: PluginGetApiRequest, options?: { enabled?: boolean }) => {
  return useQuery(
    ['pluginMcpTool', request.space_id, request.plugin_id, request.tool_id],
    async () => {
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginMcpTool(request)
    },
    {
      enabled: (options?.enabled !== false) && !!request.space_id && !!request.plugin_id && !!request.tool_id,
      staleTime: 30 * 1000,
      cacheTime: 5 * 60 * 1000,
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      retry: (failureCount, error) => {
        if ((error as any)?.message?.includes('API client not initialized')) return false
        if (failureCount >= 3) return false
        return (error as any)?.message?.includes('Network Error') || (error as any)?.message?.includes('timeout')
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      onError: (error: any) => {
        console.error('获取插件 MCP 工具失败:', error)
      },
    },
  )
}

// 发现 MCP 工具（在创建插件后立即调用）
export const useDiscoverMcpTools = () => {
  return useMutation(
    (request: PluginDiscoverMcpToolsRequest): Promise<PluginDiscoverMcpToolsResponse> =>
      PluginService.discoverMcpTools(request),
    {
      onError: (error: any) => {
        console.error('MCP tool discovery failed:', error)
      },
    },
  )
}

// 插件 Code 相关的 React Query hooks

// 创建插件 Code
export const usePluginCreateCode = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginCreateCodeRequest) => PluginService.createPluginCode(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 创建成功后，使相关缓存失效
        queryClient.invalidateQueries(['pluginCodeList', variables.space_id, variables.plugin_id])
        console.log('插件 Code 创建成功')
      }
    },
    onError: error => {
      console.error('创建插件 Code 失败:', error)
    },
  })
}

// 更新插件 Code
export const usePluginUpdateCode = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginUpdateCodeRequest) => PluginService.updatePluginCode(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 更新成功后，使相关缓存失效
        queryClient.invalidateQueries(['pluginCode', variables.space_id, variables.plugin_id, variables.tool_id])
        queryClient.invalidateQueries(['pluginCodeList', variables.space_id, variables.plugin_id])
        console.log('插件 Code 更新成功')
      }
    },
    onError: error => {
      console.error('更新插件 Code 失败:', error)
    },
  })
}

// 删除插件 Code
export const usePluginDeleteCode = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginDeleteCodeRequest) => PluginService.deletePluginCode(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 删除成功后，使插件 Code 缓存失效
        queryClient.removeQueries(['pluginCode', variables.space_id, variables.plugin_id, variables.tool_id])
        queryClient.invalidateQueries(['pluginCodeList', variables.space_id, variables.plugin_id])
        console.log('插件 Code 删除成功')
      }
    },
    onError: error => {
      console.error('删除插件 Code 失败:', error)
    },
  })
}

// 获取插件 Code
export const usePluginGetCode = (request: PluginGetCodeRequest) => {
  return useQuery(
    ['pluginCode', request.space_id, request.plugin_id, request.tool_id],
    async () => {
      // Add a small delay to ensure API client is initialized
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginCode(request)
    },
    {
      enabled: !!request.space_id && !!request.plugin_id && !!request.tool_id,

      // 优化缓存策略
      staleTime: 30 * 1000, // 30秒内数据视为新鲜
      cacheTime: 5 * 60 * 1000, // 缓存5分钟

      // 添加自动刷新机制
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,

      // 重试策略
      retry: (failureCount, error) => {
        // Don't retry on API client initialization errors
        if (error?.message?.includes('API client not initialized')) {
          console.warn('API client not initialized, skipping retry for plugin code:', request.tool_id)
          return false
        }
        if (failureCount >= 3) return false
        return error?.message?.includes('Network Error') || error?.message?.includes('timeout')
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),

      // 错误处理
      onError: error => {
        console.error('获取插件 Code 失败:', error)
        const errorResponse = getErrorResponse(error)
        if (errorResponse?.status === 404) {
          console.warn(`插件 Code ${request.tool_id} 不存在或已被删除`)
        } else if (errorResponse?.status === 403) {
          console.warn(`没有权限访问插件 Code ${request.tool_id}`)
        }
      },
    },
  )
}

// 获取插件 Code 列表
export const usePluginListCode = (request: PluginListCodeRequest) => {
  return useQuery(
    ['pluginCodeList', request.space_id, request.plugin_id, request.page, request.size],
    async () => {
      // Add a small delay to ensure API client is initialized
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginCodeList(request)
    },
    {
      enabled: !!request.space_id && !!request.plugin_id,

      // 优化缓存策略
      staleTime: 30 * 1000, // 30秒内数据视为新鲜
      cacheTime: 5 * 60 * 1000, // 缓存5分钟

      // 添加自动刷新机制
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,

      // 重试策略
      retry: (failureCount, error) => {
        // Don't retry on API client initialization errors
        if (error?.message?.includes('API client not initialized')) {
          console.warn('API client not initialized, skipping retry for plugin code list:', request.plugin_id)
          return false
        }
        if (failureCount >= 3) return false
        return error?.message?.includes('Network Error') || error?.message?.includes('timeout')
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),

      // 错误处理
      onError: error => {
        console.error('获取插件 Code 列表失败:', error)
        if (error?.response?.status === 403) {
          console.warn(`没有权限访问插件 ${request.plugin_id} 的 Code 列表`)
        }
      },
    },
  )
}

// 执行插件
export const useExecutePlugin = () => {
  return useMutation(
    async ({
      request,
      onEvent,
      onError,
      onComplete,
    }: {
      request: PluginExecuteRequest
      onEvent: PluginExecutionEventHandler
      onError?: (error: Error) => void
      onComplete?: () => void
    }) => {
      return PluginService.executePlugin(request, onEvent, onError, onComplete)
    },
    {
      onSuccess: (closeConnection, variables) => {
        console.log(`插件执行已启动: ${variables.request.plugin_id}/${variables.request.tool_id}`)
        // closeConnection 是一个用于关闭SSE连接的函数
        // 在这里可以保存这个引用以便在需要时手动关闭连接
      },
      onSettled: (closeConnection, error, variables) => {
        if (error) {
          console.error(`插件执行失败: ${variables.request.plugin_id}/${variables.request.tool_id}`, error)
        } else {
          console.log(`插件执行完成: ${variables.request.plugin_id}/${variables.request.tool_id}`)
        }
      },
    },
  )
}

// Plugin Publish 相关的 React Query hooks

// 发布插件
export const usePluginPublish = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginPublishRequest) => PluginService.publishPlugin(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 发布成功后，使相关缓存失效
        queryClient.invalidateQueries(['pluginPublishList', variables.space_id])
        queryClient.invalidateQueries(['plugin', variables.plugin_id, variables.space_id])
        console.log('插件发布成功')
      }
    },
    onError: error => {
      console.error('插件发布失败:', error)
    },
  })
}

// 获取插件发布信息
export const usePluginPublishGet = (request: PluginPublishGetRequest) => {
  return useQuery(
    ['pluginPublish', request.space_id, request.plugin_id, request.plugin_version],
    async () => {
      // Add a small delay to ensure API client is initialized
      console.log('PluginPublishGetRequest:', request)
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginPublish(request)
    },
    {
      enabled: !!request.space_id && !!request.plugin_id,

      // 优化缓存策略
      staleTime: 30 * 1000, // 30秒内数据视为新鲜
      cacheTime: 5 * 60 * 1000, // 缓存5分钟

      // 添加自动刷新机制
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,

      // 重试策略
      retry: (failureCount, error) => {
        // Don't retry on API client initialization errors
        if (error?.message?.includes('API client not initialized')) {
          console.warn('API client not initialized, skipping retry for plugin publish:', request.plugin_id)
          return false
        }
        if (failureCount >= 3) return false
        const errorMessage = getErrorMessage(error)
        return errorMessage.includes('Network Error') || errorMessage.includes('timeout')
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),

      // 错误处理
      onError: error => {
        console.error('获取插件发布信息失败:', error)
        const errorResponse = getErrorResponse(error)
        if (errorResponse?.status === 404) {
          console.warn(`插件发布信息 ${request.plugin_id}/${request.version || 'latest'} 不存在`)
        } else if (errorResponse?.status === 403) {
          console.warn(`没有权限访问插件 ${request.plugin_id} 的发布信息`)
        }
      },
    },
  )
}

// 获取插件发布列表
export const usePluginPublishList = (request: PluginPublishListRequest, options?: { enabled?: boolean }) => {
  return useQuery(
    ['pluginPublishList', request.space_id, request.plugin_id],
    async () => {
      // Add a small delay to ensure API client is initialized
      await new Promise(resolve => setTimeout(resolve, 100))
      return PluginService.getPluginPublishList(request)
    },
    {
      enabled: options?.enabled !== false && !!request.space_id, // 只有当space_id存在时才执行查询，允许外部控制
      retry: (failureCount, error) => {
        // Don't retry on API client initialization errors
        if (error?.message?.includes('API client not initialized')) {
          return false
        }
        // Only retry on network errors, max 3 times
        if (failureCount >= 3) return false
        const errorMessage = getErrorMessage(error)
        return errorMessage.includes('Network Error') || errorMessage.includes('timeout')
      },

      // Set staleTime to 0 to ensure refetch always gets fresh data
      staleTime: 0, // 立即过期，确保每次refetch都获取最新数据
      cacheTime: 5 * 60 * 1000, // 缓存5分钟

      // 添加自动刷新机制
      refetchOnMount: true,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,

      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),

      // 错误处理
      onError: error => {
        console.error('获取插件发布列表失败:', error)
        if (error?.response?.status === 403) {
          console.warn(`没有权限访问空间 ${request.space_id} 的插件发布列表`)
        }
      },
    },
  )
}

// 删除插件发布
export const usePluginPublishDelete = () => {
  const queryClient = useQueryClient()

  return useMutation((request: PluginPublishDeleteRequest) => PluginService.deletePluginPublish(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 删除成功后，使插件发布缓存失效
        queryClient.removeQueries(['pluginPublish', variables.space_id, variables.plugin_id, variables.plugin_version])
        queryClient.invalidateQueries(['pluginPublishList', variables.space_id])
        console.log('插件发布删除成功')
      }
    },
    onError: error => {
      console.error('删除插件发布失败:', error)
    },
  })
}

// 获取插件市场数据
export const usePluginGetMarket = () => {
  return useMutation((request: PluginGetMarketRequest) => PluginService.getPluginMarket(request), {
    onSuccess: response => {
      if (response.code === 200) {
        console.log('插件市场数据获取成功')
      }
    },
    onError: error => {
      console.error('获取插件市场数据失败:', error)

      // 添加错误日志记录，便于调试
      const errorResponse = getErrorResponse(error)
      if (errorResponse?.status === 403) {
        console.warn('没有权限访问插件市场数据')
      } else if (errorResponse?.status === 404) {
        console.warn('插件市场数据不存在')
      }
    },
  })
}

export default {
  useCreatePlugin,
  usePlugin,
  usePluginList,
  useRefreshPlugin,
  useUpdatePlugin,
  useDeletePlugin,
  usePluginCreateApi,
  usePluginUpdateApi,
  usePluginDeleteApi,
  usePluginGetApi,
  usePluginListApi,
  usePluginListMcpTools,
  usePluginCreateCode,
  usePluginUpdateCode,
  usePluginDeleteCode,
  usePluginGetCode,
  usePluginListCode,
  useExecutePlugin,
  usePluginPublish,
  usePluginPublishGet,
  usePluginPublishList,
  usePluginPublishDelete,
  usePluginGetMarket,
}
