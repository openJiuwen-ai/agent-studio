/**
 * MermaidChart 工具函数
 */

import type { MermaidCodeBlockProps } from '../types'
import { CHART_COLORS, SVG_NS, VIEWBOX_PADDING } from './constants'
import mermaid from 'mermaid'

// 重新导出常量供其他模块使用
export { CHART_COLORS, SVG_NS } from './constants'

// ==================== Mermaid 初始化管理器 ====================

/**
 * Mermaid 初始化管理器
 * 使用依赖注入模式提高可测试性
 */
class MermaidManager {
  private initialized: boolean = false

  /**
   * 初始化 mermaid（仅首次调用生效）
   */
  initialize(): void {
    if (this.initialized) return

    try {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        securityLevel: 'loose',
        logLevel: 'error',
        themeVariables: {
          // ==================== 通用颜色 ====================
          darkMode: false,
          background: '#ffffff',
          fontFamily: 'trebuchet ms, verdana, arial',
          fontSize: '16px',

          // 主色系
          primaryColor: CHART_COLORS[0],
          primaryTextColor: '#1F2937',
          primaryBorderColor: this.darkenColor(CHART_COLORS[0], 20),

          // 次色系
          secondaryColor: CHART_COLORS[1],
          secondaryTextColor: '#1F2937',
          secondaryBorderColor: this.darkenColor(CHART_COLORS[1], 20),

          // 第三色系
          tertiaryColor: CHART_COLORS[2],
          tertiaryTextColor: '#1F2937',
          tertiaryBorderColor: this.darkenColor(CHART_COLORS[2], 20),

          // 线条和文字颜色
          lineColor: CHART_COLORS[0],
          textColor: '#1F2937',

          // 节点背景
          mainBkg: CHART_COLORS[0],

          // ==================== 流程图变量 ====================
          nodeBorder: this.darkenColor(CHART_COLORS[0], 20),
          clusterBkg: CHART_COLORS[2],
          clusterBorder: this.darkenColor(CHART_COLORS[2], 20),
          defaultLinkColor: CHART_COLORS[0],
          titleColor: '#1F2937',
          edgeLabelBackground: CHART_COLORS[1],
          nodeTextColor: '#1F2937',

          // ==================== 饼图变量 ====================
          pie1: CHART_COLORS[0],   // 蓝色
          pie2: CHART_COLORS[1],   // 绿色
          pie3: CHART_COLORS[2],   // 橙色
          pie4: CHART_COLORS[3],   // 红色
          pie5: CHART_COLORS[4],   // 紫色
          pie6: CHART_COLORS[5],   // 青色
          pie7: CHART_COLORS[6],   // 粉色
          pie8: CHART_COLORS[7],   // 青柠
          pie9: CHART_COLORS[8],   // 靛蓝
          pie10: CHART_COLORS[9],  // 蓝绿
          pie11: CHART_COLORS[10], // 玫瑰
          pie12: CHART_COLORS[11], // 深紫
          pieTitleTextSize: '25px',
          pieTitleTextColor: '#1F2937',
          pieSectionTextSize: '17px',
          pieSectionTextColor: '#1F2937',
          pieLegendTextSize: '17px',
          pieLegendTextColor: '#1F2937',
          pieStrokeColor: '#ffffff',
          pieStrokeWidth: '2px',
          pieOuterStrokeWidth: '2px',
          pieOuterStrokeColor: '#ffffff',
          pieOpacity: '1',
        },
      })
      this.initialized = true
    } catch (err) {
      console.error('[MermaidChart] Initialization error:', err)
    }
  }

  /**
   * 加深颜色（用于边框颜色）
   * @param color 十六进制颜色
   * @param percent 加深百分比
   * @returns 加深后的颜色
   */
  private darkenColor(color: string, percent: number): string {
    const num = parseInt(color.replace('#', ''), 16)
    const amt = Math.round(2.55 * percent)
    const R = Math.max((num >> 16) - amt, 0)
    const G = Math.max((num >> 8 & 0x00FF) - amt, 0)
    const B = Math.max((num & 0x0000FF) - amt, 0)
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)
  }

  /**
   * 检查是否已初始化
   */
  isInitialized(): boolean {
    return this.initialized
  }

  /**
   * 重置初始化状态（仅用于测试）
   */
  reset(): void {
    this.initialized = false
  }
}

// 导出单例实例
export const mermaidManager = new MermaidManager()

// 向后兼容的导出函数
export const initMermaid = (): void => mermaidManager.initialize()

// ==================== 颜色工具 ====================

/**
 * 获取图表颜色
 * @param index 索引
 * @returns 颜色值
 */
export const getColor = (index: number): string => {
  return CHART_COLORS[index % CHART_COLORS.length]
}

// ==================== SVG 操作 ====================

/**
 * 调整SVG的viewBox增加padding
 */
export const adjustViewBox = (svgElement: SVGSVGElement): void => {
  const viewBox = svgElement.getAttribute('viewBox')
  if (!viewBox) return

  const parts = viewBox.split(' ').map(v => parseFloat(v))
  if (parts.length !== 4) return

  const [x, y, width, height] = parts
  svgElement.setAttribute(
    'viewBox',
    `${x - VIEWBOX_PADDING.left} ${y - VIEWBOX_PADDING.top} ${width + VIEWBOX_PADDING.left + VIEWBOX_PADDING.right} ${height + VIEWBOX_PADDING.top + VIEWBOX_PADDING.bottom}`
  )
}

/**
 * 创建SVG text元素
 */
export const createSvgText = (
  container: Element,
  x: number,
  y: number,
  text: string,
  options: {
    fontSize?: string
    fontWeight?: string
    fill?: string
    textAnchor?: string
  } = {}
): void => {
  const textEl = document.createElementNS(SVG_NS, 'text')
  textEl.setAttribute('x', String(x))
  textEl.setAttribute('y', String(y))
  textEl.setAttribute('text-anchor', options.textAnchor || 'middle')
  textEl.setAttribute('font-size', options.fontSize || '14px')
  textEl.setAttribute('font-weight', options.fontWeight || 'bold')
  textEl.setAttribute('fill', options.fill || '#1F2937')
  textEl.textContent = text
  container.appendChild(textEl)
}