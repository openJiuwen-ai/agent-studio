import { getApiClient } from '../utils/apiClientFactory'
import { API_ENDPOINTS } from '../config'
import type {
  TraceListRequest,
  TraceListResponse,
  TraceSpan,
  TraceRecord,
  TraceFilterParams,
  TraceApiError,
  TraceTreeRequest,
  TraceTreeResponse,
  TraceTreeSpan,
  TraceTreeNode,
} from '../types/traceTypes'

/**
 * Trace API 服务类
 */
export class TraceService {
  /**
   * 获取Trace列表
   * @param params 查询参数
   * @returns Promise<TraceListResponse>
   */
  static async getTraceList(params: TraceListRequest): Promise<TraceListResponse> {
    try {
      const response = await getApiClient().post<TraceListResponse>(API_ENDPOINTS.OBSERVABILITY.TRACE_LIST, params)
      return response.data
    } catch (error) {
      console.error('获取Trace列表失败:', error)
      throw error
    }
  }

  /**
   * 获取调用树信息
   * @param params 查询参数（workspace_id必需，debug_id或trace_id可选其一，start_time和end_time可选）
   * @returns Promise<TraceTreeResponse>
   */
  static async getTraceTree(params: TraceTreeRequest): Promise<TraceTreeResponse> {
    try {
      const response = await getApiClient().post<TraceTreeResponse>(API_ENDPOINTS.OBSERVABILITY.TRACE_TREE, params)
      return response.data
    } catch (error) {
      console.error('获取调用树信息失败:', error)
      throw error
    }
  }

  /**
   * 构建调用树结构
   * @param spans API返回的spans数据
   * @returns TraceTreeNode | null 返回根节点
   */
  static buildTraceTree(spans: TraceTreeSpan[]): TraceTreeNode | null {
    if (!spans || spans.length === 0) {
      return null
    }

    // 创建span_id到span的映射
    const spanMap = new Map<string, TraceTreeSpan>()
    spans.forEach(span => {
      spanMap.set(span.span_id, span)
    })

    // 创建节点映射
    const nodeMap = new Map<string, TraceTreeNode>()
    spans.forEach(span => {
      nodeMap.set(span.span_id, {
        span,
        children: [],
        level: 0,
      })
    })

    // 找到根节点并构建树结构
    let rootNode: TraceTreeNode | null = null
    spans.forEach(span => {
      const currentNode = nodeMap.get(span.span_id)
      if (!currentNode) return

      if (span.parent_id === '0' || span.parent_id === '') {
        // 这是根节点
        rootNode = currentNode
      } else {
        // 找到父节点并添加为子节点
        const parentNode = nodeMap.get(span.parent_id)
        if (parentNode) {
          currentNode.level = parentNode.level + 1
          parentNode.children.push(currentNode)
        }
      }
    })

    return rootNode
  }

  /**
   * 获取调用树的根节点信息（用于标题栏）
   * @param spans API返回的spans数据
   * @returns TraceTreeSpan | null 返回根节点span
   */
  static getRootSpan(spans: TraceTreeSpan[]): TraceTreeSpan | null {
    if (!spans || spans.length === 0) {
      return null
    }

    return spans.find(span => span.parent_id === '0' || span.parent_id === '') || null
  }

  /**
   * 扁平化调用树（用于展示）
   * @param rootNode 根节点
   * @returns TraceTreeNode[] 扁平化后的节点数组
   */
  static flattenTraceTree(rootNode: TraceTreeNode | null): TraceTreeNode[] {
    if (!rootNode) {
      return []
    }

    const result: TraceTreeNode[] = []
    const traverse = (node: TraceTreeNode) => {
      result.push(node)
      node.children.forEach(child => traverse(child))
    }

    traverse(rootNode)
    return result
  }

