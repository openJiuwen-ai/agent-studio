/**
 * Apps Page Style Constants
 * 探索页面样式常量
 */

/**
 * 字体常量 (Typography)
 * 统一页面字体大小和字体家族
 */

// 字体家族 - 统一使用系统默认字体栈
export const FONT_FAMILY = 'font-sans'

// 字体大小 - 正文内容（统一标准，16px）
export const TEXT_BASE = 'text-base'

// 字体大小 - 辅助文字、按钮文字（14px）
export const TEXT_SMALL = 'text-sm'

// 字体大小 - 小型标签、标题（12px）
export const TEXT_XS = 'text-xs'

/**
 * 圆角半径常量 (Border Radius)
 * 所有圆角值以输入文本框的 rounded-3xl (24px) 为基准
 */

// 大容器圆角 - 输入框、对话框、卡片等主要容器
export const RADIUS_CONTAINER = 'rounded-3xl'

// 按钮圆角 - 按钮组件使用稍小的圆角
export const RADIUS_BUTTON = 'rounded-xl'

// 小元素圆角 - 小型图标容器、标签等
export const RADIUS_SMALL = 'rounded-lg'

// 中等圆角 - 对话历史项等
export const RADIUS_MEDIUM = 'rounded-2xl'

// 圆形按钮/图标 - 用于圆形图标按钮
export const RADIUS_CIRCLE = 'rounded-full'

/**
 * 按钮交互效果常量 (Button Interaction Effects)
 * 统一的 hover 和 active 状态效果
 */
export const BUTTON_HOVER_EFFECTS = 'hover:bg-gray-100 active:bg-gray-200 active:scale-95'
export const BUTTON_TRANSITION = 'transition-all duration-200'

/**
 * 其他样式常量
 */

// 过渡动画时长
export const TRANSITION_DURATION = 'duration-200'

// 焦点环样式
export const FOCUS_RING = 'focus:outline-none focus:ring-2 focus:ring-blue-400'
