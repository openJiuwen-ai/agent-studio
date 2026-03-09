import { API_ENDPOINTS, getApiClient } from '@test-agentstudio/api-client'
import { useCallback, useMemo, useRef, useState } from 'react'
import { WorkflowDetail } from '@/types/agentTypes'

export type WorkflowValidationResult = { status: 'loading' | 'success' | 'error'; message?: string }

export const useWorkflowValidation = ({ workflows, spaceId }: { workflows: WorkflowDetail[]; spaceId: string }) => {
  const [validationResults, setValidationResults] = useState<Record<string, WorkflowValidationResult>>({})
  const validationSeqRef = useRef(0)

  const isValidating = useMemo(() => Object.values(validationResults).some(v => v.status === 'loading'), [validationResults])

  const workflowValidationErrorCount = useMemo(
    () => workflows.filter(w => validationResults[w.workflow_id]?.status === 'error').length,
    [workflows, validationResults],
  )

  // 清理已删除工作流的验证结果
  const cleanupDeletedWorkflows = useCallback((currentWorkflows: WorkflowDetail[]) => {
    const currentIds = new Set(currentWorkflows.map(w => w.workflow_id))
    setValidationResults(prev => {
      const next: Record<string, WorkflowValidationResult> = { ...prev }
      let hasChanges = false
      Object.keys(next).forEach(id => {
        if (!currentIds.has(id)) {
          delete next[id]
          hasChanges = true
        }
      })
      return hasChanges ? next : prev
    })
  }, [])

  /**
   * 验证工作流
   * @param nextWorkflows - 所有工作流列表
   * @param targetIds - 可选，只验证指定 ID 的工作流。不传则验证全部并清理已删除的
   */
  const validateWorkflows = useCallback(
    async (nextWorkflows: WorkflowDetail[], targetIds?: string[]) => {
      if (!spaceId) return

      const seq = ++validationSeqRef.current

      // 确定要验证的工作流
      const toValidate = targetIds
        ? nextWorkflows.filter(w => targetIds.includes(w.workflow_id))
        : nextWorkflows

      if (toValidate.length === 0) return

      setValidationResults(prev => {
        const next: Record<string, WorkflowValidationResult> = { ...prev }

        // 只在全量验证时清理已删除的工作流
        if (!targetIds) {
          const currentIds = new Set(nextWorkflows.map(w => w.workflow_id))
          Object.keys(next).forEach(id => {
            if (!currentIds.has(id)) delete next[id]
          })
        }

        // 设置待验证工作流的状态为 loading
        toValidate.forEach(w => {
          next[w.workflow_id] = { status: 'loading' }
        })
        return next
      })

      const apiClient = getApiClient()
      await Promise.all(
        toValidate.map(async w => {
          const version = w.workflow_version || 'draft'
          try {
            await apiClient.post(API_ENDPOINTS.EXECUTION.WORKFLOW_VALIDATE, {
              id: w.workflow_id,
              version,
              space_id: spaceId,
            })
            if (validationSeqRef.current !== seq) return
            setValidationResults(prev => ({ ...prev, [w.workflow_id]: { status: 'success' } }))
          } catch (err: unknown) {
            const message = (err as any)?.response?.data?.message || (err as any)?.response?.data?.msg || (err as any)?.message || '工作流校验失败'
            if (validationSeqRef.current !== seq) return
            setValidationResults(prev => ({ ...prev, [w.workflow_id]: { status: 'error', message } }))
          }
        }),
      )
    },
    [spaceId],
  )

  return { validationResults, setValidationResults, validateWorkflows, isValidating, workflowValidationErrorCount, cleanupDeletedWorkflows }
}
