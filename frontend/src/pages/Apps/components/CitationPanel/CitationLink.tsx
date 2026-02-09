/**
 * CitationLink 组件
 * 只处理引用链接 [1]
 */

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { cn } from '@test-agentstudio/base-ui'
import type { CitationMessages } from '@/pages/Apps/types'
import { CitationTooltip } from './CitationTooltip'
import { CitationTooltipContent } from './CitationTooltipContent'

export interface CitationLinkProps {
  href?: string
  children: React.ReactNode
  citations?: CitationMessages | null
  markdownInstanceId?: string | null
}

// ============ linkIndex 计数器 ============

// 模块级计数器存储：instanceId → 当前计数
const linkIndexCounters = new Map<string, number>()

/**
 * 重置实例的链接索引计数器
 */
export function resetLinkIndexCounter(instanceId: string | null): void {
  if (instanceId) {
    linkIndexCounters.delete(instanceId)
  }
}

// ============ 组件 ============

/**
 * 引用链接组件
 *
 * @description
 * - 只处理引用链接 [1] 格式
 * - linkIndex 从 0 开始，按出现顺序递增
 * - 直接用 linkIndex 作为 citations.data 的索引
 * - 显示 tooltip，包含引用详细信息
 */
export const CitationLink: React.FC<CitationLinkProps> = ({
  href,
  children,
  citations = null,
  markdownInstanceId = null,
}) => {
  // ============ linkIndex 计数逻辑 ============
  const linkIndexRef = useRef<number>(-1)

  useEffect(() => {
    if (!markdownInstanceId) {
      return
    }

    // 获取当前计数器值
    const current = linkIndexCounters.get(markdownInstanceId) ?? 0

    // 分配索引
    linkIndexRef.current = current

    // 递增计数器
    linkIndexCounters.set(markdownInstanceId, current + 1)
  }, [markdownInstanceId])

  const linkIndex = linkIndexRef.current

  // ============ 数据查找逻辑 ============
  const citationData = useMemo(() => {
    // 如果没有引用数据或 linkIndex 无效，返回空
    if (
      !citations?.data ||
      citations.data.length === 0 ||
      linkIndex < 0
    ) {
      return null
    }

    // 直接用 linkIndex 作为索引
    return citations.data[linkIndex] || null
  }, [linkIndex, citations])

  // ============ Tooltip 状态 ============
  const [isTooltipOpen, setIsTooltipOpen] = useState(false)
  const tooltipRef = useRef<HTMLSpanElement>(null)

  // 点击处理
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsTooltipOpen(!isTooltipOpen)
  }

  // 外部点击监听
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (tooltipRef.current && !tooltipRef.current.contains(event.target as Node)) {
        setIsTooltipOpen(false)
      }
    }

    if (isTooltipOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isTooltipOpen])

  return (
    <span ref={tooltipRef}>
      <CitationTooltip
        open={isTooltipOpen}
        className="border border-gray-200 bg-white shadow-lg [&_svg]:!bg-white [&_svg]:!fill-white"
        title={citationData ? <CitationTooltipContent citationData={citationData} href={href} /> : null}
        side="top"
        sideOffset={2}
      >
        <a
          href="#"
          onClick={e => {
            e.preventDefault()
            handleClick(e)
          }}
          className={cn(
            'cursor-pointer font-semibold',
            'text-blue-600',
            'hover:text-blue-800',
            'hover:underline',
            'transition-colors duration-150',
          )}
          data-link-index={linkIndex}
        >
          {children}
        </a>
      </CitationTooltip>
    </span>
  )
}

export default CitationLink
