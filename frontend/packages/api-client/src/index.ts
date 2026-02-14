// 导出所有服务和 hooks

// 核心客户端
export { apiClient, apiRequest, apiUtils, createApiClientInstance, ApiError, startTokenRenewal, stopTokenRenewal } from './client'
export type { TokenProvider, AuthStateUpdater } from './client'

// 上下文和Provider
export { ApiClientProvider, useApiClient, useToken } from './context/ApiClientProvider'

// 工具函数
export {
  getApiClient,
  getToken,
  setGlobalTokenProvider,
  isApiClientInitialized,
  waitForApiClientInitialization,
  stream,
} from './utils/apiClientFactory'
export type { StreamOptions } from './utils/apiClientFactory'
export { isApiError, getErrorMessage, getErrorResponse } from './utils/errorHandling'
export type { ApiError } from './utils/errorHandling'

// 配置
export { API_CONFIG, API_ENDPOINTS, HTTP_STATUS, ERROR_TYPES, updateApiConfig, setApiBaseUrl } from './config'

// 类型定义
export * from './types'
export { ModelProvider } from './types/modelTypes'

// Embedding 模型相关类型
export { EmbeddingProtocol } from './types/embeddingModelTypes'
export type {
  EmbeddingModelConfigBase,
  EmbeddingModelConfigCreate,
  EmbeddingModelConfigUpdate,
  EmbeddingModelConfigResponse,
  EmbeddingModelConfigList,
  EmbeddingModelConfigRequest,
  EmbeddingModelTestRequest,
  EmbeddingModelTestResponse,
  EmbeddingModelConfigQueryParams,
  EmbeddingModelApiResponse,
  EmbeddingModelApiError,
} from './types/embeddingModelTypes'
export type {
  ModelParameters as ModelConfigParameters,
  ModelUsageStats,
  ModelConfigBase,
  ModelConfigCreate,
  ModelConfigUpdate,
  ModelConfigResponse,
  ModelConfigList,
  ModelTestRequest,
  ModelTestResponse,
  ModelConfigFilter,
  ModelConfigQueryParams,
  ModelApiResponse,
  ModelApiError,
  ValidationError as ModelValidationError,
} from './types/modelTypes'

// 自优化相关类型
export type {
  OptimizationMessage,
  OptimizationCase,
  OptimizeInfo,
  ModelInfo,
  CreateOptimizationJobRequest,
  SaveJobDraftRequest,
  JobDraftContent,
  JobInfo,
  CreateOptimizationJobResponse,
  SaveJobDraftResponse,
  GetJobDraftResponse,
  JobDetail,
  GetJobListRequest,
  GetJobListResponse,
  DeleteJobResponse,
  CaseCheckRequest,
  CaseCheckResponse,
  OptimizationHistory,
  OptimizationProgress,
  OptimizeInfoDetail,
  GetJobDetailResponse,
  SelfOptApiResponse,
  SelfOptApiError,
  CaseInputs,
  CaseLabel,
  CaseDetail,
  CaseAnswer,
  EvaluateCase,
  JobHistoryItem,
  GetJobHistoryResponse,
} from './types/selfOptTypes'

// 反馈优化相关类型
export type {
  ModelInfo as FeedbackModelInfo,
  AgentModelInfo,
  QuickOptimizeModelInfo,
  QuickOptimizeRequest,
  OptimizeResponse,
  OptimizationMode,
  OptimizeFeedbackRequest,
  Badcase,
  OptimizeBadcaseRequest,
  StreamDataCallback,
  StreamErrorCallback,
  StreamCompleteCallback,
  FeedbackOptApiResponse,
  FeedbackOptApiError,
} from './types/feedbackOptTypes'

// 提示词模型相关类型
export type {
  ParamSchema,
  ParamConfig,
  OpenModel,
  ModelSeries,
  Model as PromptModel,
  GetModelsListRequest,
  GetModelsListResponse,
  GetModelDetailResponse,
  GetModelsListParams,
  PromptModelApiResponse,
  PromptModelApiError,
} from './types/promptModelTypes'

