/**
 * usePlaybackHistory Hook
 *
 * 管理 SSE 回放历史记录的 React Hook
 */

import { useState, useEffect, useCallback } from 'react'
import i18n from '@/i18n'
import SSERecorder, { type RecordingSession } from '../utils/sseRecorder'

export interface PlaybackHistoryItem {
  id: string
  name: string
  timestamp: number
  eventCount: number
  compressedCount: number
  duration: number
  query: string
}

export function usePlaybackHistory(enabled: boolean = true, limit: number = 10) {
  const [recordings, setRecordings] = useState<PlaybackHistoryItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  // 加载录制列表
  const loadRecordings = useCallback(async () => {
    if (!enabled) return

    setIsLoading(true)
    setError(null)

    try {
      const data = await SSERecorder.listRecordings(limit)

      // 转换为显示格式
      const items: PlaybackHistoryItem[] = data.map(rec => ({
        id: rec.id,
        name: formatRecordingName(rec),
        timestamp: rec.startTime,
        eventCount: rec.eventCount,
        compressedCount: rec.compressedCount,
        duration: rec.duration || 0,
        query: rec.query,
      }))

      setRecordings(items)
    } catch (err) {
      setError(err as Error)
      console.error('[usePlaybackHistory] Failed to load recordings:', err)
    } finally {
      setIsLoading(false)
    }
  }, [enabled, limit])

  // 删除录制
  const deleteRecording = useCallback(async (id: string) => {
    try {
      await SSERecorder.deleteRecording(id)
      // 重新加载列表
      await loadRecordings()
    } catch (err) {
      console.error('[usePlaybackHistory] Failed to delete recording:', err)
      throw err
    }
  }, [loadRecordings])

  // 清空所有录制
  const clearAll = useCallback(async () => {
    try {
      await SSERecorder.clearAll()
      setRecordings([])
    } catch (err) {
      console.error('[usePlaybackHistory] Failed to clear recordings:', err)
      throw err
    }
  }, [])

  // 获取单个录制
  const getRecording = useCallback(async (id: string): Promise<RecordingSession | null> => {
    return SSERecorder.getRecording(id)
  }, [])

  // 初始化时加载
  useEffect(() => {
    loadRecordings()
  }, [loadRecordings])

  // 监听录制更新（通过自定义事件）
  useEffect(() => {
    if (!enabled) return

    const handleRecordingUpdate = () => {
      loadRecordings()
    }

    window.addEventListener('sse-recording-saved', handleRecordingUpdate)
    window.addEventListener('sse-recording-deleted', handleRecordingUpdate)

    return () => {
      window.removeEventListener('sse-recording-saved', handleRecordingUpdate)
      window.removeEventListener('sse-recording-deleted', handleRecordingUpdate)
    }
  }, [enabled, loadRecordings])

  return {
    recordings,
    isLoading,
    error,
    loadRecordings,
    deleteRecording,
    clearAll,
    getRecording,
  }
}

// ===== 辅助函数 =====

function formatRecordingName(recording: RecordingSession): string {
  const date = new Date(recording.startTime)
  // 根据当前语言动态选择locale
  const locale = i18n.language.startsWith('zh') ? 'zh-CN' : 'en-US'
  const timeStr = date.toLocaleTimeString(locale, {
    hour: '2-digit',
    minute: '2-digit',
  })

  // 提取查询的关键词（前20个字符）
  const queryPreview = recording.query.length > 20
    ? recording.query.substring(0, 20) + '...'
    : recording.query

  return `${timeStr} - ${queryPreview}`
}