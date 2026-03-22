import { DeepSearchConfig } from '../components/AgentConfigDialog'

/**
 * DeepSearch Agent 默认配置
 * 当用户没有在 localStorage 中保存配置时使用
 */
export const DEFAULT_DEEPSEARCH_CONFIG: DeepSearchConfig = {
  enableHumanInteraction: true,
  outlineInteractionEnabled: true, // 大纲交互开关，默认开启
  planChapterCount: 5,
  enableTraceability: true,
  enableSourceTracerInfer: true, // 溯源推理功能开关，默认开启
  searchMode: 'web',
  selectedWebSearchEngineId: undefined,
  webSearchResultCount: 5,
  localSearchResultCount: 5,
  selectedKnowledgeBaseIds: [], // 本地知识库ID列表
  recallThreshold: 0.5, // 最小匹配分数，默认 0.5
  enableTemplate: false,
  selectedTemplateId: undefined,
  // 模型配置（undefined 表示未配置）
  generalModelId: undefined,
  planUnderstandingModelId: undefined,
  infoCollectingModelId: undefined,
  writingCheckingModelId: undefined,
}
