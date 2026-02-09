import { getApiClient, getToken, getAcceptLanguage } from '../utils/apiClientFactory'
import { API_ENDPOINTS } from '../config'
import {
  WorkflowExecutionRequest,
  WorkflowUserInputRequest,
  WorkflowCancelRequest,
  WorkflowCancelResponse,
  WorkflowExecutionEvent,
  AgentExecutionEvent,
  WorkflowExecutionEventHandler,
  ComponentExecuteRequest,
  ComponentExecuteResponse,
  ComponentCancelRequest,
  ComponentCancelResponse,
  SSEMessage,
  SSEData,
  interactionPayload,
} from '../types'

// 消息处理器接口 - 策略模式
interface MessageProcessor {
  processData(dataStr: string): { sseMessage: SSEMessage; messageData: SSEData }
  processTracePayload(payload: any): any
  createExecutionEvent(processedPayload: any): AgentExecutionEvent | WorkflowExecutionEvent
}

// Workflow消息处理器
class WorkflowMessageProcessor implements MessageProcessor {
  processData(dataStr: string): { sseMessage: SSEMessage; messageData: SSEData } {
    // 标准消息格式: {data: {type, payload}, code, message}
    const sseMessage = JSON.parse(dataStr) as SSEMessage
    return { sseMessage, messageData: sseMessage.data }
  }

  processTracePayload(payload: any): any {
    // 标准处理：直接返回payload
    return payload
  }

  createExecutionEvent(processedPayload: any): WorkflowExecutionEvent {
    // 标准workflow事件创建逻辑
    return {
      id: processedPayload.id,
      version: processedPayload.version,
      name: processedPayload.name,
      description: processedPayload.description,
      status: processedPayload.status,
      inputs: processedPayload.inputs,
      outputs: processedPayload.outputs,
      output_text: processedPayload.output_text,
      error: processedPayload.error,
      start_time: processedPayload.start_time,
      end_time: processedPayload.end_time,
      timestamp: processedPayload.timestamp,
      parent_id: processedPayload.parent_id,
      loop_index: processedPayload.loop_index,
      interaction_node: undefined,
      interaction_msg: undefined,
    }
  }
}

// 智能体消息处理器
class AgentMessageProcessor implements MessageProcessor {
  processData(dataStr: string): { sseMessage: SSEMessage; messageData: SSEData } {
    // 智能体响应可能包含两层data结构
    if (dataStr.includes('"data": {"data":')) {
      const agentResponse = JSON.parse(dataStr)
      // 智能体响应格式为 {data: {data: {type, payload}}, code, message}
      const sseMessage: SSEMessage = {
        data: agentResponse.data.data,
        code: agentResponse.code,
        message: agentResponse.message,
      }
      return { sseMessage, messageData: sseMessage.data }
    }
    // 回退到标准处理
    const sseMessage = JSON.parse(dataStr) as SSEMessage
    return { sseMessage, messageData: sseMessage.data }
  }

  processTracePayload(payload: any): any {
    // 提取智能体响应中的outputs.output.result到output_text
    if (payload.outputs && payload.outputs.output && payload.outputs.output.result) {
      return {
        ...payload,
        output_text: payload.outputs.output.result,
      }
    }
    return payload
  }

  createExecutionEvent(processedPayload: any): AgentExecutionEvent {
    // 智能体事件创建逻辑 - 简化为主要包含output字段
    return {
      output: processedPayload.output,
      // 保留基础字段以便与WorkflowExecutionEvent兼容
      id: processedPayload.id,
      version: processedPayload.version,
      name: processedPayload.name,
      description: processedPayload.description,
      status: processedPayload.status,
      error: processedPayload.error,
      // 添加交互中断相关字段
      interaction_node: processedPayload.interaction_node,
      interaction_msg: processedPayload.interaction_msg,
    }
  }
}

// 消息处理器工厂
class MessageProcessorFactory {
  static createProcessor(endpoint: string): MessageProcessor {
    if (endpoint === API_ENDPOINTS.EXECUTION.AGENT || endpoint === API_ENDPOINTS.EXECUTION.AGENT_USERINPUT) {
      return new AgentMessageProcessor()
    }
    return new WorkflowMessageProcessor()
  }
}

