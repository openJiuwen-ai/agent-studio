import { DeepSearchConfig } from '../components/AgentConfigDialog'

/**
 * DeepSearch 配置模式
 */
export type DeepSearchConfigMode = 'research' | 'search'

/**
 * DeepResearch Agent 默认配置
 * 当用户没有在 localStorage 中保存配置时使用
 */
export const DEFAULT_DEEPRESEARCH_CONFIG: DeepSearchConfig = {
  enableHumanInteraction: true,
  outlineInteractionEnabled: true, // 大纲交互开关，默认开启
  planChapterCount: 5,
  enableTraceability: true,
  enableSourceTracerInfer: true, // 溯源推理功能开关，默认开启
  userFeedbackProcessorEnable: true, // 报告改写功能开关，默认开启
  userFeedbackProcessorMaxInteractions: 3, // 用户反馈优化最大交互次数，默认 3
  vlmChartGeneratorEnable: false,
  vlmChartGeneratorMaxIterations: 1,
  searchMode: 'web',
  selectedWebSearchEngineId: undefined,
  webSearchResultCount: 5,
  localSearchResultCount: 5,
  webSearchMaxQps: 0, // 联网搜索最大 QPS，0 表示不限流
  selectedKnowledgeBaseIds: [], // 本地知识库ID列表
  recallThreshold: 0.5, // 最小匹配分数，默认 0.5
  enableTemplate: false,
  selectedTemplateId: undefined,
  execution_method: "parallel",   // "parallel", "dependency_driving", 默认平行模式
  // 模型配置（undefined 表示未配置）
  generalModelId: undefined,
  planUnderstandingModelId: undefined,
  infoCollectingModelId: undefined,
  writingCheckingModelId: undefined,
  vlmChartModelId: undefined,
}

/**
 * DeepSearch Explorer Agent 默认配置
 */
export const DEFAULT_DEEPSEARCH_EXPLORER_CONFIG: DeepSearchConfig = {
  enableHumanInteraction: false,
  outlineInteractionEnabled: false,
  planChapterCount: 1,
  enableTraceability: false,
  enableSourceTracerInfer: false,
  userFeedbackProcessorEnable: false,
  userFeedbackProcessorMaxInteractions: 0,
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
  actionProposalsLimit: 5,
  timeLimit: 3600,
  actionsExploredLimit: 200,
  maxLlmCallsPerRun: 10,
  enableQuestionRouter: false,
  // Model config (platform model picker IDs)
  planningModelId: undefined,
  searchModelId: undefined,
  // Milvus / local KB
  milvusHost: '169.254.171.63',
  milvusPort: 19530,
  milvusDatabaseName: 'deepsearch_benchmarks',
  milvusCollectionName: 'browsecompplus_with_bm25_test_2',
  embedderModelName: 'qwen/qwen3-embedding-8b',
  embedderApiKey: '',
  embedderBaseUrl: 'https://openrouter.ai/api/v1/embeddings',
  // Online search provider
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

export const getDefaultDeepSearchConfigByMode = (mode: DeepSearchConfigMode): DeepSearchConfig => (
  mode === 'search'
    ? { ...DEFAULT_DEEPSEARCH_EXPLORER_CONFIG }
    : { ...DEFAULT_DEEPRESEARCH_CONFIG }
)

export const getDefaultDeepSearchConfigByAgentId = (agentId?: string | null): DeepSearchConfig => (
  getDefaultDeepSearchConfigByMode(getConfigModeFromAgentId(agentId))
)
