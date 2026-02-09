/**
 * useRecordingHistory Hook
 *
 * 管理 SSE 录制历史的持久化存储（使用 IndexedDB）
 * 提供录制保存、加载、删除等功能
 */

import { useState, useEffect, useCallback } from 'react'

export interface RecordingMetadata {
  query: string
  spaceId: string
  modelConfigId?: number
  searchMode: string
  timestamp: string
  duration: number // 持续时间（秒）
  eventCount: number
}

export interface Recording extends RecordingMetadata {
  id: string
  name: string // 友好的显示名称
  events: any[]
}

const DB_NAME = 'sse_recordings'
const STORE_NAME = 'recordings'
const DB_VERSION = 1

// IndexedDB 初始化
const initDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => {
      console.error('[useRecordingHistory] Failed to open database:', request.error)
      reject(request.error)
    }

    request.onsuccess = () => {
      resolve(request.result)
    }

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result

      // 创建对象存储
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        store.createIndex('timestamp', 'timestamp', { unique: false })
      }
    }
  })
}

// 生成友好的显示名称
const generateFriendlyName = (metadata: RecordingMetadata): string => {
  const date = new Date(metadata.timestamp)
  const timeStr = date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })

  // 提取查询关键词（前 15 个字符）
  const query = metadata.query
    .replace(/\n/g, ' ')
    .slice(0, 15)
    .trim()

  return query ? `${timeStr} - ${query}` : `${timeStr} - 未命名`
}

export interface UseRecordingHistoryReturn {
  /** 所有录制历史 */
  recordings: Recording[]
  /** 是否正在加载 */
  isLoading: boolean
  /** 保存录制 */
  saveRecording: (metadata: RecordingMetadata, events: any[]) => Promise<void>
  /** 加载最近的录制 */
  loadRecentRecordings: (limit?: number) => Promise<void>
  /** 删除录制 */
  deleteRecording: (id: string) => Promise<void>
  /** 清空所有录制 */
  clearAll: () => Promise<void>
  /** 根据 ID 获取录制 */
  getRecording: (id: string) => Promise<Recording | null>
}

/**
 * 录制历史管理 Hook
 */
export function useRecordingHistory(
  autoLoad = true,
  loadLimit = 10
): UseRecordingHistoryReturn {
  const [recordings, setRecordings] = useState<Recording[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // 初始化并加载录制历史
  useEffect(() => {
    if (autoLoad) {
      loadRecentRecordings(loadLimit)
    }

    // 监听录制保存事件
    const handleRecordingSaved = (event: Event) => {
      const customEvent = event as CustomEvent<{ recording: Recording }>
      if (customEvent.detail) {
        loadRecentRecordings(loadLimit)
      }
    }

    window.addEventListener('sse-recording-saved', handleRecordingSaved)

    return () => {
      window.removeEventListener('sse-recording-saved', handleRecordingSaved)
    }
  }, [autoLoad, loadLimit])

  // 保存录制
  const saveRecording = useCallback(
    async (metadata: RecordingMetadata, events: any[]) => {
      try {
        const db = await initDB()
        const id = `recording-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

        const recording: Recording = {
          id,
          name: generateFriendlyName(metadata),
          ...metadata,
          events,
        }

        const tx = db.transaction(STORE_NAME, 'readwrite')
        await new Promise<void>((resolve, reject) => {
          const request = tx.objectStore(STORE_NAME).add(recording)

          request.onsuccess = () => {
            resolve()
          }

          request.onerror = () => {
            console.error('[useRecordingHistory] Failed to save recording:', request.error)
            reject(request.error)
          }
        })

        // 触发自定义事件，让其他组件知道有新录制
        window.dispatchEvent(
          new CustomEvent('sse-recording-saved', {
            detail: { recording },
          })
        )

        // 重新加载列表
        await loadRecentRecordings(loadLimit)

        return recording
      } catch (error) {
        console.error('[useRecordingHistory] Error saving recording:', error)
        throw error
      }
    },
    [loadLimit]
  )

  // 加载最近的录制
  const loadRecentRecordings = useCallback(
    async (limit = 10) => {
      setIsLoading(true)
      try {
        const db = await initDB()
        const tx = db.transaction(STORE_NAME, 'readonly')
        const store = tx.objectStore(STORE_NAME)
        const index = store.index('timestamp')
        const request = index.openCursor(null, 'prev') // 倒序

        const results: Recording[] = []
        let count = 0

        await new Promise<void>((resolve, reject) => {
          request.onsuccess = (event) => {
            const cursor = (event.target as IDBRequest).result
            if (cursor && count < limit) {
              results.push(cursor.value)
              cursor.continue()
              count++
            } else {
              resolve()
            }
          }
          request.onerror = () => {
            console.error('[useRecordingHistory] Failed to load recordings:', request.error)
            reject(request.error)
          }
        })

        setRecordings(results)
      } catch (error) {
        console.error('[useRecordingHistory] Error loading recordings:', error)
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  // 根据 ID 获取录制
  const getRecording = useCallback(async (id: string): Promise<Recording | null> => {
    try {
      const db = await initDB()
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)

      return new Promise((resolve, reject) => {
        const request = store.get(id)

        request.onsuccess = () => {
          resolve(request.result || null)
        }

        request.onerror = () => {
          console.error('[useRecordingHistory] Failed to get recording:', request.error)
          reject(request.error)
        }
      })
    } catch (error) {
      console.error('[useRecordingHistory] Error getting recording:', error)
      return null
    }
  }, [])

  // 删除录制
  const deleteRecording = useCallback(async (id: string) => {
    try {
      const db = await initDB()
      const tx = db.transaction(STORE_NAME, 'readwrite')

      await new Promise<void>((resolve, reject) => {
        const request = tx.objectStore(STORE_NAME).delete(id)

        request.onsuccess = () => {
          resolve()
        }

        request.onerror = () => {
          console.error('[useRecordingHistory] Failed to delete recording:', request.error)
          reject(request.error)
        }
      })

      // 更新状态
      setRecordings((prev) => prev.filter((r) => r.id !== id))
    } catch (error) {
      console.error('[useRecordingHistory] Error deleting recording:', error)
      throw error
    }
  }, [])

  // 清空所有录制
  const clearAll = useCallback(async () => {
    try {
      const db = await initDB()
      const tx = db.transaction(STORE_NAME, 'readwrite')

      await new Promise<void>((resolve, reject) => {
        const request = tx.objectStore(STORE_NAME).clear()

        request.onsuccess = () => {
          resolve()
        }

        request.onerror = () => {
          console.error('[useRecordingHistory] Failed to clear recordings:', request.error)
          reject(request.error)
        }
      })

      setRecordings([])
    } catch (error) {
      console.error('[useRecordingHistory] Error clearing recordings:', error)
      throw error
    }
  }, [])

  return {
    recordings,
    isLoading,
    saveRecording,
    loadRecentRecordings,
    deleteRecording,
    clearAll,
    getRecording,
  }
}