// 提示词相关类型
export type {
  PromptBasic,
  RelationObj,
  ApiPrompt,
  ApiUser,
  Prompt,
  CreatePromptRequest,
  CreatePromptResponse,
  UpdatePromptRequest,
  EditPromptBasicInfoRequest,
  EditPromptBasicInfoResponse,
  DeletePromptRequest,
  DeletePromptResponse,
  ApiPromptListResponse,
  PromptListResponse,
  PromptMessage,
  VariableDef,
  PromptTemplate,
  ToolFunction,
  Tool,
  ToolCallConfig,
  PromptModelConfig,
  PromptDetail,
  DraftInfo,
  CommitInfo,
  PromptDraft,
  PromptCommit,
  ApiPromptDetail,
  GetPromptDetailResponse,
  GetPromptDetailRequest,
  DraftMessage,
  DraftVariableDef,
  DraftModelConfig,
  DraftToolCallConfig,
  DraftTool,
  DraftDetail,
  SaveDraftRequest,
  SaveDraftResponse,
  CommitVersionRequest,
  CommitVersionResponse,
  RevertToVersionRequest,
  RevertToVersionResponse,
  PromptCommitInfo,
  GetVersionListRequest,
  GetVersionListResponse,
  DebugMessage,
  DebugVariableVal,
  DebugMockTool,
  DebugStreamingRequest,
  DebugStreamingResponse,
  SaveDebugContextRequest,
  SaveDebugContextResponse,
  MockContext,
  MockVariable,
  MockTool,
  DebugCore,
  DebugConfig,
  DebugContext,
  GetDebugContextResponse,
  GetMockContext,
  DebugHistoryListRequest,
  DebugHistoryListResponse,
  DebugHistoryItem,
  ClonePromptRequest,
  ClonePromptResponse,
  PromptApiResponse,
  PromptApiError,
} from './types/promptTypes'

// Trace相关类型
export type {
  OrderBy,
  TraceListRequest,
  TraceListResponse,
  TraceSpan,
  TraceRecord,
  TraceFilterParams,
  TraceApiError,
  TimeRangeOption,
  SpanTypeOption,
  DataSourceOption,
  TraceTreeRequest,
  TraceTreeResponse,
  TraceTreeSpan,
  TraceTreeNode,
  TraceAdvanceInfo,
} from './types/traceTypes'

// 服务
export { WorkflowService } from './services/workflowService'
export { ExecutionService } from './services/executionService'
export { ModelService, modelService } from './services/modelService'
export { EmbeddingModelService, embeddingModelService } from './services/embeddingModelService'
export type { FrontendEmbeddingModelConfig } from './services/embeddingModelService'
export { AuthService } from './services/authService'
export { SpaceService } from './services/spaceService'
export { AgentService } from './services/agentService'
export { RelatedMemberService } from './services/relatedMemberService'
export { SelfOptService } from './services/selfOptService'
export { FeedbackOptService } from './services/feedbackOptService'
export { PromptModelService } from './services/promptModelService'
export { PromptService } from './services/promptService'
export { PluginService } from './services/pluginService'
export { TagService } from './services/tagService'
export { TraceService, traceService } from './services/traceService'
export { KnowledgeBaseService } from './services/knowledgeBaseService'
export { MemoryBaseService } from './services/memoryBaseService'
export { deepsearchTemplateService, deepsearchHeartbeatService, fileToBase64 } from './services/deepsearchTemplateService'
export { webSearchEngineService } from './services/webSearchEngineService'
export type { FrontendModelConfig } from './services/modelService'
export type { Space, SpaceResponse } from './services/spaceService'
export { MemberType } from './services/relatedMemberService'
export type { RelatedMemberInfo } from './services/relatedMemberService'
export type {
  ReportTemplate,
  TemplateImportRequest,
  TemplateImportResponse,
  TemplateListResponse,
  TemplateDeleteResponse,
  TemplateContentResponse,
  HeartbeatResponse
} from './services/deepsearchTemplateService'
export type {
  WebSearchEngineConfig,
  WebSearchEngineCreateRequest,
  WebSearchEngineCreateResponse,
  WebSearchEngineListResponse,
  WebSearchEngineDeleteResponse,
  WebSearchEngineUpdateRequest,
  WebSearchEngineUpdateResponse,
  WebSearchEngineDetailResponse,
  WebSearchEngineTestRequest,
  WebSearchEngineTestResponse
} from './services/webSearchEngineService'

