import { useMutation, useQuery, useQueryClient } from 'react-query'
import WorkflowService from '../services/workflowService'
import {
  WorkflowListRequest,
  CreateWorkflowRequest,
  WorkflowCanvasRequest,
  WorkflowSaveRequest,
  DeleteWorkflowRequest,
  CopyWorkflowRequest,
  UpdateWorkflowRequest,
  WorkflowUpdateResponse,
  WorkflowSearchRequest,
} from '../types'

// 工作流相关的React Query hooks

// 从API获取工作流列表
export const useWorkflows = (request: WorkflowListRequest) => {
  return useQuery(['workflows', 'api', 'list', request], () => WorkflowService.getWorkflows(request), {
    enabled: !!request.space_id, // 只有当space_id存在时才执行查询

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
      console.error('从API获取工作流列表失败:', error)
    },

    // 🎯 成功回调，用于调试
    onSuccess: data => {
      console.log(`成功获取 space_id ${request.space_id} 的工作流列表，共 ${data.data?.workflow_list?.length || 0} 个工作流`)
    },
  })
}

// 刷新工作流列表
export const useRefreshWorkflows = () => {
  const queryClient = useQueryClient()

  return useMutation((request: WorkflowListRequest) => WorkflowService.getWorkflows(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 刷新成功后，更新缓存
        queryClient.setQueryData(['workflows', 'api', 'list', variables], response)
        console.log('工作流列表刷新成功')
      }
    },
    onError: error => {
      console.error('刷新工作流列表失败:', error)
    },
  })
}

// 创建工作流
export const useCreateWorkflow = () => {
  const queryClient = useQueryClient()

  return useMutation((request: CreateWorkflowRequest) => WorkflowService.createWorkflow(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 创建成功后，使工作流列表缓存失效，触发重新获取
        queryClient.invalidateQueries(['workflows', 'api', 'list'], { predicate: query => query.queryKey[3]?.space_id === variables.space_id })
        console.log('工作流创建成功')
      }
    },
    onError: error => {
      console.error('创建工作流失败:', error)
    },
  })
}

// 获取工作流画布
export const useWorkflowCanvas = (request: WorkflowCanvasRequest) => {
  return useQuery(['workflows', 'canvas', request.workflow_id, request.space_id, request.version], () => WorkflowService.getWorkflowCanvas(request), {
    enabled: !!request.workflow_id && !!request.space_id, // 只有当workflow_id和space_id都存在时才执行查询

    // 🎯 优化缓存策略：减少不必要的网络请求
    staleTime: 5 * 60 * 1000, // 5分钟内数据视为新鲜
    cacheTime: 10 * 60 * 1000, // 缓存10分钟

    // 🎯 简化刷新机制，避免过度请求
    refetchOnMount: false, // 不在挂载时强制刷新
    refetchOnWindowFocus: false, // 不在窗口聚焦时刷新
    refetchOnReconnect: true, // 只在网络重连时刷新

    // 🎯 简化重试策略
    retry: 2, // 最多重试2次
    retryDelay: 1000, // 固定1秒延迟

    // 🎯 错误处理
    onError: error => {
      console.error('获取工作流画布失败:', error)

      // 🎯 添加错误日志记录，便于调试
      if (error?.response?.status === 404) {
        console.warn(`工作流 ${request.workflow_id} 不存在或已被删除`)
      } else if (error?.response?.status === 403) {
        console.warn(`没有权限访问工作流 ${request.workflow_id}`)
      }
    },

    // 🎯 成功回调，用于调试
    onSuccess: data => {
      console.log(`成功获取工作流 ${request.workflow_id} 的画布数据，更新时间:`, data?.data?.workflow?.updated_at)
    },
  })
}

// 刷新工作流画布
export const useRefreshWorkflowCanvas = () => {
  const queryClient = useQueryClient()

  return useMutation((request: WorkflowCanvasRequest) => WorkflowService.getWorkflowCanvas(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 刷新成功后，更新缓存，包含version参数
        queryClient.invalidateQueries(['workflows', 'canvas', variables.workflow_id, variables.space_id, variables.version])
        console.log('工作流画布刷新成功')
      }
    },
    onError: error => {
      console.error('刷新工作流画布失败:', error)
    },
  })
}

