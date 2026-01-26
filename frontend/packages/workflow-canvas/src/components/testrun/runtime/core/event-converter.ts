/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { StreamResponse, ExecutionEventWrapper, InteractionMessage } from '../types'

export class EventConverter {
  private nodeStartTimes = new Map<string, number>()
  private hasError = false
  private nodeOutputs = new Map<string, any>()
  private finalOutputs: any = null
  private streamMessageOutput = ''
  private waitingForInputNodes = new Set<string>()

  reset(): void {
    this.nodeStartTimes.clear()
    this.hasError = false
    this.nodeOutputs.clear()
    this.finalOutputs = null
    this.streamMessageOutput = ''
    this.waitingForInputNodes.clear()
  }

  getHasError(): boolean {
    return this.hasError
  }

  setHasError(value: boolean): void {
    this.hasError = value
  }

  getFinalOutputs(): any {
    return this.finalOutputs
  }

  setFinalOutputs(value: any): void {
    this.finalOutputs = value
  }

  appendStreamOutput(output: string): void {
    this.streamMessageOutput += output
  }

  setNodeOutput(nodeId: string, output: any): void {
    this.nodeOutputs.set(nodeId, output)
  }

  getNodeStartTime(nodeId: string): number | undefined {
    return this.nodeStartTimes.get(nodeId)
  }

  setNodeStartTime(nodeId: string, time: number): void {
    this.nodeStartTimes.set(nodeId, time)
  }

  deleteNodeStartTime(nodeId: string): void {
    this.nodeStartTimes.delete(nodeId)
  }

  addWaitingForInputNode(nodeId: string): void {
    this.waitingForInputNodes.add(nodeId)
  }

  removeWaitingForInputNode(nodeId: string): void {
    this.waitingForInputNodes.delete(nodeId)
  }

  isWaitingForInput(nodeId: string): boolean {
    return this.waitingForInputNodes.has(nodeId)
  }

  clearWaitingForInputNodes(): void {
    this.waitingForInputNodes.clear()
  }

  getFinalData(inputs: any): any {
    return {
      inputs,
      outputs:
        this.finalOutputs ||
        (this.streamMessageOutput
          ? {
              responseContent: this.streamMessageOutput,
            }
          : Object.fromEntries(this.nodeOutputs)),
    }
  }

  isInputNode(nodeId: string): boolean {
    if (!nodeId) return false
    const nodeIdStr = nodeId.toString()
    return (
      nodeIdStr.includes('input') ||
      nodeIdStr.startsWith('input_') ||
      nodeIdStr.includes('Input')
    )
  }

  convert(event: ExecutionEventWrapper): StreamResponse {
    if (this.isErrorEvent(event)) {
      return this.convertErrorEvent(event)
    }

    if (this.isInteractionEvent(event)) {
      return this.convertInteractionEvent(event)
    }

    const status = this.getEventProperty(event, 'status')

    if (status === 'start') {
      return this.convertStartEvent(event)
    }

    if (status === 'finish') {
      return this.convertFinishEvent(event)
    }

    if (status === 'failed' || status === 'error') {
      return this.convertFailedEvent(event)
    }

    if (this.isStreamMessageEvent(event)) {
      return this.convertStreamMessageEvent(event)
    }

    return {
      type: 'progress',
      data: {
        nodeId: this.getEventProperty(event, 'id') || 'unknown',
        status: status || 'unknown',
        timestamp: this.getEventProperty(event, 'timestamp') || Date.now(),
      },
    }
  }

  private isDirectEvent(event: any): event is { id: string; status: string } {
    return event && typeof event === 'object' && 'id' in event && 'status' in event
  }

  private isDataWrappedEvent(event: any): event is { data: any } {
    return event && typeof event === 'object' && 'data' in event
  }

  private getEventProperty(event: any, property: string): any {
    if (this.isDirectEvent(event) && property in event) {
      return (event as any)[property]
    }

    if (this.isDataWrappedEvent(event) && event.data?.payload && property in event.data.payload) {
      return event.data.payload[property]
    }

    return undefined
  }

  private isErrorEvent(event: any): boolean {
    const status = this.getEventProperty(event, 'status')
    const description = this.getEventProperty(event, 'description')
    return status === 'error' || (description && description.includes('失败'))
  }