// Hooks
export * from './hooks/useWorkflow'
export * from './hooks/useExecution'
export * from './hooks/useExecutionLogs'
export type {
  WorkflowExecutionRequest,
  WorkflowCancelRequest,
  WorkflowCancelResponse,
  WorkflowExecutionEvent,
  WorkflowExecutionResult,
  WorkflowExecutionStatus,
  WorkflowExecutionEventHandler,
  NodeExecutionStatus,
  SSEMessage,
} from './types'
export * from './hooks/useModels'
export * from './hooks/useEmbeddingModels'
export * from './hooks/useAuth'
export * from './hooks/useSpace'
export * from './hooks/useAgent'
export * from './hooks/usePrompt'
export * from './hooks/useRelatedMember'
export * from './hooks/useSelfOpt'
export * from './hooks/useFeedbackOpt'
export * from './hooks/usePromptModel'
export * from './hooks/usePrompt'
export * from './hooks/usePlugin'
export * from './hooks/useTags'
export * from './hooks/useTrace'

// Export delete workflow types
export type { DeleteWorkflowRequest, DeleteWorkflowResponse } from './types'

// Tag相关类型导出
export type {
  Tag,
  TagCreate,
  TagUpdate,
  TagResponse,
  TagListResponse,
  TagGetOrCreateResponse,
  TagBatchCreateResponse,
  TagCreateRequest,
  TagUpdateRequest,
  TagGetOrCreateRequest,
  TagBatchCreateRequest,
  TagSearchRequest,
  TagListRequest,
  TagApiResponse,
  TagApiError,
  TagQueryParams,
  TagSearchQueryParams,
  WorkflowTagRelation,
  WorkflowTagRequest,
  WorkflowTagResponse,
  CreateWorkflowWithTagsRequest,
  UpdateWorkflowWithTagsRequest,
} from './types/tagTypes'

// 知识库相关类型
export type {
  CreateKnowledgeBaseRequest,
  CreateKnowledgeBaseResponse,
  GetKnowledgeBasesRequest,
  GetKnowledgeBasesResponse,
  KnowledgeBaseItem,
  KnowledgeBase,
  UpdateKnowledgeBaseRequest,
  UpdateKnowledgeBaseResponse,
  DeleteKnowledgeBaseRequest,
  DeleteKnowledgeBaseResponse,
  GetKnowledgeBaseDetailRequest,
  GetKnowledgeBaseDetailResponse,
  UploadFilesRequest,
  UploadFilesResponse,
  FileSettingsRequest,
  FileSettingsResponse,
  GetDocumentsListRequest,
  GetDocumentsListResponse,
  UpdateDocumentRequest,
  UpdateDocumentResponse,
  DeleteDocumentsRequest,
  DeleteDocumentsResponse,
  ProcessDocumentsRequest,
  ProcessDocumentsResponse,
  GetDocumentStatusRequest,
  GetDocumentStatusResponse,
  DocumentStatusItem,
  DocumentItem,
  SearchKnowledgeBaseRequest,
  SearchKnowledgeBaseResponse,
  SearchKnowledgeBaseItem,
} from './types/knowledgeBase'

export type {
  CreateMemoryBaseRequest,
  CreateMemoryBaseResponse,
  GetMemoryBasesRequest,
  GetMemoryBasesResponse,
  MemoryBaseItem,
  MemoryBase,
  UpdateMemoryBaseRequest,
  UpdateMemoryBaseResponse,
  DeleteMemoryBaseRequest,
  DeleteMemoryBaseResponse,
  GetMemoryBaseDetailRequest,
  GetMemoryBaseDetailResponse,
  SearchMemoryBaseRequest,
  SearchMemoryBaseResponse,
  SearchMemoryBaseItem,
} from './types/memoryBase'
