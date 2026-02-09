/**
 * 通知系统工具函数
 *
 * 使用全局 CustomEvent 来触发 Snackbar 通知
 * 配合 UnifiedSnackbar 组件使用
 */

export type NotificationSeverity = 'success' | 'error' | 'warning' | 'info'

// 防抖机制：记录最近的通知消息
const recentMessages = new Map<string, number>()
const DEFAULT_DEBOUNCE_MS = 1000 // 默认防抖时间 1 秒

/**
 * 清理过期的通知记录
 *
 * @param key - 消息键
 * @param debounceMs - 防抖时间
 */
function cleanupRecentMessage(key: string, debounceMs: number): void {
  setTimeout(() => {
    recentMessages.delete(key)
  }, debounceMs)
}

/**
 * 显示全局通知消息（带防抖）
 *
 * 通过分发 'global-snackbar' 事件来触发 Snackbar 通知
 * 需要确保页面中已渲染 UnifiedSnackbar 组件
 *
 * @param message - 通知消息内容
 * @param severity - 通知级别，默认为 'info'
 * @param debounceMs - 防抖时间（毫秒），默认 1000ms
 *
 * @example
 * ```ts
 * showNotification('操作成功', 'success')
 * showNotification('发生错误', 'error')
 * showNotification('请注意', 'warning')
 * showNotification('提示信息') // 默认 info
 * ```
 */
export function showNotification(message: string, severity: NotificationSeverity = 'info', debounceMs = DEFAULT_DEBOUNCE_MS): void {
  const key = `${message}-${severity}`
  const now = Date.now()
  const lastTime = recentMessages.get(key)

  // 如果相同消息在短时间内显示过，则跳过
  if (lastTime && now - lastTime < debounceMs) {
    return
  }

  recentMessages.set(key, now)
  cleanupRecentMessage(key, debounceMs)

  window.dispatchEvent(new CustomEvent('global-snackbar', {
    detail: { message, severity }
  }))
}

/**
 * 显示成功通知
 *
 * @param message - 成功消息
 */
export function showSuccess(message: string): void {
  showNotification(message, 'success')
}

/**
 * 显示错误通知
 *
 * @param message - 错误消息
 */
export function showError(message: string): void {
  showNotification(message, 'error')
}

/**
 * 显示警告通知
 *
 * @param message - 警告消息
 */
export function showWarning(message: string): void {
  showNotification(message, 'warning')
}

/**
 * 显示信息通知
 *
 * @param message - 信息消息
 */
export function showInfo(message: string): void {
  showNotification(message, 'info')
}
