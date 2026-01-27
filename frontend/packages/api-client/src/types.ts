// API相关类型定义

// 基础响应类型
export interface ApiResponse<T = unknown> {
  success?: boolean
  data?: T
  message?: string
  error?: string
  code?: string | number
  timestamp?: string
  requestId?: string
}

// 通用响应类型 - 兼容不同的后端格式
export interface GenericApiResponse<T = unknown> {
  success?: boolean
  data?: T
  message?: string
  error?: string
  code?: string | number
  msg?: string
  timestamp?: string
  requestId?: string
}

// 分页请求参数
export interface PaginationParams {
  page?: number
  pageSize?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

// 分页响应数据
export interface PaginatedResponse<T> {
  items: T[]
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages: number
    hasNext: boolean
    hasPrev: boolean
  }
}

// 删除智能体请求类型
export interface DeleteAgentRequest {
  space_id: string
  agent_id: string
}

// 删除智能体响应类型
export interface DeleteAgentResponse {
  data: Record<string, never>
  code: number
  message: string
}

// 智能体保存请求类型
export interface SaveAgentRequest {
  agent_id: string
  agent_version?: string
  name: string
  space_id: string
  description: string
  agent_type: string
  configs: Record<string, unknown>
  icon: string
  edit_mode: string
  plugins: AgentPlugin[]
  workflows: Array<{
    workflow_id: string
    workflow_version: string
    workflow_name: string
    description: string
  }>
  model: {
    model_provider: string
    model_info: {
      model_id?: number
      api_key: string
      api_base: string
      model_name: string
      temperature: number
      top_p: number
      streaming: boolean
      max_tokens: number
      timeout: number
      model_type: string
    }
  }
  prompt_template_name: string
  prompt_template: Array<{
    role: string
    content: string
  }>
  constraint: {
    reserved_max_chat_rounds: number
    max_iteration: number
  }
  auto_generated_prompt: string
  prompt_tuning: {
    input_mode: string
    examples: string
    use_cases: Array<{
      id: number
      name: string
      data: Array<{
        user: string
        assistant: string
      }>
      upload_time: string
    }>
    optimization_model: string
    evaluation_model: string
    optimization_rounds: number
  }
  triggers: string[]
  knowledge: string[]
  memory: {
    max_tokens: number
    longterm_memory_config?: boolean
    variable_config?: Array<{
      id: string
      name: string
      description?: string // 可选
      enabled?: boolean // 是否启用，默认 true
    }>
  }
  opening_remarks: string
  default_response?: string
}

// 智能体保存响应类型
export interface SaveAgentResponse {
  code: number
  message: string
}

// 列表查询参数
export interface ListQueryParams extends PaginationParams {
  search?: string
  filters?: Record<string, unknown>
  include?: string[]
  exclude?: string[]
}

// 列表响应
export interface ListResponse<T> extends ApiResponse<PaginatedResponse<T>> {}

// 详情响应
export interface DetailResponse<T> extends ApiResponse<T> {}

// 创建响应
export interface CreateResponse<T> extends ApiResponse<T> {}

// 更新响应
export interface UpdateResponse<T> extends ApiResponse<T> {}

// 删除响应
export interface DeleteResponse extends ApiResponse<{ deleted: boolean }> {}

// 执行响应
export interface ExecuteResponse<T = unknown> extends ApiResponse<T> {}

// 错误响应
export interface ErrorResponse extends ApiResponse<null> {
  code: number
  error: string
  details?: Record<string, unknown>
  validationErrors?: ValidationError[]
}

// 验证错误
export interface ValidationError {
  field: string
  message: string
  code: string
  value?: unknown
}

// 认证相关类型
export interface LoginRequest {
  username: string
  password: string
  grant_type: string
  rememberMe?: boolean
}

// 用户信息接口
export interface UserInfo {
  user_id_str: string
  username: string
  user_unique_name: string
  avatar_url: string | null
  role_type: number
  email: string
  locale: string
  description: string
  user_create_time: number
  user_update_time: number
  is_active: boolean
  screen_name: string
  app_user_info: unknown | null
  space_id: string
}

// 包含标签信息的用户信息接口
export interface UserInfoWithTag extends UserInfo {
  first_name?: string
  last_name?: string
  phone_number?: string
  compunknown?: string
  occupation?: string
  skills?: string[]
}

// 登录响应数据接口
interface LoginData {
  access_token: string
  token_type: string
  user: UserInfo
}

// 登录响应接口
export interface LoginResponse {
  data: LoginData
  code: number
  message: string
}

export interface RefreshTokenRequest {
  refreshToken: string
}

export interface RefreshTokenResponse extends ApiResponse<{
  token: string
  expiresAt: string
}> {}

