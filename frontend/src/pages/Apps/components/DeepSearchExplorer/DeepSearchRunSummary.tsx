import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Search, CheckCircle2, XCircle, Loader2, Compass, HelpCircle, ChevronDown } from 'lucide-react'
import * as api from './api'
import type { RunStatusResponse, ActionResponse, AnswerResponse, EntityVariable } from './types'

const POLL_INTERVAL_MS = 3000
const ELAPSED_STORAGE_PREFIX = 'deepsearch.elapsed.'

interface DeepSearchRunSummaryProps {
  runId: string
  onToggleExplorer?: () => void
  isExplorerOpen?: boolean
  forceFailed?: boolean
}

/**
 * DeepSearchRunSummary — compact summary of a Deep Search run.
 * Displayed in the conversation area below messages.
 * Polls the DS API for status, shows entities parsed from the question and action counts.
 */
export default function DeepSearchRunSummary({
  runId,
  onToggleExplorer,
  isExplorerOpen = false,
  forceFailed = false,
}: DeepSearchRunSummaryProps) {
  const { t } = useTranslation()

  const [runStatus, setRunStatus] = useState<RunStatusResponse | null>(null)
  const [actions, setActions] = useState<ActionResponse[]>([])
  const [answers, setAnswers] = useState<AnswerResponse[]>([])
  const [entities, setEntities] = useState<EntityVariable[]>([])
  const [entitiesOpen, setEntitiesOpen] = useState(true)
  const [collapsedEntityIds, setCollapsedEntityIds] = useState<Set<number>>(new Set())
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const runStartTimeRef = useRef(Date.now())
  const answersLoadedRef = useRef(false)

  const terminalStatuses = new Set(['completed', 'failed', 'killed', 'cancelled', 'aborted'])
  const isTerminal = forceFailed || (runStatus?.status ? terminalStatuses.has(runStatus.status) : false)
  const elapsedStorageKey = `${ELAPSED_STORAGE_PREFIX}${runId}`

  useEffect(() => {
    answersLoadedRef.current = false
    setAnswers([])
    try {
      const raw = window.localStorage.getItem(elapsedStorageKey)
      const saved = raw ? Number(raw) : Number.NaN
      const initialSeconds = Number.isFinite(saved) && saved >= 0 ? Math.floor(saved) : 0
      setElapsedSeconds(initialSeconds)
      runStartTimeRef.current = Date.now() - initialSeconds * 1000
    } catch {
      setElapsedSeconds(0)
      runStartTimeRef.current = Date.now()
    }
  }, [elapsedStorageKey])

  // Poll for status, actions, and entities
  const fetchData = useCallback(async () => {
    try {
      if (!forceFailed) {
        const [status, actionsRes] = await Promise.all([
          api.getRunStatus(runId),
          api.getActions(runId),
        ])
        setRunStatus(status)
        setActions(actionsRes)
      } else {
        setRunStatus((prev) => ({
          run_id: runId,
          question: prev?.question || '',
          status: 'failed',
        }))
      }

      // Keep entities in sync as telemetry progresses (candidate answers can appear later).
      try {
        const entitiesRes = await api.getEntities(runId)
        setEntities(entitiesRes.entities ?? [])
      } catch {
        // Will retry on next poll
      }
    } catch (e) {
      console.error('[DeepSearchRunSummary] poll error:', e)
    }
  }, [forceFailed, runId])

  useEffect(() => {
    if (isTerminal) return
    fetchData()
    const id = setInterval(fetchData, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [fetchData, isTerminal])

  // Fetch answers when run completes
  useEffect(() => {
    if ((!isTerminal && !forceFailed) || answersLoadedRef.current) return
    answersLoadedRef.current = true
    api.getAnswers(runId)
      .then(setAnswers)
      .catch((e) => console.error('[DeepSearchRunSummary] answers error:', e))
  }, [forceFailed, isTerminal, runId])

  useEffect(() => {
    setCollapsedEntityIds((prev) => {
      if (prev.size === 0) return prev
      const currentEntityIds = new Set(entities.map((entity) => entity.id))
      const next = new Set<number>()
      prev.forEach((id) => {
        if (currentEntityIds.has(id)) {
          next.add(id)
        }
      })
      return next.size === prev.size ? prev : next
    })
  }, [entities])

  // Elapsed timer
  useEffect(() => {
    if (isTerminal) return
    const id = setInterval(() => {
      const nextElapsed = Math.max(0, Math.floor((Date.now() - runStartTimeRef.current) / 1000))
      setElapsedSeconds(nextElapsed)
      try {
        window.localStorage.setItem(elapsedStorageKey, String(nextElapsed))
      } catch {
        // Ignore storage errors and continue showing in-memory elapsed time.
      }
    }, 1000)
    return () => clearInterval(id)
  }, [elapsedStorageKey, isTerminal])

  useEffect(() => {
    const completionTimes = answers
      .map((ans) => ans.completion_time)
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
  }, [answers, elapsedStorageKey])

  const completedActions = useMemo(
    () => actions.filter((a) => a.type === 'completed'),
    [actions],
  )
  const runningActions = useMemo(
    () => actions.filter((a) => a.type === 'running'),
    [actions],
  )

  const foundAnswer = useMemo(() => {
    const a = answers.find((ans) => ans.answer)
    return a?.answer ?? null
  }, [answers])

  const elapsedDisplay = `${Math.floor(elapsedSeconds / 60)}m ${elapsedSeconds % 60}s`

  const statusIcon = isTerminal
    ? runStatus?.status === 'completed'
      ? <CheckCircle2 className="w-5 h-5 text-green-500" />
      : <XCircle className="w-5 h-5 text-red-500" />
    : <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />

  const statusText = isTerminal
    ? runStatus?.status === 'completed'
      ? t('apps.deepSearchExplorer.runSummary.statusCompleted', 'Search completed')
      : t('apps.deepSearchExplorer.runSummary.statusFailed', 'Search failed')
    : t('apps.deepSearchExplorer.runSummary.statusRunning', 'Searching...')
  const routeName =
    runStatus?.route === 'simple'
      ? t('apps.deepSearchExplorer.routeSimpleAgent', 'Simple agent')
      : runStatus?.route === 'deepsearch'
        ? t('apps.deepSearchExplorer.routeDeepSearchAgent', 'DeepSearch agent')
        : t('apps.deepSearchExplorer.routeDetecting', 'Detecting...')

  useEffect(() => {
    if (runStatus?.route === 'simple' && isExplorerOpen && onToggleExplorer) {
      onToggleExplorer()
    }
  }, [isExplorerOpen, onToggleExplorer, runStatus?.route])

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[90%] bg-white rounded-lg px-4 py-3 shadow-sm border border-gray-200 w-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-semibold text-gray-900">
              {t('apps.deepSearchExplorer.runSummary.title', 'Deep Search')}
            </span>
          </div>

          {/* DeepSearch Explorer toggle button */}
          {onToggleExplorer && runStatus?.route !== 'simple' && (
            <button
              onClick={onToggleExplorer}
              className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
                isExplorerOpen
                  ? 'text-blue-600 bg-blue-50 hover:bg-blue-100'
                  : 'text-gray-500 hover:text-blue-500 hover:bg-blue-50'
              }`}
              title={t('apps.deepSearchExplorer.openExplorer', 'DeepSearch Explorer')}
            >
              <Compass className="w-4 h-4" />
              <span>{t('apps.deepSearchExplorer.openExplorer', 'DeepSearch Explorer')}</span>
            </button>
          )}
        </div>

        {/* Status row */}
        <div className="flex items-center gap-2 mb-3 text-sm">
          {statusIcon}
          <span className="text-gray-700">{statusText}</span>
          <span className="text-gray-500 text-xs ml-1">
            {t('apps.deepSearchExplorer.runSummary.routeLabel', 'Route: {{route}}', { route: routeName })}
          </span>
          <span className="text-gray-400 ml-auto text-xs">
            {t('apps.deepSearchExplorer.runSummary.elapsedTime', 'Elapsed: {{time}}', { time: elapsedDisplay })}
          </span>
        </div>

        {/* Entities parsed from the question */}
        {entities.length > 0 && (
          <div className="mb-3">
            <button
              type="button"
              onClick={() => setEntitiesOpen((prev) => !prev)}
              className="w-full flex items-center gap-1.5 mb-2 text-left rounded px-1 py-1 hover:bg-gray-50"
            >
              <ChevronDown className={`w-3.5 h-3.5 text-gray-500 transition-transform ${entitiesOpen ? '' : '-rotate-90'}`} />
              <HelpCircle className="w-3.5 h-3.5 text-orange-500" />
              <span className="text-xs font-medium text-gray-700">
                {t('apps.deepSearchExplorer.runSummary.entities', 'Entities')}
              </span>
              <span className="text-xs text-gray-400">({entities.length})</span>
            </button>
            {entitiesOpen && (
              <div className="space-y-2">
                {entities.map((entity) => {
                  const isCollapsed = collapsedEntityIds.has(entity.id)
                  const entityName = entity.type?.trim() || t('apps.deepSearchExplorer.runSummary.entityFallback', 'Entity {{id}}', { id: entity.id })
                  return (
                    <div
                      key={entity.id}
                      className={`rounded-md border px-3 py-2 ${
                        entity.candidate
                          ? 'bg-green-50 border-green-200'
                          : 'bg-orange-50 border-orange-200'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => {
                          setCollapsedEntityIds((prev) => {
                            const next = new Set(prev)
                            if (next.has(entity.id)) {
                              next.delete(entity.id)
                            } else {
                              next.add(entity.id)
                            }
                            return next
                          })
                        }}
                        className="w-full flex items-center justify-between gap-2 text-left"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-gray-800">{entityName}</span>
                          {entity.candidate ? (
                              <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                                {t('apps.deepSearchExplorer.runSummary.known', 'Known')}
                              </span>
                            ) : (
                              <span className="text-[10px] bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">
                                {t('apps.deepSearchExplorer.runSummary.unknown', 'Unknown')}
                              </span>
                            )}
                        </div>
                        <ChevronDown className={`w-3.5 h-3.5 text-gray-500 transition-transform ${isCollapsed ? '-rotate-90' : ''}`} />
                      </button>

                      {!isCollapsed && (
                        <>
                          {/* Description from question_clues */}
                          {entity.question_clues.length > 0 && (
                            <div className="text-xs text-gray-600 mt-1">
                              {entity.question_clues.join('; ')}
                            </div>
                          )}
                          {/* Discovered clues */}
                          {entity.discovered_clues.length > 0 && (
                            <div className="mt-1.5 flex flex-wrap gap-1">
                              {entity.discovered_clues.map((clue, i) => (
                                <span key={i} className="text-[10px] bg-white border border-gray-200 text-gray-600 rounded px-1.5 py-0.5">
                                  {clue}
                                </span>
                              ))}
                            </div>
                          )}
                          {/* Candidate value if known */}
                          {entity.candidate && (
                            <div className="text-xs font-mono text-green-800 mt-1 bg-green-100/60 rounded px-1.5 py-0.5 inline-block">
                              {entity.candidate}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Action counts (no progress bar) */}
        {actions.length > 0 && (
          <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
            <span>
              {t('apps.deepSearchExplorer.runSummary.actionsCompleted', '{{count}} actions completed', {
                count: completedActions.length,
              })}
            </span>
            {runningActions.length > 0 && (
              <span className="text-blue-500">
                {t('apps.deepSearchExplorer.runSummary.runningCount', '{{count}} running', { count: runningActions.length })}
              </span>
            )}
          </div>
        )}

        {/* No actions yet */}
        {actions.length === 0 && !isTerminal && (
          <div className="text-xs text-gray-400 mb-2">
            {t('apps.deepSearchExplorer.runSummary.noActionsYet', 'Starting search...')}
          </div>
        )}

        {/* Answer */}
        {foundAnswer && (
          <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 mt-2">
            <div className="text-xs font-medium text-green-700 mb-1">
              {t('apps.deepSearchExplorer.runSummary.answer', 'Answer')}
            </div>
            <div className="text-sm text-green-900">{foundAnswer}</div>
          </div>
        )}
      </div>
    </div>
  )
}
