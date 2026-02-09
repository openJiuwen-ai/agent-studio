/**
 * 推理图谱模态框组件
 *
 * 显示推理图谱的浮动面板，定位在报告右下角
 * 长宽为报告界面的 3/5
 */

import React, { useEffect, useRef } from 'react'
import { X, ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useReducedMotion, useIsMobile } from '@/pages/Apps/components/shared'
import { GraphIframe } from './GraphIframe'
import type { GraphModalProps } from './types'

/**
 * 获取可聚焦元素选择器
 */
const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  '[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

/**
 * 推理图谱模态框组件
 */
export const GraphModal: React.FC<GraphModalProps> = ({
  show,
  blobUrl,
  closeButtonRef,
  onClose,
  onOpenInNewTab,
  className = '',
}) => {
  const { t } = useTranslation()
  const prefersReducedMotion = useReducedMotion()
  const isMobile = useIsMobile()
  const modalRef = useRef<HTMLDivElement>(null)

  // 点击遮罩层关闭
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  // 阻止 modal 内容点击冒泡
  const handleModalClick = (e: React.MouseEvent) => {
    e.stopPropagation()
  }

  // 焦点陷阱实现
  useEffect(() => {
    if (!show) return

    const modalElement = modalRef.current
    if (!modalElement) return

    // 获取所有可聚焦元素
    const focusableElements = modalElement.querySelectorAll<HTMLElement>(
      FOCUSABLE_SELECTOR
    )
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    // 处理 Tab 键循环
    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        // Shift + Tab: 移动到最后一个元素
        if (document.activeElement === firstElement) {
          e.preventDefault()
          lastElement?.focus()
        }
      } else {
        // Tab: 移动到第一个元素
        if (document.activeElement === lastElement) {
          e.preventDefault()
          firstElement?.focus()
        }
      }
    }

    document.addEventListener('keydown', handleTab)

    return () => {
      document.removeEventListener('keydown', handleTab)
    }
  }, [show])

  if (!show || !blobUrl) return null

  // 桌面端：不显示 backdrop（因为推理图是浮在右下角的）
  // 移动端：显示 backdrop（因为推理图是全屏的）
  const showBackdrop = isMobile

  return (
    <>
      {/* 移动端 backdrop */}
      {showBackdrop && (
        <div
          className={`fixed inset-0 z-40 bg-black/40 backdrop-blur-sm ${
            prefersReducedMotion ? '' : 'transition-opacity duration-200'
          }`}
          onClick={handleBackdropClick}
          aria-hidden="true"
        />
      )}

      {/* Modal 主体 - 定位在报告右下角，长宽为报告界面的 3/5 */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label={t('apps.inferenceGraph.title')}
        onClick={handleModalClick}
        className={`
          absolute z-50 bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden antialiased
          ${isMobile
            ? 'inset-4 w-auto h-auto'
            : 'bottom-0 right-5 w-3/5 h-3/5'
          }
          ${prefersReducedMotion ? '' : 'transition-[opacity,transform] duration-200 ease-out'}
          ${className}
        `}
      >
        {/* 操作按钮组 */}
        <div className="absolute top-1 right-4 z-10 flex items-center gap-2">
          {/* 新页签按钮 */}
          <button
            onClick={onOpenInNewTab}
            className="p-3 bg-purple-100 hover:bg-purple-200 rounded-lg transition-colors duration-200 shadow-md cursor-pointer focus-visible:outline-2 focus-visible:outline-purple-500 focus-visible:outline-offset-2"
            title={t('apps.inferenceGraph.openInNewTab')}
            aria-label={t('apps.inferenceGraph.openInNewTab')}
            type="button"
          >
            <ExternalLink className="w-5 h-5 text-purple-600" />
          </button>

          {/* 关闭按钮 */}
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="p-3 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200 shadow-md cursor-pointer focus-visible:outline-2 focus-visible:outline-gray-500 focus-visible:outline-offset-2"
            title={t('apps.inferenceGraph.closeModal')}
            aria-label={t('apps.inferenceGraph.closeModal')}
            type="button"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* 推理图谱内容 */}
        <GraphIframe inferFiles={[blobUrl]} />
      </div>
    </>
  )
}