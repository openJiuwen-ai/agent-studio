import { useMutation, useQuery, useQueryClient } from 'react-query'
import { PromptService } from '../services/promptService'
import {
  CreatePromptRequest,
  UpdatePromptRequest,
  EditPromptBasicInfoRequest,
  DeletePromptRequest,
  SaveDraftRequest,
  CommitVersionRequest,
  RevertToVersionRequest,
  GetVersionListRequest,
  ClonePromptRequest,
  SaveDebugContextRequest,
} from '../types/promptTypes'

// 提示词相关的React Query hooks

// 获取提示词列表
export const usePromptList = (params?: {
  page?: number
  pageSize?: number
  search?: string
  key_word?: string
  category?: string
  tags?: string[]
  isPublic?: boolean
  workspaceId?: string
}) => {
  return useQuery(['prompts', 'list', params?.workspaceId, params?.page, params?.pageSize, params?.key_word], () => PromptService.getPrompts(params), {
    enabled: !!params?.workspaceId, // 只有当workspaceId存在时才执行查询
    staleTime: 2 * 60 * 1000, // 2分钟内不重新获取
    cacheTime: 5 * 60 * 1000, // 缓存5分钟
    retry: 2,
    retryDelay: 1000,
    onError: (error: any) => {
      console.error('获取提示词列表失败:', error)
    },
  })
}

// 获取提示词详情
export const usePromptDetail = (
  promptId?: string,
  options?: {
    withCommit?: boolean
    withDraft?: boolean
    withDefaultConfig?: boolean
    workspaceId?: string
  },
) => {
  return useQuery(
    ['prompts', 'detail', promptId, options?.withCommit, options?.withDraft, options?.withDefaultConfig],
    () => PromptService.getPromptDetail(promptId!, options),
    {
      enabled: !!promptId, // 只有当promptId存在时才执行查询
      staleTime: 5 * 60 * 1000, // 5分钟内不重新获取
      cacheTime: 10 * 60 * 1000, // 缓存10分钟
      retry: 2,
      retryDelay: 1000,
      onError: (error: any) => {
        console.error('获取提示词详情失败:', error)
      },
    },
  )
}

// 创建提示词
export const useCreatePrompt = () => {
  const queryClient = useQueryClient()

  return useMutation((request: CreatePromptRequest) => PromptService.createPrompt(request), {
    onSuccess: (response: any, variables) => {
      if (response.code === 0) {
        // 创建成功后，使提示词列表缓存失效，触发重新获取
        queryClient.invalidateQueries(['prompts', 'list', variables.workspace_id])
        console.log('提示词创建成功')
      }
    },
    onError: (error: any) => {
      console.error('创建提示词失败:', error)
    },
  })
}

// 编辑提示词基本信息
export const useEditPromptBasicInfo = () => {
  const queryClient = useQueryClient()

  return useMutation(
    ({ promptId, workspaceId, data }: { promptId: string; workspaceId: string; data: { prompt_name: string; prompt_description: string } }) =>
      PromptService.editPromptBasicInfo(promptId, workspaceId, data),
    {
      onSuccess: (response: any, variables) => {
        if (response.code === 0) {
          // 编辑成功后，使提示词列表和详情缓存失效
          queryClient.invalidateQueries(['prompts', 'list', variables.workspaceId])
          queryClient.invalidateQueries(['prompts', 'detail', variables.promptId])
          console.log('提示词基本信息编辑成功')
        }
      },
      onError: (error: any) => {
        console.error('编辑提示词基本信息失败:', error)
      },
    },
  )
}

// 删除提示词
export const useDeletePrompt = () => {
  const queryClient = useQueryClient()

  return useMutation(
    ({ promptId, workspaceId }: { promptId: string; workspaceId: string }) => PromptService.deletePrompt(promptId, workspaceId),
    {
      onSuccess: (response: any, variables) => {
        if (response.code === 0) {
          // 删除成功后，使提示词列表缓存失效
          queryClient.invalidateQueries(['prompts', 'list'])
          queryClient.invalidateQueries(['prompts', 'detail', variables.promptId])
          console.log('提示词删除成功')
        }
      },
      onError: (error: any) => {
        console.error('删除提示词失败:', error)
      },
    },
  )
}

// 保存草稿
export const useSaveDraft = () => {
  const queryClient = useQueryClient()

  return useMutation(
    ({ promptId, spaceId, editorData }: { promptId: string; spaceId: string; editorData: any }) =>
      PromptService.saveDraft(promptId, spaceId, editorData),
    {
      onSuccess: (response: any, variables) => {
        if (response.code === 0) {
          // 保存成功后，使提示词详情缓存失效，触发重新获取
          queryClient.invalidateQueries(['prompts', 'detail', variables.promptId])
          console.log('草稿保存成功')
        }
      },
      onError: (error: any) => {
        console.error('保存草稿失败:', error)
      },
    },
  )
}

// 提交版本
export const useCommitVersion = () => {
  const queryClient = useQueryClient()

  return useMutation(
    ({ promptId, workspaceId, data }: { promptId: string; workspaceId: string; data: CommitVersionRequest }) =>
      PromptService.commitVersion(promptId, workspaceId, data),
    {
      onSuccess: (response: any, variables) => {
        if (response.code === 0) {
          // 提交成功后，使相关缓存失效
          queryClient.invalidateQueries(['prompts', 'detail', variables.promptId])
          queryClient.invalidateQueries(['prompts', 'versions', variables.promptId, variables.workspaceId])
          console.log('版本提交成功')
        }
      },
      onError: (error: any) => {
        console.error('提交版本失败:', error)
      },
    },
  )
}

// 还原版本
export const useRevertToVersion = () => {
  const queryClient = useQueryClient()

  return useMutation(
    ({ promptId, workspaceId, data }: { promptId: string; workspaceId: string; data: RevertToVersionRequest }) =>
      PromptService.revertToVersion(promptId, workspaceId, data),
    {
      onSuccess: (response: any, variables) => {
        if (response.code === 0) {
          // 还原成功后，使相关缓存失效
          queryClient.invalidateQueries(['prompts', 'detail', variables.promptId])
          queryClient.invalidateQueries(['prompts', 'versions', variables.promptId, variables.workspaceId])
          console.log('版本还原成功')
        }
      },
      onError: (error: any) => {
        console.error('还原版本失败:', error)
      },
    },
  )
}

// 获取版本列表
export const usePromptVersionList = (promptId?: string, workspaceId?: string, params?: GetVersionListRequest) => {
  return useQuery(['prompts', 'versions', promptId, workspaceId, params?.page_size], () => PromptService.getVersionList(promptId!, workspaceId!, params), {
    enabled: !!promptId && !!workspaceId, // 只有当 promptId 和 workspaceId 存在时才执行查询
    staleTime: 1 * 60 * 1000, // 1分钟内不重新获取
    cacheTime: 5 * 60 * 1000, // 缓存5分钟
    retry: 2,
    retryDelay: 1000,
    onError: (error: any) => {
      console.error('获取版本列表失败:', error)
    },
  })
}

// 克隆提示词
export const useClonePrompt = () => {
  const queryClient = useQueryClient()

  return useMutation(({ promptId, data }: { promptId: string; data: ClonePromptRequest }) => PromptService.clonePrompt(promptId, data), {
    onSuccess: (response: any, variables) => {
      if (response.code === 0) {
        // 克隆成功后，使提示词列表缓存失效
        queryClient.invalidateQueries(['prompts', 'list', variables.data.workspace_id])
        console.log('提示词克隆成功')
      }
    },
    onError: (error: any) => {
      console.error('克隆提示词失败:', error)
    },
  })
}
