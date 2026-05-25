/**
 * ReportPanel 共享常量
 *
 * @description
 * 集中管理报告面板相关的常量定义
 */

import type { ReportRewriteAction } from '@/pages/Apps/types'

// ============================================================================
// Block 高亮样式
// ============================================================================

/** 高亮样式元素 ID */
export const HIGHLIGHT_STYLE_ID = 'ai-block-highlight-style'

/** 高亮 CSS 规则 */
export const HIGHLIGHT_CSS = `
  background-color: rgba(59, 130, 246, 0.08) !important;
  border-radius: 6px !important;
  outline: 2px solid rgba(59, 130, 246, 0.4) !important;
  outline-offset: -2px;
  transition: all 0.2s ease;
`

// ============================================================================
// AI 改写动作配置
// ============================================================================

/** 改写动作配置 */
export const REWRITE_ACTIONS: {
  action: ReportRewriteAction
  icon: string
  labelKey: string
  defaultLabel: string
  hasSubMenu?: boolean
}[] = [
  { action: 'polish', icon: 'Sparkles', labelKey: 'apps.report.aiPolish', defaultLabel: '润色', hasSubMenu: false },
  { action: 'expand', icon: 'Expand', labelKey: 'apps.report.aiExpand', defaultLabel: '扩写', hasSubMenu: false },
  { action: 'shorten', icon: 'Shrink', labelKey: 'apps.report.aiShrink', defaultLabel: '缩写', hasSubMenu: false },
  { action: 'supplementary_search', icon: 'Search', labelKey: 'apps.report.aiSupplementarySearch', defaultLabel: '补充搜索', hasSubMenu: true },
  // new_task 不需要子菜单：范围由用户在输入框中自由描述，无需 selected_only / selected_and_related 预设
  { action: 'new_task', icon: 'ListPlus', labelKey: 'apps.report.aiNewTask', defaultLabel: '新增任务', hasSubMenu: false },
]

/** 补充搜索子菜单配置 */
export const SUPPLEMENTARY_SEARCH_OPTIONS = {
  selected_only: {
    labelKey: 'apps.report.supplementarySearch.selectedOnly',
    defaultLabel: '仅改选中',
  },
  selected_and_related: {
    labelKey: 'apps.report.supplementarySearch.selectedAndRelated',
    defaultLabel: '智能联改',
  },
} as const

// ============================================================================
// 面板尺寸
// ============================================================================

/** 输入栏高度 */
export const INPUT_BAR_HEIGHT = 60

/** 选项区域高度 */
export const OPTIONS_HEIGHT = 160

/** 选项面板与目标元素的间距 */
export const OPTIONS_OFFSET = 4

/** 面板总高度 */
export const PANEL_TOTAL_HEIGHT = OPTIONS_HEIGHT + INPUT_BAR_HEIGHT

// ============================================================================
// 加载状态
// ============================================================================

/** 加载状态延迟时间 (ms) */
export const LOADING_DELAY = 200

/** 加载超时时间 (ms) */
export const LOADING_TIMEOUT = 3000
