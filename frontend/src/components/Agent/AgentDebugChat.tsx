import { Paper, Switch } from '@mui/material'
import { useState, useEffect, useRef, memo } from 'react'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { ExecutionService, SaveAgentRequest } from '@test-agentstudio/api-client'
import { ActionSlotMount } from '@/components/Common/ActionSlot'
import AgentOperationsBar from './AgentOperationsBar'
import AgentDebugPanel from './AgentDebugPanel'
import MemoryButton from '@/pages/MemoryBase/MemoryButton'
import { MessageRenderer } from './messages/MessageRenderer'
import { useScopedTranslation } from '@/i18n'

import type { ChatMessage } from './messages/chatTypes'

const extractTextFromOutput = (outputRaw: any) => {
  if (typeof outputRaw === 'string') return outputRaw
  if (outputRaw == null) return ''
  try {
    return JSON.stringify(outputRaw)
  } catch {
    return String(outputRaw)
  }
}

/**
 * 智能体调试聊天组件的属性接口
 */
interface AgentDebugChatProps {
  /** 智能体ID */
  agentId: string
  /** 此智能体的记忆库ID */
  mdbId?: string
  /** 调试信息面板开关变化回调 */
  onDebugInfoChange?: (open: boolean) => void
  /** 是否显示长期记忆，透传给MemoryButton */
  enableLongTerm?: boolean
  /** 是否隐藏记忆按钮（单Agent多工作流模式下隐藏） */
  hideMemoryButton?: boolean
  /** 智能体保存请求（包含所有业务数据和版本信息） */
  saveAgentRequest: SaveAgentRequest
  /** 模型是否可用（未被禁用） */
  isModelActive?: boolean
}

/**
 * 智能体调试聊天组件
 * 提供与智能体交互的聊天界面，支持调试信息显示
 */