export interface ChangePasswordRequest {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

// 用户相关类型
export interface User {
  id: string
  username: string
  email: string
  firstName?: string
  lastName?: string
  avatar?: string
  role: UserRole
  permissions: string[]
  status: UserStatus
  lastLoginAt?: string
  createdAt: string
  updatedAt: string
}

export type UserRole = 'admin' | 'user' | 'developer' | 'viewer'
export type UserStatus = 'active' | 'inactive' | 'suspended' | 'pending'

export interface CreateUserRequest {
  username: string
  email: string
  password: string
  firstName?: string
  lastName?: string
  role: UserRole
  permissions?: string[]
}

export interface UpdateUserRequest {
  username?: string
  email?: string
  firstName?: string
  lastName?: string
  role?: UserRole
  permissions?: string[]
  status?: UserStatus
}

// 工作流相关类型
export interface Workflow {
  id: string
  name: string
  description: string
  status: WorkflowStatus
  trigger: WorkflowTrigger
  lastRunAt?: string
  nextRunAt?: string
  successRate: number
  averageExecutionTime: number
  nodeCount: number
  tags: string[]
  isActive: boolean
  createdBy: string
  createdAt: string
  updatedAt: string
  workflowData?: unknown
  version?: string
}

export type WorkflowStatus = 'running' | 'stopped' | 'scheduled' | 'error' | 'completed' | 'paused'
export type WorkflowTrigger = 'manual' | 'webhook' | 'schedule' | 'event' | 'api'

// 工作流列表请求类型
export interface WorkflowListRequest {
  space_id: string
  page?: number
  page_size?: number
}

// 工作流创建请求类型 (已移动到API类型部分)

export interface UpdateWorkflowRequest {
  workflow_id: string
  space_id: string
  name?: string
  desc?: string
  url?: string
  icon_uri?: string
  tags?: string[]
}

export interface WorkflowUpdateResponse {
  code: number
  message: string
  data: {
    workflow_id: string
    success: boolean
  }
}

export interface ExecuteWorkflowRequest {
  input?: Record<string, unknown>
  parameters?: Record<string, unknown>
  timeout?: number
}

export interface WorkflowExecution {
  id: string
  workflowId: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  input?: Record<string, unknown>
  output?: Record<string, unknown>
  error?: string
  startedAt?: string
  completedAt?: string
  executionTime?: number
  logs?: WorkflowLog[]
}

export interface WorkflowLog {
  id: string
  executionId: string
  level: 'debug' | 'info' | 'warning' | 'error'
  message: string
  timestamp: string
  nodeId?: string
  metadata?: Record<string, unknown>
}

// 代理相关类型
export interface Agent {
  id: string
  name: string
  description: string
  type: AgentType
  model: string
  status: AgentStatus
  capabilities: string[]
  configuration: Record<string, unknown>
  performance: AgentPerformance
  createdBy: string
  createdAt: string
  updatedAt: string
}

export type AgentType = 'conversational' | 'task' | 'analytical' | 'creative' | 'custom'
export type AgentStatus = 'draft' | 'active' | 'inactive' | 'training' | 'deployed'

export interface AgentPerformance {
  totalExecutions: number
  successRate: number
  averageResponseTime: number
  lastExecutedAt?: string
}

// 模型相关类型
export interface Model {
  id: string
  name: string
  description: string
  type: ModelType
  provider: string
  version: string
  status: ModelStatus
  capabilities: string[]
  parameters: ModelParameters
  performance: ModelPerformance
  cost: ModelCost
  createdBy: string
  createdAt: string
  updatedAt: string
}

export type ModelType = 'llm' | 'embedding' | 'vision' | 'audio' | 'multimodal'
export type ModelStatus = 'available' | 'maintenance' | 'deprecated' | 'custom'

export interface ModelParameters {
  contextLength: number
  maxTokens: number
  temperature: number
  topP: number
  frequencyPenalty: number
  presencePenalty: number
}

export interface ModelPerformance {
  accuracy: number
  latency: number
  throughput: number
  lastTestedAt?: string
}

export interface ModelCost {
  inputTokens: number
  outputTokens: number
  currency: string
}

export interface CreateModelRequest {
  name: string
  description: string
  type: ModelType
  provider: string
  version: string
  capabilities: string[]
  parameters: ModelParameters
  cost: ModelCost
}

export interface UpdateModelRequest {
  name?: string
  description?: string
  capabilities?: string[]
  parameters?: Partial<ModelParameters>
  cost?: Partial<ModelCost>
  status?: ModelStatus
}

// 提示词相关类型

export type PromptType = 'instruction' | 'conversation' | 'completion' | 'question' | 'template'

export interface PromptVariable {
  name: string
  description: string
  type: 'string' | 'number' | 'boolean' | 'array' | 'object'
  required: boolean
  defaultValue?: unknown
  validation?: string
}

export interface PromptExample {
  input: Record<string, unknown>
  output: string
  description?: string
}

export interface CreatePromptRequest {
  name: string
  description: string
  content?: string
  type: PromptType
  category?: string
  tags?: string[]
  variables?: PromptVariable[]
  examples?: PromptExample[]
  isTemplate?: boolean
}

export interface UpdatePromptRequest {
  name?: string
  description?: string
  content?: string
  type?: PromptType
  category?: string
  tags?: string[]
  variables?: PromptVariable[]
  examples?: PromptExample[]
  isTemplate?: boolean
}

// 分析统计相关类型
export interface AnalyticsOverview {
  totalWorkflows: number
  totalAgents: number
  totalUsers: number
  activeWorkflows: number
  totalExecutions: number
  successRate: number
  averageExecutionTime: number
  systemHealth: SystemHealth
  recentActivity: RecentActivity[]
}

export interface SystemHealth {
  status: 'healthy' | 'warning' | 'critical'
  cpuUsage: number
  memoryUsage: number
  diskUsage: number
  networkLatency: number
  lastUpdated: string
}

export interface RecentActivity {
  id: string
  type: 'workflow_execution' | 'user_login' | 'system_event' | 'error'
  description: string
  timestamp: string
  severity: 'info' | 'warning' | 'error'
  metadata?: Record<string, unknown>
}

// 通用查询参数
export interface DateRangeParams {
  startDate?: string
  endDate?: string
  timezone?: string
}

export interface SearchParams {
  query: string
  fields?: string[]
  fuzzy?: boolean
  highlight?: boolean
}

// 文件相关类型
export interface FileMetadata {
  id: string
  filename: string
  originalName: string
  size: number
  mimeType: string
  url: string
  uploadedBy: string
  uploadedAt: string
  tags?: string[]
  metadata?: Record<string, unknown>
}

// 通知相关类型
export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  severity: 'info' | 'warning' | 'error' | 'success'
  isRead: boolean
  createdAt: string
  metadata?: Record<string, unknown>
}

