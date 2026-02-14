import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Trash2, TestTube, Brain, Sliders, Check, ChevronDown, ChevronUp } from 'lucide-react'
import { Button, Typography, Card, CardContent, IconButton, Tooltip } from '@mui/material'
import { useTranslation } from 'react-i18next'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import {
  MultiRunDialog,
  PromptBasicInfoDialog,
  ChatMessageArea,
  QuickOptimizeDialog,
  DebugOptimizeDialog,
  SubmitVersionDialog,
  AssociationsDialog,
  type ChatMessage,
  PromptContentEditor,
  type PromptMessage,
  AdvancedConfigEditor,
  type Model,
  type ModelConfig,
  ToolEditDialog,
  AddVariableDialog,
  type VariableData,
  FeedbackOptimizeDialog,
  type OptimizationMode,
  ExitComparisonDialog,
  VersionHistory,
  TemplateEngineSwitchDialog,
  RestoreVersionConfirmationDialog,
  PromptEditHeader,
  DebugInputAreaGroup,
  DebugInputArea,
} from '@/components/Prompts'
import { ENV_CONFIG } from '../../config/environment'
import { useAuthStore } from '@/stores/useAuthStore'
import {
  useAddVariableDialog,
  useAdvancedConfigEditor,
  useChatMessageArea,
  useClickOutsideSelectors,
  useDebugInputArea,
  useDebugInputAreaGroup,
  useDebugOptimizeDialog,
  useDraft,
  useFeedbackOptimizeDialog,
  useMultiRunDialog,
  usePromptBasicInfoDialog,
  usePromptEditHeader,
  useQuickOptimizeDialog,
  useSubmitVersionDialog,
  useToolEditDialog,
  useVersionHistory,
  useLoadPrompt,
} from '@/hooks/prompts'
import {
  type PromptParameter,
  type ComparisonGroupData,
  type GroupEditingMessage,
  type DebugTraceInfo,
  type SelectedAiReply,
  type OptimizingTarget,
  type OptimizationSource,
  type OptimizeStep,
} from '@/types/promptType'
import {
  calculateSelectionIndices,
  extractVariables,
  extractVariablesFromNonPlaceholderMessages,
  findModelByIdAndFrom,
  isValidVariableName,
  validateAllPlaceholders,
  validatePlaceholderContentWithMessage,
} from '@/utils/prompts/promptEditPageUtils'
import { convertApiToolsToFrontendTools } from '@/utils/prompts/toolFormatConverter'
import { copyToClipboard } from '@/utils/prompts/utils'
import { PromptService, PromptModelService, type RelationObj, type MockContext } from '@test-agentstudio/api-client'

