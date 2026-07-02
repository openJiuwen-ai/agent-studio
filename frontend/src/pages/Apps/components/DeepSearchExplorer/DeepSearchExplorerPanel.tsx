import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Maximize2, Minimize2, Square } from 'lucide-react'
import DeepSearchExplorerView from './DeepSearchExplorerView'
import { Action } from './ActionQueue'
import { Entity, CandidateEntity, ActionToolCall } from './EntityPanel'
import * as api from './api'
import { deriveEntitiesFromActionInfo } from './deriveActionEntities'
import { killDeepSearchExplorerRun } from '../../utils/deepSearchExplorerRunManagement'
import type {
  RunStatusResponse,
  ActionResponse,
  ActionInfoResponse,
  EntitiesResponse,
} from './types'

// ── Helpers ──

function mapEntities(
  res: EntitiesResponse,
): { knownEntities: Entity[]; unknownEntities: Entity[] } {
  const known: Entity[] = []
  const unknown: Entity[] = []
  for (const ev of res.entities) {
    const base: Entity = {
      name: ev.type,
      type: ev.type,
      discoveredClues: ev.discovered_clues,
      targetAnswer: ev.id === res.answer_variable,
    }
    if (ev.candidate != null) {
      known.push({ ...base, value: ev.candidate })
    } else {
      unknown.push(base)
    }
  }
  return { knownEntities: known, unknownEntities: unknown }
}

