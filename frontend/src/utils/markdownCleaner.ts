/**
 * Markdown cleaning and projection helpers for the report editor.
 *
 * Normal flow:
 * raw markdown -> mdast cleanup -> cleaned markdown + cleaned/raw offset map
 * cleaned markdown -> hast projection -> visible text + visible/raw offset map
 *
 * The backend still expects offsets in the raw markdown, while BlockNote renders
 * cleaned markdown and the user selects visible text. This module keeps those
 * layers aligned through AST-based transforms instead of regex/string heuristics.
 */

import type { Element as HastElement, Root as HastRoot, Text as HastText } from 'hast'
import type { Link as MdastLink, Parent as MdastParent, Root as MdastRoot } from 'mdast'
import rehypeRaw from 'rehype-raw'
import remarkCjkFriendly from 'remark-cjk-friendly'
import remarkCjkFriendlyGfmStrikethrough from 'remark-cjk-friendly-gfm-strikethrough'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import remarkParse from 'remark-parse'
import remarkRehype from 'remark-rehype'
import { unified } from 'unified'
import type { Node as UnistNode, Parent as UnistParent } from 'unist'
import { remarkDemoteFalsePositiveInlineMath } from './remarkDemoteFalsePositiveInlineMath'

export interface PreprocessResult {
  cleaned: string
  offsetMap: number[]
  blockOffsets: BlockOffset[]
}

export interface BlockOffset {
  cleanedStart: number
  cleanedEnd: number
  originalStart: number
  originalEnd: number
}

export interface VisibleProjectionResult {
  visibleText: string
  visibleToOriginalMap: number[]
}

export interface MarkdownProjectionResult extends PreprocessResult, VisibleProjectionResult {
  raw: string
}

type SourceRange = {
  start: number
  end: number
}

type ReplacementSegment = {
  start: number
  end: number
  replacement: string
  replacementToOriginalMap: number[]
}

type VisibleProjectionState = {
  textParts: string[]
  visibleToOriginalMap: number[]
}

type VisibleProjectionOptions = {
  parentTagName?: string
  preserveWhitespace?: boolean
}

const createBaseMarkdownProcessor = () =>
  unified()
    .use(remarkParse)
    // singleTilde: false — a lone `~` (e.g. "30~40%") must not be parsed as a
    // strikethrough delimiter; only `~~text~~` should be.
    .use(remarkGfm, { singleTilde: false })
    .use(remarkCjkFriendly)
    .use(remarkCjkFriendlyGfmStrikethrough, { singleTilde: false })
    // singleDollarTextMath: true so `$x=1$`-style inline math renders (matching
    // VS Code/Pandoc). remarkDemoteFalsePositiveInlineMath then demotes spans
    // like "price from $30 to $40" back to text — same anti-currency rule
    // VS Code's KaTeX preview uses.
    .use(remarkMath, { singleDollarTextMath: true })
    .use(remarkDemoteFalsePositiveInlineMath)

const markdownAstProcessor = createBaseMarkdownProcessor()

const visibleProjectionProcessor = createBaseMarkdownProcessor()
  .use(remarkRehype, { allowDangerousHtml: true })
  .use(rehypeRaw)

const INVISIBLE_WHITESPACE_PARENT_TAGS = new Set([
  'root',
  'ul',
  'ol',
  'blockquote',
  'table',
  'thead',
  'tbody',
  'tfoot',
  'tr',
])

const TABLE_CELL_TAGS = new Set(['td', 'th'])

const isTextNode = (node: UnistNode): node is HastText => node.type === 'text'

const isElementNode = (node: UnistNode): node is HastElement => node.type === 'element'

const hasChildren = (node: UnistNode): node is UnistParent =>
  Array.isArray((node as UnistParent).children)

const isMdastParent = (node: UnistNode): node is MdastParent =>
  Array.isArray((node as MdastParent).children)

const isMdastLink = (node: UnistNode): node is MdastLink => node.type === 'link'

const getSourceRange = (node: UnistNode | null | undefined): SourceRange | null => {
  const start = node?.position?.start?.offset
  const end = node?.position?.end?.offset

  if (typeof start !== 'number' || typeof end !== 'number' || end <= start) {
    return null
  }

  return { start, end }
}

const collectIdentitySlice = (
  source: string,
  start: number,
  end: number,
  textParts: string[],
  offsetMap: number[]
) => {
  for (let index = start; index < end; index++) {
    textParts.push(source[index])
    offsetMap.push(index)
  }
}

const getNodeChildrenRange = (node: MdastParent): SourceRange | null => {
  const firstChild = node.children[0]
  const lastChild = node.children[node.children.length - 1]
  const firstRange = getSourceRange(firstChild)
  const lastRange = getSourceRange(lastChild)

  if (!firstRange || !lastRange || lastRange.end <= firstRange.start) {
    return null
  }

  return {
    start: firstRange.start,
    end: lastRange.end,
  }
}

