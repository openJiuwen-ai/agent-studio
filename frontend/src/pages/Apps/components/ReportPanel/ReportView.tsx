/**
 * 报告内容视图组件
 *
 * @description
 * 封装 Markdown 组件，专门用于展示报告内容
 * InferenceGraph 在 ReportView 层级渲染，定位在报告右下角
 */

import React, { useMemo, useEffect, useState, useRef } from 'react'
import { ReportMarkdown } from '../Markdown'
import { InferenceGraph } from '../InferenceGraph'
import { FileText, AlertCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { Report, TruthVerificationEntry } from '@/pages/Apps/types'
import { TruthVerificationLayer } from './TruthVerificationLayer'

/**
 * 加载状态类型
 */
type LoadingState = 'loading' | 'loaded' | 'empty' | 'timeout'

export interface ReportViewProps {
  /** 报告数据 */
  report: Report
  /** 自定义类名 */
  className?: string
  /** 真实性核验批注列表 */
  truthVerificationEntries?: TruthVerificationEntry[]
}

/**
 * 报告视图组件
 *
 * @description
 * - 为每个报告实例生成唯一的 instanceId
 * - 使用 Markdown 组件渲染报告内容
 */
export const ReportView: React.FC<ReportViewProps> = ({
  report,
  className = '',
  truthVerificationEntries = [],
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const articleRef = useRef<HTMLElement>(null)
  const { t } = useTranslation()
  // 检测用户是否偏好减少动画
  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }, [])

  // 加载状态
  const [loadingState, setLoadingState] = useState<LoadingState>('loading')
  // 使用 ref 跟踪当前加载状态（用于在超时定时器中检查）
  const loadingStateRef = useRef<LoadingState>('loading')

  // 超时和空内容检测
  useEffect(() => {
    // 报告切换时重置加载状态
    setLoadingState('loading')
    loadingStateRef.current = 'loading'

    // 检查内容是否为空
    const hasContent = report.content?.trim()

    // 正常加载：200ms 后显示内容或空状态
    const normalTimer = setTimeout(() => {
      const newState = hasContent ? 'loaded' : 'empty'
      setLoadingState(newState)
      loadingStateRef.current = newState
    }, 200)

    // 超时保护：3 秒后强制显示超时状态（仅当仍为 loading 时）
    const timeoutTimer = setTimeout(() => {
      if (loadingStateRef.current === 'loading') {
        setLoadingState('timeout')
        loadingStateRef.current = 'timeout'
      }
    }, 3000)

    return () => {
      clearTimeout(normalTimer)
      clearTimeout(timeoutTimer)
    }
  }, [report.id, report.content])

  // 生成唯一的 instanceId，用于缓存管理和引用链接标识
  const instanceId = useMemo(() => `report-${report.id}`, [report.id])

  return (
    <div className={`relative h-full flex flex-col ${className}`}>
      {/* 推理图浮层 - 定位在报告右下角 */}
      {report.inferMessages && report.inferMessages.length > 0 && (
        <InferenceGraph
          inferMessages={report.inferMessages}
          instanceId={instanceId}
        />
      )}

      {/* 内容区域 - 可滚动 */}
      <div
        ref={scrollContainerRef}
        className={`relative flex-1 overflow-auto ${prefersReducedMotion ? '' : 'scroll-smooth'} group`}
        style={{
          scrollbarWidth: 'thin',
          scrollbarColor: 'transparent transparent',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.scrollbarColor = '#6b7280 transparent'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.scrollbarColor = 'transparent transparent'
        }}
      >
        <article
          ref={articleRef as React.RefObject<HTMLElement>}
          className="max-w-10xl mx-auto bg-gray-50 px-6 pb-6 md:px-8 md:pb-8 min-h-[200px]"
          aria-label={`${t('apps.report.reportLabel')}: ${report.title || t('apps.report.unnamedReport')}`}
          aria-busy={loadingState === 'loading'}
          role="article"
        >
          {loadingState === 'loading' ? (
            // 加载骨架屏
            <div className="animate-pulse space-y-3" aria-hidden="true">
              <div className="h-4 bg-gray-200 rounded w-full"></div>
              <div className="h-4 bg-gray-200 rounded w-11/12"></div>
              <div className="h-4 bg-gray-200 rounded w-full"></div>
              <div className="h-4 bg-gray-200 rounded w-4/5"></div>
              <div className="h-4 bg-gray-200 rounded w-full"></div>
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            </div>
          ) : loadingState === 'empty' ? (
            // 空状态提示
            <div className="flex flex-col items-center justify-center py-16">
              <FileText className="w-12 h-12 text-gray-300 mb-4" />
              <p className="text-gray-500 text-sm">{t('apps.report.contentEmpty')}</p>
            </div>
          ) : loadingState === 'timeout' ? (
            // 超时错误提示
            <div className="flex flex-col items-center justify-center py-16">
              <AlertCircle className="w-12 h-12 text-amber-500 mb-4" />
              <p className="text-gray-700 font-medium mb-1">{t('apps.report.loadingTimeout')}</p>
              <p className="text-gray-500 text-sm text-center">{t('apps.report.timeoutMessage')}</p>
            </div>
          ) : (
            // 正常内容
            <ReportMarkdown
              instanceId={instanceId}
              content={report.content}
              citations={report.citations || null}
              inferMessages={report.inferMessages}
              chartMessages={report.chartMessages}
            />
          )}
        </article>
        {loadingState === 'loaded' && truthVerificationEntries.length > 0 && (
          <TruthVerificationLayer
            annotations={truthVerificationEntries}
            contentRef={articleRef}
            scrollContainerRef={scrollContainerRef}
            mode="view"
          />
        )}
      </div>
    </div>
  )
}