function mapActionsToQueue(actions: ActionResponse[]): Action[] {
  const result: Action[] = []

  const pending = actions.filter((a) => a.type === 'pending')
  const running = actions.filter((a) => a.type === 'running')
  const completed = actions.filter((a) => a.type === 'completed')

  const sortedPending = [...pending].sort((a, b) => b.score - a.score)
  sortedPending.forEach((entry, index) => {
    result.push({
      id: entry.action_id,
      type: 'query',
      description: entry.action_proposal,
      status: 'pending',
      priority: sortedPending.length - index,
      target: entry.depth != null ? `Depth ${entry.depth}` : undefined,
      score: entry.score,
      stateDepth: entry.depth ?? undefined,
    })
  })

  const sortedRunning = [...running].sort((a, b) => b.score - a.score)
  sortedRunning.forEach((entry, index) => {
    result.push({
      id: entry.action_id,
      type: 'query',
      description: entry.action_proposal,
      status: 'running',
      priority: sortedRunning.length - index,
      target: entry.depth != null ? `Depth ${entry.depth}` : undefined,
      score: entry.score,
      stateDepth: entry.depth ?? undefined,
    })
  })

  completed.forEach((entry, index) => {
    result.push({
      id: entry.action_id,
      type: entry.had_result ? 'expand' : 'filter',
      description: entry.action_proposal,
      status: 'completed',
      priority: completed.length - index,
      target: entry.depth != null ? `Depth ${entry.depth}` : undefined,
      score: entry.score,
      stateDepth: entry.depth ?? undefined,
    })
  })

  return result
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function parseToolCallsFromActionInfo(info: ActionInfoResponse): ActionToolCall[] {
  if (!isRecord(info.result)) {
    return []
  }

  const result = info.result as Record<string, unknown>
  const history = Array.isArray(result.tool_calls_history)
    ? result.tool_calls_history
    : Array.isArray(result.tool_calls)
      ? result.tool_calls
      : []

  const seen = new Set<string>()
  const parsed: ActionToolCall[] = []

  for (const item of history) {
    if (!isRecord(item)) continue
    const tool = typeof item.tool === 'string' && item.tool.trim()
      ? item.tool.trim()
      : typeof item.name === 'string' && item.name.trim()
        ? item.name.trim()
        : 'tool_call'
    const query = typeof item.query === 'string' && item.query.trim()
      ? item.query.trim()
      : typeof item.urls === 'string' && item.urls.trim()
        ? item.urls.trim()
        : ''
    if (!query) continue
    const key = `${tool}::${query}`
    if (seen.has(key)) continue
    seen.add(key)
    parsed.push({ tool, query })
  }

  return parsed
}

const API_POLL_INTERVAL_MS = 3000
const TERMINAL_STATUSES = new Set(['completed', 'failed', 'killed', 'cancelled', 'aborted'])
const ELAPSED_STORAGE_PREFIX = 'deepsearch.elapsed.'

const EMPTY_ACTION_ENTITIES: {
  knownEntities: Entity[]
  unknownEntities: Entity[]
  candidateEntities: CandidateEntity[]
} = {
  knownEntities: [],
  unknownEntities: [],
  candidateEntities: [],
}

// ── Props ──

export interface DeepSearchExplorerPanelProps {
  /** The question submitted by the user (triggers a new run). */
  question?: string | null
  /** Backend payload required when creating a run from question. */
  runConfig?: Record<string, unknown> | null
  /** An existing run ID to poll (skips run creation). */
  runId?: string | null
  /** Called when the user clicks the close button. */
  onClose?: () => void
  /** Whether the panel is in fullscreen mode. */
  isFullscreen?: boolean
  /** Called when the user toggles fullscreen. */
  onToggleFullscreen?: () => void
  /** Called when a run is killed from explorer. */
  onKilled?: (runId: string) => void
}

/**
 * DeepSearchExplorerPanel — container with Summary/Explorer tab switch.
 * Manages Deep Search API polling and passes data to child views.
 */
export default function DeepSearchExplorerPanel({
  question,
  runConfig,
  runId: externalRunId,
  onClose,
  isFullscreen = false,
  onToggleFullscreen,
  onKilled,
}: DeepSearchExplorerPanelProps) {
  const { t } = useTranslation()

  // ── Run state ──
  const [runId, setRunId] = useState<string | null>(null)
  const [runStatus, setRunStatus] = useState<RunStatusResponse | null>(null)
  const [actions, setActions] = useState<Action[]>([])
  const [selectedAction, setSelectedAction] = useState<Action | null>(null)

  const actionInfoCache = useRef<Map<string, ActionInfoResponse>>(new Map())

  const [actionEntities, setActionEntities] = useState<{
    knownEntities: Entity[]
    unknownEntities: Entity[]
    candidateEntities: CandidateEntity[]
  } | null>(null)
  const [actionToolCalls, setActionToolCalls] = useState<ActionToolCall[] | null>(null)

  const [runEntities, setRunEntities] = useState<{
    knownEntities: Entity[]
    unknownEntities: Entity[]
  } | null>(null)

  // ── Elapsed timer ──
  const runStartTimeRef = useRef<number | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const elapsedStorageKey = runId ? `${ELAPSED_STORAGE_PREFIX}${runId}` : null

  useEffect(() => {
    if (!runId) {
      setElapsedSeconds(0)
      runStartTimeRef.current = null
      return
    }

    try {
      const raw = window.localStorage.getItem(`${ELAPSED_STORAGE_PREFIX}${runId}`)
      const saved = raw ? Number(raw) : Number.NaN
      const initialSeconds = Number.isFinite(saved) && saved >= 0 ? Math.floor(saved) : 0
      setElapsedSeconds(initialSeconds)
      runStartTimeRef.current = Date.now() - initialSeconds * 1000
    } catch {
      setElapsedSeconds(0)
      runStartTimeRef.current = Date.now()
    }
  }, [runId])

  useEffect(() => {
    if (!runId || runStartTimeRef.current === null) return
    if (runStatus?.status && TERMINAL_STATUSES.has(runStatus.status)) return
    const id = setInterval(() => {
      const nextElapsed = Math.max(0, Math.floor((Date.now() - runStartTimeRef.current!) / 1000))
      setElapsedSeconds(nextElapsed)
      if (elapsedStorageKey) {
        try {
          window.localStorage.setItem(elapsedStorageKey, String(nextElapsed))
        } catch {
          // Ignore storage errors and continue showing in-memory elapsed time.
        }
      }
    }, 1000)
    return () => clearInterval(id)
  }, [elapsedStorageKey, runId, runStatus?.status])

  // ── Use external runId when provided ──
  useEffect(() => {
    if (!externalRunId || externalRunId === runId) return
    setRunId(externalRunId)
    setRunStatus(null)
    setActions([])
    setSelectedAction(null)
    setActionEntities(null)
    setActionToolCalls(null)
    setRunEntities(null)
    actionInfoCache.current.clear()
  }, [externalRunId])

  // ── Create a new run when question changes (only if no external runId) ──
  const prevQuestionRef = useRef<string | null>(null)

  useEffect(() => {
    if (externalRunId) return // Skip run creation when using external runId
    if (!question || question === prevQuestionRef.current) return
    prevQuestionRef.current = question

    const startRun = async () => {
      try {
        if (!runConfig) {
          console.warn('DeepSearchExplorerPanel: runConfig is required when creating a run from question')
          return
        }
        const result = await api.createRun(question, runConfig)
        setRunId(result.run_id)
        setRunStatus(null)
        setActions([])
        setSelectedAction(null)
        setActionEntities(null)
        setActionToolCalls(null)
        setRunEntities(null)
        actionInfoCache.current.clear()
      } catch (e) {
        console.error('Failed to create Deep Search run:', e)
      }
    }

    startRun()
  }, [question, runConfig, externalRunId])

  // ── Polling ──

  const fetchRunData = useCallback(async () => {
    if (!runId) return
    try {
      const [status, actionsRes] = await Promise.all([
        api.getRunStatus(runId),
        api.getActions(runId),
      ])
      setRunStatus(status)
      setActions(mapActionsToQueue(actionsRes))

      try {
        const entitiesRes = await api.getEntities(runId)
        setRunEntities(mapEntities(entitiesRes))
      } catch {
        // Will retry on next poll
      }

      if (selectedAction) {
        let selectedInfo: ActionInfoResponse | null = null
        try {
          selectedInfo = await api.getActionInfo(runId, selectedAction.id)
          actionInfoCache.current.set(selectedAction.id, selectedInfo)
        } catch (error) {
          console.error('Error refreshing selected action info:', error)
        }
        if (selectedInfo) {
          setActionEntities(deriveEntitiesFromActionInfo(selectedInfo))
          setActionToolCalls(parseToolCallsFromActionInfo(selectedInfo))
        }
      }
    } catch (e) {
      console.error('Error fetching run data:', e)
    }
  }, [runId, selectedAction])

  const isRunTerminal = !!runStatus?.status && TERMINAL_STATUSES.has(runStatus.status)

  useEffect(() => {
    if (!runId || !isRunTerminal || !elapsedStorageKey) return
    let isCancelled = false

    api.getAnswers(runId)
      .then((answerList) => {
        if (isCancelled) return
        const completionTimes = answerList
          .map((answer) => answer.completion_time)
          .filter((value): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0)

        if (completionTimes.length === 0) {
          return
        }

        const finalElapsedSeconds = Math.floor(Math.max(...completionTimes))
        if (finalElapsedSeconds <= 0) {
          return
        }

        setElapsedSeconds((prev) => (prev === finalElapsedSeconds ? prev : finalElapsedSeconds))
        try {
          window.localStorage.setItem(elapsedStorageKey, String(finalElapsedSeconds))
        } catch {
          // Ignore storage errors and continue showing in-memory elapsed time.
        }
      })
      .catch((error) => {
        console.error('Error fetching answers for elapsed time sync:', error)
      })

    return () => {
      isCancelled = true
    }
  }, [elapsedStorageKey, isRunTerminal, runId])

  useEffect(() => {
    if (!runId || isRunTerminal) return
    fetchRunData()
    const interval = setInterval(fetchRunData, API_POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [runId, fetchRunData, isRunTerminal])

  // ── Handlers ──

  const fetchActionInfo = useCallback(
    async (actionId: string) => {
      if (!runId) return null
      try {
        const info = await api.getActionInfo(runId, actionId)
        actionInfoCache.current.set(actionId, info)
        return info
      } catch (e) {
        console.error('Error fetching action info:', e)
        return null
      }
    },
    [runId],
  )

  const handleActionClick = async (action: Action) => {
    setSelectedAction(action)
    setActionEntities(EMPTY_ACTION_ENTITIES)
    setActionToolCalls([])

    const info = await fetchActionInfo(action.id)
    if (info) {
      setActionEntities(deriveEntitiesFromActionInfo(info))
      setActionToolCalls(parseToolCallsFromActionInfo(info))
    } else {
      setActionEntities(EMPTY_ACTION_ENTITIES)
      setActionToolCalls([])
    }
  }

  const handlePause = (actionId: string) => {
    setActions((prev) =>
      prev.map((a) =>
        a.id === actionId ? { ...a, status: 'paused' as const } : a,
      ),
    )
  }

  const handleResume = (actionId: string) => {
    setActions((prev) =>
      prev.map((a) =>
        a.id === actionId ? { ...a, status: 'running' as const } : a,
      ),
    )
  }

  const handleUpvote = (actionId: string) => {
    setActions((prev) =>
      prev.map((a) =>
        a.id === actionId ? { ...a, priority: Math.min(10, a.priority + 1) } : a,
      ),
    )
  }

  const handleDownvote = (actionId: string) => {
    setActions((prev) =>
      prev.map((a) =>
        a.id === actionId ? { ...a, priority: Math.max(1, a.priority - 1) } : a,
      ),
    )
  }

  const handleDelete = (actionId: string) => {
    setActions((prev) => prev.filter((a) => a.id !== actionId))
    if (selectedAction?.id === actionId) {
      setSelectedAction(null)
      setActionEntities(null)
      setActionToolCalls(null)
    }
  }

  const handleReorder = (dragIndex: number, hoverIndex: number, status: Action['status']) => {
    setActions((prev) => {
      const statusActions = prev.filter((a) => a.status === status)
      const otherActions = prev.filter((a) => a.status !== status)
      const dragged = statusActions[dragIndex]
      const reordered = [...statusActions]
      reordered.splice(dragIndex, 1)
      reordered.splice(hoverIndex, 0, dragged)
      const withPriorities = reordered.map((a, i) => ({
        ...a,
        priority: reordered.length - i,
      }))
      return [...otherActions, ...withPriorities]
    })
  }

  const handleEditAction = (actionId: string, newDescription: string) => {
    setActions((prev) =>
      prev.map((a) =>
        a.id === actionId ? { ...a, description: newDescription } : a,
      ),
    )
  }

  // ── Kill & Reset handlers ──

  const handleKill = async () => {
    if (!runId) return
    try {
      await killDeepSearchExplorerRun(runId, api.killRun)
      setRunStatus((prev) => (prev ? { ...prev, status: 'cancelled' } : prev))
      onKilled?.(runId)
    } catch (e) {
      console.error('Failed to kill run:', e)
    }
  }



  const isRunning = runStatus?.status === 'running' || actions.some((a) => a.status === 'running')

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header with title and close button */}
      <div className="
        h-[52px]
        flex-shrink-0
        bg-white
        shadow-[0px_1px_8px_0px_#1919190F]
        px-4
        flex items-center
        relative
        z-10
      ">
        {/* Title */}
        <span className="text-sm font-semibold text-gray-900">
          {t('apps.deepSearchExplorer.title', 'Deep Search Explorer')}
        </span>

        {/* Header right buttons */}
        <div className="ml-auto flex items-center gap-1">
          {/* Kill button */}
          <button
            onClick={handleKill}
            type="button"
            disabled={!runId || !runStatus || TERMINAL_STATUSES.has(runStatus.status)}
            className="
              h-7 px-2
              rounded-md
              flex items-center gap-1
              text-xs
              text-gray-500
              transition-colors duration-200
              hover:text-red-600 hover:bg-red-50
              disabled:opacity-40 disabled:cursor-not-allowed
              focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2
            "
            aria-label={t('apps.deepSearchExplorer.kill', 'Kill')}
          >
            <Square className="w-3.5 h-3.5" />
            <span>{t('apps.deepSearchExplorer.kill', 'Kill')}</span>
          </button>

          {/* Separator */}
          <div className="h-5 w-px bg-gray-200 mx-1" />

          {/* Fullscreen toggle */}
          {onToggleFullscreen && (
            <button
              onClick={onToggleFullscreen}
              type="button"
              className="
                w-9 h-9
                rounded-lg
                flex items-center justify-center
                text-gray-500
                transition-colors duration-200
                hover:text-gray-700 hover:bg-gray-100
                focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2
              "
              aria-label={isFullscreen
                ? t('apps.deepSearchExplorer.exitFullscreen', 'Exit fullscreen')
                : t('apps.deepSearchExplorer.fullscreen', 'Fullscreen')
              }
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          )}

          {/* Close button */}
          {onClose && (
            <button
              onClick={onClose}
              type="button"
              className="
                w-9 h-9
                rounded-lg
                flex items-center justify-center
                text-gray-500
                transition-colors duration-200
                hover:text-gray-700 hover:bg-gray-100
                focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2
              "
              aria-label={t('apps.deepSearchExplorer.close', 'Close')}
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Explorer content (no tab switch) */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <DeepSearchExplorerView
          actions={actions}
          selectedAction={selectedAction}
          onActionClick={handleActionClick}
          onPause={handlePause}
          onResume={handleResume}
          onUpvote={handleUpvote}
          onDownvote={handleDownvote}
          onDelete={handleDelete}
          onReorder={handleReorder}
          onEditAction={handleEditAction}
          actionEntities={actionEntities}
          actionToolCalls={actionToolCalls}
          runEntities={runEntities}
          currentQuestion={runStatus?.question}
          isRunning={isRunning}
          runStatus={runStatus?.status}
          runRoute={runStatus?.route}
          elapsedSeconds={elapsedSeconds}
        />
      </div>
    </div>
  )
}
