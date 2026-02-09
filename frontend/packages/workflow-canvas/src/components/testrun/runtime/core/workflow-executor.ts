/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { ExecutionService } from '@test-agentstudio/api-client'
import { Emitter } from '@flowgram.ai/free-layout-editor'
import { v4 as uuidv4 } from 'uuid'

import { StreamExecuteParams, StreamResponse, ExecutionOptions, NodeExecutionStatus } from '../types'
import { EventConverter } from './event-converter'
import { ExecutionStatusManager } from './execution-status-manager'

export class WorkflowExecutor {
  private isExecuting = false
  private executionCount = 0
  private activeExecutions = new Set<string>()
  private eventHandlers: ((event: StreamResponse) => void)[] = []
  private executionController?: AbortController
  private closeExecutionFunction?: () => void
  private currentExecutionParams?: StreamExecuteParams
  private currentConversationId?: string
  private currentSpaceId?: string

  private resultEmitter = new Emitter<{
    errors?: string[]
    result?: {
      inputs: any
      outputs: any
    }
  }>()

  public onResultChanged = this.resultEmitter.event

  constructor(private eventConverter: EventConverter, private statusManager: ExecutionStatusManager) {}

  getIsExecuting(): boolean {
    return this.isExecuting
  }

  getCurrentParams(): StreamExecuteParams | undefined {
    return this.currentExecutionParams
  }