export type NotificationType = 'system' | 'workflow' | 'user' | 'security' | 'performance'

// 工作流列表响应类型
export interface WorkflowListResponse {
  code: number
  msg: string
  data: {
    workflow_list: WorkflowItem[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}

// API工作流创建请求类型
export interface CreateWorkflowRequest {
  name: string
  desc: string
  space_id: string
  url: string
  icon_uri: string
  tags: string[]
}

// API工作流创建响应类型
export interface CreateWorkflowResponse {
  code: number
  message: string
  data: {
    workflow: {
      workflow_id: string
      name: string
      desc: string
      create_time: number
      update_time: number
      space_id: string
    }
  }
}

// 工作流画布请求类型
export interface WorkflowCanvasRequest {
  workflow_id: string
  space_id: string
  version?: string
}

// 工作流画布响应类型
export interface WorkflowCanvasResponse {
  code: number
  msg: string
  data: {
    workflow: {
      workflow_id: string
      name: string
      desc: string
      create_time: number
      update_time: number
      space_id: string
      schema: string
    }
  }
}

// 工作流保存请求类型
export interface WorkflowSaveRequest {
  workflow_id: string
  workflow_version: string
  space_id: string
  schema: string
}

// 工作流保存响应类型
export interface WorkflowSaveResponse {
  code: number
  msg: string
  data: Record<string, never>
}

// 工作流删除请求类型
export interface DeleteWorkflowRequest {
  workflow_id: string
  space_id: string
  workflow_version: string
}

// 工作流删除响应类型
export interface DeleteWorkflowResponse {
  code: number
  message: string
  data: unknown
}

// 工作流复制请求类型
export interface CopyWorkflowRequest {
  workflow_id: string
  space_id: string
  version?: string
}

// 工作流复制响应类型
export interface CopyWorkflowResponse {
  code: number
  message: string
  data: {
    workflow: {
      workflow_id: string
    }
  }
}

// 工作流搜索请求类型
export enum WorkflowSortBy {
  name = 'name',
  create_time = 'create_time',
  update_time = 'update_time',
}

export enum WorkflowSortOrder {
  asc = 'asc',
  desc = 'desc',
}

export interface WorkflowSearchRequest {
  space_id: string
  search_term?: string
  tags?: string[]
  status_filter?: string
  sort_by?: WorkflowSortBy
  sort_order?: WorkflowSortOrder
  page?: number
  page_size?: number
}

// 工作流基础类型 - 与后端 WorkflowResponse 对应
export interface WorkflowItem {
  workflow_id: string
  name: string
  desc: string
  url: string
  icon_uri: string
  create_time: number
  update_time: number
  space_id: string
  tags: Array<Record<string, unknown>>
}

// 工作流搜索响应类型
export interface WorkflowSearchResponse {
  code: number
  message: string
  data: {
    workflow_list: WorkflowItem[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}

// 工作流执行请求类型
export interface WorkflowExecutionRequest {
  id: string
  version: string
  space_id: string
  inputs: Record<string, unknown>
  conversation_id: string
}

// 工作流用户输入请求类型
export interface WorkflowUserInputRequest {
  space_id: string
  id: string
  version: string
  conversation_id: string
  inputs: {
    node_id: string
    input_value: Record<string, unknown>
  }
}

export interface WorkflowCancelRequest {
  space_id: string
  conversation_id: string

}

export interface WorkflowCancelResponse {
  code: number
  message: string
  data?: {
    conversation_id: string
    cancelled: boolean
  }
}

export enum WorkflowExecutionStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export interface WorkflowExecutionResult {
  executionId: string
  status: WorkflowExecutionStatus
  startTime: string
  endTime?: string
  duration?: number
  outputs?: Record<string, unknown>
  error?: {
    message: string
    code: string
    details?: unknown
  }
  logs?: Array<{
    timestamp: string
    level: 'debug' | 'info' | 'warn' | 'error'
    message: string
    nodeId?: string
    data?: unknown
  }>
  progress?: {
    current: number
    total: number
    percentage: number
    currentNode?: string
  }
}

// SSE 事件类型
export interface WorkflowExecutionEvent {
  id: string
  version: string
  name: string
  description: string
  status: string
  type?: string
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown>
  output_text?: string
  error?: string
  start_time?: string
  end_time?: string
  timestamp?: string
  parent_id?: string
  loop_index?: number
  // 交互中断相关字段
  interaction_node?: string
  interaction_msg?: string | string[]
  _streamPayload?: unknown
}

// 智能体执行事件类型
export interface AgentExecutionEvent {
  output?: string
  // 保留一些基础字段以便与WorkflowExecutionEvent兼容
  id?: string
  version?: string
  name?: string
  description?: string
  status?: 'start' | 'finish' | 'running' | 'completed' | 'failed'
  error?: string
  // 交互中断相关字段
  interaction_node?: string
  interaction_msg?: string | string[]
}

// 工作流执行流式响应处理器
export type WorkflowExecutionEventHandler = (_event: WorkflowExecutionEvent) => void

// 执行日志相关类型
export interface ExecutionLogItem {
  id: string
  workflow_id: string
  workflow_name: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  start_time: string
  end_time?: string
  duration?: number
  trigger_type: string
  error_message?: string
  node_count?: number
  created_at: string
  updated_at: string
}

export interface ExecutionLogsListRequest {
  workflow_id?: string
  space_id?: string
  page?: number
  page_size?: number
  status?: string
  start_date?: string
  end_date?: string
}

export interface ExecutionLogsListResponse {
  code: number
  message: string
  data: {
    logs: ExecutionLogItem[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}

export interface ExecutionLogDetailRequest {
  trace_id: string
  workflow_id?: string
  space_id?: string
}

export interface ExecutionLogNode {
  node_id: string
  node_name: string
  node_type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  start_time: string
  end_time?: string
  duration?: number
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  error_message?: string
  logs?: string[]
}

export interface ExecutionLogDetail {
  id: string
  workflow_id: string
  workflow_name: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  start_time: string
  end_time?: string
  duration?: number
  trigger_type: string
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  error_message?: string
  nodes: ExecutionLogNode[]
  created_at: string
  updated_at: string
}

export interface ExecutionLogDetailResponse {
  code: number
  message: string
  data: ExecutionLogDetail
}

// 调试树相关类型
export interface DebugTreeNode {
  id: string
  name: string
  type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  start_time?: string
  end_time?: string
  duration?: number
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  error_message?: string
  logs?: string[]
  children?: DebugTreeNode[]
  parent_id?: string
  level: number
}

export interface ExecutionDebugRequest {
  workflow_id?: string
  space_id?: string
  trace_id?: string
}

// 执行日志调试相关类型
export interface ExecutionLogCreateInfo {
  trace_id: string
  create_time: string
}

export interface InvokeExecuteInfo {
  invokeId: string
  invoke_id?: string // 下划线命名格式
  workflow_version?: string
  invokeType?: string
  invoke_type?: string // 下划线命名格式
  invokeName?: string
  invoke_name?: string // 下划线命名格式
  status?: string
  startTimestamp?: number
  start_timestamp?: number // 下划线命名格式
  duration?: number
  llmMaximumReplyLength?: number
  llm_maximum_reply_length?: number // 下划线命名格式
  llmModel?: string
  llm_model?: string // 下划线命名格式
  llmTemperature?: number
  llm_temperature?: number // 下划线命名格式
  llmTtft?: number
  llm_ttft?: number // 下划线命名格式
  inputTokens?: number
  input_tokens?: number // 下划线命名格式
  outputTokens?: number
  output_tokens?: number // 下划线命名格式
  loopNodeId?: string
  loop_node_id?: string // 下划线命名格式
  loopIndex?: number
  loop_index?: number // 下划线命名格式
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown>
  childInvokesExecuteInfo?: InvokeExecuteInfo[]
  child_invokes_execute_info?: InvokeExecuteInfo[] // 下划线命名格式
}

export interface ExecutionLogSummary {
  traceId: string
  createTime: string
  duration?: number
  status: number // 0=success 1=fail 2=running 3=interrupted
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown>
  inputTokens?: number
  input_tokens?: number // 下划线命名格式
  outputTokens?: number
  output_tokens?: number // 下划线命名格式
  executeInfoList?: InvokeExecuteInfo[] // 驼峰命名格式
  execute_info_list?: InvokeExecuteInfo[] // 下划线命名格式 - 实际API返回的格式
}

export interface TraceWorkflowSpan {
  // TraceWorkflowSpan的详细字段定义，需要根据实际数据结构调整
  traceId?: string
  spanId?: string
  parentSpanId?: string
  operationName?: string
  startTime?: string
  endTime?: string
  duration?: number
  status?: string
  tags?: Record<string, unknown>
  logs?: Array<{
    timestamp: string
    fields?: Record<string, unknown>
  }>
}

export interface ExecutionDebugResponse {
  code: number
  message: string
  data: {
    logSummary: ExecutionLogSummary
    logDetails: TraceWorkflowSpan[]
    logsCreateList: ExecutionLogCreateInfo[]
    // 保留原有的字段以兼容现有代码
    log_summary?: ExecutionLogSummary
    log_details?: TraceWorkflowSpan[]
    logs_create_list?: ExecutionLogCreateInfo[]
    root_node?: DebugTreeNode
    execution_info?: {
      workflow_id: string
      workflow_name: string
      status: string
      start_time: string
      end_time?: string
      duration?: number
    }
  }
}

// 提示词相关类型

export interface PromptBasic {
  display_name: string
  description: string
  latest_version: string
  created_by: string
  updated_by: string
  created_at: string
  updated_at: string
  latest_committed_at: string | null
}

export interface ApiPrompt {
  id: number
  workspace_id: number
  prompt_key: string
  prompt_basic: PromptBasic
  prompt_draft: unknown | null
  prompt_commit: unknown | null
}

// API返回的用户信息
export interface ApiUser {
  user_id: string | null
  name: string | null
  nick_name: string | null
  avatar_url: string | null
  email: string | null
  mobile: string | null
}

export interface Prompt {
  id: string
  name: string
  description: string
  content: string
  category: string
  tags: string[]
  version: string
  usageCount: number
  rating: number
  isPublic: boolean
  author: string
  createdAt: string
  lastModified: string
  prompt_key: string
  updated_by: string
  isDraftEdited?: boolean
}

// 提示词列表请求类型
export interface PromptListRequest {
  workspace_id: string
  page?: number
  pageSize?: number
  search?: string
  filters?: Record<string, unknown>
}

// 提示词列表响应类型
export interface PromptListResponse {
  prompts: ApiPrompt[]
  users: ApiUser[]
  total: number
  msg: string
  code: number
}

// 提示词详情请求类型
export interface PromptDetailRequest {
  prompt_id: string
  with_draft?: boolean
  with_commit?: boolean
  commit_version?: string
  with_default_config?: boolean
}

// 提示词详情响应类型
export interface PromptDetailResponse extends ApiResponse<{
  prompt: ApiPrompt
  default_config: unknown | null
}> {}

// 创建提示词请求类型
export interface CreatePromptRequest {
  prompt_key: string
  prompt_name: string
  prompt_description: string
  workspace_id?: string
  content?: string
  category?: string
  language?: string
}

// 创建提示词响应类型
export interface CreatePromptResponse extends ApiResponse<{
  prompt_id: number
  msg: string
  code: number
}> {}

// 更新提示词请求类型
export interface UpdatePromptRequest {
  id: string
  prompt_key?: string
  prompt_name?: string
  prompt_description?: string
  workspace_id?: string
  content?: string
  category?: string
  language?: string
}

// 更新提示词响应类型
export interface UpdatePromptResponse extends ApiResponse<{
  msg: string
  code: number
}> {}

// 删除提示词请求类型
export interface DeletePromptRequest {
  prompt_id: string
}

// 删除提示词响应类型
export interface DeletePromptResponse extends ApiResponse<{
  msg: string
  code: number
}> {}

// 克隆提示词请求类型
export interface ClonePromptRequest {
  prompt_id: string
  prompt_name: string
  prompt_description?: string
}

// 克隆提示词响应类型
export interface ClonePromptResponse extends CreatePromptResponse {}

// 保存草稿请求类型
export interface SaveDraftRequest {
  prompt_id: string
  prompt_draft: {
    detail: unknown
    draft_info: {
      user_id: string
      base_version: string
      is_modified: boolean
    }
  }
}

// 保存草稿响应类型
export interface SaveDraftResponse extends ApiResponse<{
  draft_info: {
    base_version: string
    created_at: string
    is_modified: boolean
    updated_at: string
    user_id: string
  }
  code: number
  msg: string
}> {}

// 获取草稿请求类型
export interface GetDraftRequest {
  prompt_id: string
  user_id?: string
}

// 获取草稿响应类型
export interface GetDraftResponse extends ApiResponse<{
  detail: unknown
  draft_info: {
    user_id: string
    base_version: string
    is_modified: boolean
    created_at: string
    updated_at: string
  }
}> {}

// 提交草稿请求类型
export interface CommitDraftRequest {
  prompt_id: string
  user_id?: string
  commit_version: string
  commit_description: string
}

// 提交草稿响应类型
export interface CommitDraftResponse extends ApiResponse<{
  code: number
  msg: string
}> {}

// 获取提交记录列表请求类型
export interface ListCommitsRequest {
  prompt_id: string
  page_size?: number
}

// 获取提交记录列表响应类型
export interface ListCommitsResponse extends ApiResponse<{
  code: number
  msg: string
  prompt_commit_infos: Array<{
    version: string
    base_version: string
    description: string
    committed_by: string
    committed_at: number
  }>
}> {}

// 从提交记录恢复请求类型
export interface RevertFromCommitRequest {
  prompt_id: string
  commit_version_reverting_from: string
}

// 从提交记录恢复响应类型
export interface RevertFromCommitResponse extends ApiResponse<{
  code: number
  msg: string
}> {}

// 节点执行状态类型
export interface NodeExecutionStatus {
  nodeId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  startTime?: string
  endTime?: string
  duration?: number
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown>
  error?: string
  parentId?: string
  loopIndex?: number
}

// SSE 消息类型
export interface SSEMessage {
  code: number
  message: string
  data: SSEData // data 字段直接是 SSEData 对象
}

export type SSEData =
  | { type: 'trace'; payload: tracePayload; error_nodes_info?: ErrorNodeInfo[] }
  | { type: 'interaction'; payload: interactionPayload; error_nodes_info?: ErrorNodeInfo[] }
  | { type: 'agent'; payload: tracePayload; error_nodes_info?: ErrorNodeInfo[] }
  | { type: 'workflow'; payload: workflowPayload; error_nodes_info?: ErrorNodeInfo[] }

export interface ErrorNodeInfo {
  node_id: string
  error_message: string
}

export interface tracePayload {
  id: string
  version: string
  name: string
  description: string
  status: 'start' | 'finish' | 'running' | 'completed' | 'failed'
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown>
  output_text?: string
  error?: string
  start_time?: string
  end_time?: string
  timestamp?: string
  parent_id?: string
  loop_index?: number
}

export interface interactionPayload {
  interaction_node: string
  interaction_msg: string
}

export interface workflowPayload {
  node_id?: string
  nodeId?: string
  output?: string
  answer?: string
}

// 智能体相关类型

// AgentPlugin 接口 - 对应后端 AgentPlugin 结构
export interface AgentPlugin {
  plugin_id: string
  tool_id: string
  plugin_name?: string
  tool_name?: string
  plugin_version?: string
}

// 智能体创建请求类型
export interface CreateAgentRequest {
  space_id: string
  agent_name: string
  description: string
  agent_type: string
  icon?: string
}

// 智能体创建响应类型
export interface CreateAgentResponse {
  code: number
  message: string
  data: {
    agent_id: string
  }
}

// 智能体更新请求类型
export interface UpdateAgentRequest {
  agent_id: string
  agent_name: string
  space_id: string
  description: string
  icon: string
  agent_type: string
}

// 智能体更新响应类型
export interface UpdateAgentResponse {
  code: number
  message: string
  data: Record<string, never>
}

// 智能体复制请求类型
export interface CopyAgentRequest {
  agent_id: string
  space_id: string
  version?: string
}

// 智能体复制响应类型
export interface CopyAgentResponse {
  code: number
  message: string
  data: {
    agent_id: string
    agent_name: string
    success: boolean
  }
}

// 智能体排序枚举
export enum AgentSortBy {
  name = 'agent_name',
  create_time = 'create_time',
  update_time = 'update_time',
}

export enum AgentSortOrder {
  asc = 'asc',
  desc = 'desc',
}

// 智能体列表请求类型
export interface AgentListRequest {
  space_id: string
  page?: number
  page_size?: number
  search_term?: string
  sort_by?: AgentSortBy
  sort_order?: AgentSortOrder
}

// 智能体列表响应类型
export interface AgentListResponse {
  code: number
  message: string
  data: {
    agent_items: Array<{
      agent_id: string
      agent_name: string
      description: string
      icon: string
      status: string
      model_name: string
      lastActive: string
      usage_count: number
      tags: string[]
      create_time: number
      update_time?: number
      api_endpoint: string
      agent_version: string
      agent_type?: string
      latest_publish_version?: string
      latest_publish_time?: number
      relation_count?: {
        workflows: number
        knowledge: number
        plugins: number
      }
    }>
    pagination: {
      page: number
      page_size: number
      total: number
      total_pages: number
    }
  }
}

// 智能体搜索请求类型
export interface AgentSearchRequest {
  space_id: string
  search_term?: string
  status_filter?: string
  sort_by?: AgentSortBy
  sort_order?: AgentSortOrder
  page?: number
  page_size?: number
}

// 智能体搜索响应类型
export interface AgentSearchResponse {
  code: number
  message: string
  data: {
    agent_items: Array<{
      agent_id: string
      agent_name: string
      description: string
      icon: string
      status: string
      model_name: string
      lastActive: string
      usage_count: number
      tags: string[]
      create_time: number
      update_time?: number
      api_endpoint: string
      agent_version: string
      agent_type: string
    }>
    pagination: {
      page: number
      page_size: number
      total: number
      total_pages: number
    }
    search_term?: string
    filters: {
      status_filter: string
      sort_by: string
      sort_order: string
    }
  }
}

// 智能体详情请求类型
export interface AgentDetailRequest {
  agent_id: string
  space_id: string
  // 可选：指定获取的历史版本（不传则返回当前/最新）
  version?: string
}

// 进入智能体执行日志调试请求类型
export interface AgentExecutionDebugEnterRequest {
  business_id: string
  business_type: string
  space_id: string
  business_version?: string
}

// 进入智能体执行日志调试响应类型
export interface AgentExecutionDebugListResponse {
  code: number
  message: string
  data: ExecutionLogCreateInfo[]
}

export interface AgentExecutionDebugDetailResponse {
  code: number
  message: string
  data: AgentExecutionLogSummary
}

export interface AgentExecutionLogSummary {
  trace_id: string
  create_time: string
  duration?: number
  status: string
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown>
  input_tokens?: number
  output_tokens?: number
  execute_info_list?: InvokeExecuteInfo[]
}

// 智能体详情响应类型
export interface AgentDetailResponse {
  code: number
  message: string
  data: {
    agent_info: {
      space_id: string
      agent_id: string
      agent_version: string
      agent_name: string
      description: string
      agent_type: string
      configs: Record<string, unknown>
      icon: string
      edit_mode: string
      plugins: AgentPlugin[]
      workflows: Array<{
        workflow_id: string
        workflow_version: string
        workflow_name: string
        description: string
      }>
      model: {
        model_provider: string
        model_info: {
          api_key: string
          api_base: string
          model_name: string
          temperature: number
          top_p: number
          streaming: boolean
          max_tokens: number
          timeout: number
          model_type: string
        }
      }
      prompt_template_name: string
      prompt_template: Array<{
        role: string
        content: string
      }>
      constraint: {
        reserved_max_chat_rounds: number
        max_iteration: number
      }
      auto_generated_prompt: string
      prompt_tuning: {
        input_mode: string
        examples: string
        use_cases: Array<{
          id: number
          name: string
          data: Array<{
            user: string
            assistant: string
          }>
          upload_time: string
        }>
        optimization_model: string
        evaluation_model: string
        optimization_rounds: number
      }
      triggers: string[]
      knowledge: string[]
      memory: {
        max_tokens: number
        longterm_memory_config?: boolean
        variable_config?: Array<{
          id: string
          name: string
          description?: string // 可选
          defaultValue?: string // 可选默认值
          enabled?: boolean // 是否启用，默认 true
        }>
      }
      opening_remarks: string
      create_time: string
      update_time: string
    }
    agent_option_info: {
      model_list: Array<{
        model_id: number
        model_name: string
        temperature: number
        top_p: number
        max_tokens: number
        model_provider: string
        api_key: string
        api_base: string
        streaming: boolean
        timeout: number
        model_type: string
      }>
      workflow_list: Array<{
        workflow_id: string
        workflow_version: string
        workflow_name: string
        description: string
      }>
    }
  }
}

// 插件相关类型

// 插件类型枚举
export enum PluginType {
  url = 1,
  code = 2,
}

// 插件API方法枚举
export enum PluginApiMethod {
  get = 1,
  post = 2,
  put = 3,
  delete = 4,
  patch = 5,
}

// 参数发送方法枚举
export enum ParamSendMethod {
  NONE = 0,
  HEADER = 1,
  QUERY = 2,
  BODY = 3,
}

// 插件参数类型枚举
export enum ParamType {
  STRING = 1,
  INT = 2,
  FLOAT = 3,
  BOOL = 4,
  OBJECT = 5,
  ARRAY_STRING = 6,
  ARRAY_INT = 7,
  ARRAY_FLOAT = 8,
  ARRAY_BOOL = 9,
}

// 插件参数优先级枚举
export enum Priority {
  TOOL = 0,
  PLUGIN = 1,
}

export interface PluginCreateRequest {
  name: string
  desc: string
  desc_mk?: string
  space_id: string
  plugin_type: PluginType | number
  url?: string
  icon_uri?: string
}

export interface PluginCreateResponse {
  code: number
  message: string
  data: {
    plugin_id: string
  }
}

export interface PluginGetRequest {
  space_id: string
  plugin_id: string
  plugin_version?: string
}

export interface PluginInfo {
  space_id: string
  plugin_id: string
  plugin_version?: string
  name: string
  desc: string
  desc_mk?: string
  plugin_type: number
  published: boolean
  url?: string
  icon_uri?: string
  request_params?: PluginRequestParam[]
}

export interface PluginGetResponse {
  code: number
  message: string
  data: {
    plugin_info: PluginInfo
  }
}

export interface PluginDeleteRequest {
  space_id: string
  plugin_id: string
  plugin_version?: string
}

export interface PluginDeleteResponse {
  code: number
  message: string
  data: Record<string, never>
}

export interface PluginUpdateRequest {
  space_id: string
  plugin_id: string
  plugin_version?: string
  name?: string
  desc?: string
  desc_mk?: string
  plugin_type?: PluginType | number
  published?: boolean
  url?: string
  icon_uri?: string
  request_params?: PluginRequestParam[]
}

export interface PluginUpdateResponse {
  code: number
  message: string
  data: Record<string, never>
}

export interface PluginListRequest {
  space_id: string
  page?: number
  size?: number
}

export interface PluginListResponse {
  code: number
  message: string
  data: {
    plugin_infos: PluginInfo[]
  }
}

export interface PluginGetMarketRequest {
  space_id: string
  page?: number
  size?: number
}

export interface PluginGetMarketResponse {
  code: number
  message: string
  data: string
}

// Plugin API 相关类型
export interface PluginApiBase {
  space_id: string
  plugin_id: string
  name: string
  desc: string
  path: string
  method: PluginApiMethod | number
  plugin_version?: string
}

export interface PluginApiId extends PluginApiBase {
  tool_id: string
}

export interface PluginListApi extends PluginApiBase {
  page?: number
  size?: number
}

export interface PluginRequestParam {
  name: string
  desc?: string
  type: ParamType | number
  is_required: boolean
  value: string
  is_runtime: boolean
  priority: Priority | number
}

export interface PluginApiParam {
  name: string
  desc?: string
  type: ParamType | number
  is_required?: boolean
  method?: ParamSendMethod
  is_runtime?: boolean
  value?: string
  priority?: Priority | number
}

export interface PluginApiHeader {
  name: string
  value: string
}

export interface PluginApiInfo extends PluginApiBase {
  tool_id: string
  request_params?: PluginApiParam[]
  response_params?: PluginApiParam[]
  headers?: PluginApiHeader[]
  available?: boolean
}

export interface PluginApiInfoResponse {
  code: number
  message: string
  data: {
    api_info: PluginApiInfo[]
    total: number
  }
}

// Plugin API 请求类型
export interface PluginCreateApiRequest {
  space_id: string
  plugin_id: string
  name: string
  desc: string
  path: string
  method: PluginApiMethod | number
  plugin_version?: string
  request_params?: PluginApiParam[]
  response_params?: PluginApiParam[]
  headers?: PluginApiHeader[]
  available?: boolean
}

export interface PluginUpdateApiRequest extends PluginApiInfo {}

export interface PluginDeleteApiRequest {
  space_id: string
  plugin_id: string
  tool_id: string
  plugin_version?: string
}

export interface PluginGetApiRequest {
  space_id: string
  plugin_id: string
  tool_id: string
  plugin_version?: string
}

export interface PluginListApiRequest {
  space_id: string
  plugin_id: string
  page?: number
  size?: number
  plugin_version?: string
}

// Plugin API 响应类型
export interface PluginCreateApiResponse {
  code: number
  message: string
  data: Record<string, never>
}

export interface PluginUpdateApiResponse {
  code: number
  message: string
  data: Record<string, never>
}

export interface PluginDeleteApiResponse {
  code: number
  message: string
  data: Record<string, never>
}

export interface PluginGetApiResponse {
  code: number
  message: string
  data: {
    api_info: PluginApiInfo[]
    total: number
  }
}

export interface PluginListApiResponse extends PluginApiInfoResponse {}

// Plugin Execution 相关类型
export interface PluginExecuteRequest {
  space_id?: string
  id?: string
  version?: string
  conversation_id?: string
  plugin_id: string
  tool_id: string
  inputs: Record<string, unknown>
}

export interface PluginExecuteResponse {
  code: number
  message: string
  data: unknown
}

// Plugin Execution Event 类型 (用于SSE流式响应)
export interface PluginExecutionEvent {
  id?: string
  version?: string
  name?: string
  description?: string
  status?: string
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown>
  output_text?: string
  error?: string
  start_time?: string
  end_time?: string
  timestamp?: string
  parent_id?: string
  loop_index?: number
}

// Plugin Execution 事件处理器类型
export interface PluginExecutionEventHandler {
  (_event: PluginExecutionEvent): void
}

// 单节点调试请求类型
export interface ComponentExecuteRequest {
  space_id: string
  id: string
  version: string
  inputs: Record<string, any>
  component_id: string
  loop_id?: string
  conversation_id?: string
  force?: boolean
}
// 单节点调试响应类型
export interface ComponentExecuteResponse {
  data: {
    responseContent: string
    output: {
      result: string
    }
  }
  code: number
  message: string
}

// 单节点调试取消请求类型
export interface ComponentCancelRequest {
  space_id: string
  id: string
  version: string
  component_id: string
  conversation_id?: string
  force?: boolean
}

// 单节点调试取消响应类型
export interface ComponentCancelResponse {
  code: number
  message: string
  data?: {
    workflow_id?: string
    component_id?: string
    conversation_id?: string
    cancelled?: boolean
    warning?: string
  }
}

// Plugin Code 相关类型
export interface PluginCodeBase {
  space_id: string
  plugin_id: string
  name: string
  desc: string
  language: string
  code: string
  plugin_version?: string
}

export interface PluginCodeInfo extends PluginCodeBase {
  tool_id: string
  request_params?: PluginApiParam[]
  response_params?: PluginApiParam[]
  available?: boolean
}

export interface PluginCodeInfoResponse {
  code: number
  message: string
  data: {
    code_info: PluginCodeInfo[]
    total: number
  }
}

// Plugin Code 请求类型
export interface PluginCreateCodeRequest {
  space_id: string
  plugin_id: string
  name: string
  desc: string
  language: string
  code: string
  plugin_version?: string
  request_params?: PluginApiParam[]
  response_params?: PluginApiParam[]
}

export interface PluginUpdateCodeRequest extends PluginCodeInfo {}

export interface PluginDeleteCodeRequest {
  space_id: string
  plugin_id: string
  tool_id: string
  plugin_version?: string
}

export interface PluginGetCodeRequest {
  space_id: string
  plugin_id: string
  tool_id: string
  plugin_version?: string
}

export interface PluginListCodeRequest {
  space_id: string
  plugin_id: string
  page?: number
  size?: number
  plugin_version?: string
}

// Plugin Code 响应类型
export interface PluginCreateCodeResponse {
  code: number
  message: string
  data: Record<string, never>
}

export interface PluginUpdateCodeResponse {
  code: number
  message: string
  data: Record<string, never>
}

export interface PluginDeleteCodeResponse {
  code: number
  message: string
  data: Record<string, never>
}

export interface PluginGetCodeResponse {
  code: number
  message: string
  data: PluginCodeInfo
}

export interface PluginListCodeResponse extends PluginCodeInfoResponse {}

// Plugin Publish 相关类型
export interface PluginPublishRequest {
  space_id: string
  plugin_id: string
  plugin_version?: string
  version_desc?: string
  force?: boolean
}

export interface PluginPublishResponse {
  code: number
  message: string
  data: {
    plugin_id: string
    version: string
    published_at: string
  }
}

export interface PluginPublishInfo {
  space_id: string
  plugin_id: string
  plugin_version?: string
  name: string
  desc: string
  plugin_type: number
  published: boolean
  url?: string
  icon_uri?: string
  version_desc?: string
  tools: Array<{
    tool_id: string
    name: string
    desc: string
    path: string
    method: number
    request_params?: Array<{
      name: string
      desc: string
      type: number
      is_required: boolean
    }>
    response_params?: Array<{
      name: string
      desc: string
      type: number
    }>
    headers?: Array<{
      name: string
      value: string
    }>
  }>
}

export interface PluginPublishGetRequest {
  space_id: string
  plugin_id: string
  plugin_version?: string
}

export interface PluginPublishGetResponse {
  code: number
  message: string
  data: {
    plugin_info: PluginPublishInfo
  }
}

export interface PluginPublishListRequest {
  space_id: string
  plugin_id: string
}

export interface PluginPublishListResponse {
  code: number
  message: string
  data: {
    plugin_infos: PluginPublishInfo[]
  }
}

export interface PluginPublishDeleteRequest {
  space_id: string
  plugin_id: string
  plugin_version?: string
}

export interface PluginPublishDeleteResponse {
  code: number
  message: string
  data: Record<string, never>
}

// 工作流发布相关类型

// 工作流发布请求类型
export interface WorkflowPublishRequest {
  workflow_id: string
  space_id: string
  force: boolean
  version: string
  version_description: string
}

// 工作流发布响应类型
export interface WorkflowPublishResponse {
  code: number
  message: string
  data: {
    workflow_id: string
    success: boolean
  }
}

// 工作流版本列表请求类型
export interface WorkflowVersionListRequest {
  workflow_id: string
  space_id: string
}

// 工作流版本信息类型
export interface WorkflowVersionInfo {
  workflow_version: string
  version_description: string
  create_time: number
}

// 工作流版本列表响应类型
export interface WorkflowVersionListResponse {
  code: number
  message: string
  data: {
    workflow_id: string
    versions: WorkflowVersionInfo[]
  }
}

// Agent发布相关类型

// Agent发布请求类型
export interface AgentPublishRequest {
  agent_id: string
  space_id: string
  version: string
  version_description: string
}

// Agent发布响应类型
export interface AgentPublishResponse {
  code: number
  message: string
  data: {
    agent_id: string
    success: boolean
  }
}

// Agent版本列表请求类型
export interface AgentVersionListRequest {
  agent_id: string
  space_id: string
}

// Agent版本信息类型
export interface AgentVersionInfo {
  agent_version: string
  version_description: string
  create_time: number
}

// Agent版本列表响应类型
export interface AgentVersionListResponse {
  code: number
  message: string
  data: {
    agent_id: string
    versions: AgentVersionInfo[]
  }
}

// 文件上传/下载相关类型

// 获取文件上传URL请求类型
export interface GetUploadUrlRequest {
  object_key: string
}

// 获取文件上传URL响应类型
export interface GetUploadUrlResponse {
  code: number
  message: string
  data: {
    upload_url: string
  }
}

// 获取文件下载URL请求类型
export interface GetDownloadUrlRequest {
  object_key?: string
}

// 获取文件下载URL响应类型
export interface GetDownloadUrlResponse {
  code: number
  message: string
  data: {
    download_url: string
  }
}
