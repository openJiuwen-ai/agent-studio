import React, { useState, useEffect, useRef, useMemo, useCallback, lazy, Suspense } from 'react'
import { Copy, Trash2, RefreshCw, History, X, AlertTriangle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { MentionItem, DEFAULT_AGENTS, DEFAULT_RESOURCES } from './components/MentionPicker'
import AgentConfigDialog, { DeepSearchConfig } from './components/AgentConfigDialog'
import ChatInputArea from './components/ChatInputArea'
import ModelPicker from './components/ModelPicker'
import { useModels, useVLMModels, getToken, deepsearchHeartbeatService } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { useConversationStore, MessageType, TaskStatus, AgentType, DeepsearchExecutionMethod, isTaskOngoing,
  type MessageItems, OUTLINE_INTERACTION_MAX_ROUNDS, MESSAGE_TITLES } from '../../stores/useConversationStore'
import { DeepsearchAgentType } from '../../stores/handlers/deepsearchSSETypes'
import { getDefaultSpaceId } from '../../utils/spaceUtils'
import {
  type DeepSearchRecordingHandle,
  type SSEData,
  useDeepSearchRecordingBridge,
  useRecordingStore,
} from '../../modules/recording';
import RecordingPanel from '../../components/Conversation/RecordingPanel'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import ConversationLimitDialog from '../../components/Common/ConversationLimitDialog'
import KeepAliveGuideDialog from '../../components/Common/KeepAliveGuideDialog'
import { conversationEventEmitter, conversationDB } from '../../utils/conversationDB'
import type { MessageInputRef } from './components/MessageInput'
import { copyToClipboard, STORAGE_KEYS, storage, getAgentConfigKeys } from './utils/utils'
import {
  type AppAgentConfig,
  DEFAULT_DEEPRESEARCH_CONFIG,
  type DeepSearchExplorerConfig,
  getDefaultDeepSearchConfigByAgentId,
  toDeepResearchConfig,
  toDeepSearchExplorerConfig,
} from './utils/deepsearchConstants'
import { getSuggestionsByAgent } from './constants/suggestions'
import { TEXT_BASE, TEXT_SMALL, FONT_FAMILY } from './constants/styles'
import type { Message, ReportRewriteParams, TruthVerificationEntry } from './types'
import { truthVerificationEntryExistsInContent } from '../../utils/reportUtils'
import { SystemMessageItem } from '../../components/Conversation'
import ResultPanel from '../../components/Conversation/ResultPanel'
import ConversationHistorySidebar from './components/ConversationHistorySidebar'
import { MindMapPanel } from '../../components/Conversation/MindMap'
import { TopToolbar, ViewType } from '../../components/Conversation'
import * as deepSearchApi from './components/DeepSearchExplorer/api'
import DeepSearchExplorerConfigDialog from './components/DeepSearchExplorer/DeepSearchExplorerConfigDialog'
import { buildDeepSearchBackendConfig } from './components/DeepSearchExplorer/buildDeepSearchBackendConfig'
import {
  cancelDeepSearchConversationRuns,
  handleDeepSearchExplorerLeave,
} from './utils/deepSearchExplorerRunManagement'

const DeepSearchExplorerPanel = lazy(() => import('./components/DeepSearchExplorer/DeepSearchExplorerPanel'))
const DeepSearchRunSummary = lazy(() => import('./components/DeepSearchExplorer/DeepSearchRunSummary'))

// ==================== 开发调试配置 ====================
// 从环境变量读取，默认为 false（生产环境）
// 在 .env 中设置 VITE_ENABLE_SSE_DEBUG=true 来启用
const ENABLE_SSE_DEBUG = import.meta.env.VITE_ENABLE_SSE_DEBUG === 'true'

const REWRITE_ACTION_LABEL_KEYS: Record<string, string> = {
  polish: 'apps.report.aiPolish',
  expand: 'apps.report.aiExpand',
  shorten: 'apps.report.aiShrink',
  supplementary_search: 'apps.report.aiSupplementarySearch',
  new_task: 'apps.report.aiNewTask',
}

const SUPPLEMENTARY_SEARCH_SCOPE_LABEL_KEYS: Record<string, string> = {
  selected_only: 'apps.report.supplementarySearch.selectedOnly',
  selected_and_related: 'apps.report.supplementarySearch.selectedAndRelated',
}

const buildRewriteUserMessage = (t: (key: string, options?: Record<string, unknown>) => string, action: string, selectedText: string, userInstruction?: string, scope?: string): string => {
  let actionLabel = REWRITE_ACTION_LABEL_KEYS[action] ? t(REWRITE_ACTION_LABEL_KEYS[action]) : action
  if (action === 'supplementary_search' && scope && SUPPLEMENTARY_SEARCH_SCOPE_LABEL_KEYS[scope]) {
    actionLabel = `${actionLabel}（${t(SUPPLEMENTARY_SEARCH_SCOPE_LABEL_KEYS[scope])}）`
  }
  const displayText = selectedText.length > 100
    ? `${selectedText.slice(0, 100)}...`
    : selectedText
  if (action === 'new_task') {
    return userInstruction
      ? t('apps.report.newTaskHelpText', { displayText, userInstruction })
      : t('apps.report.newTaskHelpTextShort', { displayText })
  }
  return userInstruction
    ? t('apps.report.rewriteHelpText', { actionLabel, displayText, userInstruction })
    : t('apps.report.rewriteHelpTextShort', { actionLabel, displayText })
}

// ==================== 主页面组件 ====================

const normalizeMaxRewriteInteractions = (value?: number): number => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 3
  }

  return Math.max(0, value)
}

const getRewriteRoundState = (
  maxInteractionsValue: number | undefined,
  originalRemainingRewriteRounds: number | undefined
) => {
  const maxInteractions = normalizeMaxRewriteInteractions(maxInteractionsValue)
  const isFirstRewrite = originalRemainingRewriteRounds === undefined
  const newRemaining = isFirstRewrite
    ? Math.max(0, maxInteractions - 1)
    : Math.max(0, (originalRemainingRewriteRounds ?? 0) - 1)

  return {
    maxInteractions,
    newRemaining,
  }
}

// 模块级变量：持久化 AbortController，在组件卸载/重挂载时不丢失
// 使得切换到其他页面再切回时，仍可正确 abort 仍在进行的 SSE
let _activeDeepSearchController: AbortController | null = null
let _activeRewriteController: AbortController | null = null

// SSE 进行中切换模块时需要跨生命周期保存的 UI 状态类型
interface AppsUISnapshot {
  currentMessageItemsId: string | null
  lastSelectedReportId: string | null
  showMindMap: boolean
  mindMapMessageItemsId: string | null
  currentGraphType: 'sectionGraph' | 'taskGraph'
  showDeepSearchExplorer: boolean
  deepSearchExplorerFullscreen: boolean
  activeDeepSearchRunId: string | null
  killedDeepSearchRunIds: Set<string>
}

// 模块级快照：SSE 进行中卸载时保存，重挂载时恢复
let _appsUISnapshot: { conversationId: string; state: AppsUISnapshot } | null = null

// 组件卸载标志：区分"切换模块（导航）"与"刷新/关闭页面"
// 导航时 JS 运行时存活，此标志保持 true；刷新/关闭后 JS 重置，标志恢复初始值 false
let _didNavigateBack = false

