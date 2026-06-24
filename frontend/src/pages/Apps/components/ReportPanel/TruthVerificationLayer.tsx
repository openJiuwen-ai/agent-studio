/**
 * 真实性核验批注图层
 *
 * 在报告右侧空白处渲染批注图钉，点击展开核验结论并高亮原文。
 * - 编辑态：block 级蓝色高亮（复用现有 <style> 注入机制）
 * - 浏览态：CSS Custom Highlight API 文字级蓝色高亮
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { ShieldCheck, X } from 'lucide-react'
import type { TruthVerificationEntry } from '@/pages/Apps/types'
import { ReportMarkdown } from '@/pages/Apps/components/Markdown'

// ─── CSS Highlight API helpers ──────────────────────────────────────────────

const TV_CSS_STYLE_ID = 'tv-css-highlight-style'
const TV_BLOCK_STYLE_ID = 'tv-block-highlight-style'
const TV_HIGHLIGHT_NAME = 'tv-active'

const _css = CSS as unknown as { highlights?: Map<string, unknown> }
const _Highlight = (globalThis as unknown as { Highlight?: new (...r: Range[]) => unknown }).Highlight
const SUPPORTS_HL = !!_css.highlights && !!_Highlight

// ─── DOM helpers ─────────────────────────────────────────────────────────────

/**
 * 剥除行内 Markdown 语法标记，返回可见纯文本
 * 处理：**bold**, __bold__, *italic*, _italic_, ~~strike~~, `code`
 * 对于历史数据（使用旧代码保存的 selected_text 可能含有原始 Markdown），
 * 用此函数预处理后再搜索 DOM 渲染出的纯文本。
 */
function stripInlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    .replace(/~~(.+?)~~/g, '$1')
    .replace(/`(.+?)`/g, '$1')
}

/**
 * 剥除 [checked_citation:N] 字面标记
 *
 * 浏览态将原始内容中的 [checked_citation:N][[N]](url) 统一 normalize 为
 * [[N]](url "checked_citation:N")，使 "[checked_citation:N]" 字面文本
 * 在浏览态 DOM 中消失。但编辑态（BlockNote）直接渲染 rawContent，该文本
 * 以字面方式出现。若 selected_text 跨越了引用标记，搜索前需剥除这部分。
 */
function stripCheckedCitationMarkers(text: string): string {
  return text.replace(/\[checked_citation:\d+\]/g, '')
}

/**
 * 在 total 中搜索 text，允许 text 内的空白与 total 中零或多个空白匹配。
 * 用于兼容 remark-cjk-friendly 的行为：CJK 字符间的 Markdown 软换行不插入空格，
 * 而 BlockNote 等编辑器在同样位置保留空格，导致 selected_text 与 DOM 文本不一致。
 */
function findWithFlexibleWhitespace(
  total: string,
  text: string,
): { start: number; end: number } | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  const parts = trimmed.split(/\s+/).filter(Boolean)
  if (parts.length === 0) return null
  if (parts.length === 1) {
    const idx = total.indexOf(parts[0])
    if (idx < 0) return null
    return { start: idx, end: idx + parts[0].length }
  }
  const escaped = parts.map(p => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  try {
    const re = new RegExp(escaped.join('\\s*'))
    const match = re.exec(total)
    if (!match) return null
    return { start: match.index, end: match.index + match[0].length }
  } catch {
    return null
  }
}

