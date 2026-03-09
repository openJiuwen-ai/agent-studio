/**
 * 推理图谱 iframe 展示组件
 *
 * 通过 iframe 嵌入后端生成的推理图谱 HTML 文件
 */

import React, { useMemo, useState, useEffect, useCallback } from 'react'
import { RotateCcw, RefreshCw, MousePointer2, ZoomIn } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { GraphIframeProps } from './types'

// 加载超时时间（毫秒）
const LOADING_TIMEOUT = 10000

/**
 * 构建推理图谱文件的基础 URL
 */
const getInferenceBaseUrl = (): string => {
  // 尝试从 Vite 环境变量获取
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL as string
    // 去掉 /api/v1 后缀，得到基础 URL
    const baseUrl = apiBaseUrl.replace(/\/api\/v\d+$/, '')
    return baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl
  }

  // 回退到 window 全局变量（由 vite 注入）
  if (typeof window !== 'undefined') {
    const win = window as unknown as { __API_BASE_URL__?: string }
    if (win.__API_BASE_URL__) {
      const baseUrl = win.__API_BASE_URL__.replace(/\/api\/v\d+$/, '')
      return baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl
    }
  }

  // 默认使用 localhost:8000
  return 'http://localhost:8000'
}

/**
 * 推理图谱 iframe 展示组件
 */
export const GraphIframe: React.FC<GraphIframeProps> = ({
  inferFiles,
  className = '',
}) => {
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [hasTimedOut, setHasTimedOut] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)

  // 构建推理图谱文件 URL
  const inferFileUrl = useMemo(() => {
    if (inferFiles.length === 0) return ''

    const filePath = inferFiles[0]

    // 如果是 Blob URL，直接使用（已经是从 base64 转换来的完整 URL）
    if (filePath.startsWith('blob:')) {
      return filePath
    }

    // 否则，按照文件路径处理（从服务器加载）
    const baseUrl = getInferenceBaseUrl()
    // 确保路径以斜杠开头
    const normalizedPath = filePath.startsWith('/') ? filePath : `/${filePath}`
    return `${baseUrl}${normalizedPath}`
  }, [inferFiles])

  // 加载超时处理
  useEffect(() => {
    if (!isLoading) {
      setHasTimedOut(false)
      return
    }

    const timer = setTimeout(() => {
      if (isLoading) {
        setHasTimedOut(true)
      }
    }, LOADING_TIMEOUT)

    return () => clearTimeout(timer)
  }, [isLoading])

  // 重试加载
  const handleRetry = useCallback(() => {
    setHasError(false)
    setHasTimedOut(false)
    setIsLoading(true)
    setIframeKey(prev => prev + 1)
  }, [])

  // 处理 iframe 加载完成
  const handleLoad = useCallback(() => {
    setIsLoading(false)
    setHasTimedOut(false)
  }, [])

  // 处理 iframe 加载错误
  const handleError = useCallback(() => {
    setIsLoading(false)
    setHasTimedOut(false)
    setHasError(true)
  }, [])

  // 如果没有文件，显示提示
  if (inferFiles.length === 0 || !inferFileUrl) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-muted-foreground text-sm">{t('apps.inferenceGraph.noGraph')}</div>
      </div>
    )
  }

  // 错误状态
  if (hasError) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div
          role="alert"
          aria-live="polite"
          className="text-center space-y-3"
        >
          <p className="text-muted-foreground text-sm">{t('apps.inferenceGraph.loadFailed')}</p>
          <p className="text-muted-foreground/60 text-xs">{t('apps.inferenceGraph.retryLater')}</p>
          <button
            onClick={handleRetry}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 hover:bg-purple-200 rounded-lg transition-colors duration-200 cursor-pointer focus-visible:outline-2 focus-visible:outline-purple-500 focus-visible:outline-offset-2"
            type="button"
            aria-label={t('apps.inferenceGraph.reload')}
          >
            <RotateCcw className="w-4 h-4 text-purple-600" />
            <span className="text-sm text-purple-600">{t('apps.inferenceGraph.retry')}</span>
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex h-full flex-col ${className}`}>
      <div className="relative flex-1 min-h-0">
        {/* 加载状态 */}
        {isLoading && (
          <div
            className="absolute inset-0 z-10 flex items-center justify-center bg-white/80 backdrop-blur-sm"
            aria-hidden="true"
          >
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-t-transparent border-purple-500" />
              <p className="text-sm text-gray-600">{t('apps.inferenceGraph.loading')}</p>
              {/* 交互提示 */}
              <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-100 px-3 py-1.5 rounded-full">
                <MousePointer2 className="w-3.5 h-3.5" />
                <span>{t('apps.inferenceGraph.dragAndZoom')}</span>
              </div>
              {hasTimedOut && (
                <button
                  onClick={handleRetry}
                  className="inline-flex items-center gap-2 px-3 py-1.5 bg-purple-100 hover:bg-purple-200 rounded-lg transition-colors duration-200 cursor-pointer focus-visible:outline-2 focus-visible:outline-purple-500 focus-visible:outline-offset-2 text-sm"
                  type="button"
                  aria-label={t('apps.inferenceGraph.cancel')}
                >
                  <RotateCcw className="w-3.5 h-3.5 text-purple-600" />
                  <span className="text-purple-600">{t('apps.inferenceGraph.retry')}</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* 推理图谱 iframe */}
        <iframe
          key={iframeKey}
          src={inferFileUrl}
          sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
          className="h-full w-full border-0"
          onLoad={handleLoad}
          onError={handleError}
          title={t('apps.inferenceGraph.title')}
          role="img"
          aria-label={t('apps.inferenceGraph.ariaLabel')}
        />

        {/* 底部操作提示栏 */}
        {!isLoading && !hasError && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10">
            <div className="flex items-center gap-3 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-full px-4 py-2 shadow-lg">
              {/* 操作提示 */}
              <div className="flex items-center gap-2 text-xs text-gray-600">
                <div className="flex items-center gap-1">
                  <MousePointer2 className="w-3.5 h-3.5" />
                  <span>{t('apps.inferenceGraph.dragToMove')}</span>
                </div>
                <span className="text-gray-300">·</span>
                <div className="flex items-center gap-1">
                  <ZoomIn className="w-3.5 h-3.5" />
                  <span>{t('apps.inferenceGraph.wheelToZoom')}</span>
                </div>
              </div>
              {/* 分隔线 */}
              <div className="w-px h-4 bg-gray-300" />
              {/* 重置按钮 */}
              <button
                onClick={handleRetry}
                className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-700 transition-colors duration-200 cursor-pointer focus-visible:outline-2 focus-visible:outline-purple-500 focus-visible:outline-offset-2"
                type="button"
                aria-label={t('apps.inferenceGraph.resetView')}
                title={t('apps.inferenceGraph.resetView')}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>{t('apps.inferenceGraph.reset')}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
