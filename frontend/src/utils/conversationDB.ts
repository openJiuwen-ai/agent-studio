/**
 * ConversationDB - 对话数据的 IndexDB 持久化管理
 *
 * 功能：
 * 1. 保存对话数据到 IndexDB
 * 2. 从 IndexDB 初始化对话数据
 * 3. 自动管理存储大小和数量限制（500MB 或 25个对话）
 */

import type {
  Conversation,
  MessageItems,
  Message,
  ConversationData
} from '../stores/useConversationStore'

// ===== 事件发射器 =====
// 用于在需要用户确认时通知 UI 层
export type ConversationEventHandler = (event: ConversationEvent) => void | Promise<void>

export interface ConversationEvent {
  type: 'before-delete-conversation' | 'conversation-deleted' | 'storage-limit-warning' | 'count-limit-warning'
  conversationId?: string
  conversationTitle?: string
  reason?: string
  details?: string
  // 存储警告相关
  currentSize?: number
  maxSize?: number
  currentCount?: number
  maxCount?: number
  // 最旧的对话信息（用于警告）
  oldestConversation?: {
    id: string
    title: string
    createdAt: number
    estimatedSize: number
  }
}

class ConversationEventEmitter {
  private listeners: Map<string, ConversationEventHandler[]> = new Map()

  on(event: string, handler: ConversationEventHandler) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(handler)
  }

  off(event: string, handler: ConversationEventHandler) {
    const handlers = this.listeners.get(event)
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  async emit(event: string, data: any) {
    const handlers = this.listeners.get(event)
    if (handlers) {
      for (const handler of handlers) {
        await handler(data)
      }
    }
  }
}

export const conversationEventEmitter = new ConversationEventEmitter()

// ===== 类型定义 =====

export interface ConversationDocument {
  id: string                    // conversationId
  title: string
  createdAt: number
  updatedAt: number
  config: Conversation['config']
  messageItems: MessageItems[]
  messages: Record<string, Message>
  estimatedSize: number
}

export interface StoreMeta {
  id: string  // 改为 id，与 keyPath 匹配
  totalEstimatedSize: number  // 单位：字节
  conversationCount: number
  lastUpdated: number
  // 人类可读的格式，方便查看
  totalSizeReadable: string  // 例如： "12.34 MB"
}

// ===== 常量 =====

const DB_NAME = 'AgentStudioDB' //JiuwenConversationDB
const DB_VERSION = 1
const STORE_NAME = 'conversations'
const MAX_SIZE_BYTES = 500 * 1024 * 1024  // 500MB
const MAX_COUNT = 25

// ===== IndexDB 管理类 =====

class ConversationDB {
  private db: IDBDatabase | null = null
  private static readonly WARNING_SIZE_THRESHOLD = 1 * 1024 * 1024 // 1MB 警告阈值

  /**
   * 删除前确认回调（已废弃，请使用事件系统）
   * @deprecated 请使用 conversationEventEmitter 监听 'before-delete-conversation' 事件
   */
  public beforeDeleteCallback?: (conversationId: string, conversationTitle: string, reason: string, details: string) => boolean | Promise<boolean>

  /**
   * 删除 Promise resolve/reject 函数（用于等待用户确认）
   */
  private deleteResolveReject?: {
    resolve: (value: boolean) => void
    reject: (reason?: any) => void
  }

  /**
   * 设置删除确认结果（由对话框调用）
   */
  public setDeleteConfirmResult(confirmed: boolean) {
    if (this.deleteResolveReject) {
      const { resolve } = this.deleteResolveReject
      this.deleteResolveReject = undefined
      resolve(confirmed)
    }
  }

  /**
   * 获取最大配置
   */
  getMaxConfig() {
    return {
      maxSize: MAX_SIZE_BYTES,
      maxCount: MAX_COUNT,
      warningThreshold: ConversationDB.WARNING_SIZE_THRESHOLD,
    }
  }