  async execute(params: StreamExecuteParams, options: ExecutionOptions, onEvent?: (event: StreamResponse) => void): Promise<void> {
    this.statusManager.manageExecutionStart(options)

    const executionId = `exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    this.activeExecutions.add(executionId)
    this.executionCount++

    this.isExecuting = true

    this.eventHandlers = onEvent ? [onEvent] : []
    this.executionController = new AbortController()

    const conversation_id = params.conversation_id || uuidv4()
    this.currentExecutionParams = { ...params, conversation_id }
    this.currentConversationId = conversation_id
    this.currentSpaceId = params.space_id

    this.eventConverter.reset()

    try {
      this.closeExecutionFunction = await ExecutionService.executeWorkflow(
        {
          id: params.id,
          version: params.version,
          space_id: params.space_id,
          inputs: params.inputs,
          conversation_id,
        },
        executionEvent => {
          const streamEvent = this.eventConverter.convert(executionEvent)
          this.handleStreamEvent(streamEvent, executionEvent)
          if (onEvent) onEvent(streamEvent)

          if (streamEvent.type === 'node_status' && streamEvent.data.status === 'completed') {
            const nodeId = streamEvent.data.nodeId
            if (nodeId && nodeId.toString().startsWith('end_')) {
              this.handleExecutionComplete(executionId, params.inputs)
            }
          }
        },
        error => {
          this.handleExecutionError(error, executionId)
        },
        () => {
          if (this.isExecuting) {
            this.executionCount--
            if (this.executionCount <= 0) {
              this.isExecuting = false
            }
          }
        },
      )

      this.executionController = undefined
    } catch (error) {
      this.isExecuting = false
      this.eventConverter.setHasError(true)

      const errorMessage = error instanceof Error ? error.message : 'Execution failed'

      this.resultEmitter.fire({
        errors: [errorMessage],
      })

      this.executionController = undefined
      throw error
    }
  }

  async resume(input: { node_id: string; input_value: Record<string, unknown> }): Promise<void> {
    if (!this.currentExecutionParams) {
      throw new Error('没有可恢复的执行 - currentExecutionParams 为空')
    }

    this.statusManager.removeWaitingForInput(input.node_id)
    this.eventConverter.removeWaitingForInputNode(input.node_id)
    this.isExecuting = true

    try {
      this.closeExecutionFunction = await ExecutionService.handleUserInput(
        {
          space_id: this.currentExecutionParams.space_id,
          id: this.currentExecutionParams.id,
          version: this.currentExecutionParams.version,
          conversation_id: this.currentExecutionParams.conversation_id,
          inputs: {
            node_id: input.node_id,
            input_value: input.input_value,
          },
        },
        executionEvent => {
          const streamEvent = this.eventConverter.convert(executionEvent)
          this.handleStreamEvent(streamEvent, executionEvent)
          this.eventHandlers.forEach(handler => handler(streamEvent))

          if (streamEvent.type === 'node_status' && streamEvent.data.status === 'completed') {
            const nodeId = streamEvent.data.nodeId
            if (nodeId && nodeId.toString().startsWith('end_')) {
              this.handleExecutionComplete('', this.currentExecutionParams?.inputs || {})
            }
          }
        },
        error => {
          this.handleExecutionError(error, '')
        },
        () => {
          this.isExecuting = false
        },
      )

      this.isExecuting = false
    } catch (error) {
      this.isExecuting = false
      this.eventConverter.setHasError(true)

      const errorMessage = error instanceof Error ? error.message : 'Resume execution failed'

      this.eventHandlers.forEach(handler =>
        handler({
          type: 'error',
          data: { message: errorMessage },
        }),
      )

      this.resultEmitter.fire({
        errors: [errorMessage],
      })

      throw error
    }
  }

  stop(): void {
    if (this.isExecuting && this.currentConversationId && this.currentSpaceId) {
      ExecutionService.cancelWorkflowExecution({
        space_id: this.currentSpaceId,
        conversation_id: this.currentConversationId,
      }).catch(error => {
        if (error?.response?.status === 404 || error?.message?.includes('Execution not found')) {
        } else {
          console.error('Failed to cancel workflow execution on server:', error)
        }
      })
    }

    const runningNodes = this.statusManager.getRunningNodes()

    for (const nodeId of runningNodes) {
      this.statusManager.setNodeStatus(nodeId, NodeExecutionStatus.CANCELED)
    }

    if (runningNodes.length > 0) {
      this.eventHandlers.forEach(handler =>
        handler({
          type: 'error',
          data: {
            nodeId: 'workflow',
            message: 'canceled by user',
            timestamp: Date.now(),
            isUserCanceled: true,
          },
        }),
      )
    }

    this.resultEmitter.fire({
      errors: ['canceled by user'],
    })

    if (this.closeExecutionFunction) {
      this.closeExecutionFunction()
      this.closeExecutionFunction = undefined
    }

    if (this.executionController) {
      this.executionController.abort()
      this.executionController = undefined
    }

    this.isExecuting = false
    this.statusManager.clearWaitingForInput()
    this.eventHandlers = []
    this.currentExecutionParams = undefined
    this.currentConversationId = undefined
    this.currentSpaceId = undefined
  }

  reset(): void {
    this.isExecuting = false
    this.executionCount = 0
    this.activeExecutions.clear()
    this.eventHandlers = []
    this.currentExecutionParams = undefined
    this.currentConversationId = undefined
    this.currentSpaceId = undefined
    this.eventConverter.reset()
  }

  private handleStreamEvent(streamEvent: StreamResponse, executionEvent: any): void {
    if (streamEvent.type === 'progress' || streamEvent.type === 'node_status') {
      const nodeId = streamEvent.data.nodeId
      const status = streamEvent.data.status

      if (status === 'processing') {
        this.statusManager.setNodeStatus(nodeId, NodeExecutionStatus.RUNNING, {
          inputs: executionEvent.inputs,
        })
      } else if (status === 'completed') {
        this.statusManager.setNodeStatus(nodeId, NodeExecutionStatus.SUCCESS, {
          inputs: executionEvent.inputs,
          outputs: streamEvent.data.outputs || executionEvent.outputs,
        })
      } else if (status === 'waiting_for_input') {
        this.statusManager.addWaitingForInput(nodeId)
        this.statusManager.setNodeStatus(nodeId, NodeExecutionStatus.RUNNING, {
          inputs: executionEvent.inputs,
        })
      }
    }

    if (streamEvent.type === 'input_required') {
      const nodeId = streamEvent.data.nodeId

      this.statusManager.addWaitingForInput(nodeId)
      this.statusManager.setNodeStatus(nodeId, NodeExecutionStatus.RUNNING, {
        inputs: executionEvent.inputs,
      })
    }
  }

  private handleExecutionError(error: any, executionId: string): void {
    this.executionCount--
    this.activeExecutions.delete(executionId)

    if (this.executionCount === 0) {
      this.isExecuting = false
    }

    this.eventConverter.setHasError(true)

    let errorMessage = 'Execution failed'

    if (error.message) {
      errorMessage = error.message
    } else if (typeof error === 'string') {
      errorMessage = error
    }

    if (error.code) {
      errorMessage = `[${error.code}] ${errorMessage}`
    }

    this.eventHandlers.forEach(handler =>
      handler({
        type: 'error',
        data: { message: errorMessage },
      }),
    )

    this.resultEmitter.fire({
      errors: [errorMessage],
    })
  }

  private handleExecutionComplete(executionId: string, inputs: any): void {
    this.executionCount--
    this.activeExecutions.delete(executionId)

    if (this.executionCount === 0) {
      this.isExecuting = false
    }

    if (!this.eventConverter.getHasError()) {
      const finalData = this.eventConverter.getFinalData(inputs)

      this.eventHandlers.forEach(handler =>
        handler({
          type: 'completed',
          data: finalData,
        }),
      )

      this.resultEmitter.fire({ result: finalData })
    }
  }
}
