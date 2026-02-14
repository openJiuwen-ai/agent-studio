import { useMutation } from 'react-query'
import { FeedbackOptService } from '../services/feedbackOptService'
import {
  OptimizeFeedbackRequest,
  OptimizeBadcaseRequest,
  QuickOptimizeRequest,
  StreamDataCallback,
  StreamErrorCallback,
  StreamCompleteCallback,
} from '../types/feedbackOptTypes'

// 反馈优化相关的React Query hooks

// 反馈优化 - 支持所有模式
export const useOptimizeFeedback = () => {
  return useMutation(
    ({
      request,
      workspaceId,
      onData,
      onError,
      onComplete,
    }: {
      request: OptimizeFeedbackRequest
      workspaceId: string
      onData: StreamDataCallback
      onError?: StreamErrorCallback
      onComplete?: StreamCompleteCallback
    }) => FeedbackOptService.optimizeFeedback(request, workspaceId, onData, onError, onComplete),
    {
      onError: (error: any) => {
        console.error('反馈优化失败:', error)
      },
    },
  )
}

// 快捷优化
export const useQuickOptimize = () => {
  return useMutation(
    ({
      request,
      workspaceId,
      onData,
      onError,
      onComplete,
    }: {
      request: QuickOptimizeRequest
      workspaceId: string
      onData: StreamDataCallback
      onError?: StreamErrorCallback
      onComplete?: StreamCompleteCallback
    }) => FeedbackOptService.quickOptimize(request, workspaceId, onData, onError, onComplete),
    {
      onError: (error: any) => {
        console.error('快捷优化失败:', error)
      },
    },
  )
}

// Badcase优化
export const useOptimizeBadcase = () => {
  return useMutation(
    ({
      request,
      workspaceId,
      onData,
      onError,
      onComplete,
    }: {
      request: OptimizeBadcaseRequest
      workspaceId: string
      onData: StreamDataCallback
      onError?: StreamErrorCallback
      onComplete?: StreamCompleteCallback
    }) => FeedbackOptService.optimizeBadcase(request, workspaceId, onData, onError, onComplete),
    {
      onError: (error: any) => {
        console.error('Badcase优化失败:', error)
      },
    },
  )
}