const PromptEditPage: React.FC = () => {
  const { t, i18n } = useTranslation()
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const isNew = id === 'new'
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const readOnlyToggleRef = useRef<HTMLDivElement>(null)
  // 用于在 useEffect 中访问 hook 返回的 setter
  const versionHistorySettersRef = useRef<{
    setApiVersionList?: React.Dispatch<React.SetStateAction<any[]>>
    setVersionHistoryOpen?: React.Dispatch<React.SetStateAction<boolean>>
    loadVersionDataToEditor?: (version: string, source?: string) => Promise<any>
  }>({})
  const READ_ONLY_BYPASS_SELECTOR = '[data-readonly-allowed="true"]'
  const readOnlyWarningLockRef = useRef(false)
  const autoReadOnlyCounterRef = useRef(0)
  const userReadOnlyRef = useRef(false)
  const { snackbar, showSnackbar, closeSnackbar, setSnackbar } = useUnifiedSnackbar()
  const { user } = useAuthStore()
  const workspaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  const userId = user?.id || ENV_CONFIG.DEFAULT_USER_ID

  // 统一的组模块展开/收起状态（基准组id=0，对照组id>=1）
  const [groupsExpanded, setGroupsExpanded] = useState<{
    [key: number]: {
      promptEditor: boolean
      advancedConfig: boolean
      promptDebug: boolean
    }
  }>({
    0: { promptEditor: true, advancedConfig: true, promptDebug: true }, // 基准组
    1: { promptEditor: true, advancedConfig: true, promptDebug: true }, // 第一个对照组
  })

  // 统一的调试区域高度状态（基准组id=0，对照组id>=1）
  const [groupsDebugHeight, setGroupsDebugHeight] = useState<{ [key: number]: number }>({
    0: 300, // 基准组
    1: 300, // 第一个对照组
  })

  // 调试区域拖动状态
  const [isDraggingGroupDebug, setIsDraggingGroupDebug] = useState<number | null>(null)
  const groupDebugRefs = useRef<{ [key: number]: HTMLDivElement | null }>({})
  const groupContainerRefs = useRef<{ [key: number]: HTMLDivElement | null }>({})
  const [optimizationDialogOpen, setOptimizationDialogOpen] = useState(false)
  const [optimizationResult, setOptimizationResult] = useState('')
  const [isOptimizing, setIsOptimizing] = useState(false)
  const [optimizingTarget, setOptimizingTarget] = useState<OptimizingTarget | null>(null)

  const [quickOptimizeStreaming, setQuickOptimizeStreaming] = useState('')
  const quickOptimizeStreamingRef = useRef('')
  // 用于反馈优化的流式处理
  const feedbackOptimizeStreamingRef = useRef('')
  // 用于badcase优化的流式处理
  const badcaseOptimizeStreamingRef = useRef('')
  // 用于取消流式请求的 AbortController（快捷优化和反馈优化使用）
  const abortControllerRef = useRef<AbortController | null>(null)
  // 用于取消调试流式请求的 AbortController（主聊天区域使用，参考快捷优化的停止逻辑）
  const debugAbortControllerRef = useRef<AbortController | null>(null)
  // 控制是否显示差异对比（延迟显示）
  const [showQuickOptimizeDiff, setShowQuickOptimizeDiff] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null)
  const [draftSavedTime, setDraftSavedTime] = useState<Date | null>(null) // 草稿保存时间
  const [latestVersion, setLatestVersion] = useState<string>('') // 最新提交版本号
  const [isDraftEdited, setIsDraftEdited] = useState<boolean>(false) // 是否有未提交的草稿
  const [isNewPromptScenario, setIsNewPromptScenario] = useState<boolean>(false) // 是否是新建提示词场景
  const [versionHistoryHeight, setVersionHistoryHeight] = useState('calc(100vh - 200px)') // 版本历史高度
  const [chatMessageMaxHeight, setChatMessageMaxHeight] = useState('calc(100vh - 300px)') // 聊天消息区域最大高度

  // 三列布局拖动调整状态
  const [columnWidths, setColumnWidths] = useState([33.33, 33.33, 33.34]) // 三列的宽度百分比
  const [isDraggingColumn, setIsDraggingColumn] = useState<number | null>(null) // 正在拖动的分界线索引（0或1）

  // 模块展开/收起状态
  const [moduleCollapsed, setModuleCollapsed] = useState({
    promptEditor: false, // 编写提示词（不可收起）
    advancedConfig: false, // 高级配置
    promptDebug: false, // 提示词调试
  })

  // 保存模块收起前的宽度
  const [savedColumnWidths, setSavedColumnWidths] = useState([33.33, 33.33, 33.34])

  const [isReadOnlyMode, setIsReadOnlyMode] = useState(false)

  const [advancedConfigTab, setAdvancedConfigTab] = useState(0)

  const autoSaveTimerRef = useRef<any>(null) // 自动保存定时器
  const promptDraftDataRef = useRef<any>(null) // promptDraftData 引用
  const [exitComparisonDialogOpen, setExitComparisonDialogOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [toolsEnabled, setToolsEnabled] = useState(true)

  // 模型列表状态
  const [availableModels, setAvailableModels] = useState<Model[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState<Model | null>(null)
  const [templateEngine, setTemplateEngine] = useState<'normal' | 'jinja2'>('normal')
  const [templateEngineChangeDialogOpen, setTemplateEngineChangeDialogOpen] = useState(false)
  const [pendingTemplateEngine, setPendingTemplateEngine] = useState<'normal' | 'jinja2'>('normal')
  // 对比组模板引擎切换状态管理
  const [groupTemplateEngineChangeDialogOpen, setGroupTemplateEngineChangeDialogOpen] = useState<{ [groupId: number]: boolean }>({})
  const [groupPendingTemplateEngine, setGroupPendingTemplateEngine] = useState<{ [groupId: number]: 'normal' | 'jinja2' }>({})
  const [currentTemplateEngineChangeGroupId, setCurrentTemplateEngineChangeGroupId] = useState<number | null>(null)
  const [addVariableDialogOpen, setAddVariableDialogOpen] = useState(false)
  // 统一的变量对话框状态，groupId为0表示基准组，>=1表示对照组
  const [groupAddVariableDialogOpen, setGroupAddVariableDialogOpen] = useState<{ open: boolean; groupId?: number }>({ open: false })
  // 编辑变量相关状态（使用 AddVariableDialog 组件）
  const [editVariableDialogOpen, setEditVariableDialogOpen] = useState(false)
  const [editingVariableIndex, setEditingVariableIndex] = useState<number | null>(null)
  const [editingVariableData, setEditingVariableData] = useState<(VariableData & { originalName?: string }) | null>(null)
  const [selectedText, setSelectedText] = useState('')
  const [selectionPosition, setSelectionPosition] = useState<{ x: number; y: number } | null>(null)
  const [selectionIndices, setSelectionIndices] = useState<{ start: number; end: number } | null>(null)
  const [isSelecting, setIsSelecting] = useState(false) // 跟踪是否正在选中文本
  const [associationsDialogOpen, setAssociationsDialogOpen] = useState(false)

  const [selectedAssociations, setSelectedAssociations] = useState<RelationObj[]>([])
  const [selectedVersionName, setSelectedVersionName] = useState('')
  const [optimizeDialogOpen, setOptimizeDialogOpen] = useState(false)
  const [cursorPosition, setCursorPosition] = useState<{ messageId: string; position: number } | null>(null)
  const [showCursorOptimizeButton, setShowCursorOptimizeButton] = useState(false)
  const [cursorOptimizePosition, setCursorOptimizePosition] = useState<{ x: number; y: number } | null>(null)

  // 根据调试结果优化提示词相关状态
  const [aiReplyOptimizeDialogOpen, setAiReplyOptimizeDialogOpen] = useState(false)
  const [selectedAiReply, setSelectedAiReply] = useState<SelectedAiReply | null>(null)
  const [optimizedPromptTemplate, setOptimizedPromptTemplate] = useState('')
  const [humanEvaluation, setHumanEvaluation] = useState('')
  const [aiReplyOptimizeStep, setAiReplyOptimizeStep] = useState<OptimizeStep>('input')
  const [optimizationSource, setOptimizationSource] = useState<OptimizationSource>({ type: 'main' })

  const [optimizeInput, setOptimizeInput] = useState('')
  const [optimizedResult, setOptimizedResult] = useState('')
  const [lastOptimizeInput, setLastOptimizeInput] = useState('') // 保存最后使用的优化需求
  const [currentOptimizationType, setCurrentOptimizationType] = useState<OptimizationMode | null>('general') // 当前优化模式
  const [regeneratePromptInput, setRegeneratePromptInput] = useState<string>('') // 重新生成提示词输入变量，初始为原始system消息
  const [regeneratePromptInputMessageId, setRegeneratePromptInputMessageId] = useState<string | undefined>(undefined) // 跟踪重新生成提示词输入对应的messageId
  const [ignoreTextSelection, setIgnoreTextSelection] = useState(false) // 临时忽略文本选中事件的标记

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [comparisonInputMessage, setComparisonInputMessage] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [debugTraceInfo, setDebugTraceInfo] = useState<DebugTraceInfo>({}) // 调试跟踪信息

  // Placeholder防抖状态
  const placeholderUpdateTimers = useRef<{ [key: string]: any }>({})
  // 保存选中文本和位置的 ref，用于在打开对话框时恢复（即使状态被清除）
  const selectedTextRef = useRef<string>('')
  // 用于跟踪上次的optimizationSource，避免频繁更新
  const lastOptimizationSourceRef = useRef<typeof optimizationSource | null>(null)
  const selectionIndicesRef = useRef<{ start: number; end: number } | null>(null)
  // 用于存储上一次同步的content，避免循环更新
  const lastSyncedContentRef = useRef<string>('')
  // 用于存储上一次的optimizationSource.messageId，避免不必要的更新
  const lastOptimizationSourceMessageIdRef = useRef<string | undefined>(undefined)
  // 用于保存全文反馈优化时的messageId，确保在执行优化时能够获取到正确的值
  const fullTextOptimizeMessageIdRef = useRef<string | undefined>(undefined)

  // 立即生效的忽略文本选中事件标记（不依赖React异步状态更新）
  const ignoreTextSelectionRef = useRef<boolean>(false)
  // 跟踪是否刚刚点击了外部区域（用于防止光标位置变化事件重新显示按钮）
  const justClickedOutsideRef = useRef<boolean>(false)
  // 跟踪最近一次点击选中文本优化按钮的时间戳（用于保护对话框打开过程中的短暂时间窗口）
  const lastClickedSelectOptimizeButtonRef = useRef<number>(0)
  // 全局点击事件处理器的定时器引用（用于防抖和清理）
  const globalClickTimerRef = useRef<NodeJS.Timeout | null>(null)
  const globalClickTimer2Ref = useRef<NodeJS.Timeout | null>(null)
  // 用户点击的按钮类型标记（用于明确判断优化类型，避免状态更新延迟问题）
  const clickedOptimizationTypeRef = useRef<OptimizationMode | null>(null)
  const [isEditingPlaceholder, setIsEditingPlaceholder] = useState<{ [key: string]: boolean }>({})

  // 光标位置优化按钮定时器
  const cursorOptimizeTimer = useRef<any>(null)
  // 对比模式变量检测防抖定时器
  const comparisonVarDetectTimerRef = useRef<any>(null)
  // 追踪每个组之前的templateEngine值，用于检测模板引擎变化
  const prevGroupTemplateEnginesRef = useRef<Map<number, 'normal' | 'jinja2'>>(new Map())

  const [expandedReasoningMessages, setExpandedReasoningMessages] = useState<Set<number>>(new Set()) // 展开的reasoning消息索引
  const [expandedToolCallMessages, setExpandedToolCallMessages] = useState<Set<number>>(new Set()) // 展开的工具调用消息索引
  const [isLoadingFromAPI, setIsLoadingFromAPI] = useState(false) // 标记是否正在从API加载数据
  const loadingRef = useRef(false) // 防止重复调用的标志
  const modelsLoadingRef = useRef(false) // 防止模型列表重复调用的标志
  const pendingModelRestoreRef = useRef<{ modelId: string; modelFrom: string } | null>(null) // 待恢复的模型信息
  const [isInitialized, setIsInitialized] = useState(false) // 组件初始化完成标志

  // 对照组数量（不包括基准组）
  const [controlGroupCount, setControlGroupCount] = useState(1)

  const [lastSavedTime, setLastSavedTime] = useState<Date | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [versionDescription, setVersionDescription] = useState('')
  const [versionNumberInitialized, setVersionNumberInitialized] = useState(false)
  const [isComparisonMode, setIsComparisonMode] = useState(false)

  // 消息控制状态
  const [messageFormats, setMessageFormats] = useState<{ [key: number]: 'txt' | 'markdown' }>({}) // 消息格式状态
  const [editingMessage, setEditingMessage] = useState<number | null>(null) // 正在编辑的消息索引
  const [editContent, setEditContent] = useState<string>('') // 编辑的内容
  const [completedMessages, setCompletedMessages] = useState<Set<number>>(new Set()) // 已完成打印的消息索引
  const [isStreamingStopped, setIsStreamingStopped] = useState(false) // 主调试区域流式响应是否已被用户停止
  const isStreamingStoppedRef = useRef(false) // 用于避免闭包问题的ref
  // 统一的流式响应停止状态（基准组id=0，对照组id>=1）
  const [groupStreamingStopped, setGroupStreamingStopped] = useState<{ [groupId: number]: boolean }>({})
  const groupStreamingStoppedRef = useRef<{ [groupId: number]: boolean }>({})
  // 用于取消对比模式调试流式请求的 AbortController（参考快捷优化的停止逻辑）
  const groupAbortControllerRefs = useRef<{ [groupId: number]: AbortController | null }>({})
  // 用于清理对比模式延迟队列的 debugController（修复停止后仍继续流式输出的问题）
  const groupDebugControllerRefs = useRef<{ [groupId: number]: { cancel: () => void } | null }>({})

  // AI思考过程直接更新机制 - 与消息内容保持一致
  const reasoningUpdateTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 比较模式消息控制状态
  // 统一的消息状态管理（基准组id=0，对照组id>=1）
  const [groupMessageFormats, setGroupMessageFormats] = useState<{ [groupId: number]: { [key: number]: 'txt' | 'markdown' } }>({})
  const [groupEditingMessage, setGroupEditingMessage] = useState<GroupEditingMessage | null>(null)
  const [groupEditContent, setGroupEditContent] = useState<string>('')
  const [groupCompletedMessages, setGroupCompletedMessages] = useState<{ [groupId: number]: Set<number> }>(() => {
    return {}
  })
  const [groupReasoningExpanded, setGroupReasoningExpanded] = useState<{ [groupId: number]: { [key: number]: boolean } }>({})
  const [groupToolCallExpanded, setGroupToolCallExpanded] = useState<{ [groupId: number]: { [key: number]: boolean } }>({})

  // 统一的聊天容器ref（基准组id=0，对照组id>=1）
  const groupChatMessageAreaRefs = useRef<{ [key: number]: HTMLDivElement | null }>({})

  // 新增：多运行实例的聊天消息管理
  const [multiRunChatMessages, setMultiRunChatMessages] = useState<Array<ChatMessage[]>>([])
  const [multiRunProcessing, setMultiRunProcessing] = useState<boolean[]>([])
  // 用于取消多实例调试流式请求的 AbortController（参考快捷优化的停止逻辑）
  const multiRunAbortControllerRefs = useRef<Array<AbortController | null>>([])
  // 用于清理多实例调试延迟队列的 debugController（参考对比模式的停止逻辑）
  const multiRunDebugControllerRefs = useRef<Array<{ cancel: () => void } | null>>([])

  // 定义runCount状态
  const [runCount, setRunCount] = useState(2)

  // 新增：多实例运行弹出对话框状态
  const [multiRunDialogOpen, setMultiRunDialogOpen] = useState(false)

  // 新增：多实例运行的工具调用展开状态管理
  const [multiRunExpandedToolCallMessages, setMultiRunExpandedToolCallMessages] = useState<Set<number>>(new Set())

  // 新增：多实例运行的AI思考过程展开状态管理
  const [multiRunExpandedReasoningMessages, setMultiRunExpandedReasoningMessages] = useState<Set<number>>(new Set())

  // Tools state
  const [tools, setTools] = useState<
    Array<{
      id: string
      name: string
      description: string
      defaultValue?: string
      fieldType?: 'PlainText' | 'JSON'
      parameters: Array<{
        name: string
        type: string
        description: string
        required: boolean
      }>
    }>
  >([])

  const enableAutoReadOnly = useCallback(() => {
    autoReadOnlyCounterRef.current += 1
    setIsReadOnlyMode(true)
  }, [])

  const disableAutoReadOnly = useCallback(() => {
    autoReadOnlyCounterRef.current = Math.max(0, autoReadOnlyCounterRef.current - 1)
    const newCounter = autoReadOnlyCounterRef.current
    const willExitReadOnly = !userReadOnlyRef.current && newCounter === 0

    if (willExitReadOnly) {
      setIsReadOnlyMode(false)
    }
  }, [])

  const showReadOnlyNotice = useCallback(() => {
    if (readOnlyWarningLockRef.current) {
      return
    }
    readOnlyWarningLockRef.current = true
    showSnackbar(t('prompts.promptEdit.readOnlyMode.toast'), 'info', 2000)
    setTimeout(() => {
      readOnlyWarningLockRef.current = false
    }, 1500)
  }, [showSnackbar, t])

  // 响应式计算版本历史的高度和聊天消息区域高度
  useEffect(() => {
    const updateResponsiveHeights = () => {
      if (window.innerWidth < 640) {
        // 小屏幕：手机等移动设备
        setVersionHistoryHeight('calc(100vh - 150px)')
        setChatMessageMaxHeight('calc(100vh - 350px)')
      } else if (window.innerWidth < 2000) {
        // 中等屏幕：平板、14寸笔记本等
        setVersionHistoryHeight('calc(100vh - 120px)')
        setChatMessageMaxHeight('calc(100vh - 200px)')
      } else {
        // 大屏幕：15寸以上笔记本、台式显示器
        setVersionHistoryHeight('calc(100vh - 120px)')
        setChatMessageMaxHeight('calc(100vh - 400px)')
      }
    }

    updateResponsiveHeights()
    window.addEventListener('resize', updateResponsiveHeights)
    return () => window.removeEventListener('resize', updateResponsiveHeights)
  }, [])

  useEffect(() => {
    if (isReadOnlyMode) {
      const activeElement = document.activeElement as HTMLElement | null
      if (activeElement && readOnlyToggleRef.current && !readOnlyToggleRef.current.contains(activeElement) && typeof activeElement.blur === 'function') {
        activeElement.blur()
      }
    }
  }, [isReadOnlyMode])

  useEffect(() => {
    if (!isReadOnlyMode) {
      return
    }

    const allowedRoot = readOnlyToggleRef.current
    const shouldBypass = (event: Event) => {
      const target = event.target as HTMLElement | null
      if (!target) {
        return false
      }
      if (target.closest(READ_ONLY_BYPASS_SELECTOR)) {
        return true
      }
      return !!allowedRoot && allowedRoot.contains(target)
    }

    const handleInteraction = (event: Event) => {
      if (shouldBypass(event)) {
        return
      }
      event.preventDefault()
      event.stopPropagation()
      showReadOnlyNotice()
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (shouldBypass(event)) {
        return
      }

      if (event.metaKey || event.ctrlKey) {
        const key = event.key.toLowerCase()
        if (key === 'v' || key === 'x') {
          event.preventDefault()
          showReadOnlyNotice()
        }
        return
      }

      const allowedKeys = ['escape', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'pageup', 'pagedown', 'home', 'end']
      if (allowedKeys.includes(event.key.toLowerCase())) {
        if (event.key.toLowerCase() === 'escape') {
          setIsReadOnlyMode(false)
        }
        return
      }

      event.preventDefault()
      showReadOnlyNotice()
    }

    const clickEvents: Array<keyof DocumentEventMap> = ['click', 'dblclick', 'submit', 'input']
    clickEvents.forEach(eventName => {
      document.addEventListener(eventName, handleInteraction, true)
    })
    document.addEventListener('keydown', handleKeyDown, true)
    document.addEventListener('paste', handleInteraction, true)

    return () => {
      clickEvents.forEach(eventName => {
        document.removeEventListener(eventName, handleInteraction, true)
      })
      document.removeEventListener('keydown', handleKeyDown, true)
      document.removeEventListener('paste', handleInteraction, true)
    }
  }, [isReadOnlyMode, showReadOnlyNotice, setIsReadOnlyMode])

  // 切换模块展开/收起状态
  const toggleModuleCollapse = (module: 'advancedConfig' | 'promptDebug') => {
    setModuleCollapsed(prev => {
      const isCurrentlyCollapsed = prev[module]

      if (!isCurrentlyCollapsed) {
        // 即将收起模块：保存当前的完整宽度设置
        // 如果当前有模块已经收起，使用savedColumnWidths，否则使用columnWidths
        const widthsToSave = prev.advancedConfig || prev.promptDebug ? savedColumnWidths : columnWidths
        setSavedColumnWidths([...widthsToSave])
      } else {
        // 即将展开模块：恢复保存的宽度设置
        setColumnWidths([...savedColumnWidths])
      }

      return {
        ...prev,
        [module]: !prev[module],
      }
    })
  }

  // 计算当前显示的模块数量和实际宽度
  const visibleModules = React.useMemo(() => {
    const modules = [
      { name: 'promptEditor', collapsed: false }, // 编写提示词不可收起
      { name: 'advancedConfig', collapsed: moduleCollapsed.advancedConfig },
      { name: 'promptDebug', collapsed: moduleCollapsed.promptDebug },
    ]

    const visibleCount = modules.filter(m => !m.collapsed).length

    // 根据显示的模块重新分配宽度
    let actualWidths = [...columnWidths]

    if (visibleCount === 1) {
      // 只有编写提示词显示时，占满全屏
      actualWidths = [100, 0, 0]
    } else if (visibleCount === 2) {
      // 两个模块显示时，使用用户设置的宽度比例
      if (moduleCollapsed.advancedConfig) {
        // 只有编写提示词和提示词调试显示：使用第1、3列的比例
        const totalVisible = columnWidths[0] + columnWidths[2]
        if (totalVisible > 0) {
          const firstRatio = columnWidths[0] / totalVisible
          const thirdRatio = columnWidths[2] / totalVisible
          actualWidths = [firstRatio * 100, 0, thirdRatio * 100]
        } else {
          actualWidths = [50, 0, 50]
        }
      } else if (moduleCollapsed.promptDebug) {
        // 只有编写提示词和高级配置显示：使用第1、2列的比例
        const totalVisible = columnWidths[0] + columnWidths[1]
        if (totalVisible > 0) {
          const firstRatio = columnWidths[0] / totalVisible
          const secondRatio = columnWidths[1] / totalVisible
          actualWidths = [firstRatio * 100, secondRatio * 100, 0]
        } else {
          actualWidths = [50, 50, 0]
        }
      }
    } else {
      // 三个模块都显示时，使用用户拖动设置的宽度
      actualWidths = columnWidths
    }

    return {
      modules,
      visibleCount,
      actualWidths,
    }
  }, [moduleCollapsed, columnWidths])

  // 处理列宽拖动
  const handleColumnMouseDown = (dividerIndex: number) => (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDraggingColumn(dividerIndex)
  }

  const handleColumnMouseMove = React.useCallback(
    (e: MouseEvent) => {
      if (isDraggingColumn === null) return

      const container = document.querySelector('.resizable-columns-container') as HTMLElement
      if (!container) return

      const containerRect = container.getBoundingClientRect()
      const mouseX = e.clientX - containerRect.left
      const containerWidth = containerRect.width
      const mousePercentage = (mouseX / containerWidth) * 100

      // 限制拖动范围（每列最小20%，最大60%）
      const minWidth = 20
      const maxWidth = 60

      // 根据当前显示的模块调整拖动逻辑
      if (isDraggingColumn === 0) {
        // 拖动第一个分界线
        if (!moduleCollapsed.advancedConfig && !moduleCollapsed.promptDebug) {
          // 编写提示词、高级配置、提示词调试都显示：调整编写提示词和高级配置的宽度
          const newFirstWidth = Math.min(Math.max(mousePercentage, minWidth), maxWidth)
          const remainingWidth = 100 - newFirstWidth
          const secondWidth = columnWidths[1]
          const thirdWidth = columnWidths[2]
          const totalSecondThird = secondWidth + thirdWidth

          const newSecondWidth = Math.min(Math.max((secondWidth / totalSecondThird) * remainingWidth, minWidth), maxWidth)
          const newThirdWidth = remainingWidth - newSecondWidth

          setColumnWidths([newFirstWidth, newSecondWidth, newThirdWidth])
          setSavedColumnWidths([newFirstWidth, newSecondWidth, newThirdWidth])
        } else if (!moduleCollapsed.promptDebug && moduleCollapsed.advancedConfig) {
          // 只有编写提示词和提示词调试显示：调整两者的比例
          const newFirstWidth = Math.min(Math.max(mousePercentage, minWidth), maxWidth)
          const newThirdWidth = 100 - newFirstWidth

          // 更新当前宽度，但保持高级配置的原始宽度在保存的设置中
          const newWidths = [newFirstWidth, savedColumnWidths[1], newThirdWidth]
          setColumnWidths([newFirstWidth, 0, newThirdWidth]) // 当前显示用
          setSavedColumnWidths(newWidths) // 保存完整宽度用于恢复
        }
      } else if (isDraggingColumn === 1) {
        // 拖动第二个分界线
        if (!moduleCollapsed.advancedConfig && !moduleCollapsed.promptDebug) {
          // 所有模块都显示：调整高级配置和提示词调试的宽度
          const firstWidth = columnWidths[0]
          const availableWidth = 100 - firstWidth
          const newSecondWidth = Math.min(Math.max(mousePercentage - firstWidth, minWidth), Math.min(maxWidth, availableWidth - minWidth))
          const newThirdWidth = availableWidth - newSecondWidth

          setColumnWidths([firstWidth, newSecondWidth, newThirdWidth])
          setSavedColumnWidths([firstWidth, newSecondWidth, newThirdWidth])
        } else if (moduleCollapsed.promptDebug && !moduleCollapsed.advancedConfig) {
          // 只有编写提示词和高级配置显示：调整两者的比例
          const newFirstWidth = Math.min(Math.max(mousePercentage, minWidth), maxWidth)
          const newSecondWidth = 100 - newFirstWidth

          // 更新当前宽度，但保持提示词调试的原始宽度在保存的设置中
          const newWidths = [newFirstWidth, newSecondWidth, savedColumnWidths[2]]
          setColumnWidths([newFirstWidth, newSecondWidth, 0]) // 当前显示用
          setSavedColumnWidths(newWidths) // 保存完整宽度用于恢复
        }
      }
    },
    [isDraggingColumn, columnWidths, moduleCollapsed, savedColumnWidths],
  )

  const handleColumnMouseUp = React.useCallback(() => {
    setIsDraggingColumn(null)
  }, [])

  // 添加全局鼠标事件监听
  React.useEffect(() => {
    if (isDraggingColumn !== null) {
      document.addEventListener('mousemove', handleColumnMouseMove)
      document.addEventListener('mouseup', handleColumnMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    } else {
      document.removeEventListener('mousemove', handleColumnMouseMove)
      document.removeEventListener('mouseup', handleColumnMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    return () => {
      document.removeEventListener('mousemove', handleColumnMouseMove)
      document.removeEventListener('mouseup', handleColumnMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isDraggingColumn, handleColumnMouseMove, handleColumnMouseUp])

  // 处理查看调试追踪
  const handleViewTrace = async (messageIndex: number) => {
    // 功能已移除
    setSnackbar({ open: true, message: t('components.prompts.promptEditPage.viewTraceNotAvailable'), severity: 'info' })
  }

  // 统一的内容获取函数，确保选中时和执行时使用相同逻辑
  const getPromptContentBySource = (messageId?: string, optimizationSourceOverride?: typeof optimizationSource) => {
    // 优先使用 override 中的信息，如果没有则使用组件状态中的 optimizationSource
    const source = optimizationSourceOverride || optimizationSource
    // 优先使用 override 中的 messageId，如果没有则使用传入的 messageId 参数，最后使用组件状态中的
    const targetMessageId = optimizationSourceOverride?.messageId || messageId || optimizationSource.messageId

    // 如果没有 messageId，直接返回空字符串，避免找到不准确的消息
    if (!targetMessageId) {
      console.warn('⚠️ [GET-PROMPT-CONTENT-FUNC] messageId 为空')
      return ''
    }

    if (source.type === 'main') {
      // 只根据 messageId 查找消息
      const systemMessage = promptMessages.find(msg => msg.id === targetMessageId)
      const content = systemMessage ? messageInputValues[systemMessage.id] || systemMessage.content : ''
      return content
    } else if (source.type === 'base' || source.type === 'control') {
      // 基准组和对照组统一处理：基准组编号为0，对照组使用指定的groupId
      const groupId = source.type === 'base' ? 0 : source.groupId
      if (groupId === undefined) {
        console.warn('⚠️ [GET-PROMPT-CONTENT-FUNC] groupId 未定义', { source })
        return ''
      }
      const group = comparisonGroupsData.find(g => g.id === groupId)
      // 只根据 messageId 查找消息
      const systemMessage = group?.messages.find(msg => msg.id === targetMessageId)
      const content = systemMessage ? (group?.messageInputValues || {})[systemMessage.id] || systemMessage.content : ''
      return content
    }
    console.warn('⚠️ [GET-PROMPT-CONTENT-FUNC] 未知的 source.type', { source })
    return ''
  }

  // FormattedPromptEditor的文本选中回调适配器
  const handleFormattedEditorTextSelection = (selectedText: string, position: { x: number; y: number }, messageId?: string) => {
    // 检查对话框是否在 DOM 中（使用 DOM 检查，因为状态更新可能有延迟）
    const dialogExistsInDOM = document.querySelector('[role="dialog"]') || document.querySelector('.MuiDialog-root')
    const isDialogOpen = optimizeDialogOpen || !!dialogExistsInDOM

    // 如果对话框已打开，立即忽略文本选中事件（防止在输入优化需求时触发）
    if (isDialogOpen) {
      return
    }

    // 如果正在忽略文本选中事件，则直接返回（优先使用ref，因为ref是同步的，更可靠）
    if (ignoreTextSelectionRef.current) {
      return
    }

    if (selectedText.trim()) {
      // 直接设置选中状态，信任CodeMirror的选中结果
      setSelectedText(selectedText)
      selectedTextRef.current = selectedText // 同时保存到 ref
      setSelectionPosition(position)
      setCurrentOptimizationType('select')
      setIsSelecting(false)

      // 使用统一的内容获取函数
      const promptContent = getPromptContentBySource(messageId)

      // 保存messageId到optimizationSource中，确保执行时能找到正确的消息
      // 优化：只在messageId实际变化时才更新
      if (messageId && lastOptimizationSourceMessageIdRef.current !== messageId) {
        lastOptimizationSourceMessageIdRef.current = messageId
        setOptimizationSource(prev => ({ ...prev, messageId }))
      }

      const indices = calculateSelectionIndices(selectedText, promptContent)
      setSelectionIndices(indices)
      selectionIndicesRef.current = indices // 同时保存到 ref
    } else {
      // 没有选中文本，清除所有状态
      setSelectedText('')
      setSelectionPosition(null)
      setSelectionIndices(null)
      setIsSelecting(false)
      // 不再清除优化类型，让对话框关闭时统一处理
    }
  }

  // FormattedPromptEditor的光标位置回调适配器工厂
  const createCursorPositionHandler = (messageId: string) => (position: { x: number; y: number }, cursorPos: number) => {
    // 如果正在忽略文本选中事件（例如点击全文反馈优化按钮时），则不处理光标位置变化
    // 优先使用 ref，因为 ref 是同步的，更可靠
    if (ignoreTextSelectionRef.current) {
      return
    }

    // 如果刚刚点击了外部区域，也忽略光标位置变化事件
    if (justClickedOutsideRef.current) {
      return
    }

    // 检查当前是否有选中文本
    const currentSelection = window.getSelection()
    const currentSelectedText = currentSelection ? currentSelection.toString().trim() : ''

    // 只有在没有选中文本时才处理光标模式
    if (!currentSelectedText && !isSelecting) {
      // 清除选中状态，因为这是光标模式
      setSelectedText('')
      setSelectionPosition(null)
      setSelectionIndices(null)
      setIsSelecting(false)

      // 检查是否是同一个消息的光标移动
      const currentCursorMessageId = cursorPosition?.messageId
      if (currentCursorMessageId && currentCursorMessageId !== messageId) {
        // 如果光标从一个消息移动到另一个消息，先清除之前的状态
        setShowCursorOptimizeButton(false)
        setCursorOptimizePosition(null)
        // 使用短暂延迟确保清除操作完成
        setTimeout(() => {
          setCursorOptimizePosition(position)
          setShowCursorOptimizeButton(true)
          // 删除：不再自动设置优化类型，只能根据用户点击的按钮来判断
          // setCurrentOptimizationType('insert')
          setCursorPosition({ messageId, position: cursorPos })
          // 优化：只在messageId实际变化时才更新optimizationSource
          if (lastOptimizationSourceMessageIdRef.current !== messageId) {
            lastOptimizationSourceMessageIdRef.current = messageId
            setOptimizationSource(prev => ({ ...prev, messageId }))
          }
        }, 50)
      } else {
        // 同一个消息内的光标移动，直接更新位置
        setCursorOptimizePosition(position)
        setShowCursorOptimizeButton(true)
        // 删除：不再自动设置优化类型，只能根据用户点击的按钮来判断
        // setCurrentOptimizationType('insert')
        setCursorPosition({ messageId, position: cursorPos })
        // 优化：只在messageId实际变化时才更新optimizationSource
        if (lastOptimizationSourceMessageIdRef.current !== messageId) {
          lastOptimizationSourceMessageIdRef.current = messageId
          setOptimizationSource(prev => ({ ...prev, messageId }))
        }
      }
    }
  }

  // 使用优化的点击外部检测：只在按钮显示时才添加监听器
  // 定义需要排除的选择器（点击这些元素不会隐藏按钮）
  const excludedSelectors = React.useMemo(
    () => [
      // 提示词内容输入框及其子元素
      '.prompt-content-area',
      '[data-testid="formatted-prompt-editor"]',
      '.MuiTextField-root',
      '[role="textbox"]',
      '.cm-editor', // CodeMirror 编辑器
      '.cm-content', // CodeMirror 内容区域
      '.cm-scroller', // CodeMirror 滚动容器
      'textarea', // 文本域
      '[contenteditable]', // 可编辑内容
      '.message-content', // 消息内容区域
      '.formatted-prompt-editor', // FormattedPromptEditor 组件
      // 优化按钮本身
      '[data-testid="selection-optimize-button"]',
      '[data-testid="cursor-optimize-button"]',
      '.bg-gradient-to-r', // 优化按钮的渐变背景类
      'button[class*="text-purple-500"]', // 全文反馈优化按钮
      'button[title*="全文反馈优化"]', // 全文反馈优化按钮（通过 title）
      // 优化对话框
      '[role="dialog"]',
      '.MuiDialog-root',
      '.MuiBackdrop-root',
      // Switch 组件和 FormControlLabel（工具启用开关）
      '.MuiSwitch-root',
      '.MuiFormControlLabel-root',
      'input[type="checkbox"]',
      '[role="switch"]',
    ],
    [],
  )

  // 只在按钮显示时才启用监听器
  const shouldListenForClickOutside = Boolean((selectedText || showCursorOptimizeButton) && !isOptimizing)

  // 使用自定义 hook 处理点击外部事件
  useClickOutsideSelectors(
    excludedSelectors,
    React.useCallback(
      (event: MouseEvent) => {
        // 检查是否点击了包含 lucide-wrench 图标的按钮（全文反馈优化按钮）
        const target = event.target as HTMLElement
        const isWrenchButton = target.closest('button')?.querySelector('.lucide-wrench')
        if (isWrenchButton) {
          return // 忽略全文反馈优化按钮
        }

        // 先设置忽略标记，防止清除状态后立即触发的文本选中事件或光标位置变化事件重新显示按钮
        ignoreTextSelectionRef.current = true
        setIgnoreTextSelection(true)
        // 设置"刚刚点击了外部区域"标记
        justClickedOutsideRef.current = true

        // 隐藏选中反馈优化按钮（只在没有进行优化操作时）
        // 只有当优化对话框已打开时，才保留选中文本和位置信息
        // 检查对话框是否真的在 DOM 中（即使状态还没更新）
        const dialogExistsInDOM = document.querySelector('[role="dialog"]') || document.querySelector('.MuiDialog-root')
        // 检查是否刚刚点击了选中文本优化按钮（在最近 500ms 内），需要短暂保护
        const timeSinceLastClick = Date.now() - lastClickedSelectOptimizeButtonRef.current
        const isRecentlyClicked = timeSinceLastClick < 500 && lastClickedSelectOptimizeButtonRef.current > 0
        // 只有当对话框确实打开时（状态为 true 或 DOM 中存在），或者刚刚点击了按钮，才保留选中文本
        const isDialogOpen = optimizeDialogOpen || !!dialogExistsInDOM
        const shouldPreserveSelection = isDialogOpen || isRecentlyClicked

        if (!shouldPreserveSelection) {
          // 对话框确实没有打开，且不是刚刚点击按钮，清除选中文本和位置信息
          setSelectedText('')
          setSelectionPosition(null)
          setSelectionIndices(null)
          setIsSelecting(false)
          // 清除选中优化类型（但保留插入优化类型，因为插入优化按钮的逻辑是直接清除光标位置）
          if (currentOptimizationType === 'select') {
            setCurrentOptimizationType('general')
          }
        }

        // 隐藏光标优化按钮
        setShowCursorOptimizeButton(false)
        setCursorOptimizePosition(null)
        setCursorPosition(null)

        // 延迟恢复忽略标记，确保点击外部区域后触发的文本选中事件和光标位置变化事件都被忽略
        // 使用防抖机制，避免频繁点击时创建大量定时器
        // 清除之前的定时器，避免堆积
        if (globalClickTimerRef.current) {
          clearTimeout(globalClickTimerRef.current)
          globalClickTimerRef.current = null
        }
        if (globalClickTimer2Ref.current) {
          clearTimeout(globalClickTimer2Ref.current)
          globalClickTimer2Ref.current = null
        }

        globalClickTimerRef.current = setTimeout(() => {
          ignoreTextSelectionRef.current = false
          setIgnoreTextSelection(false)
          // 延迟恢复"刚刚点击了外部区域"标记，确保光标位置变化事件也被忽略
          globalClickTimer2Ref.current = setTimeout(() => {
            justClickedOutsideRef.current = false
            globalClickTimer2Ref.current = null
          }, 500) // 再延迟500ms，总共1500ms，确保光标位置变化事件也被忽略
          globalClickTimerRef.current = null
        }, 1000) // 延长到1000ms，确保光标位置变化事件也被忽略（编辑器可能延迟触发）
      },
      [
        optimizeDialogOpen,
        currentOptimizationType,
        // setState 函数在 React 中是稳定的，不需要作为依赖
        // 但为了代码清晰，我们只包含实际使用的状态值
      ],
    ),
    shouldListenForClickOutside,
  )

  // 设置用户点击的按钮类型标记（在按钮点击时调用）
  const handleSetClickedOptimizationType = (type: OptimizationMode | null) => {
    clickedOptimizationTypeRef.current = type
  }

  // 清理placeholder防抖定时器
  useEffect(() => {
    return () => {
      // 组件卸载时清理所有定时器
      Object.values(placeholderUpdateTimers.current).forEach(timer => {
        clearTimeout(timer)
      })
      placeholderUpdateTimers.current = {}

      // 清理光标优化定时器
      if (cursorOptimizeTimer.current) {
        clearTimeout(cursorOptimizeTimer.current)
      }
    }
  }, [])

  // 比较模式消息操作函数
  const toggleGroupMessageFormat = (groupId: number, index: number) => {
    setGroupMessageFormats(prev => ({
      ...prev,
      [groupId]: {
        ...prev[groupId],
        [index]: prev[groupId]?.[index] === 'markdown' ? 'txt' : 'markdown',
      },
    }))
  }

  const startGroupEditMessage = (groupId: number, index: number, content: string) => {
    setGroupEditingMessage({ groupId, messageIndex: index })
    setGroupEditContent(content)
  }

  const saveGroupEditMessage = (groupId: number, index: number, content: string) => {
    setComparisonGroupsData(prev =>
      prev.map(group =>
        group.id === groupId
          ? {
              ...group,
              chatMessages: group.chatMessages.map((msg, i) => (i === index ? { ...msg, content } : msg)),
            }
          : group,
      ),
    )
    setGroupEditingMessage(null)
    setGroupEditContent('')
  }

  const cancelGroupEditMessage = () => {
    setGroupEditingMessage(null)
    setGroupEditContent('')
  }

  // 统一的拖拽处理函数
  const handleGroupDragStart = (e: React.DragEvent, messageId: string, groupId: number) => {
    setComparisonGroupsData(prev => prev.map(g => (g.id === groupId ? { ...g, draggedMessageId: messageId } : g)))
    e.dataTransfer.setData('application/x-prompt-message-id', messageId)
  }

  const handleGroupDragEnd = (groupId: number) => {
    setComparisonGroupsData(prev => prev.map(g => (g.id === groupId ? { ...g, draggedMessageId: null } : g)))
  }

  const handleGroupDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleGroupDrop = (e: React.DragEvent, index: number, groupId: number) => {
    e.preventDefault()
    const draggedMessageId = e.dataTransfer.getData('application/x-prompt-message-id')

    setComparisonGroupsData(prev =>
      prev.map(group => {
        if (group.id !== groupId) return group

        const draggedIndex = group.messages.findIndex(msg => msg.id === draggedMessageId)
        if (draggedIndex === -1) return group

        const newMessages = [...group.messages]
        const [draggedMessage] = newMessages.splice(draggedIndex, 1)
        newMessages.splice(index, 0, draggedMessage)

        // 更新prompt.content
        const systemMessage = newMessages.find(msg => msg.role === 'system')
        const updatedPrompt = {
          ...group.prompt,
          content: systemMessage?.content || '',
        }

        return {
          ...group,
          messages: newMessages,
          prompt: updatedPrompt,
          draggedMessageId: null,
        }
      }),
    )
  }

  // 统一的调试区域拖动处理
  const handleGroupDebugMouseDown = (groupId: number) => (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDraggingGroupDebug(groupId)
  }

  // 处理拖动事件的useEffect
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingGroupDebug === null || !groupDebugRefs.current[isDraggingGroupDebug]) return

      const debugRef = groupDebugRefs.current[isDraggingGroupDebug]
      const containerRef = groupContainerRefs.current[isDraggingGroupDebug]
      if (!debugRef || !containerRef) return

      const containerRect = containerRef.getBoundingClientRect()
      const newHeight = containerRect.bottom - e.clientY
      const minHeight = 5
      const maxHeight = containerRect.height - 70

      setGroupsDebugHeight(prev => ({
        ...prev,
        [isDraggingGroupDebug]: Math.max(minHeight, Math.min(maxHeight, newHeight)),
      }))
    }

    const handleMouseUp = () => {
      setIsDraggingGroupDebug(null)
    }

    if (isDraggingGroupDebug !== null) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ns-resize'

      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
        document.body.style.cursor = 'auto'
      }
    }
  }, [isDraggingGroupDebug])

  // 统一的参数处理函数
  const handleGroupParameterChange = (groupId: number, paramName: string, value: string) => {
    setComparisonGroupsData(prev =>
      prev.map(g =>
        g.id === groupId
          ? {
              ...g,
              parameters: g.parameters.map(p => (p.name === paramName ? { ...p, value: value } : p)),
            }
          : g,
      ),
    )
  }

  const validateAndClearGroupParameterValue = (groupId: number, paramName: string, value: string) => {
    setComparisonGroupsData(prev =>
      prev.map(g =>
        g.id === groupId
          ? {
              ...g,
              parameters: g.parameters.map(p => (p.name === paramName ? { ...p, value: value.trim() === '' ? '' : value } : p)),
            }
          : g,
      ),
    )
  }

  const handleDeleteGroupTool = (toolId: string, groupId: number) => {
    setComparisonGroupsData(prev =>
      prev.map(g =>
        g.id === groupId
          ? {
              ...g,
              tools: (g.tools || []).filter(tool => tool.id !== toolId),
            }
          : g,
      ),
    )
  }

  // 初始化多运行实例的状态
  React.useEffect(() => {
    const newMultiRunChatMessages = Array(runCount)
      .fill(null)
      .map(() => [])
    const newMultiRunProcessing = Array(runCount).fill(false)

    setMultiRunChatMessages(newMultiRunChatMessages)
    setMultiRunProcessing(newMultiRunProcessing)
    // 初始化多实例 AbortController refs
    multiRunAbortControllerRefs.current = Array(runCount).fill(null)
    // 初始化多实例 debugController refs
    multiRunDebugControllerRefs.current = Array(runCount).fill(null)
  }, [runCount])

  // 统一的对比组数据结构，基准组id为0，对照组id从1开始
  // 初始状态为空数组，实际数据通过 handleEnterComparisonMode 从主页面状态加载
  const [comparisonGroupsData, setComparisonGroupsData] = useState<ComparisonGroupData[]>([])
  // 用于在验证函数中获取最新的 comparisonGroupsData（避免闭包问题）
  const comparisonGroupsDataRef = useRef<ComparisonGroupData[]>([])

  // 群组消息操作 hook
  const { handleDeleteMessage, handleOptimizeAiReplyDialog } = useChatMessageArea({
    setComparisonGroupsData,
    setGroupCompletedMessages,
    comparisonGroupsData,
    setSnackbar,
    t,
    setSelectedAiReply,
    setOptimizationSource,
    setAiReplyOptimizeDialogOpen,
    setAiReplyOptimizeStep,
    setOptimizedPromptTemplate,
    setHumanEvaluation,
  })

  // 进入自由对比模式时，设置所有组的调试区域初始高度为容器高度的50%
  useEffect(() => {
    if (isComparisonMode) {
      // 延迟执行以确保DOM已经渲染
      setTimeout(() => {
        comparisonGroupsData.forEach(group => {
          const containerRef = groupContainerRefs.current[group.id]
          if (containerRef) {
            // 每次进入自由对比模式都重置高度到50%
            const containerHeight = containerRef.offsetHeight
            setGroupsDebugHeight(prev => ({
              ...prev,
              [group.id]: containerHeight * 0.5,
            }))
          }
        })
      }, 100)
    }
  }, [isComparisonMode, comparisonGroupsData.length]) // 只监听数组长度变化，不监听内容变化

  // 从localStorage读取基本信息（用于新创建的提示词）
  const basicInfoStr = localStorage.getItem('newPromptBasicInfo')
  const basicInfo = basicInfoStr ? JSON.parse(basicInfoStr) : null

  // 检查是否是刚创建的提示词
  const isNewlyCreated = basicInfo && basicInfo.prompt_id && String(basicInfo.prompt_id) === id

  // 如果是刚创建的提示词，使用基本信息并清除localStorage
  if (isNewlyCreated) {
    localStorage.removeItem('newPromptBasicInfo')
  }

  // 保持原有的prompt状态用于非对比模式的兼容性
  const [prompt, setPrompt] = useState({
    key: (isNewlyCreated && basicInfo?.key) || '',
    name: (isNewlyCreated && basicInfo?.name) || '',
    description: (isNewlyCreated && basicInfo?.description) || '',
    category: isNew || isNewlyCreated ? 'customer-service' : 'customer-service',
    content: '',
    tags: (isNewlyCreated && basicInfo?.tags) || [],
    isPublic: isNewlyCreated && basicInfo?.isPublic !== undefined ? basicInfo.isPublic : false,
    language: 'zh-CN',
  })

  // 提示词消息状态
  const [promptMessages, setPromptMessages] = useState<PromptMessage[]>([
    {
      id: Date.now().toString(),
      role: 'system',
      content: '',
    },
  ])

  // 解析prompt.content到消息格式 - 只在初始化时执行
  useEffect(() => {
    // 检查是否是多消息格式
    const messagePattern = /\[(SYSTEM|USER|PLACEHOLDER|ASSISTANT)\]\n([\s\S]*?)(?=\n\n\[|$)/g
    const matches = [...prompt.content.matchAll(messagePattern)]

    if (matches.length > 0) {
      // 如果是多消息格式，解析它
      const messages = matches.map((match, index) => ({
        id: Date.now().toString() + index,
        role: match[1].toLowerCase() as any,
        content: match[2].trim(),
      }))
      setPromptMessages(messages)
      // 初始化输入值
      const inputValues: { [key: string]: string } = {}
      messages.forEach(msg => {
        inputValues[msg.id] = msg.content
      })
      setMessageInputValues(inputValues)
    } else if (prompt.content && promptMessages.length === 1) {
      // 如果不是多消息格式，更新第一个消息
      setPromptMessages([
        {
          id: promptMessages[0].id,
          role: 'system',
          content: prompt.content,
        },
      ])
      setMessageInputValues({
        [promptMessages[0].id]: prompt.content,
      })
    }
  }, []) // 只在组件挂载时执行一次

  // 同步promptMessages到prompt.content
  // 优化：移除prompt.content依赖，使用ref避免循环更新
  useEffect(() => {
    // 如果正在从API加载数据（包括加载版本数据），不执行同步，避免触发自动保存
    if (isLoadingFromAPI) {
      return
    }

    const systemMessage = promptMessages.find(msg => msg.role === 'system')
    const newContent = systemMessage?.content || ''

    // 使用ref来比较，避免因为prompt.content变化导致的循环更新
    if (newContent !== lastSyncedContentRef.current) {
      lastSyncedContentRef.current = newContent
      setPrompt(prev => ({ ...prev, content: newContent }))
    }
  }, [promptMessages, isLoadingFromAPI])

  // 添加一个ref来防止重复应用优化数据
  const optimizedDataApplied = useRef(false)

  // 保持原有的modelConfig状态用于非对比模式的兼容性
  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    model: '', // 将在模型列表加载后设置
    temperature: 0.7,
    maxTokens: 1000,
    topP: 1.0,
    frequencyPenalty: 0.0,
    presencePenalty: 0.0,
    stopSequences: [],
  })


  // 统一的变量名格式验证函数
  const autoGeneratedParameters = useMemo(() => {
    // 获取placeholder消息的内容作为placeholder变量
    const placeholderVars: string[] = []

    // 从promptMessages中获取placeholder类型消息的内容
    promptMessages.forEach(msg => {
      if (msg.role === 'placeholder' && msg.content.trim()) {
        placeholderVars.push(msg.content.trim())
      }
    })

    // 在Jinja2模式下，只自动生成placeholder变量（且变量名格式有效）
    if (templateEngine === 'jinja2') {
      return placeholderVars
        .filter(varName => {
          if (!isValidVariableName(varName)) {
            console.warn(`🚫 [VAR-VALIDATION] 跳过无效变量名: "${varName}"，不符合格式要求`)
            return false
          }
          return true
        })
        .map(varName => ({
          name: varName,
          value: '',
          description: `Placeholder变量: ${varName}`,
          type: 'placeholder' as const,
          messages: [
            {
              id: Date.now().toString(),
              role: 'user' as const,
              content: '',
            },
          ],
        }))
    }

    // Normal模式下，生成所有变量（普通变量和placeholder变量）
    const normalVariables = extractVariablesFromNonPlaceholderMessages(promptMessages, templateEngine)
    const allVariables = [...new Set([...normalVariables, ...placeholderVars])]

    return allVariables
      .filter(varName => {
        if (!isValidVariableName(varName)) {
          console.warn(`🚫 [VAR-VALIDATION] 跳过无效变量名: "${varName}"，不符合格式要求`)
          return false
        }
        return true
      })
      .map(varName => {
        const isPlaceholder = placeholderVars.includes(varName)
        return {
          name: varName,
          value: '',
          description: isPlaceholder ? `Placeholder变量: ${varName}` : `变量: ${varName}`,
          type: isPlaceholder ? ('placeholder' as const) : ('text' as const),
          messages: isPlaceholder
            ? [
                {
                  id: Date.now().toString(),
                  role: 'user' as const,
                  content: '',
                },
              ]
            : undefined,
        }
      })
  }, [promptMessages, extractVariablesFromNonPlaceholderMessages, templateEngine])

  const [parameters, setParameters] = useState<PromptParameter[]>(autoGeneratedParameters)

  // 确保参数状态与autoGeneratedParameters保持同步（修复闪现问题）
  useEffect(() => {
    // 只在非API加载状态下同步，避免覆盖API数据
    if (!isLoadingFromAPI) {
      if (templateEngine === 'jinja2') {
        // Jinja2模式下不进行自动同步，保留手动添加的变量
        return
      }

      // 检查当前参数与自动生成的参数是否匹配
      const currentParamNames = parameters.map(p => p.name).sort()
      const autoParamNames = autoGeneratedParameters.map(p => p.name).sort()
      const parametersMatch = currentParamNames.length === autoParamNames.length && currentParamNames.every((name, index) => name === autoParamNames[index])

      if (!parametersMatch) {
        // 智能合并参数，保留已填写的值
        setParameters(currentParams => {
          const mergedParams = autoGeneratedParameters.map(autoParam => {
            // 查找是否有相同名称的现有参数
            const existingParam = currentParams.find(p => p.name === autoParam.name)
            if (existingParam) {
              // 保留现有参数的值和其他用户填写的属性
              return {
                ...autoParam,
                value: existingParam.value,
                dataType: existingParam.dataType || autoParam.dataType,
                messages: existingParam.messages || autoParam.messages,
              }
            }
            return autoParam
          })
          return mergedParams
        })
      }
    }
  }, [autoGeneratedParameters, isLoadingFromAPI, parameters, templateEngine])
  const [editingParamId, setEditingParamId] = useState<string | null>(null)
  const [compositionState, setCompositionState] = useState<{ [key: string]: boolean }>({})
  const [messageInputValues, setMessageInputValues] = useState<{ [key: string]: string }>({})
  const [placeholderValidationErrors, setPlaceholderValidationErrors] = useState<{ [key: string]: string }>({})

  // 对比组的placeholder验证错误状态（基准组id=0，对照组id>=1）
  const [groupPlaceholderValidationErrors, setGroupPlaceholderValidationErrors] = useState<{ [groupId: number]: { [messageId: string]: string } }>({})

  // 稳定的空对象引用，避免每次渲染创建新对象
  const emptyValidationErrors = useMemo(() => ({}), [])

  // 为每个对比组创建 optimizationSource
  const getGroupOptimizationSource = (groupId: number) => {
    const group = comparisonGroupsData.find(g => g.id === groupId)
    return group?.isBaseGroup ? { type: 'base' as const, groupId: undefined } : { type: 'control' as const, groupId }
  }

  // 第一次调用 useLoadPrompt，获取基础加载函数（用于 useDraft 和 useVersionHistory）
  // loadPromptDetail 需要更多参数，会在 useSubmitVersionDialog 之后再次调用获取
  const { 
    loadPromptDetailToPage, 
    loadModels, 
    loadDebugContext,
  } = useLoadPrompt({
    // 基本参数
    id,
    isNew,
    workspaceId,
    userId,
    // 基础状态 setters
    setTemplateEngine,
    setPromptMessages,
    setMessageInputValues,
    setParameters,
    setTools,
    setToolsEnabled,
    setSelectedModel,
    setModelConfig,
    setAvailableModels,
    setModelsLoading,
    setChatMessages,
    setCompletedMessages,
    // 扩展状态 setters（可选，提前传入不影响）
    setPrompt,
    setLatestVersion,
    setIsDraftEdited,
    setDraftSavedTime,
    setIsNewPromptScenario,
    setLoading,
    setIsLoadingFromAPI,
    setSnackbar,
    // 依赖数据
    availableModels,
    selectedModel,
    // Refs
    loadingRef,
    optimizedDataApplied,
    modelsLoadingRef,
    // 回调函数
    showSnackbar,
  })

  // 主页面 messageInputValues 更新函数
  const handleMessageInputValuesChange = (newValues: Record<string, string>) => {
    setMessageInputValues(newValues)
  }

  // 为每个对比组创建 messageInputValues 更新函数
  const handleGroupMessageInputValuesChange = (groupId: number) => (newValues: Record<string, string>) => {
    setComparisonGroupsData(prev => prev.map(g => (g.id === groupId ? { ...g, messageInputValues: newValues } : g)))
  }

  // 初始化messageInputValues
  useEffect(() => {
    const initialValues: { [key: string]: string } = {}
    promptMessages.forEach(msg => {
      initialValues[msg.id] = msg.content
    })
    setMessageInputValues(initialValues)
  }, [])

  // 处理placeholder类型变化
  useEffect(() => {
    // 在Jinja2模式下，不执行类型转换，直接删除不存在的placeholder变量
    if (templateEngine === 'jinja2') {
      // 检查是否有placeholder正在编辑中，如果有则跳过更新
      const isAnyPlaceholderEditing = Object.values(isEditingPlaceholder).some(editing => editing)
      if (isAnyPlaceholderEditing) {
        return
      }

      // 获取当前的placeholder变量
      const placeholderVars: string[] = []
      promptMessages.forEach(msg => {
        if (msg.role === 'placeholder' && msg.content.trim()) {
          placeholderVars.push(msg.content.trim())
        }
      })

      // 在Jinja2模式下，直接删除不存在的placeholder变量
      setParameters(prev =>
        prev.filter(param => {
          if (param.type === 'placeholder') {
            return placeholderVars.includes(param.name)
          }
          return true // 保留所有非placeholder类型的参数
        }),
      )
      return
    }

    // Normal模式下的原有逻辑：允许类型转换
    const placeholderVars: string[] = []
    promptMessages.forEach(msg => {
      if (msg.role === 'placeholder' && msg.content.trim()) {
        placeholderVars.push(msg.content.trim())
      }
    })

    // 更新参数的placeholder类型，但不重新创建参数
    setParameters(prev =>
      prev.map(param => {
        const isPlaceholder = placeholderVars.includes(param.name)
        if (param.type === 'placeholder' && !isPlaceholder) {
          // 从placeholder变为普通变量
          return { ...param, type: 'text', description: `变量: ${param.name}`, messages: undefined }
        } else if (param.type !== 'placeholder' && isPlaceholder) {
          // 从普通变量变为placeholder
          return {
            ...param,
            type: 'placeholder',
            description: `Placeholder变量: ${param.name}`,
            messages: param.messages || [
              {
                id: Date.now().toString(),
                role: 'user' as const,
                content: '',
              },
            ],
          }
        }
        return param
      }),
    )
  }, [promptMessages.map(m => (m.role === 'placeholder' ? m.content.trim() : '')).join('|'), templateEngine, isEditingPlaceholder])

  // 修复变量定义闪现问题：当API加载完成后确保参数同步
  useEffect(() => {
    // 只在API加载完成后执行
    if (isLoadingFromAPI) {
      return
    }

    // 检查是否有placeholder正在编辑中，如果有则跳过参数同步
    const isAnyPlaceholderEditing = Object.values(isEditingPlaceholder).some(editing => editing)
    if (isAnyPlaceholderEditing) {
      return
    }

    // 检查是否需要重新同步参数
    const placeholderVars: string[] = []
    promptMessages.forEach(msg => {
      if (msg.role === 'placeholder' && msg.content.trim()) {
        placeholderVars.push(msg.content.trim())
      }
    })

    let allVariables: string[] = []
    let hasVariables = false
    const hasNoParameters = parameters.length === 0

    if (templateEngine === 'jinja2') {
      // Jinja2模式：只处理placeholder变量，不检测{{variable}}格式
      allVariables = [...placeholderVars]
      hasVariables = placeholderVars.length > 0
    } else {
      // Normal模式：处理{{variable}}格式 + placeholder变量（避免重复）
      const currentVariables = extractVariablesFromNonPlaceholderMessages(promptMessages, templateEngine)
      allVariables = [...new Set([...currentVariables, ...placeholderVars])]
      hasVariables = allVariables.length > 0
    }

    // 如果有变量但没有参数，说明需要同步
    if (hasVariables && hasNoParameters) {
      const newParameters = allVariables
        .filter(varName => {
          if (!isValidVariableName(varName)) {
            console.warn(`🚫 [VAR-VALIDATION] 跳过无效变量名: "${varName}"，不符合格式要求`)
            return false
          }
          return true
        })
        .map(varName => {
          const isPlaceholder = placeholderVars.includes(varName)
          return {
            name: varName,
            value: '',
            description: isPlaceholder ? `Placeholder变量: ${varName}` : `变量: ${varName}`,
            type: isPlaceholder ? ('placeholder' as const) : ('text' as const),
            messages: isPlaceholder
              ? [
                  {
                    id: Date.now().toString(),
                    role: 'user' as const,
                    content: '',
                  },
                ]
              : undefined,
          }
        })

      setParameters(newParameters)
    }
  }, [isLoadingFromAPI, promptMessages, parameters.length, extractVariablesFromNonPlaceholderMessages, isEditingPlaceholder, templateEngine])

  // Update parameters when prompt content changes - 原有逻辑保持兼容性
  useEffect(() => {
    // 如果正在从API加载数据，跳过自动生成变量
    if (isLoadingFromAPI) {
      return
    }

    // 在Jinja2模式下，如果有placeholder正在编辑，完全跳过参数更新
    if (templateEngine === 'jinja2') {
      const isAnyPlaceholderEditing = Object.values(isEditingPlaceholder).some(editing => editing)
      if (isAnyPlaceholderEditing) {
        return
      }
    }

    // 检查是否有placeholder正在编辑中，如果有则跳过自动更新
    const isAnyPlaceholderEditing = Object.values(isEditingPlaceholder).some(editing => editing)
    if (isAnyPlaceholderEditing) {
      return
    }

    // 获取placeholder消息的内容作为placeholder变量
    const placeholderVars: string[] = []
    promptMessages.forEach(msg => {
      if (msg.role === 'placeholder' && msg.content.trim()) {
        placeholderVars.push(msg.content.trim())
      }
    })

    if (templateEngine === 'jinja2') {
      // 检查是否有placeholder正在编辑中，如果有则跳过自动更新
      const isAnyPlaceholderEditing = Object.values(isEditingPlaceholder).some(editing => editing)
      if (isAnyPlaceholderEditing) {
        // 在编辑中时，完全跳过参数更新，避免生成中间状态的变量
        return
      }

      // 在Jinja2模式下，只处理placeholder变量的自动更新
      setParameters(currentParameters => {
        const currentParamNames = currentParameters.map(p => p.name)

        // 🔧 在Jinja2模式下，只保留手动添加的非placeholder变量
        // 不保留任何可能从placeholder消息中误生成的普通变量
        const manualParams = currentParameters.filter(p => {
          // 只保留手动添加的非placeholder类型变量
          // 在Jinja2模式下，所有普通变量都应该是手动添加的
          return p.type !== 'placeholder'
        })

        // 获取当前存在的placeholder参数，用于值保留
        const currentPlaceholderParams = currentParameters.filter(p => p.type === 'placeholder')

        // 添加新的placeholder变量，保留现有placeholder变量的值
        const newPlaceholderParams = [...currentPlaceholderParams]

        placeholderVars.forEach(varName => {
          if (!currentParamNames.includes(varName) && isValidVariableName(varName)) {
            newPlaceholderParams.push({
              name: varName,
              value: '',
              description: `Placeholder变量: ${varName}`,
              type: 'placeholder',
              dataType: 'string', // 默认数据类型
              messages: [
                {
                  id: Date.now().toString(),
                  role: 'user' as const,
                  content: '',
                },
              ],
            })
          } else if (!isValidVariableName(varName)) {
            console.warn(`🚫 [VAR-VALIDATION] 跳过无效placeholder变量名: "${varName}"，不符合格式要求`)
          }
        })

        // 移除不再存在的placeholder变量，但保留手动添加的变量
        // 同时保留现有placeholder变量的值和其他属性
        const filteredPlaceholderParams = newPlaceholderParams
          .filter(param => placeholderVars.includes(param.name))
          .map(param => {
            // 查找原有参数中是否有相同名称的参数，如果有则保留其值
            const existingParam = currentParameters.find(p => p.name === param.name)
            return existingParam
              ? {
                  ...param,
                  value: existingParam.value, // 保留原有的值
                  dataType: existingParam.dataType || param.dataType, // 保留原有的数据类型
                  messages: existingParam.messages || param.messages, // 保留原有的messages
                }
              : param
          })

        // manualParams已经在上面进行了严格清理，这里不需要额外清理

        // 合并清理后的手动添加的变量和自动生成的placeholder变量
        const finalParams = [...manualParams, ...filteredPlaceholderParams]

        return finalParams
      })
      return
    }

    // Normal模式下的原有逻辑
    // 检查是否需要重新生成参数（修复闪现问题）
    const normalVariables = extractVariablesFromNonPlaceholderMessages(promptMessages, templateEngine)
    const hasNoParameters = parameters.length === 0

    // 合并所有变量
    const allVariables = [...new Set([...normalVariables, ...placeholderVars])]

    // 保护逻辑：如果当前已有参数且包含所有需要的变量，不要覆盖
    if (parameters.length > 0 && allVariables.length > 0) {
      const existingParamNames = parameters.map(p => p.name)
      const allVariablesExist = allVariables.every(varName => existingParamNames.includes(varName))

      if (allVariablesExist) {
        return
      }
    }

    // 使用函数式更新，避免依赖parameters状态
    setParameters(currentParameters => {
      const currentParamNames = currentParameters.map(p => p.name)

      // Add new variables
      const newParameters = [...currentParameters]
      allVariables.forEach(varName => {
        if (!currentParamNames.includes(varName) && isValidVariableName(varName)) {
          const isPlaceholder = placeholderVars.includes(varName)
          const existingParam = currentParameters.find(p => p.name === varName)

          if (!existingParam) {
            newParameters.push({
              name: varName,
              value: '',
              description: isPlaceholder ? `Placeholder变量: ${varName}` : `变量: ${varName}`,
              type: isPlaceholder ? 'placeholder' : 'text',
              messages: isPlaceholder
                ? [
                    {
                      id: Date.now().toString(),
                      role: 'user' as const,
                      content: '',
                    },
                  ]
                : undefined,
            })
          }
        }
      })

      // Remove variables that no longer exist，但保留messages数据和用户填写的值
      // 如果allVariables为空但当前有参数，说明是prompt.content为空的情况，不要过滤掉现有参数
      const shouldPreserveExistingParams = allVariables.length === 0 && newParameters.length > 0

      const filteredParameters = (shouldPreserveExistingParams ? newParameters : newParameters.filter(param => allVariables.includes(param.name))).map(
        param => {
          // 查找原有参数中是否有相同名称的参数，如果有则保留其值
          const existingParam = currentParameters.find(p => p.name === param.name)
          const isPlaceholder = placeholderVars.includes(param.name)

          return {
            ...param,
            // 保留原有的值，如果是新参数则使用空值
            value: existingParam ? existingParam.value : param.value,
            type: isPlaceholder ? 'placeholder' : 'text',
            description: isPlaceholder ? `Placeholder变量: ${param.name}` : `变量: ${param.name}`,
            // 保留现有的messages和dataType
            messages: existingParam?.messages || (param.type === 'placeholder' ? param.messages : undefined),
            dataType: existingParam?.dataType || param.dataType,
          }
        },
      )

      return filteredParameters
    })
    // 只在placeholder消息实质性变化时触发
    // 在Jinja2模式下，只监听placeholder消息的内容变化
  }, [
    templateEngine,
    templateEngine === 'jinja2'
      ? promptMessages
          .filter(m => m.role === 'placeholder')
          .map(m => m.content)
          .join('|')
      : promptMessages,
    extractVariablesFromNonPlaceholderMessages,
    isLoadingFromAPI,
    isEditingPlaceholder,
  ])

  // 同步更新 ref，确保验证函数能获取到最新的数据
  useEffect(() => {
    comparisonGroupsDataRef.current = comparisonGroupsData
  }, [comparisonGroupsData])

  // 使用useMemo缓存对比组消息的依赖项字符串，避免每次渲染都重新计算
  const comparisonGroupsMessagesKey = useMemo(
    () => comparisonGroupsData.map(g => g.messages.map(msg => `${msg.role}:${msg.content}`).join('|')).join(';;'),
    [comparisonGroupsData],
  )

  // 自动检测对比组中的变量（自由对比模式下）
  // 优化：使用防抖机制，减少检测频率，提升性能
  useEffect(() => {
    // 只在自由对比模式下才自动检测变量
    if (!isComparisonMode) {
      return
    }

    // 如果正在从API加载数据，跳过自动生成变量
    if (isLoadingFromAPI) {
      return
    }

    // 如果正在编辑 placeholder，跳过检测，避免干扰用户输入
    const isAnyPlaceholderEditing = Object.values(isEditingPlaceholder).some(editing => editing)
    if (isAnyPlaceholderEditing) {
      // 如果正在编辑，清除之前的定时器，不执行检测
      if (comparisonVarDetectTimerRef.current) {
        clearTimeout(comparisonVarDetectTimerRef.current)
        comparisonVarDetectTimerRef.current = null
      }
      return
    }

    // 清除之前的定时器
    if (comparisonVarDetectTimerRef.current) {
      clearTimeout(comparisonVarDetectTimerRef.current)
    }

    // 检测每个组的模板引擎是否变化，如果任何组变化则立即执行检测，否则使用防抖延迟
    let hasGroupTemplateEngineChanged = false
    const currentGroupTemplateEngines = new Map<number, 'normal' | 'jinja2'>()
    comparisonGroupsData.forEach(group => {
      const prevEngine = prevGroupTemplateEnginesRef.current.get(group.id)
      const currentEngine = group.templateEngine
      currentGroupTemplateEngines.set(group.id, currentEngine)

      // 如果之前有记录且与当前不同，说明模板引擎变化了
      if (prevEngine !== undefined && prevEngine !== currentEngine) {
        hasGroupTemplateEngineChanged = true
      }
      // 如果是第一次记录（prevEngine为undefined），不认为是变化，只是初始化
    })
    // 更新所有组的模板引擎记录
    prevGroupTemplateEnginesRef.current = currentGroupTemplateEngines

    // 执行变量检测的函数
    const executeDetection = () => {
      setComparisonGroupsData(prevGroups => {
        // 使用函数式更新，确保获取最新的 messageInputValues，避免覆盖用户正在输入的内容
        return prevGroups.map(group => {
          // 使用每个组自己的模板引擎
          const groupTemplateEngine = group.templateEngine

          let allVariables: string[] = []

          if (groupTemplateEngine === 'jinja2') {
            // Jinja2模式：只处理placeholder变量，不检测{{variable}}格式
            const placeholderVars: string[] = []
            group.messages.forEach(msg => {
              if (msg.role === 'placeholder' && msg.content.trim()) {
                placeholderVars.push(msg.content.trim())
              }
            })
            allVariables = [...placeholderVars]
          } else {
            // Normal模式：处理{{variable}}格式 + placeholder变量（避免重复）
            const extractedVariables = extractVariables(
              group.messages
                .filter(msg => msg.role !== 'placeholder' && msg.content)
                .map(msg => msg.content)
                .join(' '),
              groupTemplateEngine,
            )

            // 获取placeholder变量
            const placeholderVars: string[] = []
            group.messages.forEach(msg => {
              if (msg.role === 'placeholder' && msg.content.trim()) {
                placeholderVars.push(msg.content.trim())
              }
            })

            // 合并所有变量
            allVariables = [...new Set([...extractedVariables, ...placeholderVars])]
          }

          // 检查当前参数
          const existingParamNames = group.parameters.map(p => p.name)
          const newVariables = allVariables.filter(varName => !existingParamNames.includes(varName))
          const removedVariables = existingParamNames.filter(paramName => !allVariables.includes(paramName))

          // 如果没有变化，跳过更新（保持原对象引用，避免不必要的重新渲染）
          if (newVariables.length === 0 && removedVariables.length === 0) {
            return group
          }

          // 移除不再存在的变量，保留现有变量的值
          // 在Jinja2模式下，保留手动添加的非placeholder变量
          let updatedParameters =
            groupTemplateEngine === 'jinja2'
              ? group.parameters.filter(param => allVariables.includes(param.name) || (param.type !== 'placeholder' && !allVariables.includes(param.name)))
              : group.parameters.filter(param => allVariables.includes(param.name))

          // 添加新变量（验证变量名格式）
          newVariables.forEach(varName => {
            if (!isValidVariableName(varName)) {
              console.warn(`🚫 [VAR-VALIDATION] 跳过无效变量名: "${varName}"，不符合格式要求`)
              return // 跳过无效的变量名
            }

            let isPlaceholder = false

            if (groupTemplateEngine === 'jinja2') {
              // Jinja2模式：检查是否在placeholder消息中
              const placeholderVars: string[] = []
              group.messages.forEach(msg => {
                if (msg.role === 'placeholder' && msg.content.trim()) {
                  placeholderVars.push(msg.content.trim())
                }
              })
              isPlaceholder = placeholderVars.includes(varName)
            } else {
              // Normal模式：检查是否是placeholder变量
              const placeholderVars: string[] = []
              group.messages.forEach(msg => {
                if (msg.role === 'placeholder' && msg.content.trim()) {
                  placeholderVars.push(msg.content.trim())
                }
              })
              isPlaceholder = placeholderVars.includes(varName)
            }

            updatedParameters.push({
              name: varName,
              value: '',
              description: isPlaceholder ? `Placeholder变量: ${varName}` : `变量: ${varName}`,
              type: isPlaceholder ? 'placeholder' : 'text',
              dataType: 'string',
              messages: isPlaceholder
                ? [
                    {
                      id: Date.now().toString(),
                      role: 'user' as const,
                      content: '',
                    },
                  ]
                : undefined,
            })
          })

          // 更新类型和描述（确保placeholder变量类型正确）
          updatedParameters = updatedParameters.map(param => {
            let isPlaceholder = false

            if (groupTemplateEngine === 'jinja2') {
              // Jinja2模式：检查是否存在于当前的placeholder消息中
              const placeholderVars: string[] = []
              group.messages.forEach(msg => {
                if (msg.role === 'placeholder' && msg.content.trim()) {
                  placeholderVars.push(msg.content.trim())
                }
              })
              isPlaceholder = placeholderVars.includes(param.name) || param.type === 'placeholder'
            } else {
              // Normal模式：检查是否是placeholder变量
              const placeholderVars: string[] = []
              group.messages.forEach(msg => {
                if (msg.role === 'placeholder' && msg.content.trim()) {
                  placeholderVars.push(msg.content.trim())
                }
              })
              isPlaceholder = placeholderVars.includes(param.name)
            }

            return {
              ...param,
              type: isPlaceholder ? 'placeholder' : 'text',
              description: isPlaceholder ? `Placeholder变量: ${param.name}` : `变量: ${param.name}`,
              // 确保placeholder变量有messages，如果没有则添加默认的
              messages: isPlaceholder
                ? param.messages || [
                    {
                      id: Date.now().toString(),
                      role: 'user' as const,
                      content: '',
                    },
                  ]
                : undefined,
            }
          })

          // 只更新 parameters，保留其他所有字段（特别是 messageInputValues，避免覆盖用户输入）
          return {
            ...group,
            parameters: updatedParameters,
            // 显式保留 messageInputValues，确保不会丢失用户正在输入的内容
            messageInputValues: group.messageInputValues,
          }
        })
      })
    }

    // 如果任何组的模板引擎变化，立即执行检测；否则使用防抖延迟
    if (hasGroupTemplateEngineChanged) {
      executeDetection()
    } else {
      // 设置防抖定时器，延迟2000ms执行检测，进一步减少频繁检测带来的性能开销
      // 增加防抖时间，避免在用户快速输入时频繁触发检测
      comparisonVarDetectTimerRef.current = setTimeout(executeDetection, 2000)
    }

    // 清理函数：清除定时器
    return () => {
      if (comparisonVarDetectTimerRef.current) {
        clearTimeout(comparisonVarDetectTimerRef.current)
        comparisonVarDetectTimerRef.current = null
      }
    }
  }, [
    isComparisonMode,
    templateEngine,
    isLoadingFromAPI,
    isEditingPlaceholder, // 添加依赖，当编辑状态变化时重新评估
    // 使用缓存的依赖项字符串，避免每次渲染都重新计算
    comparisonGroupsMessagesKey,
    extractVariables,
  ])

  // Initialize last saved time
  useEffect(() => {
    if (!lastSavedTime) {
      setLastSavedTime(new Date())
    }
  }, [lastSavedTime])




  // 组件初始化完成后设置标志
  useEffect(() => {
    const initTimer = setTimeout(() => {
      setIsInitialized(true)
    }, 200) // 等待200ms确保所有依赖都已初始化
    return () => clearTimeout(initTimer)
  }, [])

  // 新建提示词场景：自动选择第一个模型
  useEffect(() => {
    // 检查是否是新建场景：isNew 为 true，或者是刚创建的提示词（通过 localStorage 判断）
    const basicInfoStr = localStorage.getItem('newPromptBasicInfo')
    const basicInfo = basicInfoStr ? JSON.parse(basicInfoStr) : null
    const isNewlyCreated = basicInfo && basicInfo.prompt_id && String(basicInfo.prompt_id) === id
    const isNewScenario = isNew || isNewlyCreated || isNewPromptScenario

    // 只在新建场景下执行
    if (!isNewScenario) {
      return
    }

    // 如果已经有选中的模型，不需要自动选择
    if (selectedModel) {
      return
    }

    // 如果模型列表已加载且没有选中模型，自动选择第一个模型
    if (availableModels.length > 0 && !selectedModel && !modelsLoading) {
      const firstModel = availableModels[0]
      setSelectedModel(firstModel)
      const defaultParams = PromptModelService.getModelDefaultParams(firstModel)
      setModelConfig(prev => ({
        ...prev,
        model: firstModel.openModel.model_id,
        model_from: firstModel.model_from,
        ...defaultParams,
      }))
    }
  }, [isNew, id, isNewPromptScenario, availableModels, selectedModel, modelsLoading])

  // 监听语言变化，重新加载模型列表以获取对应语言的模型参数信息
  useEffect(() => {
    const handleLanguageChange = () => {
      // 如果已经有选中的模型，保存当前模型信息，然后重新加载模型列表
      if (selectedModel && workspaceId) {
        pendingModelRestoreRef.current = {
          modelId: selectedModel.openModel.model_id,
          modelFrom: selectedModel.model_from,
        }
        loadModels()
      }
    }

    i18n.on('languageChanged', handleLanguageChange)

    return () => {
      i18n.off('languageChanged', handleLanguageChange)
    }
  }, [i18n, selectedModel, workspaceId, loadModels])

  // 当模型列表更新后，恢复之前选中的模型（用于语言切换场景）
  useEffect(() => {
    if (pendingModelRestoreRef.current && availableModels.length > 0) {
      const { modelId, modelFrom } = pendingModelRestoreRef.current
      const restoredModel = findModelByIdAndFrom(modelId, modelFrom, availableModels)
      if (restoredModel) {
        setSelectedModel(restoredModel)
      }
      // 清除待恢复标记
      pendingModelRestoreRef.current = null
    }
  }, [availableModels, setSelectedModel])

  // 【统一加载逻辑】整合所有进入提示词页面的加载逻辑
  useEffect(() => {
    // 检查基础条件：必须有workspaceId和初始化完成
    if (!workspaceId || !isInitialized) {
      return
    }

    const unifiedLoadProcess = async () => {
      try {
        // 0. 先加载模型列表（所有场景都需要）
        await loadModels()

        // 如果是新建提示词，只加载模型列表即可
        if (isNew || !id) {
          return
        }

        // 1. 调用loadPromptDetail加载所有信息（非新建提示词场景）
        await loadPromptDetail(true)

        // 等待loadPromptDetail完成
        let retryCount = 0
        const maxRetries = 20
        while (loadingRef.current && retryCount < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, 300))
          retryCount++
        }

        // 2. 判断url中是否有版本号，如果有版本号，就根据版本号加载版本信息
        const version = searchParams.get('version')
        const from = searchParams.get('from')

        if (version) {
          // 调用版本列表API
          const response = await PromptService.getVersionList(id, workspaceId, { page_size: 20 })

          if (response.code === 0) {
            const versionList = response.prompt_commit_infos
            // 使用 ref 中存储的 setter
            if (versionHistorySettersRef.current.setApiVersionList) {
              versionHistorySettersRef.current.setApiVersionList(versionList)
            }

            // 查找对应的版本
            const targetVersion = versionList.find((v: any) => v.version === version)
            if (targetVersion) {
              try {
                // 使用统一的版本加载函数
                const loadVersionDataToEditor = versionHistorySettersRef.current.loadVersionDataToEditor
                if (!loadVersionDataToEditor) {
                  console.warn('⚠️ [UNIFIED-LOAD] loadVersionDataToEditor 尚未初始化')
                  return
                }
                const result = await loadVersionDataToEditor(version, 'url')

                if (result.success) {
                  // 自动打开版本历史面板
                  if (versionHistorySettersRef.current.setVersionHistoryOpen) {
                    versionHistorySettersRef.current.setVersionHistoryOpen(true)
                  }

                  // 清除URL参数，避免重复加载
                  const newUrl = new URL(window.location.href)
                  newUrl.searchParams.delete('version')
                  newUrl.searchParams.delete('from')
                  window.history.replaceState({}, '', newUrl.toString())

                  // 显示成功提示
                  showSnackbar(`已自动加载版本 ${version}${from ? ` (来自${from})` : ''}`, 'success')
                } else {
                  showSnackbar(result.message, 'error')
                }
              } catch (error) {
                showSnackbar('版本加载失败，请稍后重试', 'error')
              }
            } else {
              showSnackbar(`未找到版本 ${version}`, 'warning')
            }
          } else {
            showSnackbar(`获取版本列表失败: ${response.msg || '未知错误'}`, 'error')
          }
        } else {
          // 3. 如果没有版本号，判断sessionStorage里面是否有信息

          // 优先处理智能体覆盖数据
          const overrideData = sessionStorage.getItem('promptOverrideData')
          if (overrideData && !optimizedDataApplied.current) {
            try {
              const data = JSON.parse(overrideData)

              // 验证数据有效性
              const now = Date.now()
              const dataAge = now - data.timestamp
              const maxAge = 5 * 60 * 1000 // 5分钟有效期

              if (dataAge < maxAge && (data.fromAgent || data.fromWorkflow) && data.systemPrompt) {
                optimizedDataApplied.current = true

                // 等待promptMessages加载完成
                let waitCount = 0
                while (promptMessages.length === 0 && waitCount < 20) {
                  await new Promise(resolve => setTimeout(resolve, 300))
                  waitCount++
                }

                if (promptMessages.length > 0) {
                  const updatedMessages = [...promptMessages]
                  const systemMessageIndex = updatedMessages.findIndex(msg => msg.role === 'system')

                  if (systemMessageIndex >= 0 && updatedMessages[systemMessageIndex]) {
                    // 更新现有的system消息
                    updatedMessages[systemMessageIndex] = {
                      ...updatedMessages[systemMessageIndex],
                      content: data.systemPrompt,
                    }
                  } else {
                    // 创建新的system消息并插入到开头
                    const newSystemMessage = {
                      id: `system_${Date.now()}`,
                      role: 'system' as const,
                      content: data.systemPrompt,
                    }
                    updatedMessages.unshift(newSystemMessage)
                  }

                  setPromptMessages(updatedMessages)
                  setHasUnsavedChanges(true)
                  const sourceText = data.fromWorkflow ? '工作流' : '智能体'
                  showSnackbar(`已从${sourceText}导入系统提示词内容`, 'success')

                  // 延迟触发自动保存，确保所有数据（包括模型信息和promptDraftData）都已加载完成
                  // 等待足够的时间让状态更新完成
                  setTimeout(() => {
                    triggerAutoSave({ promptMessages: updatedMessages })
                  }, 2000) // 延迟2秒，确保所有数据都已加载
                }

                // 清除sessionStorage中的数据
                sessionStorage.removeItem('promptOverrideData')
              } else {
                sessionStorage.removeItem('promptOverrideData')
              }
            } catch (error) {
              sessionStorage.removeItem('promptOverrideData')
            }
          } else {
            // 检查优化数据
            const optimizedData = sessionStorage.getItem('optimizedPromptData')
            if (optimizedData && !optimizedDataApplied.current) {
              try {
                const data = JSON.parse(optimizedData)

                if (data.fromOptimization && data.content) {
                  optimizedDataApplied.current = true

                  // 等待promptMessages加载完成
                  let waitCount = 0
                  while (promptMessages.length === 0 && waitCount < 20) {
                    await new Promise(resolve => setTimeout(resolve, 300))
                    waitCount++
                  }

                  if (promptMessages.length > 0) {
                    const updatedMessages = [...promptMessages]
                    if (updatedMessages[0] && updatedMessages[0].role === 'system') {
                      updatedMessages[0] = {
                        ...updatedMessages[0],
                        content: data.content,
                      }
                      setPromptMessages(updatedMessages)
                      setHasUnsavedChanges(true)
                      showSnackbar('已应用优化后的提示词内容', 'success')

                      // 延迟触发自动保存，确保所有数据（包括模型信息和promptDraftData）都已加载完成
                      // 等待足够的时间让状态更新完成
                      // 注意：triggerAutoSave 在 useDraft hook 之后定义，这里使用 setTimeout 确保它已定义
                      setTimeout(() => {
                        // 使用 ref 来访问 triggerAutoSave
                        triggerAutoSave({ promptMessages: updatedMessages })
                      }, 2000) // 延迟2秒，确保所有数据都已加载
                    }
                  }

                  // 延迟清除 sessionStorage 和重置标记
                  setTimeout(() => {
                    sessionStorage.removeItem('optimizedPromptData')
                    optimizedDataApplied.current = false
                  }, 3000)
                }
              } catch (error) {
                // 忽略解析优化数据错误
              }
            }
          }
        }

        // 4. 确保调试上下文被加载（在统一加载流程完成后）
        // 等待足够的时间确保loadPromptDetail中的调试上下文加载逻辑已完成
        // 如果loadPromptDetail中的调试上下文加载失败或未执行，这里作为备用加载
        await new Promise(resolve => setTimeout(resolve, 500)) // 等待500ms，确保loadPromptDetail中的调试上下文加载逻辑已完成

        // 再次尝试加载调试上下文（作为备用，确保即使loadPromptDetail中的加载失败也能加载）
        if (!isNew && id) {
          try {
            await loadDebugContext()
          } catch (error) {
            // 忽略调试上下文加载错误
          }
        }
      } catch (error) {
        // 忽略统一加载流程错误
      }
    }

    // 延迟执行，确保组件完全初始化
    const loadTimer = setTimeout(() => {
      unifiedLoadProcess()
    }, 200)

    return () => clearTimeout(loadTimer)
  }, [isInitialized, id, isNew, workspaceId]) // 只依赖关键状态，searchParams 在函数内部读取，不加入依赖

  // 监听路由参数变化，确保数据同步
  useEffect(() => {
    // 当 URL 参数发生变化时，确保重新加载数据
    const forceParam = searchParams.get('force')
    const refreshParam = searchParams.get('refresh')

    if (forceParam === 'true' || refreshParam === 'true') {
      loadPromptDetail(true)

      // 清除参数，避免重复加载
      const newUrl = new URL(window.location.href)
      newUrl.searchParams.delete('force')
      newUrl.searchParams.delete('refresh')
      window.history.replaceState({}, '', newUrl.toString())
    }
  }, [searchParams])

  // 清理定时器
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
        autoSaveTimerRef.current = null
      }
    }
  }, [])

  const { handleEditMessage, handleOptimizeAiReply } = useChatMessageArea({
    chatMessages,
    setEditingMessage,
    setEditContent,
    promptMessages,
    setSnackbar,
    t,
    setSelectedAiReply,
    setOptimizationSource,
    setAiReplyOptimizeDialogOpen,
    setAiReplyOptimizeStep,
    setOptimizedPromptTemplate,
    setHumanEvaluation,
  })

  // 处理关联对象对话框
  const handleOpenAssociationsDialog = (associations: RelationObj[], versionName: string) => {
    setSelectedAssociations(associations)
    setSelectedVersionName(versionName)
    setAssociationsDialogOpen(true)
  }

  const handleCloseAssociationsDialog = () => {
    setAssociationsDialogOpen(false)
    setSelectedAssociations([])
    setSelectedVersionName('')
  }

  // 拖拽相关函数
  const [draggedMessageId, setDraggedMessageId] = useState<string | null>(null)

  const handleDragStart = (e: React.DragEvent, messageId: string) => {
    setDraggedMessageId(messageId)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('application/x-prompt-message-id', messageId)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDragEnd = () => {
    setDraggedMessageId(null)
  }

  // 使用 PromptEditHeader hooks
  const { handleEnterComparisonMode, handleAddControlGroup, handleNavigateToOptimization } = usePromptEditHeader({
    prompt,
    promptMessages,
    messageInputValues,
    modelConfig,
    selectedModel,
    availableModels,
    parameters,
    tools,
    toolsEnabled,
    templateEngine,
    comparisonGroupsData,
    id,
    optimizationSource,
    setGroupCompletedMessages,
    setModelConfig,
    setSelectedModel,
    setComparisonGroupsData,
    setControlGroupCount,
    setGroupsExpanded,
    setGroupsDebugHeight,
    setIsComparisonMode,
  })

  const handleAdvancedConfigTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setAdvancedConfigTab(newValue)
  }

  // 滚动到聊天容器底部
  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }

  // 消息控制功能函数
  const toggleMessageFormat = (index: number) => {
    setMessageFormats(prev => ({
      ...prev,
      [index]: prev[index] === 'markdown' ? 'txt' : 'markdown',
    }))
  }

  const startEditMessage = (index: number, content: string) => {
    setEditingMessage(index)
    setEditContent(content)
  }

  const saveEditMessage = (index: number, content: string) => {
    // 更新消息内容
    const updatedMessages = chatMessages.map((msg, i) => (i === index ? { ...msg, content } : msg))
    setChatMessages(updatedMessages)
    setEditingMessage(null)
    setEditContent('')

    // 非对比模式下，保存调试上下文
    if (!isComparisonMode) {
      saveDebugContext(updatedMessages, debugTraceInfo, undefined, undefined, parameters).catch(err => {
        console.error('保存调试上下文失败:', err)
      })
    }
  }

  const cancelEditMessage = () => {
    setEditingMessage(null)
    setEditContent('')
  }

  const copyMessageContent = async (content: string) => {
    try {
      await copyToClipboard(content, setSnackbar, t('components.prompts.promptEditPage.contentCopied'))
    } catch (err) {
      console.error('复制失败:', err)
    }
  }

  const deleteMessage = (index: number) => {
    const updatedMessages = chatMessages.filter((_, i) => i !== index)
    setChatMessages(prev => prev.filter((_, i) => i !== index))
    // 同时清理对应的格式状态
    setMessageFormats(prev => {
      const newFormats = { ...prev }
      delete newFormats[index]
      // 重新索引后面的消息
      const reindexed: { [key: number]: 'txt' | 'markdown' } = {}
      Object.entries(newFormats).forEach(([key, value]) => {
        const oldIndex = parseInt(key)
        const newIndex = oldIndex > index ? oldIndex - 1 : oldIndex
        reindexed[newIndex] = value
      })
      return reindexed
    })

    // 非对比模式下，删除消息后保存调试上下文
    if (!isComparisonMode) {
      saveDebugContext(updatedMessages, debugTraceInfo, undefined, undefined, parameters).catch(err => {
        console.error('保存调试上下文失败:', err)
      })
    }
  }

  // 监听聊天消息变化，自动滚动到底部
  useEffect(() => {
    scrollToBottom()
  }, [chatMessages])

  // 包装 validateAllPlaceholders 函数，供 hooks 使用
  const validateAllPlaceholdersWrapper = useCallback((): boolean => {
    return validateAllPlaceholders(promptMessages, messageInputValues, t, showSnackbar)
  }, [promptMessages, messageInputValues, t, showSnackbar])

  // 使用调试输入区域 hook
  const {
    handleSendMessage,
    handleRetryLastMessage,
    saveDebugContext,
    buildDebugRequest,
    executeStreamingDebugRequest,
    handleStopStreaming,
    handleClearMainChat,
  } = useDebugInputArea({
    promptId: id!,
    workspaceId,
    userId,
    chatMessages,
    setChatMessages,
    inputMessage,
    setInputMessage,
    isProcessing,
    setIsProcessing,
    isStreamingStopped,
    setIsStreamingStopped,
    debugTraceInfo,
    setDebugTraceInfo,
    completedMessages,
    setCompletedMessages,
    expandedReasoningMessages,
    setExpandedReasoningMessages,
    expandedToolCallMessages,
    setExpandedToolCallMessages,
    scrollToBottom,
    validateAllPlaceholders: validateAllPlaceholdersWrapper,
    enableAutoReadOnly,
    disableAutoReadOnly,
    showSnackbar,
    promptMessages,
    messageInputValues,
    parameters,
    tools,
    templateEngine,
    selectedModel,
    modelConfig,
    availableModels,
    toolsEnabled,
    debugAbortControllerRef, // 传递 AbortController ref（参考快捷优化的停止逻辑）
    reasoningUpdateTimerRef, // 传递 AI 思考过程定时器 ref
  })

  // 使用草稿保存 hook（需要在 useDebugInputArea 之后，因为需要 saveDebugContext）
  const { triggerAutoSave } = useDraft({
    promptId: id,
    isNew,
    userId,
    workspaceId,
    promptMessages,
    parameters,
    modelConfig,
    selectedModel,
    templateEngine,
    toolsEnabled,
    tools,
    modelsLoadingRef,
    loadingRef,
    availableModels,
    promptDraftData: promptDraftDataRef.current, // 使用 ref 来访问 promptDraftData
    chatMessages,
    debugTraceInfo,
    saveDebugContext,
    setDraftSavedTime,
    setIsDraftEdited,
    isComparisonMode,
    isLoadingFromAPI,
    autoSaveTimerRef,
  })

  // 应用组内容到主页面的通用函数（需要在 useDraft 之后，因为依赖 triggerAutoSave）
  const applyGroupContentToMain = useCallback(
    (group: ComparisonGroupData, source: 'exit-comparison' | 'direct-apply') => {
      // 同步所有组数据到主页面
      setPrompt(group.prompt)
      setModelConfig(group.modelConfig)
      setParameters(group.parameters)
      setTools(group.tools)
      setToolsEnabled(group.toolsEnabled)
      setTemplateEngine(group.templateEngine) // 应用模板引擎设置

      // 两种模式都使用追加逻辑：将组聊天消息追加到主页面聊天消息后面
      setChatMessages(prevChatMessages => {
        const combinedChatMessages = [...prevChatMessages, ...group.chatMessages]
        return combinedChatMessages
      })

      // 同步消息相关状态
      setPromptMessages(group.messages)
      setMessageInputValues(group.messageInputValues)

      // 根据modelConfig找到对应的selectedModel
      const groupSelectedModel = findModelByIdAndFrom(group.modelConfig.model, group.modelConfig.model_from, availableModels)
      if (groupSelectedModel) {
        setSelectedModel(groupSelectedModel)
      } else {
        console.warn('⚠️ [APPLY-GROUP-CONTENT] 未找到对应的selectedModel:', {
          modelId: group.modelConfig.model,
          modelFrom: group.modelConfig.model_from,
        })
      }

      setHasUnsavedChanges(true)

      // 根据来源决定是否退出对比模式
      if (source === 'direct-apply') {
        setIsComparisonMode(false)
        // 清理对比组的placeholder验证错误状态
        setGroupPlaceholderValidationErrors({})
      }

      // 使用 setTimeout 确保状态更新后再触发自动保存
      // 注意：由于 setIsComparisonMode(false) 是异步的，isComparisonMode 在闭包中可能还是旧值
      // 所以使用 forceSave=true 强制保存，即使 isComparisonMode 在闭包中还是 true
      setTimeout(() => {
        // 触发自动保存，使用 forceSave=true 强制保存（因为已经调用了 setIsComparisonMode(false)）
        triggerAutoSave(
          {
            promptMessages: group.messages,
            parameters: group.parameters,
            tools: group.tools,
            modelConfig: group.modelConfig, // 直接使用组的模型配置，确保保存的是最新的
            selectedModel: groupSelectedModel, // 直接使用找到的模型，确保保存的是最新的
          },
          true, // forceSave: 强制保存，即使 isComparisonMode 在闭包中还是 true
        )
      }, 0)

      const groupName = group.isBaseGroup
        ? t('components.prompts.exitComparisonDialog.baseGroup')
        : t('components.prompts.exitComparisonDialog.controlGroup', { number: group.id })
      setSnackbar({
        open: true,
        message: t('components.prompts.promptEditPage.appliedGroupContentToEditor', { groupName }),
        severity: 'success',
      })
    },
    [availableModels, triggerAutoSave, t],
  )

  // 使用高级配置编辑器 hook（需要在 useDraft 之后，因为依赖 triggerAutoSave）
  const { handleEditVariable, validateAndClearParameterValue } = useAdvancedConfigEditor({
    parameters,
    setEditingVariableIndex,
    setEditingVariableData,
    setEditVariableDialogOpen,
    setParameters,
    setHasUnsavedChanges,
    triggerAutoSave,
  })

  // 检测变化并更新状态（需要在 useDraft 之后定义，因为依赖 triggerAutoSave）
  const handlePromptChange = useCallback(
    (field: string, value: any) => {
      // 优化：在对比模式下，不需要更新prompt状态和触发自动保存，避免不必要的性能开销
      if (isComparisonMode) {
        // 对比模式下只更新状态，不触发自动保存相关逻辑
        // 注意：这里仍然需要更新prompt状态，因为可能被其他地方使用
        // 但不触发自动保存和hasUnsavedChanges标记
        setPrompt(prev => ({ ...prev, [field]: value }))
        return
      }

      setPrompt(prev => ({ ...prev, [field]: value }))
      setHasUnsavedChanges(true)

      // 如果字段是 'content' 且已经有待保存的定时器，说明可能是 handlePromptMessagesChange 触发的
      // 此时不应该再次触发保存，因为 handlePromptMessagesChange 已经处理了保存逻辑
      // 注意：这里不能完全跳过，因为其他地方也可能修改 content，所以只在有定时器时跳过
      if (field === 'content' && autoSaveTimerRef.current) {
        return
      }

      // 如果不是新建且id存在，触发自动保存
      if (!isNew && id) {
        triggerAutoSave()
      }
    },
    [isComparisonMode, isNew, id, triggerAutoSave],
  )

  // 处理消息列表变化，确保触发自动保存
  const handlePromptMessagesChange = useCallback(
    (newMessages: PromptMessage[]) => {
      const oldMessagesCount = promptMessages.length
      const newMessagesCount = newMessages.length
      const isUserAddingMessage = newMessagesCount > oldMessagesCount
      const isUserDeletingMessage = newMessagesCount < oldMessagesCount

      // 更新消息列表状态
      setPromptMessages(newMessages)

      // 在对比模式下不触发自动保存
      if (isComparisonMode) {
        return
      }

      // 更新prompt.content为所有消息的组合
      const combinedContent = newMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')

      // 更新prompt状态并触发自动保存
      setPrompt(prev => ({ ...prev, content: combinedContent }))
      setHasUnsavedChanges(true)

      // 如果用户主动添加或删除消息，即使 isLoadingFromAPI 为 true，也应该允许保存
      // 因为这是用户操作，不是 API 加载数据导致的
      const shouldAllowSave = isUserAddingMessage || isUserDeletingMessage
      const canTriggerSave = !isNew && id && (!isLoadingFromAPI || shouldAllowSave)

      if (canTriggerSave) {
        triggerAutoSave({ promptMessages: newMessages })
      }
    },
    [isComparisonMode, isNew, id, isLoadingFromAPI, promptMessages, triggerAutoSave],
  )

  // 拖拽相关函数（需要在 useDraft 之后，因为 handleDrop 依赖 handlePromptChange）
  const handleDrop = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault()

    if (!draggedMessageId) return

    const draggedIndex = promptMessages.findIndex(m => m.id === draggedMessageId)
    if (draggedIndex === -1 || draggedIndex === targetIndex) return

    const newMessages = [...promptMessages]
    const [draggedMessage] = newMessages.splice(draggedIndex, 1)
    newMessages.splice(targetIndex, 0, draggedMessage)

    setPromptMessages(newMessages)
    setDraggedMessageId(null)

    // 更新prompt.content
    const combinedContent = newMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
    handlePromptChange('content', combinedContent)

    // 更新输入值的顺序
    const newInputValues: { [key: string]: string } = {}
    newMessages.forEach(msg => {
      newInputValues[msg.id] = messageInputValues[msg.id] || msg.content
    })
    setMessageInputValues(newInputValues)
  }

  // 工具编辑相关功能通过 hooks 管理（需要在 useDraft 之后，因为依赖 triggerAutoSave）
  const {
    editingTool,
    setEditingTool,
    toolDialogOpen,
    currentToolContext,
    handleAddTool,
    handleEditTool,
    handleDeleteTool,
    handleSaveTool,
    handleCloseToolDialog,
  } = useToolEditDialog({
    tools,
    setTools,
    toolsEnabled,
    comparisonGroupsData,
    setComparisonGroupsData,
    showSnackbar,
    setHasUnsavedChanges,
    triggerAutoSave,
  })

  // 使用变量管理 hook（需要在 useDraft 之后，因为依赖 triggerAutoSave）
  const { handleAddVariableFromDialog, handleEditVariableSave } = useAddVariableDialog({
    parameters,
    setParameters,
    promptMessages,
    templateEngine,
    comparisonGroupsData,
    setComparisonGroupsData,
    setAddVariableDialogOpen,
    setGroupAddVariableDialogOpen,
    setEditVariableDialogOpen,
    setEditingVariableIndex,
    setEditingVariableData,
    editingVariableIndex,
    setHasUnsavedChanges,
    triggerAutoSave,
    showSnackbar,
  })

  // 使用反馈优化对话框 hook（需要在 useDraft 之后，因为依赖 triggerAutoSave 和 handlePromptChange）
  const { handleOptimizeDialogOpen, handleOptimizeRequest, handleApplyOptimization, closeOptimizationDialog, handleStopFeedbackOptimization } =
    useFeedbackOptimizeDialog({
      optimizationSource,
      setOptimizationSource,
      currentOptimizationType,
      setCurrentOptimizationType,
      optimizeDialogOpen,
      setOptimizeDialogOpen,
      optimizeInput,
      setOptimizeInput,
      optimizedResult,
      setOptimizedResult,
      isOptimizing,
      setIsOptimizing,
      selectedText,
      setSelectedText,
      selectionIndices,
      setSelectionIndices,
      selectionPosition,
      setSelectionPosition,
      cursorPosition,
      setCursorPosition,
      setShowCursorOptimizeButton,
      setCursorOptimizePosition,
      regeneratePromptInput,
      setRegeneratePromptInput,
      regeneratePromptInputMessageId,
      setRegeneratePromptInputMessageId,
      lastOptimizeInput,
      setLastOptimizeInput,
      ignoreTextSelection,
      setIgnoreTextSelection,
      clickedOptimizationTypeRef,
      fullTextOptimizeMessageIdRef,
      lastOptimizationSourceMessageIdRef,
      selectedTextRef,
      selectionIndicesRef,
      ignoreTextSelectionRef,
      lastClickedSelectOptimizeButtonRef,
      abortControllerRef,
      feedbackOptimizeStreamingRef,
      justClickedOutsideRef,
      cursorOptimizeTimer,
      promptMessages,
      messageInputValues,
      comparisonGroupsData,
      selectedModel,
      modelConfig,
      availableModels,
      workspaceId,
      getPromptContentBySource,
      calculateSelectionIndices,
      setSnackbar,
      setPromptMessages,
      setMessageInputValues,
      setComparisonGroupsData,
      triggerAutoSave,
    })

  // 快捷优化对话框 hooks（需要在 useDraft 之后，因为依赖 triggerAutoSave 和 handlePromptChange）
  const { handleOptimizePrompt, handleStopQuickOptimization, handleApplyQuickOptimization } = useQuickOptimizeDialog({
    optimizingTarget,
    setOptimizingTarget,
    optimizationSource,
    setOptimizationSource,
    quickOptimizeStreaming,
    setQuickOptimizeStreaming,
    optimizationResult,
    setOptimizationResult,
    isOptimizing,
    setIsOptimizing,
    optimizationDialogOpen,
    setOptimizationDialogOpen,
    showQuickOptimizeDiff,
    setShowQuickOptimizeDiff,
    abortControllerRef,
    quickOptimizeStreamingRef,
    promptMessages,
    messageInputValues,
    comparisonGroupsData,
    selectedModel,
    modelConfig,
    availableModels,
    workspaceId,
    setSnackbar,
    setPromptMessages,
    setMessageInputValues,
    setComparisonGroupsData,
    setHasUnsavedChanges,
    triggerAutoSave,
    handlePromptChange,
  })

  // 使用调试优化对话框 hook（需要在 useDraft 之后，因为依赖 triggerAutoSave 和 handlePromptChange）
  const {
    handleStartAiReplyOptimization,
    handleRetryAiReplyOptimization,
    handleStopDebugOptimization,
    handleDebugOptimizeClose,
    handleDebugOptimizeStepChange,
    handleDebugOptimizedTemplateChange,
    handleDebugHumanEvaluationChange,
    handleAdoptOptimizedPrompt,
  } = useDebugOptimizeDialog({
    selectedAiReply,
    setSelectedAiReply,
    humanEvaluation,
    setHumanEvaluation,
    aiReplyOptimizeStep,
    setAiReplyOptimizeStep,
    optimizedPromptTemplate,
    setOptimizedPromptTemplate,
    aiReplyOptimizeDialogOpen,
    setAiReplyOptimizeDialogOpen,
    abortControllerRef,
    badcaseOptimizeStreamingRef,
    workspaceId,
    optimizationSource,
    promptMessages,
    setPromptMessages,
    messageInputValues,
    setMessageInputValues,
    comparisonGroupsData,
    setComparisonGroupsData,
    selectedModel,
    modelConfig,
    availableModels,
    setSnackbar,
    handlePromptChange,
    setHasUnsavedChanges,
    triggerAutoSave,
  })

  // 使用调试输入区域组 hook（对比模式）
  const { handleSendComparisonMessage, handleClearComparisonChat, handleGroupRetryLastMessage, handleStopGroupStreaming } = useDebugInputAreaGroup({
    promptId: id!,
    comparisonGroupsData,
    setComparisonGroupsData,
    groupAbortControllerRefs,
    groupDebugControllerRefs,
    groupReasoningExpanded,
    setGroupReasoningExpanded,
    groupToolCallExpanded,
    setGroupToolCallExpanded,
    setGroupCompletedMessages,
    setGroupStreamingStopped,
    groupStreamingStoppedRef,
    isStreamingStoppedRef,
    availableModels,
    enableAutoReadOnly,
    disableAutoReadOnly,
    executeStreamingDebugRequest,
    comparisonInputMessage,
    setComparisonInputMessage,
    isStreamingStopped,
    setIsStreamingStopped,
    workspaceId,
    t,
    showSnackbar,
  })

  // 使用多实例运行对话框 hook
  const {
    handleMultiRunSendMessage,
    handleRegenerateMessage,
    handleStopMultiRunStreaming,
    handleClearAllMultiRun,
    handleClearMultiRunInstance,
    handleDeleteMultiRunMessage,
    handleUpdateMultiRunMessage,
    handleAdoptConversation,
    handleToggleMultiRunToolCallExpanded,
    handleToggleMultiRunReasoningExpanded,
  } = useMultiRunDialog({
    multiRunChatMessages,
    setMultiRunChatMessages,
    multiRunProcessing,
    setMultiRunProcessing,
    multiRunAbortControllerRefs,
    multiRunDebugControllerRefs,
    multiRunExpandedToolCallMessages,
    setMultiRunExpandedToolCallMessages,
    multiRunExpandedReasoningMessages,
    setMultiRunExpandedReasoningMessages,
    validateAllPlaceholders: validateAllPlaceholdersWrapper,
    buildDebugRequest,
    executeStreamingDebugRequest,
    disableAutoReadOnly,
    runCount,
    promptId: id!,
    workspaceId,
    selectedModel,
    modelConfig,
    availableModels,
    showSnackbar,
    chatMessages,
    setChatMessages,
    setCompletedMessages,
    scrollToBottom,
    saveDebugContext,
    debugTraceInfo,
    setMultiRunDialogOpen,
  })

  // 使用版本历史 hook（需要在 useSubmitVersionDialog 之前调用，以便传递 setVersionHistoryOpen）
  const {
    versionHistoryOpen,
    setVersionHistoryOpen,
    versionListLoading,
    setApiVersionList,
    revertConfirmOpen,
    setRevertConfirmOpen,
    handleOpenVersionHistory,
    getDisplayVersions,
    handleSelectVersion,
    loadVersionDataToEditor,
    handleRollbackToVersion,
    handleConfirmRevert,
  } = useVersionHistory({
    id,
    isNew,
    workspaceId,
    userId,
    isDraftEdited,
    draftSavedTime,
    selectedVersion,
    availableModels,
    selectedModel,
    setSelectedVersion,
    setPromptMessages,
    setPrompt,
    setHasUnsavedChanges,
    setMessageInputValues,
    setParameters,
    setTools,
    setToolsEnabled,
    setSelectedModel,
    setModelConfig,
    setIsLoadingFromAPI,
    setTemplateEngine,
    setChatMessages,
    setCompletedMessages,
    setLastSavedTime,
    setIsDraftEdited,
    loadPromptDetailToPage,
    loadDebugContext,
  })

  // 将 hook 返回的 setter 存储到 ref 中，供 useEffect 使用
  useEffect(() => {
    versionHistorySettersRef.current = {
      setApiVersionList,
      setVersionHistoryOpen,
      loadVersionDataToEditor,
    }
  }, [setApiVersionList, setVersionHistoryOpen, loadVersionDataToEditor])

  // 使用提交版本对话框 hook（在 useVersionHistory 之后调用，以便传递正确的 setVersionHistoryOpen）
  // 这个 hook 会返回 setPromptCommitData 和 setPromptDraftData，供 loadPromptDetail 使用
  const {
    submitVersionDialogOpen,
    submitVersionStep,
    promptCommitData,
    promptDraftData,
    versionNumber,
    versionNumberError,
    setPromptCommitData,
    setPromptDraftData,
    setVersionNumber,
    setVersionNumberError,
    handleSubmitVersion,
    handleCloseSubmitVersionDialog,
    handleNextStep,
    handlePrevStep,
    handleConfirmSubmitVersion,
  } = useSubmitVersionDialog({
    id,
    workspaceId,
    userId,
    isNew,
    prompt,
    parameters,
    modelConfig,
    versionDescription,
    setVersionDescription,
    setVersionNumberInitialized,
    setLastSavedTime,
    setHasUnsavedChanges,
    setDraftSavedTime,
    setIsDraftEdited,
    setVersionHistoryOpen, // 使用 hook 返回的 setVersionHistoryOpen
    setLatestVersion,
    setIsLoadingFromAPI,
    loadPromptDetailToPage,
    loadDebugContext, // 传递加载调试上下文的函数
    showSnackbar,
    setSnackbar,
  })

  // 第二次调用 useLoadPrompt，补充传入 setPromptCommitData 和 setPromptDraftData，获取完整的 loadPromptDetail
  const { loadPromptDetail } = useLoadPrompt({
    // 基本参数
    id,
    isNew,
    workspaceId,
    userId,
    // 基础状态 setters
    setTemplateEngine,
    setPromptMessages,
    setMessageInputValues,
    setParameters,
    setTools,
    setToolsEnabled,
    setSelectedModel,
    setModelConfig,
    setAvailableModels,
    setModelsLoading,
    setChatMessages,
    setCompletedMessages,
    // 扩展状态 setters（用于 loadPromptDetail，包括来自 useSubmitVersionDialog 的 setters）
    setPrompt,
    setLatestVersion,
    setPromptCommitData, // 来自 useSubmitVersionDialog
    setPromptDraftData, // 来自 useSubmitVersionDialog
    setIsDraftEdited,
    setDraftSavedTime,
    setIsNewPromptScenario,
    setLoading,
    setIsLoadingFromAPI,
    setSnackbar,
    // 依赖数据
    availableModels,
    selectedModel,
    // Refs
    loadingRef,
    optimizedDataApplied,
    modelsLoadingRef,
    // 回调函数
    showSnackbar,
  })

  // 将 promptDraftData 存储到 ref 中，供 useDraft 使用
  useEffect(() => {
    promptDraftDataRef.current = promptDraftData
  }, [promptDraftData])

  // 使用基本信息对话框 hook
  const {
    editInfoDialogOpen,
    setEditInfoDialogOpen,
    handleOpenEditInfoDialog,
    handleSaveBasicInfo,
    createCopyDialogOpen,
    setCreateCopyDialogOpen,
    copyPromptData,
    setCopyPromptData,
    handleCreateCopy,
    handleConfirmCreateCopy,
  } = usePromptBasicInfoDialog({
    id,
    isNew,
    workspaceId,
    userId,
    prompt,
    setPrompt,
    setLoading,
    setHasUnsavedChanges,
    selectedVersion,
    getDisplayVersions,
    showSnackbar,
    setSnackbar,
  })

  // Placeholder消息防抖更新函数（主页面）
  const debouncedUpdatePlaceholderContent = useCallback(
    (messageId: string, index: number, newValue: string) => {
      // 立即更新promptMessages，但不立即更新prompt.content
      setPromptMessages(prevMessages => {
        const newMessages = [...prevMessages]
        // 添加边界检查，确保索引有效且消息对象存在
        if (index >= 0 && index < newMessages.length && newMessages[index]) {
          newMessages[index].content = newValue
        } else {
          console.error(`[debouncedUpdatePlaceholderContent-MAIN] 无效的索引或消息对象: index=${index}, length=${newMessages.length}, messageId=${messageId}`)
          return prevMessages // 如果索引无效，不更新
        }
        return newMessages
      })

      // 清除之前的定时器
      if (placeholderUpdateTimers.current[messageId]) {
        clearTimeout(placeholderUpdateTimers.current[messageId])
      }

      // 标记正在编辑
      setIsEditingPlaceholder(prev => ({ ...prev, [messageId]: true }))

      // 设置防抖定时器，延迟更新prompt.content（这会触发参数重新生成）
      placeholderUpdateTimers.current[messageId] = setTimeout(() => {
        // 🔧 修复时序问题：在Jinja2模式下，在更新prompt.content之后才标记编辑完成
        // 这样可以确保参数更新时不会误判断编辑状态
        setPromptMessages(currentMessages => {
          const combinedContent = currentMessages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
          handlePromptChange('content', combinedContent)
          return currentMessages // 不改变promptMessages，只触发prompt.content更新
        })

        // 在下一个事件循环中标记编辑完成，确保参数更新逻辑已经执行
        setTimeout(() => {
          setIsEditingPlaceholder(prev => ({ ...prev, [messageId]: false }))
          // 清理定时器引用
          delete placeholderUpdateTimers.current[messageId]
        }, 0)
      }, 800) // 800ms防抖延迟
    },
    [handlePromptChange, templateEngine],
  )

  // Placeholder消息防抖更新函数（对比组专用）
  const createGroupDebouncedUpdatePlaceholderContent = useCallback(
    (groupId: number) => (messageId: string, index: number, newValue: string) => {
      // 立即更新对应组的messages
      setComparisonGroupsData(prevGroups => {
        return prevGroups.map(group => {
          if (group.id !== groupId) return group

          const newMessages = [...group.messages]

          // 添加边界检查，确保索引有效且消息对象存在
          if (index >= 0 && index < newMessages.length && newMessages[index]) {
            newMessages[index].content = newValue
          } else {
            console.error(
              `[debouncedUpdatePlaceholderContent-GROUP-${groupId}] 无效的索引或消息对象: index=${index}, length=${newMessages.length}, messageId=${messageId}`,
            )
            return group // 如果索引无效，不更新
          }

          return {
            ...group,
            messages: newMessages,
          }
        })
      })

      // 清除之前的定时器
      if (placeholderUpdateTimers.current[messageId]) {
        clearTimeout(placeholderUpdateTimers.current[messageId])
      }

      // 标记正在编辑
      setIsEditingPlaceholder(prev => ({ ...prev, [messageId]: true }))

      // 设置防抖定时器，延迟触发自动保存
      placeholderUpdateTimers.current[messageId] = setTimeout(() => {
        setHasUnsavedChanges(true)
        triggerAutoSave()

        // 标记编辑完成
        setIsEditingPlaceholder(prev => ({ ...prev, [messageId]: false }))
      }, 800)
    },
    [placeholderUpdateTimers, triggerAutoSave],
  )

  const handleParameterChange = useCallback(
    (paramName: string, value: string) => {
      // 使用 setParameters 的回调函数来确保获取最新状态并触发自动保存
      setParameters(prev => {
        const updatedParameters = prev.map(param => (param.name === paramName ? { ...param, value } : param))

        // 在状态更新后触发自动保存草稿（草稿保存成功后会统一调用 saveDebugContext，避免重复触发）
        setTimeout(() => {
          setHasUnsavedChanges(true)
          triggerAutoSave({ parameters: updatedParameters })
        }, 0)

        return updatedParameters
      })
    },
    [setHasUnsavedChanges, triggerAutoSave],
  )

  return (
    <div className="bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 px-6 py-6 h-full" style={{ minHeight: '93vh', width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
      {/* Page header */}
      <PromptEditHeader
        isNew={isNew}
        prompt={prompt}
        loading={loading}
        isReadOnlyMode={isReadOnlyMode}
        onOpenEditInfoDialog={handleOpenEditInfoDialog}
        isNewPromptScenario={isNewPromptScenario}
        isDraftEdited={isDraftEdited}
        draftSavedTime={draftSavedTime}
        latestVersion={latestVersion}
        isComparisonMode={isComparisonMode}
        onEnterComparisonMode={handleEnterComparisonMode}
        onNavigateToOptimization={handleNavigateToOptimization}
        onOpenVersionHistory={handleOpenVersionHistory}
        onSubmitVersion={handleSubmitVersion}
        onExitComparison={() => setExitComparisonDialogOpen(true)}
        comparisonGroupsData={comparisonGroupsData}
        onAddControlGroup={handleAddControlGroup}
      />

      {/* 自由对比模式 */}
      {isComparisonMode ? (
        <div className="min-h-[calc(100vh-200px)]">
          {/* 动态列对比布局 */}
          <div
            className={`grid grid-cols-1 ${controlGroupCount === 1 ? 'xl:grid-cols-2' : controlGroupCount === 2 ? 'xl:grid-cols-3' : 'xl:grid-cols-4'} gap-0`}
          >
            {/* 渲染所有组（基准组id=0，对照组id>=1） */}
            {comparisonGroupsData.map(group => (
              <div
                key={group.id}
                ref={el => (groupContainerRefs.current[group.id] = el)}
                className="bg-white border border-gray-200 flex flex-col h-[calc(100vh-250px)]"
              >
                <div className="p-4 border-b border-gray-200 bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Typography variant="h6" className="text-gray-800 font-semibold">
                        {group.isBaseGroup
                          ? t('prompts.promptEdit.comparisonMode.baseGroup')
                          : t('prompts.promptEdit.comparisonMode.controlGroup', { id: group.id })}
                      </Typography>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<Check className="w-4 h-4" />}
                        onClick={() => {
                          // 直接应用组内容到主页面
                          applyGroupContentToMain(group, 'direct-apply')
                        }}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        {t('prompts.promptEdit.comparisonMode.apply')}
                      </Button>
                      {!group.isBaseGroup && (
                        <IconButton
                          size="small"
                          className={comparisonGroupsData.length <= 2 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-400 hover:text-red-600'}
                          title={
                            comparisonGroupsData.length <= 2
                              ? t('prompts.promptEdit.comparisonMode.keepAtLeastOneControl')
                              : t('prompts.promptEdit.comparisonMode.deleteGroup')
                          }
                          disabled={comparisonGroupsData.length <= 2}
                          onClick={() => {
                            if (comparisonGroupsData.length <= 2) return

                            // 删除指定的对照组
                            const newGroups = comparisonGroupsData.filter(g => g.id !== group.id)
                            // 重新编号对照组（基准组保持id=0，对照组从1开始重新编号）
                            const renumberedGroups = newGroups.map(g =>
                              g.isBaseGroup ? g : { ...g, id: newGroups.filter(ng => !ng.isBaseGroup).indexOf(g) + 1 },
                            )
                            setComparisonGroupsData(renumberedGroups)
                            setControlGroupCount(renumberedGroups.length - 1) // 减去基准组
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                        </IconButton>
                      )}
                    </div>
                  </div>
                </div>

                {/* 编写提示词和高级配置区域 */}
                <div className="flex-1 overflow-hidden" style={{ height: `calc(100% - ${groupsDebugHeight[group.id] || 300}px - 8px)` }}>
                  <div className="p-4 flex flex-col h-full overflow-y-auto">
                    {/* 编写提示词 */}
                    <div className="mb-6">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Typography variant="subtitle1" className="text-gray-800 font-medium">
                            {t('prompts.promptEdit.comparisonMode.editPrompt')}
                          </Typography>
                          <IconButton
                            size="small"
                            onClick={() =>
                              setGroupsExpanded(prev => ({
                                ...prev,
                                [group.id]: {
                                  ...prev[group.id],
                                  promptEditor: !prev[group.id]?.promptEditor,
                                },
                              }))
                            }
                            className="text-gray-600 hover:bg-gray-100"
                          >
                            {groupsExpanded[group.id]?.promptEditor ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </IconButton>
                        </div>
                      </div>

                      {/* 使用PromptContentEditor组件 */}
                      {groupsExpanded[group.id]?.promptEditor && (
                        <PromptContentEditor
                          templateEngine={group.templateEngine}
                          readOnly={isReadOnlyMode}
                          onTemplateEngineChange={newEngine => {
                            if (newEngine !== group.templateEngine) {
                              setGroupPendingTemplateEngine(prev => ({ ...prev, [group.id]: newEngine }))
                              setGroupTemplateEngineChangeDialogOpen(prev => ({ ...prev, [group.id]: true }))
                              setCurrentTemplateEngineChangeGroupId(group.id)
                            }
                          }}
                          promptMessages={group.messages}
                          onPromptMessagesChange={newMessages => {
                            setComparisonGroupsData(prev => prev.map(g => (g.id === group.id ? { ...g, messages: newMessages } : g)))
                          }}
                          messageInputValues={group.messageInputValues || {}}
                          onMessageInputValuesChange={handleGroupMessageInputValuesChange(group.id)}
                          externalValidationErrors={groupPlaceholderValidationErrors[group.id] || emptyValidationErrors}
                          onValidationErrorsChange={errors => {
                            setGroupPlaceholderValidationErrors(prev => ({
                              ...prev,
                              [group.id]: errors,
                            }))
                          }}
                          optimizationSource={getGroupOptimizationSource(group.id)}
                          currentMessageId={cursorPosition?.messageId}
                          selectedText={selectedText}
                          selectionPosition={selectionPosition}
                          isSelecting={isSelecting}
                          showCursorOptimizeButton={showCursorOptimizeButton}
                          cursorOptimizePosition={cursorOptimizePosition}
                          onTextSelection={(selectedText, position, messageId) => {
                            // 如果正在忽略文本选中事件（例如点击全文反馈优化按钮时），则直接返回
                            // 优先使用ref，因为ref是同步的，更可靠
                            if (ignoreTextSelectionRef.current) {
                              return
                            }

                            // 检查对话框是否在 DOM 中（使用 DOM 检查，因为状态更新可能有延迟）
                            const dialogExistsInDOM = document.querySelector('[role="dialog"]') || document.querySelector('.MuiDialog-root')
                            const isDialogOpen = optimizeDialogOpen || !!dialogExistsInDOM
                            if (isDialogOpen) {
                              return
                            }

                            // 对比组的文本选中处理：需要保留组信息
                            if (selectedText.trim()) {
                              // 先更新 optimizationSource，确保包含正确的组信息
                              const newOptimizationSource = {
                                type: group.isBaseGroup ? 'base' : 'control',
                                groupId: group.isBaseGroup ? undefined : group.id,
                                messageId: messageId || undefined,
                              } as typeof optimizationSource
                              setOptimizationSource(newOptimizationSource)
                              // 同时更新 ref，确保在打开对话框时能正确恢复 messageId
                              if (messageId && lastOptimizationSourceMessageIdRef.current !== messageId) {
                                lastOptimizationSourceMessageIdRef.current = messageId
                              }

                              // 设置选中文本和位置
                              setSelectedText(selectedText)
                              selectedTextRef.current = selectedText
                              setSelectionPosition(position)
                              setCurrentOptimizationType('select')
                              setIsSelecting(false)

                              // 使用组信息获取内容
                              const targetGroup = group.isBaseGroup
                                ? comparisonGroupsData.find(g => g.id === 0)
                                : comparisonGroupsData.find(g => g.id === group.id)
                              const targetMessage = messageId ? targetGroup?.messages.find(msg => msg.id === messageId) : undefined
                              const promptContent = targetMessage ? (targetGroup?.messageInputValues || {})[targetMessage.id] || targetMessage.content : ''

                              // 计算选中位置
                              const indices = calculateSelectionIndices(selectedText, promptContent)
                              setSelectionIndices(indices)
                              selectionIndicesRef.current = indices
                            } else {
                              // 没有选中文本，清除所有状态
                              setSelectedText('')
                              setSelectionPosition(null)
                              setSelectionIndices(null)
                              setIsSelecting(false)
                            }
                          }}
                          onCursorPositionChange={(messageId: string) => (position: { x: number; y: number }, cursorPos: number) => {
                            // 对比组的光标位置处理：需要保留组信息
                            // 如果正在忽略文本选中事件（例如点击全文反馈优化按钮时），则不处理光标位置变化
                            // 优先使用ref，因为ref是同步的，更可靠
                            if (ignoreTextSelectionRef.current) {
                              return
                            }

                            // 如果刚刚点击了外部区域，也忽略光标位置变化事件
                            if (justClickedOutsideRef.current) {
                              return
                            }

                            // 检查当前是否有选中文本
                            const currentSelection = window.getSelection()
                            const currentSelectedText = currentSelection ? currentSelection.toString().trim() : ''

                            // 只有在没有选中文本时才处理光标模式
                            if (!currentSelectedText && !isSelecting) {
                              // 清除选中状态，因为这是光标模式
                              setSelectedText('')
                              setSelectionPosition(null)
                              setSelectionIndices(null)
                              setIsSelecting(false)

                              // 检查是否是同一个消息的光标移动
                              const currentCursorMessageId = cursorPosition?.messageId
                              if (currentCursorMessageId && currentCursorMessageId !== messageId) {
                                // 如果光标从一个消息移动到另一个消息，先清除之前的状态
                                setShowCursorOptimizeButton(false)
                                setCursorOptimizePosition(null)
                                // 使用短暂延迟确保清除操作完成
                                setTimeout(() => {
                                  setCursorOptimizePosition(position)
                                  setShowCursorOptimizeButton(true)
                                  // 删除：不再自动设置优化类型，只能根据用户点击的按钮来判断
                                  // setCurrentOptimizationType('insert')
                                  setCursorPosition({ messageId, position: cursorPos })
                                  // 根据当前所在的组设置正确的 optimizationSource
                                  // 优化：只在真正变化时才更新，避免频繁触发effect
                                  const newOptimizationSource = {
                                    type: group.isBaseGroup ? 'base' : 'control',
                                    groupId: group.isBaseGroup ? undefined : group.id,
                                    messageId,
                                  } as typeof optimizationSource
                                  // 检查是否与上次的值相同，避免不必要的更新
                                  const lastSource = lastOptimizationSourceRef.current
                                  if (
                                    !lastSource ||
                                    lastSource.type !== newOptimizationSource.type ||
                                    lastSource.groupId !== newOptimizationSource.groupId ||
                                    lastSource.messageId !== newOptimizationSource.messageId
                                  ) {
                                    setOptimizationSource(newOptimizationSource)
                                    lastOptimizationSourceRef.current = newOptimizationSource
                                  }
                                }, 50)
                              } else {
                                // 同一个消息内的光标移动，直接更新位置
                                setCursorOptimizePosition(position)
                                setShowCursorOptimizeButton(true)
                                // 删除：不再自动设置优化类型，只能根据用户点击的按钮来判断
                                // setCurrentOptimizationType('insert')
                                setCursorPosition({ messageId, position: cursorPos })
                                // 根据当前所在的组设置正确的 optimizationSource
                                // 优化：只在真正变化时才更新，避免频繁触发effect
                                const newOptimizationSource = {
                                  type: group.isBaseGroup ? 'base' : 'control',
                                  groupId: group.isBaseGroup ? undefined : group.id,
                                  messageId,
                                } as typeof optimizationSource
                                // 检查是否与上次的值相同，避免不必要的更新
                                const lastSource = lastOptimizationSourceRef.current
                                if (
                                  !lastSource ||
                                  lastSource.type !== newOptimizationSource.type ||
                                  lastSource.groupId !== newOptimizationSource.groupId ||
                                  lastSource.messageId !== newOptimizationSource.messageId
                                ) {
                                  setOptimizationSource(newOptimizationSource)
                                  lastOptimizationSourceRef.current = newOptimizationSource
                                }
                              }
                            }
                          }}
                          draggedMessageId={group.draggedMessageId}
                          onDragStart={(e, messageId) => handleGroupDragStart(e, messageId, group.id)}
                          onDragEnd={() => handleGroupDragEnd(group.id)}
                          onDragOver={handleGroupDragOver}
                          onDrop={(e, index) => handleGroupDrop(e, index, group.id)}
                          compositionState={compositionState}
                          onCompositionStateChange={setCompositionState}
                          onPromptChange={handlePromptChange}
                          onCopyToClipboard={content => copyToClipboard(content, setSnackbar, t('prompts.promptEdit.promptEditor.messageCopied'))}
                          onValidatePlaceholderContent={validatePlaceholderContentWithMessage}
                          onDebouncedUpdatePlaceholderContent={createGroupDebouncedUpdatePlaceholderContent(group.id)}
                          onOptimizePrompt={target => handleOptimizePrompt({ ...target, groupId: group.id })}
                          onOptimizeDialogOpen={(optimizationSourceOverride?: typeof optimizationSource) => {
                            handleOptimizeDialogOpen(optimizationSourceOverride)
                          }}
                          onOptimizeInput={setOptimizeInput}
                          onSelectedTextChange={text => {
                            setSelectedText(text)
                            selectedTextRef.current = text // 同步更新 ref
                          }}
                          onSelectionIndicesChange={indices => {
                            setSelectionIndices(indices)
                            selectionIndicesRef.current = indices // 同步更新 ref
                          }}
                          onOptimizationSourceChange={setOptimizationSource}
                          onCurrentOptimizationTypeChange={type => {
                            setCurrentOptimizationType(type as OptimizationMode | null)
                            // 如果设置为 'select'，记录时间戳用于保护对话框打开过程
                            if (type === 'select') {
                              lastClickedSelectOptimizeButtonRef.current = Date.now()
                            }
                          }}
                          onSetClickedOptimizationType={handleSetClickedOptimizationType}
                          onOptimizingTargetChange={setOptimizingTarget}
                          onIgnoreTextSelectionChange={setIgnoreTextSelection}
                          onIgnoreTextSelectionRefChange={ignore => {
                            ignoreTextSelectionRef.current = ignore
                          }}
                        />
                      )}
                    </div>

                    {/* 高级配置 */}
                    <div className="mb-6">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Typography variant="subtitle1" className="text-gray-800 font-medium">
                            {t('prompts.promptEdit.comparisonMode.advancedConfig')}
                          </Typography>
                          <IconButton
                            size="small"
                            onClick={() =>
                              setGroupsExpanded(prev => ({
                                ...prev,
                                [group.id]: {
                                  ...prev[group.id],
                                  advancedConfig: !prev[group.id]?.advancedConfig,
                                },
                              }))
                            }
                            className="text-gray-600 hover:bg-gray-100"
                          >
                            {groupsExpanded[group.id]?.advancedConfig ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </IconButton>
                        </div>
                      </div>

                      {groupsExpanded[group.id]?.advancedConfig && (
                        <div className="border border-gray-200 rounded-lg bg-white/60">
                          <AdvancedConfigEditor
                            activeTab={group.tab}
                            readOnly={isReadOnlyMode}
                            onTabChange={(e, newValue) => {
                              setComparisonGroupsData(prev => prev.map(g => (g.id === group.id ? { ...g, tab: newValue } : g)))
                            }}
                            parameters={group.parameters}
                            templateEngine={group.templateEngine}
                            onParametersChange={newParams => {
                              setComparisonGroupsData(prev => prev.map(g => (g.id === group.id ? { ...g, parameters: newParams } : g)))
                            }}
                            onParameterChange={(paramName, value) => handleGroupParameterChange(group.id, paramName, value)}
                            onParameterBlur={(paramName, value) => validateAndClearGroupParameterValue(group.id, paramName, value)}
                            onCopyToClipboard={content => copyToClipboard(content, setSnackbar, t('prompts.promptEdit.advancedConfig.variableValueCopied'))}
                            onEditVariable={() => {}} // 组不支持编辑变量
                            onDeleteVariable={() => {}} // 组不支持删除变量
                            onAddVariable={templateEngine === 'jinja2' ? () => setGroupAddVariableDialogOpen({ open: true, groupId: group.id }) : undefined}
                            editingParamId={null}
                            onEditingParamIdChange={() => {}}
                            availableModels={availableModels}
                            selectedModel={findModelByIdAndFrom(group.modelConfig.model, group.modelConfig.model_from, availableModels) || null}
                            modelConfig={group.modelConfig}
                            onModelChange={model => {
                              if (model) {
                                // 获取模型的默认参数
                                const defaultParams = PromptModelService.getModelDefaultParams(model)
                                // 更新模型配置，包括默认参数
                                setComparisonGroupsData(prev =>
                                  prev.map(g =>
                                    g.id === group.id
                                      ? {
                                          ...g,
                                          modelConfig: {
                                            ...g.modelConfig,
                                            model: String(model.openModel.model_id),
                                            model_from: model.model_from,
                                            ...defaultParams,
                                          },
                                        }
                                      : g,
                                  ),
                                )
                              }
                            }}
                            onModelConfigChange={config => {
                              setComparisonGroupsData(prev => prev.map(g => (g.id === group.id ? { ...g, modelConfig: config } : g)))
                            }}
                            modelsLoading={modelsLoading}
                            tools={group.tools || []}
                            toolsEnabled={group.toolsEnabled}
                            onToolsChange={newTools => {
                              setComparisonGroupsData(prev => prev.map(g => (g.id === group.id ? { ...g, tools: newTools } : g)))
                            }}
                            onToolsEnabledChange={enabled => {
                              setComparisonGroupsData(prev => prev.map(g => (g.id === group.id ? { ...g, toolsEnabled: enabled } : g)))
                            }}
                            onAddTool={() => handleAddTool(group.id)}
                            onEditTool={tool => handleEditTool(tool, group.id === 0 ? 'base' : { type: 'control', groupId: group.id })}
                            onDeleteTool={toolId => handleDeleteGroupTool(toolId, group.id)}
                            onHasUnsavedChanges={setHasUnsavedChanges}
                            onTriggerAutoSave={triggerAutoSave}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* 可拖动的分隔线 */}
                <div
                  className="h-2 bg-gray-200 hover:bg-gray-300 cursor-ns-resize transition-colors relative"
                  onMouseDown={handleGroupDebugMouseDown(group.id)}
                >
                  <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-1 bg-gray-400 rounded-full w-12 mx-auto" />
                </div>

                {/* 提示词调试 */}
                <div
                  ref={el => (groupDebugRefs.current[group.id] = el)}
                  className="border-t border-gray-200 overflow-hidden"
                  style={{ height: `${groupsDebugHeight[group.id] || 300}px` }}
                >
                  <div className="p-4 h-full flex flex-col">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Typography variant="subtitle1" className="text-gray-800 font-medium">
                          {t('prompts.promptEdit.promptDebug.title')}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() =>
                            setGroupsExpanded(prev => ({
                              ...prev,
                              [group.id]: {
                                ...prev[group.id],
                                promptDebug: !prev[group.id]?.promptDebug,
                              },
                            }))
                          }
                          className="text-gray-600 hover:bg-gray-100"
                        >
                          {groupsExpanded[group.id]?.promptDebug ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </IconButton>
                      </div>
                      {groupsExpanded[group.id]?.promptDebug && (
                        <Button
                          size="small"
                          startIcon={<Trash2 className="w-4 h-4" />}
                          onClick={() => {
                            setComparisonGroupsData(prev => prev.map(g => (g.id === group.id ? { ...g, chatMessages: [] } : g)))
                            setGroupCompletedMessages(prev => ({
                              ...prev,
                              [group.id]: new Set(),
                            }))
                          }}
                          className="text-gray-600 hover:bg-gray-50"
                        >
                          {t('prompts.promptEdit.comparisonMode.clear')}
                        </Button>
                      )}
                    </div>

                    {/* 聊天消息区域 */}
                    {groupsExpanded[group.id]?.promptDebug && (
                      <div
                        className="flex-1 bg-gray-50 rounded-lg border border-gray-200 mb-3"
                        style={{
                          minHeight: 0,
                          maxHeight: 'calc(100vh - 500px)', // 限制最大高度
                          overflow: 'hidden',
                          display: 'flex',
                          flexDirection: 'column',
                        }}
                      >
                        <ChatMessageArea
                          messages={group.chatMessages || []}
                          onRetryMessage={index => handleGroupRetryLastMessage(group.id, index)}
                          onOptimizeReply={index => handleOptimizeAiReplyDialog?.(group.id, index)}
                          onCopyMessage={content => copyToClipboard(content, setSnackbar, t('components.prompts.promptEditPage.messageCopied'))}
                          onEditMessage={index => startGroupEditMessage(group.id, index, group.chatMessages?.[index]?.content || '')}
                          onDeleteMessage={index => handleDeleteMessage?.(group.id, index)}
                          onViewTrace={handleViewTrace}
                          isProcessing={group.isProcessing}
                          onStopStreaming={() => handleStopGroupStreaming(group.id)}
                          isStreamingStopped={groupStreamingStopped[group.id] || false}
                          messageFormats={groupMessageFormats[group.id] || {}}
                          onToggleMessageFormat={index => toggleGroupMessageFormat(group.id, index)}
                          completedMessages={(() => {
                            const completed = groupCompletedMessages[group.id] || new Set()

                            return completed
                          })()}
                          expandedReasoningMessages={
                            new Set(
                              Object.keys(groupReasoningExpanded[group.id] || {})
                                .filter(key => groupReasoningExpanded[group.id][parseInt(key)])
                                .map(key => parseInt(key)),
                            )
                          }
                          onToggleReasoningExpanded={index =>
                            setGroupReasoningExpanded(prev => ({
                              ...prev,
                              [group.id]: {
                                ...prev[group.id],
                                [index]: !prev[group.id]?.[index],
                              },
                            }))
                          }
                          expandedToolCallMessages={
                            new Set(
                              Object.keys(groupToolCallExpanded[group.id] || {})
                                .filter(key => groupToolCallExpanded[group.id][parseInt(key)])
                                .map(key => parseInt(key)),
                            )
                          }
                          onToggleToolCallExpanded={index =>
                            setGroupToolCallExpanded(prev => ({
                              ...prev,
                              [group.id]: {
                                ...prev[group.id],
                                [index]: !prev[group.id]?.[index],
                              },
                            }))
                          }
                          editingMessageIndex={groupEditingMessage?.groupId === group.id ? groupEditingMessage?.messageIndex : null}
                          editingContent={groupEditContent}
                          onStartEdit={(index, content) => startGroupEditMessage(group.id, index, content)}
                          onSaveEdit={(index, content) => {
                            setGroupEditContent(content)
                            saveGroupEditMessage(group.id, index, content)
                          }}
                          onCancelEdit={cancelGroupEditMessage}
                          onEditContentChange={setGroupEditContent}
                          containerRef={groupChatMessageAreaRefs.current[group.id]}
                          emptyStateText={t('components.prompts.chatMessageArea.emptyStateText')}
                          emptyStateSubtext={t('components.prompts.chatMessageArea.emptyStateSubtext')}
                          className="p-4 flex-1"
                          readOnly={isReadOnlyMode}
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 底部共享输入框 */}
          <DebugInputAreaGroup
            comparisonInputMessage={comparisonInputMessage}
            onInputChange={setComparisonInputMessage}
            onSend={handleSendComparisonMessage}
            onClear={handleClearComparisonChat}
            comparisonGroupsData={comparisonGroupsData}
          />
        </div>
      ) : (
        /* 正常编辑模式 */
        <div className="resizable-columns-container flex min-h-[calc(100vh-200px)] gap-0 h-[calc(100%-72px)]" style={{ minWidth: 'fit-content', width: '100%' }}>
          {/* Column 1: 编写提示词 */}
          <div style={{ width: `${visibleModules.actualWidths[0]}%` }}>
            <Card className="h-full shadow-lg border-0 bg-white/60 backdrop-blur-sm flex flex-col overflow-hidden" sx={{ borderRadius: 0 }}>
              <CardContent 
                className="flex-1 flex flex-col overflow-hidden"
                sx={{
                  padding: 'clamp(0.2rem, 1vw, 1.5rem) !important',
                }}
              >
                <div 
                  className="flex items-center justify-between"
                  style={{
                    marginBottom: 'clamp(0.375rem, 1.5vh, 1rem)',
                  }}
                >
                  <div 
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.25rem, 0.5vw, 0.625rem)',
                    }}
                  >
                    <div 
                      className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-md"
                      style={{
                        padding: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                      }}
                    >
                      <Brain 
                        className="text-white"
                        style={{
                          width: 'clamp(0.5rem, 1vw, 1rem)',
                          height: 'clamp(0.5rem, 1vw, 1rem)',
                        }}
                      />
                    </div>
                    <Typography 
                      variant="h6" 
                      className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent"
                      sx={{
                        fontSize: 'clamp(0.625rem, 1.2vw, 1.125rem)',
                        lineHeight: 1.3,
                      }}
                    >
                      {t('prompts.promptEdit.promptEditor.title')}
                    </Typography>
                  </div>

                  {/* 展开其他模块的按钮 */}
                  <div 
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                    }}
                  >
                    {moduleCollapsed.advancedConfig && (
                      <Tooltip title={t('prompts.promptEdit.promptEditor.expandAdvancedConfig')}>
                        <IconButton
                          size="small"
                          onClick={() => toggleModuleCollapse('advancedConfig')}
                          className="text-gray-400 hover:text-blue-600"
                          sx={{
                            width: 'clamp(1.25rem, 2.5vw, 2rem)',
                            height: 'clamp(1.25rem, 2.5vw, 2rem)',
                            '&:hover': {
                              backgroundColor: '#eff6ff',
                            },
                          }}
                        >
                          <Sliders 
                            style={{
                              width: 'clamp(0.625rem, 1.2vw, 1rem)',
                              height: 'clamp(0.625rem, 1.2vw, 1rem)',
                            }}
                          />
                        </IconButton>
                      </Tooltip>
                    )}

                    {moduleCollapsed.promptDebug && (
                      <Tooltip title={t('prompts.promptEdit.promptEditor.expandPromptDebug')}>
                        <IconButton
                          size="small"
                          onClick={() => toggleModuleCollapse('promptDebug')}
                          className="text-gray-400 hover:text-blue-600"
                          sx={{
                            width: 'clamp(1.25rem, 2.5vw, 2rem)',
                            height: 'clamp(1.25rem, 2.5vw, 2rem)',
                            '&:hover': {
                              backgroundColor: '#eff6ff',
                            },
                          }}
                        >
                          <TestTube 
                            style={{
                              width: 'clamp(0.625rem, 1.2vw, 1rem)',
                              height: 'clamp(0.625rem, 1.2vw, 1rem)',
                            }}
                          />
                        </IconButton>
                      </Tooltip>
                    )}
                  </div>
                </div>

                <PromptContentEditor
                  templateEngine={templateEngine}
                  readOnly={isReadOnlyMode}
                  onTemplateEngineChange={newEngine => {
                    if (newEngine !== templateEngine) {
                      setPendingTemplateEngine(newEngine)
                      setTemplateEngineChangeDialogOpen(true)
                    }
                  }}
                  promptMessages={promptMessages}
                  onPromptMessagesChange={handlePromptMessagesChange}
                  messageInputValues={messageInputValues}
                  onMessageInputValuesChange={handleMessageInputValuesChange}
                  externalValidationErrors={placeholderValidationErrors}
                  onValidationErrorsChange={setPlaceholderValidationErrors}
                  optimizationSource={optimizationSource.type === 'main' ? optimizationSource : { type: 'main' }}
                  currentMessageId={cursorPosition?.messageId}
                  selectedText={selectedText}
                  selectionPosition={selectionPosition}
                  isSelecting={isSelecting}
                  showCursorOptimizeButton={showCursorOptimizeButton}
                  cursorOptimizePosition={cursorOptimizePosition}
                  onTextSelection={handleFormattedEditorTextSelection}
                  onCursorPositionChange={createCursorPositionHandler}
                  onOptimizeDialogOpen={(optimizationSourceOverride?: typeof optimizationSource) => {
                    handleOptimizeDialogOpen(optimizationSourceOverride)
                  }}
                  onOptimizeInput={setOptimizeInput}
                  onSelectedTextChange={text => {
                    setSelectedText(text)
                    // 同步更新 ref
                    selectedTextRef.current = text
                  }}
                  onSelectionIndicesChange={indices => {
                    setSelectionIndices(indices)
                    // 同步更新 ref
                    selectionIndicesRef.current = indices
                  }}
                  onOptimizationSourceChange={setOptimizationSource}
                  onCurrentOptimizationTypeChange={type => {
                    setCurrentOptimizationType(type as OptimizationMode | null)
                    // 如果设置为 'select'，记录时间戳用于保护对话框打开过程
                    if (type === 'select') {
                      lastClickedSelectOptimizeButtonRef.current = Date.now()
                    }
                  }}
                  onSetClickedOptimizationType={handleSetClickedOptimizationType}
                  onOptimizingTargetChange={setOptimizingTarget}
                  onIgnoreTextSelectionChange={setIgnoreTextSelection}
                  onIgnoreTextSelectionRefChange={ignore => {
                    ignoreTextSelectionRef.current = ignore
                  }}
                  draggedMessageId={draggedMessageId}
                  onDragStart={handleDragStart}
                  onDragEnd={handleDragEnd}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  compositionState={compositionState}
                  onCompositionStateChange={setCompositionState}
                  onPromptChange={handlePromptChange}
                  onCopyToClipboard={content => copyToClipboard(content, setSnackbar, t('prompts.promptEdit.promptEditor.messageCopied'))}
                  onValidatePlaceholderContent={validatePlaceholderContentWithMessage}
                  onDebouncedUpdatePlaceholderContent={debouncedUpdatePlaceholderContent}
                  onOptimizePrompt={handleOptimizePrompt}
                />
              </CardContent>
            </Card>
          </div>

          {/* 第一个拖动分界线 - 当编写提示词和高级配置都显示时显示 */}
          {!moduleCollapsed.advancedConfig && !moduleCollapsed.promptDebug && (
            <div
              className={`w-1 bg-gradient-to-b from-gray-200/60 to-gray-300/60 hover:from-blue-400 hover:to-blue-500 cursor-col-resize transition-all duration-300 relative group ${
                isDraggingColumn === 0 ? 'from-blue-500 to-blue-600 shadow-lg' : ''
              }`}
              onMouseDown={handleColumnMouseDown(0)}
            >
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/60">
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full mr-0.5"></div>
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full ml-0.5"></div>
              </div>
            </div>
          )}

          {/* 编写提示词和提示词调试之间的分界线 - 当高级配置收起时显示 */}
          {moduleCollapsed.advancedConfig && !moduleCollapsed.promptDebug && (
            <div
              className={`w-1 bg-gradient-to-b from-gray-200/60 to-gray-300/60 hover:from-blue-400 hover:to-blue-500 cursor-col-resize transition-all duration-300 relative group ${
                isDraggingColumn === 0 ? 'from-blue-500 to-blue-600 shadow-lg' : ''
              }`}
              onMouseDown={handleColumnMouseDown(0)}
            >
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/60">
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full mr-0.5"></div>
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full ml-0.5"></div>
              </div>
            </div>
          )}

          {/* Column 2: 高级配置 */}
          {!moduleCollapsed.advancedConfig && (
            <div style={{ width: `${visibleModules.actualWidths[1]}%` }}>
              <Card className="h-full shadow-lg border-0 bg-white/60 backdrop-blur-sm flex flex-col overflow-hidden" sx={{ borderRadius: 0 }}>
                <CardContent 
                  className="flex-1 flex flex-col overflow-hidden"
                  sx={{
                    padding: 'clamp(0.2rem, 1vw, 1.5rem) !important',
                  }}
                >
                  <div 
                    className="flex items-center justify-between"
                    style={{
                      marginBottom: 'clamp(0.1rem, 0.25vh, 0.2rem)',
                    }}
                  >
                    <div 
                      className="flex items-center"
                      style={{
                        gap: 'clamp(0.25rem, 0.5vw, 0.625rem)',
                      }}
                    >
                      <div 
                        className="bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg shadow-md"
                        style={{
                          padding: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                        }}
                      >
                        <Sliders 
                          className="text-white"
                          style={{
                            width: 'clamp(0.5rem, 1vw, 1rem)',
                            height: 'clamp(0.5rem, 1vw, 1rem)',
                          }}
                        />
                      </div>
                      <Typography 
                        variant="h6" 
                        className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent"
                        sx={{
                          fontSize: 'clamp(0.625rem, 1.2vw, 1.125rem)',
                          lineHeight: 1.3,
                        }}
                      >
                        {t('prompts.promptEdit.advancedConfig.title')}
                      </Typography>
                    </div>
                    <Tooltip title={t('prompts.promptEdit.advancedConfig.collapse')}>
                      <IconButton 
                        size="small" 
                        onClick={() => toggleModuleCollapse('advancedConfig')} 
                        className="text-gray-400 hover:text-gray-600"
                        sx={{
                          width: 'clamp(1.25rem, 2.5vw, 2rem)',
                          height: 'clamp(1.25rem, 2.5vw, 2rem)',
                        }}
                      >
                        <ChevronUp 
                          style={{
                            width: 'clamp(0.625rem, 1.2vw, 1rem)',
                            height: 'clamp(0.625rem, 1.2vw, 1rem)',
                          }}
                        />
                      </IconButton>
                    </Tooltip>
                  </div>

                  <AdvancedConfigEditor
                    activeTab={advancedConfigTab}
                    readOnly={isReadOnlyMode}
                    onTabChange={handleAdvancedConfigTabChange}
                    parameters={parameters}
                    templateEngine={templateEngine}
                    onParametersChange={newParameters => {
                      setParameters(newParameters)
                      setHasUnsavedChanges(true)
                      triggerAutoSave({ parameters: newParameters })
                    }}
                    onParameterChange={handleParameterChange}
                    onParameterBlur={validateAndClearParameterValue}
                    onCopyToClipboard={content => copyToClipboard(content, setSnackbar, t('prompts.promptEdit.advancedConfig.variableValueCopied'))}
                    onEditVariable={handleEditVariable}
                    onDeleteVariable={index => {
                      const newParameters = parameters.filter((_, i) => i !== index)
                      setParameters(newParameters)
                      setHasUnsavedChanges(true)
                      triggerAutoSave({ parameters: newParameters })
                    }}
                    onAddVariable={() => setAddVariableDialogOpen(true)}
                    editingParamId={editingParamId}
                    onEditingParamIdChange={setEditingParamId}
                    availableModels={availableModels}
                    selectedModel={selectedModel}
                    modelConfig={modelConfig}
                    onModelChange={model => {
                      if (model) {
                        setSelectedModel(model)
                        // 更新模型配置，包括model_from字段
                        const defaultParams = PromptModelService.getModelDefaultParams(model)
                        const newModelConfig = {
                          ...modelConfig,
                          model: model.openModel.model_id,
                          model_from: model.model_from,
                          ...defaultParams,
                        }
                        setModelConfig(newModelConfig)

                        // 触发自动保存，使用新的模型信息
                        setHasUnsavedChanges(true)
                        triggerAutoSave({
                          selectedModel: model,
                          modelConfig: newModelConfig,
                        })
                      }
                    }}
                    onModelConfigChange={newConfig => {
                      setModelConfig(newConfig)
                      // 触发自动保存，使用新的模型配置
                      setHasUnsavedChanges(true)
                      triggerAutoSave({
                        modelConfig: newConfig,
                      })
                    }}
                    modelsLoading={modelsLoading}
                    tools={tools}
                    toolsEnabled={toolsEnabled}
                    onToolsChange={setTools}
                    onToolsEnabledChange={setToolsEnabled}
                    onAddTool={handleAddTool}
                    onEditTool={tool => handleEditTool(tool, 'main')}
                    onDeleteTool={handleDeleteTool}
                    onHasUnsavedChanges={setHasUnsavedChanges}
                    onTriggerAutoSave={triggerAutoSave}
                    enableAutoSave={true}
                  />
                </CardContent>
              </Card>
            </div>
          )}

          {/* 第二个拖动分界线 - 当高级配置和提示词调试都显示时显示 */}
          {!moduleCollapsed.advancedConfig && !moduleCollapsed.promptDebug && (
            <div
              className={`w-1 bg-gradient-to-b from-gray-200/60 to-gray-300/60 hover:from-blue-400 hover:to-blue-500 cursor-col-resize transition-all duration-300 relative group ${
                isDraggingColumn === 1 ? 'from-blue-500 to-blue-600 shadow-lg' : ''
              }`}
              onMouseDown={handleColumnMouseDown(1)}
            >
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/60">
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full mr-0.5"></div>
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full ml-0.5"></div>
              </div>
            </div>
          )}

          {/* 编写提示词和高级配置之间的分界线 - 当提示词调试收起时显示 */}
          {moduleCollapsed.promptDebug && !moduleCollapsed.advancedConfig && (
            <div
              className={`w-1 bg-gradient-to-b from-gray-200/60 to-gray-300/60 hover:from-blue-400 hover:to-blue-500 cursor-col-resize transition-all duration-300 relative group ${
                isDraggingColumn === 1 ? 'from-blue-500 to-blue-600 shadow-lg' : ''
              }`}
              onMouseDown={handleColumnMouseDown(1)}
            >
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/60">
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full mr-0.5"></div>
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full ml-0.5"></div>
              </div>
            </div>
          )}

          {/* Column 3: 聊天调试 */}
          {!moduleCollapsed.promptDebug && (
            <div style={{ width: `${visibleModules.actualWidths[2]}%` }}>
              <Card className="h-full shadow-lg border-0 bg-white/60 backdrop-blur-sm flex flex-col" sx={{ borderRadius: 0 }}>
                <CardContent 
                  className="flex-1 flex flex-col h-full min-h-0"
                  sx={{
                    padding: 'clamp(0.2rem, 1vw, 1.5rem) !important',
                  }}
                >
                  {/* 标题区域 */}
                  <div 
                    className="flex items-center justify-between flex-shrink-0"
                    style={{
                      marginBottom: 'clamp(0.375rem, 1.5vh, 1rem)',
                    }}
                  >
                    <div 
                      className="flex items-center"
                      style={{
                        gap: 'clamp(0.25rem, 0.5vw, 0.625rem)',
                      }}
                    >
                      <div 
                        className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg shadow-md"
                        style={{
                          padding: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                        }}
                      >
                        <TestTube 
                          className="text-white"
                          style={{
                            width: 'clamp(0.5rem, 1vw, 1rem)',
                            height: 'clamp(0.5rem, 1vw, 1rem)',
                          }}
                        />
                      </div>
                      <Typography 
                        variant="h6" 
                        className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent"
                        sx={{
                          fontSize: 'clamp(0.625rem, 1.2vw, 1.125rem)',
                          lineHeight: 1.3,
                        }}
                      >
                        {t('prompts.promptEdit.promptDebug.title')}
                      </Typography>
                    </div>
                    <Tooltip title={t('prompts.promptEdit.promptDebug.collapse')}>
                      <IconButton 
                        size="small" 
                        onClick={() => toggleModuleCollapse('promptDebug')} 
                        className="text-gray-400 hover:text-gray-600"
                        sx={{
                          width: 'clamp(1.25rem, 2.5vw, 2rem)',
                          height: 'clamp(1.25rem, 2.5vw, 2rem)',
                        }}
                      >
                        <ChevronUp 
                          style={{
                            width: 'clamp(0.625rem, 1.2vw, 1rem)',
                            height: 'clamp(0.625rem, 1.2vw, 1rem)',
                          }}
                        />
                      </IconButton>
                    </Tooltip>
                  </div>

                  {/* 聊天消息区域 - 使用ChatMessageArea组件 */}
                  <div
                    className="flex-1 bg-transparent border border-transparent"
                    style={{
                      minHeight: 0,
                      maxHeight: chatMessageMaxHeight, // 根据屏幕尺寸动态设置
                      overflow: 'hidden',
                      borderRadius: 'clamp(0.375rem, 0.3rem + 0.3vw, 0.5rem)',
                    }}
                  >
                    <ChatMessageArea
                      messages={chatMessages}
                      onRetryMessage={handleRetryLastMessage}
                      onOptimizeReply={handleOptimizeAiReply}
                      onCopyMessage={copyMessageContent}
                      onEditMessage={handleEditMessage}
                      onDeleteMessage={deleteMessage}
                      onViewTrace={handleViewTrace}
                      isProcessing={isProcessing}
                      onStopStreaming={handleStopStreaming}
                      isStreamingStopped={isStreamingStopped}
                      messageFormats={messageFormats}
                      onToggleMessageFormat={toggleMessageFormat}
                      completedMessages={completedMessages}
                      expandedReasoningMessages={expandedReasoningMessages}
                      onToggleReasoningExpanded={index => {
                        const newExpanded = new Set(expandedReasoningMessages)
                        if (expandedReasoningMessages.has(index)) {
                          newExpanded.delete(index)
                        } else {
                          newExpanded.add(index)
                        }
                        setExpandedReasoningMessages(newExpanded)
                      }}
                      expandedToolCallMessages={expandedToolCallMessages}
                      onToggleToolCallExpanded={index => {
                        const newExpanded = new Set(expandedToolCallMessages)
                        if (expandedToolCallMessages.has(index)) {
                          newExpanded.delete(index)
                        } else {
                          newExpanded.add(index)
                        }
                        setExpandedToolCallMessages(newExpanded)
                      }}
                      editingMessageIndex={editingMessage}
                      editingContent={editContent}
                      onStartEdit={startEditMessage}
                      onSaveEdit={saveEditMessage}
                      onCancelEdit={cancelEditMessage}
                      onEditContentChange={setEditContent}
                      containerRef={chatContainerRef}
                      readOnly={isReadOnlyMode}
                    />
                  </div>

                  <DebugInputArea
                    inputMessage={inputMessage}
                    onInputChange={setInputMessage}
                    onSend={handleSendMessage}
                    onClear={handleClearMainChat}
                    onMultiRunClick={() => setMultiRunDialogOpen(true)}
                    isProcessing={isProcessing}
                    isReadOnlyMode={isReadOnlyMode}
                  />
                </CardContent>
              </Card>
            </div>
          )}

          {/* Column 4: 版本历史 */}
          {versionHistoryOpen && (
            <div 
              className="flex-shrink-0"
              style={{
                minWidth: 'clamp(16rem, 20vw, 26rem)',
                maxWidth: 'clamp(15rem, 24vw, 30rem)',
              }}
            >
              <VersionHistory
                isOpen={versionHistoryOpen}
                onClose={handleOpenVersionHistory}
                versions={getDisplayVersions()}
                selectedVersion={selectedVersion}
                onSelectVersion={handleSelectVersion}
                loading={versionListLoading}
                draftSavedTime={draftSavedTime}
                height={versionHistoryHeight}
                width="100%"
                onOpenAssociationsDialog={handleOpenAssociationsDialog}
                onCreateCopy={handleCreateCopy}
                onRollbackToVersion={handleRollbackToVersion}
              />
            </div>
          )}
        </div>
      )}

      {/* Submit Version Dialog */}
      <SubmitVersionDialog
        open={submitVersionDialogOpen}
        onClose={handleCloseSubmitVersionDialog}
        submitVersionStep={submitVersionStep}
        promptCommitData={promptCommitData}
        promptDraftData={promptDraftData}
        latestVersion={latestVersion}
        versionNumber={versionNumber}
        setVersionNumber={setVersionNumber}
        versionDescription={versionDescription}
        setVersionDescription={setVersionDescription}
        versionNumberError={versionNumberError}
        setVersionNumberError={setVersionNumberError}
        onNextStep={handleNextStep}
        onPrevStep={handlePrevStep}
        onConfirmSubmit={handleConfirmSubmitVersion}
      />

      {/* 工具编辑对话框 */}
      <ToolEditDialog open={toolDialogOpen} editingTool={editingTool} onClose={handleCloseToolDialog} onSave={handleSaveTool} onToolChange={setEditingTool} />

      {/* 快捷优化对话框 */}
      <QuickOptimizeDialog
        open={optimizationDialogOpen}
        onClose={() => {
          // 取消正在进行的流式请求
          if (abortControllerRef.current) {
            abortControllerRef.current.abort()
            abortControllerRef.current = null
          }

          setOptimizationDialogOpen(false)
          // 重置快捷优化相关状态
          setQuickOptimizeStreaming('')
          quickOptimizeStreamingRef.current = ''
          setOptimizationResult('')
          setShowQuickOptimizeDiff(false)
          setIsOptimizing(false)
        }}
        isOptimizing={isOptimizing}
        optimizingTarget={optimizingTarget}
        optimizationSource={optimizationSource}
        optimizationResult={optimizationResult}
        quickOptimizeStreaming={quickOptimizeStreaming}
        showDiffViewer={showQuickOptimizeDiff}
        promptMessages={promptMessages}
        baseGroupMessages={comparisonGroupsData.find(g => g.id === 0)?.messages || []}
        controlGroupsData={comparisonGroupsData}
        selectedModel={selectedModel}
        availableModels={availableModels}
        modelConfig={modelConfig}
        baseGroupModelConfig={comparisonGroupsData.find(g => g.id === 0)?.modelConfig || {}}
        onOptimizePrompt={handleOptimizePrompt}
        onApplyOptimization={handleApplyQuickOptimization}
        onStopOptimization={handleStopQuickOptimization}
        onShowSnackbar={showSnackbar}
      />

      {/* 退出对比模式确认对话框 */}
      <ExitComparisonDialog
        open={exitComparisonDialogOpen}
        comparisonGroups={comparisonGroupsData}
        onClose={() => {
          setExitComparisonDialogOpen(false)
        }}
        onExit={selectedGroupId => {
          if (selectedGroupId === 'none') {
            // 不覆盖退出
            setExitComparisonDialogOpen(false)
            setIsComparisonMode(false)
            // 清理对比组的placeholder验证错误状态
            setGroupPlaceholderValidationErrors({})
            setSnackbar({
              open: true,
              message: t('components.prompts.promptEditPage.exitComparisonModeNoChanges'),
              severity: 'info',
            })
          } else if (typeof selectedGroupId === 'number') {
            // 使用选择的组覆盖主页面（基准组id=0，对照组id>=1）
            const selectedGroup = comparisonGroupsData.find(g => g.id === selectedGroupId)
            if (selectedGroup) {
              // 应用组内容到主页面
              applyGroupContentToMain(selectedGroup, 'exit-comparison')

              // 关闭退出对比模式对话框
              setExitComparisonDialogOpen(false)
              setIsComparisonMode(false)
              // 清理对比组的placeholder验证错误状态
              setGroupPlaceholderValidationErrors({})
            }
          }
        }}
      />

      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} anchorOrigin={{ vertical: 'top', horizontal: 'center' }} />

      {/* 编辑基本信息对话框 */}
      <PromptBasicInfoDialog
        open={editInfoDialogOpen}
        onClose={() => setEditInfoDialogOpen(false)}
        onConfirm={handleSaveBasicInfo}
        title={t('components.prompts.promptBasicInfoDialog.editTitle')}
        keyEditable={false}
        buttonText={{
          loading: t('components.prompts.promptBasicInfoDialog.editButtonLoading'),
          normal: t('components.prompts.promptBasicInfoDialog.editButtonNormal'),
        }}
        defaultValues={{
          key: prompt.key,
          name: prompt.name,
          description: prompt.description,
          tags: prompt.tags,
          isPublic: prompt.isPublic,
        }}
      />

      {/* 新增变量对话框 */}
      <AddVariableDialog
        open={addVariableDialogOpen}
        templateEngine={templateEngine}
        existingVariableNames={parameters.map(p => p.name)}
        onClose={() => setAddVariableDialogOpen(false)}
        onAdd={handleAddVariableFromDialog}
      />

      {/* 组新增变量对话框（基准组id=0，对照组id>=1） */}
      <AddVariableDialog
        open={groupAddVariableDialogOpen.open}
        templateEngine={
          groupAddVariableDialogOpen.groupId
            ? comparisonGroupsData.find(g => g.id === groupAddVariableDialogOpen.groupId)?.templateEngine || 'normal'
            : templateEngine
        }
        existingVariableNames={
          groupAddVariableDialogOpen.groupId
            ? comparisonGroupsData.find(g => g.id === groupAddVariableDialogOpen.groupId)?.parameters.map(p => p.name) || []
            : []
        }
        onClose={() => setGroupAddVariableDialogOpen({ open: false })}
        onAdd={(variableData: VariableData) => {
          // 调用统一的变量添加函数，传入组ID（验证逻辑已移动到函数内部）
          handleAddVariableFromDialog(variableData, groupAddVariableDialogOpen.groupId)
        }}
      />

      {/* 编辑变量对话框（使用 AddVariableDialog 组件） */}
      <AddVariableDialog
        open={editVariableDialogOpen}
        templateEngine={templateEngine}
        existingVariableNames={parameters.map(p => p.name)}
        onClose={() => {
          setEditVariableDialogOpen(false)
          setEditingVariableIndex(null)
          setEditingVariableData(null)
        }}
        onAdd={handleEditVariableSave}
        isEditMode={true}
        editingVariable={editingVariableData}
      />

      {/* 模板引擎切换确认对话框 */}
      <TemplateEngineSwitchDialog
        open={templateEngineChangeDialogOpen}
        pendingTemplateEngine={pendingTemplateEngine}
        onClose={() => setTemplateEngineChangeDialogOpen(false)}
        onConfirm={() => {
          setTemplateEngine(pendingTemplateEngine)
          setTemplateEngineChangeDialogOpen(false)
          setHasUnsavedChanges(true)
          // 切换模板引擎后触发自动保存，传递新的templateEngine值
          triggerAutoSave({
            templateEngine: pendingTemplateEngine,
          })
        }}
      />

      {/* 对比组模板引擎切换对话框 */}
      {currentTemplateEngineChangeGroupId !== null && (
        <TemplateEngineSwitchDialog
          open={groupTemplateEngineChangeDialogOpen[currentTemplateEngineChangeGroupId] || false}
          pendingTemplateEngine={groupPendingTemplateEngine[currentTemplateEngineChangeGroupId] || 'normal'}
          onClose={() => {
            setGroupTemplateEngineChangeDialogOpen(prev => ({ ...prev, [currentTemplateEngineChangeGroupId]: false }))
            setCurrentTemplateEngineChangeGroupId(null)
          }}
          onConfirm={() => {
            const groupId = currentTemplateEngineChangeGroupId
            const newEngine = groupPendingTemplateEngine[groupId]

            // 更新对比组的模板引擎
            setComparisonGroupsData(prev => prev.map(g => (g.id === groupId ? { ...g, templateEngine: newEngine } : g)))

            // 关闭对话框
            setGroupTemplateEngineChangeDialogOpen(prev => ({ ...prev, [groupId]: false }))
            setCurrentTemplateEngineChangeGroupId(null)
            setHasUnsavedChanges(true)
          }}
        />
      )}

      {/* 反馈优化对话框 */}
      <FeedbackOptimizeDialog
        open={optimizeDialogOpen}
        currentOptimizationType={currentOptimizationType}
        selectedText={selectedText}
        cursorPosition={cursorPosition}
        optimizeInput={optimizeInput}
        optimizedResult={optimizedResult}
        isOptimizing={isOptimizing}
        onClose={closeOptimizationDialog}
        onOptimizeInputChange={setOptimizeInput}
        onOptimizeRequest={handleOptimizeRequest}
        onApplyOptimization={handleApplyOptimization}
        onStopOptimization={handleStopFeedbackOptimization}
        onCopyResult={result => copyToClipboard(result, setSnackbar, t('components.prompts.promptEditPage.optimizeResultCopied'))}
      />

      {/* 多实例运行弹出对话框 */}
      <MultiRunDialog
        open={multiRunDialogOpen}
        onClose={() => setMultiRunDialogOpen(false)}
        runCount={runCount}
        onRunCountChange={setRunCount}
        multiRunChatMessages={multiRunChatMessages}
        multiRunProcessing={multiRunProcessing}
        onSendMessage={handleMultiRunSendMessage}
        onClearAll={handleClearAllMultiRun}
        onClearInstance={handleClearMultiRunInstance}
        onRegenerateMessage={handleRegenerateMessage}
        onAdoptConversation={handleAdoptConversation}
        onViewTrace={handleViewTrace}
        onDeleteMessage={handleDeleteMultiRunMessage}
        onUpdateMessage={handleUpdateMultiRunMessage}
        onStopStreaming={handleStopMultiRunStreaming}
        prompt={prompt}
        modelConfig={modelConfig}
        parameters={parameters}
        multiRunExpandedToolCallMessages={multiRunExpandedToolCallMessages}
        onToggleMultiRunToolCallExpanded={handleToggleMultiRunToolCallExpanded}
        multiRunExpandedReasoningMessages={multiRunExpandedReasoningMessages}
        onToggleMultiRunReasoningExpanded={handleToggleMultiRunReasoningExpanded}
        readOnly={isReadOnlyMode}
      />

      {/* 还原版本确认弹窗 */}
      <RestoreVersionConfirmationDialog open={revertConfirmOpen} onClose={() => setRevertConfirmOpen(false)} onConfirm={handleConfirmRevert} />

      {/* 根据调试结果优化提示词对话框 */}
      <DebugOptimizeDialog
        open={aiReplyOptimizeDialogOpen}
        onClose={handleDebugOptimizeClose}
        selectedAiReply={selectedAiReply}
        optimizeStep={aiReplyOptimizeStep}
        optimizedPromptTemplate={optimizedPromptTemplate}
        humanEvaluation={humanEvaluation}
        optimizationSource={optimizationSource}
        promptMessages={promptMessages}
        baseGroupMessages={comparisonGroupsData.find(g => g.id === 0)?.messages || []}
        controlGroupsData={comparisonGroupsData}
        onStepChange={handleDebugOptimizeStepChange}
        onOptimizedTemplateChange={handleDebugOptimizedTemplateChange}
        onHumanEvaluationChange={handleDebugHumanEvaluationChange}
        onAdoptOptimizedPrompt={handleAdoptOptimizedPrompt}
        onStartOptimization={handleStartAiReplyOptimization}
        onRetryOptimization={handleRetryAiReplyOptimization}
        onStopOptimization={handleStopDebugOptimization}
      />

      {/* 创建副本对话框 */}
      <PromptBasicInfoDialog
        open={createCopyDialogOpen}
        onClose={() => {
          setCreateCopyDialogOpen(false)
          setCopyPromptData(null)
        }}
        onConfirm={handleConfirmCreateCopy}
        title={t('components.prompts.promptBasicInfoDialog.createCopyTitle')}
        keyEditable={true}
        buttonText={{
          loading: t('components.prompts.promptBasicInfoDialog.createCopyButtonLoading'),
          normal: t('components.prompts.promptBasicInfoDialog.createCopyButtonNormal'),
        }}
        defaultValues={
          copyPromptData
            ? {
                key: copyPromptData.key,
                name: copyPromptData.name,
                description: copyPromptData.description,
                tags: copyPromptData.tags,
                isPublic: copyPromptData.isPublic,
              }
            : undefined
        }
      />

      {/* 关联对象列表对话框 */}
      <AssociationsDialog
        open={associationsDialogOpen}
        onClose={handleCloseAssociationsDialog}
        associations={selectedAssociations}
        versionName={selectedVersionName}
        workspaceId={workspaceId}
      />
    </div>
  )
}

export default PromptEditPage