/** 在容器内按 text 内容定位第一个匹配的 Range */
function findTextRange(container: HTMLElement, text: string): Range | null {
  if (!text) return null
  // 候选搜索文本：原始 text、剥除行内 Markdown、剥除引用标记、组合剥除
  // 引用标记差异：编辑态渲染 rawContent 含字面 [checked_citation:N]，
  // 浏览态已 normalize 掉该文本，需额外尝试剥除后的候选
  const stripped = stripInlineMarkdown(text)
  const noCitation = stripCheckedCitationMarkers(text)
  const noCitationStripped = stripCheckedCitationMarkers(stripped)
  const candidates = [text, stripped, noCitation, noCitationStripped]
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i)
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT)
  const nodes: Array<{ node: Text; offset: number }> = []
  let total = ''
  while (walker.nextNode()) {
    const n = walker.currentNode as Text
    nodes.push({ node: n, offset: total.length })
    total += n.textContent ?? ''
  }

  let start = -1
  let end = -1

  // Pass 1: 精确 indexOf
  for (const candidate of candidates) {
    const idx = total.indexOf(candidate)
    if (idx >= 0) { start = idx; end = idx + candidate.length; break }
  }

  // Pass 2: 弹性空白匹配（处理 remark-cjk-friendly 软换行差异）
  if (start < 0) {
    for (const candidate of candidates) {
      const result = findWithFlexibleWhitespace(total, candidate)
      if (result) { start = result.start; end = result.end; break }
    }
  }

  if (start < 0) return null

  // 从后往前找首个 offset <= start 的节点
  let sNode: (typeof nodes)[0] | undefined
  let eNode: (typeof nodes)[0] | undefined
  for (let i = nodes.length - 1; i >= 0; i--) {
    if (!eNode && nodes[i].offset < end) eNode = nodes[i]
    if (!sNode && nodes[i].offset <= start) { sNode = nodes[i]; break }
  }
  if (!sNode || !eNode) return null
  try {
    const range = document.createRange()
    range.setStart(sNode.node, start - sNode.offset)
    range.setEnd(eNode.node, end - eNode.offset)
    return range
  } catch {
    return null
  }
}

/** 查找包含目标文字的 BlockNote blockOuter 的 data-id */
function findBlockId(container: HTMLElement, text: string): string | null {
  const candidates = [text, stripInlineMarkdown(text)].filter(Boolean)
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT)
  const nodes: Array<{ node: Text; offset: number }> = []
  let total = ''
  while (walker.nextNode()) {
    const n = walker.currentNode as Text
    nodes.push({ node: n, offset: total.length })
    total += n.textContent ?? ''
  }
  let start = -1
  for (const candidate of candidates) {
    const idx = total.indexOf(candidate)
    if (idx >= 0) { start = idx; break }
  }
  if (start < 0) return null
  let sNode: (typeof nodes)[0] | undefined
  for (let i = nodes.length - 1; i >= 0; i--) {
    if (nodes[i].offset <= start) { sNode = nodes[i]; break }
  }
  if (!sNode) return null
  let el: Element | null = sNode.node.parentElement
  while (el && el !== container) {
    if (el.getAttribute('data-node-type') === 'blockOuter') return el.getAttribute('data-id')
    el = el.parentElement
  }
  return null
}

// ─── AnnotationPin ────────────────────────────────────────────────────────────

interface AnnotationPinProps {
  top: number
  entry: TruthVerificationEntry
  active: boolean
  onToggle: () => void
}

