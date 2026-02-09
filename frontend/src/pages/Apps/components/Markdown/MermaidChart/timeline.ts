/**
 * Mermaid timeline 图表处理器
 * 专门处理 timeline 图表的后处理
 */

import { getColor } from './utils'

// ==================== 常量定义 ====================

/** timeline 专用样式常量 */
const TIMELINE_STYLES = {
  /** 标题字体大小 */
  TITLE_FONT_SIZE: 18,
  /** 标题Y坐标 */
  TITLE_Y: 30,
} as const

// ==================== 标题处理 ====================

/**
 * 居中timeline图表标题
 */
export const centerTimelineTitle = (svgElement: SVGSVGElement): void => {
  const svgChildren = Array.from(svgElement.children)
  for (const child of svgChildren) {
    if (child.tagName === 'text' && !child.getAttribute('class')) {
      const svgWidth = svgElement.viewBox.baseVal.width
      child.setAttribute('x', String(svgWidth / 2))
      child.setAttribute('text-anchor', 'middle')
      child.setAttribute('y', String(TIMELINE_STYLES.TITLE_Y))
      child.setAttribute('font-size', String(TIMELINE_STYLES.TITLE_FONT_SIZE))
      child.setAttribute('font-weight', 'bold')
      break
    }
  }
}

// ==================== 颜色优化 ====================

/**
 * 优化timeline图表颜色
 * 将所有 timeline 相关元素统一使用 CHART_COLORS 配色方案
 */
export const optimizeTimelineColors = (svgElement: SVGSVGElement): void => {
  const styleTag = svgElement.querySelector('style')
  if (!styleTag?.textContent) return

  let cssContent = styleTag.textContent

  // 找到所有 section 的索引（-1, 0, 1, 2, ...）
  const sectionMatches = cssContent.match(/\.section-(\-\d+|\d+)/g)
  const sectionIndices = sectionMatches
    ? [...new Set(sectionMatches.map((m) => m.replace('.section-', '')))]
    : []

  // 为每个 section 替换颜色
  sectionIndices.forEach((sectionIndex, i) => {
    const color = getColor(i)

    // 替换 section 的 fill 颜色（HSL 格式）
    const fillHslRegex = new RegExp(
      `(#mermaid-[\\w-]+\\s+\\.section-${sectionIndex}[^}]*)\\{fill:hsl\\([^)]+\\)`,
      'g'
    )
    cssContent = cssContent.replace(fillHslRegex, `$1{fill:${color} !important;}`)

    // 替换 section-edge 的 stroke 颜色（HSL 格式）
    const edgeHslRegex = new RegExp(
      `(#mermaid-[\\w-]+\\s+\\.section-edge-${sectionIndex})\\{stroke:hsl\\([^)]+\\)`,
      'g'
    )
    cssContent = cssContent.replace(edgeHslRegex, `$1{stroke:${color} !important;}`)

    // 替换 section line 的 stroke 颜色（RGB 格式）
    const lineRgbRegex = new RegExp(
      `(#mermaid-[\\w-]+\\s+\\.section-${sectionIndex}\\s+line)\\{stroke:rgb\\([^)]+\\)`,
      'g'
    )
    cssContent = cssContent.replace(lineRgbRegex, `$1{stroke:${color} !important;}`)
  })

  // 更新 style 标签内容
  styleTag.textContent = cssContent
}