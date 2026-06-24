/**
 * 报告相关工具函数
 */

import { parseMarkdownToCanonical } from '@/pages/Apps/components/ReportPanel/editor/canonical';
import type { ChartMessage, DeepSearchResult, Report } from '@/pages/Apps/types'
import { MESSAGE_TITLES } from '@/stores/useConversationStore'

const CHART_PLACEHOLDER_PATTERN = /\(#insertChart:([^)]+)\)/g
const VLM_CHART_PROTOCOL = 'vlm-chart:'
const CHECKED_CITATION_PATTERN = /\[checked_citation:(\d+)\]\[\[(\d+)\]\]\(([^)\s]+)\)/g

/**
 * 清理报告内容中的引用标记
 */
export function cleanReportContent(content: string): string {
  if (!content) return ''
  return normalizeCheckedCitationLinks(content)
}

export function normalizeCheckedCitationLinks(content: string): string {
  if (!content) return ''

  return content.replace(CHECKED_CITATION_PATTERN, (_match, citationIndex, displayIndex, url) => {
    return `[[${displayIndex}]](${url} "checked_citation:${citationIndex}")`
  })
}

/**
 * 从 Markdown 内容中提取标题
 */
export function extractTitleFromMarkdown(content: string): string {
  if (!content) return ''

  const lines = content.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('# ')) {
      return trimmed.substring(2).trim()
    }
  }
  return ''
}

/**
 * 格式化报告标题用于显示
 */
export function formatReportTitleForDisplay(
  title: string | undefined,
  t: (key: string, params?: any) => string,
  fallbackKey: string = 'apps.deepSearch.reportCard'
): string {
  if (title === MESSAGE_TITLES.FINAL_REPORT) {
    return t('apps.deepSearch.finalReport')
  }
  return title || t(fallbackKey)
}

function normalizeChartDataUrl(chart: ChartMessage): string | null {
  const trimmedBase64 = (chart.base64 || '').trim()

  if (!trimmedBase64) {
    return null
  }

  if (trimmedBase64.startsWith('data:image/')) {
    return trimmedBase64
  }

  return `data:image/png;base64,${trimmedBase64}`
}

export function createVLMChartReference(chartId: string): string {
  return `${VLM_CHART_PROTOCOL}${chartId}`
}

export function isVLMChartReference(value: string): boolean {
  return value.startsWith(VLM_CHART_PROTOCOL)
}

export function getChartIdFromReference(value: string): string {
  return value.slice(VLM_CHART_PROTOCOL.length)
}

function escapeMarkdownAltText(value: string): string {
  return value.replace(/[\[\]\r\n]/g, ' ').trim()
}

function getChartAltText(chart: ChartMessage): string {
  return escapeMarkdownAltText(
    chart.chart_title || chart.description || chart.chart_id || 'VLM chart'
  )
}

export function getChartDataUrl(chart: ChartMessage): string | null {
  return normalizeChartDataUrl(chart)
}


/**
 * 将报告中的 VLM 图表占位符替换成 Markdown 图片
 */
export function insertVLMChartsIntoReportContent(
  content: string,
  chartMessages?: ChartMessage[] | null,
  imageSrcResolver: (chart: ChartMessage) => string | null = normalizeChartDataUrl
): string {
  if (!content || !chartMessages?.length) {
    return content
  }

  const chartsById = new Map(chartMessages.map(chart => [chart.chart_id, chart]))

  return content.replace(CHART_PLACEHOLDER_PATTERN, (placeholder, chartId) => {
    const chart = chartsById.get(chartId)
    if (!chart) {
      return placeholder
    }

    const imageSrc = imageSrcResolver(chart)
    if (!imageSrc) {
      return placeholder
    }

    const altText = getChartAltText(chart)

    return `![${altText}](${imageSrc})`
  })
}

// ─── 真实性核验筛选工具 ──────────────────────────────────────────────────────

