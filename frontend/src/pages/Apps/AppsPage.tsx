import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Copy, Trash2, RefreshCw, History } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { MentionItem, DEFAULT_AGENTS, DEFAULT_RESOURCES } from './components/MentionPicker'
import AgentConfigDialog, { DeepSearchConfig } from './components/AgentConfigDialog'
import ChatInputArea from './components/ChatInputArea'
import ModelPicker from './components/ModelPicker'
import { useModels, getToken, deepsearchHeartbeatService } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { useConversationStore, MessageType, TaskStatus, AgentType, type MessageItems, OUTLINE_INTERACTION_MAX_ROUNDS } from '../../stores/useConversationStore'
import { getDefaultSpaceId } from '../../utils/spaceUtils'
import SSERecorder from '../../utils/sseRecorder'
import PlaybackPanel from '../../components/Conversation/PlaybackPanel'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import ConversationLimitDialog from '../../components/Common/ConversationLimitDialog'
import { conversationEventEmitter, conversationDB } from '../../utils/conversationDB'
import type { MessageInputRef } from './components/MessageInput'
import { copyToClipboard, STORAGE_KEYS, storage, getAgentConfigKeys } from './utils/utils'
import { DEFAULT_DEEPSEARCH_CONFIG } from './utils/deepsearchConstants'
import { getSuggestionsByAgent } from './constants/suggestions'
import { TEXT_BASE, TEXT_SMALL, FONT_FAMILY } from './constants/styles'
import type { Message } from './types'
import { SystemMessageItem } from '../../components/Conversation'
import ResultPanel from '../../components/Conversation/ResultPanel'
import ConversationHistorySidebar from './components/ConversationHistorySidebar'

// ==================== 开发调试配置 ====================
// 从环境变量读取，默认为 false（生产环境）
// 在 .env 中设置 VITE_ENABLE_SSE_DEBUG=true 来启用
const ENABLE_SSE_DEBUG = import.meta.env.VITE_ENABLE_SSE_DEBUG === 'true'

// ==================== 主页面组件 ====================

