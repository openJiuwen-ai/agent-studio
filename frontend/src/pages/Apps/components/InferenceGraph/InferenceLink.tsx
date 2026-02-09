/**
 * InferenceLink 组件
 * 只处理推理图谱链接 #inference:1
 */

import React, { useMemo, useState } from 'react'
import { Lightbulb } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@test-agentstudio/base-ui'
import { InferenceGraphManager } from './InferenceGraphManager'
import type { InferenceLinkProps } from './types'

/**
 * 判断链接是否指向推理图谱
 */
function parseInferenceLink(href: string | undefined): number | null {
  if (!href) return null
  const indexMatch = href.match(/#inference:(\d+)/)
  return indexMatch ? parseInt(indexMatch[1], 10) : null
}

/**
 * 推理图谱链接组件
 *
 * @description
 * - 只处理推理图谱链接 #inference:1 格式
 * - 显示悬停提示
 * - 点击时通过全局单例 InferenceGraphManager 打开推理图
 * - 支持多实例，通过 instanceId 区分不同报告
 * - 包含重试机制，处理渲染顺序依赖问题
 */
export const InferenceLink: React.FC<InferenceLinkProps> = ({
  href,
  children,
  instanceId,
}) => {
  const { t } = useTranslation()
  const inferenceIndex = useMemo(() => parseInferenceLink(href), [href])
  const isSourceTracerLink = inferenceIndex !== null

  // Tooltip 状态
  const [showTooltip, setShowTooltip] = useState(false)

  // 重试状态
  const [isRetrying, setIsRetrying] = useState(false)

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    if (inferenceIndex === null || !instanceId) return

    // 尝试打开推理图
    const success = InferenceGraphManager.open(instanceId, inferenceIndex)

    if (!success && !isRetrying) {
      // 失败且未重试，尝试重试
      setIsRetrying(true)

      // 等待 100ms 后重试（可能是 InferenceGraph 还未注册）
      setTimeout(() => {
        const retrySuccess = InferenceGraphManager.open(instanceId, inferenceIndex)
        if (!retrySuccess) {
          // 仍然失败，显示警告
          console.warn(
            `[InferenceLink] 无法打开推理图 #${inferenceIndex}，实例 ${instanceId} 未注册`
          )
        }
        setIsRetrying(false)
      }, 100)
    }
  }

  return (
    <>
      {isSourceTracerLink ? (
        <a
          href="#"
          onClick={handleClick}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          className={cn(
            'relative cursor-pointer',
            'text-purple-600',
            'hover:text-purple-800',
            'font-semibold',
            'hover:underline decoration-purple-500/50 underline-offset-2',
            'transition-all duration-150',
          )}
        >
          {/* Tooltip */}
          {showTooltip && (
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50">
              <span className="flex items-center gap-2 px-3 py-2 bg-white border border-purple-200 rounded-lg shadow-lg whitespace-nowrap">
                <span className="p-1 bg-purple-100 rounded">
                  <Lightbulb className="w-5.5 h-5.5 text-purple-600" />
                </span>
                <span>
                  <span className="block text-sm font-medium text-gray-900 leading-tight">{t('apps.inferenceGraph.title')}</span>
                  <span className="block text-xs text-gray-500 leading-tight">{t('apps.inferenceGraph.clickToViewDetail')}</span>
                </span>
              </span>
              {/* 箭头 */}
              <span className="absolute left-1/2 -translate-x-1/2 top-0 translate-y-1/2 rotate-45 w-2 h-2 bg-white border-r border-b border-purple-200"></span>
            </span>
          )}
          {children}
        </a>
      ) : (
        // 如果不是推理图链接，不渲染任何内容
        <>{children}</>
      )}
    </>
  )
}
