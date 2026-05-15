import type { DeepSearchConfig as DeepResearchConfig } from '../components/AgentConfigDialog'

/**
 * DeepSearch 配置模式
 */
export type DeepSearchConfigMode = 'research' | 'search'

export interface DeepSearchExplorerConfig {
  enableQuestionRouter: boolean
  actionsExploredLimit: number
  timeLimit: number
  searchMode: 'local' | 'web'
  selectedKnowledgeBaseIds: string[]
  planningModelId?: string
  searchModelId?: string
  generalModelId?: string
  onlineSearchProvider?: 'jina' | 'serper'
  jinaApiKey?: string
  serperApiKey?: string
}

export type AppAgentConfig = DeepResearchConfig | DeepSearchExplorerConfig

/**
 * DeepResearch Agent 默认配置
 * 当用户没有在 localStorage 中保存配置时使用
 */
export const DEFAULT_DEEPRESEARCH_CONFIG: DeepResearchConfig = {
  enableHumanInteraction: true,
  outlineInteractionEnabled: true,
  planChapterCount: 5,
  enableTraceability: true,
  enableSourceTracerInfer: true,
  userFeedbackProcessorEnable: true,
  userFeedbackProcessorMaxInteractions: 3,
  vlmChartGeneratorEnable: false,
  vlmChartGeneratorMaxIterations: 1,
  searchMode: 'web',
  selectedWebSearchEngineId: undefined,
  webSearchResultCount: 5,
  localSearchResultCount: 5,
  webSearchMaxQps: 0,
  selectedKnowledgeBaseIds: [],
  recallThreshold: 0.5,
  enableTemplate: false,
  selectedTemplateId: undefined,
  execution_method: 'parallel',
  generalModelId: undefined,
  planUnderstandingModelId: undefined,
  infoCollectingModelId: undefined,
  writingCheckingModelId: undefined,
  vlmChartModelId: undefined,
}

/**
 * DeepSearch Explorer Agent 默认配置
 */
export const DEFAULT_DEEPSEARCH_EXPLORER_CONFIG: DeepSearchExplorerConfig = {
  enableQuestionRouter: false,
  actionsExploredLimit: 200,
  timeLimit: 3600,
  searchMode: 'web',
  selectedKnowledgeBaseIds: [],
  planningModelId: undefined,
  searchModelId: undefined,
  generalModelId: undefined,
  onlineSearchProvider: 'jina',
  jinaApiKey: '',
  serperApiKey: '',
}

/**
 * 兼容旧引用：DEFAULT_DEEPSEARCH_CONFIG 指向 DeepResearch 默认配置
 */
export const DEFAULT_DEEPSEARCH_CONFIG = DEFAULT_DEEPRESEARCH_CONFIG

export const getConfigModeFromAgentId = (agentId?: string | null): DeepSearchConfigMode => (
  agentId === 'deepsearch-explorer' ? 'search' : 'research'
)

export const getDefaultDeepSearchConfigByMode = (
  mode: DeepSearchConfigMode
): AppAgentConfig => (
  mode === 'search'
    ? { ...DEFAULT_DEEPSEARCH_EXPLORER_CONFIG }
    : { ...DEFAULT_DEEPRESEARCH_CONFIG }
)

export const getDefaultDeepSearchConfigByAgentId = (
  agentId?: string | null
): AppAgentConfig => getDefaultDeepSearchConfigByMode(getConfigModeFromAgentId(agentId))

const asStringArray = (value: unknown): string[] => (
  Array.isArray(value)
    ? value
      .filter((item): item is string => typeof item === 'string')
      .map(item => item.trim())
      .filter(item => item.length > 0)
    : []
)

const normalizeResearchSearchMode = (value: unknown): DeepResearchConfig['searchMode'] => (
  value === 'web' || value === 'local' || value === 'all'
    ? value
    : DEFAULT_DEEPRESEARCH_CONFIG.searchMode
)

const normalizeExplorerSearchMode = (value: unknown): DeepSearchExplorerConfig['searchMode'] => (
  value === 'web' || value === 'local'
    ? value
    : DEFAULT_DEEPSEARCH_EXPLORER_CONFIG.searchMode
)

const normalizeExplorerOnlineProvider = (
  value: unknown
): DeepSearchExplorerConfig['onlineSearchProvider'] => (
  value === 'jina' || value === 'serper'
    ? value
    : DEFAULT_DEEPSEARCH_EXPLORER_CONFIG.onlineSearchProvider
)

const normalizeExecutionMethod = (value: unknown): DeepResearchConfig['execution_method'] => (
  value === 'parallel' || value === 'dependency_driving'
    ? value
    : DEFAULT_DEEPRESEARCH_CONFIG.execution_method
)

export const toDeepResearchConfig = (config?: AppAgentConfig): DeepResearchConfig => {
  const merged = {
    ...DEFAULT_DEEPRESEARCH_CONFIG,
    ...(config as Partial<DeepResearchConfig> | undefined),
  }

  return {
    ...merged,
    searchMode: normalizeResearchSearchMode(merged.searchMode),
    selectedKnowledgeBaseIds: asStringArray(merged.selectedKnowledgeBaseIds),
    execution_method: normalizeExecutionMethod(merged.execution_method),
  }
}

export const toDeepSearchExplorerConfig = (
  config?: AppAgentConfig
): DeepSearchExplorerConfig => {
  const merged = {
    ...DEFAULT_DEEPSEARCH_EXPLORER_CONFIG,
    ...(config as Partial<DeepSearchExplorerConfig> | undefined),
  }

  return {
    ...merged,
    searchMode: normalizeExplorerSearchMode(merged.searchMode),
    selectedKnowledgeBaseIds: asStringArray(merged.selectedKnowledgeBaseIds),
    onlineSearchProvider: normalizeExplorerOnlineProvider(merged.onlineSearchProvider),
  }
}
