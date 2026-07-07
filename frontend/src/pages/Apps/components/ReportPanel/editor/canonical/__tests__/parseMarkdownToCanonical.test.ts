import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import {
  parseMarkdownToCanonical,
  projectParagraphView,
} from '../index'

const fixture = (name: string) =>
  readFileSync(new URL(`../../__fixtures__/${name}`, import.meta.url), 'utf8')

describe('reportEditor fixtures', () => {
  it('loads all phase-1 fixtures as utf8 markdown', () => {
    expect(fixture('simple-paragraph.md')).toContain('总收入达**13091亿元**')
    expect(fixture('protected-inline-paragraph.md')).toContain('(#inference:1)')
    expect(fixture('protected-inline-paragraph.md')).toContain(
      'https://xueqiu.com/S/JD/379829331',
    )
    expect(fixture('structured-report.md')).toContain('| 财务指标 | 2025年数值 |')
    expect(fixture('structured-report.md')).toContain('- **战略协同效应**')
  })
})

describe('parseMarkdownToCanonical', () => {
  it('parses paragraph, heading, list, and table blocks from real-report fixtures', () => {
    const document = parseMarkdownToCanonical({
      rawMarkdown: fixture('structured-report.md'),
      baseVersion: 'test-v1',
      draftRevision: 0,
    })

    expect(document.rawMarkdown).toContain('京东集团2025年经济状况综合评估')
    expect(document.blocks.map((block) => block.kind)).toEqual([
      'heading',
      'heading',
      'table',
      'list',
    ])
    expect(document.blocks.map((block) => block.editable)).toEqual([
      false,
      false,
      false,
      false,
    ])
    expect(document.blocks.map((block) => block.aiRewritable)).toEqual([
      false,
      false,
      false,
      false,
    ])
  })

  it('parses a protected-inline paragraph and preserves inference/citation source ranges', () => {
    const rawMarkdown = fixture('protected-inline-paragraph.md')
    const document = parseMarkdownToCanonical({
      rawMarkdown,
      baseVersion: 'test-v1',
      draftRevision: 0,
    })

    expect(document.blocks).toHaveLength(1)
    expect(document.blocks[0]?.kind).toBe('paragraph')
    expect(document.blocks[0]?.editable).toBe(true)
    expect(document.blocks[0]?.aiRewritable).toBe(true)

    const paragraph = document.blocks[0]
    if (paragraph.kind !== 'paragraph') {
      throw new Error('expected paragraph block')
    }

    const inferenceInline = paragraph.inlines.find((inline) => inline.kind === 'inference')
    const citationInline = paragraph.inlines.find((inline) => inline.kind === 'citation')

    expect(inferenceInline?.source.rawSlice).toContain('(#inference:1)')
    expect(citationInline?.source.rawSlice).toContain('https://xueqiu.com/S/JD/379829331')
  })

  it('marks only paragraph blocks editable and aiRewritable in phase 1', () => {
    const document = parseMarkdownToCanonical({
      rawMarkdown: [fixture('simple-paragraph.md'), '', fixture('structured-report.md')].join('\n\n'),
      baseVersion: 'test-v1',
      draftRevision: 0,
    })

    const paragraphBlocks = document.blocks.filter((block) => block.kind === 'paragraph')
    const nonParagraphBlocks = document.blocks.filter((block) => block.kind !== 'paragraph')

    expect(paragraphBlocks.length).toBeGreaterThan(0)
    expect(paragraphBlocks.every((block) => block.editable && block.aiRewritable)).toBe(true)
    expect(nonParagraphBlocks.every((block) => !block.editable && !block.aiRewritable)).toBe(
      true,
    )
  })

  it('keeps untouched block ids stable when content is inserted before them', () => {
    const previous = parseMarkdownToCanonical({
      rawMarkdown: '第一段\n\n第二段',
      baseVersion: 'v1',
      draftRevision: 0,
    })

    const next = parseMarkdownToCanonical({
      rawMarkdown: '新增段落\n\n第一段\n\n第二段',
      baseVersion: 'v2',
      draftRevision: 1,
      previous,
    })

    expect(previous.blocks).toHaveLength(2)
    expect(next.blocks).toHaveLength(3)
    expect(next.blocks[1]?.id).toBe(previous.blocks[0]?.id)
    expect(next.blocks[2]?.id).toBe(previous.blocks[1]?.id)
  })

  it('assigns new ids to newly inserted blocks', () => {
    const previous = parseMarkdownToCanonical({
      rawMarkdown: '第一段\n\n第二段',
      baseVersion: 'v1',
      draftRevision: 0,
    })

    const next = parseMarkdownToCanonical({
      rawMarkdown: '新增段落\n\n第一段\n\n第二段',
      baseVersion: 'v2',
      draftRevision: 1,
      previous,
    })

    expect(next.blocks[0]?.id).not.toBe(previous.blocks[0]?.id)
    expect(next.blocks[0]?.id).not.toBe(previous.blocks[1]?.id)
  })

  it('does not use rawStart or rawEnd as permanent identity', () => {
    const previous = parseMarkdownToCanonical({
      rawMarkdown: '第一段\n\n第二段',
      baseVersion: 'v1',
      draftRevision: 0,
    })

    const next = parseMarkdownToCanonical({
      rawMarkdown: '前缀内容\n\n第一段\n\n第二段',
      baseVersion: 'v2',
      draftRevision: 1,
      previous,
    })

    expect(next.blocks[1]?.source.rawStart).not.toBe(previous.blocks[0]?.source.rawStart)
    expect(next.blocks[2]?.source.rawStart).not.toBe(previous.blocks[1]?.source.rawStart)
    expect(next.blocks[1]?.id).toBe(previous.blocks[0]?.id)
    expect(next.blocks[2]?.id).toBe(previous.blocks[1]?.id)
  })
})

