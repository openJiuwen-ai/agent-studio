/**
 * SSE Recorder
 *
 * 录制 SSE 事件流，支持事件压缩和 IndexedDB 持久化存储
 */

// ===== 类型定义 =====

export interface SSEData {
  event: 'start' | 'message' | 'done' | 'summary_response' | 'waiting_user_input';
  agent: string;
  content?: any;
  section_idx?: string | number;
  plan_idx?: string | number;
  step_idx?: string | number;
  message_id?: string;
}

export interface RecordedEvent {
  // 原始 SSE 数据
  data: SSEData

  // 时间戳（毫秒）
  timestamp: number

  // 压缩信息（如果有）
  compressed?: {
    count: number           // 连续相同事件的次数
    firstTimestamp: number  // 第一个事件的时间戳
  }
}

export interface RecordingSession {
  id: string
  query: string
  startTime: number
  endTime?: number
  duration?: number
  eventCount: number
  compressedCount: number

  // 原始事件列表（已压缩）
  events: RecordedEvent[]

  // 元数据
  metadata: {
    agentType: string
    modelConfigId?: number
    conversationId: string
    spaceId?: string
  }
}

// ===== IndexedDB 配置 =====

const DB_NAME = 'sse-recorder-db'
const DB_VERSION = 1
const STORE_NAME = 'recordings'

class IndexedDBStorage {
  private db: IDBDatabase | null = null

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        // 创建 recordings 对象存储
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })

          // 创建索引
          store.createIndex('startTime', 'startTime', { unique: false })
          store.createIndex('query', 'query', { unique: false })
        }
      }
    })
  }

  async saveRecording(recording: RecordingSession): Promise<void> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readwrite')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.put(recording)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  async getRecording(id: string): Promise<RecordingSession | null> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readonly')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.get(id)

      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  }

  async listRecordings(limit?: number): Promise<RecordingSession[]> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readonly')
      const store = transaction.objectStore(STORE_NAME)
      const index = store.index('startTime')
      const request = index.openCursor(null, 'prev') // 按时间倒序

      const results: RecordingSession[] = []
      let count = 0

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result
        if (cursor && (!limit || count < limit)) {
          results.push(cursor.value)
          count++
          cursor.continue()
        } else {
          resolve(results)
        }
      }

      request.onerror = () => reject(request.error)
    })
  }

  async deleteRecording(id: string): Promise<void> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readwrite')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.delete(id)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  async clearAll(): Promise<void> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readwrite')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.clear()

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }
}

// ===== SSE Recorder =====

interface RecordingOptions {
  enableCompression?: boolean  // 是否启用压缩，默认 true
}

class SSERecorderClass {
  private storage: IndexedDBStorage
  private currentRecording: RecordingSession | null = null
  private lastEvent: SSEData | null = null
  private compressCount = 0
  private enableCompression = true  // 默认启用压缩

  constructor() {
    this.storage = new IndexedDBStorage()
  }

  /**
   * 开始录制
   */
  async startRecording(
    query: string,
    metadata: RecordingSession['metadata'],
    options?: RecordingOptions
  ): Promise<string> {
    // 生成短 ID
    const id = await this.generateShortId()

    // 保存压缩配置
    this.enableCompression = options?.enableCompression ?? true

    this.currentRecording = {
      id,
      query,
      startTime: Date.now(),
      eventCount: 0,
      compressedCount: 0,
      events: [],
      metadata,
    }

    this.lastEvent = null
    this.compressCount = 0

    return id
  }

