import remarkGfm from 'remark-gfm'
import remarkParse from 'remark-parse'
import { unified } from 'unified'
import type { Paragraph, Root, RootContent } from 'mdast'

import type { ParagraphLine } from './types'

// singleTilde: false — keep lone `~` (e.g. "30~40%") from being parsed as strikethrough.
const paragraphProcessor = unified()
  .use(remarkParse)
  .use(remarkGfm, { singleTilde: false })

const normalizeVisibleText = (input: string) => input.replace(/\s+/g, ' ').trim()

const extractInlineText = (node: RootContent): string => {
  switch (node.type) {
    case 'text':
      return node.value
    case 'inlineCode':
      return node.value
    case 'strong':
    case 'emphasis':
    case 'delete':
    case 'link':
      return node.children.map(extractInlineText).join('')
    case 'break':
      return '\n'
    case 'footnoteReference':
      return `[^${node.label ?? node.identifier}]`
    default:
      return ''
  }
}

const getParagraphNode = (rawSlice: string): Paragraph | null => {
  const tree = paragraphProcessor.parse(rawSlice) as Root
  return tree.children.find((node): node is Paragraph => node.type === 'paragraph') ?? null
}

const computeSoftBreakLines = (visibleText: string): ParagraphLine[] => {
  const segments = visibleText.split('\n')
  const lines: ParagraphLine[] = []
  let cursor = 0

  for (const segment of segments) {
    lines.push({
      kind: 'soft-break-line',
      visibleStart: cursor,
      visibleEnd: cursor + segment.length,
    })
    cursor += segment.length + 1
  }

  return lines
}

export function projectParagraphView(rawSlice: string): {
  visibleText: string
  normalizedVisibleText: string
  lines: ParagraphLine[]
} {
  const paragraph = getParagraphNode(rawSlice)
  const visibleText = paragraph ? paragraph.children.map(extractInlineText).join('') : rawSlice

  return {
    visibleText,
    normalizedVisibleText: normalizeVisibleText(visibleText),
    lines: computeSoftBreakLines(visibleText),
  }
}
