/**
 * 引用提示内容组件
 * 显示引用的详细信息，支持高亮标记和自动滚动
 */

import React, { useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import type { CitationData } from '@/pages/Apps/types'

export interface CitationTooltipContentProps {
  citationData: CitationData
  href?: string
  onScrollRef?: (ref: HTMLDivElement | null) => void
}

// 高亮内容的样式
const HIGHLIGHT_MARK_STYLE = 'background-color: #fef08a; padding: 0 0.25rem; border-radius: 0.25rem;'

// 格式化content中的mark标签
const formatContent = (content: string): string => {
  return content.replace(/\n/g, '<br>').replace(/<mark>(.*?)<\/mark>/g, (_match, p1) => `<mark style="${HIGHLIGHT_MARK_STYLE}">${p1}</mark>`)
}

// 滚动到高亮内容的Hook
const useScrollToHighlight = (isActive: boolean, _scrollRef: React.RefObject<HTMLDivElement | null>) => {
  useEffect(() => {
    if (!isActive) return

    const scheduleScroll = () => {
      const executeScroll = (rafCount = 0) => {
        if (rafCount < 3) {
          requestAnimationFrame(() => executeScroll(rafCount + 1))
          return
        }

        const markElement = document.querySelector('mark')
        if (!markElement) return

        // 查找滚动容器
        let scrollContainer: HTMLElement | null = markElement as HTMLElement
        let foundScrollContainer = false

        while (scrollContainer && !foundScrollContainer) {
          const style = window.getComputedStyle(scrollContainer)
          const overflowY = style.overflowY
          const overflow = style.overflow
          const isOverflowScroll = ['auto', 'scroll'].includes(overflowY) || ['auto', 'scroll'].includes(overflow)
          const hasScrollableContent = scrollContainer.scrollHeight > scrollContainer.clientHeight

          if (isOverflowScroll && hasScrollableContent) {
            foundScrollContainer = true
            break
          }
          scrollContainer = scrollContainer.parentElement
        }

        if (!scrollContainer) return

        // 计算滚动位置
        const containerRect = scrollContainer.getBoundingClientRect()
        const markRect = (markElement as HTMLElement).getBoundingClientRect()
        const relativeTop = markRect.top - containerRect.top
        const maxScroll = scrollContainer.scrollHeight - scrollContainer.clientHeight

        let targetScrollTop = scrollContainer.scrollTop + relativeTop
        targetScrollTop = Math.max(0, Math.min(targetScrollTop, maxScroll))

        // 执行滚动
        try {
          scrollContainer.scrollTop = targetScrollTop
          requestAnimationFrame(() => {
            if (scrollContainer) {
              scrollContainer.scrollTop = targetScrollTop
            }
          })
        } catch (error) {
          console.error('[CitationTooltipContent] Error during scroll:', error)
        }
      }

      executeScroll()
    }

    setTimeout(scheduleScroll, 200)
  }, [isActive])
}

// 日历图标组件
const CalendarIcon: React.FC<{ className?: string }> = ({ className = 'mr-1 text-gray-500' }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="10"
    height="10"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
    <line x1="16" y1="2" x2="16" y2="6"></line>
    <line x1="8" y1="2" x2="8" y2="6"></line>
    <line x1="3" y1="10" x2="21" y2="10"></line>
  </svg>
)

// 验证 publish_time 是否为有效时间格式
const isValidPublishTime = (publishTime: string): boolean => {
  if (!publishTime || publishTime.trim() === '') return false

  const timestamp = Date.parse(publishTime)
  return !isNaN(timestamp)
}

// 可信度评分显示组件
const CreditScore: React.FC<{ score?: number }> = ({ score }) => {
  const { t } = useTranslation()

  if (score === undefined) return null

  const getScoreLabel = (score: number) => {
    if (score < 0.5) return { label: t('apps.citation.scoreLow'), className: 'text-amber-500' }
    if (score < 0.9) return { label: t('apps.citation.scoreMedium'), className: 'text-blue-500' }
    return { label: t('apps.citation.scoreHigh'), className: 'text-green-500' }
  }

  const { label, className } = getScoreLabel(score)

  return (
    <span className="inline-flex items-center">
      <span className="text-gray-700">{t('apps.citation.matchScore')}：</span>
      <span className={className}>{label}</span>
    </span>
  )
}

/**
 * 引用提示内容组件
 *
 * @description
 * - 显示引用的标题、来源、内容
 * - 支持高亮标记 <mark> 标签
 * - 自动滚动到高亮内容
 * - 显示匹配度评分
 */
export const CitationTooltipContent: React.FC<CitationTooltipContentProps> = ({ citationData, href, onScrollRef }) => {
  const { t } = useTranslation()
  const contentScrollRef = useRef<HTMLDivElement>(null)

  // 暴露ref给父组件
  useEffect(() => {
    if (onScrollRef) {
      onScrollRef(contentScrollRef.current)
    }
  }, [onScrollRef])

  // 当tooltip显示时滚动到高亮内容
  useScrollToHighlight(true, contentScrollRef)

  return (
    <div className="max-w-md p-2">
      {/* 标题部分 */}
      {citationData.title && (
        <div className="mb-3">
          <div
            role="link"
            tabIndex={0}
            onClick={e => {
              e.stopPropagation()
              if (href) window.open(href, '_blank')
            }}
            onMouseDown={e => e.stopPropagation()}
            className="cursor-pointer transition-colors hover:text-blue-600"
          >
            <h3 className="mt-2 mb-2 flex items-center text-base font-bold text-gray-900">
              {citationData.from && (
                <span className="mr-2 flex-shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                  {citationData.from}
                </span>
              )}
              <span className="truncate">{citationData.title}</span>
            </h3>
          </div>
        </div>
      )}

      {/* 内容部分 */}
      {citationData.content && (
        <div className="mb-4">
          <div ref={contentScrollRef} style={{ maxHeight: '300px', overflow: 'auto' }} className="w-full rounded-md bg-gray-200/30 p-2">
            <div className="text-sm break-words text-gray-700">
              <div dangerouslySetInnerHTML={{ __html: formatContent(citationData.content) }} />
            </div>
          </div>
        </div>
      )}

      {/* 底部元数据 */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-1">
          {citationData.publish_time !== undefined &&
           citationData.publish_time !== null &&
           citationData.publish_time !== '' &&
           isValidPublishTime(citationData.publish_time) && (
            <span className="inline-flex items-center text-gray-600">
              <CalendarIcon />
              {citationData.publish_time}
            </span>
          )}
          {citationData.source &&
           citationData.publish_time !== undefined &&
           citationData.publish_time !== null &&
           citationData.publish_time !== '' &&
           isValidPublishTime(citationData.publish_time) && (
            <span className="mx-1 inline-flex items-center text-gray-500">|</span>
          )}
          {citationData.source && <span className="inline-flex items-center text-gray-600">{t('apps.citation.source')}：{citationData.source}</span>}
        </div>
        <div className="flex items-center gap-2">
          <CreditScore score={citationData.score} />
        </div>
      </div>
    </div>
  )
}