const AnnotationPin: React.FC<AnnotationPinProps> = ({ top, entry, active, onToggle }) => {
  const { t } = useTranslation()
  return (
    <div
      className="absolute pointer-events-auto select-none"
      style={{ top: Math.max(0, top), right: 4, zIndex: active ? 60 : 50 }}
    >
      {/* 图钉按钮 */}
      <button
        type="button"
        className={`w-7 h-7 rounded-full flex items-center justify-center border-2 transition-all duration-150 shadow-sm cursor-pointer ${
          active
            ? 'bg-amber-400 border-amber-500 text-white shadow-sm shadow-amber-100'
            : 'bg-white border-amber-300 text-amber-400 hover:bg-amber-50 hover:border-amber-400 hover:scale-110'
        }`}
        onClick={e => { e.stopPropagation(); onToggle() }}
        title={active ? undefined : entry.selected_text.slice(0, 60)}
      >
        <ShieldCheck size={14} strokeWidth={2.5} />
      </button>

      {/* 展开卡片 */}
      {active && (
        <div
          className="absolute top-0 bg-white rounded-lg shadow-xl border border-amber-200/70 overflow-hidden"
          style={{ right: 32, width: 380, zIndex: 100 }}
          onClick={e => e.stopPropagation()}
        >
          {/* 标题栏 */}
          <div className="flex items-center gap-2 px-3 py-2 bg-amber-50/80 border-b border-amber-100/80">
            <ShieldCheck size={13} className="text-amber-500 shrink-0" />
            <span className="text-xs font-semibold text-amber-700 flex-1 truncate">
              {t('apps.report.aiTruthVerification', '真实性核验')}
            </span>
            <button
              type="button"
              className="text-amber-300 hover:text-amber-500 transition-colors shrink-0 leading-none"
              onClick={e => { e.stopPropagation(); onToggle() }}
            >
              <X size={13} />
            </button>
          </div>

          {/* 选中原文预览 */}
          <div className="px-3 py-2 bg-amber-50/40 border-b border-amber-100/60">
            <p className="text-xs text-amber-700/70 italic leading-snug line-clamp-2">
              「{entry.selected_text}」
            </p>
          </div>

          {/* 核验结论（markdown 渲染） */}
          <div
            className="px-3 py-3 text-sm text-gray-700 leading-relaxed overflow-y-auto"
            style={{ maxHeight: 200 }}
          >
            <ReportMarkdown
              className="prose-sm text-sm [&_p]:my-1 [&_ul]:my-1 [&_li]:my-0.5"
              content={entry.content}
            />
          </div>

          {/* 检索证据说明（证据不足时尤其有用） */}
          {entry.evidence && (
            <div className="border-t border-amber-100/70">
              <div className="px-3 pt-2 text-[11px] font-semibold text-amber-600/80">
                {t('apps.report.truthVerificationEvidence', '检索说明')}
              </div>
              <div
                className="px-3 pb-3 pt-1 text-xs text-gray-500 leading-relaxed overflow-y-auto"
                style={{ maxHeight: 160 }}
              >
                <ReportMarkdown
                  className="prose-sm text-xs [&_p]:my-1 [&_ul]:my-1 [&_li]:my-0.5"
                  content={entry.evidence}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── TruthVerificationLayer ───────────────────────────────────────────────────

export interface TruthVerificationLayerProps {
  annotations: TruthVerificationEntry[]
  /** article 元素 ref（文字搜索目标） */
  contentRef: React.RefObject<HTMLElement>
  /** overflow-auto 滚动容器 ref（pin 定位基准） */
  scrollContainerRef: React.RefObject<HTMLDivElement>
  /** 渲染模式：影响高亮策略 */
  mode: 'view' | 'edit'
}

export const TruthVerificationLayer: React.FC<TruthVerificationLayerProps> = ({
  annotations,
  contentRef,
  scrollContainerRef,
  mode,
}) => {
  const [pinTops, setPinTops] = useState<(number | null)[]>([])
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  const blockStyleRef = useRef<HTMLStyleElement | null>(null)

  // 注入 ::highlight() CSS 规则（仅浏览态且 API 可用）
  useEffect(() => {
    if (!SUPPORTS_HL) return
    let el = document.getElementById(TV_CSS_STYLE_ID) as HTMLStyleElement | null
    if (!el) {
      el = document.createElement('style')
      el.id = TV_CSS_STYLE_ID
      document.head.appendChild(el)
    }
    el.textContent = `::highlight(${TV_HIGHLIGHT_NAME}) { background-color: rgba(245,158,11,0.18); color: inherit; }`
    return () => { document.getElementById(TV_CSS_STYLE_ID)?.remove() }
  }, [])

  // 卸载时清理所有副作用
  useEffect(() => {
    return () => {
      if (SUPPORTS_HL) _css.highlights?.delete(TV_HIGHLIGHT_NAME)
      document.getElementById(TV_BLOCK_STYLE_ID)?.remove()
    }
  }, [])

  // 激活/取消高亮
  useEffect(() => {
    // 先清
    if (SUPPORTS_HL) _css.highlights?.delete(TV_HIGHLIGHT_NAME)
    if (blockStyleRef.current) blockStyleRef.current.textContent = ''

    if (activeIndex === null || !contentRef.current) return
    const entry = annotations[activeIndex]
    if (!entry) return

    if (mode === 'edit') {
      // 编辑态：block 级高亮
      const blockId = findBlockId(contentRef.current, entry.selected_text)
      if (!blockId) return
      let el = document.getElementById(TV_BLOCK_STYLE_ID) as HTMLStyleElement | null
      if (!el) {
        el = document.createElement('style')
        el.id = TV_BLOCK_STYLE_ID
        document.head.appendChild(el)
        blockStyleRef.current = el
      }
      el.textContent = `
        [data-node-type="blockOuter"][data-id="${blockId}"] .bn-block-content {
          background: rgba(245,158,11,0.07) !important;
          border-radius: 6px !important;
          outline: 2px solid rgba(245,158,11,0.30) !important;
          outline-offset: 2px;
        }
      `
    } else {
      // 浏览态：文字级高亮（CSS Custom Highlight API）
      if (!SUPPORTS_HL) return
      const range = findTextRange(contentRef.current, entry.selected_text)
      if (!range) return
      _css.highlights!.set(TV_HIGHLIGHT_NAME, new _Highlight!(range))
    }
  }, [activeIndex, annotations, mode, contentRef])

  // 计算 pin 的垂直位置，返回是否所有 pin 都定位成功
  const calculatePositions = useCallback((): boolean => {
    const container = contentRef.current
    const scroller = scrollContainerRef.current
    if (!container || !scroller) return false

    const tops = annotations.map(ann => {
      const range = findTextRange(container, ann.selected_text)
      if (!range) return null
      const rect = range.getBoundingClientRect()
      const scrollRect = scroller.getBoundingClientRect()
      return rect.top - scrollRect.top + scroller.scrollTop
    })

    // 碰撞推开：先按文档位置（raw top）排序，再向下推开，保证推开方向与文档方向一致
    const MIN_GAP = 32
    const sortedPairs = tops
      .map((t, i) => [i, t] as [number, number | null])
      .filter((pair): pair is [number, number] => pair[1] !== null)
      .sort(([, a], [, b]) => a - b)

    const adjustedMap = new Map<number, number>()
    let prevAdj: number | null = null
    for (const [idx, raw] of sortedPairs) {
      const adj = prevAdj !== null && raw - prevAdj < MIN_GAP ? prevAdj + MIN_GAP : raw
      adjustedMap.set(idx, adj)
      prevAdj = adj
    }

    const adjusted = tops.map((t, i) => t === null ? null : (adjustedMap.get(i) ?? t))
    setPinTops(adjusted)
    return tops.every(t => t !== null)
  }, [annotations, contentRef, scrollContainerRef])

  // rAF 触发首次计算；若有 pin 未定位（内容尚未渲染），300ms 后自动重试一次
  useEffect(() => {
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    const id = requestAnimationFrame(() => {
      const allFound = calculatePositions()
      if (!allFound) {
        retryTimer = setTimeout(calculatePositions, 300)
      }
    })
    return () => {
      cancelAnimationFrame(id)
      if (retryTimer !== null) clearTimeout(retryTimer)
    }
  }, [calculatePositions])

  useEffect(() => {
    window.addEventListener('resize', calculatePositions)
    const resizeObserver = new ResizeObserver(calculatePositions)
    if (contentRef.current) resizeObserver.observe(contentRef.current)

    // MutationObserver：当内容区 DOM 结构变化时（骨架屏 → 正文）重新定位
    // 用 rAF 节流，避免编辑器初始化时大量 DOM 操作导致频繁重算
    let mutationRaf: ReturnType<typeof requestAnimationFrame> | null = null
    const onMutation: MutationCallback = () => {
      if (mutationRaf !== null) return
      mutationRaf = requestAnimationFrame(() => {
        mutationRaf = null
        calculatePositions()
      })
    }
    const mutationObserver = new MutationObserver(onMutation)
    if (contentRef.current) {
      mutationObserver.observe(contentRef.current, { childList: true, subtree: true })
    }

    return () => {
      window.removeEventListener('resize', calculatePositions)
      resizeObserver.disconnect()
      mutationObserver.disconnect()
      if (mutationRaf !== null) cancelAnimationFrame(mutationRaf)
    }
  }, [calculatePositions, contentRef])

  // 点击外部关闭
  useEffect(() => {
    if (activeIndex === null) return
    const close = () => setActiveIndex(null)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [activeIndex])

  if (!annotations.length) return null

  return (
    <div
      className="absolute top-0 right-0 bottom-0 pointer-events-none overflow-visible"
      style={{ width: 0 }}
      aria-hidden="true"
    >
      {annotations.map((ann, i) => {
        const top = pinTops[i]
        if (top == null) return null
        return (
          <AnnotationPin
            key={i}
            top={top}
            entry={ann}
            active={activeIndex === i}
            onToggle={() => setActiveIndex(prev => prev === i ? null : i)}
          />
        )
      })}
    </div>
  )
}
