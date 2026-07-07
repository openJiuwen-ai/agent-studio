import remarkGfm from 'remark-gfm'
import remarkParse from 'remark-parse'
import { unified } from 'unified'
import type {
  Blockquote,
  Code,
  Content,
  FootnoteDefinition,
  FootnoteReference,
  Heading,
  Link,
  List,
  Paragraph,
  PhrasingContent,
  Root,
  Table,
} from 'mdast'

import { projectParagraphView } from './projectParagraphView'
import { reconcileBlockIds } from './reconcileBlockIds'
import type {
  BaseInline,
  BlockSource,
  CanonicalBlock,
  CanonicalDocument,
  CanonicalInline,
  CanonicalInlineKind,
  HeadingBlock,
  InlineSource,
  ParagraphBlock,
  TableBlock,
} from './types'

// singleTilde: false — a lone `~` (e.g. Chinese approximate-range notation "30~40%")
// must not be parsed as a GFM strikethrough delimiter; only `~~text~~` should be.
const markdownProcessor = unified()
  .use(remarkParse)
  .use(remarkGfm, { singleTilde: false })

const createBlockId = (kind: string, source: BlockSource, blockIndex: number) =>
  `${kind}:${source.rawStart}:${source.rawEnd}:${blockIndex}`

type ParseInput = {
  rawMarkdown: string
  baseVersion: string
  draftRevision: number
  previous?: CanonicalDocument | null
}

type VisibleState = {
  cursor: number
}

const getBlockSource = (rawMarkdown: string, node: Content): BlockSource => {
  const rawStart = node.position?.start?.offset ?? 0
  const rawEnd = node.position?.end?.offset ?? rawStart

  return {
    rawStart,
    rawEnd,
    rawSlice: rawMarkdown.slice(rawStart, rawEnd),
  }
}

const getInlineSource = (rawMarkdown: string, node: PhrasingContent): InlineSource => {
  const rawStart = node.position?.start?.offset ?? 0
  const rawEnd = node.position?.end?.offset ?? rawStart

  return {
    rawStart,
    rawEnd,
    rawSlice: rawMarkdown.slice(rawStart, rawEnd),
  }
}