const AgentDebugChat = ({ agentId, mdbId, onDebugInfoChange, enableLongTerm, hideMemoryButton, saveAgentRequest, isModelActive = true }: AgentDebugChatProps) => {
  // 提供给MemoryEngine
  const userIdForMem = getDefaultSpaceId()
  const groupIdForMem = mdbId || agentId
  // 状态管理
  const [showDebugInfo, setShowDebugInfo] = useState(false)
  const [inputMessage, setInputMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [isInterrupted, setIsInterrupted] = useState(false)
  const [isSimpleInteraction, setIsSimpleInteraction] = useState(false)
  const [activeInteractionNodeIds, setActiveInteractionNodeIds] = useState<string[]>([])
  const [inputFocused, setInputFocused] = useState(false)
  const streamingMsgTsRef = useRef<number | null>(null)
  const lastErrorSigRef = useRef<string | null>(null)
  const cancelStreamRef = useRef<(() => void) | null>(null)
  const userCancelRequestedRef = useRef(false)

  // 从 saveAgentRequest 读取所有数据（统一数据源）
  const openingRemarks = saveAgentRequest.opening_remarks || ''
  const agentType = saveAgentRequest.agent_type || 'react'
  const workflowsCount = saveAgentRequest.workflows?.length || 0
  const model = saveAgentRequest.model
  const agentName = saveAgentRequest.name
  // agent_version 为空字符串表示草稿状态，执行 API 使用空字符串或 'draft' 均可
  const agentVersion = saveAgentRequest.agent_version || 'draft'

  const { t } = useScopedTranslation('agents.agentEditor.previewDebug.agentDebugChat')

  // 模型未配置的判断
  const modelNotConfigured = !model
  // 模型已被禁用的判断
  const modelDisabled = !isModelActive
  // 聊天被阻止：多工作流模式且没有工作流
  const chatBlocked = agentType === 'workflow' && workflowsCount === 0

  // 创建聊天容器的引用
  const chatContainerRef = useRef<HTMLDivElement>(null)

  // 实时同步开场白：作为第一条助手消息展示与更新
  useEffect(() => {
    const trimmed = openingRemarks.trim()
    setChatHistory(prev => {
      // 当开场白被清空时，移除已有的开场白消息
      if (!trimmed) {
        if (prev.some(m => m.kind === 'opening')) {
          return prev.filter(m => m.kind !== 'opening')
        }
        return prev
      }
      // 非空：更新已存在的开场白内容，若不存在则在顶部插入
      const idx = prev.findIndex(m => m.kind === 'opening')
      if (idx >= 0) {
        const updated = [...prev]
        updated[idx] = { ...updated[idx], content: trimmed }
        return updated
      }
      return [
        {
          role: 'assistant',
          content: trimmed,
          timestamp: Date.now(),
          kind: 'opening',
        },
        ...prev,
      ]
    })
  }, [openingRemarks])

  const appendUserMessage = (content: string) => {
    const msg: ChatMessage = {
      role: 'user',
      content,
      timestamp: Date.now(),
      kind: 'normal',
    }
    setChatHistory(prev => [...prev, msg])
  }

  const appendAssistantStreaming = (initialContent = '') => {
    const ts = Date.now()
    const msg: ChatMessage = {
      role: 'assistant',
      content: initialContent,
      timestamp: ts,
      kind: 'normal',
      detailInfo: { streaming: true },
    }
    setChatHistory(prev => [...prev, msg])
    return ts
  }

  const normalizeStreamEvent = (
    raw: any,
  ): {
    text: string
    type: string
    nodeId?: string
    nodeName?: string
    index?: number
  } | null => {
    if (!raw || typeof raw !== 'object') return null

    const event = raw as any
    const eventType = typeof event.type === 'string' ? event.type : undefined

    const streamPayload = (event as any)._streamPayload
    if (streamPayload) {
      const nodeIdRaw = streamPayload?.node_id ?? streamPayload?.nodeId
      const nodeId = nodeIdRaw != null && String(nodeIdRaw).trim() ? String(nodeIdRaw) : undefined
      const nodeNameRaw = streamPayload?.node_name ?? streamPayload?.nodeName ?? streamPayload?.name
      const nodeName = nodeNameRaw != null && String(nodeNameRaw).trim() ? String(nodeNameRaw) : undefined
      const index = typeof streamPayload?.index === 'number' ? streamPayload.index : undefined
      const text = extractTextFromOutput(streamPayload?.output ?? streamPayload?.answer ?? streamPayload?.output_text)
      if (!text) return null
      return { text, type: eventType || 'workflow', nodeId, nodeName, index }
    }

    const outputText = event.output_text
    if (typeof outputText === 'string' && outputText) {
      const nodeIdRaw = event.node_id ?? event.nodeId
      const nodeId = nodeIdRaw != null && String(nodeIdRaw).trim() ? String(nodeIdRaw) : undefined
      const nodeNameRaw = event.node_name ?? event.nodeName ?? event.name
      const nodeName = nodeNameRaw != null && String(nodeNameRaw).trim() ? String(nodeNameRaw) : undefined
      return { text: outputText, type: eventType || 'agent', nodeId, nodeName }
    }

    // 如果事件本身带有 type 和 output 字段，也按原样透传
    if (eventType && typeof event.output === 'string' && event.output) {
      const nodeIdRaw = event.node_id ?? event.nodeId
      const nodeId = nodeIdRaw != null && String(nodeIdRaw).trim() ? String(nodeIdRaw) : undefined
      const nodeNameRaw = event.node_name ?? event.nodeName ?? event.name
      const nodeName = nodeNameRaw != null && String(nodeNameRaw).trim() ? String(nodeNameRaw) : undefined
      return { text: event.output, type: eventType, nodeId, nodeName }
    }

    return null
  }

  const updateAssistantStreamingContent = (
    ts: number | null,
    incoming: string,
    meta?: { type: string; nodeId?: string; nodeName?: string; index?: number },
  ) => {
    if (!ts) return
    setChatHistory(prev => {
      const idx = prev.findIndex(m => m.timestamp === ts && m.role === 'assistant')
      if (idx === -1) return prev
      const updated = [...prev]
      const msg = updated[idx]

      const safeType = meta?.type || 'agent'
      const safeNodeId = meta?.nodeId
      const safeNodeName = meta?.nodeName
      const safeIndex = meta?.index

      let nextChunks = msg.chunks ? [...msg.chunks] : []

      let existingIdx = -1
      // If index is 0, we force creating a new chunk, so skip searching for existing one.
      if (safeIndex !== 0) {
        // Search from end to find the latest matching chunk
        for (let i = nextChunks.length - 1; i >= 0; i--) {
          const c = nextChunks[i]
          if (c.type === safeType && c.nodeId === safeNodeId) {
            existingIdx = i
            break
          }
        }
      }

      if (existingIdx >= 0) {
        const existing = nextChunks[existingIdx]
        // 直接拼接，不再使用 mergeStreamText
        const newContent = (existing.content || '') + incoming

        nextChunks[existingIdx] = {
          ...existing,
          nodeName: existing.nodeName || safeNodeName,
          content: newContent,
          status: 'streaming',
          index: safeIndex ?? existing.index,
        }
      } else {
        nextChunks.push({
          id: `${Date.now()}_${Math.random().toString(36).slice(2)}`,
          type: safeType,
          nodeId: safeNodeId,
          nodeName: safeNodeName,
          content: incoming,
          status: 'streaming',
          index: safeIndex,
        })
      }

      const aggregated = nextChunks.length > 0 ? nextChunks.map(c => c.content).join('') : (msg.content || '') + incoming
      updated[idx] = { ...msg, content: aggregated, chunks: nextChunks }
      return updated
    })
  }

  const finalizeAssistantStreaming = (ts: number | null) => {
    if (!ts) return
    setChatHistory(prev => {
      const idx = prev.findIndex(m => m.timestamp === ts && m.role === 'assistant')
      if (idx === -1) return prev
      const updated = [...prev]
      const msg = updated[idx]
      const doneChunks = msg.chunks ? msg.chunks.map(c => ({ ...c, status: 'done' as const })) : msg.chunks
      updated[idx] = {
        ...msg,
        chunks: doneChunks,
        detailInfo: { ...(msg.detailInfo || {}), streaming: false },
      }
      return updated
    })
  }

  const finalizeOrRemoveAssistantStreaming = (ts: number | null) => {
    if (!ts) return
    setChatHistory(prev => {
      const idx = prev.findIndex(m => m.timestamp === ts && m.role === 'assistant')
      if (idx === -1) return prev
      const msg = prev[idx]
      const content = (msg.content || '').trim()
      if (content.length > 0) {
        const updated = [...prev]
        const doneChunks = msg.chunks ? msg.chunks.map(c => ({ ...c, status: 'done' as const })) : msg.chunks
        updated[idx] = {
          ...msg,
          chunks: doneChunks,
          detailInfo: { ...(msg.detailInfo || {}), streaming: false },
        }
        return updated
      }
      return prev.filter(m => !(m.timestamp === ts && m.role === 'assistant'))
    })
    streamingMsgTsRef.current = null
  }

  const normalizeErrorSignature = (content: string) => {
    const trimmed = (content || '').trim()
    const withoutCodePrefix = trimmed.replace(/^错误\s*\d+[:：]\s*/i, '')
    return withoutCodePrefix.trim()
  }

  const appendErrorIfNew = (content: string) => {
    const sig = normalizeErrorSignature(content)
    const ignored = ['GraphInterrupt']
    if (ignored.some(k => sig.includes(k))) return
    if (lastErrorSigRef.current !== sig) {
      lastErrorSigRef.current = sig
      setChatHistory(prev => [
        ...prev,
        {
          role: 'assistant',
          content,
          timestamp: Date.now(),
          kind: 'error',
        },
      ])
    }
  }

  const startStreamCycle = () => {
    setIsProcessing(true)
    streamingMsgTsRef.current = appendAssistantStreaming('')
    lastErrorSigRef.current = null
  }

  const endStreamCycle = () => {
    finalizeAssistantStreaming(streamingMsgTsRef.current)
    setIsProcessing(false)
    streamingMsgTsRef.current = null
    cancelStreamRef.current = null
  }

  const handleStreamEvent = (event: any) => {
    const rawData = event && typeof event === 'object' && 'data' in event && (event as any).data ? (event as any).data : event
    const payloadFromTyped = rawData && typeof rawData === 'object' && (rawData as any).type === 'interaction' ? (rawData as any).payload : null
    const interactionPayload = payloadFromTyped || (rawData && typeof rawData === 'object' && 'interaction_node' in rawData ? rawData : null)
    if (interactionPayload && (interactionPayload as any).interaction_node) {
      emitInteractionPrompt(interactionPayload)
      return { interrupted: true }
    }
    if (event.status === 'error') {
      finalizeOrRemoveAssistantStreaming(streamingMsgTsRef.current)
      appendErrorIfNew(formatError(event.error))
      setIsProcessing(false)
      resetInteractionState()
      return { error: true }
    }
    const normalized = normalizeStreamEvent(rawData)
    if (!normalized) return {}
    const ignoreTokens = ['tool_call']
    if (normalized.text && !ignoreTokens.some(t => normalized.text.includes(t))) {
      updateAssistantStreamingContent(streamingMsgTsRef.current, normalized.text, {
        type: normalized.type,
        nodeId: normalized.nodeId,
        nodeName: normalized.nodeName,
        index: normalized.index,
      })
    }
    return {}
  }

  const runExecutionStream = async (
    exec: (payload: any, onEvent: (e: any) => void, onError: (err: any) => void, onDone: () => void) => Promise<() => void>,
    payload: any,
  ) => {
    return new Promise<void>((resolve, reject) => {
      exec(
        payload,
        e => {
          const res = handleStreamEvent(e)
          if (res?.error) return
        },
        err => {
          reject(err)
        },
        () => {
          endStreamCycle()
          resolve()
        },
      )
        .then(close => {
          cancelStreamRef.current = () => {
            try {
              close && close()
            } catch {}
          }
          if (userCancelRequestedRef.current) {
            try {
              cancelStreamRef.current()
            } catch {}
            userCancelRequestedRef.current = false
          }
        })
        .catch(error => {
          reject(error)
        })
    })
  }

  const appendInteractionMessage = (rawData: any) => {
    const msg: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      kind: 'interaction',
      detailInfo: { ...rawData },
    }
    setChatHistory(prev => [...prev, msg])
  }

  const emitInteractionPrompt = (event: any) => {
    const nodeId = event?.interaction_node ? String(event.interaction_node) : ''
    if (nodeId) {
      setActiveInteractionNodeIds(prev => {
        const set = new Set(prev)
        set.add(nodeId)
        return Array.from(set)
      })
    }
    setIsInterrupted(true)

    const ts = streamingMsgTsRef.current
    streamingMsgTsRef.current = null

    try {
      const raw = event?.interaction_msg
      let simple = false
      if (typeof raw === 'string') {
        try {
          const parsed = JSON.parse(raw)
          simple = !(Array.isArray(parsed) || (parsed && typeof parsed === 'object'))
        } catch {
          simple = true
        }
      }
      if (simple) {
        finalizeOrRemoveAssistantStreaming(ts)
        const content = String(event?.interaction_msg || event?.output_text || '')
        setChatHistory(prev => [...prev, { role: 'assistant', content, timestamp: Date.now(), kind: 'normal' }])
        setIsSimpleInteraction(true)
      } else {
        setIsSimpleInteraction(false)
        const interactionData = { ...event, simple: false }

        setChatHistory(prev => {
          const idx = prev.findIndex(m => m.timestamp === ts && m.role === 'assistant')
          if (idx !== -1) {
            const msg = prev[idx]
            const doneChunks = msg.chunks ? msg.chunks.map(c => ({ ...c, status: 'done' as const })) : msg.chunks
            const updatedMsg: ChatMessage = {
              ...msg,
              chunks: doneChunks,
              detailInfo: {
                ...(msg.detailInfo || {}),
                streaming: false,
                ...interactionData,
              },
              kind: 'interaction',
            }
            const updated = [...prev]
            updated[idx] = updatedMsg
            return updated
          }
          // No streaming message found, append new
          const newMsg: ChatMessage = {
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
            kind: 'interaction',
            detailInfo: { ...interactionData },
          }
          return [...prev, newMsg]
        })
      }
    } catch {
      // Fallback for error case: treat as complex interaction
      setIsSimpleInteraction(false)
      const interactionData = { ...event }
      setChatHistory(prev => {
        // Same fallback logic: try to merge if possible, or append
        const idx = prev.findIndex(m => m.timestamp === ts && m.role === 'assistant')
        if (idx !== -1) {
          const msg = prev[idx]
          const doneChunks = msg.chunks ? msg.chunks.map(c => ({ ...c, status: 'done' as const })) : msg.chunks
          const updatedMsg: ChatMessage = {
            ...msg,
            chunks: doneChunks,
            detailInfo: { ...(msg.detailInfo || {}), streaming: false, ...interactionData },
            kind: 'interaction',
          }
          const updated = [...prev]
          updated[idx] = updatedMsg
          return updated
        }
        return [
          ...prev,
          {
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
            kind: 'interaction',
            detailInfo: { ...interactionData },
          },
        ]
      })
    }
    setIsProcessing(false)
  }

  const resetInteractionState = () => {
    setIsInterrupted(false)
    setActiveInteractionNodeIds([])
    setIsSimpleInteraction(false)
  }

  const formatError = (e: any): string => {
    try {
      if (!e) return t('errors.executeFailed')
      if (typeof e === 'string') return e
      if (e && typeof e === 'object' && 'message' in e && e.message) return String(e.message)
      return JSON.stringify(e)
    } catch {
      return String(e)
    }
  }

  // 聊天历史更新时滚动到底部
  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [chatHistory.length])

  /**
   * 发送消息并获取智能体响应
   */
  const handleSendMessage = async () => {
    if (isProcessing) return
    if (modelNotConfigured) return
    if (modelDisabled) return
    if (chatBlocked) return
    const trimmed = inputMessage.trim()
    if (!trimmed) return

    setChatHistory(prev =>
      prev.map(m =>
        m.kind === 'interaction'
          ? {
              ...m,
              detailInfo: { ...(m.detailInfo || {}), isHistorical: true },
            }
          : m,
      ),
    )
    appendUserMessage(trimmed)
    setInputMessage('')
    resetInteractionState()
    startStreamCycle()

    // 记录开始时间，用于计算响应时间
    try {
      await runExecutionStream((payload, onEvent, onError, onDone) => ExecutionService.executionAgent(payload, onEvent, onError, onDone), {
        space_id: getDefaultSpaceId(),
        id: agentId,
        version: agentVersion,
        inputs: {
          query: trimmed,
          conversation_id: agentId,
        },
        conversation_id: agentId,
      })
    } catch (error: any) {
      handleAgentError(error)
    }
  }

  const resumeAgentInteraction = async (userInput: string, nodeId?: string) => {
    const inputObj = JSON.parse(userInput)
    const inputValue = inputObj && typeof inputObj === 'object' && 'input_value' in inputObj ? (inputObj as any).input_value : inputObj
    let hasNewInteraction = false
    setChatHistory(prev =>
      prev.map(m =>
        m.kind === 'interaction'
          ? {
              ...m,
              detailInfo: { ...(m.detailInfo || {}), isHistorical: true },
            }
          : m,
      ),
    )
    startStreamCycle()
    return new Promise<void>((resolve, reject) => {
      ExecutionService.handleAgentUserInput(
        {
          space_id: getDefaultSpaceId(),
          id: agentId,
          version: agentVersion,
          conversation_id: agentId,
          inputs: {
            node_id: nodeId || '',
            input_value: inputValue,
          },
        },
        (event: any) => {
          const res = handleStreamEvent(event)
          if (res?.interrupted) {
            hasNewInteraction = true
            return
          }
          if (res?.error) return
        },
        (error: any) => {
          handleAgentError(error as Error)
          reject(error)
        },
        () => {
          if (nodeId) {
            setActiveInteractionNodeIds(prev => {
              const next = prev.filter(id => id !== nodeId)
              if (next.length === 0) setIsInterrupted(false)
              return next
            })
          } else if (!hasNewInteraction) {
            resetInteractionState()
          }
          endStreamCycle()
          resolve()
        },
      )
        .then(close => {
          cancelStreamRef.current = () => {
            try {
              close && close()
            } catch {}
          }
          if (userCancelRequestedRef.current) {
            try {
              cancelStreamRef.current()
            } catch {}
            userCancelRequestedRef.current = false
          }
        })
        .catch(error => {
          reject(error)
        })
    })
  }
  const handleInlineInteractionSubmit = async (value: string, ts: number) => {
    const targetMsg = chatHistory.find(m => m.timestamp === ts && m.kind === 'interaction')
    const nodeId = (targetMsg?.detailInfo as any)?.interaction_node
    const nodeIdForSubmit = typeof nodeId === 'string' ? nodeId : undefined

    setChatHistory(prev => {
      const idx = prev.findIndex(m => m.timestamp === ts && m.kind === 'interaction')
      if (idx === -1) return prev
      const updated = [...prev]
      const msg = updated[idx]
      updated[idx] = {
        ...msg,
        detailInfo: { ...(msg.detailInfo || {}), submittedValue: value },
      }
      return updated
    })
    try {
      const parsed = JSON.parse(value)
      if (parsed && typeof parsed === 'object') {
        const lines: string[] = []
        for (const k of Object.keys(parsed)) {
          const v = parsed[k]
          const s = typeof v === 'string' ? v : v == null ? '' : String(v)
          if (s && s.trim().length > 0) lines.push(`${k}: ${s}`)
        }
        if (lines.length > 0) appendUserMessage(lines.join('\n'))
      } else if (parsed != null) {
        appendUserMessage(String(parsed))
      }
    } catch {
      if (value) appendUserMessage(String(value))
    }
    if (nodeIdForSubmit) {
      setActiveInteractionNodeIds(prev => {
        const next = prev.filter(id => id !== nodeIdForSubmit)
        if (next.length === 0) setIsInterrupted(false)
        return next
      })
    }
    setIsSimpleInteraction(false)
    const inputEl = document.querySelector<HTMLInputElement>('input[data-agent-chat-input="true"]')
    inputEl?.focus()
    await resumeAgentInteraction(value, nodeIdForSubmit)
  }

  /**
   * 处理智能体错误
   */
  const handleAgentError = (error: Error) => {
    appendErrorIfNew(formatError(error))
    finalizeOrRemoveAssistantStreaming(streamingMsgTsRef.current)
    setIsProcessing(false)
    cancelStreamRef.current = null
    resetInteractionState()
  }

  const handleCancel = () => {
    const cancel = cancelStreamRef.current
    if (cancel) {
      try {
        cancel()
      } catch {}
    } else {
      userCancelRequestedRef.current = true
    }
    finalizeOrRemoveAssistantStreaming(streamingMsgTsRef.current)
    setIsProcessing(false)
    cancelStreamRef.current = null
  }

  return (
    <Paper elevation={0} className="flex flex-col bg-gradient-to-br h-full overflow-x-hidden overflow-y-hidden">
      {/* 头部区域 */}
      <div className="flex items-center justify-between">
        <ActionSlotMount name="debug-title-actions">
          <div className="flex items-center space-x-2">
            {!hideMemoryButton && <MemoryButton userId={userIdForMem} groupId={groupIdForMem} enableLongTerm={enableLongTerm} />}
            <Switch
              checked={showDebugInfo}
              onChange={() => {
                const next = !showDebugInfo
                setShowDebugInfo(next)
                onDebugInfoChange?.(next)
              }}
              size="small"
              color="primary"
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: '#6366F1',
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  backgroundColor: '#818CF8',
                },
              }}
            />
            <span className="text-sm text-gray-600">{t('header.debugInfo')}</span>
          </div>
        </ActionSlotMount>
      </div>
      {/* 主体区域 - 根据showDebugInfo状态决定布局 */}
      <div className={`flex-1 flex ${showDebugInfo ? 'gap-4' : ''} min-h-0`}>
        {/* 聊天消息区域 */}
        <div className={`${showDebugInfo ? 'flex-1' : 'w-full'} flex flex-col min-w-0 min-h-0`}>
          {/* 未配置模型的提示 */}
          {modelNotConfigured && (
            <div className="mx-4 mt-4 mb-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5 text-amber-400 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-amber-800">{t('tips.modelNotConfiguredTitle')}</h3>
                  <p className="mt-1 text-sm text-amber-700">{t('tips.modelNotConfiguredDescription')}</p>
                </div>
              </div>
            </div>
          )}
          {/* 模型已被禁用的提示 */}
          {modelDisabled && !modelNotConfigured && (
            <div className="mx-4 mt-4 mb-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5 text-red-400 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">{t('tips.modelDisabledTitle')}</h3>
                  <p className="mt-1 text-sm text-red-700">{t('tips.modelDisabledDescription')}</p>
                </div>
              </div>
            </div>
          )}
          <div ref={chatContainerRef} className="flex-1 bg-white p-4 mb-4 overflow-y-auto overflow-x-hidden">
            <ChatMessageList
              messages={chatHistory}
              onSubmitInteraction={handleInlineInteractionSubmit}
              interactionNodeIds={activeInteractionNodeIds}
              inputFocused={inputFocused}
              agentName={agentName}
            />
          </div>

          {/* 输入区域（固定在底部） */}
          <AgentOperationsBar
            value={inputMessage}
            onChange={setInputMessage}
            onSend={handleSendMessage}
            onCancel={handleCancel}
            disabled={!inputMessage.trim() || isProcessing || modelNotConfigured || modelDisabled || chatBlocked}
            inputDisabled={modelNotConfigured || modelDisabled || chatBlocked}
            onClearChat={async () => {
              // 重置交互状态
              resetInteractionState()
              // 清空聊天记录
              const trimmed = openingRemarks.trim()
              setChatHistory(() => {
                if (!trimmed) return []
                return [
                  {
                    role: 'assistant',
                    content: trimmed,
                    timestamp: Date.now(),
                    kind: 'opening',
                  },
                ]
              })
              // 重建agent实例 - 调用后端reset接口
              try {
                await ExecutionService.resetAgentInstance({
                  space_id: getDefaultSpaceId(),
                  id: agentId,
                  version: agentVersion,
                  inputs: {
                    query: '',
                    conversation_id: agentId,
                  },
                  conversation_id: agentId,
                })
              } catch (error) {
                console.error('重建agent实例失败:', error)
              }
            }}
            isProcessing={isProcessing}
            onInputFocusChange={setInputFocused}
            placeholder={
              modelNotConfigured
                ? t('placeholders.configModelFirst')
                : modelDisabled
                  ? t('placeholders.modelDisabled')
                  : chatBlocked
                    ? t('placeholders.addWorkflowFirst')
                    : isInterrupted && !isSimpleInteraction
                      ? t('placeholders.waitInputComplex')
                      : isInterrupted
                        ? t('placeholders.waitInputSimple')
                        : t('placeholders.inputMessage')
            }
          />
        </div>

        {/* 调试信息面板 */}
        {showDebugInfo && <AgentDebugPanel agentId={agentId} agentVersion={agentVersion} agentName={agentName} />}
      </div>
    </Paper>
  )
}