const isCitationLink = (node: MdastLink) =>
  node.url != null &&
  node.children.length === 1 &&
  node.children[0]?.type === 'text' &&
  /^\[\d+\]$/.test((node.children[0] as HastText).value)

const isInferenceLink = (node: MdastLink) => /^#inference:\d+$/.test(node.url ?? '')

const buildReplacementSegment = (
  source: string,
  node: MdastLink
): ReplacementSegment | null => {
  const nodeRange = getSourceRange(node)
  if (!nodeRange) {
    return null
  }

  if (isCitationLink(node)) {
    return {
      start: nodeRange.start,
      end: nodeRange.end,
      replacement: '',
      replacementToOriginalMap: [],
    }
  }

  if (!isInferenceLink(node)) {
    return null
  }

  const labelRange = getNodeChildrenRange(node)
  if (!labelRange) {
    return {
      start: nodeRange.start,
      end: nodeRange.end,
      replacement: '',
      replacementToOriginalMap: [],
    }
  }

  const replacement = source.slice(labelRange.start, labelRange.end)
  const replacementToOriginalMap: number[] = []
  const isSingleChar = replacement.length === 1

  for (let index = 0; index < replacement.length; index++) {
    if (index === 0) {
      replacementToOriginalMap.push(nodeRange.start)
    } else if (index === replacement.length - 1 && !isSingleChar) {
      replacementToOriginalMap.push(nodeRange.end - 1)
    } else {
      replacementToOriginalMap.push(labelRange.start + index)
    }
  }

  return {
    start: nodeRange.start,
    end: nodeRange.end,
    replacement,
    replacementToOriginalMap,
  }
}

const collectReplacementSegments = (
  node: UnistNode,
  source: string,
  segments: ReplacementSegment[]
) => {
  if (isMdastLink(node)) {
    const segment = buildReplacementSegment(source, node)
    if (segment) {
      segments.push(segment)
      return
    }
  }

  if (!isMdastParent(node)) {
    return
  }

  for (const child of node.children) {
    collectReplacementSegments(child, source, segments)
  }
}

const buildCleanedMarkdown = (
  source: string,
  segments: ReplacementSegment[]
) => {
  const cleanedParts: string[] = []
  const offsetMap: number[] = []
  let cursor = 0

  for (const segment of segments.sort((left, right) => left.start - right.start)) {
    if (segment.start < cursor) {
      continue
    }

    collectIdentitySlice(source, cursor, segment.start, cleanedParts, offsetMap)
    cleanedParts.push(segment.replacement)
    offsetMap.push(...segment.replacementToOriginalMap)
    cursor = segment.end
  }

  collectIdentitySlice(source, cursor, source.length, cleanedParts, offsetMap)

  return {
    cleaned: cleanedParts.join(''),
    offsetMap,
  }
}

function computeBlockOffsets(cleaned: string, offsetMap: number[]): BlockOffset[] {
  const blockOffsets: BlockOffset[] = []
  const lines = cleaned.split('\n')
  let currentPos = 0
  let blockStart = 0
  let inBlock = false

  for (const line of lines) {
    if (line.trim().length > 0) {
      if (!inBlock) {
        blockStart = currentPos
        inBlock = true
      }
    } else if (inBlock) {
      const blockEnd = currentPos
      if (blockEnd > blockStart) {
        blockOffsets.push({
          cleanedStart: blockStart,
          cleanedEnd: blockEnd,
          originalStart: offsetMap[blockStart] ?? blockStart,
          originalEnd: (offsetMap[blockEnd - 1] ?? (blockEnd - 1)) + 1,
        })
      }
      inBlock = false
    }

    currentPos += line.length + 1
  }

  if (inBlock && blockStart < cleaned.length) {
    blockOffsets.push({
      cleanedStart: blockStart,
      cleanedEnd: cleaned.length,
      originalStart: offsetMap[blockStart] ?? blockStart,
      originalEnd: (offsetMap[cleaned.length - 1] ?? (cleaned.length - 1)) + 1,
    })
  }

  return blockOffsets
}

const preprocessMarkdownAst = (markdown: string): PreprocessResult => {
  try {
    const mdast = markdownAstProcessor.runSync(markdownAstProcessor.parse(markdown)) as MdastRoot
    const replacementSegments: ReplacementSegment[] = []

    collectReplacementSegments(mdast, markdown, replacementSegments)

    const { cleaned, offsetMap } = buildCleanedMarkdown(markdown, replacementSegments)

    return {
      cleaned,
      offsetMap,
      blockOffsets: computeBlockOffsets(cleaned, offsetMap),
    }
  } catch (error) {
    console.warn('[markdownCleaner] Failed to preprocess markdown via AST, falling back to identity map', error)

    const offsetMap = Array.from({ length: markdown.length }, (_, index) => index)

    return {
      cleaned: markdown,
      offsetMap,
      blockOffsets: computeBlockOffsets(markdown, offsetMap),
    }
  }
}