// 保存工作流
export const useSaveWorkflow = () => {
  const queryClient = useQueryClient()

  return useMutation((request: WorkflowSaveRequest) => WorkflowService.saveWorkflow(request), {
    // 🎯 乐观更新：在发送请求前更新缓存
    onMutate: async variables => {
      // 取消正在进行的查询，避免竞争条件，包含version参数以匹配查询键
      await queryClient.cancelQueries(['workflows', 'canvas', variables.workflow_id, variables.space_id])

      // 获取当前缓存数据的快照
      const previousData = queryClient.getQueryData(['workflows', 'canvas', variables.workflow_id, variables.space_id])

      // 从schema中提取工作流名称
      const schemaData = JSON.parse(variables.schema)
      const workflowName = schemaData?.name || previousData?.data?.workflow?.name || `工作流-${variables.workflow_id}`

      // 乐观更新：立即更新缓存以提供即时反馈
      queryClient.setQueryData(['workflows', 'canvas', variables.workflow_id, variables.space_id], {
        ...previousData,
        data: {
          workflow: {
            ...previousData?.data?.workflow,
            name: workflowName, // 使用schema中的名称
            schema: variables.schema,
            updated_at: new Date().toISOString(),
          },
        },
      })

      // 返回之前的数据以便在出错时回滚
      return { previousData }
    },

    // 🎯 如果保存失败，回滚到之前的数据
    onError: (error, variables, context) => {
      console.error('保存工作流失败:', error)

      if (context?.previousData) {
        // 恢复之前的缓存数据
        queryClient.setQueryData(['workflows', 'canvas', variables.workflow_id, variables.space_id], context.previousData)
      }
    },

    // 🎯 保存成功后，确保数据同步
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        console.log('工作流保存成功')

        // 立即更新缓存，确保下次进入编辑器显示最新数据
        queryClient.setQueryData(['workflows', 'canvas', variables.workflow_id, variables.space_id], {
          ...response,
          data: {
            workflow: {
              ...response.data.workflow,
              name: response.data.name, // 使用后端返回的工作流名称
              schema: variables.schema, // 使用最新保存的 schema
              updated_at: new Date().toISOString(),
            },
          },
        })

        // 🎯 强制清除工作流画布缓存，确保重新进入时获取最新数据
        queryClient.invalidateQueries(['workflows', 'canvas', variables.workflow_id, variables.space_id])

        // 🎯 更新工作流列表缓存，确保列表显示最新信息
        queryClient.invalidateQueries(['workflows', 'api', 'list'], { predicate: query => query.queryKey[3]?.space_id === variables.space_id })

        console.log('工作流保存成功，画布和列表缓存已刷新')
      }
    },
  })
}

// 删除工作流
export const useDeleteWorkflow = () => {
  const queryClient = useQueryClient()

  return useMutation((request: DeleteWorkflowRequest) => WorkflowService.deleteWorkflow(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 删除成功后，使工作流列表缓存失效，触发重新获取
        queryClient.invalidateQueries(['workflows', 'api', 'list'], { predicate: query => query.queryKey[3]?.space_id === variables.space_id })
        console.log('工作流删除成功')
      }
    },
    onError: error => {
      console.error('删除工作流失败:', error)
    },
  })
}

// 更新工作流
export const useUpdateWorkflow = () => {
  const queryClient = useQueryClient()

  return useMutation((request: UpdateWorkflowRequest) => WorkflowService.updateWorkflow(request), {
    onSuccess: (response: WorkflowUpdateResponse, variables) => {
      if (response.code === 200) {
        // 更新成功后，使工作流列表缓存失效，触发重新获取
        queryClient.invalidateQueries(['workflows', 'api', 'list'], { predicate: query => query.queryKey[3]?.space_id === variables.space_id })
        console.log('工作流更新成功')
        // 可以在这里添加成功提示
        return { success: true, message: response.message }
      }
    },
    onError: error => {
      console.error('更新工作流失败:', error)
      // 可以在这里添加失败提示
      return { success: false, message: '更新工作流失败，请稍后重试' }
    },
  })
}

// 复制工作流
export const useCopyWorkflow = () => {
  const queryClient = useQueryClient()

  return useMutation((request: CopyWorkflowRequest) => WorkflowService.copyWorkflow(request), {
    onSuccess: (response, variables) => {
      if (response.code === 200) {
        // 复制成功后，使工作流列表缓存失效，触发重新获取
        queryClient.invalidateQueries(['workflows', 'api', 'list'], { predicate: query => query.queryKey[3]?.space_id === variables.space_id })
        console.log('工作流复制成功')
      }
    },
    onError: error => {
      console.error('复制工作流失败:', error)
    },
  })
}

// 搜索工作流
export const useSearchWorkflows = (request: WorkflowSearchRequest, options?: { enabled?: boolean }) => {
  return useQuery(['workflows', 'search', request], () => WorkflowService.searchWorkflows(request), {
    enabled: options?.enabled !== false && !!request.space_id && request.search_term.trim() !== '', // 只有当enabled为true且space_id存在且有搜索词时才执行查询

    // 🎯 禁用缓存，确保搜索、排序、过滤时都重新请求
    staleTime: 0, // 数据立即过期，每次参数改变时都重新请求
    cacheTime: 3 * 60 * 1000, // 保留缓存时间用于内存管理（组件卸载后保留3分钟）

    // 🎯 搜索优化的自动刷新机制
    refetchOnMount: true, // 组件挂载时重新获取数据
    refetchOnWindowFocus: false, // 窗口聚焦时不刷新搜索结果（避免干扰用户操作）
    refetchOnReconnect: true, // 网络重连时刷新

    // 🎯 搜索特定的重试策略
    retry: 1, // 搜索只重试1次，避免用户等待过久
    retryDelay: 1000,

    // 🎯 搜索错误处理
    onError: error => {
      console.error('搜索工作流失败:', error)
    },

    onSuccess: data => {
      console.log(`成功搜索工作流，共 ${data.data?.workflow_list?.length || 0} 个结果`)
    },
  })
}

export default {
  useWorkflows,
  useRefreshWorkflows,
  useCreateWorkflow,
  useWorkflowCanvas,
  useRefreshWorkflowCanvas,
  useSaveWorkflow,
  useUpdateWorkflow,
  useDeleteWorkflow,
  useCopyWorkflow,
  useSearchWorkflows,
}