// 执行服务
export class ExecutionService {
  // 获取当前活跃的节点状态（用于错误映射）
  private static activeNodeStatuses: Map<string, any> = new Map()

  // 设置活跃节点状态
  static setActiveNodeStatuses(statuses: Map<string, any>) {
    ExecutionService.activeNodeStatuses = statuses
  }

  // 通用的SSE流处理函数
  private static async processSSEStream(
    endpoint: string,
    request: WorkflowExecutionRequest | WorkflowUserInputRequest,
    onEvent: WorkflowExecutionEventHandler,
    onError?: (error: Error) => void,
    onComplete?: () => void,
  ): Promise<() => void> {
    // 保存请求信息用于错误事件
    const workflowInfo = {
      id: request.id,
      version: request.version || '',
      space_id: request.space_id,
    }
    // 创建对应的消息处理器
    const messageProcessor = MessageProcessorFactory.createProcessor(endpoint)
    const apiClient = getApiClient()
    const baseURL = apiClient.defaults.baseURL || ''

    try {
      const controller = new AbortController()
      const { signal } = controller
      const response = await fetch(`${baseURL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          'Cache-Control': 'no-cache',
          Authorization: `Bearer ${getToken() || ''}`,
          'Accept-Language': getAcceptLanguage(),
        },
        body: JSON.stringify(request),
        credentials: 'include',
        signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      if (!response.body) {
        throw new Error('Response body is null')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let isReaderReleased = false
      let isCanceled = false

      const processStream = async () => {
        try {
          for (;;) {
            const { done, value } = await reader.read()

            if (done) {
              console.log('SSE stream completed')
              if (!isCanceled && onComplete) onComplete()
              break
            }

            // 解码数据并添加到缓冲区
            buffer += decoder.decode(value, { stream: true })

            // 处理完整的行
            const lines = buffer.split('\n')
            buffer = lines.pop() || '' // 保留最后一个不完整的行

            for (const line of lines) {
              if (line.trim() === '') continue

              // 解析 SSE 消息
              if (line.startsWith('data: ')) {
                const dataStr = line.substring(6) // 移除 'data: ' 前缀
                console.log(dataStr)

                try {
                  // 解析完整的 SSE 消息
                  const sseMessage = JSON.parse(dataStr) as SSEMessage

                  // 检查 code 是否为 200，只有 200 才继续解析 data 字段
                  if (sseMessage.code !== 200) {
                    // code 不为 200，表示执行错误，将 code 和 message 拼接成错误消息
                    const originalErrorMessage = sseMessage.message || 'Unknown error'
                    const errorMessage = `error ${sseMessage.code}: ${originalErrorMessage}`

                    const messageData = sseMessage.data
                    const errorNodesInfo = messageData?.error_nodes_info

                    if (messageData?.type === 'trace' && messageData?.payload) {
                      const payload = messageData.payload

                      if (payload.id && payload.status === 'finish' && payload.error) {
                        const errorValue = (payload as any).error
                        const traceErrorEvent: WorkflowExecutionEvent = {
                          id: payload.id,
                          version: payload.version || '',
                          name: payload.name || '',
                          description: payload.description || '',
                          status: 'error',
                          inputs: payload.inputs,
                          outputs: payload.outputs,
                          output_text: payload.output_text,
                          error: typeof errorValue === 'string' ? errorValue : errorValue?.message || String(errorValue),
                          start_time: payload.start_time,
                          end_time: payload.end_time,
                          interaction_node: undefined,
                          interaction_msg: undefined,
                        }
                        onEvent(traceErrorEvent)
                        continue
                      }
                    }

                    let targetNodeId: string | null = null
                    let finalErrorMessage = errorMessage

                    if (errorNodesInfo && Array.isArray(errorNodesInfo) && errorNodesInfo.length > 0) {
                      for (const errorNode of errorNodesInfo) {
                        if (errorNode.node_id && errorNode.error_message) {
                          targetNodeId = errorNode.node_id
                          finalErrorMessage = errorNode.error_message
                          break
                        }
                      }

                      if (!targetNodeId) {
                        const errorMsg = originalErrorMessage.toLowerCase()
                        const workflowMatch = errorMsg.match(/component\s+\[([^\]]+)\]/)
                        if (workflowMatch && workflowMatch[1]) {
                          const workflowNodeId = workflowMatch[1]
                          for (const [nodeId, status] of ExecutionService.activeNodeStatuses) {
                            if (nodeId.includes(workflowNodeId) && status.status === 'running') {
                              targetNodeId = nodeId
                              break
                            }
                          }

                          if (!targetNodeId) {
                            const runningWorkflowNodes = Array.from(ExecutionService.activeNodeStatuses.entries())
                              .filter(([nodeId, status]) => nodeId.startsWith('workflow_') && status.status === 'running')
                              .sort(([a], [b]) => a.length - b.length)

                            if (runningWorkflowNodes.length > 0) {
                              targetNodeId = runningWorkflowNodes[0][0]
                            }
                          }
                        }
                      }
                    } else {
                      const errorMsg = originalErrorMessage.toLowerCase()

                      if (errorMsg.includes('question') || errorMsg.includes('direct user response')) {
                        for (const [nodeId, status] of ExecutionService.activeNodeStatuses) {
                          if (nodeId.includes('questioner') && status.status === 'running') {
                            targetNodeId = nodeId
                            break
                          }
                        }
                      } else if (errorMsg.includes('llm') || errorMsg.includes('model')) {
                        for (const [nodeId, status] of ExecutionService.activeNodeStatuses) {
                          if (nodeId.includes('llm') && status.status === 'running') {
                            targetNodeId = nodeId
                            break
                          }
                        }
                      } else {
                        for (const [nodeId, status] of ExecutionService.activeNodeStatuses) {
                          if (status.status === 'running' && !nodeId.startsWith('start_')) {
                            targetNodeId = nodeId
                            break
                          }
                        }
                      }
                    }

                    if (targetNodeId) {
                      const nodeErrorEvent: WorkflowExecutionEvent = {
                        id: targetNodeId,
                        version: workflowInfo.version,
                        name: 'Node Error',
                        description: 'Node execution failed',
                        status: 'error',
                        inputs: undefined,
                        outputs: undefined,
                        output_text: undefined,
                        error: finalErrorMessage,
                        start_time: new Date().toISOString(),
                        end_time: new Date().toISOString(),
                        interaction_node: undefined,
                        interaction_msg: undefined,
                      }
                      onEvent(nodeErrorEvent)
                    } else {
                      const workflowErrorEvent: WorkflowExecutionEvent = {
                        id: workflowInfo.id,
                        version: workflowInfo.version,
                        name: 'Workflow Error',
                        description: 'Workflow execution failed',
                        status: 'error',
                        inputs: undefined,
                        outputs: undefined,
                        output_text: undefined,
                        error: finalErrorMessage,
                        start_time: new Date().toISOString(),
                        end_time: new Date().toISOString(),
                        interaction_node: undefined,
                        interaction_msg: undefined,
                      }
                      onEvent(workflowErrorEvent)
                    }

                    continue
                  }

                  // code 为 200，继续解析 data 字段
                  const { messageData } = messageProcessor.processData(dataStr)

                  if (messageData.type === 'trace') {
                    // trace 类型：payload 包含执行事件字段
                    const payload = messageData.payload

                    // 使用对应的处理器处理payload
                    const executionEvent = messageProcessor.createExecutionEvent(messageProcessor.processTracePayload(payload))
                    // WorkflowExecutionEvent类型，直接使用
                    onEvent(executionEvent as WorkflowExecutionEvent)
                  } else if (messageData.type === 'agent') {
                    // agent 类型：payload 包含执行事件字段
                    const payload = messageData.payload

                    // 使用对应的处理器处理payload
                    const executionEvent = messageProcessor.createExecutionEvent(messageProcessor.processTracePayload(payload))
                    // 根据返回类型决定是否需要转换
                    if ('output' in executionEvent) {
                      // AgentExecutionEvent类型，需要转换为WorkflowExecutionEvent
                      const workflowEvent: WorkflowExecutionEvent = {
                        type: messageData.type,
                        id: executionEvent.id || '',
                        version: executionEvent.version || '',
                        name: executionEvent.name || '',
                        description: executionEvent.description || '',
                        status: 'finish',
                        inputs: undefined,
                        outputs: undefined,
                        output_text: executionEvent.output,
                        error: executionEvent.error,
                        // 添加交互中断相关字段
                        interaction_node: executionEvent.interaction_node,
                        interaction_msg: executionEvent.interaction_msg,
                      }
                      onEvent(workflowEvent)
                    } else {
                      // WorkflowExecutionEvent类型，直接使用
                      const enrichedEvent: WorkflowExecutionEvent = {
                        ...(executionEvent as WorkflowExecutionEvent),
                        type: messageData.type,
                      }
                      onEvent(enrichedEvent)
                    }
                  } else if (messageData.type === 'workflow') {
                    const payload = messageData.payload

                    const workflowEvent: WorkflowExecutionEvent = {
                      id: 'workflow_stream',
                      version: '',
                      name: 'Workflow Stream',
                      description: 'Streaming workflow message',
                      status: 'running',
                      inputs: undefined,
                      outputs: undefined,
                      output_text: payload.output || '', // 使用后端的 output 字段
                      error: undefined,
                      start_time: undefined,
                      end_time: undefined,
                      timestamp: new Date().toISOString(),
                      parent_id: undefined,
                      loop_index: undefined,
                      interaction_node: undefined,
                      interaction_msg: undefined,
                      _streamPayload: payload,
                    }

                    onEvent(workflowEvent)
                  } else if (messageData.type === 'interaction') {
                    // interaction 类型：payload 只包含 {interaction_node, interaction_msg}
                    const payload = messageData.payload as interactionPayload
                    const workflowEvent: WorkflowExecutionEvent = {
                      id: '',
                      version: '',
                      name: '',
                      description: '',
                      status: 'running', // interaction 类型使用 running 状态
                      inputs: undefined,
                      outputs: undefined,
                      output_text: undefined,
                      error: undefined,
                      start_time: undefined,
                      end_time: undefined,
                      timestamp: undefined,
                      parent_id: undefined,
                      loop_index: undefined,
                      // interaction 字段
                      interaction_node: payload.interaction_node,
                      interaction_msg: payload.interaction_msg,
                    }

                    onEvent(workflowEvent)
                  }
                } catch (parseError) {
                  console.error('Failed to parse SSE message:', parseError)
                  console.error('Raw data:', dataStr)
                  if (onError) onError(parseError as Error)
                }
              }
            }
          }
        } catch (error) {
          console.error('Error processing SSE stream:', error)
          if (onError) onError(error as Error)
        } finally {
          // 只有在reader还未释放时才释放
          if (!isReaderReleased) {
            reader.releaseLock()
            isReaderReleased = true
          }
        }
      }

      // 开始处理流
      processStream()

      return () => {
        if (!isReaderReleased) {
          reader.cancel().catch(error => {
            console.warn('Failed to cancel reader:', error)
          })
          isReaderReleased = true
        }
        try {
          isCanceled = true
          controller.abort()
        } catch (e) {
          console.warn('Abort controller error:', e)
        }
      }
    } catch (error) {
      console.error('Failed to start SSE connection:', error)
      if (onError) onError(error as Error)
      return () => {}
    }
  }

  // 执行工作流（流式响应）
  static async executeWorkflow(
    request: WorkflowExecutionRequest,
    onEvent: WorkflowExecutionEventHandler,
    onError?: (error: Error) => void,
    onComplete?: () => void,
  ): Promise<() => void> {
    return this.processSSEStream(API_ENDPOINTS.EXECUTION.WORKFLOW, request, onEvent, onError, onComplete)
  }

  // 用户输入处理（流式响应）
  static async handleUserInput(
    request: WorkflowUserInputRequest,
    onEvent: WorkflowExecutionEventHandler,
    onError?: (error: Error) => void,
    onComplete?: () => void,
  ): Promise<() => void> {
    return this.processSSEStream(API_ENDPOINTS.EXECUTION.USERINPUT, request, onEvent, onError, onComplete)
  }

  // 智能体用户输入处理（流式响应）
  static async handleAgentUserInput(
    request: WorkflowUserInputRequest,
    onEvent: WorkflowExecutionEventHandler,
    onError?: (error: Error) => void,
    onComplete?: () => void,
  ): Promise<() => void> {
    return this.processSSEStream(API_ENDPOINTS.EXECUTION.AGENT_USERINPUT, request, onEvent, onError, onComplete)
  }

  // 执行智能体（流式响应）
  static async executionAgent(
    request: WorkflowExecutionRequest,
    onEvent: WorkflowExecutionEventHandler,
    onError?: (error: Error) => void,
    onComplete?: () => void,
  ): Promise<() => void> {
    return this.processSSEStream(API_ENDPOINTS.EXECUTION.AGENT, request, onEvent, onError, onComplete)
  }

  // 重置智能体实例
  static async resetAgentInstance(request: WorkflowExecutionRequest): Promise<void> {
    try {
      const apiClient = getApiClient()
      await apiClient.post(API_ENDPOINTS.EXECUTION.AGENT_RESET, request)
      console.log('Agent instance reset successfully')
    } catch (error: any) {
      console.error('Failed to reset agent instance:', error)
      throw error
    }
  }

  // 执行组件（单节点调试）
  static async executeComponent(request: ComponentExecuteRequest): Promise<ComponentExecuteResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<ComponentExecuteResponse>(API_ENDPOINTS.EXECUTION.COMPONENT, request)
      return response.data
    } catch (error: any) {
      console.error('执行组件失败:', error)

      // 提取详细的错误信息
      let errorMessage = '未知错误'

      if (error?.response) {
        // 处理 axios错误响应
        const response = error.response

        // 优先使用响应中的 message 字段
        if (response.data?.message) {
          errorMessage = response.data.message
        }
        // 如果没有 data.message，使用直接的 message
        else if (response.message) {
          errorMessage = response.message
        }

        // 如果有具体的错误数据，也提取出来
        if (response.data?.data?.payload?.output?.result) {
          const backendError = response.data.data.payload.output.result
          if (backendError && backendError !== errorMessage) {
            errorMessage = `${errorMessage}`
          }
        }
      } else if (error?.message) {
        // 直接的 JavaScript 错误
        errorMessage = error.message
      } else if (error?.detail) {
        // 兼容原有的 detail 字段
        errorMessage = error.detail
      }

      throw new Error(errorMessage)
    }
  }

  static async cancelComponent(request: ComponentCancelRequest): Promise<ComponentCancelResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<ComponentCancelResponse>(API_ENDPOINTS.EXECUTION.COMPONENT_CANCEL, request)
      return response.data
    } catch (error: any) {
      console.error('取消单节点调试失败:', error)

      let errorMessage = '未知错误'

      if (error?.response) {
        if (error.response.data?.message) {
          errorMessage = error.response.data.message
        } else if (error.response.message) {
          errorMessage = error.response.message
        }
      } else if (error?.message) {
        errorMessage = error.message
      } else if (error?.detail) {
        errorMessage = error.detail
      }

      throw new Error(errorMessage)
    }
  }

  static async cancelWorkflowExecution(request: WorkflowCancelRequest): Promise<WorkflowCancelResponse> {
    try {
      const apiClient = getApiClient()
      const response = await apiClient.post<WorkflowCancelResponse>(API_ENDPOINTS.EXECUTION.WORKFLOW_CANCEL, request)
      return response.data
    } catch (error: any) {
      console.error('取消工作流执行失败:', error)
      throw error
    }
  }
}

export default ExecutionService