export function mapCleanedOffsetToOriginal(
  cleanedStart: number,
  cleanedEnd: number,
  offsetMap: number[]
): { originalStart: number; originalEnd: number } {
  if (offsetMap.length === 0) {
    return { originalStart: cleanedStart, originalEnd: cleanedEnd }
  }

  const originalStart = offsetMap[cleanedStart] ?? cleanedStart
  if (cleanedEnd <= cleanedStart) {
    return { originalStart, originalEnd: originalStart }
  }

  const lastCharIndex = cleanedEnd - 1
  const originalLastCharIndex = offsetMap[lastCharIndex] ?? lastCharIndex

  return {
    originalStart,
    originalEnd: originalLastCharIndex + 1,
  }
}

export function findTextPositionInCleaned(
  selectedText: string,
  cleanedContent: string
): { start: number; end: number } | null {
  const index = cleanedContent.indexOf(selectedText)
  if (index === -1) {
    return null
  }

  return {
    start: index,
    end: index + selectedText.length,
  }
}

export function getOriginalTextFromCleaned(
  cleanedStart: number,
  cleanedEnd: number,
  rawContent: string,
  offsetMap: number[]
): string {
  const { originalStart, originalEnd } = mapCleanedOffsetToOriginal(
    cleanedStart,
    cleanedEnd,
    offsetMap
  )

  return rawContent.slice(originalStart, originalEnd)
}

const pushVisibleChar = (
  ch: string,
  cleanedIndex: number,
  state: VisibleProjectionState,
  cleanedToOriginalMap: number[]
) => {
  state.textParts.push(ch)
  state.visibleToOriginalMap.push(cleanedToOriginalMap[cleanedIndex] ?? cleanedIndex)
}

const locateValueStartInRange = (
  source: string,
  range: SourceRange,
  value: string
) => {
  if (!value) {
    return range.start
  }

  const rangeContent = source.slice(range.start, range.end)
  const relativeIndex = rangeContent.indexOf(value)

  return relativeIndex === -1 ? range.start : range.start + relativeIndex
}

const appendPreservedValue = (
  value: string,
  range: SourceRange,
  source: string,
  state: VisibleProjectionState,
  cleanedToOriginalMap: number[]
) => {
  if (!value) {
    return
  }

  const valueStart = locateValueStartInRange(source, range, value)
  const maxIndex = Math.max(range.start, range.end - 1)

  for (let i = 0; i < value.length; i++) {
    const cleanedIndex = Math.min(valueStart + i, maxIndex)
    pushVisibleChar(value[i], cleanedIndex, state, cleanedToOriginalMap)
  }
}

const appendCollapsedValue = (
  value: string,
  range: SourceRange,
  state: VisibleProjectionState,
  cleanedToOriginalMap: number[]
) => {
  let whitespaceStart: number | null = null
  const maxIndex = Math.max(range.start, range.end - 1)

  for (let i = 0; i < value.length; i++) {
    const cleanedIndex = Math.min(range.start + i, maxIndex)
    const ch = value[i]

    if (/\s/.test(ch)) {
      if (whitespaceStart === null) {
        whitespaceStart = cleanedIndex
      }
      continue
    }

    if (whitespaceStart !== null) {
      pushVisibleChar(' ', whitespaceStart, state, cleanedToOriginalMap)
      whitespaceStart = null
    }

    pushVisibleChar(ch, cleanedIndex, state, cleanedToOriginalMap)
  }

  if (whitespaceStart !== null) {
    pushVisibleChar(' ', whitespaceStart, state, cleanedToOriginalMap)
  }
}

const appendNewline = (
  range: SourceRange,
  source: string,
  state: VisibleProjectionState,
  cleanedToOriginalMap: number[]
) => {
  const gap = source.slice(range.start, range.end)

  for (let i = 0; i < gap.length; i++) {
    if (gap[i] === '\n') {
      pushVisibleChar('\n', range.start + i, state, cleanedToOriginalMap)
      return
    }
  }

  pushVisibleChar('\n', Math.max(range.start, range.end - 1), state, cleanedToOriginalMap)
}