const AppsPage: React.FC = () => {
  const { user } = useAuthStore()
  const { t } = useTranslation()
  // Snackbar 支持 - 必须在组件顶层调用以监听全局事件
  const { snackbar, closeSnackbar } = useUnifiedSnackbar()

  const [inputValue, setInputValue] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [selectedModelId, setSelectedModelId] = useState<number>(-1)
  const [selectedAgent, setSelectedAgent] = useState<MentionItem | null>(null)
  const [hasConversation, setHasConversation] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [isSending, setIsSending] = useState(false)

  // ===== DeepSearch 插件状态（最小化侵入） =====
  const [isDeepSearchMode, setIsDeepSearchMode] = useState(false)
  const [abortController, setAbortController] = useState<AbortController | null>(null)
  const [showPlaybackPanel, setShowPlaybackPanel] = useState(false)
  const [deepsearchServiceAvailable, setDeepsearchServiceAvailable] = useState<boolean | null>(null)
  const [checkingDeepsearch, setCheckingDeepsearch] = useState(false)

  // ===== 对话限制对话框状态 =====
  const [limitDialogOpen, setLimitDialogOpen] = useState(false)
  const [limitDialogType, setLimitDialogType] = useState<'count-warning' | 'storage-warning' | 'delete-confirm'>('count-warning')
  const [limitDialogData, setLimitDialogData] = useState<{
    currentCount?: number
    maxCount?: number
    currentSize?: number
    maxSize?: number
    warningThreshold?: number
    oldestConversation?: {
      id: string
      title: string
      createdAt: number
    }
    deleteReason?: string
    deleteDetails?: string
  }>({})
  const [pendingConversationCreate, setPendingConversationCreate] = useState<{
    title: string
    config: any
  } | null>(null)

  // ConversationStore 用于 DeepSearch 模式
  // 优化消息列表计算逻辑避免无限循环
  // 使用独立订阅状态和useMemo替代getMessageItemsByConversationId方法，防止因对象创建导致的重复渲染

  // 获取状态（分别订阅各个值，避免对象引用问题）
  const currentConversationId = useConversationStore(state => state.currentConversationId)
  const selectedResultMessageId = useConversationStore(state => state.selectedResultMessageId)
  const isLoading = useConversationStore(state => state.isLoading)
  const sseProcessingQueue = useConversationStore(state => state.sseProcessingQueue)
  const SESSION_CONVERSATION_ID = useConversationStore(state => state.SESSION_CONVERSATION_ID)

  // 订阅 conversation 来触发 messageItemsList 重新计算
  const conversation = useConversationStore(state =>
    state.currentConversationId ? state.conversationsMap.get(state.currentConversationId) : undefined
  )

  // 计算 SSE 是否正在传输
  // isSending: 发起请求时的状态
  // isLoading: 从 store 读取的加载状态
  // sseProcessingQueue: SSE 事件队列是否正在处理
  const isStreaming = isSending || isLoading || sseProcessingQueue

  // 订阅 messageItemsMap 来触发 messageItemsList 重新计算
  const messageItemsMap = useConversationStore(state => state.messageItemsMap)

  // 使用 useMemo 计算消息列表（只依赖原始状态值的引用变化）
  const messageItemsList = useMemo(() => {
    if (!currentConversationId || !conversation) return []

    return conversation.messageItemsIds
      .map(id => messageItemsMap.get(id))
      .filter((items): items is MessageItems => items !== undefined)
      .sort((a, b) => a.createdAt - b.createdAt)
  }, [currentConversationId, conversation, messageItemsMap])

  // 获取方法（稳定的引用）
  const createConversation = useConversationStore(state => state.createConversation)
  const checkCreateConversationWarning = useConversationStore(state => state.checkCreateConversationWarning)
  const switchConversation = useConversationStore(state => state.switchConversation)
  const getConversationById = useConversationStore(state => state.getConversationById)
  const addUserMessage = useConversationStore(state => state.addUserMessage)
  const addSystemMessage = useConversationStore(state => state.addSystemMessage)
  const setLoading = useConversationStore(state => state.setLoading)
  const setSelectedResultMessageId = useConversationStore(state => state.setSelectedResultMessageId)
  const clearAll = useConversationStore(state => state.clearAll)
  const clearCurrentConversation = useConversationStore(state => state.clearCurrentConversation)
  const initializeFromDB = useConversationStore(state => state.initializeFromDB)

  // ===== 处理创建对话前警告 =====
  const handleCreateConversation = async (title: string, config: any) => {
    // 检查是否需要警告
    const warning = await checkCreateConversationWarning()
    if (warning && warning.type) {
      // 需要显示警告对话框
      setPendingConversationCreate({ title, config })
      setLimitDialogType(warning.type)
      setLimitDialogData({
        currentCount: warning.currentCount,
        maxCount: warning.maxCount,
        currentSize: warning.currentSize,
        maxSize: warning.maxSize,
        warningThreshold: warning.warningThreshold,
        oldestConversation: warning.oldestConversation,
      })
      setLimitDialogOpen(true)
      return null // 暂时不创建，等待用户确认
    }
    // 不需要警告，直接创建
    return createConversation(title, config)
  }

  // 处理对话框确认
  const handleLimitDialogConfirm = async () => {
    if (limitDialogType === 'delete-confirm') {
      // 删除确认：通知 conversationDB 继续删除
      conversationDB.setDeleteConfirmResult(true)
      setLimitDialogOpen(false)
      return
    }

    if (pendingConversationCreate) {
      // 对于数量警告：用户确认后，先删除最旧的对话，再创建新对话
      if (limitDialogType === 'count-warning' && limitDialogData.oldestConversation) {
        try {
          // 从 store 和 IndexDB 中删除最旧的对话
          await useConversationStore.getState().deleteConversation(limitDialogData.oldestConversation.id)
          console.log('[AppsPage] Deleted oldest conversation before creating new one:', limitDialogData.oldestConversation.id)
        } catch (error) {
          console.error('[AppsPage] Failed to delete oldest conversation:', error)
        }
      }

      // 创建新对话
      const conversationId = createConversation(pendingConversationCreate.title, pendingConversationCreate.config)
      setPendingConversationCreate(null)
      setLimitDialogOpen(false)
      return conversationId
    }
    // 对于存储警告，只是提示，不需要创建
    setLimitDialogOpen(false)
  }

  // 处理对话框取消
  const handleLimitDialogCancel = () => {
    if (limitDialogType === 'delete-confirm') {
      // 删除确认：通知 conversationDB 取消删除
      conversationDB.setDeleteConfirmResult(false)
    }

    setPendingConversationCreate(null)
    setLimitDialogOpen(false)
  }

  // 智能体配置弹窗状态
  const [configDialogOpen, setConfigDialogOpen] = useState(false)
  const [agentConfigs, setAgentConfigs] = useState<Record<string, DeepSearchConfig>>({})
  // 待选择的智能体（需要先配置才能选中）
  const [pendingAgent, setPendingAgent] = useState<MentionItem | null>(null)
  // 是否是首次配置模式（配置完成后才选中智能体）
  const [isFirstConfigMode, setIsFirstConfigMode] = useState(false)

  // 模型选择弹窗状态
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [modelPickerPosition, setModelPickerPosition] = useState<{ x: number; y: number } | null>(null)
  const modelButtonRef = useRef<HTMLButtonElement>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatInputRef = useRef<MessageInputRef>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // 用户滚动状态：true = 用户向上滚动了（不在底部），false = 用户在底部
  const [isUserScrolled, setIsUserScrolled] = useState(false)

  // 从后端获取模型列表
  const { data: modelsData, isLoading: modelsLoading } = useModels({
    spaceId: user?.spaceId || getDefaultSpaceId(),
    is_active: true,
    size: 100,
  })

  // 提取模型名称列表和 ID 映射
  const models = modelsData?.items?.map(model => model.name) || []
  const modelIdMap = React.useMemo(() => {
    const map = new Map<string, number>()
    modelsData?.items?.forEach(model => {
      if (model.id !== undefined) {
        map.set(model.name, Number(model.id))
      }
    })
    return map
  }, [modelsData])

  // 转换模型数据为 ModelSelector 需要的格式
  const availableModels = React.useMemo(() => {
    if (!modelsData?.items) return []
    return modelsData.items.map(model => ({
      tags: model.tags || [],
      icon: '',
      openModel: {
        model_id: String(model.id),
        name: model.name,
        desc: model.description || '',
        workspace_id: '',
        param_config: { param_schemas: [] },
      },
      series: {
        icon: '',
        name: model.model_type || '',
        vendor: model.provider || '',
      },
      model_from: model.is_system_model ? 'config' : 'db',
    }))
  }, [modelsData])

  // 从 localStorage 恢复对话状态和智能体配置
  useEffect(() => {
    const savedData = storage.get<{ messages: Message[], inputValue: string, hasConversation: boolean, selectedAgent: MentionItem | null }>(STORAGE_KEYS.APPS_PAGE_STATE)
    if (savedData) {
      if (savedData.messages && savedData.messages.length > 0) {
        setMessages(savedData.messages)
        setHasConversation(savedData.hasConversation || true)
      }
      if (savedData.inputValue) {
        setInputValue(savedData.inputValue)
      }
      if (savedData.selectedAgent) {
        setSelectedAgent(savedData.selectedAgent)
      }
    }
  }, [])

  // 从 localStorage 恢复智能体配置（按 spaceId 隔离）
  useEffect(() => {
    const spaceId = user?.spaceId
    if (!spaceId) return

    const configKey = STORAGE_KEYS.AGENT_CONFIGS(spaceId)
    const savedConfigs = storage.get<Record<string, DeepSearchConfig>>(configKey)
    if (savedConfigs) {
      setAgentConfigs(savedConfigs)
    } else {
      // 如果没有保存的配置，使用空配置
      setAgentConfigs({})
    }
  }, [user?.spaceId])

  // 当 agentConfigs.deepsearch.generalModelId 变化时，同步到 selectedModelId（反向同步）
  useEffect(() => {
    const deepsearchConfig = agentConfigs['deepsearch']
    if (deepsearchConfig?.generalModelId) {
      const modelId = Number(deepsearchConfig.generalModelId)
      if (modelId !== selectedModelId && modelId !== -1) {
        setSelectedModelId(modelId)
        // 同时需要更新 selectedModel 字符串
        const modelName = Array.from(modelIdMap.entries())
          .find(([_, id]) => id === modelId)?.[0]
        if (modelName) {
          setSelectedModel(modelName)
        }
      }
    }
  }, [agentConfigs['deepsearch']?.generalModelId, modelIdMap, selectedModelId])

  // 从 IndexDB 初始化对话数据
  useEffect(() => {
    initializeFromDB()
  }, [])

  // 保存对话状态到 localStorage
  useEffect(() => {
    storage.set(STORAGE_KEYS.APPS_PAGE_STATE, {
      messages,
      inputValue,
      hasConversation,
      selectedAgent,
    })
  }, [messages, inputValue, hasConversation, selectedAgent])

  // 保存智能体配置到 localStorage（按 spaceId 隔离）
  useEffect(() => {
    const spaceId = user?.spaceId
    if (!spaceId) return

    const configKey = STORAGE_KEYS.AGENT_CONFIGS(spaceId)
    storage.set(configKey, agentConfigs)
  }, [agentConfigs, user?.spaceId])

  // 当模型列表加载完成后，设置默认选中第一个模型
  useEffect(() => {
    if (models.length > 0 && !selectedModel) {
      const firstModel = models[0]
      setSelectedModel(firstModel)
      setSelectedModelId(modelIdMap.get(firstModel) || -1)
    }
  }, [models, selectedModel, modelIdMap])

  // ===== DeepSearch 模式检测 =====
  useEffect(() => {
    const isDeepSearch = selectedAgent?.id === 'deepsearch'
    setIsDeepSearchMode(isDeepSearch)

    // 不在这里自动创建 conversation
    // 改为只在发送消息时才创建，避免产生空对话
  }, [selectedAgent])

  // ===== 对话状态同步 =====
  // 当 currentConversationId 变化时，同步本地 hasConversation 状态
  useEffect(() => {
    const hasActiveConversation = !!currentConversationId
    setHasConversation(hasActiveConversation)

    if (!hasActiveConversation) {
      // 如果清空了对话，也清空 selectedAgent
      setSelectedAgent(null)
    } else {
      // 如果有对话，根据对话的 agentType 自动设置智能体
      const conversation = getConversationById(currentConversationId)
      if (conversation && conversation.config?.agentType) {
        const matchedAgent = DEFAULT_AGENTS.find(a => a.id === conversation.config.agentType)
        if (matchedAgent) {
          setSelectedAgent(matchedAgent)
        }
      }
    }
  }, [currentConversationId])

  // ===== 用户空间切换监听 =====
  // 使用 ref 跟踪上次的 spaceId，避免初始加载时误清空
  const prevSpaceIdRef = useRef<string | null>(null)

  useEffect(() => {
    const currentSpaceId = user?.spaceId || null
    const prevSpaceId = prevSpaceIdRef.current

    // 只在 spaceId 真正改变时清空（跳过初始值 null -> spaceId）
    if (currentSpaceId && prevSpaceId && currentSpaceId !== prevSpaceId) {
      console.log('[AppsPage] User space changed:', prevSpaceId, '->', currentSpaceId)

      // 清空其他用户的智能体配置，保留当前用户的配置
      const otherUserKeys = getAgentConfigKeys(currentSpaceId)
      otherUserKeys.forEach(key => localStorage.removeItem(key))
      console.log('[AppsPage] Cleared agent configs for other users:', otherUserKeys)

      // // 清空所有对话数据, 暂时不清空所有对话数据
      // clearAll()
      // // 清空本地对话状态
      // setHasConversation(false)
      // setMessages([])
      // setInputValue('')
      // setSelectedAgent(null)

      // 重置智能体配置为空，等待从新 spaceId 加载
      setAgentConfigs({})
    }

    prevSpaceIdRef.current = currentSpaceId
  }, [user?.spaceId, clearAll])

  // 根据当前选择的智能体获取建议提示词
  const currentSuggestions = selectedAgent
    ? getSuggestionsByAgent(selectedAgent.id, t)
    : []

  // 智能体列表（架子数据）
  const [agents] = useState<MentionItem[]>(DEFAULT_AGENTS)

  // 资源列表（架子数据）
  const [resources] = useState<MentionItem[]>(DEFAULT_RESOURCES)

  // ===== 滚动状态检测 =====
  // 监听滚动事件，判断用户是否向上滚动（不在底部）
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      // 距离底部的阈值（像素）
      const THRESHOLD = 100
      const isNearBottom = scrollHeight - scrollTop - clientHeight < THRESHOLD

      // 只有当状态真正改变时才更新（避免不必要的重渲染）
      setIsUserScrolled(prev => {
        if (prev && isNearBottom) {
          // 用户从向上滚动状态回到了底部附近
          return false
        } else if (!prev && !isNearBottom) {
          // 用户从底部向上滚动了
          return true
        }
        return prev
      })
    }

    // 添加滚动监听器
    container.addEventListener('scroll', handleScroll, { passive: true })

    // 初始化检查一次
    handleScroll()

    return () => {
      container.removeEventListener('scroll', handleScroll)
    }
  }, [])

  // ===== 辅助函数：滚动到底部 =====
  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const container = messagesContainerRef.current
    if (!container) return

    // 使用 scrollTo 直接滚动到容器的最底部
    container.scrollTo({
      top: container.scrollHeight,
      behavior: behavior
    })
  }

  // 自动滚动到底部（智能判断：只在用户位于底部时才自动滚动）
  useEffect(() => {
    if (hasConversation && !isUserScrolled) {
      scrollToBottom('smooth')
    }
  }, [messages, hasConversation, isDeepSearchMode, isUserScrolled]) // ⚠️ 移除 messageItemsList 依赖

  // DeepSearch 模式：切换对话时滚动到底部
  useEffect(() => {
    if (isDeepSearchMode && currentConversationId && messageItemsList.length > 0) {
      // 延迟一帧确保 DOM 更新完成
      requestAnimationFrame(() => {
        scrollToBottom('auto')
      })
    }
  }, [currentConversationId]) // ⚠️ 只依赖 currentConversationId，不依赖 messageItemsList.length

  // DeepSearch 模式：监听消息更新并自动滚动
  useEffect(() => {
    if (isDeepSearchMode && hasConversation && !isUserScrolled && messageItemsList.length > 0) {
      const timer = setTimeout(() => {
        scrollToBottom('smooth')
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [isDeepSearchMode, hasConversation, isUserScrolled, messageItemsList.length])

  // ===== 大纲交互接受事件监听 =====
  const pendingOutlineInteraction = useConversationStore(state => state.pendingOutlineInteraction)
  const clearPendingOutlineInteraction = useConversationStore(state => state.clearPendingOutlineInteraction)
  
  useEffect(() => {
    if (!pendingOutlineInteraction) return

    const { userMessage, backendMessage, interruptFeedback } = pendingOutlineInteraction

    console.log('[AppsPage] Received outline-interaction-accept:', pendingOutlineInteraction)

    clearPendingOutlineInteraction()

    handleDeepSearchSend(userMessage, {
      interrupt_feedback: interruptFeedback || 'accepted',
      backend_message: backendMessage,
    })
  }, [pendingOutlineInteraction])

  // ===== SSE 回放事件监听 =====
  useEffect(() => {
    const handlePlaybackEvent = (event: Event) => {
      const customEvent = event as CustomEvent<{ data: any; conversationId: string }>
      const { data, conversationId } = customEvent.detail

      // 将回放的 SSE 事件转发到 ConversationStore
      useConversationStore.getState().handleSSEMessage(data, conversationId)
    }

    window.addEventListener('sse-playback-event', handlePlaybackEvent)

    return () => {
      window.removeEventListener('sse-playback-event', handlePlaybackEvent)
    }
  }, [])

  // ===== 监听 IndexDB 存储警告和删除确认事件 =====
  useEffect(() => {
    const handleStorageWarning = (event: any) => {
      console.log('[AppsPage] Received storage-limit-warning event:', event)
      setLimitDialogType('storage-warning')
      setLimitDialogData({
        currentSize: event.currentSize,
        maxSize: event.maxSize,
        warningThreshold: event.warningThreshold,
        oldestConversation: event.oldestConversation,
      })
      setLimitDialogOpen(true)
    }

    const handleCountWarning = (event: any) => {
      console.log('[AppsPage] Received count-limit-warning event:', event)
      setLimitDialogType('count-warning')
      setLimitDialogData({
        currentCount: event.currentCount,
        maxCount: event.maxCount,
        oldestConversation: event.oldestConversation,
      })
      setLimitDialogOpen(true)
    }

    const handleDeleteConfirm = (event: any) => {
      console.log('[AppsPage] Received before-delete-conversation event:', event)
      setLimitDialogType('delete-confirm')
      setLimitDialogData({
        deleteReason: event.reason,
        deleteDetails: event.details,
        oldestConversation: event.oldestConversation ? {
          id: event.oldestConversation.id,
          title: event.oldestConversation.title,
          createdAt: event.oldestConversation.createdAt,
        } : undefined,
      })
      setLimitDialogOpen(true)
    }

    // 注册事件监听器
    conversationEventEmitter.on('storage-limit-warning', handleStorageWarning)
    conversationEventEmitter.on('count-limit-warning', handleCountWarning)
    conversationEventEmitter.on('before-delete-conversation', handleDeleteConfirm)

    return () => {
      // 清理事件监听器
      conversationEventEmitter.off('storage-limit-warning', handleStorageWarning)
      conversationEventEmitter.off('count-limit-warning', handleCountWarning)
      conversationEventEmitter.off('before-delete-conversation', handleDeleteConfirm)
    }
  }, [])

  // ===== SSE超时检测: 页面加载时检查未完成消息 =====
  useEffect(() => {
    if (currentConversationId && isDeepSearchMode) {
      const hasIncomplete = useConversationStore.getState().checkAndMarkIncompleteAsFailed()
      if (hasIncomplete) {
        console.log('[AppsPage] Marked incomplete messages as FAILED on page load')
      }
    }
  }, [currentConversationId, isDeepSearchMode])

  // ===== 组件卸载时清理SSE超时监控 =====
  useEffect(() => {
    return () => {
      useConversationStore.getState().stopSSETimeoutMonitor()
    }
  }, [])

  // 删除消息（删除用户消息及其下一条AI回复）
  const handleDeleteMessage = (messageId: string) => {
    setMessages(prev => {
      const messageIndex = prev.findIndex(m => m.id === messageId)
      if (messageIndex === -1) return prev

      const message = prev[messageIndex]
      if (message.isUser) {
        // 如果是用户消息，删除该消息和下一条AI回复（如果存在）
        const nextMessage = prev[messageIndex + 1]
        if (nextMessage && !nextMessage.isUser) {
          // 删除用户消息和下一条AI回复
          return prev.filter((_, idx) => idx !== messageIndex && idx !== messageIndex + 1)
        } else {
          // 只删除用户消息
          return prev.filter((_, idx) => idx !== messageIndex)
        }
      } else {
        // 如果是AI消息，只删除该AI消息
        return prev.filter(m => m.id !== messageId)
      }
    })
  }

  // 重新发送（普通模式功能）
  const handleRegenerate = async (aiMessageId: string) => {
    // 模拟重新生成
    const aiMessage: Message = {
      id: Date.now().toString(),
      content: t('apps.chat.featureNotImplemented'),
      isUser: false,
      status: 'sent',
    }
    setMessages(prev => [...prev, aiMessage])
  }

  const handleSendMessage = async () => {
    if (inputValue.trim() && !isStreaming && selectedAgent) {
      const messageToSend = inputValue
      setInputValue('')

      // 重置滚动状态，确保新消息显示时能滚动到底部
      setIsUserScrolled(false)

      // ===== DeepSearch 插件模式检测 =====
      if (isDeepSearchMode) {
        // DeepSearch 模式：关闭旧的报告面板
        setSelectedResultMessageId(null)
        // 使用 ConversationStore 和 SSE 处理
        setHasConversation(true)
        await handleDeepSearchSend(messageToSend)
        return
      }

      // ===== 普通模式：显示用户消息 + mock 回复 =====
      setHasConversation(true)

      // 添加用户消息
      const userMessage: Message = {
        id: Date.now().toString(),
        content: messageToSend,
        isUser: true,
        status: 'sent',
      }
      setMessages(prev => [...prev, userMessage])

      // 添加 AI 回复
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: t('apps.chat.featureNotImplemented'),
        isUser: false,
        status: 'sent',
        modelName: selectedModel,
      }
      setMessages(prev => [...prev, aiMessage])
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion)
    chatInputRef.current?.focus()
  }

  // 处理智能体选择（首次配置弹出配置弹窗，非首次配置直接选中）
  const handleAgentSelect = (agent: MentionItem) => {
    // 如果是 DeepSearch 智能体，总是检查服务状态
    if (agent.id === 'deepsearch') {
      // 如果正在检查心跳，避免重复检查
      if (checkingDeepsearch) {
        setPendingAgent(agent)
        return
      }

      // 总是重新检查心跳，确保获取最新状态
      // 这修复了 stale state 问题（服务从可用变为不可用时）
      checkDeepsearchHeartbeatCallback()
      // 暂时保存待选择的智能体，等心跳检查完成后再处理
      setPendingAgent(agent)
      return
    }

    // 其他智能体：检查该智能体是否已有配置
    const hasConfig = agentConfigs[agent.id] !== undefined

    if (!hasConfig) {
      // 首次配置：跳转到配置界面
      setPendingAgent(agent)
      setIsFirstConfigMode(true)
      setConfigDialogOpen(true)
    } else {
      // 已有配置：直接选中智能体
      setSelectedAgent(agent)
    }
  }

  // 处理智能体配置
  const handleAgentConfig = () => {
    // 已选中的智能体配置，不是首次配置模式
    setIsFirstConfigMode(false)
    setConfigDialogOpen(true)
  }

  // 保存智能体配置
  const handleSaveAgentConfig = (agentId: string, config: DeepSearchConfig) => {
    setAgentConfigs(prev => ({
      ...prev,
      [agentId]: config,
    }))

    // 保存配置后选中该智能体
    if (pendingAgent) {
      setSelectedAgent(pendingAgent)
      setPendingAgent(null)
      setIsFirstConfigMode(false)
    }
  }

  // 取消选择智能体
  const handleAgentDeselect = () => {
    setSelectedAgent(null)
  }

  // 检查 DeepSearch 服务心跳
  const checkDeepsearchHeartbeatCallback = useCallback(async () => {
    setCheckingDeepsearch(true)
    try {
      const result = await deepsearchHeartbeatService.checkHeartbeat()
      setDeepsearchServiceAvailable(result.status === 'available')
    } catch (error) {
      setDeepsearchServiceAvailable(false)
    } finally {
      setCheckingDeepsearch(false)
    }
  }, [])

  // 处理资源选择
  const handleResourceSelect = (resource: MentionItem) => {
    // TODO: 后续可以实现资源选择逻辑
  }

  // 当选择 DeepSearch 智能体时，自动进行心跳检测
  useEffect(() => {
    // 确保 selectedAgent 存在且是 deepsearch 时才检测
    if (selectedAgent && selectedAgent.id === 'deepsearch') {
      checkDeepsearchHeartbeatCallback()
    } else {
      setDeepsearchServiceAvailable(null)
    }
  }, [selectedAgent?.id, checkDeepsearchHeartbeatCallback])

  // 心跳检查完成后，处理待选择的智能体
  useEffect(() => {
    if (pendingAgent && deepsearchServiceAvailable !== null && !checkingDeepsearch) {
      if (pendingAgent.id === 'deepsearch') {
        if (deepsearchServiceAvailable === false) {
          // 服务不可用：选中智能体以显示警告
          setSelectedAgent(pendingAgent)
          setPendingAgent(null)
        } else {
          // 服务可用：检查配置
          const hasConfig = agentConfigs[pendingAgent.id] !== undefined
          if (!hasConfig) {
            // 无配置：打开配置弹窗（使用 pendingAgent 作为 agent prop）
            // 不选中智能体，避免触发心跳检查 useEffect
            setIsFirstConfigMode(true)
            setConfigDialogOpen(true)
            // 注意：这里不清除 pendingAgent，等用户保存配置或关闭弹窗后再清除
          } else {
            // 有配置：直接选中智能体
            setSelectedAgent(pendingAgent)
            setPendingAgent(null)
          }
        }
      }
    }
  }, [pendingAgent, deepsearchServiceAvailable, checkingDeepsearch])

  // 处理文件上传
  const handleFileUpload = (files: FileList) => {
    // 将文件名添加到输入框
    // 移除末尾的 #，然后添加文件引用
    let newValue = inputValue
    if (newValue.endsWith('#')) {
      newValue = newValue.slice(0, -1)
    }

    // 为每个文件添加引用: #[文件名]
    const fileReferences = Array.from(files).map(file => `#[${file.name}]`)

    // 更新输入框的值
    setInputValue(newValue + fileReferences.join(' ') + ' ')
    chatInputRef.current?.focus()
  }

  // 处理模型按钮点击
  const handleModelButtonClick = () => {
    const button = modelButtonRef.current
    if (!button) return

    const rect = button.getBoundingClientRect()
    setModelPickerPosition({
      x: rect.left,
      y: rect.bottom + 5,
    })
    setShowModelPicker(true)
  }

  // 处理模型选择
  const handleModelSelect = (model: string) => {
    setSelectedModel(model)
    const modelId = modelIdMap.get(model) || -1
    setSelectedModelId(modelId)
    setShowModelPicker(false)

    // 同步到智能体配置的通用模型（仅对 deepsearch 智能体）
    if (selectedAgent?.id === 'deepsearch' && modelId !== -1) {
      setAgentConfigs(prev => ({
        ...prev,
        deepsearch: {
          ...prev['deepsearch'],
          generalModelId: String(modelId),
        }
      }))
    }
  }

  // 发起新对话
  const handleNewConversation = () => {
    // 如果有正在进行的 SSE，先中断
    if (abortController) {
      abortController.abort()
      setAbortController(null)
    }

    // 清除选择的结果面板
    setSelectedResultMessageId(null)
    // 清空当前 conversationId（useEffect 会自动同步其他状态）
    clearCurrentConversation()
    // 清空本地 UI 状态
    setMessages([])
    setInputValue('')
  }

  // 切换历史对话
  const handleConversationSelect = async (conversationId: string) => {
    // 如果有正在进行的 SSE，先中断
    if (abortController) {
      abortController.abort()
      setAbortController(null)
    }

    // 清除选择的结果面板（修复bug：切换对话时需要清除，否则会导致页面空白）
    setSelectedResultMessageId(null)

    // 切换对话（异步加载）
    await switchConversation(conversationId)

    // ===== 检查新对话是否有未完成的消息 =====
    const conversation = getConversationById(conversationId)
    if (conversation?.config?.agentType === 'deepsearch') {
      // 等待一帧，确保数据已加载
      requestAnimationFrame(() => {
        const hasIncomplete = useConversationStore.getState().checkAndMarkIncompleteAsFailed()
        if (hasIncomplete) {
          console.log('[AppsPage] Marked incomplete messages as FAILED on conversation switch')
        }
      })
    }
  }

  // ===== DeepSearch 插件：消息发送处理 =====
  const handleDeepSearchSend = async (
    content: string,
    options?: { interrupt_feedback?: string; backend_message?: string }
  ) => {
    // 标记SSE是否正常完成（收到正常结束信号）
    // 需要在 try 块外定义，这样 finally 块也能访问
    let sseCompletedNormally = false
    let recordingId: string | undefined

    // 如果没有 conversation，先创建一个
    let conversationId = currentConversationId
    if (!conversationId) {
      // 使用消息内容作为标题（截断到50个字符）
      const title = content.length > 50 ? content.slice(0, 50) + '...' : content

      // 使用带检查的创建函数
      conversationId = await handleCreateConversation(title, {
        agentType: 'deepsearch',
      })

      // 如果返回 null，说明用户取消了创建
      if (!conversationId) {
        console.log('[DeepSearch] User cancelled conversation creation due to limit warning')
        setInputValue(content) // 恢复输入框内容
        return
      }

      console.log('[DeepSearch] Created new conversation with title:', title, 'id:', conversationId)
    }

    // 1. 添加用户消息到 ConversationStore
    addUserMessage(conversationId, content)

    // 2. 设置加载状态
    setIsSending(true)
    setLoading(true)

    // 3. 创建 AbortController 用于中断请求
    const controller = new AbortController()
    setAbortController(controller)

    try {
      // 4. 获取并验证配置
      let config = agentConfigs['deepsearch'] || DEFAULT_DEEPSEARCH_CONFIG

      // ===== 配置验证 =====
      // 本地搜索模式：必须配置知识库
      if (config.searchMode === 'local' || config.searchMode === 'all') {
        if (!config.selectedKnowledgeBaseIds || config.selectedKnowledgeBaseIds.length === 0) {
          // 显示错误提示
          addSystemMessage(conversationId, MessageType.ERROR, {
            text: `${t('apps.chat.configError')}：${t('apps.chat.selectKnowledgeBase')}`,
            searchMode: config.searchMode === 'local' ? t('apps.chat.localSearch') : t('apps.chat.comprehensiveSearch')
          })
          setIsSending(false)
          setLoading(false)
          return
        }
      }

      // 网络搜索模式：必须配置搜索引擎
      if (config.searchMode === 'web' || config.searchMode === 'all') {
        if (!config.selectedWebSearchEngineId) {
          // 显示错误提示
          addSystemMessage(conversationId, MessageType.ERROR, {
            text: `${t('apps.chat.configError')}：${t('apps.chat.selectSearchEngine')}`,
            searchMode: config.searchMode === 'web' ? t('apps.chat.webSearch') : t('apps.chat.comprehensiveSearch')
          })
          setIsSending(false)
          setLoading(false)
          return
        }
      }

      // 构建本地搜索配置
      const local_search_config = (config.searchMode === 'local' || config.searchMode === 'all')
        ? {
            local_search_config_ids: config.selectedKnowledgeBaseIds || [],
            max_local_search_results: config.localSearchResultCount,
            recall_threshold: config.recallThreshold,
          }
        : undefined

      // 构建网络搜索配置
      const web_search_config = (config.searchMode === 'web' || config.searchMode === 'all')
        ? {
            web_search_config_id: config.selectedWebSearchEngineId!,
            max_web_search_results: config.webSearchResultCount,
          }
        : undefined

      // ===== HITL 判断逻辑：判断是否是回复 HITL interrupt 消息 =====
      let interrupt_feedback = options?.interrupt_feedback ?? ''  // 默认为空

      const messageItemsList = useConversationStore.getState().getCurrentMessageItems()

      // ===== 判断是否是新的 deepsearch 运行 =====
      // 用于确定是否需要使用新的 session ID
      let isNewDeepSearchRun = !options?.interrupt_feedback  // 默认认为是新的运行

      if (!options?.interrupt_feedback && messageItemsList && messageItemsList.length > 0) {
        // 从后往前找最后一个系统消息（非用户消息）
        // 因为最后一个是刚添加的用户消息，所以要往前找
        let lastSystemMessageItems: MessageItems | undefined

        for (let i = messageItemsList.length - 1; i >= 0; i--) {
          if (!useConversationStore.getState().getMessageItemsIsUser(messageItemsList[i])) {
            lastSystemMessageItems = messageItemsList[i]
            break
          }
        }

        if (lastSystemMessageItems) {
          // 获取最后一个 Message
          const lastMessageId = lastSystemMessageItems.messagesIds[lastSystemMessageItems.messagesIds.length - 1]
          const lastMessage = lastMessageId ? useConversationStore.getState().getMessageById(lastMessageId) : undefined

          // 判断是否是 HITL interrupt 消息（包括 INTERRUPT 和 OUTLINE_INTERACTION 类型）
          if (lastMessage &&
              (lastMessage.type === MessageType.INTERRUPT || lastMessage.type === MessageType.OUTLINE_INTERACTION) &&
              (lastMessage.status === TaskStatus.IN_PROGRESS || lastMessage.status === TaskStatus.PENDING || lastMessage.status === TaskStatus.UNKNOWN)) {
            // 这是 HITL 的第一次回复，判断 agent 是否匹配
            const hitlAgent = lastSystemMessageItems.agentType  // 从 MessageItems 获取 agentType

            if (hitlAgent === AgentType.DEEPSEARCH) {
              // Agent 匹配：更新 interrupt 消息状态为 COMPLETED，设置 interrupt_feedback
              // 这是 HITL 延续，不是新的 deepsearch 运行
              isNewDeepSearchRun = false
              console.log('[HITL] Before update - status:', lastMessage.status)
              useConversationStore.getState().updateMessage(
                lastSystemMessageItems.id,
                lastMessage.id,
                { status: TaskStatus.COMPLETED }
              )
              // 更新 MessageItems 状态为 COMPLETED，隐藏"生成中"提示
              useConversationStore.getState().updateMessageItems(
                lastSystemMessageItems.id,
                { status: TaskStatus.COMPLETED }
              )

              // 根据消息类型设置不同的 interrupt_feedback
              if (lastMessage.type === MessageType.OUTLINE_INTERACTION) {
                // 大纲交互：用户在输入框输入的是修改意见
                interrupt_feedback = 'revise_comment'
              } else {
                // 普通 INTERRUPT：用户反馈
                interrupt_feedback = 'accepted'
              }
            } else {
              // Agent 不匹配：更新 interrupt 消息状态为 CANCELLED
              useConversationStore.getState().updateMessage(
                lastSystemMessageItems.id,
                lastMessage.id,
                { status: TaskStatus.CANCELLED }
              )
              // 更新 MessageItems 状态为 CANCELLED，隐藏"生成中"提示
              useConversationStore.getState().updateMessageItems(
                lastSystemMessageItems.id,
                { status: TaskStatus.CANCELLED }
              )
              interrupt_feedback = ''  // 保持为空
            }
          } else {
            // 不是 HITL interrupt 消息，清除 SESSION_CONVERSATION_ID
            useConversationStore.getState().setSessionConversationId(null)
          }
        } else {
        }
      } else {
      }

      // ===== 计算 DeepSearch 运行 Session ID =====
      // 因为已经添加了用户消息，所以用户消息数量就是应该用的 sessionId
      const userMessageCount = messageItemsList.filter(items =>
        useConversationStore.getState().getMessageItemsIsUser(items)
      ).length

      // ===== 生成后端使用的 conversation_id =====
      // 如果是新的 deepsearch 运行，或者没有 SESSION_CONVERSATION_ID，则生成新的后端 conversation_id
      // 否则使用现有的 SESSION_CONVERSATION_ID
      // 注意：需要在函数内部获取最新的 SESSION_CONVERSATION_ID，而不是使用组件渲染时的值
      const currentSessionConversationId = useConversationStore.getState().SESSION_CONVERSATION_ID
      const backendConversationId = (isNewDeepSearchRun || !currentSessionConversationId)
        ? `${conversationId}_${Math.random().toString(36).substring(2, 6)}_${String(userMessageCount).padStart(3, '0')}`
        : currentSessionConversationId

      // 立即保存到 Store 中，以便取消请求时使用
      useConversationStore.getState().setSessionConversationId(backendConversationId)

      // ===== SSE 录制：开始录制（仅开发模式） =====
      if (ENABLE_SSE_DEBUG) {
        try {
          // 从 localStorage 读取压缩配置
          const COMPRESSION_STORAGE_KEY = 'sse_recording_compression_enabled'
          const enableCompression = localStorage.getItem(COMPRESSION_STORAGE_KEY) !== 'false'

          recordingId = await SSERecorder.startRecording(content, {
            agentType: 'deepsearch',
            modelConfigId: selectedModelId,
            conversationId: backendConversationId, // 使用带 session 的 conversation_id
            spaceId: user?.spaceId || getDefaultSpaceId(),
          }, {
            enableCompression,
          })
        } catch (error) {
          console.warn('[DeepSearch] Failed to start SSE recording:', error)
        }
      }

      // 获取认证 token
      const token = getToken()
      if (!token) {
        throw new Error('无法获取认证信息，请重新登录')
      }

      const messageToBackend = options?.backend_message ?? content

      const response = await fetch('/api/v1/agent/deepsearch/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          space_id: user?.spaceId || getDefaultSpaceId(),
          general_model_config_id: config.generalModelId ? parseInt(config.generalModelId) : selectedModelId,
          message: messageToBackend,
          conversation_id: backendConversationId, // 使用带 session 的 conversation_id
          search_mode: 'research', // DeepSearch 模式固定为 research
          outliner_max_section_num: config.planChapterCount,
          workflow_human_in_the_loop: config.enableHumanInteraction,
          outline_interaction_enabled: config.outlineInteractionEnabled,
          outline_interaction_max_rounds: config.outlineInteractionEnabled ? OUTLINE_INTERACTION_MAX_ROUNDS : undefined,
          info_collector_search_method: config.searchMode,
          source_tracer_research_trace_source_switch: config.enableTraceability,
          source_tracer_source_tracer_infer_switch: config.enableSourceTracerInfer,
          web_search_config,  // 可能是undefined
          local_search_config,  // 新增：可能是undefined
          template_id: config.selectedTemplateId ?? -1,
          interrupt_feedback: interrupt_feedback,   // 中断反馈标识, 可填值: ['accepted', ''], 默认''
          // 高级配置模型 ID（可选，仅在有值时传递）
          ...(config.planUnderstandingModelId && { plan_understanding_model_id: parseInt(config.planUnderstandingModelId) }),
          ...(config.infoCollectingModelId && { info_collecting_model_id: parseInt(config.infoCollectingModelId) }),
          ...(config.writingCheckingModelId && { writing_checking_model_id: parseInt(config.writingCheckingModelId) }),
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // ===== 启动SSE超时监控 =====
      useConversationStore.getState().startSSETimeoutMonitor(conversationId)

      // 5. 处理 SSE 流式响应
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          // SSE 流读取结束时，需要等待SSE事件队列处理完成
          // 因为 reader.read() 返回 done: true 不代表所有事件都被处理了

          // 设置一个检查机制，等待队列处理完成后停止监控
          if (sseCompletedNormally) {
            // SSE 正常完成，等待队列处理完成后停止监控
            const checkQueueProcessed = () => {
              const state = useConversationStore.getState()
              // 检查队列是否为空且没有正在处理
              if (state.sseEventQueue.length === 0 && !state.sseProcessingQueue) {
                useConversationStore.getState().stopSSETimeoutMonitor()
              } else {
                // 队列还有事件，继续等待
                requestAnimationFrame(checkQueueProcessed)
              }
            }
            requestAnimationFrame(checkQueueProcessed)
          }
          // 注意：如果 sseCompletedNormally 为 false，不停止监控，让定时器在超时后标记为FAILED

          // SSE 流读取结束时，不再自动标记所有未完成消息为完成
          // 让SSE事件处理逻辑（如 ALL END）来决定最终状态
          // 这样可以避免覆盖正常的完成状态

          // ===== SSE 录制：停止录制 =====
          if (recordingId) {
            try {
              await SSERecorder.stopRecording()
            } catch (error) {
              console.warn('[DeepSearch] Failed to save SSE recording:', error)
            }
          }

          break
        }

        // 解码数据
        buffer += decoder.decode(value, { stream: true })

        // 按行分割 SSE 数据
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // 保留最后一个不完整的行

        for (const line of lines) {

          if (line.trim().startsWith('data:')) {
            // ===== 每次收到SSE事件，更新时间戳 =====
            useConversationStore.getState().updateLastSSEEventTime()
            try {
              const jsonStr = line.substring(5).trim() // 移除 'data:' 前缀
              if (!jsonStr || jsonStr === '[DONE]') continue

              const data = JSON.parse(jsonStr)

              // 检测是否收到正常结束信号
              if (data.agent === 'end' && data.content === 'ALL END') {
                sseCompletedNormally = true
              }

              // ===== SSE 录制：录制事件 =====
              if (recordingId) {
                try {
                  await SSERecorder.recordEvent(data)
                } catch (error) {
                  console.warn('[DeepSearch] Failed to record SSE event:', error)
                }
              }

              // 处理 SSE 消息
              useConversationStore.getState().handleSSEMessage(data, conversationId)
            } catch (e) {
              console.error('[DeepSearch] 解析 SSE 数据失败:', e, '原始行:', line)
            }
          }
        }
      }
    } catch (error: any) {
      // 发生错误时不停止SSE超时监控，让定时器在超时后检测并标记为FAILED

      if (error.name !== 'AbortError') {
        console.error('[DeepSearch] Error sending message:', error)
      }

      // ===== SSE 录制：错误时也要停止录制 =====
      if (typeof recordingId !== 'undefined' && recordingId && SSERecorder.isRecording()) {
        try {
          await SSERecorder.stopRecording()
        } catch (error) {
          console.warn('[DeepSearch] Failed to stop SSE recording on error:', error)
        }
      }
    } finally {
      // SSE超时监控的停止逻辑：
      // 1. SSE正常完成（sseCompletedNormally = true）→ 停止监控
      // 2. 发生错误/异常中断（sseCompletedNormally = false）→ 不停止监控，让定时器检测超时
      if (sseCompletedNormally) {
        useConversationStore.getState().stopSSETimeoutMonitor()
      }

      setIsSending(false)
      setLoading(false)
      setAbortController(null)
    }
  }

  // ===== DeepSearch 停止请求处理 =====
  const handleStopDeepSearch = async () => {
    // 使用 SESSION_CONVERSATION_ID (带随机后缀的 ID)，如果为空则回退到 currentConversationId
    // 必须与 handleDeepSearchSend 中生成的 backendConversationId 保持一致
    const conversation_id = useConversationStore.getState().SESSION_CONVERSATION_ID || currentConversationId

    if (!conversation_id) {
      console.error('[DeepSearch Cancel] No conversationId found')
      // 仍然尝试 abort 前端 SSE 流
      if (abortController) {
        abortController.abort()
        setAbortController(null)
      }
      return
    }

    const token = getToken()
    if (!token) {
      console.error('[DeepSearch Cancel] No auth token')
      return
    }

    // 【关键 1】立即更新 UI 状态，不等待后端响应
    useConversationStore.getState().updateMessageItemsStatusToCancelled()

    // 【关键 2】发送取消请求到后端
    // 根据 DeepSearch 服务代码，取消请求只需要 space_id 和 conversation_id
    // interrupt_feedback 必须是 "cancel"
    const cancelAbortController = new AbortController()

    console.log('[DeepSearch Cancel] Sending cancel request, conversation_id:', conversation_id)

    // 获取 space_id（与发起请求时保持一致）
    const space_id = user?.spaceId || getDefaultSpaceId()

    fetch('/api/v1/agent/deepsearch/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        space_id: space_id,
        conversation_id: conversation_id,
        message: '',  // 必填字段，取消请求时为空字符串
        interrupt_feedback: 'cancel',  // DeepSearch 服务根据这个字段识别取消请求
        general_model_config_id: -1, // 必填字段，但在取消请求中不使用
      }),
      signal: cancelAbortController.signal,
    }).then(async (response) => {
      if (!response.ok) {
        console.error('[DeepSearch Cancel] Failed, status:', response.status)
        const errorText = await response.text()
        console.error('[DeepSearch Cancel] Error body:', errorText)
      } else {
        const data = await response.json()
        console.log('[DeepSearch Cancel] Success:', data)
      }
    }).catch((error) => {
      if (error.name === 'AbortError') {
        console.log('[DeepSearch Cancel] Request aborted')
      } else {
        console.error('[DeepSearch Cancel] Error:', error)
      }
    })

    // 【关键 3】立即 abort 前端的 SSE 流，不需要等待 cancel 请求完成
    if (abortController) {
      abortController.abort()
      setAbortController(null)
    }
  }


  return (
    <div className={`${FONT_FAMILY} flex flex-col h-full w-full min-h-0`}>
      {/* SSE 回放浮动按钮（仅开发模式） */}
      {ENABLE_SSE_DEBUG && (
        <button
          onClick={() => setShowPlaybackPanel(true)}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white text-sm font-medium rounded-full shadow-lg hover:shadow-xl transition-all duration-200"
          title={t('apps.chat.openSSEPanel')}
        >
          <History className="w-4 h-4" />
          <span>{t('apps.chat.replayHistory')}</span>
        </button>
      )}

      {/* 主内容区 - 使用 flex 布局 */}
      <div className="flex-1 flex flex-row min-h-0 overflow-hidden">
        {/* 对话历史侧边栏 - 始终显示 */}
        <ConversationHistorySidebar
          currentConversationId={currentConversationId}
          onConversationSelect={handleConversationSelect}
          onNewConversation={handleNewConversation}
          isStreaming={isStreaming}
          forceCollapsed={!!selectedResultMessageId}
        />

        {/* 右侧主内容区 */}
        <div
          className={`flex-1 flex min-h-0 overflow-hidden ${selectedResultMessageId ? 'flex-row' : 'flex-col'}`}
        >
          {/* 无对话状态 - 居中的输入框 */}
          {!hasConversation && !selectedResultMessageId && (
            <div className="flex-1 flex flex-col items-center justify-center px-4">
              <div className="w-full max-w-3xl">
                {/* 欢迎区域 */}
                <div className="text-left mb-8">
                  {/* DeepSearch 服务不可用时的警告 */}
                  {selectedAgent?.id === 'deepsearch' && deepsearchServiceAvailable === false ? (
                    <p className={`${TEXT_BASE} text-orange-600 mb-2`}>
                      {t('apps.chat.deepSearchServiceUnavailable')}
                      <a
                        href="https://gitcode.com/openJiuwen/deepsearch/blob/v0.1.0/docs/zh/2.%E5%AE%89%E8%A3%85%E6%8C%87%E5%AF%BC/DeepSearch%E5%AE%8C%E6%95%B4%E7%89%88%E5%AE%89%E8%A3%85%E6%8C%87%E5%AF%BC.md"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-600 underline mx-0.5"
                      >
                        OpenJiuwen
                      </a>
                      {t('apps.chat.deepSearchConfigRetry')}
                    </p>
                  ) : (
                    <>
                      {/* 第一段话：用户名，你好 */}
                      <p className={`${TEXT_BASE} text-gray-500 mb-1`}>
                        {user?.username || t('apps.user.defaultUsername')}，{t('apps.chat.welcome')}
                      </p>
                      {/* 第二段话：选择智能体开始对话 */}
                      <h1 className="text-2xl font-semibold text-gray-900 mb-6">
                        {t('apps.chat.welcomeMessage')}
                      </h1>
                    </>
                  )}
                </div>

                {/* 使用统一的输入区域组件 */}
                <ChatInputArea
                  inputValue={inputValue}
                  onInputChange={setInputValue}
                  onPressEnter={handleSendMessage}
                  onStopClick={handleStopDeepSearch}
                  inputRef={chatInputRef}
                  isStreaming={isStreaming}
                  selectedAgent={selectedAgent}
                  onAgentSelect={handleAgentSelect}
                  onAgentConfig={handleAgentConfig}
                  onAgentDeselect={handleAgentDeselect}
                  agents={agents}
                  onResourceSelect={handleResourceSelect}
                  resources={resources}
                  onFileUpload={handleFileUpload}
                  selectedModel={selectedModel}
                  modelsLoading={modelsLoading}
                  models={models}
                  onModelClick={handleModelButtonClick}
                  modelButtonRef={modelButtonRef}
                  onNewConversation={handleNewConversation}
                  deepsearchUnavailable={selectedAgent?.id === 'deepsearch' && deepsearchServiceAvailable === false}
                  checkingDeepsearch={checkingDeepsearch}
                  className="mb-6"
                  inputStyle={{ minHeight: '80px' }}
                />

                {/* 建议提示词卡片 - 一行布局，居中对齐 */}
                {currentSuggestions.length > 0 && (
                  <div className="flex justify-center items-center gap-3">
                    {currentSuggestions.map(suggestion => (
                      <button
                        key={suggestion.id}
                        onClick={() => handleSuggestionClick(suggestion.text)}
                        className="
                          flex items-center gap-2 px-4 py-2
                          bg-white
                          border border-gray-200 rounded-xl
                          hover:border-blue-500 hover:bg-blue-50 hover:shadow-md
                          focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-white
                          transition-all duration-200
                          text-left w-fit
                        "
                      >
                        <span className={TEXT_BASE}>{suggestion.icon}</span>
                        <span className={`${TEXT_SMALL} text-gray-600`}>{suggestion.text}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 有对话状态 */}
          {hasConversation && (
            <>
              {/* 对话区域 */}
              <div className={`flex flex-col min-h-0 ${selectedResultMessageId ? 'w-2/5' : 'flex-1'}`}>
                <div ref={messagesContainerRef} className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-6 py-6">
                <div className="max-w-4xl mx-auto space-y-4">
                  {messageItemsList.map((messageItems) => (
                    <SystemMessageItem key={messageItems.id} messageItems={messageItems} />
                  ))}

                  {/* AI 正在输入指示器 */}
                  {isSending && (
                    <div className="flex justify-start">
                      <div className="max-w-[70%] rounded-2xl px-5 py-3 text-gray-900">
                        <div className="flex items-center gap-1">
                          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* 底部输入框 */}
              <div className="shrink-0 px-6 py-6">
                <div className="max-w-4xl mx-auto">
                  <ChatInputArea
                    inputValue={inputValue}
                    onInputChange={setInputValue}
                    onPressEnter={handleSendMessage}
                    onStopClick={handleStopDeepSearch}
                    inputRef={chatInputRef}
                    isStreaming={isStreaming}
                    selectedAgent={selectedAgent}
                    onAgentSelect={handleAgentSelect}
                    onAgentConfig={handleAgentConfig}
                    onAgentDeselect={handleAgentDeselect}
                    agents={agents}
                    onResourceSelect={handleResourceSelect}
                    resources={resources}
                    onFileUpload={handleFileUpload}
                    selectedModel={selectedModel}
                    modelsLoading={modelsLoading}
                    models={models}
                    onModelClick={handleModelButtonClick}
                    modelButtonRef={modelButtonRef}
                    onNewConversation={handleNewConversation}
                  />
                </div>
              </div>
            </div>

            {/* 右侧：结果面板（分屏显示） */}
            {selectedResultMessageId && (
              <div className="w-3/5 h-full bg-white border border-gray-200 rounded-lg ml-4 overflow-hidden">
                <ResultPanel />
              </div>
            )}
          </>
          )}
        </div>
      </div>

      {/* 智能体配置弹窗 */}
      <AgentConfigDialog
        agent={pendingAgent || selectedAgent}
        open={configDialogOpen}
        onClose={() => {
          setConfigDialogOpen(false)
          // 无论是否是首次配置模式，都清除待选择的智能体
          setPendingAgent(null)
          setIsFirstConfigMode(false)
        }}
        onSave={handleSaveAgentConfig}
        savedConfigs={agentConfigs}
        spaceId={user?.spaceId || getDefaultSpaceId()}
        modelConfigId={selectedModelId}
        isFirstConfig={isFirstConfigMode}
        availableModels={availableModels}
        modelsLoading={modelsLoading}
      />

      {/* 模型选择弹窗 */}
      {showModelPicker && modelPickerPosition && (
        <ModelPicker
          models={models}
          selectedModel={selectedModel}
          onSelect={handleModelSelect}
          onClose={() => setShowModelPicker(false)}
          position={modelPickerPosition}
          isLoading={modelsLoading}
        />
      )}

      {/* SSE 回放面板（仅开发模式） */}
      {ENABLE_SSE_DEBUG && showPlaybackPanel && (
        <PlaybackPanel
          onClose={() => setShowPlaybackPanel(false)}
          onPlaybackStart={async (conversationId) => {
            // conversationId 是回放对话的 ID（由 PlaybackPanel 通过 getOrCreatePlaybackConversation 获取）
            // 直接切换到回放对话，不再创建新对话
            await switchConversation(conversationId)
            // 切换到 DeepSearch 模式
            const deepsearchAgent = DEFAULT_AGENTS.find(a => a.id === 'deepsearch')
            if (deepsearchAgent) {
              setSelectedAgent(deepsearchAgent)
            }
            // 返回 conversationId（回放对话的 ID）
            return conversationId
          }}
        />
      )}

      {/* 全局 Snackbar 通知 */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />

      {/* 对话限制和删除确认对话框 */}
      <ConversationLimitDialog
        open={limitDialogOpen}
        type={limitDialogType}
        currentCount={limitDialogData.currentCount}
        maxCount={limitDialogData.maxCount}
        currentSize={limitDialogData.currentSize}
        maxSize={limitDialogData.maxSize}
        warningThreshold={limitDialogData.warningThreshold}
        oldestConversation={limitDialogData.oldestConversation}
        deleteReason={limitDialogData.deleteReason}
        deleteDetails={limitDialogData.deleteDetails}
        onConfirm={handleLimitDialogConfirm}
        onCancel={handleLimitDialogCancel}
      />
    </div>
  )
}

export default AppsPage