describe('footnote handling', () => {
  it('keeps a footnote definition block instead of dropping it', () => {
    const rawMarkdown = '国产化率约30%[^1]，预计2030年增长\n\n[^1]: 来源：工信部《产业报告》'
    const document = parseMarkdownToCanonical({
      rawMarkdown,
      baseVersion: 'test-v1',
      draftRevision: 0,
    })

    expect(document.blocks.map((block) => block.kind)).toEqual([
      'paragraph',
      'footnoteDefinition',
    ])

    const definitionBlock = document.blocks[1]
    if (definitionBlock.kind !== 'footnoteDefinition') {
      throw new Error('expected footnoteDefinition block')
    }
    expect(definitionBlock.identifier).toBe('1')
    expect(definitionBlock.editable).toBe(false)
    expect(definitionBlock.aiRewritable).toBe(false)
    expect(definitionBlock.source.rawSlice).toContain('来源：工信部《产业报告》')
  })

  it('preserves the footnote reference marker as visible paragraph text', () => {
    const rawMarkdown = '国产化率约30%[^1]，预计2030年增长\n\n[^1]: 来源：工信部《产业报告》'
    const document = parseMarkdownToCanonical({
      rawMarkdown,
      baseVersion: 'test-v1',
      draftRevision: 0,
    })

    const paragraph = document.blocks[0]
    if (paragraph.kind !== 'paragraph') {
      throw new Error('expected paragraph block')
    }

    expect(paragraph.visibleText).toBe('国产化率约30%[^1]，预计2030年增长')

    const footnoteInline = paragraph.inlines.find((inline) => inline.kind === 'footnoteReference')
    expect(footnoteInline?.text).toBe('[^1]')
  })
})

describe('projectParagraphView', () => {
  it('preserves paragraph soft-break lines without splitting the paragraph block', () => {
    const projected = projectParagraphView('第一行\n第二行\n第三行')

    expect(projected.visibleText).toBe('第一行\n第二行\n第三行')
    expect(projected.normalizedVisibleText).toBe('第一行 第二行 第三行')
    expect(projected.lines).toEqual([
      { kind: 'soft-break-line', visibleStart: 0, visibleEnd: 3 },
      { kind: 'soft-break-line', visibleStart: 4, visibleEnd: 7 },
      { kind: 'soft-break-line', visibleStart: 8, visibleEnd: 11 },
    ])
  })
})
