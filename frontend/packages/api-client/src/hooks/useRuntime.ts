import { useMutation, useQuery, useQueryClient } from 'react-query'
import RuntimeService from '../services/runtime'
import { RuntimeDeployRequest, RuntimeDetailRequest, RuntimeRemoveRequest, RuntimeResetConversationRequest } from '../types'

// Runtime 相关的 React Query hooks
const isSuccessCode = (code: unknown) => Number(code) === 200

type RuntimeResponseLike = {
  code?: number | string
  message?: string
}

const getResponseMessage = (response: RuntimeResponseLike | undefined) => response?.message || '请求失败'

// 查询运行时部署详情
export const useRuntimeDetail = (request: RuntimeDetailRequest, options?: { enabled?: boolean }) => {
  return useQuery(
    ['runtime', 'detail', request.agent_id, request.space_id],
    async () => {
      const response = await RuntimeService.detail(request)
      if (!isSuccessCode(response.code)) {
        throw new Error(getResponseMessage(response))
      }
      return response
    },
    {
    enabled: options?.enabled !== false && !!request.agent_id && !!request.space_id,
    staleTime: 0,
    cacheTime: 0,
    retry: 2,
    retryDelay: 1000,
    onError: error => {
      console.error('获取运行时部署详情失败:', error)
    },
    }
  )
}

// 部署运行时
export const useDeployRuntime = () => {
  const queryClient = useQueryClient()

  return useMutation(async (request: RuntimeDeployRequest) => {
    const response = await RuntimeService.deploy(request)
    if (!isSuccessCode(response.code)) {
      throw new Error(getResponseMessage(response))
    }
    return response
  }, {
    onSuccess: (_response, variables) => {
      queryClient.invalidateQueries(['runtime', 'detail', variables.agent_id, variables.space_id])
    },
    onError: error => {
      console.error('部署运行时失败:', error)
    },
  })
}

// 下架运行时
export const useRemoveRuntime = () => {
  const queryClient = useQueryClient()

  return useMutation(async (request: RuntimeRemoveRequest) => {
    const response = await RuntimeService.remove(request)
    if (!isSuccessCode(response.code)) {
      throw new Error(getResponseMessage(response))
    }
    return response
  }, {
    onSuccess: (_response, variables) => {
      queryClient.removeQueries(['runtime', 'detail', variables.agent_id, variables.space_id], { exact: true })
    },
    onError: error => {
      console.error('下架运行时失败:', error)
    },
  })
}

// 重置运行时会话
export const useResetConversation = () => {
  return useMutation(async (request: RuntimeResetConversationRequest) => {
    const response = await RuntimeService.resetConversation(request)
    if (!isSuccessCode(response.code)) {
      throw new Error(getResponseMessage(response))
    }
    return response
  }, {
    onError: error => {
      console.error('重置会话失败:', error)
    },
  })
}

export default {
  useRuntimeDetail,
  useDeployRuntime,
  useRemoveRuntime,
  useResetConversation,
}
