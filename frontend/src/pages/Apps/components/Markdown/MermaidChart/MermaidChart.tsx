/**
 * Mermaid 图表组件
 * 支持多种图表类型，优化颜色和布局
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import DOMPurify from 'dompurify'
import mermaid from 'mermaid'
import type { MermaidCodeBlockProps } from '../types'
import { initMermaid, adjustViewBox } from './utils'
import { centerTimelineTitle, optimizeTimelineColors } from './timeline'
import { centerXyTitle, handleXyChart } from './xyChart'

// ==================== 子组件 ====================

/**
 * 图表错误显示组件
 */
const ChartError: React.FC<{
  title: string
  message: string
  code: string
  viewCodeLabel: string
}> = ({ title, message, code, viewCodeLabel }) => (
  <div className="border border-red-200 bg-red-50 rounded-lg p-4 my-4">
    <p className="text-sm font-medium text-red-700">{title}</p>
    <p className="text-sm text-red-600 mt-1">{message}</p>
    <details className="mt-2">
      <summary className="cursor-pointer text-xs text-red-500">{viewCodeLabel}</summary>
      <pre className="mt-2 text-xs p-2 bg-red-100 rounded overflow-auto max-h-40">
        {code}
      </pre>
    </details>
  </div>
)

// ==================== 主组件 ====================

export const MermaidChart: React.FC<MermaidCodeBlockProps> = ({ code }) => {
  const { t } = useTranslation()
  const ref = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const uniqueId = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}-${Date.now()}`)

  /**
   * 处理图表后处理（根据图表类型应用不同的优化）
   */
  const postProcessSvg = useCallback((svgElement: SVGSVGElement, chartType: string | null) => {
    // 调整viewBox避免内容截断
    adjustViewBox(svgElement)

    // 处理不同类型图表的标题
    if (chartType === 'timeline') {
      centerTimelineTitle(svgElement)
      optimizeTimelineColors(svgElement)
    } else if (chartType === 'xychart') {
      centerXyTitle(svgElement)
      handleXyChart(svgElement, code)
    }
  }, [code])

  /**
   * 验证 mermaid 语法
   */
  const validateSyntax = useCallback(async (mermaidCode: string): Promise<boolean> => {
    try {
      await mermaid.parse(mermaidCode)
      return true
    } catch (parseError) {
      const errorMessage = parseError instanceof Error ? parseError.message : String(parseError)
      console.error('[MermaidChart] Parse error:', parseError)
      console.error('[MermaidChart] Code:', mermaidCode.substring(0, 200))
      setError(`${t('apps.chart.syntaxError')}: ${errorMessage}`)
      return false
    }
  }, [t])

  /**
   * 渲染图表
   */
  const renderDiagram = useCallback(async () => {
    if (!ref.current) return

    // 清除之前的错误
    setError(null)

    // 验证语法
    const isValid = await validateSyntax(code)
    if (!isValid) return

    try {
      // 渲染 SVG
      const { svg } = await mermaid.render(uniqueId.current, code)

      if (!ref.current) return

      // 插入消毒后的 SVG，防止 XSS 攻击
      ref.current.innerHTML = DOMPurify.sanitize(svg, {
        USE_PROFILES: { svg: true, svgFilters: true },
        ADD_TAGS: ['foreignObject'],
        ADD_ATTR: [
          'transform', 'viewBox', 'preserveAspectRatio', 'x', 'y', 'width', 'height',
          'd', 'cx', 'cy', 'r', 'rx', 'ry', 'x1', 'y1', 'x2', 'y2',
          'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
          'font-size', 'font-weight', 'font-family', 'text-anchor', 'dominant-baseline',
          'class', 'id', 'aria-roledescription', 'aria-label', 'role',
        ],
        FORBID_ATTR: ['xlink:href', 'onclick', 'onload', 'onerror', 'onmouseover', 'onfocus', 'onblur'],
      })
      const svgElement = ref.current.querySelector('svg')
      if (!svgElement) return

      // 获取图表类型并应用后处理
      const chartType = svgElement.getAttribute('aria-roledescription')
      postProcessSvg(svgElement, chartType)

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      console.error('[MermaidChart] Rendering error:', err)
      console.error('[MermaidChart] Code:', code.substring(0, 200))
      setError(`${t('apps.chart.renderFailed')}: ${errorMessage}`)
    }
  }, [code, validateSyntax, postProcessSvg, t])

  // 当代码变化时重新渲染
  useEffect(() => {
    initMermaid()
    renderDiagram()
  }, [renderDiagram])

  // 错误状态
  if (error) {
    return (
      <ChartError
        title={t('apps.chart.mermaidError')}
        message={error}
        code={code}
        viewCodeLabel={t('apps.chart.viewCode')}
      />
    )
  }

  // 正常渲染
  return (
    <div
      ref={ref}
      className="flex justify-center items-center overflow-x-auto rounded-lg bg-white"
      style={{ minHeight: '100px' }}
    />
  )
}