/**
 * 聊天消息列表组件
 */
const ChatMessageList = ({
  messages,
  onSubmitInteraction,
  interactionNodeIds,
  inputFocused,
  agentName,
}: {
  messages: ChatMessage[]
  onSubmitInteraction?: (value: string, ts: number) => void
  interactionNodeIds?: string[]
  inputFocused?: boolean
  agentName?: string
}) => {
  const activeNodeIds = interactionNodeIds || []

  return (
    <div className="space-y-4">
      {messages.map((message, index) => (
        <ChatMessageItem
          key={`${message.role}-${message.timestamp}-${index}`}
          message={message}
          onSubmitInteraction={onSubmitInteraction}
          isActiveInteraction={message.kind === 'interaction' && !message.detailInfo?.submittedValue && !(message.detailInfo as any)?.isHistorical}
          inputFocused={inputFocused}
          agentName={agentName}
        />
      ))}
    </div>
  )
}

/**
 * 单个聊天消息组件
 */
const ChatMessageItem = memo(
  ({
    message,
    onSubmitInteraction,
    isActiveInteraction,
    inputFocused,
    agentName,
  }: {
    message: ChatMessage
    onSubmitInteraction?: (value: string, ts: number) => void
    isActiveInteraction?: boolean
    inputFocused?: boolean
    agentName?: string
  }) => {
    const { t } = useScopedTranslation('agents.agentEditor.previewDebug.agentDebugChat')
    return (
      <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
        <div className={`${message.kind === 'interaction' ? 'w-[85%]' : 'max-w-[85%]'} min-w-0 ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
          {message.role === 'assistant' && (
            <div className="flex items-center space-x-2 mb-2">
              <div className="w-6 h-6 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">AI</span>
              </div>
              <span className="text-sm text-gray-600 font-medium">{agentName || t('messages.assistantLabel')}</span>
            </div>
          )}

          <MessageRenderer
            message={message}
            onSubmitInteraction={onSubmitInteraction}
            interactionDisabled={message.kind === 'interaction' && !isActiveInteraction}
            inputFocused={inputFocused}
          />

          {message.role === 'user' && (
            <div className="flex items-center justify-end space-x-2 mt-2">
              <div className="w-5 h-5 bg-gradient-to-br from-blue-400 to-indigo-500 rounded-full flex items-center justify-center">
                <span className="text-white text-xs font-bold">{t('messages.userLabel')}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  },
)

ChatMessageItem.displayName = 'ChatMessageItem'

export default AgentDebugChat
