import React, { useMemo } from 'react'
import dayjs from 'dayjs'
import type { TraceSummaryBriefWithStatus, ActiveExecution } from '@test-agentstudio/api-client'
import ExecutionStatusBadge from './ExecutionStatusBadge'
import { CircularProgress } from '@mui/material'

interface ExecutionListProps {
  traces: TraceSummaryBriefWithStatus[]
  activeExecutions: ActiveExecution[]
  selectedTraceId: string | null
  onSelect: (traceId: string) => void
  isLoading: boolean
}

const formatDuration = (ms?: number): string => {
  if (ms == null) return '-'
  const n = Number(ms) || 0
  if (n < 1000) return `${n}ms`
  if (n < 60000) return `${(n / 1000).toFixed(1)}s`
  return `${(n / 60000).toFixed(1)}m`
}

const formatElapsed = (startTime?: number): string => {
  if (!startTime) return '-'
  const elapsed = Math.floor((Date.now() / 1000 - startTime) * 1000)
  return formatDuration(elapsed)
}

const ExecutionList: React.FC<ExecutionListProps> = React.memo(({
  traces,
  activeExecutions,
  selectedTraceId,
  onSelect,
  isLoading,
}) => {
  // Merge active executions as synthetic "running" entries at the top
  const mergedList = useMemo(() => {
    // Create synthetic entries for active executions not already in the trace list
    // Show active executions in both tabs since agents also run workflows
    const syntheticEntries: TraceSummaryBriefWithStatus[] = activeExecutions
      .map(exec => ({
        trace_id: `active-${exec.conversation_id}`,
        business_id: exec.workflow_id,
        business_name: exec.workflow_name,
        business_version: exec.workflow_version,
        business_type: 'WORKFLOW' as const,
        create_time: exec.start_time
          ? new Date(exec.start_time * 1000).toISOString()
          : new Date().toISOString(),
        duration: exec.start_time
          ? Math.floor((Date.now() / 1000 - exec.start_time) * 1000)
          : undefined,
        status: 'running',
      }))

    // Also mark existing traces as running if their business_id matches an active execution
    const activeWorkflowIds = new Set(activeExecutions.map(e => e.workflow_id))
    const updatedTraces = traces.map(t => {
      if (activeWorkflowIds.has(t.business_id) && (!t.status || t.status === 'start')) {
        return { ...t, status: 'running' }
      }
      return t
    })

    // Combine: synthetic running entries + DB traces (dedup by business_id for running)
    const combined = [...syntheticEntries, ...updatedTraces]

    // Sort: running first, then by create_time desc
    return combined.sort((a, b) => {
      const aRunning = a.status === 'running' || a.status === 'start'
      const bRunning = b.status === 'running' || b.status === 'start'
      if (aRunning && !bRunning) return -1
      if (!aRunning && bRunning) return 1
      return dayjs(b.create_time).valueOf() - dayjs(a.create_time).valueOf()
    })
  }, [traces, activeExecutions])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <CircularProgress size={24} />
      </div>
    )
  }

  if (mergedList.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
        No executions found
      </div>
    )
  }

  return (
    <div className="flex flex-col overflow-y-auto">
      {mergedList.map(trace => {
        const isSelected = trace.trace_id === selectedTraceId
        const isRunning = trace.status === 'running' || trace.status === 'start'

        return (
          <div
            key={trace.trace_id}
            onClick={() => onSelect(trace.trace_id)}
            className={`
              px-3 py-2.5 cursor-pointer border-b border-gray-100 transition-colors
              hover:bg-gray-50
              ${isSelected ? 'bg-blue-50 border-l-2 border-l-blue-500' : 'border-l-2 border-l-transparent'}
              ${isRunning ? 'bg-blue-50/30' : ''}
            `}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-800 truncate" title={trace.business_name || trace.business_id}>
                {trace.business_name || trace.business_id.slice(0, 8) + '...'}
              </span>
              <ExecutionStatusBadge status={trace.status} />
            </div>
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>{dayjs(trace.create_time).format('MM/DD HH:mm:ss')}</span>
              <span className="font-mono">
                {isRunning ? formatElapsed(
                  trace.create_time ? new Date(trace.create_time).getTime() / 1000 : undefined
                ) : formatDuration(trace.duration)}
              </span>
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
              <span>{trace.business_type === 'WORKFLOW' ? 'Workflow' : 'Agent'}</span>
              {trace.business_version && trace.business_version !== 'draft' && (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg>
                  <span>{trace.business_version}</span>
                </>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
})

export default React.memo(ExecutionList)
