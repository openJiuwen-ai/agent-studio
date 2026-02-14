import { API_ENDPOINTS } from '../config'
import { stream } from '../utils/apiClientFactory'
import {
  OptimizeFeedbackRequest,
  OptimizeBadcaseRequest,
  QuickOptimizeRequest,
  OptimizeResponse,
  StreamDataCallback,
  StreamErrorCallback,
  StreamCompleteCallback,
} from '../types/feedbackOptTypes'

/**
 * 反馈优化管理服务类
 *
 * 支持三种反馈优化场景：
 * 1. 全文反馈优化（feedback）：在编辑提示词页面右上角点击全文反馈优化按钮，完全覆盖提示词内容
 * 2. 插入反馈优化（insert）：用户光标停留1秒后出现插入反馈优化按钮，在光标位置插入优化内容
 * 3. 选中反馈优化（select）：用户选中文本后出现选中反馈优化按钮，替换选中的内容
 */
export class FeedbackOptService {
  /**
   * 反馈优化API调用 - 支持三种优化模式
   *
   * 支持的优化模式：
   * 1. 'general' - 全文反馈优化：完全覆盖提示词内容，不需要传递位置参数
   * 2. 'insert' - 插入反馈优化：在光标位置插入内容，需要传递 start_pos
   * 3. 'select' - 选中反馈优化：替换选中的内容，需要传递 start_pos 和 end_pos
   *
   * @param request 反馈优化请求参数
   * @param workspaceId 工作空间ID
   */
  static async optimizeFeedback(
    request: OptimizeFeedbackRequest,
    workspaceId: string,
    onData: StreamDataCallback,
    onError?: StreamErrorCallback,
    onComplete?: StreamCompleteCallback,
    abortController?: AbortController,
  ): Promise<void> {
    return this.callStreamAPI(
      API_ENDPOINTS.FEEDBACK_OPTIMIZATION.OPTIMIZE_FEEDBACK,
      { ...request, workspace_id: workspaceId },
      onData,
      onError,
      onComplete,
      abortController,
    )
  }

  /**
   * 快捷优化API调用
   * 用于编辑提示词页面右上角的快捷优化按钮
   * 流式输出优化结果
   * @param request 快捷优化请求参数
   * @param workspaceId 工作空间ID
   */
  static async quickOptimize(
    request: QuickOptimizeRequest,
    workspaceId: string,
    onData: StreamDataCallback,
    onError?: StreamErrorCallback,
    onComplete?: StreamCompleteCallback,
    abortController?: AbortController,
  ): Promise<void> {
    return this.callStreamAPI(
      API_ENDPOINTS.FEEDBACK_OPTIMIZATION.QUICK_OPTIMIZE,
      { ...request, workspace_id: workspaceId },
      onData,
      onError,
      onComplete,
      abortController,
    )
  }

  /**
   * 调用badcase优化API（流式）
   * @param request badcase优化请求参数
   * @param workspaceId 工作空间ID
   */
  static async optimizeBadcase(
    request: OptimizeBadcaseRequest,
    workspaceId: string,
    onData: StreamDataCallback,
    onError?: StreamErrorCallback,
    onComplete?: StreamCompleteCallback,
    abortController?: AbortController,
  ): Promise<void> {
    return this.callStreamAPI(
      API_ENDPOINTS.FEEDBACK_OPTIMIZATION.OPTIMIZE_BADCASE,
      { ...request, workspace_id: workspaceId },
      onData,
      onError,
      onComplete,
      abortController,
    )
  }

  // 核心的流式API调用方法
  private static async callStreamAPI(
    endpoint: string,
    request: QuickOptimizeRequest | OptimizeFeedbackRequest | OptimizeBadcaseRequest,
    onData: StreamDataCallback,
    onError?: StreamErrorCallback,
    onComplete?: StreamCompleteCallback,
    abortController?: AbortController,
  ): Promise<void> {
    return stream<OptimizeResponse | any>(endpoint, request, {
      onData: (response: OptimizeResponse | any) => {
        // 如果响应包含错误信息但没有content，直接调用错误回调，而不是转换为字符串传递
        if ((response.error || (response.code && response.code !== 200 && response.code !== 0)) && !response.content) {
          // 提取错误信息并调用错误回调
          const errorMessage = response.message || response.msg || (typeof response.error === 'string' ? response.error : '未知错误')
          console.log('🔍 [feedbackOptService] :', errorMessage)
          if (onError) {
            onError(errorMessage)
          }
          return
        }

        // 只发送content字段的内容
        if (response.content !== undefined && response.content !== null) {
          onData(response.content)
        }
      },
      onError,
      onComplete,
      abortController,
      parseData: (line: string): OptimizeResponse | null => {
        // 统一的解析逻辑，处理流式格式
        if (line.startsWith('data: ')) {
          // 处理 Server-Sent Events 格式
          const contentStr = line.substring(6) // 移除 'data: ' 前缀

          // 尝试解析为JSON
          try {
            return JSON.parse(contentStr) as OptimizeResponse
          } catch (e) {
            // 如果不是JSON格式，直接作为纯文本内容处理
            return { content: contentStr }
          }
        } else {
          // 尝试直接解析为JSON
          try {
            return JSON.parse(line) as OptimizeResponse
          } catch (e) {
            // 如果不是JSON格式，可能是纯文本content
            if (!line.startsWith('data:') && !line.startsWith('{')) {
              return { content: line }
            }
            return null
          }
        }
      },
    })
  }
}
