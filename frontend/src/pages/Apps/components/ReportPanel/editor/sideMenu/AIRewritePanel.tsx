/**
 * AI 改写面板组件
 *
 * @description
 * 显示在块下方，提供用户输入和快捷选项
 * - AIRewriteInput 直接插入到块下方
 * - AIRewriteOptions 基于 Input 位置定位
 */

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import type { Block, BlockNoteEditor } from '@blocknote/core'
import { AIRewriteInput } from './AIRewriteInput'
import { AIRewriteOptions } from './AIRewriteOptions'
import { useClickOutsideSelectors } from '@/hooks/prompts'
import type { ReportRewriteAction, RewriteScope } from '@/pages/Apps/types'

// 使用泛型 Block 类型以兼容 BlockNote 的扩展状态
type AnyBlock = Block<any, any, any>

export interface AIRewritePanelProps {
  /** 当前块 */
  block: AnyBlock
  /** 编辑器实例 - 预留给未来功能使用 */
  editor?: BlockNoteEditor
  /** 关闭回调 */
  onClose: () => void
  /** 提交回调 */
  onSubmit: (action: ReportRewriteAction, prompt?: string, rewriteScope?: RewriteScope) => void
  /** 剩余改写次数 */
  remainingRewriteRounds?: number
  /** 当前选中的范围 */
  selectedScope: RewriteScope | null
  /** 选中范围回调 */
  onScopeSelect: (scope: RewriteScope | null) => void
}

/**
 * AI 改写面板组件
 */
export const AIRewritePanel: React.FC<AIRewritePanelProps> = ({
  block,
  onClose,
  onSubmit,
  remainingRewriteRounds,
  selectedScope,
  onScopeSelect,
}) => {
  const { t } = useTranslation()
  const [input, setInput] = useState('')
  const [selectedAction, setSelectedAction] = useState<ReportRewriteAction | null>(null)
  const [inputPosition, setInputPosition] = useState({ top: 0, left: 0, width: 320 })
  const inputRef = useRef<HTMLDivElement>(null)

  // 计算 Input 位置（在块下方）
  const updatePosition = useCallback(() => {
    if (!block?.id) return
    const blockElement = document.querySelector(`[data-id="${block.id}"]`)
    if (blockElement) {
      const rect = blockElement.getBoundingClientRect()
      const newTop = rect.bottom + window.scrollY + 8
      const newLeft = rect.left + window.scrollX
      const newWidth = rect.width

      // 仅在位置变化时更新状态，避免不必要的重渲染
      setInputPosition(prev => {
        if (prev.top !== newTop || prev.left !== newLeft || prev.width !== newWidth) {
          return { top: newTop, left: newLeft, width: newWidth }
        }
        return prev
      })
    }
  }, [block?.id])

  // 初始化位置和监听滚动
  useEffect(() => {
    updatePosition()

    const handleScroll = () => updatePosition()
    window.addEventListener('scroll', handleScroll, true)
    window.addEventListener('resize', updatePosition)

    return () => {
      window.removeEventListener('scroll', handleScroll, true)
      window.removeEventListener('resize', updatePosition)
    }
  }, [updatePosition])

  // 发送处理（带 prompt）
  const handleSend = () => {
    if (!selectedAction) return
    if (selectedAction === 'supplementary_search') {
      onSubmit(selectedAction, input || undefined, selectedScope)
    } else {
      onSubmit(selectedAction, input || undefined)
    }
  }

  // 选项选中处理
  const handleSelectAction = (action: ReportRewriteAction) => {
    setSelectedAction(action)
    // 如果选择的不是补充搜索，重置选择范围
    if (action !== 'supplementary_search') {
      onScopeSelect(null)
    }
  }

  // 范围选择处理
  const handleScopeSelect = (scope: RewriteScope | null) => {
    onScopeSelect(scope)
    if (scope !== null) {
      setSelectedAction('supplementary_search')
    }
  }

  // 点击外部关闭（使用现有 hook）
  const clickOutsideSelectors = useMemo(() => [
    '.ai-rewrite-input',
    '.ai-rewrite-options',
    `[data-id="${block?.id}"]`,
  ], [block?.id])

  useClickOutsideSelectors(clickOutsideSelectors, onClose, !!block?.id)

  // 是否因为次数用完而禁用
  const isDisabledByRounds = remainingRewriteRounds === 0

  return (
    <>
      {/* Input 渲染在块下方 */}
      {createPortal(
        <div
          className="ai-rewrite-panel absolute z-50"
          style={{
            top: inputPosition.top,
            left: inputPosition.left,
            width: inputPosition.width,
          }}
        >
          <AIRewriteInput
            ref={inputRef}
            input={input}
            onInputChange={setInput}
            onSend={handleSend}
            canSend={(!!selectedAction || !!input.trim()) && (remainingRewriteRounds === undefined || remainingRewriteRounds > 0)}
            disabledHint={isDisabledByRounds ? t('apps.report.rewriteRoundsExhausted') : undefined}
          />
        </div>,
        document.body
      )}

      {/* Options 基于 Input 位置定位 */}
      <AIRewriteOptions
        selectedAction={selectedAction}
        selectedScope={selectedScope}
        onSelect={handleSelectAction}
        onScopeSelect={handleScopeSelect}
        targetElement={inputRef.current}
      />
    </>
  )
}