const appendSiblingGap = (
  previousNode: UnistNode | null,
  nextNode: UnistNode,
  source: string,
  state: VisibleProjectionState,
  cleanedToOriginalMap: number[]
) => {
  const previousRange = getSourceRange(previousNode)
  const nextRange = getSourceRange(nextNode)
  const previousIsTableCell =
    previousNode !== null && isElementNode(previousNode) && TABLE_CELL_TAGS.has(previousNode.tagName)

  if (!previousRange || !nextRange || nextRange.start < previousRange.end) {
    return
  }

  if (previousIsTableCell && nextRange.start === previousRange.end) {
    pushVisibleChar('\t', previousRange.end - 1, state, cleanedToOriginalMap)
    return
  }

  const gapRange = {
    start: previousRange.end,
    end: nextRange.start,
  }
  const gap = source.slice(gapRange.start, gapRange.end)

  if (gap.includes('\n')) {
    appendNewline(gapRange, source, state, cleanedToOriginalMap)
    return
  }

  if (previousIsTableCell) {
    pushVisibleChar('\t', Math.max(gapRange.start, gapRange.end - 1), state, cleanedToOriginalMap)
  }
}

const projectVisibleNode = (
  node: UnistNode,
  source: string,
  state: VisibleProjectionState,
  cleanedToOriginalMap: number[],
  options: VisibleProjectionOptions = {},
  fallbackRange?: SourceRange
) => {
  if (isTextNode(node)) {
    const range = getSourceRange(node) ?? fallbackRange
    if (!range) {
      return
    }

    if (options.preserveWhitespace) {
      appendPreservedValue(node.value, range, source, state, cleanedToOriginalMap)
      return
    }

    if (!node.value.trim() && options.parentTagName && INVISIBLE_WHITESPACE_PARENT_TAGS.has(options.parentTagName)) {
      return
    }

    appendCollapsedValue(node.value, range, state, cleanedToOriginalMap)
    return
  }

  if (isElementNode(node)) {
    if (['script', 'style', 'input', 'img', 'hr'].includes(node.tagName)) {
      return
    }

    if (node.tagName === 'br') {
      const range = getSourceRange(node) ?? fallbackRange
      if (range) {
        appendNewline(range, source, state, cleanedToOriginalMap)
      }
      return
    }

    const preserveWhitespace = options.preserveWhitespace || node.tagName === 'pre' || node.tagName === 'code'
    const childFallbackRange =
      node.tagName === 'pre' || node.tagName === 'code'
        ? getSourceRange(node) ?? fallbackRange
        : undefined

    projectVisibleChildren(
      node.children,
      source,
      state,
      cleanedToOriginalMap,
      {
        parentTagName: node.tagName,
        preserveWhitespace,
      },
      childFallbackRange
    )
    return
  }

  if (hasChildren(node)) {
    projectVisibleChildren(node.children, source, state, cleanedToOriginalMap, options, fallbackRange)
  }
}

const projectVisibleChildren = (
  children: UnistNode[],
  source: string,
  state: VisibleProjectionState,
  cleanedToOriginalMap: number[],
  options: VisibleProjectionOptions = {},
  childFallbackRange?: SourceRange
) => {
  let previousPositionedNode: UnistNode | null = null

  for (const child of children) {
    if (getSourceRange(child)) {
      appendSiblingGap(previousPositionedNode, child, source, state, cleanedToOriginalMap)
    }

    projectVisibleNode(child, source, state, cleanedToOriginalMap, options, childFallbackRange)

    if (getSourceRange(child)) {
      previousPositionedNode = child
    }
  }
}

export function buildVisibleProjection(
  cleanedContent: string,
  offsetMap: number[]
): VisibleProjectionResult {
  try {
    const hastTree = visibleProjectionProcessor.runSync(
      visibleProjectionProcessor.parse(cleanedContent)
    ) as HastRoot
    const state: VisibleProjectionState = {
      textParts: [],
      visibleToOriginalMap: [],
    }

    projectVisibleChildren(hastTree.children, cleanedContent, state, offsetMap, {
      parentTagName: 'root',
    })

    return {
      visibleText: state.textParts.join(''),
      visibleToOriginalMap: state.visibleToOriginalMap,
    }
  } catch (error) {
    console.warn('[markdownCleaner] Failed to build visible projection via AST, falling back to cleaned text', error)

    return {
      visibleText: cleanedContent,
      visibleToOriginalMap: offsetMap.slice(0, cleanedContent.length),
    }
  }
}

export function projectMarkdown(markdown: string): MarkdownProjectionResult {
  const preprocessResult = preprocessMarkdownAst(markdown)
  const visibleProjection = buildVisibleProjection(preprocessResult.cleaned, preprocessResult.offsetMap)

  return {
    raw: markdown,
    cleaned: preprocessResult.cleaned,
    offsetMap: preprocessResult.offsetMap,
    blockOffsets: preprocessResult.blockOffsets,
    visibleText: visibleProjection.visibleText,
    visibleToOriginalMap: visibleProjection.visibleToOriginalMap,
  }
}
