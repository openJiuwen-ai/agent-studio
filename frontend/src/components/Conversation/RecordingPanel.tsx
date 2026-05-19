import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Check,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  DownloadCloud,
  Eye,
  EyeOff,
  History,
  Loader2,
  MessageSquareText,
  Pause,
  Play,
  RefreshCw,
  Search,
  Sparkles,
  Square,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import {
  RECORDING_EVENTS,
  addRecordingEventListener,
  isFuzzyRewriteRequestMatch,
  isRelaxedRewriteRequestMatch,
  isSameRewriteRequest,
  usePlayback,
  useRecordingList,
  useRecordingModule,
  type MockResultEventDetail,
} from '../../modules/recording'
import { useConversationStore } from '../../stores/useConversationStore'
import { MessageType, TaskStatus } from '../../stores/useConversationStore'
import type {
  InteractionEvent,
  RewriteMockDiagnostic,
  RecordingSession,
  RewriteEvent,
  RewriteRequest,
  SSEData,
} from '../../modules/recording/types'

interface RecordingPanelProps {
  onClose: () => void
  onPlaybackStart: (conversationId: string) => Promise<string>
}

interface DebugReport {
  id: string
  name: string
  timestamp: number
  content: string
}

interface RewriteMockStatus {
  id: string
  rewriteEvent: RewriteEvent
  status: 'pending' | 'matched' | 'not-matched'
  diagnostic?: RewriteMockDiagnostic | null
}

const findMatchedStatusIndex = (
  items: RewriteMockStatus[],
  request: RewriteRequest
): number =>
  items.findIndex((item) =>
    item.status !== 'matched' &&
    (isSameRewriteRequest(item.rewriteEvent.request, request) ||
      isRelaxedRewriteRequestMatch(item.rewriteEvent.request, request))
  )

const findNotMatchedStatusIndex = (
  items: RewriteMockStatus[],
  request: RewriteRequest
): number => {
  const fuzzyIndex = items.findIndex((item) =>
    item.status === 'pending' &&
    isFuzzyRewriteRequestMatch(item.rewriteEvent.request, request)
  )
  if (fuzzyIndex !== -1) {
    return fuzzyIndex
  }

  const sameActionIndexes = items.reduce<number[]>((indexes, item, index) => {
    if (
      item.status === 'pending' &&
      item.rewriteEvent.request.action === request.action
    ) {
      indexes.push(index)
    }
    return indexes
  }, [])

  return sameActionIndexes.length === 1
    ? sameActionIndexes[0]
    : -1
}

const getInteractionKindLabel = (t: (key: string) => string, kind: InteractionEvent['kind']) =>
  kind === 'outline' ? t('apps.deepSearch.playback.outlineInteraction') : 'HITL'

const getInteractionFeedbackLabel = (t: (key: string) => string, feedback: string) => {
  switch (feedback) {
    case 'accepted':
      return t('apps.deepSearch.playback.acceptedContinue')
    case 'revise_comment':
      return t('apps.deepSearch.playback.reviseComment')
    default:
      return feedback
  }
}

const getRewriteMismatchLabel = (t: (key: string) => string, reason: NonNullable<RewriteMockDiagnostic['mismatchReasons']>[number]) => {
  switch (reason) {
    case 'action':
      return t('apps.deepSearch.playback.mismatchAction')
    case 'selectedText':
      return t('apps.deepSearch.playback.mismatchSelectedText')
    case 'offset':
      return t('apps.deepSearch.playback.mismatchOffset')
    case 'userInstruction':
      return t('apps.deepSearch.playback.mismatchUserInstruction')
    default:
      return reason
  }
}

