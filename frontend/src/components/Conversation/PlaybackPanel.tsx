/**
 * PlaybackPanel
 *
 * SSE 回放控制面板组件
 */

import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Play, Trash2, RefreshCw, X, Clock, Activity, Download, DownloadCloud, Zap, FileText, Eye } from 'lucide-react'
import SSEPlayer, { type PlaybackStatus } from '../../utils/ssePlayer'
import { usePlaybackHistory } from '../../hooks/usePlaybackHistory'
import { useConversationStore } from '../../stores/useConversationStore'
import { MessageType } from '../../stores/useConversationStore'
import type { RecordingSession } from '../../utils/sseRecorder'

interface PlaybackPanelProps {
  onClose: () => void
  onPlaybackStart: (conversationId: string) => Promise<string>
}

type PlaybackSpeed = 1 | 2 | 5 | 10

const SPEED_OPTIONS: { value: PlaybackSpeed; label: string }[] = [
  { value: 1, label: '1x' },
  { value: 2, label: '2x' },
  { value: 5, label: '5x' },
  { value: 10, label: '10x' },
]

// localStorage key for compression setting
const COMPRESSION_STORAGE_KEY = 'sse_recording_compression_enabled'

// 调试报告类型
interface DebugReport {
  id: string
  name: string
  timestamp: number
  content: string
}