  /**
   * 转换API响应数据为页面显示格式
   * @param spans API返回的spans数据
   * @returns TraceRecord[]
   */
  static transformSpansToRecords(spans: TraceSpan[]): TraceRecord[] {
    return spans.map(span => ({
      traceId: span.trace_id,
      input: span.input !== undefined ? span.input : '-',
      output: span.output !== undefined ? span.output : '-',
      tokens: span.custom_tags.tokens ? parseInt(span.custom_tags.tokens, 10) : '-',
      latency: parseInt(span.duration, 10),
      latencyFirstResp: parseInt(span.custom_tags.latency_first_resp || '0', 10),
      startTime: this.formatTimestamp(span.started_at),
      feedback: null, // 暂时都置为null，后续可根据实际业务逻辑设置
      inputTokens: span.custom_tags.input_tokens ? parseInt(span.custom_tags.input_tokens, 10) : '-',
      outputTokens: span.custom_tags.output_tokens ? parseInt(span.custom_tags.output_tokens, 10) : '-',
      spanId: span.span_id,
      spanType: span.span_type,
      spanName: span.span_name,
      promptKey: span.custom_tags.prompt_key || '-',
      workflow: span.custom_tags.workflow_name || '-', // 从custom_tags.workflow_name获取工作流名称
      agent: span.custom_tags.bot_name || '-', // 从custom_tags.bot_name获取智能体名称
      app: '-', // 应用暂时都置为-
      expirationTime: this.formatTimestamp(span.logic_delete_date),
      status: this.mapStatus(span.status),
    }))
  }

  /**
   * 映射API的status到页面显示的status
   * @param apiStatus API返回的status
   * @returns 页面显示的status
   */
  private static mapStatus(apiStatus: string): 'success' | 'failed' | 'pending' {
    switch (apiStatus) {
      case 'success':
        return 'success'
      case 'failed':
        return 'failed'
      case 'pending':
        return 'pending'
      default:
        return 'pending'
    }
  }

  /**
   * 格式化时间戳
   * @param timestamp 时间戳字符串
   * @returns 格式化后的时间字符串
   */
  private static formatTimestamp(timestamp: string): string {
    try {
      const date = new Date(parseInt(timestamp, 10))
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch (error) {
      console.warn('时间戳格式化失败:', timestamp, error)
      return timestamp
    }
  }

  /**
   * 转换筛选参数为API请求参数
   * @param filterParams 页面筛选参数
   * @param workspaceId 工作空间ID
   * @returns TraceListRequest
   */
  static convertFilterToApiParams(filterParams: TraceFilterParams, workspaceId: string): TraceListRequest {
    const { timeRange, customTimeStart, customTimeEnd, spanType, dataSource } = filterParams

    // 计算时间范围
    let startTime: string
    let endTime: string

    if (timeRange === '自定义' && customTimeStart && customTimeEnd) {
      startTime = new Date(customTimeStart).getTime().toString()
      endTime = new Date(customTimeEnd).getTime().toString()
    } else {
      const now = new Date()
      const { start, end } = this.calculateTimeRange(timeRange, now)
      startTime = start.getTime().toString()
      endTime = end.getTime().toString()
    }

    // 直接使用API值，无需映射
    const spanListType = spanType as 'root_span' | 'all_span' | 'llm_span'
    const platformType = dataSource as 'all' | 'prompt' | 'workflow' | 'bot' | 'project' | 'sdk'

    return {
      workspace_id: workspaceId,
      start_time: startTime,
      end_time: endTime,
      page_size: 30,
      platform_type: platformType,
      span_list_type: spanListType,
      order_bys: [
        {
          field: 'start_time',
          is_asc: false
        }
      ]
    }
  }

  /**
   * 计算时间范围
   * @param timeRange 时间范围选项
   * @param now 当前时间
   * @returns 开始和结束时间
   */
  private static calculateTimeRange(timeRange: string, now: Date): { start: Date; end: Date } {
    const end = new Date(now)
    const start = new Date(now)

    switch (timeRange) {
      case '过去1小时':
        start.setHours(start.getHours() - 1)
        break
      case '过去3小时':
        start.setHours(start.getHours() - 3)
        break
      case '过去1天':
        start.setDate(start.getDate() - 1)
        break
      case '过去3天':
        start.setDate(start.getDate() - 3)
        break
      case '过去7天':
        start.setDate(start.getDate() - 7)
        break
      case '过去15天':
        start.setDate(start.getDate() - 15)
        break
      case '过去30天':
        start.setDate(start.getDate() - 30)
        break
      case '过去180天':
        start.setDate(start.getDate() - 180)
        break
      case '过去1年':
        start.setFullYear(start.getFullYear() - 1)
        break
      default:
        start.setHours(start.getHours() - 1)
    }

    return { start, end }
  }
}

// 导出服务实例
export const traceService = TraceService