export default function RecordingPanel({ onClose, onPlaybackStart }: RecordingPanelProps) {
  const { t, i18n } = useTranslation()
  const [recordingsExpanded, setRecordingsExpanded] = useState(true)
  const [reportsExpanded, setReportsExpanded] = useState(true)
  const [selectedRecordingId, setSelectedRecordingId] = useState<string | null>(null)
  const [selectedRecording, setSelectedRecording] = useState<RecordingSession | null>(null)
  const [mockModeEnabled, setMockModeEnabled] = useState(false)
  const [isHidden, setIsHidden] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [debugReports, setDebugReports] = useState<DebugReport[]>([])
  const [rewriteMockStatuses, setRewriteMockStatuses] = useState<RewriteMockStatus[]>([])

  const { play, pause, resume, stop, status: playbackStatus, progress: playbackProgress } = usePlayback()
  const { recordings, isLoading, refresh, deleteRecording, clearAll, getFullRecording } = useRecordingList(50)
  const { clearRewriteMockEvents, loadRewriteMockEvents, setRewriteMockEnabled } = useRecordingModule()

  const waitForPlaybackQueueFlush = useCallback(async () => {
    const maxAttempts = 120

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const state = useConversationStore.getState()
      if (!state.sseProcessingQueue && state.sseEventQueue.length === 0) {
        await new Promise((resolve) => requestAnimationFrame(() => resolve(undefined)))

        const nextState = useConversationStore.getState()
        if (!nextState.sseProcessingQueue && nextState.sseEventQueue.length === 0) {
          return
        }
      }

      await new Promise((resolve) => setTimeout(resolve, 16))
    }
  }, [])

  const replayInteractionReply = useCallback(async (conversationId: string, interaction: InteractionEvent) => {
    const conversationStore = useConversationStore.getState()
    const messageItemsList = conversationStore.getMessageItemsByConversationId(conversationId)

    const expectedMessageType =
      interaction.kind === 'outline'
        ? MessageType.OUTLINE_INTERACTION
        : MessageType.INTERRUPT

    const isInteractionPending = (status: TaskStatus) =>
      status === TaskStatus.IN_PROGRESS ||
      status === TaskStatus.PENDING ||
      status === TaskStatus.UNKNOWN

    let matchedMessageItemsId: string | null = null
    let matchedMessageId: string | null = null

    for (let i = messageItemsList.length - 1; i >= 0; i--) {
      const messageItems = messageItemsList[i]
      if (conversationStore.getMessageItemsIsUser(messageItems)) {
        continue
      }

      for (let j = messageItems.messagesIds.length - 1; j >= 0; j--) {
        const messageId = messageItems.messagesIds[j]
        const message = conversationStore.getMessageById(messageId)

        if (
          message &&
          message.type === expectedMessageType &&
          isInteractionPending(message.status)
        ) {
          matchedMessageItemsId = messageItems.id
          matchedMessageId = messageId
          break
        }
      }

      if (matchedMessageItemsId && matchedMessageId) {
        break
      }
    }

    if (matchedMessageItemsId && matchedMessageId) {
      conversationStore.updateMessage(matchedMessageItemsId, matchedMessageId, {
        status: TaskStatus.COMPLETED,
      })
      conversationStore.updateMessageItems(matchedMessageItemsId, {
        status: TaskStatus.COMPLETED,
      })
    }

    conversationStore.addUserMessage(conversationId, interaction.userMessage)
  }, [])

  useEffect(() => {
    if (!selectedRecordingId) {
      setSelectedRecording(null)
      setRewriteMockStatuses([])
      return
    }

    let cancelled = false

    getFullRecording(selectedRecordingId).then((recording) => {
      if (!cancelled) {
        setSelectedRecording(recording)
      }
    })

    return () => {
      cancelled = true
    }
  }, [getFullRecording, selectedRecordingId])

  useEffect(() => {
    if (!selectedRecordingId || !selectedRecording?.rewriteEvents) {
      setRewriteMockStatuses([])
      return
    }

    setRewriteMockStatuses(
      selectedRecording.rewriteEvents.map((rewriteEvent, index) => ({
        id: `${selectedRecordingId}-rewrite-${index}`,
        rewriteEvent,
        status: 'pending',
        diagnostic: null,
      }))
    )
  }, [selectedRecording, selectedRecordingId])

  useEffect(() => {
    if (!mockModeEnabled || !selectedRecording?.rewriteEvents?.length) {
      clearRewriteMockEvents()
      setRewriteMockEnabled(false)
      return
    }

    loadRewriteMockEvents(selectedRecording.rewriteEvents)
    setRewriteMockEnabled(true)
  }, [clearRewriteMockEvents, loadRewriteMockEvents, mockModeEnabled, selectedRecording, setRewriteMockEnabled])

  useEffect(() => {
    const handleMockResult = (detail: MockResultEventDetail) => {
      if (!mockModeEnabled || !detail?.request) return

      setRewriteMockStatuses((prev) => {
        const targetIndex = detail.matched
          ? findMatchedStatusIndex(prev, detail.request)
          : findNotMatchedStatusIndex(prev, detail.request)

        if (targetIndex === -1) return prev

        return prev.map((item, index) =>
          index === targetIndex
            ? {
                ...item,
                status: detail.matched ? 'matched' : 'not-matched',
                diagnostic: detail.matched ? null : detail.diagnostic ?? null,
              }
            : item
        )
      })
    }

    return addRecordingEventListener(RECORDING_EVENTS.MOCK_RESULT, handleMockResult)
  }, [mockModeEnabled])

  const filteredRecordings = useMemo(() => {
    if (!searchQuery) return recordings
    const query = searchQuery.toLowerCase()
    return recordings.filter((recording) => recording.query.toLowerCase().includes(query))
  }, [recordings, searchQuery])

  const formatTime = (timestamp: number) => {
    const locale = i18n.language === 'zh-CN' ? 'zh-CN' : 'en-US'
    return new Date(timestamp).toLocaleString(locale, {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
  }

  const resetStatuses = useCallback(() => {
    setRewriteMockStatuses((prev) => prev.map((item) => ({ ...item, status: 'pending' })))
  }, [])

  const resetMockQueue = useCallback(() => {
    if (selectedRecording?.rewriteEvents?.length) {
      loadRewriteMockEvents(selectedRecording.rewriteEvents)
    }
  }, [loadRewriteMockEvents, selectedRecording])

  const handlePlayback = useCallback(async () => {
    if (!selectedRecording) return

    try {
      const store = useConversationStore.getState()
      store.setSelectedResultMessageId(null)

      const existingPlaybackConversationId = Array.from(store.conversationsMap.entries()).find(
        ([, conversation]) => conversation.title === t('apps.deepSearch.playback.playbackConversation')
      )?.[0]

      if (existingPlaybackConversationId) {
        await store.deleteConversation(existingPlaybackConversationId)
      }

      const playbackConversationId = store.getOrCreatePlaybackConversation()
      await onPlaybackStart(playbackConversationId)
      await new Promise((resolve) => setTimeout(resolve, 100))
      store.addUserMessage(playbackConversationId, selectedRecording.query)
      setIsHidden(false)
      resetStatuses()
      resetMockQueue()

      await play(
        selectedRecording.id,
        async (sseData: SSEData) => {
          useConversationStore.getState().handleSSEMessage(sseData as any, playbackConversationId)
          await waitForPlaybackQueueFlush()
        },
        async (interaction) => {
          await replayInteractionReply(playbackConversationId, interaction)
        }
      )
    } catch (error) {
      console.error('[RecordingPanel] Playback failed:', error)
    }
  }, [onPlaybackStart, play, replayInteractionReply, resetMockQueue, resetStatuses, selectedRecording, waitForPlaybackQueueFlush])

  const handlePauseResume = useCallback(() => {
    if (playbackStatus === 'playing') pause()
    else if (playbackStatus === 'paused') resume()
  }, [pause, playbackStatus, resume])

  const handleStop = useCallback(() => {
    stop()
    clearRewriteMockEvents()
    setRewriteMockEnabled(false)
    setMockModeEnabled(false)
    resetStatuses()
  }, [clearRewriteMockEvents, resetStatuses, setRewriteMockEnabled, stop, setMockModeEnabled])

  const handleHide = useCallback(() => {
    setIsHidden(true)
  }, [])

  const handleShow = useCallback(() => {
    setIsHidden(false)
  }, [])

  const handleClosePanel = useCallback(() => {
    handleStop()
    setIsHidden(false)
    onClose()
  }, [handleStop, onClose])

  useEffect(() => () => {
    stop()
    clearRewriteMockEvents()
    setRewriteMockEnabled(false)
  }, [clearRewriteMockEvents, setRewriteMockEnabled, stop])

  const handleImportReport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const titleMatch = text.match(/^#\s+(.+)$/m)
      const name = titleMatch ? titleMatch[1].trim() : file.name.replace(/\.(md|markdown)$/, '')
      setDebugReports((prev) => [{ id: `debug-${Date.now()}`, name, timestamp: Date.now(), content: text }, ...prev])
      event.target.value = ''
    } catch (error) {
      console.error('[RecordingPanel] Failed to import report:', error)
      alert(t('apps.deepSearch.playback.importFailed') + (error as Error).message)
    }
  }

  const handleViewDebugReport = (report: DebugReport) => {
    const store = useConversationStore.getState()
    const currentConversationId = store.currentConversationId
    if (!currentConversationId) {
      alert(t('apps.deepSearch.playback.selectConversationFirst'))
      return
    }

    store.addUserMessage(currentConversationId, report.name)
    store.addSystemMessage(
      currentConversationId,
      MessageType.REPORT,
      { response_content: report.content, citation_messages: null, infer_messages: [] },
      undefined,
      t('apps.deepSearch.playback.finalReport'),
      'debug'
    )
    onClose()
  }

  const downloadJson = (filename: string, data: unknown) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const isPlaying = playbackStatus === 'playing' || playbackStatus === 'paused'
  const selectedInteractionCount = selectedRecording?.interactionEvents?.length || 0
  const selectedRewriteCount = selectedRecording?.rewriteEvents?.length || 0
  const matchedCount = rewriteMockStatuses.filter((item) => item.status === 'matched').length
  const notMatchedCount = rewriteMockStatuses.filter((item) => item.status === 'not-matched').length
  const pendingCount = rewriteMockStatuses.filter((item) => item.status === 'pending').length
  const playbackStatusLabel = isPlaying
    ? playbackStatus === 'playing'
      ? t('apps.deepSearch.playback.status.playing')
      : t('apps.deepSearch.playback.resume')
    : t('apps.deepSearch.playback.off')

  const handleDeleteSelectedRecording = useCallback(async () => {
    if (!selectedRecording) return
    if (!confirm(t('apps.deepSearch.playback.confirmDelete'))) return

    try {
      if (isPlaying) {
        handleStop()
      }
      setIsHidden(false)
      await deleteRecording(selectedRecording.id)
      setSelectedRecordingId(null)
    } catch (error) {
      alert(t('apps.deepSearch.playback.deleteFailed') + (error as Error).message)
    }
  }, [deleteRecording, handleStop, isPlaying, selectedRecording, t])

  if (isHidden) {
    return (
      <div className="fixed bottom-6 right-6 z-40 w-[180px] rounded-2xl border border-slate-200/80 bg-white/96 p-2 shadow-[0_18px_40px_rgba(15,23,42,0.18)] backdrop-blur">
        <button
          onClick={handleShow}
          className="flex w-full min-w-0 items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 px-2.5 py-2 text-xs font-medium text-white shadow-sm transition-all duration-200 hover:from-blue-700 hover:to-purple-700"
          title={t('apps.deepSearch.playback.showPanel')}
        >
          <Eye className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{t('apps.chat.replayHistory')}</span>
        </button>
        {isPlaying && (
          <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50/90 p-2">
            <div className="flex items-center justify-between text-[10px] font-medium text-slate-500">
              <span>{playbackStatusLabel}</span>
              <span>{playbackProgress}%</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-600 to-purple-600 transition-all duration-300"
                style={{ width: `${playbackProgress}%` }}
              />
            </div>
            <div className="mt-2 flex items-center gap-1.5">
              <button
                onClick={handlePauseResume}
                className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-1.5 py-1.5 text-[11px] font-medium text-slate-600 transition-colors hover:bg-slate-100"
              >
                {playbackStatus === 'playing' ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                <span className="truncate">
                  {playbackStatus === 'playing'
                    ? t('apps.deepSearch.playback.pause')
                    : t('apps.deepSearch.playback.resume')}
                </span>
              </button>
              <button
                onClick={handleStop}
                className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-1.5 py-1.5 text-[11px] font-medium text-slate-600 transition-colors hover:bg-slate-100"
              >
                <Square className="h-3 w-3" />
                <span>{t('apps.deepSearch.playback.stop')}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 px-4 py-5 backdrop-blur-[2px] md:px-6">
      <div className="flex h-[min(86vh,760px)] w-full max-w-[1080px] overflow-hidden rounded-[22px] border border-slate-200/90 bg-white shadow-[0_24px_60px_rgba(15,23,42,0.18)]">
        <div className="flex w-full min-w-0 flex-col">
        <div className="flex items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 py-3.5">
          <div>
            <h2 className="text-[20px] font-semibold tracking-tight text-slate-950">
              {t('apps.deepSearch.playback.panelTitle')}
            </h2>
          </div>
          <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 p-1 shadow-sm">
            <button
              onClick={handleHide}
              className="rounded-xl px-3 py-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
              title={t('apps.deepSearch.playback.hidePanel')}
            >
              <EyeOff className="h-4 w-4" />
            </button>
            <button
              onClick={handleClosePanel}
              className="rounded-xl px-3 py-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          <div className="flex w-[188px] min-w-[188px] flex-col border-r border-slate-200 bg-[linear-gradient(180deg,_#fbfdff,_#f8fafc)] text-slate-900">
            <div className="border-b border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.1),_transparent_42%),linear-gradient(180deg,_#ffffff,_#f8fafc)] p-2.5">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder={t('apps.deepSearch.playback.searchPlaceholder')}
                  className="w-full rounded-xl border border-slate-200 bg-white py-1.5 pl-8.5 pr-3 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-blue-300"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-1.5">
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <button
                  onClick={() => setRecordingsExpanded((value) => !value)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left transition-colors hover:bg-slate-50"
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-slate-900">
                    <Clock className="h-4 w-4 text-slate-400" />
                    {t('apps.deepSearch.playback.recordingSessions')}
                  </span>
                  <span className="flex items-center gap-2 text-xs text-slate-400">
                    {filteredRecordings.length}
                    {recordingsExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </span>
                </button>
                {recordingsExpanded && (
                  <div className="border-t border-slate-100 px-2 pb-2 pt-1">
                    {isLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                      </div>
                    ) : filteredRecordings.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400">
                        {searchQuery
                          ? t('apps.deepSearch.playback.noMatchingRecordings')
                          : t('apps.deepSearch.playback.noRecordings')}
                      </div>
                    ) : filteredRecordings.map((recording) => (
                      <button
                        key={recording.id}
                        onClick={() => setSelectedRecordingId(recording.id)}
                        disabled={isPlaying}
                        className={`mt-1.5 w-full rounded-2xl border px-2.5 py-1.5 text-left transition-all ${
                          selectedRecordingId === recording.id
                            ? 'border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50 shadow-[0_10px_24px_rgba(59,130,246,0.12)]'
                            : 'border-slate-200 bg-slate-50/60 hover:border-slate-300 hover:bg-white'
                        } ${isPlaying ? 'cursor-not-allowed opacity-60' : ''}`}
                      >
                        <div className="truncate text-[13px] font-medium text-slate-900">
                          {recording.query}
                        </div>
                        <div className="mt-1.5 truncate text-[11px] text-slate-500">
                          {formatTime(recording.startTime)}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-2.5 overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <button
                  onClick={() => setReportsExpanded((value) => !value)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left transition-colors hover:bg-slate-50"
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-slate-900">
                    <Upload className="h-4 w-4 text-slate-400" />
                    {t('apps.deepSearch.playback.debugReports')}
                  </span>
                  <span className="flex items-center gap-2 text-xs text-slate-400">
                    {debugReports.length}
                    {reportsExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </span>
                </button>
                {reportsExpanded && (
                  <div className="border-t border-slate-100 px-2 pb-2 pt-1">
                    {debugReports.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 px-4 py-5 text-center text-sm text-slate-400">{t('apps.deepSearch.playback.noReports')}</div> : debugReports.map((report) => (
                      <div key={report.id} className="group flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50/60 px-2.5 py-2">
                        <button onClick={() => handleViewDebugReport(report)} className="min-w-0 flex-1 text-left">
                          <div className="truncate text-[13px] font-medium text-slate-900">{report.name}</div>
                        </button>
                        <button onClick={() => setDebugReports((prev) => prev.filter((item) => item.id !== report.id))} className="rounded-lg p-1.5 text-slate-400 opacity-0 transition-all hover:bg-slate-100 hover:text-rose-500 group-hover:opacity-100" title={t('apps.deepSearch.playback.buttons.delete')}>
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <label className="mx-2 mb-2 flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-slate-200 px-2.5 py-2 text-sm text-slate-600 transition-colors hover:border-slate-300 hover:bg-slate-50">
                  <Upload className="h-4 w-4" />{t('apps.deepSearch.playback.importMarkdown')}
                  <input type="file" accept=".md,.markdown" onChange={handleImportReport} className="hidden" />
                </label>
              </div>
            </div>
          </div>

          <div className="flex-1 flex flex-col overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(191,219,254,0.2),_transparent_28%),linear-gradient(180deg,_#ffffff,_#f8fafc_48%,_#f8fafc)]">
            {selectedRecording ? (
              <>
                <div className="border-b border-slate-200/80 px-4 py-3">
                  <h3 className="text-[18px] font-semibold tracking-tight text-slate-950">{selectedRecording.query}</h3>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-slate-500">
                    <span className="inline-flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-slate-400" />
                      {formatTime(selectedRecording.startTime)}
                    </span>
                    <span>{t('apps.deepSearch.playback.duration')}: {formatDuration(selectedRecording.duration)}</span>
                    {selectedInteractionCount > 0 && (
                      <span className="inline-flex items-center gap-1.5 text-indigo-700">
                        <MessageSquareText className="h-3.5 w-3.5" />
                        {t('apps.deepSearch.playback.interactionCount', { count: selectedInteractionCount })}
                      </span>
                    )}
                    {selectedInteractionCount === 0 && (
                      <span className="inline-flex items-center gap-1.5 text-slate-500">
                        <MessageSquareText className="h-3.5 w-3.5" />
                        {t('apps.deepSearch.playback.interactionCount', { count: 0 })}
                      </span>
                    )}
                    {selectedRewriteCount > 0 && (
                      <span className="inline-flex items-center gap-1.5 text-purple-700">
                        <Sparkles className="h-3.5 w-3.5" />
                        {t('apps.deepSearch.playback.rewritesCount', { count: selectedRewriteCount })}
                      </span>
                    )}
                  </div>
                </div>

                <div className={`grid gap-3.5 border-b border-slate-200/80 px-4 py-3.5 ${selectedRewriteCount > 0 ? 'xl:grid-cols-[minmax(0,1.35fr)_minmax(250px,0.85fr)]' : ''}`}>
                  <div className="relative overflow-hidden rounded-[20px] border border-slate-200 bg-white/90 p-3.5 shadow-[0_14px_34px_rgba(15,23,42,0.06)]">
                    <div className={`pointer-events-none absolute inset-x-0 top-0 h-px ${isPlaying ? 'bg-gradient-to-r from-blue-500/80 via-indigo-400/70 to-purple-500/80' : 'bg-slate-200/80'}`} />
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <div className="text-sm font-semibold text-slate-900">
                            {t('apps.deepSearch.playback.playRecording')}
                          </div>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                              isPlaying
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-slate-100 text-slate-500'
                            }`}
                          >
                            {isPlaying ? playbackStatusLabel : 'Ready'}
                          </span>
                        </div>
                        <p className="mt-0.5 text-[12px] text-slate-500">
                          {t('apps.deepSearch.playback.eventsCount', { count: selectedRecording.eventCount })}
                        </p>
                      </div>
                      <div className="ml-auto flex flex-wrap items-center gap-2">
                        <button onClick={async () => {
                          const recording = await getFullRecording(selectedRecording.id)
                          if (!recording) return
                          const dateStr = new Date(recording.startTime).toISOString().replace(/[:.]/g, '-').slice(0, 19)
                          downloadJson(`recording_${dateStr}.json`, { ...recording, exportedAt: Date.now() })
                        }} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"><Download className="h-4 w-4" />{t('apps.deepSearch.playback.exportJson')}</button>
                        <button onClick={handleDeleteSelectedRecording} className="inline-flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-medium text-rose-600 transition-colors hover:bg-rose-100"><Trash2 className="h-4 w-4" />{t('apps.deepSearch.playback.buttons.delete')}</button>
                      {isPlaying ? (
                        <div className="flex items-center gap-2">
                            <button onClick={handlePauseResume} className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-slate-800">
                            {playbackStatus === 'playing' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                            <span>{playbackStatus === 'playing' ? t('apps.deepSearch.playback.pause') : t('apps.deepSearch.playback.resume')}</span>
                          </button>
                            <button onClick={handleStop} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50">
                            <Square className="h-4 w-4" />
                            <span>{t('apps.deepSearch.playback.stop')}</span>
                          </button>
                        </div>
                      ) : (
                          <button onClick={handlePlayback} className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:from-blue-700 hover:to-purple-700">
                          <Play className="h-4 w-4" />
                          <span>{t('apps.deepSearch.playback.playRecording')}</span>
                        </button>
                      )}
                      </div>
                    </div>

                    <div
                      className={`mt-3.5 rounded-2xl border p-3 transition-colors ${
                        isPlaying
                          ? 'border-blue-100 bg-gradient-to-br from-blue-50/90 via-white to-purple-50/80'
                          : 'border-slate-200 bg-slate-50/90'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <div className="flex items-center gap-2 text-slate-600">
                          <History className={`h-4 w-4 ${isPlaying ? 'text-blue-500' : 'text-slate-400'}`} />
                          <span>{isPlaying ? playbackStatusLabel : t('apps.deepSearch.playback.playRecording')}</span>
                        </div>
                        <span className={`font-medium ${isPlaying ? 'text-blue-700' : 'text-slate-700'}`}>
                          {isPlaying ? `${playbackProgress}%` : 'Ready'}
                        </span>
                      </div>
                      {isPlaying ? (
                        <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-blue-100">
                          <div className="h-full rounded-full bg-gradient-to-r from-blue-600 to-purple-600 transition-all duration-300" style={{ width: `${playbackProgress}%` }} />
                        </div>
                      ) : (
                        <p className="mt-2 text-[12px] text-slate-500">
                          {t('apps.deepSearch.playback.playRecording')}
                        </p>
                      )}
                      <div className="mt-3 flex flex-wrap gap-2 text-sm">
                        <div className="w-[112px] rounded-xl bg-white px-3 py-2.5 ring-1 ring-slate-200/80">
                          <div className="text-[11px] font-medium text-slate-400">{t('apps.deepSearch.playback.mainFlow')}</div>
                          <div className="mt-1 text-lg font-semibold text-slate-950">{selectedRecording.eventCount}</div>
                        </div>
                        {selectedInteractionCount > 0 && (
                          <div className="w-[112px] rounded-xl bg-white px-3 py-2.5 ring-1 ring-slate-200/80">
                            <div className="text-[11px] font-medium text-slate-400">{t('apps.deepSearch.playback.interaction')}</div>
                            <div className="mt-1 text-lg font-semibold text-slate-950">{selectedInteractionCount}</div>
                          </div>
                        )}
                        {selectedInteractionCount === 0 && (
                          <div className="w-[112px] rounded-xl bg-white px-3 py-2.5 ring-1 ring-slate-200/80">
                            <div className="text-[11px] font-medium text-slate-400">{t('apps.deepSearch.playback.interaction')}</div>
                            <div className="mt-1 text-lg font-semibold text-slate-950">0</div>
                          </div>
                        )}
                        <div className="w-[112px] rounded-xl bg-white px-3 py-2.5 ring-1 ring-slate-200/80">
                          <div className="text-[11px] font-medium text-slate-400">{t('apps.deepSearch.playback.duration')}</div>
                          <div className="mt-1 text-lg font-semibold text-slate-950">{formatDuration(selectedRecording.duration)}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {selectedRewriteCount > 0 && (
                  <div className="rounded-[20px] border border-slate-200 bg-white/90 p-3.5 shadow-[0_14px_34px_rgba(15,23,42,0.06)]">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-slate-900">
                          {t('apps.deepSearch.playback.mockMode')}
                        </div>
                        <p className="mt-1 text-sm text-slate-500">
                          {selectedRewriteCount > 0 ? t('apps.deepSearch.playback.mockModeHint') : t('apps.deepSearch.playback.selectRecordingHintDesc')}
                        </p>
                      </div>
                      <button
                        onClick={() => setMockModeEnabled((value) => !value)}
                        disabled={selectedRewriteCount === 0}
                        className={`rounded-2xl border px-3 py-2 transition-colors ${selectedRewriteCount === 0 ? 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-300' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
                      >
                        {mockModeEnabled ? <ToggleRight className="h-7 w-7 text-purple-600" /> : <ToggleLeft className="h-7 w-7 text-slate-400" />}
                      </button>
                    </div>

                    <div className="mt-4 grid grid-cols-3 gap-3">
                      <div className="rounded-2xl bg-slate-50 px-3 py-3 ring-1 ring-slate-200/80">
                        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-slate-400">{t('apps.deepSearch.playback.pending')}</div>
                        <div className="mt-2 text-xl font-semibold text-slate-950">{pendingCount}</div>
                      </div>
                      <div className="rounded-2xl bg-emerald-50 px-3 py-3 ring-1 ring-emerald-100">
                        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-emerald-500">{t('apps.deepSearch.playback.matched')}</div>
                        <div className="mt-2 text-xl font-semibold text-emerald-700">{matchedCount}</div>
                      </div>
                      <div className="rounded-2xl bg-rose-50 px-3 py-3 ring-1 ring-rose-100">
                        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-rose-500">{t('apps.deepSearch.playback.notMatched')}</div>
                        <div className="mt-2 text-xl font-semibold text-rose-700">{notMatchedCount}</div>
                      </div>
                    </div>

                    <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50/90 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-medium text-slate-700">
                          {t('apps.deepSearch.playback.mockMode')}: {mockModeEnabled ? t('apps.deepSearch.playback.on') : t('apps.deepSearch.playback.off')}
                        </div>
                        {mockModeEnabled && selectedRewriteCount > 0 && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2.5 py-1 text-[11px] font-medium text-purple-700">
                            <Sparkles className="h-3 w-3" />
                            {t('apps.deepSearch.playback.on')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  )}
                </div>

                {(
                  <div className="flex-1 overflow-y-auto px-4 py-3.5">
                    <div className="space-y-3">
                      {selectedInteractionCount === 0 && (
                        <div className="rounded-[20px] border border-slate-200 bg-white/90 p-4 shadow-[0_14px_34px_rgba(15,23,42,0.06)]">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <h4 className="text-sm font-semibold text-slate-900">{t('apps.deepSearch.playback.interactionTrack')}</h4>
                              <p className="mt-1 text-sm text-slate-500">{t('apps.deepSearch.playback.hitlOutlineCount', { count: 0 })}</p>
                            </div>
                            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
                              No interaction
                            </span>
                          </div>
                          <div className="mt-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-6 text-sm leading-6 text-slate-500">
                            {t('apps.deepSearch.playback.noInteractionDesc')}
                          </div>
                        </div>
                      )}
                      {selectedInteractionCount > 0 && (
                        <div className="rounded-[20px] border border-slate-200 bg-white/90 p-4 shadow-[0_14px_34px_rgba(15,23,42,0.06)]">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <h4 className="text-sm font-semibold text-slate-900">{t('apps.deepSearch.playback.interactionTrack')}</h4>
                              <p className="mt-1 text-sm text-slate-500">{t('apps.deepSearch.playback.hitlOutlineCount', { count: selectedInteractionCount })}</p>
                            </div>
                            <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                              Continuation
                            </span>
                          </div>
                          <div className="mt-4 space-y-4">
                            {selectedRecording.interactionEvents?.map((interactionEvent, index) => (
                              <div
                                key={`${selectedRecording.id}-interaction-${index}`}
                                className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
                              >
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                  <div className="min-w-0 flex-1">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-full bg-indigo-600 px-2 text-xs font-semibold text-white">
                                        {index + 1}
                                      </span>
                                      <span className="text-sm font-semibold text-slate-900">
                                        {getInteractionKindLabel(t, interactionEvent.kind)}
                                      </span>
                                      <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 ring-1 ring-slate-200/80">
                                        {getInteractionFeedbackLabel(t, interactionEvent.feedback)}
                                      </span>
                                      <span className="text-xs text-slate-400">
                                        {formatTime(interactionEvent.timestamp)}
                                      </span>
                                    </div>
                                    <div className="mt-3 rounded-2xl bg-white px-4 py-3.5 text-sm leading-6 text-slate-600 ring-1 ring-slate-200/80">
                                      {interactionEvent.userMessage}
                                    </div>
                                  </div>
                                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                                    {t('apps.deepSearch.playback.afterMainFlowEvent', { count: interactionEvent.afterEventCount })}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {(selectedRecording.rewriteEvents?.length || 0) > 0 && (
                        <div className="rounded-[20px] border border-slate-200 bg-white/90 p-3.5 shadow-[0_14px_34px_rgba(15,23,42,0.06)]">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <h4 className="text-sm font-semibold text-slate-900">{t('apps.deepSearch.playback.rewriteHistory')}</h4>
                              <p className="mt-1 text-sm text-slate-500">{t('apps.deepSearch.playback.rewritesCount', { count: selectedRecording.rewriteEvents?.length || 0 })}</p>
                            </div>
                            {mockModeEnabled && (
                              <div className="flex flex-wrap items-center gap-2 text-xs font-medium">
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{t('apps.deepSearch.playback.pending')}: {pendingCount}</span>
                                <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-700">{t('apps.deepSearch.playback.matched')}: {matchedCount}</span>
                                <span className="rounded-full bg-rose-100 px-3 py-1 text-rose-700">{t('apps.deepSearch.playback.notMatched')}: {notMatchedCount}</span>
                              </div>
                            )}
                          </div>
                          <div className="mt-5 space-y-3">
                            {selectedRecording.rewriteEvents?.map((rewriteEvent, index) => {
                              const statusEntry = rewriteMockStatuses.find((item) => item.id === `${selectedRecording.id}-rewrite-${index}`)
                              const status = statusEntry?.status ?? 'pending'
                              const diagnostic = statusEntry?.diagnostic
                              return (
                                <div key={`${selectedRecording.id}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50/80 p-3.5">
                                  <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div className="min-w-0 flex-1">
                                      <div className="flex flex-wrap items-center gap-2">
                                        <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-full bg-slate-900 px-2 text-xs font-semibold text-white">{index + 1}</span>
                                        <span className="text-sm font-semibold text-slate-900">{rewriteEvent.request.action}</span>
                                        <span className="text-xs text-slate-400">{formatTime(rewriteEvent.timestamp)}</span>
                                        <span className="text-xs text-slate-400">{t('apps.deepSearch.playback.eventsCount', { count: rewriteEvent.responseEvents.length })}</span>
                                      </div>
                                      <div className="mt-3 rounded-2xl bg-white px-3.5 py-3 text-sm leading-6 text-slate-600 ring-1 ring-slate-200/80">
                                        <span className="font-medium text-slate-900">{t('apps.deepSearch.playback.selectedText')}:</span>{' '}
                                        {rewriteEvent.request.selectedText}
                                      </div>
                                    </div>
                                    {mockModeEnabled && (
                                      <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${status === 'matched' ? 'bg-emerald-100 text-emerald-700' : status === 'pending' ? 'bg-slate-200 text-slate-600' : 'bg-rose-100 text-rose-700'}`}>
                                        {status === 'matched' && <Check className="h-3 w-3" />}
                                        {status === 'matched' ? t('apps.deepSearch.playback.matched') : status === 'pending' ? t('apps.deepSearch.playback.pending') : t('apps.deepSearch.playback.notMatched')}
                                      </span>
                                    )}
                                  </div>
                                  {mockModeEnabled && status === 'not-matched' && diagnostic && (
                                    <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50/80 px-3.5 py-3 text-xs text-rose-700">
                                      <div className="font-medium text-rose-800">{t('apps.deepSearch.playback.mismatchReason')}</div>
                                      {diagnostic.sequenceHint && (
                                        <div className="mt-2 rounded-xl bg-white/80 px-3 py-2 text-[11px] text-rose-800 ring-1 ring-rose-100">
                                          {t('apps.deepSearch.playback.sequenceHintDesc', {
                                            expectedOrder: diagnostic.sequenceHint.expectedOrder,
                                            attemptedOrder: diagnostic.sequenceHint.attemptedOrder ?? '?'
                                          })}
                                        </div>
                                      )}
                                      <div className="mt-1 flex flex-wrap gap-2">
                                        {diagnostic.mismatchReasons.map((reason) => (
                                          <span
                                            key={reason}
                                            className="rounded-full bg-white/80 px-2.5 py-1 text-[11px] font-medium text-rose-700 ring-1 ring-rose-200"
                                          >
                                            {getRewriteMismatchLabel(t, reason)}{t('apps.deepSearch.playback.mismatchInconsistent')}
                                          </span>
                                        ))}
                                      </div>
                                      {diagnostic.closestRequest && (
                                        <div className="mt-3 grid gap-2 text-[11px] text-rose-700/90 sm:grid-cols-2">
                                          <div className="rounded-xl bg-white/80 px-3 py-2 ring-1 ring-rose-100">
                                            <span className="font-medium text-rose-800">{t('apps.deepSearch.playback.closestAction')}</span>: {diagnostic.closestRequest.action}
                                          </div>
                                          <div className="rounded-xl bg-white/80 px-3 py-2 ring-1 ring-rose-100">
                                            <span className="font-medium text-rose-800">{t('apps.deepSearch.playback.closestOffset')}</span>: {diagnostic.closestRequest.startOffset}-{diagnostic.closestRequest.endOffset}
                                          </div>
                                          <div className="rounded-xl bg-white/80 px-3 py-2 ring-1 ring-rose-100 sm:col-span-2">
                                            <span className="font-medium text-rose-800">{t('apps.deepSearch.playback.closestSelectedText')}</span>: {diagnostic.closestRequest.selectedText || t('apps.deepSearch.playback.empty')}
                                          </div>
                                          <div className="rounded-xl bg-white/80 px-3 py-2 ring-1 ring-rose-100 sm:col-span-2">
                                            <span className="font-medium text-rose-800">{t('apps.deepSearch.playback.closestUserInstruction')}</span>: {diagnostic.closestRequest.userInstruction || t('apps.deepSearch.playback.empty')}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

              </>
            ) : (
              <div className="flex flex-1 items-center justify-center px-4 py-4">
                <div className="max-w-lg rounded-[22px] border border-dashed border-slate-300 bg-white/90 px-7 py-10 text-center shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 text-white shadow-lg">
                    <History className="h-7 w-7" />
                  </div>
                  <p className="mt-4 text-lg font-semibold tracking-tight text-slate-950">{t('apps.deepSearch.playback.selectRecordingHint')}</p>
                  <p className="mt-2.5 text-sm leading-6 text-slate-500">{t('apps.deepSearch.playback.selectRecordingHintDesc')}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-slate-200/80 bg-white/90 px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[11px] text-slate-500">{t('apps.deepSearch.playback.tip')}</p>
          <div className="flex items-center gap-2">
            <button onClick={refresh} disabled={isLoading} className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"><RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />{t('apps.deepSearch.playback.buttons.refresh')}</button>
            {recordings.length > 0 && (
              <>
                <button onClick={async () => {
                  const fullRecordings = await Promise.all(recordings.map((recording) => getFullRecording(recording.id)))
                  downloadJson(`recordings_all_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.json`, { exportedAt: Date.now(), count: fullRecordings.filter(Boolean).length, recordings: fullRecordings.filter(Boolean) })
                }} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100"><DownloadCloud className="h-4 w-4" />{t('apps.deepSearch.playback.exportAll')}</button>
                <button onClick={async () => {
                  if (!confirm(t('apps.deepSearch.playback.confirmClearAll'))) return
                  try {
                    if (isPlaying) {
                      handleStop()
                    }
                    await clearAll()
                    setSelectedRecordingId(null)
                    setIsHidden(false)
                  } catch (error) {
                    alert(t('apps.deepSearch.playback.clearFailed') + (error as Error).message)
                  }
                }} className="inline-flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-3.5 py-2 text-sm font-medium text-rose-600 transition-colors hover:bg-rose-100"><Trash2 className="h-4 w-4" />{t('apps.deepSearch.playback.buttons.clear')}</button>
              </>
            )}
          </div>
          </div>
        </div>
        </div>
      </div>
    </div>
  )
}
