/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useState, useRef, useCallback } from 'react'

import { testRunRuntimeService } from '../runtime/testrun-runtime-service'
import { UnifiedExecutionParams } from '../runtime/types'
import { useExecutionContext } from '../../../context'

interface UseTestExecutionOptions {
  workflowId?: string
  spaceId?: string
  nodeId?: string
  conversationId?: string
  version?: string
  loopId?: string
}

interface UseTestExecutionResult {
  isExecuting: boolean
  errors: string[] | undefined
  result: any | undefined
  execute: (values: Record<string, unknown>) => Promise<void>
  cancel: () => void
  resetErrors: () => void
}

export function useTestExecution(options: UseTestExecutionOptions): UseTestExecutionResult {
  const { workflowId, spaceId, nodeId, conversationId, version, loopId } = options
  const executionContext = useExecutionContext()

  const [isExecuting, setIsExecuting] = useState(false)
  const [errors, setErrors] = useState<string[]>()
  const [result, setResult] = useState<any>()
  const valuesRef = useRef<Record<string, unknown>>({})

  const resetErrors = useCallback(() => {
    setErrors(undefined)
  }, [])

  const execute = useCallback(
    async (values: Record<string, unknown>) => {
      valuesRef.current = values

      if (!workflowId && !nodeId) {
        setErrors(['缺少工作流ID或节点ID'])
        return
      }

      const finalSpaceId = spaceId
      if (!finalSpaceId) {
        setErrors(['缺少空间ID，请确保工作空间信息正确'])
        return
      }

      setIsExecuting(true)
      setErrors(undefined)
      setResult(undefined)

      testRunRuntimeService.stopStreamExecution()
      executionContext.clearExecution()

      try {
        const params: UnifiedExecutionParams = {
          id: workflowId || nodeId || '',
          version: version || '',
          space_id: finalSpaceId,
          inputs: values,
          component_id: nodeId,
          loop_id: loopId,
          conversation_id: conversationId,
          options: {
            statusManagement: {
              clearBeforeStart: true,
              triggerNodeStatus: true,
              triggerGlobalReset: false,
            },
            eventHandling: {
              enableNodeReport: true,
              enableProgressTracking: true,
              enableResultBroadcast: true,
            },
            mode: nodeId ? 'single-node' : 'workflow',
          },
        }

        const response = await testRunRuntimeService.execute(params)

        if (nodeId) {
          if (response.code === 200) {
            let outputData = null
            if (response.data?.output?.result) {
              outputData = response.data.output.result
            } else if (response.data?.response) {
              outputData = response.data.response
            } else {
              outputData = response.data
            }
            setResult(outputData)
          } else {
            setErrors([response.message])
          }
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '执行过程中发生未知错误'
        setErrors([errorMessage])
      } finally {
        setIsExecuting(false)
      }
    },
    [workflowId, spaceId, nodeId, conversationId, version, loopId, executionContext],
  )

  const cancel = useCallback(() => {
    setIsExecuting(false)
    executionContext.clearExecution()

    if (nodeId) {
      testRunRuntimeService.cancelSingleComponent(nodeId).catch(error => {
        console.error('Cancel component execution failed:', error)
      })
    }
  }, [nodeId, executionContext])

  return {
    isExecuting,
    errors,
    result,
    execute,
    cancel,
    resetErrors,
  }
}
