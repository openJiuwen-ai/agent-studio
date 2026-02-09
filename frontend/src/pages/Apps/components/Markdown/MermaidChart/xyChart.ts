/**
 * Mermaid xychart-beta 图表处理器
 * 专门处理柱状图和折线图的后处理
 */

import { SVG_NS, getColor } from './utils'

// ==================== 类型定义 ====================

/** xychart 图表类型 */
export enum XyChartType {
  BAR = 'bar',
  LINE = 'line',
}

// ==================== 常量定义 ====================

/** xychart 专用颜色 */
const XY_CHART_COLORS = {
  /** 主色（折线图、数据点） */
  PRIMARY: '#3B82F6',
  /** 边框色 */
  STROKE: '#1F2937',
  /** 白色 */
  WHITE: '#fff',
} as const

/** xychart 专用样式常量 */
const XY_CHART_STYLES = {
  /** 柱状图数据标签偏移 */
  BAR_LABEL_OFFSET: 8,
  /** 折线图数据标签偏移 */
  LINE_LABEL_OFFSET: 12,
  /** 折线图数据点圆圈半径 */
  LINE_POINT_RADIUS: 6,
  /** 折线图线条宽度 */
  LINE_STROKE_WIDTH: 4,
  /** 柱状图边框宽度 */
  BAR_STROKE_WIDTH: 1,
  /** 数据点圆圈描边宽度 */
  POINT_STROKE_WIDTH: 2,
} as const

/** xychart 专用正则表达式 */
const XY_CHART_REGEX = {
  /** 匹配 xychart-beta 数据 */
  DATA: /(bar|line)\s+\[([\d\s,.-]+)\]/,
  /** 匹配 horizontal 配置（只匹配 config 中的 horizontal: true） */
  HORIZONTAL: /horizontal\s*:\s*true/,
  /** 匹配单个 SVG 点坐标 */
  SVG_POINT: /[ML](\d+\.?\d*),(\d+\.?\d*)/,
  /** 匹配所有 SVG 点 */
  SVG_POINTS: /M(\d+\.?\d*),(\d+\.?\d*)|L(\d+\.?\d*),(\d+\.?\d*)/g,
} as const

// ==================== 工具函数 ====================

/**
 * 创建 SVG text 元素
 */
const createSvgText = (
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

// ==================== 图表处理器 ====================

/**
 * 处理柱状图
 * @param svgElement SVG 元素
 * @param values 数据值数组
 * @param isHorizontal 是否为水平柱状图
 */
const handleBarChart = (svgElement: SVGSVGElement, values: number[], isHorizontal: boolean = false): void => {
  const barPlotGroup = svgElement.querySelector('.bar-plot-0, [class*="bar-plot"]')
  if (!barPlotGroup) return

  const rects = barPlotGroup.querySelectorAll('rect')
  rects.forEach((rect, index) => {
    if (index >= values.length) return

    rect.setAttribute('fill', getColor(index))
    rect.setAttribute('stroke', XY_CHART_COLORS.STROKE)
    rect.setAttribute('stroke-width', String(XY_CHART_STYLES.BAR_STROKE_WIDTH))

    const x = parseFloat(rect.getAttribute('x') || '0')
    const y = parseFloat(rect.getAttribute('y') || '0')
    const width = parseFloat(rect.getAttribute('width') || '0')
    const height = parseFloat(rect.getAttribute('height') || '0')

    if (isHorizontal) {
      // 水平柱状图：标注在柱子右侧中间
      createSvgText(
        barPlotGroup,
        x + width + XY_CHART_STYLES.BAR_LABEL_OFFSET,
        y + height / 2,
        String(values[index]),
        { textAnchor: 'start' }
      )
    } else {
      // 垂直柱状图：标注在柱顶上方
      createSvgText(barPlotGroup, x + width / 2, y - XY_CHART_STYLES.BAR_LABEL_OFFSET, String(values[index]))
    }
  })
}

/**
 * 处理折线图
 * @param svgElement SVG 元素
 * @param values 数据值数组
 * @param isHorizontal 是否为水平折线图
 */
const handleLineChart = (svgElement: SVGSVGElement, values: number[], isHorizontal: boolean = false): void => {
  const linePlotGroup = svgElement.querySelector('.line-plot-0, [class*="line-plot"]')
  if (!linePlotGroup) return

  const path = linePlotGroup.querySelector('path')
  if (!path) return

  // 优化线条样式
  path.setAttribute('stroke-width', String(XY_CHART_STYLES.LINE_STROKE_WIDTH))
  path.setAttribute('stroke', XY_CHART_COLORS.PRIMARY)
  path.setAttribute('fill', 'none')

  const d = path.getAttribute('d')
  if (!d) return

  // 解析路径数据点
  const points = d.match(XY_CHART_REGEX.SVG_POINTS)
  if (!points) return

  points.forEach((pointStr, index) => {
    if (index >= values.length) return

    const coords = pointStr.match(XY_CHART_REGEX.SVG_POINT)
    if (!coords) return

    const cx = parseFloat(coords[1])
    const cy = parseFloat(coords[2])

    // 创建数据点圆圈
    const circle = document.createElementNS(SVG_NS, 'circle')
    circle.setAttribute('cx', String(cx))
    circle.setAttribute('cy', String(cy))
    circle.setAttribute('r', String(XY_CHART_STYLES.LINE_POINT_RADIUS))
    circle.setAttribute('fill', XY_CHART_COLORS.PRIMARY)
    circle.setAttribute('stroke', XY_CHART_COLORS.WHITE)
    circle.setAttribute('stroke-width', String(XY_CHART_STYLES.POINT_STROKE_WIDTH))
    linePlotGroup.appendChild(circle)

    if (isHorizontal) {
      // 水平折线图：标注在数据点右侧
      createSvgText(
        linePlotGroup,
        cx + XY_CHART_STYLES.LINE_LABEL_OFFSET,
        cy,
        String(values[index]),
        { textAnchor: 'start' }
      )
    } else {
      // 垂直折线图：标注在数据点上方
      createSvgText(linePlotGroup, cx, cy - XY_CHART_STYLES.LINE_LABEL_OFFSET, String(values[index]))
    }
  })
}

// ==================== 标题处理 ====================

/**
 * 居中xychart-beta标题
 */
export const centerXyTitle = (svgElement: SVGSVGElement): void => {
  const xyTitle = svgElement.querySelector('.title')
  if (xyTitle && xyTitle.tagName === 'text') {
    const svgWidth = svgElement.viewBox.baseVal.width
    xyTitle.setAttribute('text-anchor', 'middle')
    xyTitle.setAttribute('x', String(svgWidth / 2))
  }
}

// ==================== 主入口 ====================

/**
 * 处理 xychart-beta 图表
 * @param svgElement 渲染后的 SVG 元素
 * @param code mermaid 代码
 */
export const handleXyChart = (svgElement: SVGSVGElement, code: string): void => {
  const match = code.match(XY_CHART_REGEX.DATA)
  if (!match) return

  const chartType = match[1] as XyChartType
  const values = match[2].split(',').map(v => parseFloat(v.trim()))

  // 检测是否为水平图表
  const isHorizontal = XY_CHART_REGEX.HORIZONTAL.test(code)

  if (chartType === XyChartType.BAR) {
    handleBarChart(svgElement, values, isHorizontal)
  } else if (chartType === XyChartType.LINE) {
    handleLineChart(svgElement, values, isHorizontal)
  }
}