  private convertErrorEvent(event: any): StreamResponse {
    this.hasError = true

    let errorMessage = 'Workflow execution failed'

    const message = this.getEventProperty(event, 'message')
    const error = this.getEventProperty(event, 'error')
    const code = this.getEventProperty(event, 'code')
    const eventId = this.getEventProperty(event, 'id')

    if (error) {
      errorMessage = error
    } else if (message && message !== 'Workflow execution failed') {
      errorMessage = message
    } else {
      const description = this.getEventProperty(event, 'description')
      if (description && description !== 'Workflow execution failed') {
        errorMessage = description
      }
    }

    if (code) {
      errorMessage = `[${code}] ${errorMessage}`
    }

    const dataStr = this.getEventProperty(event, 'dataStr')
    if (dataStr) {
      try {
        const dataObj = JSON.parse(dataStr)
        if (dataObj.message && dataObj.message !== errorMessage) {
          errorMessage = dataObj.message
        }
      } catch {
        // ignore
      }
    }

    return {
      type: 'error',
      data: {
        nodeId: eventId || 'workflow',
        message: errorMessage,
        timestamp: Date.now(),
      },
    }
  }

  private isInteractionEvent(event: any): boolean {
    const interactionNode = this.getEventProperty(event, 'interaction_node')
    return !!interactionNode
  }

  private convertInteractionEvent(event: any): StreamResponse {
    const eventId = this.getEventProperty(event, 'id')
    const interactionNode = this.getEventProperty(event, 'interaction_node') || eventId
    const interactionMsg = this.getEventProperty(event, 'interaction_msg')
    const inputs = this.getEventProperty(event, 'inputs')

    if (interactionNode) {
      this.waitingForInputNodes.add(interactionNode)
    }

    return {
      type: 'input_required',
      data: {
        nodeId: interactionNode,
        message: (interactionMsg || 'Input required') as InteractionMessage,
        requiredInputs: Object.keys(inputs || {}),
      },
    }
  }

  private convertStartEvent(event: any): StreamResponse {
    const eventId = this.getEventProperty(event, 'id')
    const startTime =
      this.getEventProperty(event, 'start_time') && typeof this.getEventProperty(event, 'start_time') === 'string'
        ? new Date(this.getEventProperty(event, 'start_time')).getTime()
        : Date.now()

    this.nodeStartTimes.set(eventId, startTime)

    return {
      type: 'progress',
      data: {
        nodeId: eventId,
        status: 'processing',
        progress: 0,
      },
    }
  }

  private convertFinishEvent(event: any): StreamResponse {
    const finishNodeId = this.getEventProperty(event, 'id')
    const outputs = this.getEventProperty(event, 'outputs')
    const timestamp = this.getEventProperty(event, 'timestamp')

    if (outputs && finishNodeId) {
      this.nodeOutputs.set(finishNodeId, outputs)
    }

    const isWaitingForInput = finishNodeId && this.waitingForInputNodes.has(finishNodeId)

    this.nodeStartTimes.delete(finishNodeId)

    let finalStatus = 'completed'
    if (isWaitingForInput) {
      const hasUserOutputs = outputs && Object.keys(outputs).length > 0
      if (!hasUserOutputs) {
        finalStatus = 'waiting_for_input'
      } else {
        this.waitingForInputNodes.delete(finishNodeId)
      }
    }

    if (finishNodeId && finishNodeId.toString().startsWith('end_')) {
      if (this.streamMessageOutput) {
        this.finalOutputs = {
          responseContent: this.streamMessageOutput,
        }
      } else {
        this.finalOutputs = outputs || {}
      }
    }

    return {
      type: 'node_status',
      data: {
        nodeId: finishNodeId,
        status: finalStatus,
        outputs: outputs,
        timestamp: timestamp || Date.now(),
      },
    }
  }

  private convertFailedEvent(event: any): StreamResponse {
    this.hasError = true

    const eventId = this.getEventProperty(event, 'id')
    const error = this.getEventProperty(event, 'error')
    const timestamp = this.getEventProperty(event, 'timestamp')

    return {
      type: 'error',
      data: {
        nodeId: eventId,
        message: error || 'Execution failed',
        timestamp: timestamp || Date.now(),
      },
    }
  }

  private isStreamMessageEvent(event: any): boolean {
    const id = this.getEventProperty(event, 'id')
    const outputText = this.getEventProperty(event, 'output_text')
    const streamPayload = (event as any)._streamPayload

    return id === 'workflow_stream' && outputText && streamPayload?.node_id
  }

  private convertStreamMessageEvent(event: any): StreamResponse {
    const streamPayload = (event as any)._streamPayload
    return {
      type: 'stream_message',
      data: {
        type: 'workflow',
        payload: {
          node_id: streamPayload.node_id,
          node_name: streamPayload.node_name,
          output: streamPayload.output || event.output_text,
          result_type: streamPayload.result_type || 'answer',
        },
      },
    }
  }
}
