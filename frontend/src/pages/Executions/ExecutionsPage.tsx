import React, { useEffect, useState, useCallback, useRef } from 'react'
import { Tabs, Tab, IconButton } from '@mui/material'
import { RefreshCcw } from 'lucide-react'
import { isEqual } from 'lodash-es'
import {
  ExecutionPanelService,
  type TraceSummaryBriefWithStatus,
  type ActiveExecution,
} from '@test-agentstudio/api-client'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import ExecutionList from '@/components/Executions/ExecutionList'
import ExecutionWaterfall, { type WaterfallDetail } from '@/components/Executions/ExecutionWaterfall'


const ExecutionsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'WORKFLOW' | 'AGENT'>('WORKFLOW')
  const [traces, setTraces] = useState<TraceSummaryBriefWithStatus[]>([])
  const [runningTraces, setRunningTraces] = useState<TraceSummaryBriefWithStatus[]>([])
  const [activeExecutions, setActiveExecutions] = useState<ActiveExecution[]>([])
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<WaterfallDetail | null>(null)
  const [listLoading, setListLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const detailPollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const spaceId = getDefaultSpaceId()

  const loadTraces = useCallback(async (isPolling = false) => {
    if (!isPolling) setListLoading(true)
    try {
      const res = await ExecutionPanelService.getTraceSummariesBySpace(spaceId, activeTab, 100)
      const newTraces = res?.data || []
      setTraces(prev => {
        if (isPolling && isEqual(prev, newTraces)) {
          return prev
        }
        return newTraces
      })
    } catch (e) {
      console.error('Failed to load traces:', e)
      if (!isPolling) setTraces([])
    } finally {
      if (!isPolling) setListLoading(false)
    }
  }, [spaceId, activeTab])

  const loadRunningTraces = useCallback(async (forceUpdate = false) => {
    try {
      const res = await ExecutionPanelService.getRunningTraces(spaceId, activeTab)
      const newRunningTraces = res?.data || []
      // Only update if data changed to prevent unnecessary re-renders
      setRunningTraces(prev => {
        if (!forceUpdate && isEqual(prev, newRunningTraces)) {
          return prev
        }
        return newRunningTraces
      })
    } catch {
      // Silently fail
    }
  }, [spaceId, activeTab])

  const loadActiveExecutions = useCallback(async () => {
    try {
      const res = await ExecutionPanelService.getActiveExecutions(spaceId)
      const newActiveExecutions = res?.data || []
      // Only update if data changed to prevent unnecessary re-renders
      setActiveExecutions(prev => {
        if (isEqual(prev, newActiveExecutions)) {
          return prev
        }
        return newActiveExecutions
      })
    } catch {
      // Silently fail
    }
  }, [spaceId])

  // Load detail - `isPolling` flag prevents flickering
  const loadDetail = useCallback(async (traceId: string, isPolling = false) => {
    if (!isPolling) setDetailLoading(true)
    try {
      if (traceId.startsWith('active-')) {
        const convId = traceId.replace('active-', '')
        const activeExec = activeExecutions.find(e => e.conversation_id === convId)
        const workflowId = activeExec?.workflow_id
        if (workflowId) {
          // Prefer the live TraceDetail-backed summary (new system) over the old debug endpoint
          const matchingTrace = runningTraces.find(rt => rt.business_id === workflowId)
          if (matchingTrace) {
            const res = await ExecutionPanelService.getTraceSummaryByTraceId(spaceId, matchingTrace.trace_id)
            setSelectedDetail(res?.data || null)
          } else {
            // Workflow uses old WorkflowExecutionDB system
            const res = await ExecutionPanelService.getWorkflowExecutionDebug(spaceId, workflowId)
            const summary = res?.data?.logSummary || res?.data?.log_summary
            const s = (summary as any)?.status
            const isTerminal = s === 'finish' || s === 'success' || s === 0 ||
              s === 'error' || s === 'fail' || s === 'failed' ||
              s === 'interrupted' || s === 'cancelled'
            // If the most recent log is a completed execution, the current run hasn't written yet
            setSelectedDetail(isTerminal ? null : (summary || null))
          }
        } else {
          setSelectedDetail(null)
        }
      } else if (traceId.startsWith('running-')) {
        // For DB-detected running traces, use the trace_id from the running trace
        const realTraceId = traceId.replace('running-', '')
        // Find the running trace to get business info
        const rt = runningTraces.find(t => t.trace_id === realTraceId)
        if (rt) {
          try {
            const res = await ExecutionPanelService.getTraceSummaryByTraceId(spaceId, realTraceId)
            setSelectedDetail(res?.data || null)
          } catch {
            // If trace summary doesn't exist yet, try debug endpoint
            if (rt.business_type === 'AGENT') {
              const res = await ExecutionPanelService.getAgentExecutionDebug(spaceId, rt.business_id)
              const summary = res?.data?.logSummary || res?.data?.log_summary
              setSelectedDetail(summary || null)
            } else {
              const res = await ExecutionPanelService.getWorkflowExecutionDebug(spaceId, rt.business_id)
              const summary = res?.data?.logSummary || res?.data?.log_summary
              setSelectedDetail(summary || null)
            }
          }
        } else {
          setSelectedDetail(null)
        }
      } else {
        // Completed traces - use trace_id lookup
        const res = await ExecutionPanelService.getTraceSummaryByTraceId(spaceId, traceId)
        setSelectedDetail(res?.data || null)
      }
    } catch (e) {
      console.error('Failed to load execution detail:', e)
      if (!isPolling) setSelectedDetail(null)
    } finally {
      if (!isPolling) setDetailLoading(false)
    }
  }, [spaceId, activeExecutions, runningTraces])

  // Load traces on mount and tab change
  useEffect(() => {
    setSelectedTraceId(null)
    setSelectedDetail(null)
    setTraces([])
    setRunningTraces([])
    loadTraces()
    loadRunningTraces()
  }, [activeTab, loadTraces, loadRunningTraces])

  // Auto-select first trace when data loads
  useEffect(() => {
    if (!selectedTraceId) {
      // Prefer running traces, then completed
      if (runningTraces.length > 0) {
        setSelectedTraceId(`running-${runningTraces[0].trace_id}`)
      } else if (traces.length > 0) {
        setSelectedTraceId(traces[0].trace_id)
      }
    }
  }, [traces, runningTraces])

  // Poll running traces + active executions every 5 seconds (only while page is visible)
  useEffect(() => {
    const startPolling = () => {
      if (pollRef.current) clearInterval(pollRef.current)
      loadActiveExecutions()
      loadRunningTraces()
      loadTraces(true)
      pollRef.current = setInterval(() => {
        loadActiveExecutions()
        loadRunningTraces()
        loadTraces(true)
      }, 5000)
    }

    const stopPolling = () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    }

    const handleVisibility = () => {
      if (document.hidden) stopPolling()
      else startPolling()
    }

    startPolling()
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [loadActiveExecutions, loadRunningTraces, loadTraces])

  // Load detail when selection changes
  useEffect(() => {
    if (selectedTraceId) {
      loadDetail(selectedTraceId)
    } else {
      setSelectedDetail(null)
    }
  }, [selectedTraceId, loadDetail])

  // Poll detail for running executions - no flicker, pauses when tab hidden
  useEffect(() => {
    const isActive = selectedTraceId?.startsWith('active-') || selectedTraceId?.startsWith('running-')
    const isRunningStatus = selectedDetail && (
      selectedDetail.status === 2 || selectedDetail.status === 'running' || selectedDetail.status === 'start'
    )
    const shouldPoll = (isActive || isRunningStatus) && selectedTraceId

    const startDetailPoll = () => {
      if (detailPollRef.current) clearInterval(detailPollRef.current)
      if (shouldPoll) {
        detailPollRef.current = setInterval(() => {
          loadDetail(selectedTraceId!, true)
        }, 3000)
      }
    }

    const stopDetailPoll = () => {
      if (detailPollRef.current) { clearInterval(detailPollRef.current); detailPollRef.current = null }
    }

    const handleVisibility = () => {
      if (document.hidden) stopDetailPoll()
      else startDetailPoll()
    }

    startDetailPoll()
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      stopDetailPoll()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [selectedDetail?.status, selectedTraceId, loadDetail])

  const handleRefresh = () => {
    loadTraces()
    loadRunningTraces()
    loadActiveExecutions()
    if (selectedTraceId) loadDetail(selectedTraceId)
  }

  // Merge running traces into the list
  const mergedTraces: TraceSummaryBriefWithStatus[] = React.useMemo(() => {
    const completedTraceIds = new Set(traces.map(t => t.trace_id))
    // Running traces from DB that aren't already in the completed list
    const uniqueRunning = runningTraces
      .filter(rt => !completedTraceIds.has(rt.trace_id))
      .map(rt => ({
        ...rt,
        trace_id: `running-${rt.trace_id}`,
        status: 'running',
      }))
    return [...uniqueRunning, ...traces]
  }, [traces, runningTraces])

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-3 pb-0 shrink-0">
        <h1 className="text-lg font-semibold text-gray-800">Executions</h1>
        <IconButton size="small" onClick={handleRefresh} title="Refresh">
          <RefreshCcw size={16} />
        </IconButton>
      </div>

      {/* Tabs */}
      <div className="px-4 shrink-0">
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          sx={{ minHeight: 36, '& .MuiTab-root': { minHeight: 36, py: 0.5, textTransform: 'none', fontSize: '0.875rem' } }}
        >
          <Tab label="Workflows" value="WORKFLOW" />
          <Tab label="Agents" value="AGENT" />
        </Tabs>
      </div>

      {/* Main content: split panel */}
      <div className="flex flex-1 overflow-hidden border-t border-gray-200">
        {/* Left: execution list */}
        <div className="w-[320px] min-w-[280px] max-w-[400px] border-r border-gray-200 overflow-y-auto bg-white">
          <ExecutionList
            traces={mergedTraces}
            activeExecutions={activeTab === 'WORKFLOW' ? activeExecutions : []}
            selectedTraceId={selectedTraceId}
            onSelect={setSelectedTraceId}
            isLoading={listLoading}
          />
        </div>

        {/* Right: waterfall detail */}
        <div className="flex-1 overflow-hidden">
          <ExecutionWaterfall detail={selectedDetail} isLoading={detailLoading} />
        </div>
      </div>
    </div>
  )
}

export default ExecutionsPage
