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
import type { Report } from '@/pages/Apps/types'

/**
 * 加载状态类型
 */
type LoadingState = 'loading' | 'loaded' | 'empty' | 'timeout'

export interface ReportViewProps {
  /** 报告数据 */
  report: Report
  /** 自定义类名 */
  className?: string
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
}) => {
  const { t } = useTranslation()
  // 检测用户是否偏好减少动画
  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }, [])

  // 加载状态
  const [loadingState, setLoadingState] = useState<LoadingState>('loading')
  const loadingStateRef = useRef<LoadingState>('loading')

  // 超时和空内容检测
  useEffect(() => {
    // 报告切换时重置加载状态
    setLoadingState('loading')
    loadingStateRef.current = 'loading'

    // 检查内容是否为空
    const hasContent = report.response_content?.trim()

    // 正常加载：200ms 后显示内容或空状态
    const normalTimer = setTimeout(() => {
      if (hasContent) {
        setLoadingState('loaded')
        loadingStateRef.current = 'loaded'
      } else {
        setLoadingState('empty')
        loadingStateRef.current = 'empty'
      }
    }, 200)

    // 超时保护：3 秒后强制显示超时状态
    const timeoutTimer = setTimeout(() => {
      // 只有当前仍然是 loading 状态时才设置为超时
      if (loadingStateRef.current === 'loading') {
        setLoadingState('timeout')
        loadingStateRef.current = 'timeout'
      }
    }, 3000)

    return () => {
      clearTimeout(normalTimer)
      clearTimeout(timeoutTimer)
    }
  }, [report.id, report.response_content])

  // 生成唯一的 instanceId，用于缓存管理和引用链接标识
  const instanceId = useMemo(() => `report-${report.id}`, [report.id])

  return (
    <div className={`relative h-full flex flex-col ${className}`}>
      {/* 推理图浮层 - 定位在报告右下角 */}
      {report.infer_messages && report.infer_messages.length > 0 && (
        <InferenceGraph
          inferMessages={report.infer_messages}
          instanceId={instanceId}
        />
      )}

      {/* 内容区域 - 可滚动 */}
      <div className={`flex-1 overflow-auto ${prefersReducedMotion ? '' : 'scroll-smooth'}`}>
        <article
          className="max-w-5xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-200 p-6 md:p-8 min-h-[200px]"
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
              content={report.response_content}
              citations={report.citation_messages || null}
              inferMessages={report.infer_messages}
            />
          )}
        </article>
      </div>
    </div>
  )
}