const AppsPage: React.FC = () => {
  const { user } = useAuthStore()
  const { t } = useTranslation()
  // Snackbar 支持 - 必须在组件顶层调用以监听全局事件
  const { snackbar, closeSnackbar, showSuccess } = useUnifiedSnackbar()

  const [inputValue, setInputValue] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [selectedModelId, setSelectedModelId] = useState<number>(-1)
  const [selectedAgent, setSelectedAgent] = useState<MentionItem | null>(null)
  const [hasConversation, setHasConversation] = useState(false)
  // 会话已开始（发出第一条消息后）则锁定 Agent，禁止切换
  // 使用 hasConversation 而非 currentConversationId：点击 + 新建对话时
  // resetModuleSessionState 立即将其设为 false，但 currentConversationId 仍保留旧值
  const isAgentLocked = hasConversation
  const [messages, setMessages] = useState<Message[]>([])
  const [isSending, setIsSending] = useState(false)

  // ===== DeepSearch 插件状态（最小化侵入） =====
  const [isDeepSearchMode, setIsDeepSearchMode] = useState(false)
  // abortController 已迁移至模块级变量 _activeDeepSearchController，见组件外声明
  const [showPlaybackPanel, setShowPlaybackPanel] = useState(false)
  const [deepsearchServiceAvailable, setDeepsearchServiceAvailable] = useState<boolean | null>(null)
  const [checkingDeepsearch, setCheckingDeepsearch] = useState(false)

  // ===== Deep Search Explorer 模式状态 =====
  const [isDeepSearchExplorerMode, setIsDeepSearchExplorerMode] = useState(false)
  const [showDeepSearchExplorer, setShowDeepSearchExplorer] = useState(false)
  const [deepSearchExplorerFullscreen, setDeepSearchExplorerFullscreen] = useState(false)
  // Map of messageItemsId → runId for multiple summaries
  const [deepSearchRunIds, setDeepSearchRunIds] = useState<Map<string, string>>(new Map())
  // The currently active runId being viewed in the explorer panel
  const [activeDeepSearchRunId, setActiveDeepSearchRunId] = useState<string | null>(null)
  // Runs killed from the explorer (used to force terminal state in summary cards)
  const [killedDeepSearchRunIds, setKilledDeepSearchRunIds] = useState<Set<string>>(new Set())
  const [pendingDeepSearchExplorerRunCounts, setPendingDeepSearchExplorerRunCounts] = useState<Map<string, number>>(new Map())
  const hasPendingDeepSearchExplorerRunCreation = pendingDeepSearchExplorerRunCounts.size > 0

  // Responsive: detect narrow screens (laptops) to auto-fullscreen explorer
  const [isNarrowScreen, setIsNarrowScreen] = useState(false)
  useEffect(() => {
    const WIDE_BREAKPOINT = 1440
    const check = () => setIsNarrowScreen(window.innerWidth < WIDE_BREAKPOINT)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // On laptop screens, auto-fullscreen the explorer when opened
  useEffect(() => {
    if (isNarrowScreen && showDeepSearchExplorer) {
      setDeepSearchExplorerFullscreen(true)
    }
  }, [isNarrowScreen, showDeepSearchExplorer])

  // ===== MindMap 思维链面板状态 =====
  const [showMindMap, setShowMindMap] = useState(false)
  const [mindMapMessageItemsId, setMindMapMessageItemsId] = useState<string | null>(null)

  // ===== 录制模块 =====
  const {
    createMainFlowRecording,
    createRewriteRecording,
    tryMockRewrite,
  } = useDeepSearchRecordingBridge()

  // ===== 右侧面板状态管理 =====
  const [currentMessageItemsId, setCurrentMessageItemsId] = useState<string | null>(null)
  const [lastSelectedReportId, setLastSelectedReportId] = useState<string | null>(null)
  const [currentGraphType, setCurrentGraphType] = useState<'sectionGraph' | 'taskGraph'>('sectionGraph')

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
  const playbackStatus = useRecordingStore(state => state.playbackStatus)
  const SESSION_CONVERSATION_ID = useConversationStore(state => state.SESSION_CONVERSATION_ID)
  const getMessageItemsByConversationId = useConversationStore(state => state.getMessageItemsByConversationId)
  const mindMapManagersMap = useConversationStore(state => state.mindMapManagersMap)

  // 订阅 conversation 来触发 messageItemsList 重新计算
  const conversation = useConversationStore(state =>
    state.currentConversationId ? state.conversationsMap.get(state.currentConversationId) : undefined
  )

  // 计算 SSE 是否正在传输
  // isSending: 发起请求时的状态
  // isLoading: 从 store 读取的加载状态
  // sseProcessingQueue: SSE 事件队列是否正在处理
  const isPlaybackReplaying = playbackStatus === 'playing' || playbackStatus === 'paused'
  const isStreaming = isSending || isLoading || (!isPlaybackReplaying && sseProcessingQueue)
  const isConversationHistoryBusy = isStreaming || hasPendingDeepSearchExplorerRunCreation

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
  const getMessageById = useConversationStore(state => state.getMessageById)
  const addUserMessage = useConversationStore(state => state.addUserMessage)
  const addSystemMessage = useConversationStore(state => state.addSystemMessage)
  const setConversationConfig = useConversationStore(state => state.setConversationConfig)
  const clearConversationConfig = useConversationStore(state => state.clearConversationConfig)
  const updateConversation = useConversationStore(state => state.updateConversation)
  const saveConversationToDB = useConversationStore(state => state.saveConversationToDB)
  const deleteConversation = useConversationStore(state => state.deleteConversation)
  const setLoading = useConversationStore(state => state.setLoading)
  const setSelectedResultMessageId = useConversationStore(state => state.setSelectedResultMessageId)
  const resetActiveSessionRuntime = useConversationStore(state => state.resetActiveSessionRuntime)
  const clearAll = useConversationStore(state => state.clearAll)
  const initializeFromDB = useConversationStore(state => state.initializeFromDB)

  // 计算当前选中消息的messageItemsId（用于兼容旧逻辑）
  const getCurrentMessageItemsId = useMemo(() => {
    if (!selectedResultMessageId) return null
    
    // 直接从选中的消息中获取messageItemsId
    const message = getMessageById(selectedResultMessageId)
    if (message) {
      return message.messageItemsId
    }
    
    // 兼容旧逻辑：通过遍历messageItems.messagesIds来查找
    if (!currentConversationId) return null
    const messageItemsList = getMessageItemsByConversationId(currentConversationId)
    for (const messageItems of messageItemsList) {
      if (messageItems.messagesIds.includes(selectedResultMessageId)) {
        return messageItems.id
      }
    }
    return null
  }, [selectedResultMessageId, currentConversationId, getMessageItemsByConversationId, getMessageById])

  const getConversationAgentType = (conversationId: string | null | undefined) => {
    if (!conversationId) return null
    return useConversationStore.getState().getConversationById(conversationId)?.config?.agentType ?? null
  }

  const getReusableConversationId = (agentId: string) => {
    const activeConversationId = useConversationStore.getState().currentConversationId
    return getConversationAgentType(activeConversationId) === agentId ? activeConversationId : null
  }

  const resetModuleSessionState = (options?: { preserveSelectedAgent?: boolean }) => {
    resetActiveSessionRuntime()
    setHasConversation(false)
    setMessages([])
    setInputValue('')
    setPendingConversationCreate(null)
    setLimitDialogOpen(false)
    setShowMindMap(false)
    setMindMapMessageItemsId(null)
    setCurrentMessageItemsId(null)
    setLastSelectedReportId(null)
    setCurrentGraphType('sectionGraph')
    setShowDeepSearchExplorer(false)
    setDeepSearchExplorerFullscreen(false)
    setDeepSearchRunIds(new Map())
    setActiveDeepSearchRunId(null)
    setKilledDeepSearchRunIds(new Set())
    setPendingAgent(null)
    setConfigDialogOpen(false)
    setIsFirstConfigMode(false)
    _appsUISnapshot = null
    if (!options?.preserveSelectedAgent) {
      setSelectedAgent(null)
    }
    clearPendingOutlineInteraction()
  }

  const clearDeepSearchExplorerUiState = (options?: { clearRunIds?: boolean; clearKilledRunIds?: boolean }) => {
    setShowDeepSearchExplorer(false)
    setDeepSearchExplorerFullscreen(false)
    setActiveDeepSearchRunId(null)
    if (options?.clearRunIds) {
      setDeepSearchRunIds(new Map())
    }
    if (options?.clearKilledRunIds) {
      setKilledDeepSearchRunIds(new Set())
    }
  }

  const incrementPendingDeepSearchExplorerRunCount = (conversationId: string) => {
    setPendingDeepSearchExplorerRunCounts((prev) => {
      const next = new Map(prev)
      next.set(conversationId, (next.get(conversationId) ?? 0) + 1)
      return next
    })
  }

  const decrementPendingDeepSearchExplorerRunCount = (conversationId: string) => {
    setPendingDeepSearchExplorerRunCounts((prev) => {
      const next = new Map(prev)
      const currentCount = next.get(conversationId) ?? 0
      if (currentCount <= 1) {
        next.delete(conversationId)
      } else {
        next.set(conversationId, currentCount - 1)
      }
      return next
    })
  }

  const interruptModuleTasks = async (agentId: string | null) => {
    if (agentId === 'deepsearch') {
      await handleStopDeepSearch()
    }

    if (_activeRewriteController) {
      _activeRewriteController.abort()
      _activeRewriteController = null
    }

    if (_activeDeepSearchController) {
      _activeDeepSearchController.abort()
      _activeDeepSearchController = null
    }
  }

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
          const oldestConversation = useConversationStore.getState().getConversationById(limitDialogData.oldestConversation.id)
          await cancelDeepSearchConversationRuns(oldestConversation?.config, deepSearchApi.killRun)
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
  const [agentConfigs, setAgentConfigs] = useState<Record<string, AppAgentConfig>>({})
  // 待选择的智能体（需要先配置才能选中）
  const [pendingAgent, setPendingAgent] = useState<MentionItem | null>(null)
  // 是否是首次配置模式（配置完成后才选中智能体）
  const [isFirstConfigMode, setIsFirstConfigMode] = useState(false)

  // 模型选择弹窗状态
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [modelPickerPosition, setModelPickerPosition] = useState<{ x: number; y: number } | null>(null)
  const modelButtonRef = useRef<HTMLButtonElement>(null)

  // "设置本网页保持活跃"操作指引弹窗状态
  const [showKeepAliveGuide, setShowKeepAliveGuide] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatInputRef = useRef<MessageInputRef>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // 记录已执行过 checkAndMarkIncompleteAsAbort 的 conversationId，防止同次挂载中重复触发
  const abortCheckedConvIdRef = useRef<string | null>(null)

  // 每帧同步当前 UI 状态，供卸载时写入模块级快照
  const uiSnapshotRef = useRef<AppsUISnapshot>({
    currentMessageItemsId: null,
    lastSelectedReportId: null,
    showMindMap: false,
    mindMapMessageItemsId: null,
    currentGraphType: 'sectionGraph',
    showDeepSearchExplorer: false,
    deepSearchExplorerFullscreen: false,
    activeDeepSearchRunId: null,
    killedDeepSearchRunIds: new Set(),
  })

  // 用户滚动状态：true = 用户向上滚动了（不在底部），false = 用户在底部
  const [isUserScrolled, setIsUserScrolled] = useState(false)

  // 从后端获取模型列表
  const { data: modelsData, isLoading: modelsLoading } = useModels({
    spaceId: user?.spaceId || getDefaultSpaceId(),
    is_active: true,
    size: 100,
  })

  const { data: vlmModelsData, isLoading: vlmModelsLoading } = useVLMModels({
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

  const availableVLMModels = React.useMemo(() => {
    if (!vlmModelsData?.items) return []
    return vlmModelsData.items.map(model => ({
      tags: model.tags || [],
      icon: '',
      openModel: {
        model_id: model.id,
        name: model.name,
        desc: model.description || '',
        workspace_id: '',
        param_config: { param_schemas: [] },
      },
      series: {
        icon: '',
        name: model.modelId || '',
        vendor: model.provider || '',
      },
      model_from: 'db',
    }))
  }, [vlmModelsData])

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
  // 加载时合并默认值，确保未保存的字段使用最新的默认值
  useEffect(() => {
    const spaceId = user?.spaceId
    if (!spaceId) return

    const configKey = STORAGE_KEYS.AGENT_CONFIGS(spaceId)
    const savedConfigs = storage.get<Record<string, AppAgentConfig>>(configKey)
    if (savedConfigs) {
      // 合并默认值：用户保存的字段覆盖默认值，未保存的字段使用默认值
      const mergedConfigs = Object.keys(savedConfigs).reduce((acc, agentId) => {
        const defaultConfig = getDefaultDeepSearchConfigByAgentId(agentId) as unknown as Record<string, unknown>
        const savedConfig = (savedConfigs[agentId] || {}) as unknown as Record<string, unknown>
        acc[agentId] = {
          ...defaultConfig,
          ...savedConfig,
        } as unknown as AppAgentConfig
        return acc
      }, {} as Record<string, AppAgentConfig>)
      setAgentConfigs(mergedConfigs)
    } else {
      // 如果没有保存的配置，使用空配置
      setAgentConfigs({})
    }
  }, [user?.spaceId])

  // 当 agentConfigs.deepsearch.generalModelId 变化时，同步到 selectedModelId（反向同步）
  useEffect(() => {
    const deepsearchConfig = toDeepResearchConfig(agentConfigs['deepsearch'])
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
  }, [agentConfigs, modelIdMap, selectedModelId])

  // 从 IndexDB 初始化对话数据
  useEffect(() => {
    initializeFromDB()
  }, [])

  // ===== UI 状态快照：SSE 期间切换模块后恢复 =====
  // 无 deps：每次渲染都更新 ref，保证卸载时 cleanup 能拿到最新值
  useEffect(() => {
    uiSnapshotRef.current = {
      currentMessageItemsId,
      lastSelectedReportId,
      showMindMap,
      mindMapMessageItemsId,
      currentGraphType,
      showDeepSearchExplorer,
      deepSearchExplorerFullscreen,
      activeDeepSearchRunId,
      killedDeepSearchRunIds,
    }
  })

  // 挂载时：若有同一对话的快照，则恢复 UI 状态（不限于 isLoading，涵盖 SSE 后台完成的边缘情况）
  useEffect(() => {
    const store = useConversationStore.getState()
    if (
      _appsUISnapshot &&
      _appsUISnapshot.conversationId === store.currentConversationId
    ) {
      const s = _appsUISnapshot.state
      setCurrentMessageItemsId(s.currentMessageItemsId)
      setLastSelectedReportId(s.lastSelectedReportId)
      setShowMindMap(s.showMindMap)
      setMindMapMessageItemsId(s.mindMapMessageItemsId)
      setCurrentGraphType(s.currentGraphType)
      setShowDeepSearchExplorer(s.showDeepSearchExplorer)
      setDeepSearchExplorerFullscreen(s.deepSearchExplorerFullscreen)
      setActiveDeepSearchRunId(s.activeDeepSearchRunId)
      setKilledDeepSearchRunIds(s.killedDeepSearchRunIds)
      _appsUISnapshot = null
    }
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
  // 只保存与默认值不同的字段，避免保存非用户配置的默认值
  useEffect(() => {
    const spaceId = user?.spaceId
    if (!spaceId) return

    const configKey = STORAGE_KEYS.AGENT_CONFIGS(spaceId)
    // 过滤：只保留与默认值不同的字段
    const filteredConfigs = Object.keys(agentConfigs).reduce((acc, agentId) => {
      const config = (agentConfigs[agentId] || {}) as unknown as Record<string, unknown>
      const defaultConfig = getDefaultDeepSearchConfigByAgentId(agentId) as unknown as Record<string, unknown>
      const diffConfig = Object.keys(config).reduce((configAcc, key) => {
        if (config[key] !== defaultConfig[key]) {
          configAcc[key] = config[key]
        }
        return configAcc
      }, {} as Record<string, unknown>)
      if (Object.keys(diffConfig).length > 0) {
        acc[agentId] = diffConfig
      }
      return acc
    }, {} as Record<string, Record<string, unknown>>)
    storage.set(configKey, filteredConfigs)
  }, [agentConfigs, user?.spaceId])

  // 当模型列表加载完成后，设置默认选中第一个模型
  useEffect(() => {
    if (models.length > 0 && !selectedModel) {
      const firstModel = models[0]
      setSelectedModel(firstModel)
      setSelectedModelId(modelIdMap.get(firstModel) || -1)
    }
  }, [models, selectedModel, modelIdMap])

  // ===== DeepSearch / DeepSearch Explorer 模式检测 =====
  useEffect(() => {
    const isDeepSearch = selectedAgent?.id === 'deepsearch'
    const isExplorer = selectedAgent?.id === 'deepsearch-explorer'
    setIsDeepSearchMode(isDeepSearch)
    setIsDeepSearchExplorerMode(isExplorer)

    // Reset Deep Search Explorer state when switching away from explorer agent
    if (!isExplorer) {
      clearDeepSearchExplorerUiState()
    }

    // 不在这里自动创建 conversation
    // 改为只在发送消息时才创建，避免产生空对话
  }, [selectedAgent])

  // ===== 对话状态同步 =====
  // 当 currentConversationId 变化时，同步本地 hasConversation 状态
  useEffect(() => {
    const hasActiveConversation = !!currentConversationId
    setHasConversation(hasActiveConversation)

    if (!hasActiveConversation) {
      setDeepSearchRunIds(new Map())
      setActiveDeepSearchRunId(null)
      setKilledDeepSearchRunIds(new Set())
    } else {
      // 如果有对话，根据对话的 agentType 自动设置智能体
      const conversation = getConversationById(currentConversationId)
      if (conversation && conversation.config?.agentType) {
        const matchedAgent = DEFAULT_AGENTS.find(a => a.id === conversation.config.agentType)
        if (matchedAgent) {
          setSelectedAgent(matchedAgent)
        }

        // Restore Deep Search Explorer runIds from conversation config
        if (conversation.config.agentType === 'deepsearch-explorer' && conversation.config.deepSearchRunIds) {
          const restoredMap = new Map<string, string>(
            Object.entries(conversation.config.deepSearchRunIds as Record<string, string>)
          )
          setDeepSearchRunIds(restoredMap)
          setKilledDeepSearchRunIds(new Set())
          restoredMap.forEach((runId) => {
            deepSearchApi.primeRunContext(runId, { spaceId: user?.spaceId || getDefaultSpaceId() })
          })
        } else {
          setDeepSearchRunIds(new Map())
          setKilledDeepSearchRunIds(new Set())
        }
      } else {
        setDeepSearchRunIds(new Map())
        setKilledDeepSearchRunIds(new Set())
      }
    }
  }, [currentConversationId, getConversationById, user?.spaceId])

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
      // SSE 正在进行中时跳过检查，避免把后台运行中的任务误标为取消
      if (useConversationStore.getState().isLoading) {
        return
      }
      // 从其他模块导航回来时跳过检查，维持切换前的状态
      // 只有刷新/关闭页面后重新加载，才执行取消逻辑
      if (_didNavigateBack) {
        _didNavigateBack = false
        return
      }
      // 幂等守卫：同一次挂载中同一对话只检查一次
      // isDeepSearchMode / selectedAgent 可能来自 localStorage 和 initializeFromDB 两条独立路径，
      // 导致此 effect 对同一 conversationId 触发两次，从而产生重复的"任务未完成"消息。
      if (abortCheckedConvIdRef.current === currentConversationId) {
        return
      }
      abortCheckedConvIdRef.current = currentConversationId
      const hasIncomplete = useConversationStore.getState().checkAndMarkIncompleteAsAbort()
      if (hasIncomplete) {
        console.log('[AppsPage] Marked incomplete messages as FAILED on page load')
      }
    }
  }, [currentConversationId, isDeepSearchMode])

  // ===== 组件卸载时：保存 UI 快照，标记为导航离开 =====
  useEffect(() => {
    return () => {
      // 标记为"导航离开"：JS 运行时存活时此标志保持，刷新/关闭后重置为 false
      _didNavigateBack = true
      const store = useConversationStore.getState()
      if (store.isLoading && store.currentConversationId) {
        // SSE 进行中：保持超时监控，保存 UI 快照以便切回时恢复
        _appsUISnapshot = {
          conversationId: store.currentConversationId,
          state: uiSnapshotRef.current,
        }
      }
      // 超时监控不在此停止：监控自身会在对话切换或触发超时时自行清理
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

      // ===== Deep Search Explorer 模式 =====
      if (isDeepSearchExplorerMode) {
        // Create conversation (like Deep Research)
        let conversationId = getReusableConversationId('deepsearch-explorer')
        if (!conversationId) {
          const title = messageToSend.length > 50 ? messageToSend.slice(0, 50) + '...' : messageToSend
          conversationId = await handleCreateConversation(title, {
            agentType: 'deepsearch-explorer',
          })
          if (!conversationId) {
            console.log('[DeepSearchExplorer] User cancelled conversation creation')
            setInputValue(messageToSend)
            return
          }
        }

        // Add user message to store — returns the MessageItems
        const userMsgItems = addUserMessage(conversationId, messageToSend)
        setHasConversation(true)
        incrementPendingDeepSearchExplorerRunCount(conversationId)

        // Create the DS run via API and store it per message
        try {
          // Build backend payload from user's saved Deep Search config
          const dsConfig = toDeepSearchExplorerConfig(agentConfigs['deepsearch-explorer'])
          const spaceId = user?.spaceId || getDefaultSpaceId()
          const backendConversationId = `${conversationId}_${userMsgItems.id}`
          const backendConfig = await buildDeepSearchBackendConfig(dsConfig, spaceId, selectedModelId)

          const result = await deepSearchApi.createRun(messageToSend, {
            ...backendConfig,
            run_id: backendConversationId,
          })

          const latestConversation = useConversationStore.getState().getConversationById(conversationId)
          if (!latestConversation) {
            try {
              await deepSearchApi.killRun(result.run_id)
            } catch (killError) {
              console.error('[DeepSearchExplorer] Failed to cancel orphaned run after conversation deletion:', killError)
            }
            return
          }

          setDeepSearchRunIds((prev) => {
            const next = new Map(prev)
            next.set(userMsgItems.id, result.run_id)
            return next
          })
          setActiveDeepSearchRunId(result.run_id)
          setKilledDeepSearchRunIds((prev) => {
            const next = new Set(prev)
            next.delete(result.run_id)
            return next
          })

          // Persist runIds in conversation.config for IndexDB recovery on refresh
          const latestDeepSearchRunIds = (
            latestConversation.config?.agentType === 'deepsearch-explorer'
            && latestConversation.config.deepSearchRunIds
            && typeof latestConversation.config.deepSearchRunIds === 'object'
            && !Array.isArray(latestConversation.config.deepSearchRunIds)
          )
            ? latestConversation.config.deepSearchRunIds as Record<string, string>
            : {}
          const configUpdate = {
            agentType: 'deepsearch-explorer',
            deepSearchRunIds: {
              ...latestDeepSearchRunIds,
              [userMsgItems.id]: result.run_id,
            },
          }
          setConversationConfig(conversationId, configUpdate)
          updateConversation(conversationId, { config: configUpdate })
          await saveConversationToDB(conversationId)
        } catch (e) {
          console.error('[DeepSearchExplorer] Failed to create run:', e)
          const errorMessage = e instanceof Error ? e.message : t('apps.chat.configError')
          window.dispatchEvent(
            new CustomEvent('global-snackbar', {
              detail: { message: errorMessage, severity: 'error' as const },
            }),
          )
        } finally {
          decrementPendingDeepSearchExplorerRunCount(conversationId)
        }
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
  /**
   * 报告局部改写处理函数
   * 复用 DeepSearch 配置，通过 SSE 流处理改写结果
   * 将改写请求和结果集成到对话流中
  */
  const handleReportRewrite = async (params: ReportRewriteParams) => {
    const { action, rewrite_scope, selectedText, displayText, startOffset, endOffset, userInstruction, conversationId, onStatusChange, onDelta, onSnapshot, onEnd, onError, silent } = params
    const actionTitle = action === 'new_task'
      ? t('apps.report.aiNewTask')
      : t('apps.report.aiSupplementarySearch')

    const config = toDeepResearchConfig(agentConfigs['deepsearch'])
    const rewriteSessionUnavailableMessage = t('apps.report.rewriteSessionUnavailable')
    const isSyncAction = action === 'sync'

    // 真实性核验：调用后端并将核验结果追加保存到 final_report message
    if (action === 'truth_verification') {
      if (config.userFeedbackProcessorEnable === false) {
        onStatusChange?.('error')
        onError?.(t('apps.report.feedbackProcessorDisabled'))
        return
      }

      const tvToken = getToken()
      if (!tvToken) {
        onError?.(t('apps.errors.unableToGetAuthToken'))
        return
      }

      const tvStore = useConversationStore.getState()
      const tvBackendConversationId = tvStore.SESSION_CONVERSATION_ID
      if (!tvBackendConversationId) {
        onStatusChange?.('error')
        onError?.(t('apps.report.rewriteSessionUnavailable'))
        return
      }

      const tvFinish = () => {
        useConversationStore.getState().stopSSETimeoutMonitor()
        onStatusChange?.('idle')
        onEnd?.()
      }
      const tvFail = (errorMsg?: string) => {
        useConversationStore.getState().stopSSETimeoutMonitor()
        onStatusChange?.('error')
        onError?.(errorMsg || t('apps.errors.requestFailed'))
      }
      const tvFinalizeRounds = () => {
        const maxInteractions = normalizeMaxRewriteInteractions(
          config.userFeedbackProcessorMaxInteractions
        )

        const syncMsgId = tvStore.selectedResultMessageId
        if (!syncMsgId) return
        const syncMsg = tvStore.messagesMap.get(syncMsgId)
        if (!syncMsg?.messageItemsId) return

        // 直接从 store 读取当前剩余次数，避免引用外层 const（TDZ）
        const currentItems = tvStore.messageItemsMap.get(syncMsg.messageItemsId)
        const currentRemaining = currentItems?.remainingRewriteRounds
        const currentMaxRounds = currentItems?.maxRewriteRounds

        const newRemaining = typeof tvFeedbackInteractionCount === 'number'
          ? Math.max(0, maxInteractions - tvFeedbackInteractionCount)
          : Math.max(0, (currentRemaining ?? maxInteractions) - 1)

        tvStore.updateMessageItems(syncMsg.messageItemsId, {
          remainingRewriteRounds: newRemaining,
          maxRewriteRounds: currentMaxRounds ?? maxInteractions,
        })
      }

      // 剥除 collector_summary 里的内部检索标记（source_id），避免泄漏到前端展示
      const stripEvidenceInternalRefs = (text: string): string =>
        text
          .replace(/[（(]\s*source_id\s*[:：][^）)]*[）)]/g, '')
          .replace(/[ \t]{2,}/g, ' ')
          .trim()

      // 将核验结论追加到当前 final_report message 的 truth_verification 列表
      const tvSave = (accumulatedContent: string, accumulatedEvidence: string) => {
        const syncMsgId = tvStore.selectedResultMessageId
        if (!syncMsgId) return
        const syncMsg = tvStore.messagesMap.get(syncMsgId)
        if (!syncMsg?.messageItemsId) return
        try {
          const rawContent = typeof syncMsg.content === 'string'
            ? syncMsg.content
            : JSON.stringify(syncMsg.content)
          const existingContent = JSON.parse(rawContent || '{}')
          const existingList = Array.isArray(existingContent.truth_verification)
            ? existingContent.truth_verification
            : []
          const evidence = stripEvidenceInternalRefs(accumulatedEvidence)
          tvStore.updateMessage(syncMsg.messageItemsId, syncMsgId, {
            content: JSON.stringify({
              ...existingContent,
              truth_verification: [
                ...existingList,
                {
                  // 批注层用可见文本做 DOM 搜索/高亮；displayText 缺省时回退到 selectedText
                  selected_text: displayText ?? selectedText,
                  start_offset: startOffset,
                  end_offset: endOffset,
                  user_instruction: userInstruction || '',
                  content: accumulatedContent,
                  ...(evidence ? { evidence } : {}),
                },
              ],
            }),
          })
          void tvStore.saveConversationToDB(conversationId)
        } catch (err) {
          console.error('[handleReportRewrite] truth_verification save failed:', err)
        }
      }

      const tvWebConfig = (config.searchMode === 'web' || config.searchMode === 'all') && config.selectedWebSearchEngineId
        ? {
            web_search_config_id: config.selectedWebSearchEngineId,
            max_web_search_results: config.webSearchResultCount,
          }
        : undefined
      const tvLocalConfig = (config.searchMode === 'local' || config.searchMode === 'all')
        ? {
            local_search_config_ids: config.selectedKnowledgeBaseIds || [],
            max_local_search_results: config.localSearchResultCount,
            recall_threshold: config.recallThreshold,
          }
        : undefined

      let tvFeedbackInteractionCount: number | undefined = undefined

      try {
        const tvResponse = await fetch('/api/v1/agent/deepsearch/run', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${tvToken}`,
          },
          body: JSON.stringify({
            space_id: user?.spaceId || getDefaultSpaceId(),
            general_model_config_id: config.generalModelId
              ? parseInt(config.generalModelId)
              : selectedModelId,
            message: JSON.stringify({
              action: 'truth_verification',
              selected_text: selectedText,
              start_offset: startOffset,
              end_offset: endOffset,
              user_instruction: userInstruction || '',
            }),
            conversation_id: tvBackendConversationId,
            search_mode: 'research',
            web_search_config: tvWebConfig,
            local_search_config: tvLocalConfig,
            user_feedback_processor_enable: config.userFeedbackProcessorEnable ?? true,
            user_feedback_processor_max_interactions: normalizeMaxRewriteInteractions(
              config.userFeedbackProcessorMaxInteractions
            ),
            execution_method: config.execution_method ?? DEFAULT_DEEPRESEARCH_CONFIG.execution_method,
          }),
        })
        if (!tvResponse.ok) {
          tvFail(`HTTP error! status: ${tvResponse.status}`)
          return
        }

        const tvReader = tvResponse.body?.getReader()
        if (!tvReader) {
          tvFail('No response body')
          return
        }

        const tvDecoder = new TextDecoder()
        let tvBuffer = ''
        let tvContent = ''
        let tvEvidence = ''

        outer: while (true) {
          const { done, value } = await tvReader.read()
          if (done) {
            tvSave(tvContent, tvEvidence)
            tvFinalizeRounds()
            tvFinish()
            break
          }

          useConversationStore.getState().updateLastSSEEventTime()

          const tvRaw = tvBuffer + tvDecoder.decode(value, { stream: true })
          const tvLines = tvRaw.split('\n')
          tvBuffer = tvLines.pop() || ''

          for (const line of tvLines) {
            if (!line.startsWith('data: ')) continue
            try {
              const tvData = JSON.parse(line.slice(6)) as {
                agent?: string
                content?: unknown
                event?: string
              }

              // 收集核验结论和已用交互次数（summary_response 为单条）
              // 必须限定 event === 'summary_response'：流末尾的 waiting_user_input
              // 同样是 user_feedback_processor + 字符串 content（"\nProvide your feedback: "），
              // 不过滤会把真正的结论覆盖掉。对齐 AI 改写忽略该事件的处理方式。
              if (
                tvData.agent === 'user_feedback_processor' &&
                tvData.event === 'summary_response'
              ) {
                if (typeof tvData.content === 'string') {
                  // 先当作纯文本赋值，再尝试解析 JSON 覆盖
                  tvContent = tvData.content
                  try {
                    const parsed = JSON.parse(tvData.content) as {
                      display_text?: string
                      feedback_interaction_count?: number
                    }
                    // 新格式 JSON 字符串：有 display_text 则用它替换原始 JSON 字符串
                    if (typeof parsed.display_text === 'string') {
                      tvContent = parsed.display_text
                    }
                    if (typeof parsed.feedback_interaction_count === 'number') {
                      tvFeedbackInteractionCount = parsed.feedback_interaction_count
                    }
                  } catch { /* 纯文本核验结论，无需解析 */ }
                } else if (typeof tvData.content === 'object' && tvData.content !== null) {
                  // content 直接为对象格式：{ display_text, feedback_interaction_count }
                  const obj = tvData.content as { display_text?: string; feedback_interaction_count?: number }
                  if (typeof obj.display_text === 'string') {
                    tvContent = obj.display_text
                  }
                  if (typeof obj.feedback_interaction_count === 'number') {
                    tvFeedbackInteractionCount = obj.feedback_interaction_count
                  }
                }
              }

              // 收集检索证据说明（collector_summary，单条）。
              // 证据不足时结论很简短，详细的检索/未命中说明在这条里。
              if (
                tvData.agent === 'collector_summary' &&
                tvData.event === 'summary_response' &&
                typeof tvData.content === 'string'
              ) {
                tvEvidence = tvData.content
              }

              // 正常终止
              if (tvData.agent === 'end' && tvData.content === 'ALL END') {
                tvSave(tvContent, tvEvidence)
                tvFinalizeRounds()
                void tvReader.cancel()
                tvFinish()
                break outer
              }

              // 后端错误事件
              if (tvData.event === 'error') {
                void tvReader.cancel()
                tvFail(typeof tvData.content === 'string' ? tvData.content : undefined)
                break outer
              }
            } catch {
              // JSON 解析失败，跳过当前行
            }
          }
        }
      } catch (err) {
        tvFail(err instanceof Error ? err.message : undefined)
      }

      return
    }

    if (config.userFeedbackProcessorEnable === false) {
      onStatusChange?.('error')
      onError?.(t('apps.report.feedbackProcessorDisabled'))
      return
    }

    const token = getToken()
    const conversationStore = useConversationStore.getState()

    // For sync: immediately write the edited markdown to the store and IndexDB.
    // The backend only returns {"action_category":"sync","synced":true} — no final_result —
    // so we cannot rely on applyRewriteFinalResult to do this update.
    if (isSyncAction) {
      const syncMsgId = conversationStore.selectedResultMessageId
      if (syncMsgId) {
        const syncMsg = conversationStore.messagesMap.get(syncMsgId)
        if (syncMsg?.messageItemsId) {
          try {
            const rawContent = typeof syncMsg.content === 'string'
              ? syncMsg.content
              : JSON.stringify(syncMsg.content)
            const existingContent = JSON.parse(rawContent || '{}')
            conversationStore.updateMessage(
              syncMsg.messageItemsId,
              syncMsgId,
              {
                content: JSON.stringify({ ...existingContent, response_content: selectedText }),
                status: TaskStatus.COMPLETED,
                isStreaming: false,
              }
            )
            void conversationStore.saveConversationToDB(conversationId)
          } catch (err) {
            console.error('[handleReportRewrite] sync local save failed:', err)
          }
        }
      }
    }

    if (!token) {
      onError?.(t('apps.errors.unableToGetAuthToken'))
      return
    }

    const sessionConversationId = conversationStore.SESSION_CONVERSATION_ID
    if (!sessionConversationId) {
      onStatusChange?.('error')
      onError?.(rewriteSessionUnavailableMessage)
      return
    }
    const backendConversationId = sessionConversationId
    const currentSelectedResultMessageId = conversationStore.selectedResultMessageId

    // 读取当前（改写前）最终报告的 truth_verification 数据，供非 sync 改写继承使用
    const getPreviousTruthVerification = (): TruthVerificationEntry[] => {
      if (!currentSelectedResultMessageId) return []
      const prevMsg = conversationStore.messagesMap.get(currentSelectedResultMessageId)
      if (!prevMsg?.content) return []
      try {
        const raw = typeof prevMsg.content === 'string' ? prevMsg.content : JSON.stringify(prevMsg.content)
        const parsed = JSON.parse(raw || '{}')
        return Array.isArray(parsed.truth_verification) ? parsed.truth_verification as TruthVerificationEntry[] : []
      } catch { return [] }
    }

    type RewriteRoundContext = {
      originalRemainingRewriteRounds: number | undefined
      originalMaxRewriteRounds: number | undefined
    }
    const getOriginalRewriteRoundContext = (): RewriteRoundContext => {
      if (!conversationStore.selectedResultMessageId) {
        return {
          originalRemainingRewriteRounds: undefined,
          originalMaxRewriteRounds: undefined,
        }
      }

      const currentMessage = conversationStore.messagesMap.get(conversationStore.selectedResultMessageId)
      const currentMessageItems = currentMessage?.messageItemsId
        ? conversationStore.messageItemsMap.get(currentMessage.messageItemsId)
        : undefined

      return {
        originalRemainingRewriteRounds: currentMessageItems?.remainingRewriteRounds,
        originalMaxRewriteRounds: currentMessageItems?.maxRewriteRounds,
      }
    }
    const { originalRemainingRewriteRounds, originalMaxRewriteRounds } = getOriginalRewriteRoundContext()

    if (!silent) {
      const userMessageContent = buildRewriteUserMessage(t, action, selectedText, userInstruction, rewrite_scope)
      addUserMessage(conversationId, userMessageContent)
    }

    type RewriteRequestContext = {
      messagePayload: {
        action: ReportRewriteParams['action']
        rewrite_scope: ReportRewriteParams['rewrite_scope']
        selected_text: string
        start_offset: number
        end_offset: number
        user_instruction: string
      }
      rewriteRequest: {
        action: ReportRewriteParams['action']
        rewrite_scope: ReportRewriteParams['rewrite_scope']
        selectedText: string
        startOffset: number
        endOffset: number
        userInstruction?: string
      }
      local_search_config: {
        local_search_config_ids: string[]
        max_local_search_results: number
        recall_threshold: number
      } | undefined
      web_search_config: {
        web_search_config_id: number
        max_web_search_results: number
      } | undefined
    }
    const createRewriteRequestContext = (): RewriteRequestContext => ({
      messagePayload: {
        action,
        rewrite_scope: rewrite_scope,
        selected_text: selectedText,
        start_offset: startOffset,
        end_offset: endOffset,
        user_instruction: userInstruction || '',
      },
      rewriteRequest: {
        action,
        rewrite_scope: rewrite_scope,
        selectedText,
        startOffset,
        endOffset,
        userInstruction,
      },
      local_search_config: (config.searchMode === 'local' || config.searchMode === 'all')
        ? {
            local_search_config_ids: config.selectedKnowledgeBaseIds || [],
            max_local_search_results: config.localSearchResultCount,
            recall_threshold: config.recallThreshold,
          }
        : undefined,
      web_search_config: (config.searchMode === 'web' || config.searchMode === 'all') && config.selectedWebSearchEngineId
        ? {
            web_search_config_id: config.selectedWebSearchEngineId,
            max_web_search_results: config.webSearchResultCount,
          }
        : undefined,
    })
    const { messagePayload, rewriteRequest, local_search_config, web_search_config } = createRewriteRequestContext()
    const rewriteFeedbackAgent = 'user_feedback_processor'
    type RewriteRuntimeState = {
      finalResultMessageId: string | null
      hasReceivedContent: boolean
      collectorTaskMessageId: string | null
      collectorTaskMessageItemsId: string | null
    }
    type RewriteProcessResult = {
      status: 'continue' | 'completed' | 'error'
      error?: string
    }
    type RewriteHandleOptions = {
      stop?: () => Promise<void>
      logError?: boolean
    }
    type RewriteEventConsumer = (events: RewriteEventData[]) => Promise<boolean>
    type RewriteEventData = {
      agent?: string
      content?: unknown
    }
    type RewriteFinalResult = {
      response_content: string
      citation_messages?: unknown
      infer_messages?: unknown[]
      chart_messages?: unknown[]
    }
    type RewriteReportMessage = {
      id: string
      messageItemsId: string
    }
    type RewriteAgentContent = {
      error?: string
      rewritten_text?: string
      original_start_offset?: number
      original_end_offset?: number
      final_result?: RewriteFinalResult
    }
    type RewriteChunkParseResult = {
      events: RewriteEventData[]
      remainingBuffer: string
    }
    type RewriteChunkConsumeResult = {
      handled: boolean
      remainingBuffer: string
    }
    type LiveRewriteRuntime = {
      controller: AbortController
      stop: () => Promise<void>
      consumeEvents: RewriteEventConsumer
    }
    const parseRewriteAgentContent = (rawContent: string): RewriteAgentContent | null => {
      try {
        return JSON.parse(rawContent) as RewriteAgentContent
      } catch {
        return null
      }
    }
    const parseRewriteEventData = (rawData: string): RewriteEventData | null => {
      try {
        return JSON.parse(rawData) as RewriteEventData
      } catch {
        return null
      }
    }
    const buildRewriteReportContent = (finalResult: RewriteFinalResult) => ({
      response_content: finalResult.response_content,
      citation_messages: finalResult.citation_messages || null,
      infer_messages: finalResult.infer_messages || [],
      chart_messages: finalResult.chart_messages || [],
    })
    const createRewriteReportMessage = (reportContent: ReturnType<typeof buildRewriteReportContent>): RewriteReportMessage | null => {
      const newMessage = addSystemMessage(
        conversationId,
        MessageType.REPORT,
        JSON.stringify(reportContent),
        undefined,
        MESSAGE_TITLES.FINAL_REPORT,
        'deepsearch'
      )

      return newMessage
        ? { id: newMessage.id, messageItemsId: newMessage.messageItemsId }
        : null
    }
    const finalizeRewriteReportMessage = (message: RewriteReportMessage) => {
      setSelectedResultMessageId(message.id)

      const { maxInteractions, newRemaining } = getRewriteRoundState(
        config.userFeedbackProcessorMaxInteractions,
        originalRemainingRewriteRounds
      )
      const remainingRewriteRounds = isSyncAction
        ? originalRemainingRewriteRounds ?? maxInteractions
        : newRemaining

      conversationStore.updateMessage(
        message.messageItemsId,
        message.id,
        { status: TaskStatus.COMPLETED, isStreaming: false }
      )

      conversationStore.updateMessageItems(
        message.messageItemsId,
        {
          status: TaskStatus.COMPLETED,
          remainingRewriteRounds,
          maxRewriteRounds: originalMaxRewriteRounds ?? maxInteractions
        }
      )
    }
    const updateCurrentRewriteReportMessage = (reportContent: ReturnType<typeof buildRewriteReportContent>) => {
      if (!currentSelectedResultMessageId) {
        return false
      }

      const currentMessage = conversationStore.messagesMap.get(currentSelectedResultMessageId)
      if (!currentMessage?.messageItemsId) {
        return false
      }

      // 合并现有 truth_verification，防止被覆盖丢失
      let existingTruthVerification: unknown[] = []
      try {
        const raw = typeof currentMessage.content === 'string'
          ? currentMessage.content
          : JSON.stringify(currentMessage.content)
        const existing = JSON.parse(raw || '{}')
        if (Array.isArray(existing.truth_verification)) {
          existingTruthVerification = existing.truth_verification
        }
      } catch { /* ignore */ }

      conversationStore.updateMessage(
        currentMessage.messageItemsId,
        currentSelectedResultMessageId,
        {
          content: JSON.stringify({
            ...reportContent,
            ...(existingTruthVerification.length > 0 ? { truth_verification: existingTruthVerification } : {}),
          }),
          status: TaskStatus.COMPLETED,
          isStreaming: false,
        }
      )
      return true
    }
    const applyRewriteFinalResult = (finalResult: RewriteFinalResult, state: Pick<RewriteRuntimeState, 'finalResultMessageId'>) => {
      onSnapshot?.({ response_content: finalResult.response_content })
      const reportContent = buildRewriteReportContent(finalResult)

      if (isSyncAction && updateCurrentRewriteReportMessage(reportContent)) {
        return
      }

      if (!state.finalResultMessageId) {
        // AI 改写产生新报告时，从旧报告继承 truth_verification 并按新内容筛选
        const prevEntries = getPreviousTruthVerification()
        const inheritedEntries = prevEntries.filter(e =>
          truthVerificationEntryExistsInContent(e.selected_text, finalResult.response_content)
        )
        const contentToSave = inheritedEntries.length > 0
          ? { ...reportContent, truth_verification: inheritedEntries }
          : reportContent
        const newMessage = createRewriteReportMessage(contentToSave as Parameters<typeof createRewriteReportMessage>[0])
        if (newMessage) {
          state.finalResultMessageId = newMessage.id
          finalizeRewriteReportMessage(newMessage)
        }
      }
    }
    const applyRewriteContent = (
      content: RewriteAgentContent,
      state: RewriteRuntimeState
    ): RewriteProcessResult => {
      if (content.error) {
        return { status: 'error', error: content.error }
      }

      if (typeof content.rewritten_text === 'string') {
        if (!state.hasReceivedContent) {
          state.hasReceivedContent = true
          onStatusChange?.('writing')
        }

        onDelta?.({
          rewritten_text: content.rewritten_text,
          original_start_offset: content.original_start_offset ?? 0,
          original_end_offset: content.original_end_offset ?? content.rewritten_text.length,
        })
      }

      if (content.final_result && typeof content.final_result.response_content === 'string') {
        applyRewriteFinalResult(content.final_result, state)
      }

      return { status: 'continue' }
    }
    const processRewriteEvent = (
      data: RewriteEventData,
      state: RewriteRuntimeState
    ): RewriteProcessResult => {
      // 处理结束
      if (data.agent === 'end' && data.content === 'ALL END') {
        return { status: 'completed' }
      }

      // 处理 collector_info_retrieval 事件
      if (data.agent === 'collector_info_retrieval' && typeof data.content === 'string') {
        // 创建或获取根任务
        if (!state.collectorTaskMessageId) {
          const taskMessage = addSystemMessage(
            conversationId,
            MessageType.TASK,
            '',
            undefined,
            actionTitle,
            'deepsearch'
          )
          if (taskMessage) {
            state.collectorTaskMessageId = taskMessage.id
            state.collectorTaskMessageItemsId = taskMessage.messageItemsId
            conversationStore.updateMessage(
              taskMessage.messageItemsId,
              taskMessage.id,
              { status: TaskStatus.IN_PROGRESS, isStreaming: false }
            )
          }
        }

        // 添加 link 子消息
        if (state.collectorTaskMessageId && state.collectorTaskMessageItemsId) {
          try {
            const linkContent = JSON.parse(data.content)
            const childMessage = conversationStore.addMessageAsChild(
              state.collectorTaskMessageItemsId,
              state.collectorTaskMessageId,
              MessageType.LINK,
              linkContent,
              `collector_info_retrieval: ${linkContent.title || t('apps.deepSearch.searchResults')}`
            )
            if (childMessage) {
              conversationStore.updateMessage(
                childMessage.messageItemsId,
                childMessage.id,
                { status: TaskStatus.COMPLETED, isStreaming: false }
              )
            }
          } catch (e) {
            console.error('[handleReportRewrite] Failed to parse collector_info_retrieval content:', e)
          }
        }
        return { status: 'continue' }
      }

      // 处理 collector_summary 事件
      if (data.agent === 'collector_summary' && typeof data.content === 'string') {
        if (state.collectorTaskMessageId && state.collectorTaskMessageItemsId) {
          const childMessage = conversationStore.addMessageAsChild(
            state.collectorTaskMessageItemsId,
            state.collectorTaskMessageId,
            MessageType.TEXT,
            data.content,
            t('apps.deepSearch.informationSummary')
          )
          if (childMessage) {
            conversationStore.updateMessage(
              childMessage.messageItemsId,
              childMessage.id,
              { status: TaskStatus.COMPLETED, isStreaming: false }
            )
            // 更新根任务状态为完成
            conversationStore.updateMessage(
              childMessage.messageItemsId,
              state.collectorTaskMessageId,
              { status: TaskStatus.COMPLETED }
            )
          }
        }
        return { status: 'continue' }
      }

      // 处理 user_feedback_processor 事件（最终报告）
      if (data.agent !== rewriteFeedbackAgent || typeof data.content !== 'string') {
        return { status: 'continue' }
      }

      const content = parseRewriteAgentContent(data.content)
      if (content) {
        return applyRewriteContent(content, state)
      }

      return { status: 'continue' }
    }
    const createRewriteState = (): RewriteRuntimeState => ({
      finalResultMessageId: null,
      hasReceivedContent: false,
      collectorTaskMessageId: null,
      collectorTaskMessageItemsId: null,
    })
    const finishRewrite = () => {
      useConversationStore.getState().stopSSETimeoutMonitor()
      onStatusChange?.('idle')
      onEnd?.()
    }
    const failRewrite = async (
      error: string | undefined,
      options?: RewriteHandleOptions
    ) => {
      const errorMessage = error || t('apps.errors.requestFailed')
      if (options?.logError) {
        console.error('[handleReportRewrite] Backend error:', errorMessage)
      }
      await options?.stop?.()
      useConversationStore.getState().stopSSETimeoutMonitor()
      onStatusChange?.('error')
      onError?.(errorMessage)
    }
    const handleRewriteResult = async (
      result: RewriteProcessResult,
      options?: RewriteHandleOptions
    ) => {
      if (result.status === 'completed') {
        await options?.stop?.()
        finishRewrite()
        return true
      }

      if (result.status === 'error') {
        await failRewrite(result.error, options)
        return true
      }

      return false
    }
    const handleRewriteData = async (
      data: RewriteEventData,
      state: RewriteRuntimeState,
      options?: RewriteHandleOptions
    ) => handleRewriteResult(processRewriteEvent(data, state), options)
    const consumeRewriteEvents = async (
      events: RewriteEventData[],
      state: RewriteRuntimeState,
      options?: RewriteHandleOptions,
      beforeHandle?: (data: RewriteEventData) => void
    ) => {
      for (const data of events) {
        beforeHandle?.(data)
        const handled = await handleRewriteData(data, state, options)
        if (handled) {
          return true
        }
      }

      return false
    }
    const createRewriteEventConsumer = (
      state: RewriteRuntimeState,
      options?: RewriteHandleOptions,
      beforeHandle?: (data: RewriteEventData) => void
    ): RewriteEventConsumer => {
      return (events) => consumeRewriteEvents(events, state, options, beforeHandle)
    }
    const createMockedRewriteEventConsumer = (): RewriteEventConsumer => createRewriteEventConsumer(
      createRewriteState()
    )
    const runRewriteEventSequence = async (
      events: RewriteEventData[],
      consumeEvents: RewriteEventConsumer,
      onUnhandled?: () => void | Promise<void>
    ) => {
      const handled = await consumeEvents(events)
      if (!handled) {
        await onUnhandled?.()
      }

      return handled
    }
    const collectMockedRewriteEvents = async () => {
      const mockedEvents: RewriteEventData[] = []
      const mocked = await tryMockRewrite(rewriteRequest, (event) => {
        mockedEvents.push(event.data)
      })

      return { mocked, mockedEvents }
    }
    const parseRewriteChunkEvents = (
      chunk: Uint8Array,
      decoder: TextDecoder,
      currentBuffer: string
    ): RewriteChunkParseResult => {
      const nextBuffer = currentBuffer + decoder.decode(chunk, { stream: true })
      const lines = nextBuffer.split('\n')
      const remainingBuffer = lines.pop() || ''
      const events: RewriteEventData[] = []

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue

        const data = parseRewriteEventData(line.slice(6))
        if (data) {
          events.push(data)
        }
      }

      return { events, remainingBuffer }
    }
    const runMockedRewriteEvents = async (events: RewriteEventData[]) => {
      const consumeMockedRewriteEvents = createMockedRewriteEventConsumer()
      await runRewriteEventSequence(events, consumeMockedRewriteEvents, finishRewrite)
      return true
    }
    const runMockedRewrite = async () => {
      const { mocked, mockedEvents } = await collectMockedRewriteEvents()

      if (!mocked) {
        return false
      }

      return runMockedRewriteEvents(mockedEvents)
    }

    if (await runMockedRewrite()) {
      return
    }

    const createLiveRewriteRuntime = (): LiveRewriteRuntime => {
      const controller = new AbortController()
      _activeRewriteController = controller
      const rewriteRecording = createRewriteRecording({
        enabled: ENABLE_SSE_DEBUG,
        request: rewriteRequest,
      })
      const stop = async () => {
        if (_activeRewriteController === controller) {
          _activeRewriteController = null
        }
        controller.abort()
        await rewriteRecording?.stop()
      }

      return {
        controller,
        stop,
        consumeEvents: createRewriteEventConsumer(
          createRewriteState(),
          { stop, logError: true },
          (data) => rewriteRecording?.record(data as SSEData)
        ),
      }
    }
    const requestLiveRewriteStream = async (signal: AbortSignal) => {
      const response = await fetch('/api/v1/agent/deepsearch/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          space_id: user?.spaceId || getDefaultSpaceId(),
          general_model_config_id: config.generalModelId ? parseInt(config.generalModelId) : selectedModelId,
          message: JSON.stringify(messagePayload),
          conversation_id: backendConversationId,
          // 保留搜索配置（续写时后端会根据 conversation_id 恢复 workflow 状态）
          search_mode: 'research',
          web_search_config,
          local_search_config,
          // 报告局部改写配置
          user_feedback_processor_enable: config.userFeedbackProcessorEnable ?? true,
          user_feedback_processor_max_interactions: config.userFeedbackProcessorMaxInteractions ?? 3,
          execution_method: config.execution_method ?? DEFAULT_DEEPRESEARCH_CONFIG.execution_method,
        }),
        signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      return reader
    }
    const consumeLiveRewriteChunk = async (
      chunk: Uint8Array,
      decoder: TextDecoder,
      currentBuffer: string,
      consumeEvents: RewriteEventConsumer
    ): Promise<RewriteChunkConsumeResult> => {
      const parsedChunk = parseRewriteChunkEvents(chunk, decoder, currentBuffer)
      const handled = await runRewriteEventSequence(parsedChunk.events, consumeEvents)

      return {
        handled,
        remainingBuffer: parsedChunk.remainingBuffer,
      }
    }
    const finishLiveRewriteStream = async (stop: () => Promise<void>) => {
      await stop()
      onEnd?.()
    }
    const consumeLiveRewriteStream = async (
      reader: ReadableStreamDefaultReader<Uint8Array>,
      runtime: LiveRewriteRuntime
    ) => {
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          await finishLiveRewriteStream(runtime.stop)
          break
        }

        useConversationStore.getState().updateLastSSEEventTime()

        const chunkResult = await consumeLiveRewriteChunk(value, decoder, buffer, runtime.consumeEvents)
        buffer = chunkResult.remainingBuffer

        if (chunkResult.handled) {
          return
        }
      }
    }
    const liveRewriteRuntime = createLiveRewriteRuntime()
    const runLiveRewrite = async () => {
      const reader = await requestLiveRewriteStream(liveRewriteRuntime.controller.signal)
      await consumeLiveRewriteStream(reader, liveRewriteRuntime)
    }

    try {
      await runLiveRewrite()
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        await liveRewriteRuntime.stop()
        onStatusChange?.('idle')
        return
      }
      await failRewrite(err instanceof Error ? err.message : undefined, {
        stop: liveRewriteRuntime.stop,
      })
    }
  }
  // 处理智能体选择（首次配置弹出配置弹窗，非首次配置直接选中）
  const handleAgentSelect = async (agent: MentionItem) => {
    // 会话已开始：禁止切换 Agent，给出提示
    if (isAgentLocked) {
      window.dispatchEvent(new CustomEvent('global-snackbar', {
        detail: {
          message: t('apps.agent.switchLockedHint', { agentName: selectedAgent?.name ?? '' }),
          severity: 'warning',
        },
      }))
      return
    }
    const activeModuleAgentId = getConversationAgentType(currentConversationId) ?? selectedAgent?.id ?? null
    const isCrossModuleSwitch = !!activeModuleAgentId && activeModuleAgentId !== agent.id

    if (isCrossModuleSwitch) {
      await interruptModuleTasks(activeModuleAgentId)
      await handleDeepSearchExplorerLeave(
        'agent-switch',
        { deepSearchRunIds, activeDeepSearchRunId, killedDeepSearchRunIds },
        deepSearchApi.killRun,
      )
      resetModuleSessionState()
    }

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
  const handleSaveAgentConfig = (agentId: string, config: DeepSearchConfig | DeepSearchExplorerConfig) => {
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

  const handleClearDeepSearchProviderCredentials = (
    agentId: string,
    config: DeepSearchExplorerConfig,
  ) => {
    setAgentConfigs(prev => ({
      ...prev,
      [agentId]: config,
    }))
  }

  // 取消选择智能体
  const handleAgentDeselect = async () => {
    // 会话已开始：禁止取消 Agent，给出提示
    if (isAgentLocked) {
      window.dispatchEvent(new CustomEvent('global-snackbar', {
        detail: {
          message: t('apps.agent.switchLockedHint', { agentName: selectedAgent?.name ?? '' }),
          severity: 'warning',
        },
      }))
      return
    }
    const activeModuleAgentId = getConversationAgentType(currentConversationId) ?? selectedAgent?.id ?? null
    await interruptModuleTasks(activeModuleAgentId)
    await handleDeepSearchExplorerLeave(
      'agent-deselect',
      { deepSearchRunIds, activeDeepSearchRunId, killedDeepSearchRunIds },
      deepSearchApi.killRun,
    )
    resetModuleSessionState()
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

  const deepResearchSavedConfigs = React.useMemo(() => ({
    deepsearch: toDeepResearchConfig(agentConfigs['deepsearch']),
  }), [agentConfigs])

  const deepSearchExplorerSavedConfigs = React.useMemo(() => ({
    'deepsearch-explorer': toDeepSearchExplorerConfig(agentConfigs['deepsearch-explorer']),
  }), [agentConfigs])

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

    // 同步到智能体配置的通用模型（deepsearch / deepsearch-explorer）
    if ((selectedAgent?.id === 'deepsearch' || selectedAgent?.id === 'deepsearch-explorer') && modelId !== -1) {
      const agentId = selectedAgent.id
      setAgentConfigs(prev => ({
        ...prev,
        [agentId]: {
          ...getDefaultDeepSearchConfigByAgentId(agentId),
          ...prev[agentId],
          generalModelId: String(modelId),
        }
      }))
    }
  }

  // 发起新对话
  const handleNewConversation = async () => {
    const activeModuleAgentId = getConversationAgentType(currentConversationId) ?? selectedAgent?.id ?? null
    await interruptModuleTasks(activeModuleAgentId)
    await handleDeepSearchExplorerLeave(
      'new-conversation',
      { deepSearchRunIds, activeDeepSearchRunId, killedDeepSearchRunIds },
      deepSearchApi.killRun,
    )
    resetModuleSessionState()
  }

  // 当selectedResultMessageId变化时，自动关闭思维链面板并更新currentMessageItemsId
  useEffect(() => {
    if (selectedResultMessageId) {
      setShowMindMap(false)
      setMindMapMessageItemsId(null)
      // 更新currentMessageItemsId为当前报告所属的messageItemsId
      const messageItemsId = getCurrentMessageItemsId
      setCurrentMessageItemsId(messageItemsId)
    }
  }, [selectedResultMessageId, getCurrentMessageItemsId])

  // 当思维链数据开始生成时，自动打开思维链视图
  // 使用 messageItemsList 来获取当前对话中最新的 messageItemsId
  const prevMindMapSizeRef = useRef(mindMapManagersMap.size)

  useEffect(() => {
    // 检查 mindMapManagersMap 是否有新增条目
    if (mindMapManagersMap.size <= prevMindMapSizeRef.current) {
      prevMindMapSizeRef.current = mindMapManagersMap.size
      return
    }
    prevMindMapSizeRef.current = mindMapManagersMap.size

    // 找到最新创建的 mindMap 对应的 messageItemsId
    if (!currentConversationId || selectedResultMessageId) {
      return
    }

    // 获取当前会话的 messageItems
    const conversationMessageItems = getMessageItemsByConversationId(currentConversationId)
    const latestMessageItems = conversationMessageItems
      .sort((a, b) => b.createdAt - a.createdAt)[0]

    if (!latestMessageItems) return

    // 检查这个 messageItems 是否有 mindMap
    if (mindMapManagersMap.has(latestMessageItems.id)) {
      // 检查当前显示的思维链是否属于当前会话
      // 如果不属于当前会话，需要先关闭再打开新的
      const currentMindMapBelongsToCurrentConversation = mindMapMessageItemsId &&
        conversationMessageItems.some(mi => mi.id === mindMapMessageItemsId)

      if (showMindMap && !currentMindMapBelongsToCurrentConversation) {
        setShowMindMap(false)
        setMindMapMessageItemsId(null)
        setCurrentMessageItemsId(null)
        // 使用 setTimeout 确保状态更新后再打开
        setTimeout(() => {
          setMindMapMessageItemsId(latestMessageItems.id)
          setCurrentMessageItemsId(latestMessageItems.id)
          setShowMindMap(true)
        }, 0)
      } else if (!showMindMap) {
        setMindMapMessageItemsId(latestMessageItems.id)
        setCurrentMessageItemsId(latestMessageItems.id)
        setShowMindMap(true)
      }
    }
  }, [mindMapManagersMap, currentConversationId, selectedResultMessageId, showMindMap, mindMapMessageItemsId, getMessageItemsByConversationId])

  // 深度研究进行中时申请 Screen Wake Lock，降低设备自动息屏导致 SSE 中断的概率
  // 注意：页面切到后台（visibilitychange -> hidden）时锁会被浏览器自动释放，
  // 重新变为可见时需要重新申请；不支持该 API 的浏览器（如 Firefox）直接静默跳过
  useEffect(() => {
    if (!isStreaming) return
    if (!('wakeLock' in navigator)) return

    let sentinel: WakeLockSentinel | null = null
    let cancelled = false

    const requestWakeLock = async () => {
      try {
        const lock = await navigator.wakeLock.request('screen')
        if (cancelled) {
          lock.release().catch(() => {})
          return
        }
        sentinel = lock
      } catch (err) {
        // 请求失败（如非安全上下文、浏览器拒绝等），静默降级，不影响主流程
        console.warn('[WakeLock] request failed:', err)
      }
    }

    requestWakeLock()

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !sentinel) {
        requestWakeLock()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      if (sentinel) {
        sentinel.release().catch(() => {})
        sentinel = null
      }
    }
  }, [isStreaming])

  // 打开思维链面板
  const handleOpenMindMap = (messageItemsId: string) => {
    // 如果当前已经在显示思维链且是同一个messageItemsId，关闭思维链面板
    if (showMindMap && mindMapMessageItemsId === messageItemsId) {
      setShowMindMap(false)
      setMindMapMessageItemsId(null)
      setCurrentMessageItemsId(null)
      setLastSelectedReportId(null)
    } else {
      // 保存当前选中的报告ID
      if (selectedResultMessageId) {
        setLastSelectedReportId(selectedResultMessageId)
      }
      // 否则打开思维链面板
      setMindMapMessageItemsId(messageItemsId)
      setCurrentMessageItemsId(messageItemsId)
      setShowMindMap(true)
      setSelectedResultMessageId(null) // 清除报告选择，避免状态冲突
    }
  }

  // 关闭思维链面板
  const handleCloseMindMap = () => {
    setShowMindMap(false)
    setMindMapMessageItemsId(null)
    setCurrentMessageItemsId(null)
    setLastSelectedReportId(null)
    setCurrentGraphType('sectionGraph')
  }

  // 关闭右侧面板（共用）
  const handleCloseRightPanel = () => {
    setShowMindMap(false)
    setMindMapMessageItemsId(null)
    setSelectedResultMessageId(null)
    setCurrentMessageItemsId(null)
    setLastSelectedReportId(null)
    setCurrentGraphType('sectionGraph')
  }

  // ===== 视图切换逻辑 =====
  // 派生当前视图类型
  const activeView: ViewType = showMindMap ? 'thinking' : 'report'

  // 视图切换处理函数
  const handleViewChange = useCallback((view: ViewType) => {
    const currentId = mindMapMessageItemsId || currentMessageItemsId || getCurrentMessageItemsId
    if (!currentId) return

    if (view === 'thinking') {
      // 切换到思维链
      if (selectedResultMessageId) {
        setLastSelectedReportId(selectedResultMessageId)
      }
      setMindMapMessageItemsId(currentId)
      setCurrentMessageItemsId(currentId)
      setShowMindMap(true)
      setSelectedResultMessageId(null)
    } else {
      // 切换到报告
      setShowMindMap(false)
      setMindMapMessageItemsId(null)
      setCurrentMessageItemsId(currentId)
      if (lastSelectedReportId) {
        setSelectedResultMessageId(lastSelectedReportId)
      } else {
        // 查找当前 messageItems 中的报告消息
        const messageItems = messageItemsMap.get(currentId)
        if (messageItems) {
          const messages = messageItems.messagesIds.map(id => getMessageById(id)).filter((msg): msg is NonNullable<typeof msg> => msg !== undefined)
          const reportMessage = messages.find(msg => msg.type === MessageType.REPORT)
          if (reportMessage) {
            setSelectedResultMessageId(reportMessage.id)
          }
        }
      }
    }
  }, [mindMapMessageItemsId, currentMessageItemsId, getCurrentMessageItemsId, selectedResultMessageId, lastSelectedReportId, messageItemsMap, getMessageById])

  // ===== TopToolbar 渲染条件（使用 useMemo 稳定渲染） =====
  const toolbarState = useMemo(() => {
    const currentId = mindMapMessageItemsId || currentMessageItemsId || getCurrentMessageItemsId
    if (!currentId) return { show: false, disabledViews: [] as ViewType[] }

    const messageItems = messageItemsMap.get(currentId)
    const hasReport = messageItems?.messagesIds.some(id => {
      const message = getMessageById(id)
      return message && message.type === MessageType.REPORT
    })
    const hasMindMap = mindMapManagersMap.has(currentId)

    // 显示 TopToolbar 的条件：有报告或有思维链
    // 注意：AI 改写产生的报告没有 mindMap，所以不能只检查 hasMindMap
    if (!hasReport && !hasMindMap) return { show: false, disabledViews: [] as ViewType[] }

    return {
      show: true,
      // 如果没有报告，禁用报告视图；如果没有思维链，禁用思维链视图
      disabledViews: [
        ...(hasReport ? [] : ['report'] as ViewType[]),
        ...(hasMindMap ? [] : ['thinking'] as ViewType[]),
      ]
    }
  }, [mindMapMessageItemsId, currentMessageItemsId, getCurrentMessageItemsId, mindMapManagersMap, messageItemsMap, getMessageById])

  // 切换历史对话
  const handleConversationSelect = async (conversationId: string) => {
    await interruptModuleTasks(getConversationAgentType(currentConversationId) ?? selectedAgent?.id ?? null)
    await handleDeepSearchExplorerLeave(
      'conversation-switch',
      { deepSearchRunIds, activeDeepSearchRunId, killedDeepSearchRunIds },
      deepSearchApi.killRun,
    )

    // 清除选择的结果面板和思维链面板（修复bug：切换对话时需要清除，否则会导致页面空白）
    setSelectedResultMessageId(null)
    setShowMindMap(false)
    setMindMapMessageItemsId(null)
    setCurrentMessageItemsId(null)
    setLastSelectedReportId(null)
    setCurrentGraphType('sectionGraph')

    // Reset Deep Search Explorer state on conversation switch
    clearDeepSearchExplorerUiState({ clearKilledRunIds: true })

    // 重置思维链大小追踪 ref，防止切换会话后自动打开错误的思维链
    prevMindMapSizeRef.current = mindMapManagersMap.size

    // 切换对话（异步加载）
    await switchConversation(conversationId)

    // ===== 检查新对话是否有未完成的消息 =====
    const conversation = getConversationById(conversationId)
    if (conversation?.config?.agentType === 'deepsearch') {
      // 等待一帧，确保数据已加载
      requestAnimationFrame(() => {
        const hasIncomplete = useConversationStore.getState().checkAndMarkIncompleteAsAbort()
        if (hasIncomplete) {
          console.log('[AppsPage] Marked incomplete messages as FAILED on conversation switch')
        }
      })
    }

    // ===== Restore Deep Search Explorer runIds from conversation config =====
    if (conversation?.config?.agentType === 'deepsearch-explorer' && conversation.config.deepSearchRunIds) {
      const restoredMap = new Map<string, string>(
        Object.entries(conversation.config.deepSearchRunIds as Record<string, string>)
      )
      setDeepSearchRunIds(restoredMap)
      restoredMap.forEach((runId) => {
        deepSearchApi.primeRunContext(runId, { spaceId: user?.spaceId || getDefaultSpaceId() })
      })
    } else {
      setDeepSearchRunIds(new Map())
    }
  }

  const handleDeleteConversation = async (conversationId: string) => {
    const conversation = getConversationById(conversationId)
    await cancelDeepSearchConversationRuns(conversation?.config, deepSearchApi.killRun)
    await deleteConversation(conversationId)
  }

  // ===== DeepSearch 插件：消息发送处理 =====
  const handleDeepSearchSend = async (
    content: string,
    options?: { interrupt_feedback?: string; backend_message?: string }
  ) => {
    // 标记SSE是否正常完成（收到正常结束信号）
    // 需要在 try 块外定义，这样 finally 块也能访问
    let sseCompletedNormally = false
    let mainFlowRecording: DeepSearchRecordingHandle | null = null

    // 如果没有 conversation，先创建一个
    let conversationId = getReusableConversationId('deepsearch')
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

    // 3. 创建 AbortController 用于中断请求（同步写入模块级变量，跨组件生命周期可访问）
    const controller = new AbortController()
    _activeDeepSearchController = controller

    try {
      // 4. 获取并验证配置
      let config = toDeepResearchConfig(agentConfigs['deepsearch'])

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
      const web_search_config = (config.searchMode === 'web' || config.searchMode === 'all') && config.selectedWebSearchEngineId
        ? {
            web_search_config_id: config.selectedWebSearchEngineId,
            max_web_search_results: config.webSearchResultCount,
          }
        : undefined

      // ===== HITL 判断逻辑：判断是否是回复 HITL interrupt 消息 =====
      let interrupt_feedback = options?.interrupt_feedback ?? ''  // 默认为空
      let continuationInteraction: {
        kind: 'hitl' | 'outline'
        feedback: string
        userMessage: string
        backendMessage?: string
      } | null = null

      const messageItemsList = useConversationStore.getState().getCurrentMessageItemsList()

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
              (isTaskOngoing(lastMessage.status) || lastMessage.status === TaskStatus.UNKNOWN)) {
            // 说明本次提问是 HITL 的第1次回复的再次提问，判断 agent 是否匹配
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
                continuationInteraction = {
                  kind: 'outline',
                  feedback: 'revise_comment',
                  userMessage: content,
                }
              } else {
                // 普通 INTERRUPT：用户反馈
                interrupt_feedback = 'accepted'
                continuationInteraction = {
                  kind: 'hitl',
                  feedback: 'accepted',
                  userMessage: content,
                }
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
        }
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
            mainFlowRecording = await createMainFlowRecording({
              enabled: true,
              query: content,
              continueSession: !isNewDeepSearchRun,
              metadata: {
                agentType: 'deepsearch',
              modelConfigId: selectedModelId,
              conversationId: backendConversationId,
              spaceId: user?.spaceId || getDefaultSpaceId(),
            },
          })
        } catch (error) {
          console.warn('[DeepSearch] Failed to start SSE recording:', error)
        }
      }

      // 获取认证 token
      const token = getToken()
      if (!token) {
        throw new Error(t('apps.errors.unableToGetAuthToken'))
      }

      const messageToBackend = options?.backend_message ?? content
      const vlmChartGeneratorEnable = config.vlmChartGeneratorEnable ?? DEFAULT_DEEPRESEARCH_CONFIG.vlmChartGeneratorEnable
      const vlmChartGeneratorMaxIterations = config.vlmChartGeneratorMaxIterations ?? DEFAULT_DEEPRESEARCH_CONFIG.vlmChartGeneratorMaxIterations

      if (!continuationInteraction && !isNewDeepSearchRun) {
        continuationInteraction = {
          kind: interrupt_feedback === 'revise_comment' ? 'outline' : 'hitl',
          feedback: interrupt_feedback || 'accepted',
          userMessage: content,
          backendMessage: messageToBackend,
        }
      } else if (continuationInteraction) {
        continuationInteraction = {
          ...continuationInteraction,
          backendMessage: messageToBackend,
        }
      }

      if (mainFlowRecording?.isActive() && continuationInteraction) {
        mainFlowRecording.recordInteraction(continuationInteraction)
      }

      // ===== 提取并保存配置参数 =====
      const agentConfig = {
        space_id: user?.spaceId || getDefaultSpaceId(),
        general_model_config_id: config.generalModelId ? parseInt(config.generalModelId) : selectedModelId,
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
        template_id: config.enableTemplate ? (config.selectedTemplateId ?? -1) : -1,
        interrupt_feedback: interrupt_feedback,   // 中断反馈标识, 可填值: ['accepted', ''], 默认''
        execution_method: config.execution_method ?? DEFAULT_DEEPRESEARCH_CONFIG.execution_method,
        // 高级配置模型 ID（可选，仅在有值时传递）
        ...(config.planUnderstandingModelId && { plan_understanding_model_id: parseInt(config.planUnderstandingModelId) }),
        ...(config.infoCollectingModelId && { info_collecting_model_id: parseInt(config.infoCollectingModelId) }),
        ...(config.writingCheckingModelId && { writing_checking_model_id: parseInt(config.writingCheckingModelId) }),
        // 用户反馈优化配置
        user_feedback_processor_enable: config.userFeedbackProcessorEnable ?? true,
        user_feedback_processor_max_interactions: normalizeMaxRewriteInteractions(config.userFeedbackProcessorMaxInteractions),
        vlm_chart_generator_enable: vlmChartGeneratorEnable,
        vlm_chart_generator_max_iterations: vlmChartGeneratorMaxIterations,
        ...(vlmChartGeneratorEnable && vlmChartGeneratorMaxIterations > 0 && config.vlmChartModelId && {
          vlm_model_config_id: parseInt(config.vlmChartModelId),
        }),
        // 联网搜索QPS限制，0表示不限流
        web_search_max_qps: config.webSearchMaxQps ?? 0,
      };

      // 保存到 store（用于 SSE Handler 读取）
      setConversationConfig(conversationId, agentConfig);


      const response = await fetch('/api/v1/agent/deepsearch/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ ...agentConfig, message: messageToBackend }),
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
          if (!sseCompletedNormally) {
            const state = useConversationStore.getState()
            const lastMessageItems = state.getLastMessageItems()
            if (
              lastMessageItems &&
              !state.getMessageItemsIsUser(lastMessageItems) &&
              !isTaskOngoing(lastMessageItems.status)
            ) {
              // 流已经结束且消息状态已终结（完成/失败/取消），可视为终态，停止超时监控。
              sseCompletedNormally = true
            }
          }

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
          if (mainFlowRecording?.isActive()) {
            try {
              await mainFlowRecording.stop()
              mainFlowRecording = null
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
              if (
                data.agent === DeepsearchAgentType.END &&
                (data.content === 'ALL END' || data.event === 'error')
              ) {
                sseCompletedNormally = true
              }

              // ===== SSE 录制：录制事件 =====
              if (mainFlowRecording?.isActive()) {
                try {
                  mainFlowRecording.record(data)
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
      if (mainFlowRecording?.isActive()) {
        try {
          await mainFlowRecording.stop()
          mainFlowRecording = null
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
      _activeDeepSearchController = null
      _appsUISnapshot = null  // SSE 结束，快照不再有效
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
      if (_activeDeepSearchController) {
        _activeDeepSearchController.abort()
        _activeDeepSearchController = null
      }
      return
    }

    const token = getToken()
    if (!token) {
      console.error('[DeepSearch Cancel] No auth token')
      useConversationStore.getState().stopSSETimeoutMonitor()
      clearPendingOutlineInteraction()
      if (_activeDeepSearchController) {
        _activeDeepSearchController.abort()
        _activeDeepSearchController = null
      }
      return
    }

    // 【关键 1】立即更新 UI 状态，不等待后端响应
    useConversationStore.getState().updateMessageItemsStatusToCancelled()

    // 停止 SSE 超时监控，用户主动取消后不再需要超时检测
    useConversationStore.getState().stopSSETimeoutMonitor()
    // 清除待处理的大纲交互，防止取消后 useEffect 重新触发 handleDeepSearchSend
    clearPendingOutlineInteraction()

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
    if (_activeDeepSearchController) {
      _activeDeepSearchController.abort()
      _activeDeepSearchController = null
    }
  }

  return (
    <div className={`${FONT_FAMILY} flex flex-col h-full w-full min-h-0`}>
      {/* SSE 回放浮动按钮（仅开发模式） */}
      {ENABLE_SSE_DEBUG && !showPlaybackPanel && (
        <div className="fixed bottom-6 right-6 z-40 w-[140px] rounded-2xl border border-slate-200 bg-white/96 p-2 shadow-xl backdrop-blur">
          <button
            onClick={() => setShowPlaybackPanel(true)}
            className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 px-2.5 py-2 text-white text-xs font-medium shadow-sm transition-all duration-200 hover:from-blue-700 hover:to-purple-700"
            title={t('apps.chat.openSSEPanel')}
          >
            <History className="w-4 h-4" />
            <span>{t('apps.chat.replayHistory')}</span>
          </button>
        </div>
      )}

      {/* 主内容区 - 使用 flex 布局 */}
      <div className="flex-1 flex flex-row min-h-0 overflow-hidden">
        {/* 对话历史侧边栏 - 始终显示 */}
        <ConversationHistorySidebar
          currentConversationId={currentConversationId}
          onConversationSelect={handleConversationSelect}
          onDeleteConversation={handleDeleteConversation}
          onNewConversation={handleNewConversation}
          isStreaming={isConversationHistoryBusy}
          forceCollapsed={!!selectedResultMessageId}
        />

        {/* 右侧主内容区 */}
        <div
          className={`flex-1 flex min-h-0 overflow-hidden ${(selectedResultMessageId || showMindMap || showDeepSearchExplorer) ? 'flex-row' : 'flex-col'}`}
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
                  isAgentLocked={isAgentLocked}
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
              {/* 对话区域 - hidden when explorer is fullscreen */}
              <div className={`flex flex-col min-h-0 ${
                deepSearchExplorerFullscreen && showDeepSearchExplorer
                  ? 'hidden'
                  : (selectedResultMessageId || showMindMap || showDeepSearchExplorer) ? 'w-2/5' : 'flex-1'
              }`}>
                <div ref={messagesContainerRef} className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-6 py-6">
                <div className="max-w-4xl mx-auto space-y-4">
                  {messageItemsList.map((messageItems) => (
                    <React.Fragment key={messageItems.id}>
                      <SystemMessageItem 
                        messageItems={messageItems}
                        onOpenMindMap={isDeepSearchMode ? handleOpenMindMap : undefined}
                      />
                      {/* Show a DeepSearchRunSummary after user messages that have an associated runId */}
                      {isDeepSearchExplorerMode && messageItems.isUser && deepSearchRunIds.has(messageItems.id) && (
                        <Suspense fallback={null}>
                          <DeepSearchRunSummary
                            runId={deepSearchRunIds.get(messageItems.id)!}
                            forceFailed={killedDeepSearchRunIds.has(deepSearchRunIds.get(messageItems.id)!)}
                            onToggleExplorer={async () => {
                              const runId = deepSearchRunIds.get(messageItems.id)!
                              if (showDeepSearchExplorer && activeDeepSearchRunId === runId) {
                                setShowDeepSearchExplorer(false)
                                setDeepSearchExplorerFullscreen(false)
                                setActiveDeepSearchRunId(null)
                              } else {
                                try {
                                  const status = await deepSearchApi.getRunStatus(runId)
                                  if (status.route === 'simple') {
                                    return
                                  }
                                } catch (error) {
                                  console.error('[DeepSearchExplorer] Failed to resolve run route:', error)
                                }
                                setActiveDeepSearchRunId(runId)
                                setShowDeepSearchExplorer(true)
                              }
                            }}
                            isExplorerOpen={showDeepSearchExplorer && activeDeepSearchRunId === deepSearchRunIds.get(messageItems.id)}
                          />
                        </Suspense>
                      )}
                    </React.Fragment>
                  ))}

                  {/* AI 正在输入指示器（isSending 本地状态 + isLoading Zustand 状态，切换模块返回后用 isLoading 托底） */}
                  {(isSending || isLoading) && (
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
                {/* 任务进行中状态提示 */}
                {isStreaming && isDeepSearchMode && (
                  <div className="flex items-center justify-center gap-2 mb-3 text-amber-600 text-sm">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span className="whitespace-pre-line">
                      {t('apps.chat.taskRunning.statusTextBefore')}
                      <button
                        type="button"
                        onClick={async () => {
                          // 无法直接跳转到浏览器内部设置页（edge://、chrome:// 属于浏览器特权页面，
                          // 普通网页无权限导航过去），退而求其次：点击时自动复制好网址，
                          // 用户只需按弹窗里的步骤打开设置页粘贴添加即可
                          const success = await copyToClipboard(window.location.origin)
                          if (success) {
                            showSuccess(t('apps.chat.taskRunning.keepAliveGuide.urlCopiedToast'))
                          }
                          setShowKeepAliveGuide(true)
                        }}
                        className="underline underline-offset-2 hover:text-amber-700 font-medium"
                      >
                        {t('apps.chat.taskRunning.keepAliveLinkText')}
                      </button>
                      {t('apps.chat.taskRunning.statusTextAfter')}
                    </span>
                  </div>
                )}
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
                    isAgentLocked={isAgentLocked}
                  />
                </div>
              </div>
            </div>

            {/* 右侧：结果面板或思维链面板（分屏显示） */}
            {(selectedResultMessageId || showMindMap) && (
              <div className="w-3/5 h-full bg-white border border-gray-200 rounded-lg ml-4 overflow-hidden flex flex-col">
                {/* 顶部工具栏 */}
                {toolbarState.show && (
                  <TopToolbar
                    activeView={activeView}
                    onViewChange={handleViewChange}
                    onClose={handleCloseRightPanel}
                    disabledViews={toolbarState.disabledViews}
                  />
                )}

                {/* 共用面板内容 */}
                <div className="flex-1 min-h-0">
                  {showMindMap && mindMapMessageItemsId ? (
                    <MindMapPanel
                      messageItemsId={mindMapMessageItemsId}
                      onClose={handleCloseMindMap}
                      graphType={currentGraphType}
                      onGraphTypeChange={setCurrentGraphType}
                    />
                  ) : (
                    <ResultPanel
                      feedbackOptimizationEnabled={toDeepResearchConfig(agentConfigs['deepsearch']).userFeedbackProcessorEnable ?? DEFAULT_DEEPRESEARCH_CONFIG.userFeedbackProcessorEnable}
                      onReportRewrite={handleReportRewrite}
                    />
                  )}
                </div>
              </div>
            )}

            {/* 右侧：Deep Search Explorer 面板 (or fullscreen) */}
            {showDeepSearchExplorer && activeDeepSearchRunId && (
              <div className={`${deepSearchExplorerFullscreen ? 'flex-1' : 'w-3/5'} h-full bg-white border border-gray-200 rounded-lg ml-4 overflow-hidden flex flex-col`}>
                <Suspense fallback={<div className="flex-1 flex items-center justify-center text-sm text-gray-500">Loading explorer...</div>}>
                  <DeepSearchExplorerPanel
                    runId={activeDeepSearchRunId}
                    onKilled={(runId) => {
                      setKilledDeepSearchRunIds((prev) => new Set(prev).add(runId))
                    }}
                    onClose={async () => {
                      await handleDeepSearchExplorerLeave(
                        'close-panel',
                        { deepSearchRunIds, activeDeepSearchRunId, killedDeepSearchRunIds },
                        deepSearchApi.killRun,
                      )
                      clearDeepSearchExplorerUiState()
                    }}
                    isFullscreen={deepSearchExplorerFullscreen}
                    onToggleFullscreen={() => setDeepSearchExplorerFullscreen((prev) => !prev)}
                  />
                </Suspense>
              </div>
            )}
          </>
          )}
        </div>
      </div>

      {/* 智能体配置弹窗 */}
      {(pendingAgent || selectedAgent)?.id === 'deepsearch-explorer' ? (
        <DeepSearchExplorerConfigDialog
          agent={pendingAgent || selectedAgent}
          open={configDialogOpen}
          onClose={() => {
            setConfigDialogOpen(false)
            setPendingAgent(null)
            setIsFirstConfigMode(false)
          }}
          onSave={handleSaveAgentConfig}
          onClearProviderCredentials={handleClearDeepSearchProviderCredentials}
          savedConfigs={deepSearchExplorerSavedConfigs}
          spaceId={user?.spaceId || getDefaultSpaceId()}
          isFirstConfig={isFirstConfigMode}
          availableModels={availableModels}
          modelsLoading={modelsLoading}
        />
      ) : (
        <AgentConfigDialog
          agent={pendingAgent || selectedAgent}
          open={configDialogOpen}
          onClose={() => {
            setConfigDialogOpen(false)
            setPendingAgent(null)
            setIsFirstConfigMode(false)
          }}
          onSave={handleSaveAgentConfig}
          savedConfigs={deepResearchSavedConfigs}
          spaceId={user?.spaceId || getDefaultSpaceId()}
          modelConfigId={selectedModelId}
          isFirstConfig={isFirstConfigMode}
          availableModels={availableModels}
          modelsLoading={modelsLoading}
          availableVLMModels={availableVLMModels}
          vlmModelsLoading={vlmModelsLoading}
        />
      )}

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
        <RecordingPanel
          onClose={() => setShowPlaybackPanel(false)}
          onPlaybackStart={async conversationId => {
            await switchConversation(conversationId);
            // 切换到 DeepSearch 模式
            const deepsearchAgent = DEFAULT_AGENTS.find(a => a.id === 'deepsearch');
            if (deepsearchAgent) {
              setSelectedAgent(deepsearchAgent);
            }
            // 返回 conversationId（回放对话的 ID）
            return conversationId;
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

      {/* "设置本网页保持活跃"操作指引弹窗 */}
      <KeepAliveGuideDialog
        open={showKeepAliveGuide}
        onClose={() => setShowKeepAliveGuide(false)}
      />

    </div>
  );
}

export default AppsPage
