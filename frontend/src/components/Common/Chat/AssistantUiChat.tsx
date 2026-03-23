/**
 * 聊天 UI（仅 AG-UI 模式）：
 * 使用 assistant-ui 内置的 AG-UI runtime（`useAgUiRuntime`）自动完成“发送 + 解析 AG-UI SSE 事件 + 状态管理”，
 * 父页面只需要提供 endpoint、鉴权 header 和请求体映射。
 */

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ActionBarPrimitive,
  AssistantRuntimeProvider,
  ComposerPrimitive,
  ThreadPrimitive,
  useMessage,
  useMessageRuntime,
  useThread,
  useThreadComposer,
  useThreadRuntime,
} from '@assistant-ui/react'
import { useActionBarCopy } from '@assistant-ui/core/react'
import { ExportedMessageRepository } from '@assistant-ui/core'
import { useAgUiRuntime } from '@assistant-ui/react-ag-ui'
import { AssistantActionBar, AssistantMessage, BranchPicker, Thread, UserMessage, useThreadConfig } from '@assistant-ui/react-ui'
import { HttpAgent } from '@ag-ui/client'
import { Copy as CopyIcon, Plus, Send, Square, Trash2 } from 'lucide-react'
import type { SnackbarMessage } from '@/Common/UnifiedSnackbar'
import { copyToClipboard } from '@/utils/prompts/utils'
import './chat.css'

