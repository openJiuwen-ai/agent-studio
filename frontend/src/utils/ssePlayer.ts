/**
 * SSE Player
 *
 * 回放录制的 SSE 事件流，支持变速播放和时间间隔还原
 */

import type { RecordingSession, SSEData } from './sseRecorder'

// ===== 回放配置 =====

export interface PlaybackConfig {
  speed?: 1 | 2 | 5 | 10     // 回放速度（默认 1x）
  restoreTiming?: boolean     // 是否还原原始时间间隔（默认 false，使用快速回放）
  onProgress?: (progress: PlaybackProgress) => void
  onError?: (error: Error) => void
}

export interface PlaybackProgress {
  currentEventIndex: number
  totalEvents: number
  percentage: number
  currentTime: number
}

export type PlaybackStatus = 'idle' | 'playing' | 'paused' | 'completed' | 'error'

// ===== SSE Player =====

class SSEPlayerClass {
  private isPlaying = false
  private isPaused = false
  private abortController: AbortController | null = null

  /**
   * 回放录制的事件流
   */
  async playback(
    recording: RecordingSession,
    messageHandler: (data: SSEData) => void,
    config: PlaybackConfig = {}
  ): Promise<void> {
    const {
      speed = 1,
      restoreTiming = false,
      onProgress,
      onError,
    } = config

    // 初始化状态
    this.isPlaying = true
    this.isPaused = false
    this.abortController = new AbortController()

    const { signal } = this.abortController

    try {
      let lastTimestamp = recording.startTime

      // 遍历所有事件
      for (let i = 0; i < recording.events.length; i++) {
        // 检查是否被中止
        if (signal.aborted) {
          break
        }

        // 检查是否暂停
        while (this.isPaused) {
          await this.sleep(100)
          if (signal.aborted) break
        }

        const recordedEvent = recording.events[i]
        const { data, timestamp, compressed } = recordedEvent

        // 处理压缩的事件
        if (compressed) {
          // 如果需要还原原始事件，展开压缩的事件
          for (let j = 0; j < compressed.count; j++) {
            if (signal.aborted) break

            // 调用消息处理器
            messageHandler(data)

            // 更新进度
            onProgress?.(this.calculateProgress(i, recording.events.length, j, compressed.count))

            // 时间延迟
            if (restoreTiming) {
              const delay = this.calculateDelay(timestamp, lastTimestamp, speed)
              if (delay > 0) {
                await this.sleep(delay)
              }
            } else {
              // 快速回放模式：固定延迟
              await this.sleep(10 / speed)
            }
          }
        } else {
          // 普通事件
          messageHandler(data)

          // 更新进度
          onProgress?.(this.calculateProgress(i, recording.events.length))

          // 时间延迟
          if (restoreTiming) {
            const delay = this.calculateDelay(timestamp, lastTimestamp, speed)
            if (delay > 0) {
              await this.sleep(delay)
            }
          } else {
            // 快速回放模式：固定延迟
            await this.sleep(10 / speed)
          }
        }

        lastTimestamp = timestamp
      }
    } catch (error) {
      console.error('[SSEPlayer] Playback error:', error)
      onError?.(error as Error)
    } finally {
      this.isPlaying = false
      this.isPaused = false
      this.abortController = null
    }
  }

  /**
   * 暂停回放
   */
  pause(): void {
    if (this.isPlaying) {
      this.isPaused = true
    }
  }

  /**
   * 恢复回放
   */
  resume(): void {
    if (this.isPlaying && this.isPaused) {
      this.isPaused = false
    }
  }

  /**
   * 停止回放
   */
  stop(): void {
    if (this.abortController) {
      this.abortController.abort()
    }
  }

  /**
   * 获取回放状态
   */
  getStatus(): PlaybackStatus {
    if (!this.isPlaying) return 'idle'
    if (this.isPaused) return 'paused'
    return 'playing'
  }

  // ===== 私有方法 =====

  /**
   * 计算延迟时间
   */
  private calculateDelay(
    currentTimestamp: number,
    lastTimestamp: number,
    speed: number
  ): number {
    const originalDelay = currentTimestamp - lastTimestamp
    return Math.max(0, originalDelay / speed)
  }

  /**
   * 计算进度
   */
  private calculateProgress(
    eventIndex: number,
    totalEvents: number,
    compressedIndex = 0,
    compressedCount = 1
  ): PlaybackProgress {
    const baseProgress = eventIndex / totalEvents
    const compressedProgress = (compressedIndex + 1) / compressedCount / totalEvents
    const percentage = Math.round((baseProgress + compressedProgress) * 100)

    return {
      currentEventIndex: eventIndex,
      totalEvents,
      percentage,
      currentTime: Date.now(),
    }
  }

  /**
   * 延迟函数
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

// ===== 导出单例 =====

export const SSEPlayer = new SSEPlayerClass()
export default SSEPlayer