export default function PlaybackPanel({ onClose, onPlaybackStart }: PlaybackPanelProps) {
  const { t, i18n } = useTranslation()

  // 面板切换状态
  const [activeTab, setActiveTab] = useState<'playback' | 'debug'>('playback')

  // 压缩开关状态
  const [enableCompression, setEnableCompression] = useState(true)

  // 初始化时从 localStorage 读取压缩配置
  useEffect(() => {
    try {
      const saved = localStorage.getItem(COMPRESSION_STORAGE_KEY)
      if (saved !== null) {
        setEnableCompression(saved === 'true')
      }
    } catch (error) {
      console.warn('[PlaybackPanel] Failed to read compression setting:', error)
    }
  }, [])

  // 处理压缩开关切换
  const handleCompressionToggle = (value: boolean) => {
    setEnableCompression(value)
    try {
      localStorage.setItem(COMPRESSION_STORAGE_KEY, String(value))
    } catch (error) {
      console.warn('[PlaybackPanel] Failed to save compression setting:', error)
    }
  }
  const {
    recordings,
    isLoading,
    loadRecordings,
    deleteRecording,
    clearAll,
    getRecording,
  } = usePlaybackHistory(true, 10)

  // 调试报告列表
  const [debugReports, setDebugReports] = useState<DebugReport[]>([])

  const [playingId, setPlayingId] = useState<string | null>(null)
  const [playbackSpeed, setPlaybackSpeed] = useState<PlaybackSpeed>(2)
  const [playbackStatus, setPlaybackStatus] = useState<PlaybackStatus>('idle')
  const [playbackProgress, setPlaybackProgress] = useState(0)

  // 处理回放
  const handlePlayback = async (recordingId: string) => {
    try {
      // 关闭旧的报告面板
      const store = useConversationStore.getState()
      store.setSelectedResultMessageId(null)

      const recording = await getRecording(recordingId)
      if (!recording) {
        console.error('[PlaybackPanel] Recording not found:', recordingId)
        return
      }

      setPlayingId(recordingId)
      setPlaybackStatus('playing')
      setPlaybackProgress(0)

      // 获取或创建回放专用对话
      const playbackConversationId = store.getOrCreatePlaybackConversation()

      // 通知父组件切换到回放对话
      await onPlaybackStart(playbackConversationId)

      // 延迟一下，确保 conversation 已切换
      await new Promise(resolve => setTimeout(resolve, 100))

      // 先添加用户消息，确保 DeepsearchSSEHandler 能找到 outlineTask
      store.addUserMessage(playbackConversationId, recording.query)

      // 添加用户消息后，检查 outlineTask 是否存在
      // 注意：messageItems 是在 store 级别管理的，不是 conversation 的属性
      const currentStateAfter = useConversationStore.getState()
      const messageItemsList = currentStateAfter.getCurrentMessageItems()
      const lastMessageItems = messageItemsList[messageItemsList.length - 1]

      if (lastMessageItems && lastMessageItems.conversationId === playbackConversationId) {
        const outlineTaskId = lastMessageItems.messagesIds.find(msgId => {
          const msg = currentStateAfter.getMessageById(msgId)
          return msg?.type === 'TASK' && msg.sectionIdx === 0
        })
        if (!outlineTaskId) {
          console.warn('[PlaybackPanel] outlineTask NOT FOUND after adding user message')
        }
      }

      // 开始回放
      await SSEPlayer.playback(recording, (sseData) => {
        // 调用父组件提供的 SSE 处理函数
        window.dispatchEvent(new CustomEvent('sse-playback-event', {
          detail: { data: sseData, conversationId: playbackConversationId },
        }))
      }, {
        speed: playbackSpeed,
        restoreTiming: false, // 使用快速回放模式
        onProgress: (progress) => {
          setPlaybackProgress(progress.percentage)
        },
        onError: (error) => {
          console.error('[PlaybackPanel] Playback error:', error)
          setPlaybackStatus('error')
        },
      })

      setPlaybackStatus('completed')
    } catch (error) {
      console.error('[PlaybackPanel] Playback failed:', error)
      setPlaybackStatus('error')
    } finally {
      setPlayingId(null)
      setPlaybackProgress(0)
    }
  }

  // 处理删除
  const handleDelete = async (id: string) => {
    if (confirm(t('apps.deepSearch.playback.confirmDelete'))) {
      try {
        await deleteRecording(id)
      } catch (error) {
        alert(t('apps.deepSearch.playback.deleteFailed') + (error as Error).message)
      }
    }
  }

  // 处理清空
  const handleClearAll = async () => {
    if (confirm(t('apps.deepSearch.playback.confirmClearAll'))) {
      try {
        await clearAll()
      } catch (error) {
        alert(t('apps.deepSearch.playback.clearFailed') + (error as Error).message)
      }
    }
  }

  // 处理导入 markdown 报告
  const handleImportReport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()

      // 提取标题
      const titleMatch = text.match(/^#\s+(.+)$/m)
      const title = titleMatch ? titleMatch[1].trim() : file.name.replace(/\.(md|markdown)$/, '')

      const debugReport: DebugReport = {
        id: `debug-${Date.now()}`,
        name: title,
        timestamp: Date.now(),
        content: text,
      }

      setDebugReports(prev => [debugReport, ...prev])

      // 清空 input 允许重复导入
      event.target.value = ''
    } catch (error) {
      console.error('[PlaybackPanel] Failed to import report:', error)
      alert(t('apps.deepSearch.playback.importFailed') + (error as Error).message)
    }
  }

  // 删除调试报告
  const handleDeleteDebugReport = (id: string) => {
    setDebugReports(prev => prev.filter(r => r.id !== id))
  }

  // 查看调试报告（在对话列表中创建一个 REPORT 消息）
  const handleViewDebugReport = (debugReport: DebugReport) => {
    const store = useConversationStore.getState()

    // 获取当前对话 ID
    const currentConversationId = store.currentConversationId
    if (!currentConversationId) {
      alert(t('apps.deepSearch.playback.selectConversationFirst'))
      return
    }

    // 构造 REPORT 类型的消息内容
    const reportContent = {
      response_content: debugReport.content,
      citation_messages: null,
      infer_messages: [],
    }

    // 添加用户消息
    store.addUserMessage(currentConversationId, debugReport.name)

    // 添加 REPORT 类型系统消息
    store.addSystemMessage(
      currentConversationId,
      MessageType.REPORT,
      reportContent,
      undefined,  // parentId
      t('apps.deepSearch.playback.finalReport'),  // title
      'debug'      // agentType
    )

    // 关闭回放面板
    onClose()
  }

  // 下载单个录制
  const handleDownload = async (recordingId: string) => {
    try {
      const recording = await getRecording(recordingId)
      if (!recording) {
        console.error('[PlaybackPanel] Recording not found:', recordingId)
        return
      }

      // 准备下载数据
      const downloadData = {
        id: recording.id,
        query: recording.query,
        startTime: recording.startTime,
        endTime: recording.endTime,
        duration: recording.duration,
        eventCount: recording.eventCount,
        compressedCount: recording.compressedCount,
        events: recording.events,
        metadata: recording.metadata,
        exportedAt: Date.now(),
      }

      // 转换为 JSON 字符串
      const jsonString = JSON.stringify(downloadData, null, 2)

      // 创建 Blob
      const blob = new Blob([jsonString], { type: 'application/json' })

      // 创建下载链接
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url

      // 生成文件名：sse_recording_YYYYMMDD_HHMMSS.json
      const date = new Date(recording.startTime)
      const dateStr = date.toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `sse_recording_${dateStr}.json`

      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      // 释放 URL
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('[PlaybackPanel] Download failed:', error)
      alert(t('apps.deepSearch.playback.downloadFailed') + (error as Error).message)
    }
  }

  // 下载所有录制（打包为 JSON 数组）
  const handleDownloadAll = async () => {
    try {
      if (recordings.length === 0) {
        alert(t('apps.deepSearch.playback.noRecordingsToDownload'))
        return
      }

      // 获取所有录制的完整数据
      const allRecordings = await Promise.all(
        recordings.map(rec => getRecording(rec.id))
      )

      // 过滤掉 null
      const validRecordings = allRecordings.filter((rec): rec is RecordingSession => rec !== null)

      // 准备下载数据
      const downloadData = {
        exportedAt: Date.now(),
        count: validRecordings.length,
        recordings: validRecordings,
      }

      // 转换为 JSON 字符串
      const jsonString = JSON.stringify(downloadData, null, 2)

      // 创建 Blob
      const blob = new Blob([jsonString], { type: 'application/json' })

      // 创建下载链接
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url

      // 生成文件名：sse_recordings_all_YYYYMMDD_HHMMSS.json
      const date = new Date()
      const dateStr = date.toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `sse_recordings_all_${dateStr}.json`

      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      // 释放 URL
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('[PlaybackPanel] Download all failed:', error)
      alert(t('apps.deepSearch.playback.downloadFailed') + (error as Error).message)
    }
  }

  // 格式化时间
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    // 根据当前语言动态选择locale
    const locale = i18n.language === 'zh-CN' ? 'zh-CN' : 'en-US'
    return date.toLocaleString(locale, {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // 计算压缩比例
  const getCompressionRatio = (original: number, compressed: number) => {
    if (original === 0) return '0%'
    const ratio = ((1 - compressed / original) * 100).toFixed(0)
    return `${ratio}%`
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        {/* 头部 + 标签切换 */}
        <div className="px-6 pt-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">{t('apps.deepSearch.playback.panelTitle')}</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* 标签切换器 */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('playback')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === 'playback'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <span className="flex items-center gap-2">
                <Play className="w-4 h-4" />
                {t('apps.deepSearch.playback.tabPlayback')}
              </span>
            </button>
            <button
              onClick={() => setActiveTab('debug')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === 'debug'
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <span className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                {t('apps.deepSearch.playback.tabDebug')}
              </span>
            </button>
          </div>
        </div>

        {/* 工具栏 */}
        {activeTab === 'playback' ? (
          <div className="flex items-center justify-between px-6 py-3 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center gap-3">
              {/* 速度控制 */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">{t('apps.deepSearch.playback.playbackSpeed')}</span>
                <div className="flex gap-1">
                  {SPEED_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setPlaybackSpeed(option.value)}
                      className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                        playbackSpeed === option.value
                          ? 'bg-blue-600 text-white'
                          : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 压缩开关 */}
              <div className="flex items-center gap-2 px-3 py-1 bg-white border border-gray-300 rounded-lg">
                <Zap className={`w-4 h-4 ${enableCompression ? 'text-yellow-500' : 'text-gray-400'}`} />
                <span className="text-sm font-medium text-gray-700">{t('apps.deepSearch.playback.compressionEnabled')}</span>
                <button
                  onClick={() => handleCompressionToggle(!enableCompression)}
                  className={`relative w-10 h-5 rounded-full transition-colors ${
                    enableCompression ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                      enableCompression ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              {/* 当前状态 */}
              {playbackStatus !== 'idle' && (
                <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 rounded-lg">
                  {playbackStatus === 'playing' && (
                    <>
                      <Activity className="w-4 h-4 text-blue-600 animate-pulse" />
                      <span className="text-sm font-medium text-blue-700">{t('apps.deepSearch.playback.status.playing')} {playbackProgress}%</span>
                    </>
                  )}
                  {playbackStatus === 'completed' && (
                    <>
                      <span className="text-sm font-medium text-green-700">{t('apps.deepSearch.playback.status.completed')}</span>
                    </>
                  )}
                  {playbackStatus === 'error' && (
                    <span className="text-sm font-medium text-red-700">{t('apps.deepSearch.playback.status.failed')}</span>
                  )}
                </div>
              )}
            </div>

            {/* 操作按钮 */}
            <div className="flex items-center gap-2">
              <button
                onClick={loadRecordings}
                disabled={isLoading}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                {t('apps.deepSearch.playback.buttons.refresh')}
              </button>
              {recordings.length > 0 && (
                <button
                  onClick={handleDownloadAll}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                  title={t('apps.deepSearch.playback.buttons.downloadAllTooltip')}
                >
                  <DownloadCloud className="w-4 h-4" />
                  {t('apps.deepSearch.playback.buttons.downloadAll')}
                </button>
              )}
              {recordings.length > 0 && (
                <button
                  onClick={handleClearAll}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  {t('apps.deepSearch.playback.buttons.clear')}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between px-6 py-3 bg-purple-50 border-b border-purple-200">
            <div className="flex items-center gap-2 text-sm text-purple-700">
              <FileText className="w-4 h-4" />
              <span>{t('apps.deepSearch.playback.debugReportsCount', { count: debugReports.length })}</span>
            </div>

            {/* 操作按钮 */}
            <div className="flex items-center gap-2">
              {/* 导入报告按钮 */}
              <label className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-purple-600 hover:bg-purple-100 border border-purple-300 rounded-lg transition-colors cursor-pointer">
                <FileText className="w-4 h-4" />
                {t('apps.deepSearch.playback.buttons.importReport')}
                <input
                  type="file"
                  accept=".md,.markdown"
                  onChange={handleImportReport}
                  className="hidden"
                />
              </label>

              {debugReports.length > 0 && (
                <button
                  onClick={() => {
                    if (confirm(t('apps.deepSearch.playback.confirmClearDebugReports'))) {
                      setDebugReports([])
                    }
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-100 border border-red-300 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  {t('apps.deepSearch.playback.buttons.clear')}
                </button>
              )}
            </div>
          </div>
        )}

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {activeTab === 'playback' ? (
            // SSE 回放标签页内容
            isLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mx-auto mb-2" />
                  <p className="text-sm text-gray-500">{t('apps.deepSearch.playback.loading')}</p>
                </div>
              </div>
            ) : recordings.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <Clock className="w-16 h-16 text-gray-300 mb-4" />
                <p className="text-lg font-medium text-gray-600 mb-1">{t('apps.deepSearch.playback.noRecordings')}</p>
                <p className="text-sm text-gray-500">
                  {t('apps.deepSearch.playback.noRecordingsDesc')}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {recordings.map((recording) => (
                  <div
                    key={recording.id}
                    className={`flex items-center gap-4 p-4 bg-gray-50 rounded-xl border-2 transition-all ${
                      playingId === recording.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-transparent hover:border-gray-300'
                    }`}
                  >
                    {/* 播放按钮 */}
                    <button
                      onClick={() => handlePlayback(recording.id)}
                      disabled={playingId !== null}
                      className="flex-shrink-0 w-12 h-12 flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {playingId === recording.id ? (
                        <Activity className="w-6 h-6 animate-pulse" />
                      ) : (
                        <Play className="w-6 h-6" />
                      )}
                    </button>

                    {/* 信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 mb-1 truncate">
                        {recording.name}
                      </div>
                      <div className="flex items-center gap-3 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {formatTime(recording.timestamp)}
                        </span>
                        <span>•</span>
                        <span>{recording.eventCount} {t('apps.deepSearch.playback.events')}</span>
                        <span>•</span>
                        <span>{recording.duration} {t('apps.deepSearch.playback.seconds')}</span>
                        {recording.compressedCount < recording.eventCount && (
                          <>
                            <span>•</span>
                            <span className="text-green-600">
                              {t('apps.deepSearch.playback.compression')} {getCompressionRatio(recording.eventCount, recording.compressedCount)}
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* 操作按钮组 */}
                    <div className="flex items-center gap-1">
                      {/* 下载按钮 */}
                      <button
                        onClick={() => handleDownload(recording.id)}
                        className="flex-shrink-0 p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title={t('apps.deepSearch.playback.buttons.download')}
                      >
                        <Download className="w-4 h-4" />
                      </button>

                      {/* 删除按钮 */}
                      <button
                        onClick={() => handleDelete(recording.id)}
                        className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title={t('apps.deepSearch.playback.buttons.delete')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            // 报告调试标签页内容
            debugReports.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <FileText className="w-16 h-16 text-purple-200 mb-4" />
                <p className="text-lg font-medium text-gray-600 mb-1">{t('apps.deepSearch.playback.noDebugReports')}</p>
                <p className="text-sm text-gray-500 mb-4">
                  {t('apps.deepSearch.playback.noDebugReportsDesc')}
                </p>
                <label className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 rounded-lg cursor-pointer transition-colors">
                  <FileText className="w-4 h-4" />
                  {t('apps.deepSearch.playback.buttons.selectMdFile')}
                  <input
                    type="file"
                    accept=".md,.markdown"
                    onChange={handleImportReport}
                    className="hidden"
                  />
                </label>
              </div>
            ) : (
              <div className="space-y-3">
                {debugReports.map((debugReport) => (
                  <div
                    key={debugReport.id}
                    className="flex items-center gap-4 p-4 bg-purple-50 border-2 border-purple-200 rounded-xl"
                  >
                    {/* 查看按钮 */}
                    <button
                      onClick={() => handleViewDebugReport(debugReport)}
                      className="flex-shrink-0 w-12 h-12 flex items-center justify-center bg-purple-600 hover:bg-purple-700 text-white rounded-full transition-colors"
                      title={t('apps.deepSearch.playback.buttons.viewReport')}
                    >
                      <Eye className="w-6 h-6" />
                    </button>

                    {/* 信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900 mb-1 truncate">
                        {debugReport.name}
                      </div>
                      <div className="flex items-center gap-3 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {formatTime(debugReport.timestamp)}
                        </span>
                        <span>•</span>
                        <span className="text-purple-600">{t('apps.deepSearch.playback.debugReport')}</span>
                      </div>
                    </div>

                    {/* 删除按钮 */}
                    <button
                      onClick={() => handleDeleteDebugReport(debugReport.id)}
                      className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title={t('apps.deepSearch.playback.buttons.delete')}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )
          )}
        </div>

        {/* 底部信息 */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            {t('apps.deepSearch.playback.tip')}
          </p>
        </div>
      </div>
    </div>
  )
}