  /**
   * 初始化数据库
   */
  async init(): Promise<void> {
    if (this.db) return

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => {
        console.error('[ConversationDB] Failed to open database:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        this.db = request.result
        console.log('[ConversationDB] Database opened successfully')
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        // 创建 conversations store
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })

          // 创建索引：按 updatedAt 排序，用于查找最老的对话
          store.createIndex('updatedAt', 'updatedAt', { unique: false })

          console.log('[ConversationDB] Object store created')
        }
      }
    })
  }

  /**
   * 检查是否需要警告（新建对话前调用）
   * 返回需要警告的类型，如果不需要警告则返回 null
   */
  async checkLimitWarning(newConversationEstimatedSize?: number): Promise<{
    type: 'count-warning' | 'storage-warning' | null
    currentCount?: number
    maxCount?: number
    currentSize?: number
    maxSize?: number
    warningThreshold?: number
    oldestConversation?: {
      id: string
      title: string
      createdAt: number
    }
  } | null> {
    if (!this.db) await this.init()

    const meta = await this.getMeta()
    if (!meta) {
      return null
    }

    const maxSize = MAX_SIZE_BYTES
    const maxCount = MAX_COUNT
    const warningThreshold = ConversationDB.WARNING_SIZE_THRESHOLD

    // 检查数量是否达到上限
    if (meta.conversationCount >= maxCount) {
      const oldest = await this.getOldestConversation()
      if (oldest) {
        return {
          type: 'count-warning',
          currentCount: meta.conversationCount,
          maxCount: maxCount,
          oldestConversation: {
            id: oldest.id,
            title: oldest.title,
            createdAt: oldest.createdAt,
          },
        }
      }
    }

    // 检查存储空间是否接近上限（如果有传入新对话大小）
    if (newConversationEstimatedSize !== undefined) {
      const newSize = meta.totalEstimatedSize + newConversationEstimatedSize
      if (newSize >= maxSize - warningThreshold) {
        return {
          type: 'storage-warning',
          currentSize: meta.totalEstimatedSize,
          maxSize: maxSize,
          warningThreshold: warningThreshold,
        }
      }
    } else if (meta.totalEstimatedSize >= maxSize - warningThreshold) {
      // 即使没有新对话大小，也检查当前是否接近上限
      return {
        type: 'storage-warning',
        currentSize: meta.totalEstimatedSize,
        maxSize: maxSize,
        warningThreshold: warningThreshold,
      }
    }

    return null
  }

  /**
   * 估算对话数据的大小（字节）
   */
  private estimateSize(data: ConversationData): number {
    try {
      const json = JSON.stringify(data)
      return new Blob([json]).size
    } catch (error) {
      console.error('[ConversationDB] Failed to estimate size:', error)
      return 0
    }
  }

  /**
   * 格式化字节大小为人类可读的格式
   * @param bytes 字节数
   * @returns 例如："12.34 MB"
   */
  private formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'

    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  /**
   * 获取 store meta
   */
  private async getMeta(): Promise<StoreMeta | null> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readonly')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.get('__store_meta__')

      request.onsuccess = () => {
        const meta = request.result
        if (meta) {
          console.log('[ConversationDB] Found meta:', {
            totalSize: (meta.totalEstimatedSize / 1024 / 1024).toFixed(2) + ' MB',
            count: meta.conversationCount
          })
        } else {
          console.log('[ConversationDB] No meta found, will create new one')
        }
        resolve(meta || null)
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to get meta:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 更新 store meta
   */
  private async updateMeta(meta: StoreMeta): Promise<void> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readwrite')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.put(meta)

      request.onsuccess = () => {
        console.log('[ConversationDB] Meta updated successfully:', {
          totalSize: (meta.totalEstimatedSize / 1024 / 1024).toFixed(2) + ' MB',
          count: meta.conversationCount,
          lastUpdated: new Date(meta.lastUpdated).toLocaleString()
        })
        resolve()
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to update meta:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 获取最老的对话（按 updatedAt）
   */
  private async getOldestConversation(): Promise<ConversationDocument | null> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readonly')
      const store = transaction.objectStore(STORE_NAME)
      const index = store.index('updatedAt')

      // 获取第一条记录（最老的）
      const request = index.openCursor(null, 'next')

      request.onsuccess = () => {
        const cursor = request.result
        if (cursor) {
          const doc = cursor.value
          // 跳过 meta 记录
          if (doc.id === '__store_meta__') {
            cursor.continue()
          } else {
            resolve(doc)
          }
        } else {
          resolve(null)
        }
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to get oldest conversation:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 删除指定对话
   */
  private async deleteConversationDoc(id: string): Promise<void> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readwrite')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.delete(id)

      request.onsuccess = () => {
        console.log('[ConversationDB] Deleted conversation:', id)
        resolve()
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to delete conversation:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 保存或更新对话
   */
  private async putConversation(doc: ConversationDocument): Promise<void> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readwrite')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.put(doc)

      request.onsuccess = () => {
        console.log('[ConversationDB] Saved conversation:', doc.id, 'size:', (doc.estimatedSize / 1024).toFixed(2), 'KB')
        resolve()
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to save conversation:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 保存对话数据（带存储管理）
   * - 保存当前对话
   * - 检查存储限制
   * - 删除最老的对话直到满足限制
   */
  async saveConversation(data: ConversationData): Promise<void> {
    try {
      // 1. 初始化数据库
      if (!this.db) await this.init()

      // 2. 估算大小
      const estimatedSize = this.estimateSize(data)

      // 3. 读取 meta
      const metaResult = await this.getMeta()
      let meta: StoreMeta
      if (!metaResult) {
        meta = {
          id: '__store_meta__',
          totalEstimatedSize: 0,
          conversationCount: 0,
          lastUpdated: Date.now(),
          totalSizeReadable: '0 MB'
        }
      } else {
        meta = metaResult
      }

      // 4. 检查是否已存在该对话
      const existingDoc = await this.getConversation(data.conversation.id)
      const isNewConversation = !existingDoc

      // 5. 检查是否需要触发存储警告（仅在新对话时）
      if (isNewConversation) {
        const warningThreshold = ConversationDB.WARNING_SIZE_THRESHOLD
        const newSize = meta.totalEstimatedSize + estimatedSize

        // 如果当前大小 + 新对话大小 >= 最大大小 - 警告阈值，触发警告
        if (newSize >= MAX_SIZE_BYTES - warningThreshold) {
          const oldest = await this.getOldestConversation()
          if (oldest) {
            await conversationEventEmitter.emit('storage-limit-warning', {
              currentSize: meta.totalEstimatedSize,
              maxSize: MAX_SIZE_BYTES,
              warningThreshold: warningThreshold,
              oldestConversation: {
                id: oldest.id,
                title: oldest.title,
                createdAt: oldest.createdAt,
                estimatedSize: oldest.estimatedSize,
              },
            })
          }
        }
      }

      // 6. 如果是新对话，检查是否需要删除最老的
      if (isNewConversation) {
        // 循环删除，直到满足条件
        while (true) {
          // 每次循环都重新计算条件
          const sizeExceeds = meta.totalEstimatedSize + estimatedSize > MAX_SIZE_BYTES
          const countExceeds = meta.conversationCount >= MAX_COUNT
          const hasAtLeastOne = meta.conversationCount >= 1

          // 如果条件都满足了，退出循环
          if (!((sizeExceeds && hasAtLeastOne) || countExceeds)) {
            break
          }

          // 需要删除最老的对话
          const oldest = await this.getOldestConversation()
          if (!oldest) break

          // 构建删除原因和详情
          let reason = ''
          let details = ''

          if (sizeExceeds) {
            reason = '存储空间不足'
            const newSizeMB = ((meta.totalEstimatedSize + estimatedSize) / (1024 * 1024)).toFixed(2)
            const limitMB = (MAX_SIZE_BYTES / (1024 * 1024)).toFixed(0)
            details = `当前总大小将达到 ${newSizeMB}MB，超过限制 ${limitMB}MB。删除最旧的对话可释放 ${(oldest.estimatedSize / 1024 / 1024).toFixed(2)}MB 空间。`
          } else if (countExceeds) {
            reason = '对话数量过多'
            details = `当前对话数量为 ${meta.conversationCount}，已达上限 ${MAX_COUNT} 个。删除最旧的对话以保存新对话。`
          }

          // 触发删除前确认事件（使用事件系统）
          let shouldDelete = true

          // 兼容旧的回调系统
          if (this.beforeDeleteCallback) {
            shouldDelete = await this.beforeDeleteCallback(oldest.id, oldest.title, reason, details)
          } else {
            // 使用新的事件系统
            await new Promise<boolean>((resolve) => {
              this.deleteResolveReject = { resolve, reject: () => resolve(false) }

              // 触发事件，UI 层会显示对话框
              conversationEventEmitter.emit('before-delete-conversation', {
                conversationId: oldest.id,
                conversationTitle: oldest.title,
                reason: reason,
                details: details,
                oldestConversation: {
                  id: oldest.id,
                  title: oldest.title,
                  createdAt: oldest.createdAt,
                  estimatedSize: oldest.estimatedSize,
                },
              })
            })
          }

          if (shouldDelete) {
            console.log('[ConversationDB] Storage limit exceeded, deleting oldest conversation:', oldest.id)
            await this.deleteConversationDoc(oldest.id)

            // 更新 meta
            meta.totalEstimatedSize -= oldest.estimatedSize
            meta.conversationCount--

            // 触发事件，通知内存层删除此对话
            await conversationEventEmitter.emit('conversation-deleted', {
              conversationId: oldest.id
            })
          } else {
            // 用户取消删除
            console.log('[ConversationDB] Delete cancelled by user, cannot save new conversation due to storage limit')
            throw new Error('保存失败：由于存储限制，无法保存新对话。请删除一些历史对话后重试。')
          }
        }

        // 更新 meta（添加新对话）
        meta.totalEstimatedSize += estimatedSize
        meta.conversationCount++
      } else {
        // 更新现有对话：调整总大小
        meta.totalEstimatedSize = meta.totalEstimatedSize - existingDoc.estimatedSize + estimatedSize
      }

      meta.lastUpdated = Date.now()

      // 更新人类可读的大小格式
      meta.totalSizeReadable = this.formatBytes(meta.totalEstimatedSize)

      // 7. 保存当前对话
      const doc: ConversationDocument = {
        id: data.conversation.id,
        title: data.conversation.title,
        createdAt: data.conversation.createdAt,
        updatedAt: data.conversation.updatedAt,
        config: data.conversation.config,
        messageItems: data.messageItems,
        messages: data.messages,
        estimatedSize
      }

      await this.putConversation(doc)

      // 8. 更新 meta
      await this.updateMeta(meta)

      console.log('[ConversationDB] Conversation saved successfully:', {
        id: data.conversation.id,
        size: (estimatedSize / 1024).toFixed(2) + ' KB',
        totalSize: (meta.totalEstimatedSize / 1024 / 1024).toFixed(2) + ' MB',
        count: meta.conversationCount
      })
    } catch (error) {
      console.error('[ConversationDB] Failed to save conversation:', error)
      throw error
    }
  }

  /**
   * 获取指定对话
   */
  async getConversation(id: string): Promise<ConversationDocument | null> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readonly')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.get(id)

      request.onsuccess = () => {
        resolve(request.result || null)
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to get conversation:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 获取所有对话（按 updatedAt 倒序）- 完整数据
   */
  async getAllConversations(): Promise<ConversationDocument[]> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readonly')
      const store = transaction.objectStore(STORE_NAME)
      const index = store.index('updatedAt')

      const request = index.openCursor(null, 'prev')  // 倒序
      const results: ConversationDocument[] = []

      request.onsuccess = () => {
        const cursor = request.result
        if (cursor) {
          const doc = cursor.value
          // 跳过 meta 记录
          if (doc.id !== '__store_meta__') {
            results.push(doc)
          }
          cursor.continue()
        } else {
          resolve(results)
        }
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to get all conversations:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 获取所有对话的基本信息（按 updatedAt 倒序）- 不包含 messageItems 和 messages
   * 用于初始化时加载对话列表，节省内存
   */
  async getAllConversationsBasicInfo(): Promise<Omit<ConversationDocument, 'messageItems' | 'messages'>[]> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readonly')
      const store = transaction.objectStore(STORE_NAME)
      const index = store.index('updatedAt')

      const request = index.openCursor(null, 'prev')  // 倒序
      const results: Array<{
        id: string
        title: string
        createdAt: number
        updatedAt: number
        config: Conversation['config']
        estimatedSize: number
      }> = []

      request.onsuccess = () => {
        const cursor = request.result
        if (cursor) {
          const doc = cursor.value
          // 跳过 meta 记录
          if (doc.id !== '__store_meta__') {
            // 只提取基本信息，不包含 messageItems 和 messages
            const { id, title, createdAt, updatedAt, config, estimatedSize } = doc
            results.push({ id, title, createdAt, updatedAt, config, estimatedSize })
          }
          cursor.continue()
        } else {
          resolve(results)
        }
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to get conversations basic info:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 初始化对话数据到内存
   * 只在内存中没有数据时才加载
   */
  async initializeConversations(
    conversationsList: string[]
  ): Promise<ConversationDocument[]> {
    // 如果内存中已有数据，不加载
    if (conversationsList.length > 0) {
      console.log('[ConversationDB] Memory has data, skipping initialization')
      return []
    }

    console.log('[ConversationDB] Loading conversations from IndexedDB...')

    try {
      const docs = await this.getAllConversations()
      console.log(`[ConversationDB] Loaded ${docs.length} conversations from IndexedDB`)

      // 重新计算 meta，防止累计误差
      console.log('[ConversationDB] Recalculating meta to prevent accumulation errors...')
      let totalEstimatedSize = 0
      docs.forEach(doc => {
        // 重新估算每个对话的实际大小
        const actualSize = doc.estimatedSize
        totalEstimatedSize += actualSize
      })

      // 创建新的 meta
      const recalculatedMeta: StoreMeta = {
        id: '__store_meta__',
        totalEstimatedSize,
        conversationCount: docs.length,
        lastUpdated: Date.now(),
        totalSizeReadable: this.formatBytes(totalEstimatedSize)
      }

      // 更新 meta 到 IndexDB
      await this.updateMeta(recalculatedMeta)

      console.log('[ConversationDB] Meta recalculated and updated:', {
        totalSize: recalculatedMeta.totalSizeReadable,
        count: recalculatedMeta.conversationCount,
        totalBytes: totalEstimatedSize
      })

      return docs
    } catch (error) {
      console.error('[ConversationDB] Failed to initialize conversations:', error)
      return []
    }
  }

  /**
   * 清空所有对话数据
   */
  async clearAll(): Promise<void> {
    if (!this.db) await this.init()

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readwrite')
      const store = transaction.objectStore(STORE_NAME)
      const request = store.clear()

      request.onsuccess = () => {
        console.log('[ConversationDB] All conversations cleared')
        resolve()
      }

      request.onerror = () => {
        console.error('[ConversationDB] Failed to clear conversations:', request.error)
        reject(request.error)
      }
    })
  }

  /**
   * 删除指定对话（公共方法）
   * @param id conversation ID
   */
  async deleteConversation(id: string): Promise<void> {
    try {
      // 1. 删除对话文档
      await this.deleteConversationDoc(id)

      // 2. 更新 meta
      const meta = await this.getMeta()
      if (meta) {
        // 重新加载所有对话来更新 meta（防止累计误差）
        const docs = await this.getAllConversations()
        let totalEstimatedSize = 0
        docs.forEach(doc => {
          totalEstimatedSize += doc.estimatedSize
        })

        const updatedMeta: StoreMeta = {
          id: '__store_meta__',
          totalEstimatedSize,
          conversationCount: docs.length,
          lastUpdated: Date.now(),
          totalSizeReadable: this.formatBytes(totalEstimatedSize)
        }

        await this.updateMeta(updatedMeta)
      }

      console.log('[ConversationDB] Conversation deleted successfully:', id)
    } catch (error) {
      console.error('[ConversationDB] Failed to delete conversation:', error)
      throw error
    }
  }
}

// 导出单例
export const conversationDB = new ConversationDB()