function reseedThreadMessagesForReset(messages: readonly any[]): readonly any[] {
  // `thread.reset()` 会把传入的消息“当作新会话初始消息”重新建图。
  // 但 thread.getState().messages 里包含 assistant-ui 内部的隐藏字段（例如 symbol 属性），
  // 直接把它们塞回 reset 可能导致分支/父子关联残留，进而出现 BranchPicker 错乱。
  // 这里把消息“摘干净”成 ThreadMessageLike，并重新生成 id，确保 reset 后是线性的干净线程。
  const newId = () => (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`)

  return messages.map((m: any) => {
    const base: any = {
      id: newId(),
      role: m.role,
      createdAt: m.createdAt,
      content: m.content,
      metadata: m.metadata,
    }
    if (m.role === 'assistant') base.status = m.status
    if (m.role === 'user') base.attachments = m.attachments
    return base as ThreadMessageLike
  })
}

function setComposerTextSafe(composer: unknown, text: string): void {
  const c = composer as any
  if (!c) return
  if (typeof c.setText === 'function') {
    c.setText(text)
    return
  }
  if (typeof c.setValue === 'function') {
    c.setValue(text)
    return
  }
  if (typeof c.setDraft === 'function') {
    c.setDraft(text)
    return
  }
  if (typeof c.update === 'function') {
    c.update({ text })
  }
}

function extractMessageText(content: unknown): string {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .map((part: any) => {
        if (typeof part === 'string') return part
        if (part && typeof part.text === 'string') return part.text
        if (part && typeof part.value === 'string') return part.value
        return ''
      })
      .join('')
  }
  if (content && typeof (content as any).text === 'string') return (content as any).text
  return ''
}

function normalizeAssistantStatusAfterCancel(message: any): any {
  if (message?.role !== 'assistant') return message

  const status = message?.status
  if (!status) return message

  const cancelledStatus = { type: 'incomplete', reason: 'cancelled' as const }

  if (typeof status === 'string') {
    const normalized = status.toLowerCase()
    if (normalized === 'running' || normalized === 'in_progress' || normalized === 'inprogress' || normalized === 'streaming') {
      return { ...message, status: cancelledStatus }
    }
    return message
  }

  if (typeof status === 'object') {
    const type = String((status as any).type ?? '').toLowerCase()
    if (type && type !== 'complete' && type !== 'incomplete') {
      return { ...message, status: cancelledStatus }
    }
  }

  return message
}

/**
 * 注意：这些组件必须放在模块顶层，保证引用稳定。
 * 否则流式更新时父组件反复 render 会导致消息组件被卸载/重挂，产生“内容闪烁”。
 */
const ExtendedAssistantActionBar = () => {
  const { t } = useTranslation()
  const thread = useThreadRuntime()
  const composer = useThreadComposer()
  const message = useMessage()
  const messageRuntime = useMessageRuntime()

  const setSnackbarGlobal = useCallback((snackbar: SnackbarMessage) => {
    // 通过全局事件让外层页面的 <UnifiedSnackbar /> 展示提示
    window.dispatchEvent(
      new CustomEvent('global-snackbar', {
        detail: {
          message: snackbar.message,
          severity: snackbar.severity,
          duration: snackbar.duration ?? 3000,
        },
      }),
    )
  }, [])

  // 复用 assistant-ui 的 copy 逻辑（从当前 assistant 消息/编辑器拿到正确的文本），
  // 但写入剪贴板仍交给项目内的 copyToClipboard（带 snackbar 反馈与兼容处理）。
  const { copy: copyAction, disabled: copyDisabled } = useActionBarCopy({
    copiedDuration: 3000,
    copyToClipboard: (text: string) => copyToClipboard(text, setSnackbarGlobal),
  })

  const handleFollowUp = () => {
    const base = (messageRuntime.unstable_getCopyText?.() || '').trim()
    const nextText = base
      ? `基于上面这条回答，我想继续追问：\n- （问题）\n\n参考内容：\n${base}\n`
      : '我想继续追问：\n- （问题）\n'
    setComposerTextSafe(composer, nextText)
  }

  const handleDelete = () => {
    const state = thread.getState()
    const aiIdx = message.index
    const msgs = state.messages

    // 找到与该 AI 回复“对应”的用户消息：向前回溯最近的一条 user
    let userIdx = -1
    for (let i = aiIdx - 1; i >= 0; i--) {
      if (msgs[i]?.role === 'user') {
        userIdx = i
        break
      }
    }
    if (userIdx < 0) return

    const remaining = msgs.filter((_, idx) => idx !== userIdx && idx !== aiIdx)
    thread.reset(reseedThreadMessagesForReset(remaining))
  }

  return (
    <AssistantActionBar.Root
      hideWhenRunning
      autohide="not-last"
      autohideFloat="single-branch"
      className="agentstudio-ai-actionbar"
    >
      <AssistantActionBar.Reload />

      <button
        type="button"
        className="aui-button aui-button-ghost aui-button-icon"
        onClick={() => copyAction?.()}
        disabled={copyDisabled}
        title={t('common.buttons.copy')}
      >
        <CopyIcon />
      </button>

      <ActionBarPrimitive.Root asChild>
        <button type="button" className="aui-button aui-button-ghost aui-button-icon" onClick={handleDelete} title={t('common.buttons.delete')}>
          <Trash2 />
        </button>
      </ActionBarPrimitive.Root>
    </AssistantActionBar.Root>
  )
}

const CustomAssistantMessage = () => {
  const { t } = useTranslation()
  const message = useMessage()
  if (message.role !== 'assistant') return null

  const dividerLabel = t('runtime.publish.chat.newChatDivider')
  const messageText = extractMessageText(message.content).trim()
  const isNewChatDivider = message?.metadata?.agentstudio?.type === 'new_chat_divider' || messageText === dividerLabel
  if (isNewChatDivider) {
    const label = messageText || dividerLabel
    return (
      <div className="agentstudio-chat-divider" role="separator" aria-label={label}>
        <span>{label}</span>
      </div>
    )
  }

  const threadConfig = useThreadConfig()
  const assistantName = threadConfig.assistantAvatar?.alt ?? ''
  return (
    <AssistantMessage.Root data-assistant-name={assistantName}>
      <AssistantMessage.Avatar />
      <AssistantMessage.Content data-assistant-name={assistantName} />
      <BranchPicker />
      <ExtendedAssistantActionBar />
    </AssistantMessage.Root>
  )
}

const CustomUserMessage = () => {
  const message = useMessage()
  if (message.role !== 'user') return null
  return (
    <UserMessage.Root>
      <UserMessage.Content />
    </UserMessage.Root>
  )
}

const CustomComposer = () => {
  const { t } = useTranslation()
  const thread = useThreadRuntime()
  const allowCancel = useThread((t) => t.capabilities.cancel)

  const [hasMessages, setHasMessages] = useState(() => (thread.getState()?.messages?.length ?? 0) > 0)

  useEffect(() => {
    let unsub: undefined | (() => void)
    const update = () => {
      setHasMessages((thread.getState()?.messages?.length ?? 0) > 0)
    }
    update()

    const maybeSubscribe = (thread as any)?.subscribe
    if (typeof maybeSubscribe === 'function') {
      unsub = maybeSubscribe.call(thread, update)
      return () => unsub?.()
    }

    const timer = window.setInterval(update, 250)
    return () => window.clearInterval(timer)
  }, [thread])

  const handleNewThread = () => {
    const state = thread.getState()
    const msgs = state?.messages ?? []
    if (!msgs.length) return

    const divider = {
      id: typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
      role: 'assistant',
      status: 'complete',
      createdAt: new Date(),
      content: t('runtime.publish.chat.newChatDivider'),
      metadata: { agentstudio: { type: 'new_chat_divider' } },
    }

    thread.import(ExportedMessageRepository.fromArray(reseedThreadMessagesForReset([...msgs, divider])))
  }

  const handleCancelFinalize = () => {
    // 对齐官方 runtime 的取消思路：优先触发线程取消，再做状态收敛兜底。
    ;(thread as any)?.cancel?.()

    const finalizeCancelState = () => {
      const state = thread.getState() as any
      const msgs = state?.messages ?? []
      const normalized = msgs.map((m: any) => normalizeAssistantStatusAfterCancel(m))
      const changed = normalized.some((m: any, i: number) => m !== msgs[i])
      if (!changed) return
      thread.import(ExportedMessageRepository.fromArray(reseedThreadMessagesForReset(normalized)))
    }

    finalizeCancelState()
    // 某些流式适配器会晚一个 tick 才把最终事件回写，补两次收敛，避免 UI 卡在 running。
    window.setTimeout(finalizeCancelState, 120)
    window.setTimeout(finalizeCancelState, 500)
  }

  return (
    <ComposerPrimitive.Root className="aui-composer-root">
      <button
        type="button"
        className="agentstudio-composer-newchat"
        onClick={handleNewThread}
        disabled={!hasMessages}
        title={t('runtime.publish.chat.newChat')}
        aria-label={t('runtime.publish.chat.newChat')}
      >
        <Plus />
      </button>
      <ComposerPrimitive.Input className="aui-composer-input" />
      {allowCancel ? (
        <>
          <ThreadPrimitive.If running={false}>
            <ComposerPrimitive.Send className="aui-composer-send" title={t('runtime.publish.chat.send')}>
              <Send />
            </ComposerPrimitive.Send>
          </ThreadPrimitive.If>
          <ThreadPrimitive.If running>
            <ComposerPrimitive.Cancel
              className="aui-composer-cancel"
              title={t('common.buttons.stopResponse')}
              aria-label={t('common.buttons.stopResponse')}
              onClick={handleCancelFinalize}
            >
              <Square />
            </ComposerPrimitive.Cancel>
          </ThreadPrimitive.If>
        </>
      ) : (
        <ComposerPrimitive.Send className="aui-composer-send" title={t('runtime.publish.chat.send')}>
          <Send />
        </ComposerPrimitive.Send>
      )}
    </ComposerPrimitive.Root>
  )
}

export interface AssistantUiChatProps {
  /**
   * AG-UI 配置：组件将接管发送和解析（必填）。
   * - `url`: 后端 AG-UI SSE 端点
   * - `headers`: 额外 header（例如 Authorization）
   * - `buildBody`: 将 RunAgentInput 映射成后端请求体（适配你们的 /execution/agent）
   */
  agUi: {
    url: string
    headers?: Record<string, string>
    buildBody: (input: any) => unknown
  }
  /** 顶部标题（不传则默认「提示词调试」） */
  title?: string
  emptyStateText?: string
  placeholder?: string
  assistantIcon?: string
  assistantName?: string
  userName?: string
  className?: string
}

/**
 * 使用 assistant-ui 拼接的完整聊天面板。
 * 使用 AG-UI runtime（useAgUiRuntime + Thread）。
 */
export function AssistantUiChat({
  agUi,
  title,
  emptyStateText,
  placeholder,
  assistantIcon,
  assistantName,
  userName,
  className = '',
}: AssistantUiChatProps) {
  const { t } = useTranslation()
  const agUiConfigRef = useRef(agUi)

  useEffect(() => {
    agUiConfigRef.current = agUi
  }, [agUi])

  const threadComponents = useMemo(
    () => ({ AssistantMessage: CustomAssistantMessage, UserMessage: CustomUserMessage, Composer: CustomComposer }),
    [],
  )

  const agUiAgent = useMemo(() => {
    class ExecutionHttpAgent extends HttpAgent {
      // react-ag-ui 当前实现会以第三个参数传入 { signal }，
      // 但 @ag-ui/client 的 runAgent 期望的是 parameters.abortController。
      // 这里做一层桥接，确保取消信号能真正中断底层流式请求。
      async runAgent(parameters?: any, subscriber?: any, maybeOptions?: any): Promise<any> {
        const params = { ...(parameters || {}) }
        const signal: AbortSignal | undefined = maybeOptions?.signal

        if (signal && !params.abortController) {
          const abortController = new AbortController()
          if (signal.aborted) {
            abortController.abort()
          } else {
            signal.addEventListener('abort', () => abortController.abort(), { once: true })
          }
          params.abortController = abortController
        }

        return super.runAgent(params, subscriber)
      }

      protected requestInit(input: any): RequestInit {
        const cfg = agUiConfigRef.current
        const base = super.requestInit(input)
        return {
          ...base,
          method: 'POST',
          headers: {
            ...(base?.headers as Record<string, string> | undefined),
            ...(cfg.headers || {}),
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
          },
          body: JSON.stringify(cfg.buildBody(input)),
          // 复用 super.requestInit(input) 里的 signal，确保 ComposerPrimitive.Cancel 可中断流式请求
          signal: base?.signal,
        }
      }
    }

    return new ExecutionHttpAgent({ url: agUi.url, headers: agUi.headers })
  }, [agUi.url])

  const agUiRuntime = useAgUiRuntime({
    agent: agUiAgent,
    onCancel: () => {
      try {
        agUiAgent.abortRun()
      } catch {
        // ignore
      }
    },
  })

  return (
    <AssistantRuntimeProvider runtime={agUiRuntime}>
      <div
        className={`agentstudio-chat ${className}`}
        // content: var(--agentstudio-user-name) 需要带引号的字符串形态（如："Tom"）
        style={{ ['--agentstudio-user-name' as any]: JSON.stringify(userName ?? '') } as CSSProperties}
      >
        <div className="agentstudio-chat-thread">
          <div className="agentstudio-chat-title sr-only">{title ?? '提示词调试'}</div>
          <Thread
            welcome={{
              message: emptyStateText ?? t('runtime.publish.chat.emptyStateText'),
            }}
            assistantAvatar={{
              fallback: assistantIcon ?? '🤖',
              alt: assistantName ?? '',
            }}
            components={threadComponents}
            strings={{
              composer: { input: { placeholder: placeholder ?? t('runtime.publish.chat.inputPlaceholder') } },
              assistantMessage: {
                reload: { tooltip: t('common.actions.retry') },
                copy: { tooltip: t('common.buttons.copy') },
              },
            }}
          />
        </div>
      </div>
    </AssistantRuntimeProvider>
  )
}
