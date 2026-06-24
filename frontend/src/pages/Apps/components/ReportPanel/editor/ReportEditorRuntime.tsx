import React, { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { BlockNoteEditor as BNEditor, type Block } from '@blocknote/core'
import { BlockNoteView } from '@blocknote/mantine'
import { SideMenuController } from '@blocknote/react'
import '@blocknote/mantine/style.css'
import rehypeRaw from 'rehype-raw'
import rehypeStringify from 'rehype-stringify'
import remarkCjkFriendly from 'remark-cjk-friendly'
import remarkCjkFriendlyGfmStrikethrough from 'remark-cjk-friendly-gfm-strikethrough'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import remarkParse from 'remark-parse'
import remarkRehype from 'remark-rehype'
import { unified } from 'unified'
import { CustomSideMenu, AIRewritePanel, AIRewriteStatusIndicator } from './sideMenu'
import { buildBlockTransitionStyleRule, buildRewriteDiffStyleRule } from './blockTransitionStyle'
import { PANEL_TOTAL_HEIGHT, HIGHLIGHT_CSS, HIGHLIGHT_STYLE_ID } from '../constants'
import {
  getNextRewriteRunId,
  getRewriteEndStrategy,
  getRewriteCompletionCleanupPlan,
  getRewritePreflightFailureCleanupPlan,
  getIncomingAnimationBlockId,
  getRewriteSuccessCleanupDelayMs,
  getRewriteTransitionDelayMs,
  resolveDisplayedRewriteStatus,
  resolveRewriteMotionProfile,
  shouldQueueIncomingRewriteSnapshot,
  shouldLockRewriteInteractions,
  shouldReleaseRewriteLockBeforeVisualSettle,
  shouldRunScheduledRewriteEffect,
  shouldApplyRemoteRewriteStatus,
} from './rewriteTransitionPolicy'
import {
  advanceRewriteMotionPhase,
  createRewriteMotionSession,
  type RewriteMotionSession,
} from './rewriteMotionState'
import {
  buildRewriteSnapshotOverlay,
  shouldRenderSnapshotOverlay,
  type RewriteSnapshotOverlay,
} from './rewriteSnapshotOverlay'
import {
  buildRewriteDiffEmphasis,
  shouldFallbackToParagraphEmphasis,
  type RewriteDiffRange,
} from './rewriteDiffEmphasis'
import { useConversationStore } from '@/stores/useConversationStore'
import { parseMarkdownToCanonical, type CanonicalDocument } from './canonical'
import {
  applyRewriteResult,
  buildRewriteRequest,
  resolveParagraphRewriteTarget,
  selectRewriteSelection,
  type SelectionSnapshot,
} from './rewrite'
import {
  buildReportEditorViewModel,
  computeChangedBlockIds,
  matchCanonicalBlockByVisibleText,
  type ReportEditorViewModel,
} from './presentation'
import { shouldApplyExternalSnapshot } from './historyBaselinePolicy'
import { resolveEditorBootstrapCanonical } from './editorBootstrapPolicy'
import type { ReportRewriteAction, ReportRewriteParams, RewriteStatus, RewriteScope } from '@/pages/Apps/types'
import { useReducedMotion } from '../../shared'
import type { RecoveryState, RewriteOverlayState } from './session'
import './sideMenu/styles.css'

type AnyBlock = Block<any, any, any>

type RangeSelectionSnapshot = SelectionSnapshot & {
  range: Range | null
}

type PendingRewriteSnapshot = {
  raw: string
  canonical: CanonicalDocument
}

type HistoryExtension = {
  undoCommand?: Parameters<BNEditor<any, any, any>['canExec']>[0]
  redoCommand?: Parameters<BNEditor<any, any, any>['canExec']>[0]
}

type RenderedRewriteSnapshotOverlay = RewriteSnapshotOverlay & {
  padding: string
  borderRadius: string
  font: string
  lineHeight: string
  letterSpacing: string
  color: string
}

type RewriteDiffOverlay = RenderedRewriteSnapshotOverlay & {
  ranges: RewriteDiffRange[]
  paragraphFallback: boolean
}

type SyncEditorSnapshotResult = {
  incomingAnimationBlockId: string | null
}

const BLOCK_OUTER_SELECTOR = '[data-node-type="blockOuter"][data-id]'
type AnimationPhase = 'highlight' | 'fadeout' | 'fadein' | 'success' | 'error'

export interface ReportEditorRuntimeProps {
  rawContent: string
  canonicalDocument?: CanonicalDocument
  readonly?: boolean
  onChange?: (markdown: string) => void
  onDraftChange?: (markdown: string) => void
  onSelectionChange?: (selectedText: string, range: Range | null) => void
  className?: string
  scrollContainerRef?: React.RefObject<HTMLDivElement | null>
  conversationId?: string
  onReportRewrite?: (params: ReportRewriteParams) => Promise<void>
  onHistoryStateChange?: (state: {
    canUndo: boolean
    canRedo: boolean
    undo: () => void
    redo: () => void
  }) => void
  onSessionStateChange?: (state: {
    rewriteOverlayState: RewriteOverlayState
    recoveryState: RecoveryState
  }) => void
}

export type ReportEditorRuntimeHandle = {
  getCurrentMarkdown: () => Promise<string>
}

const getEditorElement = (wrapper: HTMLDivElement | null) =>
  wrapper?.querySelector('.bn-editor') as HTMLDivElement | null

const getBlockElement = (blockId: string, root: ParentNode = document) =>
  root.querySelector(
    `[data-node-type="blockOuter"][data-id="${blockId}"]`,
  ) as HTMLElement | null

const getBlockContentElement = (blockId: string, root: ParentNode = document) =>
  getBlockElement(blockId, root)?.querySelector('.bn-block-content') as HTMLElement | null

const getClosestBlockElement = (node: Node | null) => {
  if (!node) {
    return null
  }

  let current: Node | null = node.nodeType === Node.ELEMENT_NODE ? node : node.parentNode
  while (current) {
    if (
      current instanceof HTMLElement &&
      current.dataset.id &&
      current.matches(BLOCK_OUTER_SELECTOR)
    ) {
      return current
    }
    current = current.parentNode
  }

  return null
}

const getBlockVisibleText = (blockElement: HTMLElement) =>
  (blockElement.innerText || blockElement.textContent || '').trim()

const buildDiffTextSegments = (text: string, ranges: RewriteDiffRange[]) => {
  if (ranges.length === 0) {
    return [{ text, changed: false }]
  }

  const segments: Array<{ text: string; changed: boolean }> = []
  let cursor = 0

  for (const range of ranges) {
    const start = Math.max(0, Math.min(text.length, range.start))
    const end = Math.max(start, Math.min(text.length, range.end))

    if (cursor < start) {
      segments.push({
        text: text.slice(cursor, start),
        changed: false,
      })
    }

    if (start < end) {
      segments.push({
        text: text.slice(start, end),
        changed: true,
      })
    }

    cursor = end
  }

  if (cursor < text.length) {
    segments.push({
      text: text.slice(cursor),
      changed: false,
    })
  }

  return segments.filter((segment) => segment.text.length > 0)
}

const getVisibleOffsetFromBlockStart = (
  blockElement: HTMLElement,
  container: Node,
  offset: number,
) => {
  const range = document.createRange()
  range.setStart(blockElement, 0)
  range.setEnd(container, offset)
  return range.toString().length
}

const trimSelectionSnapshot = (snapshot: RangeSelectionSnapshot): RangeSelectionSnapshot | null => {
  const leadingWhitespace = snapshot.text.match(/^\s+/)?.[0].length ?? 0
  const trailingWhitespace = snapshot.text.match(/\s+$/)?.[0].length ?? 0
  const trimmedText = snapshot.text.trim()

  if (!trimmedText) {
    return null
  }

  return {
    ...snapshot,
    text: trimmedText,
    startOffsetInStartBlock: snapshot.startOffsetInStartBlock + leadingWhitespace,
    endOffsetInEndBlock: snapshot.endOffsetInEndBlock - trailingWhitespace,
  }
}

const createSelectionSnapshotFromRange = (range: Range): RangeSelectionSnapshot | null => {
  const rawText = range.toString()
  if (!rawText.trim()) {
    return null
  }

  const startBlockElement = getClosestBlockElement(range.startContainer)
  const endBlockElement = getClosestBlockElement(range.endContainer)
  if (!startBlockElement || !endBlockElement) {
    return null
  }

  return trimSelectionSnapshot({
    text: rawText,
    range: range.cloneRange(),
    startBlockId: startBlockElement.dataset.id || null,
    endBlockId: endBlockElement.dataset.id || null,
    startOffsetInStartBlock: getVisibleOffsetFromBlockStart(
      startBlockElement,
      range.startContainer,
      range.startOffset,
    ),
    endOffsetInEndBlock: getVisibleOffsetFromBlockStart(
      endBlockElement,
      range.endContainer,
      range.endOffset,
    ),
  })
}

const createSelectionSnapshotFromBlock = (blockElement: HTMLElement): RangeSelectionSnapshot | null => {
  const text = getBlockVisibleText(blockElement)
  if (!text) {
    return null
  }

  return {
    text,
    range: null,
    startBlockId: blockElement.dataset.id || null,
    endBlockId: blockElement.dataset.id || null,
    startOffsetInStartBlock: 0,
    endOffsetInEndBlock: text.length,
  }
}

const htmlRendererProcessor = unified()
  .use(remarkParse)
  .use(remarkGfm)
  .use(remarkCjkFriendly)
  .use(remarkCjkFriendlyGfmStrikethrough)
  .use(remarkMath, { singleDollarTextMath: true })
  .use(remarkRehype, { allowDangerousHtml: true })
  .use(rehypeRaw)
  .use(rehypeStringify)

const renderMarkdownToHTML = (markdown: string) => String(htmlRendererProcessor.processSync(markdown))

const parseMarkdownToEditorBlocks = (editor: BNEditor<any, any, any>, markdown: string) =>
  editor.tryParseHTMLToBlocks(renderMarkdownToHTML(markdown))

const createBlockNoteEditor = (initialMarkdown: string) => {
  const codeBlock = {
    createHighlighter: async () => ({
      codeToHtml: (code: string) => `<pre><code>${code}</code></pre>`,
    }),
  }
  const parserEditor = BNEditor.create({
    initialContent: [{ type: 'paragraph', props: {} }],
    codeBlock,
  })

  try {
    const initialBlocks = parseMarkdownToEditorBlocks(parserEditor, initialMarkdown)

    return BNEditor.create({
      initialContent:
        initialBlocks && initialBlocks.length > 0
          ? (initialBlocks as any)
          : [{ type: 'paragraph', props: {} }],
      codeBlock,
    })
  } finally {
    parserEditor._tiptapEditor.destroy()
  }
}

const buildCanonicalFromRaw = (
  rawMarkdown: string,
  previous: CanonicalDocument | null,
  fallbackBaseVersion: string,
) =>
  parseMarkdownToCanonical({
    rawMarkdown,
    baseVersion: previous?.meta.baseVersion ?? fallbackBaseVersion,
    draftRevision: previous?.meta.draftRevision ?? 0,
    previous,
  })

const buildEditorToCanonicalBlockMap = (
  editor: BNEditor<any, any, any>,
  document: CanonicalDocument,
  editorRoot: ParentNode | null,
) => {
  const map = new Map<string, string>()
  const editorBlocks = editor.document

  for (let index = 0; index < editorBlocks.length; index += 1) {
    const editorBlock = editorBlocks[index]
    const editorElement = editorRoot ? getBlockElement(editorBlock.id, editorRoot) : null
    const matchedCanonicalBlockId = matchCanonicalBlockByVisibleText({
      editorBlockIndex: index,
      editorVisibleText: editorElement ? getBlockVisibleText(editorElement) : '',
      blocks: document.blocks,
    })

    if (matchedCanonicalBlockId) {
      map.set(editorBlock.id, matchedCanonicalBlockId)
    }
  }

  return map
}

const translateSelectionToCanonical = (
  editor: BNEditor<any, any, any>,
  document: CanonicalDocument,
  selection: SelectionSnapshot,
  editorRoot: ParentNode | null,
): SelectionSnapshot => {
  const blockMap = buildEditorToCanonicalBlockMap(editor, document, editorRoot)

  return {
    text: selection.text,
    startBlockId: selection.startBlockId ? (blockMap.get(selection.startBlockId) ?? null) : null,
    endBlockId: selection.endBlockId ? (blockMap.get(selection.endBlockId) ?? null) : null,
    startOffsetInStartBlock: selection.startOffsetInStartBlock,
    endOffsetInEndBlock: selection.endOffsetInEndBlock,
  }
}

const buildViewModel = (
  previousDocument: CanonicalDocument | null,
  nextDocument: CanonicalDocument,
) => {
  const changedBlockIds = previousDocument
    ? computeChangedBlockIds(previousDocument, nextDocument)
    : nextDocument.blocks.map((block) => block.id)

  return buildReportEditorViewModel(nextDocument, changedBlockIds)
}

export const ReportEditorRuntime = forwardRef<ReportEditorRuntimeHandle, ReportEditorRuntimeProps>(({
  rawContent,
  canonicalDocument,
  readonly = false,
  onChange,
  onDraftChange,
  onSelectionChange,
  className = '',
  scrollContainerRef,
  conversationId: propConversationId,
  onReportRewrite,
  onHistoryStateChange,
  onSessionStateChange,
}, ref) => {
  const storeConversationId = useConversationStore((state) => state.currentConversationId)
  const conversationId = propConversationId || storeConversationId
  const sessionConversationId = useConversationStore((state) => state.SESSION_CONVERSATION_ID)
  const selectedResultMessageId = useConversationStore((state) => state.selectedResultMessageId)
  const messagesMap = useConversationStore((state) => state.messagesMap)
  const messageItemsMap = useConversationStore((state) => state.messageItemsMap)

  const remainingRewriteRounds = useMemo(() => {
    if (!selectedResultMessageId) {
      return undefined
    }

    const message = messagesMap.get(selectedResultMessageId)
    if (!message?.messageItemsId) {
      return undefined
    }

    const messageItems = messageItemsMap.get(message.messageItemsId)
    return messageItems?.remainingRewriteRounds
  }, [selectedResultMessageId, messagesMap, messageItemsMap])

  const [showRewritePanel, setShowRewritePanel] = useState(false)
  const [selectedBlock, setSelectedBlock] = useState<AnyBlock | null>(null)
  const [rewriteStatus, setRewriteStatus] = useState<RewriteStatus>('idle')
  const [rewriteErrorMessage, setRewriteErrorMessage] = useState<string | undefined>()
  const [isRewriting, setIsRewriting] = useState(false)
  const [selectedScope, setSelectedScope] = useState<RewriteScope | null>(null)
  const [needsRecovery, setNeedsRecovery] = useState(false)
  const [recoveryMessage, setRecoveryMessage] = useState<string | undefined>()
  const [motionSession, setMotionSession] = useState<RewriteMotionSession | null>(null)
  const [snapshotOverlay, setSnapshotOverlay] = useState<RenderedRewriteSnapshotOverlay | null>(null)
  const [diffOverlay, setDiffOverlay] = useState<RewriteDiffOverlay | null>(null)
  const [activeTransition, setActiveTransition] = useState<{
    blockId: string | null
    phase: AnimationPhase
  } | null>(null)
  const prefersReducedMotion = useReducedMotion()
  const motionProfile = useMemo(
    () => resolveRewriteMotionProfile({ prefersReducedMotion }),
    [prefersReducedMotion],
  )
  const displayedRewriteStatus = useMemo(
    () =>
      resolveDisplayedRewriteStatus({
        rewriteStatus,
        isRewriting,
        motionPhase: motionSession?.phase ?? null,
      }),
    [isRewriting, motionSession?.phase, rewriteStatus],
  )
  const isRewriteInteractionLocked = useMemo(
    () =>
      shouldLockRewriteInteractions({
        isRewriting,
        rewriteStatus,
        motionPhase: motionSession?.phase ?? null,
        hasActiveTransition: activeTransition !== null,
        needsRecovery,
      }),
    [activeTransition, isRewriting, motionSession?.phase, needsRecovery, rewriteStatus],
  )

  const fallbackBaseVersion = useMemo(
    () => `report:${selectedResultMessageId || 'draft'}`,
    [selectedResultMessageId],
  )
  const initialCanonicalRef = useRef<CanonicalDocument | null>(null)
  initialCanonicalRef.current = resolveEditorBootstrapCanonical({
    existingBootstrap: initialCanonicalRef.current,
    incomingCanonical: canonicalDocument,
    buildFallback: () => buildCanonicalFromRaw(rawContent, null, fallbackBaseVersion),
  })
  const initialCanonical = initialCanonicalRef.current
  const wrapperRef = useRef<HTMLDivElement | null>(null)
  const styleElRef = useRef<HTMLStyleElement | null>(null)
  const transitionStyleElRef = useRef<HTMLStyleElement | null>(null)
  const rawContentRef = useRef(initialCanonical.rawMarkdown)
  const canonicalDocumentRef = useRef<CanonicalDocument | null>(initialCanonical)
  const currentViewModelRef = useRef<ReportEditorViewModel | null>(
    buildReportEditorViewModel(
      initialCanonical,
      initialCanonical.blocks.map((block) => block.id),
    ),
  )
  const cachedSelectionRef = useRef<RangeSelectionSnapshot | null>(null)
  const rewriteSelectionRef = useRef<SelectionSnapshot | null>(null)
  const pendingIncomingPropsRef = useRef<PendingRewriteSnapshot | null>(null)
  const pendingAppliedRewriteRef = useRef<PendingRewriteSnapshot | null>(null)
  const needsRecoveryRef = useRef(false)
  const rewriteRunIdRef = useRef(0)
  const settleTimerRef = useRef<number | null>(null)
  const cleanupTimerRef = useRef<number | null>(null)
  const errorCleanupTimerRef = useRef<number | null>(null)
  const overlayCleanupTimerRef = useRef<number | null>(null)
  const applyingSnapshotRef = useRef(false)
  const draftChangeSeqRef = useRef(0)

  useEffect(() => {
    needsRecoveryRef.current = needsRecovery
  }, [needsRecovery])

  const clearScheduledRewriteTimers = useCallback(() => {
    if (settleTimerRef.current !== null) {
      window.clearTimeout(settleTimerRef.current)
      settleTimerRef.current = null
    }

    if (cleanupTimerRef.current !== null) {
      window.clearTimeout(cleanupTimerRef.current)
      cleanupTimerRef.current = null
    }

    if (errorCleanupTimerRef.current !== null) {
      window.clearTimeout(errorCleanupTimerRef.current)
      errorCleanupTimerRef.current = null
    }

    if (overlayCleanupTimerRef.current !== null) {
      window.clearTimeout(overlayCleanupTimerRef.current)
      overlayCleanupTimerRef.current = null
    }
  }, [])

  const applyBlockTransition = useCallback((blockId: string, phase: AnimationPhase) => {
    setActiveTransition({ blockId, phase })
  }, [])

  const captureRenderedSnapshotOverlay = useCallback(
    (blockId: string): RenderedRewriteSnapshotOverlay | null => {
      const editorElement = getEditorElement(wrapperRef.current)
      if (!editorElement) {
        return null
      }

      const blockContentElement =
        getBlockContentElement(blockId, editorElement) ?? getBlockElement(blockId, editorElement)
      if (!blockContentElement) {
        return null
      }

      const rect = blockContentElement.getBoundingClientRect()
      const styles = window.getComputedStyle(blockContentElement)

      return {
        ...buildRewriteSnapshotOverlay({
          blockId,
          text: getBlockVisibleText(blockContentElement),
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
        }),
        padding: styles.padding,
        borderRadius: styles.borderRadius,
        font: styles.font,
        lineHeight: styles.lineHeight,
        letterSpacing: styles.letterSpacing,
        color: styles.color,
      }
    },
    [],
  )

  const editor = useMemo(() => createBlockNoteEditor(initialCanonical.rawMarkdown), [initialCanonical])

  const syncEditorSnapshot = useCallback(
    (
      nextDocument: CanonicalDocument,
      options?: {
        changedCanonicalBlockIds?: string[]
        forceFullReplace?: boolean
      },
    ): SyncEditorSnapshotResult => {
      const previousViewModel = currentViewModelRef.current
      const changedCanonicalBlockIds =
        options?.changedCanonicalBlockIds ??
        buildViewModel(canonicalDocumentRef.current, nextDocument).blocks
          .filter((block) => block.isChanged)
          .map((block) => block.blockId)
      const nextViewModel = buildReportEditorViewModel(nextDocument, changedCanonicalBlockIds)

      if (!options?.forceFullReplace && previousViewModel && changedCanonicalBlockIds.length === 0) {
        currentViewModelRef.current = nextViewModel
        return { incomingAnimationBlockId: null }
      }

      const replaceWholeDocument = () => {
        const nextBlocks = parseMarkdownToEditorBlocks(editor, nextDocument.rawMarkdown)
        if (nextBlocks && nextBlocks.length > 0) {
          applyingSnapshotRef.current = true
          try {
            editor.replaceBlocks(editor.document, nextBlocks as any)
          } finally {
            applyingSnapshotRef.current = false
          }
        }
        currentViewModelRef.current = nextViewModel
        return { incomingAnimationBlockId: null }
      }

      const shouldForceFullReplace =
        options?.forceFullReplace ||
        !previousViewModel ||
        previousViewModel.blocks.length !== nextViewModel.blocks.length ||
        changedCanonicalBlockIds.length !== 1

      if (shouldForceFullReplace) {
        return replaceWholeDocument()
      }

      const changedCanonicalBlockId = changedCanonicalBlockIds[0]
      const nextIndex = nextViewModel.blocks.findIndex((block) => block.blockId === changedCanonicalBlockId)
      if (nextIndex < 0 || nextIndex >= editor.document.length) {
        return replaceWholeDocument()
      }

      const nextCanonicalBlock = nextDocument.blocks[nextIndex]
      const replacementBlocks = parseMarkdownToEditorBlocks(editor, nextCanonicalBlock.source.rawSlice)
      if (!replacementBlocks || replacementBlocks.length !== 1) {
        return replaceWholeDocument()
      }

      applyingSnapshotRef.current = true
      const replacementResult = (() => {
        try {
          return editor.replaceBlocks([editor.document[nextIndex]], replacementBlocks as any)
        } finally {
          applyingSnapshotRef.current = false
        }
      })()
      currentViewModelRef.current = nextViewModel
      return {
        incomingAnimationBlockId: getIncomingAnimationBlockId({
          insertedBlockIds: replacementResult.insertedBlocks.map((block) => block.id),
          replacementBlockIds: replacementBlocks.map((block) => block.id),
          nextEditorBlockIds: editor.document.map((block) => block.id),
          changedIndex: nextIndex,
        }),
      }
    },
    [editor],
  )

  const serializeEditorMarkdown = useCallback(async () => {
    const serializer = (editor as unknown as {
      blocksToMarkdownLossy?: (blocks?: AnyBlock[]) => string | Promise<string>
    }).blocksToMarkdownLossy

    if (!serializer) {
      return rawContentRef.current
    }

    return await serializer.call(editor, editor.document as AnyBlock[])
  }, [editor])

  useImperativeHandle(
    ref,
    () => ({
      getCurrentMarkdown: serializeEditorMarkdown,
    }),
    [serializeEditorMarkdown],
  )

  const emitHistoryState = useCallback(() => {
    const historyExtension =
      ((editor.getExtension('yUndo') ?? editor.getExtension('history')) as HistoryExtension | undefined)
    const canUndo = historyExtension?.undoCommand ? editor.canExec(historyExtension.undoCommand) : false
    const canRedo = historyExtension?.redoCommand ? editor.canExec(historyExtension.redoCommand) : false

    onHistoryStateChange?.({
      canUndo,
      canRedo,
      undo: () => {
        editor.undo()
      },
      redo: () => {
        editor.redo()
      },
    })
  }, [editor, onHistoryStateChange])

  const handleEditorChange = useCallback(() => {
    if (readonly || applyingSnapshotRef.current) {
      return
    }

    const seq = draftChangeSeqRef.current + 1
    draftChangeSeqRef.current = seq

    void serializeEditorMarkdown()
      .then((markdown) => {
        if (seq !== draftChangeSeqRef.current) {
          return
        }

        onChange?.(markdown)
        onDraftChange?.(markdown)
        emitHistoryState()
      })
      .catch((error) => {
        console.error('[ReportEditor] Markdown 序列化失败:', error)
      })
  }, [emitHistoryState, onChange, onDraftChange, readonly, serializeEditorMarkdown])

  useEffect(() => {
    return () => {
      editor._tiptapEditor.destroy()
    }
  }, [editor])

  useEffect(() => {
    const nextRawContent = rawContent
    const previousRawContent = rawContentRef.current
    const previousCanonical = canonicalDocumentRef.current

    const nextCanonical =
      canonicalDocument ??
      buildCanonicalFromRaw(nextRawContent, previousCanonical, fallbackBaseVersion)
    const changedCanonicalBlockIds = previousCanonical
      ? computeChangedBlockIds(previousCanonical, nextCanonical)
      : nextCanonical.blocks.map((block) => block.id)

    if (isRewriting) {
      if (
        shouldQueueIncomingRewriteSnapshot({
          previousRawContent,
          nextRawContent,
          changedCanonicalBlockIdsCount: changedCanonicalBlockIds.length,
        })
      ) {
        pendingIncomingPropsRef.current = {
          raw: nextRawContent,
          canonical: nextCanonical,
        }
      }
      return
    }

    if (
      !shouldApplyExternalSnapshot({
        previousRawContent,
        nextRawContent,
        changedCanonicalBlockIdsCount: changedCanonicalBlockIds.length,
        hasCurrentViewModel: currentViewModelRef.current !== null,
      })
    ) {
      canonicalDocumentRef.current = nextCanonical
      emitHistoryState()
      return
    }

    rawContentRef.current = nextRawContent
    syncEditorSnapshot(nextCanonical, {
      changedCanonicalBlockIds,
      forceFullReplace: !previousCanonical,
    })
    canonicalDocumentRef.current = nextCanonical
    setNeedsRecovery(false)
    setRecoveryMessage(undefined)
    emitHistoryState()
  }, [canonicalDocument, rawContent, isRewriting, fallbackBaseVersion, syncEditorSnapshot, emitHistoryState])

  useEffect(() => {
    emitHistoryState()
  }, [emitHistoryState])

  useEffect(() => {
    if (selectedBlock?.id) {
      let styleEl = document.getElementById(HIGHLIGHT_STYLE_ID) as HTMLStyleElement | null
      if (!styleEl) {
        styleEl = document.createElement('style')
        styleEl.id = HIGHLIGHT_STYLE_ID
        document.head.appendChild(styleEl)
      }

      styleElRef.current = styleEl
      styleEl.innerHTML = `[data-node-type="blockOuter"][data-id="${selectedBlock.id}"] { ${HIGHLIGHT_CSS} }`
      return
    }

    if (styleElRef.current) {
      styleElRef.current.innerHTML = ''
    }
  }, [selectedBlock?.id])

  useEffect(() => {
    let styleEl = document.getElementById('ai-block-transition-style') as HTMLStyleElement | null
    if (!styleEl) {
      styleEl = document.createElement('style')
      styleEl.id = 'ai-block-transition-style'
      document.head.appendChild(styleEl)
    }

    transitionStyleElRef.current = styleEl
    styleEl.innerHTML = [
      activeTransition ? buildBlockTransitionStyleRule(activeTransition) : '',
      buildRewriteDiffStyleRule({
        blockId: diffOverlay?.blockId ?? null,
        paragraphFallback: diffOverlay?.paragraphFallback ?? false,
      }),
    ]
      .filter(Boolean)
      .join('\n')
  }, [activeTransition, diffOverlay?.blockId, diffOverlay?.paragraphFallback])

  useEffect(() => {
    onSessionStateChange?.({
      rewriteOverlayState: displayedRewriteStatus,
      recoveryState: needsRecovery ? 'needsRecovery' : 'idle',
    })
  }, [displayedRewriteStatus, needsRecovery, onSessionStateChange])

  useEffect(() => {
    return () => {
      clearScheduledRewriteTimers()
      if (styleElRef.current) {
        styleElRef.current.remove()
        styleElRef.current = null
      }
      if (transitionStyleElRef.current) {
        transitionStyleElRef.current.remove()
        transitionStyleElRef.current = null
      }
    }
  }, [clearScheduledRewriteTimers])

  const captureCurrentSelection = useCallback(() => {
    const editorElement = getEditorElement(wrapperRef.current)
    const selection = window.getSelection()

    if (!editorElement || !selection || selection.rangeCount === 0 || selection.isCollapsed) {
      return null
    }

    const range = selection.getRangeAt(0)
    if (!editorElement.contains(range.commonAncestorContainer)) {
      return null
    }

    const snapshot = createSelectionSnapshotFromRange(range)
    if (!snapshot) {
      return null
    }

    cachedSelectionRef.current = snapshot
    onSelectionChange?.(snapshot.text, snapshot.range)
    return snapshot
  }, [onSelectionChange])

  useEffect(() => {
    const handleSelectionChange = () => {
      captureCurrentSelection()
    }

    document.addEventListener('mouseup', handleSelectionChange)
    document.addEventListener('keyup', handleSelectionChange)

    return () => {
      document.removeEventListener('mouseup', handleSelectionChange)
      document.removeEventListener('keyup', handleSelectionChange)
    }
  }, [captureCurrentSelection])

  const handleOpenRewritePanel = useCallback(
    (block: AnyBlock) => {
      if (needsRecovery) {
        return
      }

      if (!sessionConversationId) {
        setRewriteStatus('error')
        setRewriteErrorMessage('报告对应的改写会话已超时，请重新提问后再尝试改写。')
        return
      }

      const editorElement = getEditorElement(wrapperRef.current)
      const blockElement = editorElement ? getBlockElement(block.id, editorElement) : null
      if (!editorElement || !blockElement) {
        return
      }

      const currentSelection = captureCurrentSelection()
      const snapshot = selectRewriteSelection({
        liveSelection: currentSelection,
        cachedSelection: cachedSelectionRef.current,
        fallbackBlockSelection: createSelectionSnapshotFromBlock(blockElement),
        targetBlockId: block.id,
      })

      if (!snapshot) {
        return
      }

      rewriteSelectionRef.current = snapshot
      setSelectedBlock(block)
      setShowRewritePanel(true)

      if (scrollContainerRef?.current) {
        const containerRect = scrollContainerRef.current.getBoundingClientRect()
        const blockRect = blockElement.getBoundingClientRect()
        const spaceBelow = containerRect.bottom - blockRect.bottom
        if (spaceBelow < PANEL_TOTAL_HEIGHT) {
          scrollContainerRef.current.scrollTop += PANEL_TOTAL_HEIGHT - spaceBelow
        }
      }
    },
    [captureCurrentSelection, needsRecovery, scrollContainerRef, sessionConversationId],
  )

  const handleCloseRewritePanel = useCallback(() => {
    setShowRewritePanel(false)
    setSelectedBlock(null)
    setSelectedScope(null) // 重置选择范围
    rewriteSelectionRef.current = null
    window.getSelection()?.removeAllRanges()
  }, [])

  const handleReloadLatestVersion = useCallback(() => {
    try {
      const nextRawContent = rawContent
      const nextCanonical =
        canonicalDocument ??
        buildCanonicalFromRaw(nextRawContent, canonicalDocumentRef.current, fallbackBaseVersion)

      rawContentRef.current = nextRawContent
      syncEditorSnapshot(nextCanonical, {
        changedCanonicalBlockIds: nextCanonical.blocks.map((block) => block.id),
        forceFullReplace: true,
      })
      canonicalDocumentRef.current = nextCanonical
      pendingIncomingPropsRef.current = null
      pendingAppliedRewriteRef.current = null
      setNeedsRecovery(false)
      setRecoveryMessage(undefined)
      setRewriteStatus('idle')
      setRewriteErrorMessage(undefined)
      setMotionSession(null)
      setSnapshotOverlay(null)
      setDiffOverlay(null)
      setActiveTransition(null)
      setIsRewriting(false)
    } catch (error) {
      console.error('[ReportEditor] 重新加载最新版本失败:', error)
      setNeedsRecovery(true)
      setRecoveryMessage('重新加载最新版本失败，请刷新页面后重试。')
    }
  }, [canonicalDocument, rawContent, fallbackBaseVersion, syncEditorSnapshot])

  const resetAfterPreflightFailure = useCallback(() => {
    const cleanupPlan = getRewritePreflightFailureCleanupPlan()
    if (cleanupPlan.clearActiveTransitionImmediately) {
      setActiveTransition(null)
    }
    if (cleanupPlan.clearMotionImmediately) {
      setMotionSession(null)
    }
    if (cleanupPlan.clearOverlaysImmediately) {
      setSnapshotOverlay(null)
      setDiffOverlay(null)
    }
    if (cleanupPlan.releaseRewriteLockImmediately) {
      setIsRewriting(false)
    }
    pendingIncomingPropsRef.current = null
    pendingAppliedRewriteRef.current = null
  }, [])

  const runRewrite = useCallback(
    async (request: ReportRewriteParams) => {
      if (!conversationId || !onReportRewrite) {
        setRewriteStatus('idle')
        resetAfterPreflightFailure()
        return
      }

      clearScheduledRewriteTimers()
      const rewriteRunId = getNextRewriteRunId(rewriteRunIdRef.current)
      rewriteRunIdRef.current = rewriteRunId
      const currentBlockId = request.blockId
      let currentSnapshotOverlay: RenderedRewriteSnapshotOverlay | null = null
      let hasAppliedFadeOut = false
      let transitionStartedAt: number | null = currentBlockId ? Date.now() : null
      let hasEnteredVisibleRewrite = false

      setDiffOverlay(null)
      if (currentBlockId) {
        setMotionSession(createRewriteMotionSession({ runId: rewriteRunId, blockId: currentBlockId }))
        if (motionProfile.useOverlayMorph) {
          currentSnapshotOverlay = captureRenderedSnapshotOverlay(currentBlockId)
          setSnapshotOverlay(currentSnapshotOverlay)
        } else {
          setSnapshotOverlay(null)
        }
      } else {
        setMotionSession(null)
        setSnapshotOverlay(null)
      }

      const startVisibleRewrite = () => {
        if (hasEnteredVisibleRewrite) {
          return
        }

        hasEnteredVisibleRewrite = true
        setRewriteStatus('writing')
        setMotionSession((current) =>
          current ? advanceRewriteMotionPhase(current, 'writing') : current,
        )

        if (currentBlockId && motionProfile.useOverlayMorph && !currentSnapshotOverlay) {
          currentSnapshotOverlay = captureRenderedSnapshotOverlay(currentBlockId)
          setSnapshotOverlay(currentSnapshotOverlay)
        }

        if (!hasAppliedFadeOut && currentBlockId) {
          transitionStartedAt = Date.now()
          applyBlockTransition(currentBlockId, motionProfile.useBlur ? 'fadeout' : 'highlight')
          hasAppliedFadeOut = true
        }
      }

      await onReportRewrite({
        ...request,
        onStatusChange: (status) => {
          if (shouldApplyRemoteRewriteStatus(status)) {
            setRewriteStatus(status)
          }
        },
        onDelta: () => {
          startVisibleRewrite()
        },
        onSnapshot: (snapshot) => {
          startVisibleRewrite()
          const previousCanonical =
            canonicalDocumentRef.current ??
            buildCanonicalFromRaw(rawContentRef.current, null, fallbackBaseVersion)

          try {
            const nextCanonical = applyRewriteResult({
              previous: previousCanonical,
              nextRawMarkdown: snapshot.response_content,
              nextBaseVersion: `${previousCanonical.meta.baseVersion}:rewrite:${Date.now()}`,
            })

            pendingAppliedRewriteRef.current = {
              raw: snapshot.response_content,
              canonical: nextCanonical,
            }
          } catch (error) {
            console.error('[ReportEditor] canonical 快照应用失败:', error)
            needsRecoveryRef.current = true
            setNeedsRecovery(true)
            setRecoveryMessage('服务端版本已更新，但本地无法正确加载，请重新加载最新版本。')
            setRewriteStatus('error')
            setRewriteErrorMessage('服务端版本已更新，但本地无法正确加载，请重新加载最新版本。')
            setMotionSession(null)
            setSnapshotOverlay(null)
            setDiffOverlay(null)
            setIsRewriting(false)
            pendingAppliedRewriteRef.current = null
          }
        },
        onEnd: async () => {
          if (needsRecoveryRef.current) {
            return
          }

          // truth_verification saves annotations only — no document rewrite result expected
          if (request.action === 'truth_verification') {
            setRewriteStatus('idle')
            setIsRewriting(false)
            setMotionSession(null)
            setSnapshotOverlay(null)
            setActiveTransition(null)
            return
          }

          const rewriteEndStrategy = getRewriteEndStrategy({
            hasAppliedSnapshot: pendingAppliedRewriteRef.current !== null,
            hasPendingIncomingProps: pendingIncomingPropsRef.current !== null,
          })

          if (rewriteEndStrategy === 'missing-result') {
            const errorMessage = '服务端未返回可应用的改写结果，请重试。'
            console.error('[ReportEditor] 改写流结束，但没有可应用结果。')
            setRewriteStatus('error')
            setRewriteErrorMessage(errorMessage)
            setMotionSession(null)
            setSnapshotOverlay(null)
            setDiffOverlay(null)
            setIsRewriting(false)
            pendingAppliedRewriteRef.current = null
            pendingIncomingPropsRef.current = null

            if (currentBlockId) {
              applyBlockTransition(currentBlockId, 'error')
              errorCleanupTimerRef.current = window.setTimeout(() => {
                if (
                  !shouldRunScheduledRewriteEffect({
                    scheduledRunId: rewriteRunId,
                    activeRunId: rewriteRunIdRef.current,
                  })
                ) {
                  return
                }

                setActiveTransition((current) =>
                  current?.blockId === currentBlockId ? null : current,
                )
                errorCleanupTimerRef.current = null
              }, getRewriteSuccessCleanupDelayMs())
            }
            return
          }

          if (shouldReleaseRewriteLockBeforeVisualSettle()) {
            setIsRewriting(false)
          }

          const nextSnapshot = pendingAppliedRewriteRef.current ?? pendingIncomingPropsRef.current
          startVisibleRewrite()
          setMotionSession((current) =>
            current ? advanceRewriteMotionPhase(current, 'morphing') : current,
          )

          const transitionDelayMs = getRewriteTransitionDelayMs({
            firstDeltaAt: transitionStartedAt,
            now: Date.now(),
          })

          if (transitionDelayMs > 0) {
            await new Promise((resolve) => setTimeout(resolve, transitionDelayMs))
          }

          let incomingAnimationBlockId: string | null = null
          if (nextSnapshot) {
            rawContentRef.current = nextSnapshot.raw
            incomingAnimationBlockId = syncEditorSnapshot(nextSnapshot.canonical, {
              changedCanonicalBlockIds: canonicalDocumentRef.current
                ? computeChangedBlockIds(canonicalDocumentRef.current, nextSnapshot.canonical)
                : nextSnapshot.canonical.blocks.map((block) => block.id),
            }).incomingAnimationBlockId
            canonicalDocumentRef.current = nextSnapshot.canonical
          } else {
            const nextRawContent = rawContentRef.current
            const nextCanonical =
              canonicalDocument ??
              buildCanonicalFromRaw(
                nextRawContent,
                canonicalDocumentRef.current,
                fallbackBaseVersion,
              )
            incomingAnimationBlockId = syncEditorSnapshot(nextCanonical, {
              changedCanonicalBlockIds: canonicalDocumentRef.current
                ? computeChangedBlockIds(canonicalDocumentRef.current, nextCanonical)
                : nextCanonical.blocks.map((block) => block.id),
            }).incomingAnimationBlockId
            canonicalDocumentRef.current = nextCanonical
          }

          pendingAppliedRewriteRef.current = null
          pendingIncomingPropsRef.current = null

          requestAnimationFrame(() => {
            if (
              !shouldRunScheduledRewriteEffect({
                scheduledRunId: rewriteRunId,
                activeRunId: rewriteRunIdRef.current,
              })
            ) {
              return
            }

            const nextBlockOverlay = incomingAnimationBlockId
              ? captureRenderedSnapshotOverlay(incomingAnimationBlockId)
              : null

            if (incomingAnimationBlockId) {
              applyBlockTransition(incomingAnimationBlockId, motionProfile.useBlur ? 'fadein' : 'success')
            }

            if (motionProfile.useOverlayMorph && currentSnapshotOverlay) {
              overlayCleanupTimerRef.current = window.setTimeout(() => {
                if (
                  !shouldRunScheduledRewriteEffect({
                    scheduledRunId: rewriteRunId,
                    activeRunId: rewriteRunIdRef.current,
                  })
                ) {
                  return
                }

                setSnapshotOverlay(null)
                overlayCleanupTimerRef.current = null
              }, 420)
            } else {
              setSnapshotOverlay(null)
            }

            if (motionProfile.useDiffEmphasis && nextBlockOverlay) {
              const ranges = buildRewriteDiffEmphasis({
                previousText: currentSnapshotOverlay?.text ?? '',
                nextText: nextBlockOverlay.text,
              })

              setDiffOverlay({
                ...nextBlockOverlay,
                ranges,
                paragraphFallback: shouldFallbackToParagraphEmphasis(ranges),
              })
            } else {
              setDiffOverlay(null)
            }

            settleTimerRef.current = window.setTimeout(() => {
              if (
                !shouldRunScheduledRewriteEffect({
                  scheduledRunId: rewriteRunId,
                  activeRunId: rewriteRunIdRef.current,
                })
              ) {
                return
              }

              setRewriteStatus('idle')
              const cleanupPlan = getRewriteCompletionCleanupPlan({
                incomingAnimationBlockId,
              })
              setMotionSession((current) =>
                current
                  ? {
                      ...advanceRewriteMotionPhase(current, 'settling'),
                      blockId: incomingAnimationBlockId ?? current.blockId,
                    }
                  : current,
              )
              if (cleanupPlan.needsDelayedSuccessCleanup && incomingAnimationBlockId) {
                applyBlockTransition(incomingAnimationBlockId, 'success')
                cleanupTimerRef.current = window.setTimeout(() => {
                  if (
                    !shouldRunScheduledRewriteEffect({
                      scheduledRunId: rewriteRunId,
                      activeRunId: rewriteRunIdRef.current,
                    })
                  ) {
                    return
                  }

                  setActiveTransition((current) =>
                    current?.blockId === incomingAnimationBlockId ? null : current,
                  )
                  setMotionSession(null)
                  setSnapshotOverlay(null)
                  setDiffOverlay(null)
                  setIsRewriting(false)
                  cleanupTimerRef.current = null
                }, getRewriteSuccessCleanupDelayMs())
              } else {
                if (cleanupPlan.clearActiveTransitionImmediately) {
                  setActiveTransition(null)
                }
                setMotionSession(null)
                setSnapshotOverlay(null)
                setDiffOverlay(null)
                setIsRewriting(false)
              }
              settleTimerRef.current = null
            }, motionProfile.settleMs)
          })
        },
        onError: (error) => {
          console.error('[ReportEditor] 改写错误:', error)
          setRewriteStatus('error')
          setRewriteErrorMessage(error)
          setMotionSession(null)
          setSnapshotOverlay(null)
          setDiffOverlay(null)
          setIsRewriting(false)
          pendingAppliedRewriteRef.current = null

          if (currentBlockId) {
            applyBlockTransition(currentBlockId, 'error')
            errorCleanupTimerRef.current = window.setTimeout(() => {
              if (
                !shouldRunScheduledRewriteEffect({
                  scheduledRunId: rewriteRunId,
                  activeRunId: rewriteRunIdRef.current,
                })
              ) {
                return
              }

              setActiveTransition((current) =>
                current?.blockId === currentBlockId ? null : current,
              )
              errorCleanupTimerRef.current = null
            }, getRewriteSuccessCleanupDelayMs())
          }
        },
      })
    },
    [
      applyBlockTransition,
      canonicalDocument,
      captureRenderedSnapshotOverlay,
      clearScheduledRewriteTimers,
      conversationId,
      fallbackBaseVersion,
      motionProfile,
      onReportRewrite,
      resetAfterPreflightFailure,
      syncEditorSnapshot,
    ],
  )

  const handleSubmitRewrite = useCallback(
    async (action: ReportRewriteAction, prompt?: string, rewriteScope?: RewriteScope) => {
      const currentSelection = rewriteSelectionRef.current
      if (needsRecovery) {
        setRewriteStatus('error')
        setRewriteErrorMessage('服务端版本已更新，但本地无法正确加载，请先重新加载最新版本。')
        return
      }

      if (!currentSelection || !currentSelection.text || !editor) {
        return
      }

      if (selectedBlock?.id) {
        applyBlockTransition(selectedBlock.id, 'highlight')
      }

      handleCloseRewritePanel()
      setIsRewriting(true)
      pendingIncomingPropsRef.current = null
      pendingAppliedRewriteRef.current = null
      setRewriteStatus('thinking')
      setRewriteErrorMessage(undefined)

      const currentCanonical =
        canonicalDocumentRef.current ??
        buildCanonicalFromRaw(rawContentRef.current, null, fallbackBaseVersion)
      const canonicalSelection = translateSelectionToCanonical(
        editor,
        currentCanonical,
        currentSelection,
        getEditorElement(wrapperRef.current),
      )
      const target = resolveParagraphRewriteTarget({
        document: currentCanonical,
        selection: canonicalSelection,
      })

      if ('error' in target) {
        const errorMessage =
          target.error === 'cross_block'
            ? '当前仅支持单段改写'
            : target.error === 'non_paragraph'
              ? '当前块类型暂不支持改写'
              : target.error === 'partial_inline_selection'
                ? '当前选区部分命中了格式化片段，请完整选中该片段或改为纯文本选区。'
              : '没有有效选区，无法执行改写'
        setRewriteStatus('error')
        setRewriteErrorMessage(errorMessage)
        resetAfterPreflightFailure()
        return
      }

      if (!conversationId) {
        setRewriteStatus('error')
        setRewriteErrorMessage('当前没有可用会话，无法执行改写。')
        setIsRewriting(false)
        return
      }

      if (!sessionConversationId) {
        setRewriteStatus('error')
        setRewriteErrorMessage('报告对应的改写会话已超时，请重新提问后再尝试改写。')
        resetAfterPreflightFailure()
        return
      }

      const request = buildRewriteRequest({
        target,
        action,
        conversationId,
        userInstruction: prompt,
        rewrite_scope: rewriteScope,
      })

      // 后端对 selected_text 的校验是 content[start:end] === selected_text，
      // 因此发给后端的 selectedText 必须与 offset 同域（raw markdown 切片），
      // 这与 AI 改写完全一致，复用同一套校验。
      // truth_verification 额外需要可见文本供批注层 findTextRange 做 DOM 搜索，
      // 故单独挂在 displayText 上（不进入后端 payload）。
      if (action === 'truth_verification') {
        request.displayText = currentSelection.text.trim()
      }

      await runRewrite({
        ...request,
        blockId: selectedBlock?.id,
      })
    },
    [
      applyBlockTransition,
      conversationId,
      editor,
      fallbackBaseVersion,
      handleCloseRewritePanel,
      needsRecovery,
      resetAfterPreflightFailure,
      runRewrite,
      sessionConversationId,
      selectedBlock?.id,
    ],
  )

  const visibleSnapshotOverlay =
    motionSession && snapshotOverlay && shouldRenderSnapshotOverlay(motionSession.phase)
      ? snapshotOverlay
      : null
  const diffSegments =
    diffOverlay && !diffOverlay.paragraphFallback
      ? buildDiffTextSegments(diffOverlay.text, diffOverlay.ranges)
      : []

  if (!editor) {
    return (
      <div className={`animate-pulse space-y-3 ${className}`}>
        <div className="h-8 w-1/2 rounded bg-gray-200"></div>
        <div className="h-4 w-full rounded bg-gray-200"></div>
        <div className="h-4 w-11/12 rounded bg-gray-200"></div>
        <div className="h-4 w-full rounded bg-gray-200"></div>
        <div className="h-4 w-4/5 rounded bg-gray-200"></div>
      </div>
    )
  }

  return (
    <div
      ref={wrapperRef}
      className={`blocknote-editor-wrapper ${className}`}
      style={{
        width: '100%',
        minHeight: '200px',
        position: 'relative',
      }}
    >
      {visibleSnapshotOverlay ? (
        <div
          className={`rewrite-snapshot-overlay rewrite-snapshot-overlay--${motionSession?.phase ?? 'locked'} ${
            motionProfile.useBlur ? '' : 'rewrite-snapshot-overlay--reduced'
          }`}
          style={{
            top: visibleSnapshotOverlay.rect.top,
            left: visibleSnapshotOverlay.rect.left,
            width: visibleSnapshotOverlay.rect.width,
            minHeight: visibleSnapshotOverlay.rect.height,
            padding: visibleSnapshotOverlay.padding,
            borderRadius: visibleSnapshotOverlay.borderRadius,
            font: visibleSnapshotOverlay.font,
            lineHeight: visibleSnapshotOverlay.lineHeight,
            letterSpacing: visibleSnapshotOverlay.letterSpacing,
            color: visibleSnapshotOverlay.color,
          }}
          aria-hidden="true"
        >
          {visibleSnapshotOverlay.text}
        </div>
      ) : null}

      {diffOverlay && !diffOverlay.paragraphFallback ? (
        <div
          className={`rewrite-diff-overlay ${
            motionProfile.useBlur ? '' : 'rewrite-diff-overlay--reduced'
          }`}
          style={{
            top: diffOverlay.rect.top,
            left: diffOverlay.rect.left,
            width: diffOverlay.rect.width,
            minHeight: diffOverlay.rect.height,
            padding: diffOverlay.padding,
            borderRadius: diffOverlay.borderRadius,
            font: diffOverlay.font,
            lineHeight: diffOverlay.lineHeight,
            letterSpacing: diffOverlay.letterSpacing,
            color: diffOverlay.color,
          }}
          aria-hidden="true"
        >
          {diffSegments.map((segment, index) =>
            segment.changed ? (
              <mark key={`rewrite-diff-${index}`} data-rewrite-diff="true">
                {segment.text}
              </mark>
            ) : (
              <span key={`rewrite-diff-${index}`}>{segment.text}</span>
            ),
          )}
        </div>
      ) : null}

      {needsRecovery ? (
        <div className="mb-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <div className="font-medium">服务端版本已更新，但本地无法正确加载</div>
          <div className="mt-1">{recoveryMessage}</div>
          <button
            type="button"
            className="mt-2 rounded border border-amber-400 bg-white px-3 py-1 text-xs font-medium text-amber-900"
            onClick={handleReloadLatestVersion}
          >
            重新加载最新版本
          </button>
        </div>
      ) : null}

      <BlockNoteView
        editor={editor}
        editable={!readonly && !needsRecovery}
        theme="light"
        onChange={handleEditorChange}
        onSelectionChange={captureCurrentSelection}
        sideMenu={false}
        formattingToolbar={false}
        linkToolbar={false}
        slashMenu={false}
      >
        <SideMenuController
          sideMenu={() =>
            showRewritePanel || isRewriteInteractionLocked ? null : (
              <CustomSideMenu onOpenRewritePanel={handleOpenRewritePanel} />
            )
          }
        />
      </BlockNoteView>

      {showRewritePanel && selectedBlock ? (
        <AIRewritePanel
          block={selectedBlock}
          editor={editor}
          onClose={handleCloseRewritePanel}
          onSubmit={handleSubmitRewrite}
          remainingRewriteRounds={remainingRewriteRounds}
          selectedScope={selectedScope}
          onScopeSelect={setSelectedScope}
        />
      ) : null}

      <AIRewriteStatusIndicator
        status={displayedRewriteStatus}
        visible={displayedRewriteStatus !== 'idle'}
        errorMessage={rewriteErrorMessage}
        onAutoHide={() => {
          setRewriteStatus('idle')
          setRewriteErrorMessage(undefined)
        }}
      />
    </div>
  )
})

ReportEditorRuntime.displayName = 'ReportEditorRuntime'
