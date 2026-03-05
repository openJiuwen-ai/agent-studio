/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useState, useCallback, useMemo, useRef } from 'react'

import { testRunRuntimeService } from '../runtime/testrun-runtime-service'
import { InputInterruption } from '../runtime/types'

export function useInputInterruption() {
  const [interruptionQueue, setInterruptionQueue] = useState<InputInterruption[]>([])
  const [inputValues, setInputValues] = useState<Record<string, unknown>>({})
  const isResumingRef = useRef(false)

  const currentInterruption = useMemo(
    () => (interruptionQueue.length > 0 ? interruptionQueue[0] : null),
    [interruptionQueue]
  )

  const pendingCount = useMemo(
    () => Math.max(0, interruptionQueue.length - 1),
    [interruptionQueue.length]
  )

  const handleInputRequired = useCallback((data: InputInterruption) => {
    setInterruptionQueue(prev => {
      if (prev.some(item => item.nodeId === data.nodeId)) {
        return prev
      }
      return [...prev, data]
    })
  }, [])

  const resume = useCallback(
    async (values: Record<string, unknown>) => {
      if (isResumingRef.current) return false

      const current = interruptionQueue[0]
      if (!current) return false

      isResumingRef.current = true
      setInterruptionQueue(prev => prev.slice(1))
      setInputValues({})

      try {
        await testRunRuntimeService.resumeStreamExecution({
          node_id: current.nodeId,
          input_value: values,
        })
        return true
      } catch (error) {
        setInterruptionQueue(prev => [{ nodeId: current.nodeId, message: current.message }, ...prev])
        return false
      } finally {
        isResumingRef.current = false
      }
    },
    [interruptionQueue],
  )

  const clear = useCallback(() => {
    setInterruptionQueue([])
    setInputValues({})
  }, [])

  return {
    interruption: currentInterruption,
    interruptionQueue,
    pendingCount,
    hasPendingInterruptions: pendingCount > 0,
    inputValues,
    setInputValues,
    handleInputRequired,
    resume,
    clear,
  }
}
