export type CanonicalBlockKind =
  | 'paragraph'
  | 'heading'
  | 'list'
  | 'blockquote'
  | 'code'
  | 'table'
  | 'footnoteDefinition'

export type CanonicalInlineKind =
  | 'text'
  | 'strong'
  | 'emphasis'
  | 'delete'
  | 'code'
  | 'link'
  | 'inference'
  | 'citation'
  | 'footnoteReference'

export interface BlockSource {
  rawStart: number
  rawEnd: number
  rawSlice: string
}

export interface InlineSource {
  rawStart: number
  rawEnd: number
  rawSlice: string
}

export interface ParagraphLine {
  kind: 'soft-break-line'
  visibleStart: number
  visibleEnd: number
}

export interface BaseInline {
  id: string
  kind: CanonicalInlineKind
  source: InlineSource
  visibleStart: number
  visibleEnd: number
  text: string
}

export interface TextInline extends BaseInline {
  kind: 'text'
}

export interface StrongInline extends BaseInline {
  kind: 'strong'
}

export interface EmphasisInline extends BaseInline {
  kind: 'emphasis'
}

export interface DeleteInline extends BaseInline {
  kind: 'delete'
}

export interface CodeInline extends BaseInline {
  kind: 'code'
}

export interface LinkInline extends BaseInline {
  kind: 'link'
  href: string
}

export interface InferenceInline extends BaseInline {
  kind: 'inference'
  inferenceId: string
}

export interface CitationInline extends BaseInline {
  kind: 'citation'
  href: string
}

export interface FootnoteReferenceInline extends BaseInline {
  kind: 'footnoteReference'
  identifier: string
}

export type CanonicalInline =
  | TextInline
  | StrongInline
  | EmphasisInline
  | DeleteInline
  | CodeInline
  | LinkInline
  | InferenceInline
  | CitationInline
  | FootnoteReferenceInline

export interface BaseBlock {
  id: string
  kind: CanonicalBlockKind
  source: BlockSource
  editable: boolean
  aiRewritable: boolean
}

export interface ParagraphBlock extends BaseBlock {
  kind: 'paragraph'
  lines: ParagraphLine[]
  inlines: CanonicalInline[]
  visibleText: string
  normalizedVisibleText: string
}

export interface HeadingBlock extends BaseBlock {
  kind: 'heading'
  depth: number
  visibleText: string
  normalizedVisibleText: string
}

export interface ListBlock extends BaseBlock {
  kind: 'list'
  ordered: boolean
}

export interface BlockquoteBlock extends BaseBlock {
  kind: 'blockquote'
}

export interface CodeBlock extends BaseBlock {
  kind: 'code'
  language?: string
}

export interface TableBlock extends BaseBlock {
  kind: 'table'
  columnCount: number
}

export interface FootnoteDefinitionBlock extends BaseBlock {
  kind: 'footnoteDefinition'
  identifier: string
}

export type CanonicalBlock =
  | ParagraphBlock
  | HeadingBlock
  | ListBlock
  | BlockquoteBlock
  | CodeBlock
  | TableBlock
  | FootnoteDefinitionBlock

export interface CanonicalDocument {
  rawMarkdown: string
  blocks: CanonicalBlock[]
  meta: {
    baseVersion: string
    draftRevision: number
    updatedAt: number
  }
}

export interface ReportCanonicalSeed {
  document: CanonicalDocument
}
