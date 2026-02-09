/**
 * 剪贴板操作 Hook
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { showNotification } from '@/utils/notifications'

/** 复制状态重置延迟 (ms) */
const COPY_RESET_DELAY = 2000

/**
 * 剪贴板 Hook 返回值
 */
export interface UseClipboardReturn {
  /** 是否已复制 */
  copied: boolean
  /** 复制文本到剪贴板 */
  copy: (text: string, successMessage?: string) => Promise<void>
  /** 复制按钮 ref */
  copyButtonRef: React.RefObject<HTMLButtonElement | null>
}

/**
 * 检查 Clipboard API 是否可用
 */
const isClipboardApiAvailable = (): boolean => {
  return (
    typeof navigator !== 'undefined' &&
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === 'function'
  )
}

/**
 * 使用传统方法复制（降级方案）
 */
const fallbackCopy = async (text: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    // 创建临时 textarea 元素
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-999999px'
    textarea.style.top = '-999999px'
    document.body.appendChild(textarea)

    // 选中文本
    textarea.focus()
    textarea.select()

    try {
      // 执行复制命令
      const successful = document.execCommand('copy')
      document.body.removeChild(textarea)

      if (successful) {
        resolve()
      } else {
        reject(new Error('execCommand copy failed'))
      }
    } catch (err) {
      document.body.removeChild(textarea)
      reject(err)
    }
  })
}

/**
 * 剪贴板操作 Hook
 * 处理复制到剪贴板功能，包含状态管理和通知
 */
export function useClipboard(): UseClipboardReturn {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  const copyTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const copyButtonRef = useRef<HTMLButtonElement | null>(null)

  /**
   * 复制文本到剪贴板
   */
  const copy = useCallback(async (text: string, successMessage?: string) => {
    const defaultMessage = t('apps.clipboard.copiedToClipboard')
    const errorMessage = t('apps.notifications.copyFailed')

    try {
      // 优先使用 Clipboard API
      if (isClipboardApiAvailable()) {
        await navigator.clipboard.writeText(text)
      } else {
        // 降级到传统方法
        await fallbackCopy(text)
      }

      setCopied(true)
      showNotification(successMessage || defaultMessage, 'success')

      // 清理之前的 timeout
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current)
      }

      // 重置复制状态
      copyTimeoutRef.current = setTimeout(() => {
        setCopied(false)
      }, COPY_RESET_DELAY)
    } catch (error) {
      console.error('[useClipboard] Copy failed:', error)
      showNotification(errorMessage, 'error')
    }
  }, [t])

  /**
   * 组件卸载时清理 timeout
   */
  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current)
      }
    }
  }, [])

  return {
    copied,
    copy,
    copyButtonRef,
  }
}
