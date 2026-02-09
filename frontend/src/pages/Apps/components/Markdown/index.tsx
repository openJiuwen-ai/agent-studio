/**
 * ReportMarkdown 组件主入口
 */

import React, { useLayoutEffect } from 'react'
import type { MarkdownProps } from './types'
import { MarkdownRenderer } from './MarkdownRenderer'
import { resetLinkIndexCounter } from '../CitationPanel/CitationLink'

/**
 * ReportMarkdown 组件
 *
 * @description
 * 专用于报告展示的增强型 Markdown 组件
 * 支持：
 * - 标准 Markdown 语法（GFM）
 * - 数学公式（LaTeX）
 * - Mermaid 图表
 * - 引用链接和提示
 * - 溯源推理图谱链接
 * - 图片懒加载和错误处理
 */
export const ReportMarkdown: React.FC<MarkdownProps> = ({
  instanceId,
  className = '',
  content,
  citations,
  inferMessages,
}) => {
  /**
   * 每次渲染前重置 linkIndex 计数器
   * 使用 useLayoutEffect 确保在渲染前同步执行
   */
  useLayoutEffect(() => {
    if (instanceId) {
      resetLinkIndexCounter(instanceId)
    }
  })

  return (
    <div
      className={`markdown-content prose max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-blue-600 ${className}`}
    >
      <MarkdownRenderer
        instanceId={instanceId}
        content={content}
        citations={citations}
        inferMessages={inferMessages}
      />
    </div>
  )
}
