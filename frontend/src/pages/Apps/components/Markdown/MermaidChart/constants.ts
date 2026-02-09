/**
 * MermaidChart 常量定义
 */

// ==================== 颜色常量 ====================

/** 图表配色方案（12种高区分度颜色） */
export const CHART_COLORS = [
  '#3B82F6', // 蓝色 - blue
  '#10B981', // 绿色 - green
  '#F59E0B', // 橙色 - amber
  '#EF4444', // 红色 - red
  '#8B5CF6', // 紫色 - purple
  '#06B6D4', // 青色 - cyan
  '#EC4899', // 粉色 - pink
  '#84CC16', // 青柠 - lime
  '#6366F1', // 靛蓝 - indigo
  '#14B8A6', // 蓝绿 - teal
  '#F43F5E', // 玫瑰 - rose
  '#A855F7', // 深紫 - violet
] as const

// ==================== SVG 常量 ====================

/** SVG命名空间 */
export const SVG_NS = 'http://www.w3.org/2000/svg'

// ==================== 图表样式常量 ====================

/** viewBox padding配置 */
export const VIEWBOX_PADDING = {
  top: 16,
  bottom: 4,
  left: 20,
  right: 20,
} as const