// CJK 字符范围（用于软换行处理）
const CJK_CHAR_RE = /[一-鿿㐀-䶿豈-﫿＀-￯]/

// 解码 HTML 数字实体（&#xHHHH; / &#NNN;）和常见命名实体
// Markdown 渲染器（如 remark）有时会将非 ASCII 字符转义为 HTML 实体，
// 导致 plain text 里出现 &#x81F3; 而 selected_text 里是实际字符“至”
function _decodeHtmlEntities(text: string): string {
  return text
    .replace(/&#x([0-9a-fA-F]+);/gi, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
    .replace(/&#([0-9]+);/g, (_, dec) => String.fromCodePoint(parseInt(dec, 10)))
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&nbsp;/g, ' ')
}

/**
 * 将 Markdown 源文本转换为近似纯文本，模拟浏览器 DOM TreeWalker 收集文本节点的效果。
 * TruthVerificationLayer 的 findTextRange 在 DOM 渲染后的文本节点里搜索；
 * 此函数在无 DOM 的环境下得到等价的搜索目标，需复现两个关键渲染行为：
 *   1. Markdown 格式符号（** * _ ~~）被剥除，只保留可见文字；
 *   2. remark-cjk-friendly：CJK 字符间的软换行不插入空格；非 CJK 软换行变为空格。
 */
function markdownToPlainText(markdown: string): string {
  let text = normalizeCheckedCitationLinks(markdown)

  // 围栏代码块整体移除（避免其中内容干扰正文匹配）
  text = text.replace(/```[\s\S]*?```/g, ' ')

  // 移除图片 ![alt](url)
  text = text.replace(/!\[[^\]]*\]\([^)]*\)/g, '')

  // 引用链接 [[N]](url "...") → [N]（已 normalize 的格式）
  text = text.replace(/\[(\[[^\]]*\])\]\([^)]*\)/g, '$1')

  // 普通链接 [text](url) → text
  text = text.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')

  // 加粗：** 优先，[\s\S]+? 支持跨软换行的加粗段落
  text = text.replace(/\*\*([\s\S]+?)\*\*/g, '$1')
  text = text.replace(/__([\s\S]+?)__/g, '$1')

  // 移除列表 / 引用前缀（* - + >），避免行首 * 被后续斜体正则误匹配
  text = text.replace(/^[*\-+]\s+/gm, '')
  text = text.replace(/^>\s*/gm, '')

  // 斜体：限制不跨行（[^*\n]+），防止跨段误匹配
  text = text.replace(/\*([^*\n]+)\*/g, '$1')
  text = text.replace(/_([^_\n]+)_/g, '$1')

  // 删除线
  text = text.replace(/~~([^~\n]+)~~/g, '$1')

  // 行内代码
  text = text.replace(/`([^`]+)`/g, '$1')

  // 标题前缀 # ## ...
  text = text.replace(/^#{1,6}\s+/gm, '')

  // ── 软换行处理（复现 remark-cjk-friendly）──
  // CJK-to-CJK：去掉换行，不插空格
  text = text.replace(
    new RegExp(
      `(${CJK_CHAR_RE.source})\n(${CJK_CHAR_RE.source})`,
      'g'
    ),
    '$1$2'
  )
  // 其余换行折叠为空格
  text = text.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim()

  // HTML 实体解码（&#x81F3; → 至 等），Markdown 渲染器可能输出实体而非实际字符
  text = _decodeHtmlEntities(text)

  return text
}

/**
 * 剥除 selected_text 里可能出现的 [checked_citation:N] 字面标记。
 * BlockNote 渲染 rawContent 时该模式以字面文本出现，normalize 后消失。
 */
function _tvStripCheckedCitationMarkers(text: string): string {
  return text.replace(/\[checked_citation:\d+\]/g, '')
}

/**
 * 剥除 selected_text 里可能残留的行内 Markdown 标记（兼容旧数据）。
 */
function _tvStripInlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    .replace(/~~(.+?)~~/g, '$1')
    .replace(/`(.+?)`/g, '$1')
}

/**
 * 弹性空白匹配：candidate 的各词之间允许零或多个空白（\s*），
 * 与 TruthVerificationLayer 的 findWithFlexibleWhitespace 保持一致。
 * 用于处理 Markdown 软换行转空格后的差异，以及 CJK 字符间无空格的情况。
 */
function _tvFlexibleMatch(content: string, candidate: string): boolean {
  const parts = candidate.trim().split(/\s+/).filter(Boolean)
  if (parts.length <= 1) return false
  const escaped = parts.map(p => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  try {
    return new RegExp(escaped.join('\\s*')).test(content)
  } catch {
    return false
  }
}

/**
 * 判断真实性核验条目的 selected_text 是否仍存在于新报告内容中。
 *
 * selected_text 是 BlockNote 选区的可见纯文本（无 Markdown 语法）。
 * response_content 是原始 Markdown 源码（含 ** / [] / 换行等语法）。
 * 直接对 response_content 做字符串搜索会因格式符号而失配。
 *
 * 策略：
 *   1. 将 response_content 转换为纯文本（markdownToPlainText），
 *      与 findTextRange 在 DOM 文本节点里搜索的效果等价；
 *   2. 对 selected_text 构造多个候选（原始 / 剥除 Markdown / 剥除引用标记），
 *      与 TruthVerificationLayer 的候选逻辑保持一致；
 *   3. Pass 1 精确 includes；Pass 2 弹性空白匹配。
 */
export function truthVerificationEntryExistsInContent(
  selectedText: string,
  responseContent: string
): boolean {
  if (!selectedText.trim() || !responseContent.trim()) return false

  // 候选列表（与 TruthVerificationLayer.findTextRange 保持一致）
  const stripped = _tvStripInlineMarkdown(selectedText)
  const noCitation = _tvStripCheckedCitationMarkers(selectedText)
  const noCitationStripped = _tvStripCheckedCitationMarkers(stripped)
  const candidates = [selectedText, stripped, noCitation, noCitationStripped]
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i)

  // 主搜索目标：纯文本（Markdown 语法已剥除，等价于 DOM 文本节点的拼接）
  const plainContent = markdownToPlainText(responseContent)
  // 备用目标：仅引用标记 normalize，保留 Markdown 结构（兜底）
  const normalizedContent = normalizeCheckedCitationLinks(responseContent)

  for (const candidate of candidates) {
    // Pass 1：精确匹配
    if (plainContent.includes(candidate)) return true
    if (normalizedContent.includes(candidate)) return true
    // Pass 2：弹性空白（处理软换行转空格后的差异）
    if (_tvFlexibleMatch(plainContent, candidate)) return true
    if (_tvFlexibleMatch(normalizedContent, candidate)) return true
  }
  return false
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * 从 DeepSearchResult 构造 Report 对象
 */
export function buildReportFromDeepSearch(
  messageId: string,
  messageCreatedAt: number,
  deepSearchResult: DeepSearchResult
): Report {
  const rawResponseContent = deepSearchResult.response_content || '';
  const responseContent = cleanReportContent(rawResponseContent);
  const canonicalDocument = parseMarkdownToCanonical({
    rawMarkdown: rawResponseContent,
    baseVersion: `report:${messageId}`,
    draftRevision: 0,
  });

  const extractedTitle = extractTitleFromMarkdown(responseContent)
  const title = extractedTitle || MESSAGE_TITLES.FINAL_REPORT

  return {
    id: messageId,
    title,
    createdAt: new Date(messageCreatedAt || Date.now()).toISOString(),
    content: responseContent,
    citations: deepSearchResult.citation_messages || null,
    inferMessages: deepSearchResult.infer_messages || [],
    chartMessages: deepSearchResult.chart_messages || [],
    rawContent: rawResponseContent,
    canonicalDocument,
  };
}
