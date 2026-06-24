/**
 * AI改写选项组件
 *
 * @description
 * 提供快捷改写选项：润色、扩写、缩写
 * 绝对定位，基于目标元素位置显示
 */

import React, { useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Sparkles, Expand, Shrink, Search, ListPlus, ShieldCheck, ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { OPTIONS_HEIGHT, OPTIONS_OFFSET, REWRITE_ACTIONS, SUPPLEMENTARY_SEARCH_OPTIONS } from '../../constants'
import type { ReportRewriteAction, RewriteScope } from '@/pages/Apps/types'

interface AIRewriteOptionsProps {
  /** 当前选中的操作（用于高亮显示） */
  selectedAction: ReportRewriteAction | null
  /** 当前选中的范围 */
  selectedScope: RewriteScope | null
  /** 选中操作 */
  onSelect: (action: ReportRewriteAction) => void
  /** 选中范围 */
  onScopeSelect?: (scope: RewriteScope) => void
  /** 目标元素，选项将显示在其下方 */
  targetElement: HTMLElement | null
  /** 剩余改写次数；0 表示次数耗尽，受限操作将被隐藏 */
  remainingRewriteRounds?: number
}

// 图标映射
const ICON_MAP: Record<string, React.ReactNode> = {
  Sparkles: <Sparkles className="w-4 h-4" />,
  Expand: <Expand className="w-4 h-4" />,
  Shrink: <Shrink className="w-4 h-4" />,
  Search: <Search className="w-4 h-4" />,
  ListPlus: <ListPlus className="w-4 h-4" />,
  ShieldCheck: <ShieldCheck className="w-4 h-4" />,
}

export const AIRewriteOptions: React.FC<AIRewriteOptionsProps> = ({
  selectedAction,
  selectedScope,
  onSelect,
  onScopeSelect,
  targetElement,
  remainingRewriteRounds,
}) => {
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement>(null)
  const [coords, setCoords] = React.useState({ top: 0, left: 0 })
  const [hoveredAction, setHoveredAction] = React.useState<ReportRewriteAction | null>(null)
  const [subMenuCoords, setSubMenuCoords] = React.useState({ top: 0, left: 0 })

  // 计算并更新主菜单位置（初始 + 滚动/resize）
  useEffect(() => {
    if (!targetElement) return

    const updatePosition = () => {
      const rect = targetElement.getBoundingClientRect()
      const newTop = rect.bottom + window.scrollY + OPTIONS_OFFSET
      const newLeft = rect.left + window.scrollX

      // 仅在位置变化时更新状态
      setCoords(prev => {
        if (prev.top !== newTop || prev.left !== newLeft) {
          return { top: newTop, left: newLeft }
        }
        return prev
      })
    }

    updatePosition()
    window.addEventListener('scroll', updatePosition, true)
    window.addEventListener('resize', updatePosition)
    return () => {
      window.removeEventListener('scroll', updatePosition, true)
      window.removeEventListener('resize', updatePosition)
    }
  }, [targetElement])

  // 处理主菜单选项鼠标悬停
  const handleActionMouseEnter = (action: ReportRewriteAction) => {
    setHoveredAction(action)
    
    // 计算子菜单位置
    if (action === 'supplementary_search') {
      const buttonElement = document.querySelector(`[data-action="${action}"]`)
      if (buttonElement) {
        const rect = buttonElement.getBoundingClientRect()
        setSubMenuCoords({
          top: rect.top + window.scrollY,
          left: rect.right + window.scrollX
        })
      }
    } else {
      // 如果选择的不是补充搜索且selectedScope为null，关闭子菜单
      if (selectedScope === null) {
        setHoveredAction(null)
      }
    }
  }

  // 处理主菜单选项鼠标离开
  const handleActionMouseLeave = () => {
    // 如果 selectedScope 非 null，保持子菜单打开
    if (selectedScope === null) {
      setHoveredAction(null)
    }
  }

  // 处理范围选择
  const handleScopeSelect = (scope: RewriteScope) => {
    // 将选择的范围传递给父组件
    onScopeSelect?.(scope)
    // 将 selectedAction 设置为 supplementary_search，以高亮显示并启用发送按钮
    onSelect('supplementary_search')
    // 保持子菜单打开，不关闭
  }

  const roundsExhausted = remainingRewriteRounds === 0
  const roundLimitedActions = REWRITE_ACTIONS.filter(btn => btn.consumesRound)
  const freeActions = REWRITE_ACTIONS.filter(btn => !btn.consumesRound)
  const visibleRoundLimitedActions = roundsExhausted ? [] : roundLimitedActions
  const showDivider = visibleRoundLimitedActions.length > 0 && freeActions.length > 0

  if (!targetElement) return null

  return createPortal(
    <>
      {/* 主菜单 */}
      <div
        ref={containerRef}
        className="ai-rewrite-options fixed z-[1030] flex flex-col gap-1 p-2 bg-white rounded-lg border border-gray-200 shadow-lg"
        style={{
          top: coords.top,
          left: coords.left,
          width: 200,
        }}
      >
        {/* 受次数限制的动作（次数耗尽时隐藏） */}
        {visibleRoundLimitedActions.map((btn) => (
          <button
            key={btn.action}
            data-action={btn.action}
            onClick={() => btn.hasSubMenu ? undefined : onSelect(btn.action)}
            onMouseEnter={() => handleActionMouseEnter(btn.action)}
            onMouseLeave={handleActionMouseLeave}
            className={`
              flex items-center justify-between px-3 py-2 rounded-lg text-left
              transition-all duration-150 cursor-pointer
              border border-transparent
              ${selectedAction === btn.action
                ? 'bg-blue-50 text-blue-600 border-blue-200'
                : 'hover:bg-blue-50 hover:text-blue-600 text-gray-600 hover:border-blue-200'
              }
              ${btn.hasSubMenu ? 'cursor-default' : ''}
            `}
          >
            <div className="flex items-center gap-2">
              <span className={selectedAction === btn.action ? 'text-blue-500' : 'text-gray-400'}>
                {ICON_MAP[btn.icon]}
              </span>
              <span className="text-sm font-medium">{t(btn.labelKey) || btn.defaultLabel}</span>
            </div>
            {btn.hasSubMenu && (
              <ChevronRight className="w-3 h-3 text-gray-400" />
            )}
          </button>
        ))}

        {/* 分隔线（两组都有可见条目时才渲染） */}
        {showDivider && <div className="border-t border-gray-100 my-1" />}

        {/* 不受次数限制的动作（始终显示） */}
        {freeActions.map((btn) => (
          <button
            key={btn.action}
            data-action={btn.action}
            onClick={() => onSelect(btn.action)}
            onMouseEnter={() => handleActionMouseEnter(btn.action)}
            onMouseLeave={handleActionMouseLeave}
            className={`
              flex items-center justify-between px-3 py-2 rounded-lg text-left
              transition-all duration-150 cursor-pointer
              border border-transparent
              ${selectedAction === btn.action
                ? 'bg-blue-50 text-blue-600 border-blue-200'
                : 'hover:bg-blue-50 hover:text-blue-600 text-gray-600 hover:border-blue-200'
              }
            `}
          >
            <div className="flex items-center gap-2">
              <span className={selectedAction === btn.action ? 'text-blue-500' : 'text-gray-400'}>
                {ICON_MAP[btn.icon]}
              </span>
              <span className="text-sm font-medium">{t(btn.labelKey) || btn.defaultLabel}</span>
            </div>
          </button>
        ))}
      </div>

      {/* 补充搜索子菜单 */}
      {(hoveredAction === 'supplementary_search' || selectedScope !== null) && (
        <div
          className="ai-rewrite-options fixed z-[1031] flex flex-col gap-1 p-2 bg-white rounded-lg border border-gray-200 shadow-lg"
          style={{
            top: subMenuCoords.top,
            left: subMenuCoords.left,
            width: 150,
          }}
          onMouseEnter={() => setHoveredAction('supplementary_search')}
          onMouseLeave={handleActionMouseLeave}
        >
          <button
            onClick={() => handleScopeSelect('selected_only')}
            className={`
              flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm font-medium
              transition-all duration-150 cursor-pointer
              ${selectedScope === 'selected_only'
                ? 'bg-blue-50 text-blue-600 border-blue-200'
                : 'hover:bg-blue-50 hover:text-blue-600 text-gray-600 hover:border-blue-200'
              }
            `}
          >
            {t(SUPPLEMENTARY_SEARCH_OPTIONS.selected_only.labelKey) || SUPPLEMENTARY_SEARCH_OPTIONS.selected_only.defaultLabel}
          </button>
          <button
            onClick={() => handleScopeSelect('selected_and_related')}
            className={`
              flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm font-medium
              transition-all duration-150 cursor-pointer
              ${selectedScope === 'selected_and_related'
                ? 'bg-blue-50 text-blue-600 border-blue-200'
                : 'hover:bg-blue-50 hover:text-blue-600 text-gray-600 hover:border-blue-200'
              }
            `}
          >
            {t(SUPPLEMENTARY_SEARCH_OPTIONS.selected_and_related.labelKey) || SUPPLEMENTARY_SEARCH_OPTIONS.selected_and_related.defaultLabel}
          </button>
        </div>
      )}
    </>,
    document.body
  )
}

// 导出高度供其他组件使用
export { OPTIONS_HEIGHT }
