/**
 * 推理图谱模态框管理 Hook
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { BlobUrlManager } from './blobUrlManager'
import { showNotification } from '@/utils/notifications'
import type { UseGraphModalReturn } from './types'

/**
 * 推理图谱模态框管理 Hook
 * 处理推理图谱的显示、隐藏和 Blob URL 生命周期
 */
export function useGraphModal(): UseGraphModalReturn {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)
  const blobManager = useRef(new BlobUrlManager())

  /**
   * 打开推理图谱
   */
  const open = useCallback((htmlBase64: string) => {
    try {
      const url = blobManager.current.set(htmlBase64)
      setBlobUrl(url)
      setIsOpen(true)
    } catch (error) {
      console.error('[useGraphModal] 打开推理图失败:', error)
      showNotification(t('apps.inferenceGraph.loadError'), 'error')
    }
  }, [t])

  /**
   * 关闭推理图谱
   */
  const close = useCallback(() => {
    setIsOpen(false)
    blobManager.current.clear()
    setBlobUrl(null)
  }, [])

  /**
   * 在新标签页打开推理图谱
   */
  const openInNewTab = useCallback(() => {
    if (blobUrl) {
      window.open(blobUrl, '_blank', 'noopener,noreferrer')
      showNotification(t('apps.inferenceGraph.openInNewTabSuccess'), 'success')
    }
  }, [blobUrl, t])

  /**
   * Escape 键处理
   */
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        close()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      // 推理图谱打开时聚焦到关闭按钮
      closeButtonRef.current?.focus()
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, close])

  /**
   * 组件卸载时清理资源
   */
  useEffect(() => {
    return () => {
      blobManager.current.destroy()
    }
  }, [])

  return {
    isOpen,
    blobUrl,
    closeButtonRef,
    open,
    close,
    openInNewTab,
  }
}