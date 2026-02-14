/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { ExecutionService } from '@test-agentstudio/api-client'
import { Emitter } from '@flowgram.ai/free-layout-editor'
import { v4 as uuidv4 } from 'uuid'

import {
  ComponentExecuteParams,
  ComponentExecuteResult,
  ExecutionOptions,
  NodeReport,
  NodeExecutionStatus,
} from '../types'
import { ExecutionStatusManager } from './execution-status-manager'

export class SingleNodeExecutor {
  private nodeStartTimes = new Map<string, number>()
  private reportEmitter = new Emitter<NodeReport>()
  private currentExecutionParams: Map<string, ComponentExecuteParams & { conversation_id: string }> = new Map()

  public onNodeReportChange = this.reportEmitter.event

  constructor(private statusManager: ExecutionStatusManager) {}

  async execute(params: ComponentExecuteParams, options: ExecutionOptions): Promise<ComponentExecuteResult> {
    const { eventHandling = {} } = options
    const startTime = Date.now()
    this.nodeStartTimes.set(params.id, startTime)

    const conversation_id = params.conversation_id || uuidv4()
    const paramsWithConversationId = { ...params, conversation_id }
    this.currentExecutionParams.set(params.component_id!, paramsWithConversationId)

    if (eventHandling.enableNodeReport) {
      this.statusManager.setNodeStatus(params.component_id!, NodeExecutionStatus.RUNNING, {
        inputs: params.inputs,
      })
    }

    try {
      const result = await ExecutionService.executeComponent(paramsWithConversationId)
      this.currentExecutionParams.delete(params.component_id!)

      if (result.code === 200 && eventHandling.enableNodeReport) {
        let outputData = null
        if (result.data?.output?.result) {
          outputData = result.data.output.result
        } else if (result.data?.response) {
          outputData = result.data.response
        } else {
          outputData = result.data
        }

        this.statusManager.setNodeStatus(params.component_id!, NodeExecutionStatus.SUCCESS, {
          inputs: params.inputs,
          outputs: outputData,
        })
      } else if (result.code !== 200 && eventHandling.enableNodeReport) {
        const errorMessage = result.message || 'Component execution failed'
        this.statusManager.setNodeStatus(params.component_id!, NodeExecutionStatus.FAILED, {
          inputs: params.inputs,
          error: errorMessage,
        })
      }

      return result
    } catch (error) {
      this.currentExecutionParams.delete(params.component_id!)

      if (eventHandling.enableNodeReport) {
        const errorMessage = error instanceof Error ? error.message : '执行过程中发生未知错误'
        this.statusManager.setNodeStatus(params.component_id!, NodeExecutionStatus.FAILED, {
          inputs: params.inputs,
          error: errorMessage,
        })
      }
      throw error
    }
  }

  async cancel(nodeId: string): Promise<void> {
    const params = this.currentExecutionParams.get(nodeId)
    if (params) {
      try {
        await ExecutionService.cancelComponent({
          space_id: params.space_id,
          id: params.id,
          version: params.version,
          component_id: params.component_id,
          conversation_id: params.conversation_id,
        })
      } catch (error) {
        console.error('Cancel component execution failed:', error)
      } finally {
        this.currentExecutionParams.delete(nodeId)
      }
    }

    this.statusManager.setNodeStatus(nodeId, NodeExecutionStatus.CANCELED, {
      error: 'canceled by user',
    })
  }
}