  /**
   * 录制单个事件
   */
  async recordEvent(data: SSEData): Promise<void> {
    if (!this.currentRecording) {
      console.warn('[SSERecorder] No active recording')
      return
    }

    const now = Date.now()

    // 检查是否启用压缩且是否可以压缩
    if (this.enableCompression && this.canCompress(this.lastEvent, data)) {
      this.compressCount++

      // 更新最后一个事件的压缩信息
      const lastRecordedEvent = this.currentRecording.events[
        this.currentRecording.events.length - 1
      ]
      if (lastRecordedEvent) {
        lastRecordedEvent.compressed = {
          count: this.compressCount,
          firstTimestamp: lastRecordedEvent.timestamp,
        }
      }

      // 替换最后一个事件的 data（用最新的）
      lastRecordedEvent!.data = data
    } else {
      // 不能压缩或压缩已禁用，添加新事件
      this.currentRecording.events.push({
        data,
        timestamp: now,
      })

      this.compressCount = 0
      this.lastEvent = data
    }

    this.currentRecording.eventCount++
  }

  /**
   * 停止录制并保存
   */
  async stopRecording(): Promise<RecordingSession | null> {
    if (!this.currentRecording) {
      console.warn('[SSERecorder] No active recording to stop')
      return null
    }

    // 计算压缩后的事件数
    const compressedEvents = this.currentRecording.events.filter(
      e => !e.compressed
    ).length + this.currentRecording.events.filter(
      e => e.compressed
    ).length

    this.currentRecording.endTime = Date.now()
    this.currentRecording.duration = Math.round(
      (this.currentRecording.endTime - this.currentRecording.startTime) / 1000
    )
    this.currentRecording.compressedCount = compressedEvents

    // 保存到 IndexedDB
    await this.storage.saveRecording(this.currentRecording)

    // 派发事件：录制已保存
    window.dispatchEvent(new CustomEvent('sse-recording-saved', {
      detail: { recordingId: this.currentRecording.id },
    }))

    const recording = this.currentRecording
    this.currentRecording = null
    this.lastEvent = null
    this.compressCount = 0

    return recording
  }

  /**
   * 获取录制列表
   */
  async listRecordings(limit?: number): Promise<RecordingSession[]> {
    return this.storage.listRecordings(limit)
  }

  /**
   * 获取单个录制
   */
  async getRecording(id: string): Promise<RecordingSession | null> {
    return this.storage.getRecording(id)
  }

  /**
   * 删除录制
   */
  async deleteRecording(id: string): Promise<void> {
    await this.storage.deleteRecording(id)

    // 派发事件：录制已删除
    window.dispatchEvent(new CustomEvent('sse-recording-deleted', {
      detail: { recordingId: id },
    }))
  }

  /**
   * 清空所有录制
   */
  async clearAll(): Promise<void> {
    await this.storage.clearAll()

    // 派发事件：所有录制已清空
    window.dispatchEvent(new CustomEvent('sse-recording-cleared'))
  }

  /**
   * 检查是否正在录制
   */
  isRecording(): boolean {
    return this.currentRecording !== null
  }

  /**
   * 获取当前录制信息
   */
  getCurrentRecording(): RecordingSession | null {
    return this.currentRecording
  }

  // ===== 私有方法 =====

  /**
   * 判断两个事件是否可以压缩
   */
  private canCompress(prev: SSEData | null, curr: SSEData): boolean {
    if (!prev) return false

    // 只有 message 事件可以压缩
    if (curr.event !== 'message') return false

    // 检查关键字段是否相同
    const isSameAgent = prev.agent === curr.agent
    const isSameSection = prev.section_idx === curr.section_idx
    const isSamePlan = prev.plan_idx === curr.plan_idx
    const isSameStep = prev.step_idx === curr.step_idx

    // 对于 message 事件，content 可以不同（流式内容）
    // 但其他字段必须相同
    return isSameAgent && isSameSection && isSamePlan && isSameStep
  }

  /**
   * 生成短 ID
   */
  private async generateShortId(): Promise<string> {
    // 简单的短 ID 生成（时间戳 + 随机数）
    const timestamp = Date.now().toString(36)
    const random = Math.random().toString(36).substring(2, 6)
    return `rec_${timestamp}_${random}`
  }
}

// ===== 导出单例 =====

export const SSERecorder = new SSERecorderClass()
export default SSERecorder