const extractInlineText = (node: PhrasingContent): string => {
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

const toInlineKind = (node: PhrasingContent): CanonicalInlineKind => {
  switch (node.type) {
    case 'strong':
      return 'strong'
    case 'emphasis':
      return 'emphasis'
    case 'delete':
      return 'delete'
    case 'inlineCode':
      return 'code'
    case 'footnoteReference':
      return 'footnoteReference'
    case 'link':
      if (/^#inference:\d+$/.test(node.url ?? '')) {
        return 'inference'
      }
      if (node.children.length === 1 && node.children[0]?.type === 'text') {
        const label = node.children[0].value
        if (/^\[\d+\]$/.test(label)) {
          return 'citation'
        }
      }
      return 'link'
    default:
      return 'text'
  }
}

const createInlineId = (blockId: string, index: number) => `${blockId}:inline:${index}`

const buildInline = (
  rawMarkdown: string,
  node: PhrasingContent,
  blockId: string,
  inlineIndex: number,
  visibleState: VisibleState,
): CanonicalInline => {
  const text = extractInlineText(node)
  const visibleStart = visibleState.cursor
  const visibleEnd = visibleStart + text.length
  visibleState.cursor = visibleEnd

  const baseInline: BaseInline = {
    id: createInlineId(blockId, inlineIndex),
    kind: toInlineKind(node),
    source: getInlineSource(rawMarkdown, node),
    visibleStart,
    visibleEnd,
    text,
  }

  if (baseInline.kind === 'link') {
    return { ...baseInline, kind: 'link', href: (node as Link).url }
  }

  if (baseInline.kind === 'inference') {
    const link = node as Link
    return {
      ...baseInline,
      kind: 'inference',
      inferenceId: link.url.replace('#inference:', ''),
    }
  }

  if (baseInline.kind === 'citation') {
    return {
      ...baseInline,
      kind: 'citation',
      href: (node as Link).url,
    }
  }

  if (baseInline.kind === 'footnoteReference') {
    const footnoteReference = node as FootnoteReference
    return {
      ...baseInline,
      kind: 'footnoteReference',
      identifier: footnoteReference.identifier,
    }
  }

  return baseInline as CanonicalInline
}

const buildParagraphBlock = (
  rawMarkdown: string,
  node: Paragraph,
  blockIndex: number,
): ParagraphBlock => {
  const source = getBlockSource(rawMarkdown, node)
  const projection = projectParagraphView(source.rawSlice)
  const blockId = createBlockId('paragraph', source, blockIndex)
  const visibleState: VisibleState = { cursor: 0 }
  const inlines = node.children.map((child, inlineIndex) =>
    buildInline(rawMarkdown, child, blockId, inlineIndex, visibleState),
  )

  return {
    id: blockId,
    kind: 'paragraph',
    source,
    editable: true,
    aiRewritable: true,
    lines: projection.lines,
    inlines,
    visibleText: projection.visibleText,
    normalizedVisibleText: projection.normalizedVisibleText,
  }
}

const buildHeadingBlock = (
  rawMarkdown: string,
  node: Heading,
  blockIndex: number,
): HeadingBlock => {
  const source = getBlockSource(rawMarkdown, node)
  const projection = projectParagraphView(source.rawSlice.replace(/^#{1,6}\s*/, ''))

  return {
    id: createBlockId('heading', source, blockIndex),
    kind: 'heading',
    source,
    editable: false,
    aiRewritable: false,
    depth: node.depth,
    visibleText: projection.visibleText,
    normalizedVisibleText: projection.normalizedVisibleText,
  }
}

const buildListBlock = (rawMarkdown: string, node: List, blockIndex: number): CanonicalBlock => {
  const source = getBlockSource(rawMarkdown, node)

  return {
    id: createBlockId('list', source, blockIndex),
    kind: 'list',
    source,
    editable: false,
    aiRewritable: false,
    ordered: Boolean(node.ordered),
  }
}

const buildBlockquoteBlock = (
  rawMarkdown: string,
  node: Blockquote,
  blockIndex: number,
): CanonicalBlock => {
  const source = getBlockSource(rawMarkdown, node)

  return {
    id: createBlockId('blockquote', source, blockIndex),
    kind: 'blockquote',
    source,
    editable: false,
    aiRewritable: false,
  }
}

const buildCodeBlock = (rawMarkdown: string, node: Code, blockIndex: number): CanonicalBlock => {
  const source = getBlockSource(rawMarkdown, node)

  return {
    id: createBlockId('code', source, blockIndex),
    kind: 'code',
    source,
    editable: false,
    aiRewritable: false,
    language: node.lang ?? undefined,
  }
}

const buildFootnoteDefinitionBlock = (
  rawMarkdown: string,
  node: FootnoteDefinition,
  blockIndex: number,
): CanonicalBlock => {
  const source = getBlockSource(rawMarkdown, node)

  return {
    id: createBlockId('footnoteDefinition', source, blockIndex),
    kind: 'footnoteDefinition',
    source,
    editable: false,
    aiRewritable: false,
    identifier: node.identifier,
  }
}

const buildTableBlock = (rawMarkdown: string, node: Table, blockIndex: number): TableBlock => {
  const source = getBlockSource(rawMarkdown, node)

  return {
    id: createBlockId('table', source, blockIndex),
    kind: 'table',
    source,
    editable: false,
    aiRewritable: false,
    columnCount: node.children[0]?.children.length ?? 0,
  }
}

const toCanonicalBlock = (
  rawMarkdown: string,
  node: Content,
  blockIndex: number,
): CanonicalBlock | null => {
  switch (node.type) {
    case 'paragraph':
      return buildParagraphBlock(rawMarkdown, node, blockIndex)
    case 'heading':
      return buildHeadingBlock(rawMarkdown, node, blockIndex)
    case 'list':
      return buildListBlock(rawMarkdown, node, blockIndex)
    case 'blockquote':
      return buildBlockquoteBlock(rawMarkdown, node, blockIndex)
    case 'code':
      return buildCodeBlock(rawMarkdown, node, blockIndex)
    case 'table':
      return buildTableBlock(rawMarkdown, node, blockIndex)
    case 'footnoteDefinition':
      return buildFootnoteDefinitionBlock(rawMarkdown, node, blockIndex)
    default:
      return null
  }
}

export function parseMarkdownToCanonical(input: ParseInput): CanonicalDocument {
  const tree = markdownProcessor.parse(input.rawMarkdown) as Root
  const nextBlocks = tree.children
    .map((node, blockIndex) => toCanonicalBlock(input.rawMarkdown, node, blockIndex))
    .filter((block): block is CanonicalBlock => block !== null)
  const blocks = input.previous
    ? reconcileBlockIds({
        previousBlocks: input.previous.blocks,
        nextBlocks,
      })
    : nextBlocks

  return {
    rawMarkdown: input.rawMarkdown,
    blocks,
    meta: {
      baseVersion: input.baseVersion,
      draftRevision: input.draftRevision,
      updatedAt: Date.now(),
    },
  }
}
