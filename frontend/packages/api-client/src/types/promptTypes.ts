// 提示词相关类型定义

// API返回的提示词基础信息
export interface PromptBasic {
  display_name: string
  description: string
  latest_version: string
  created_by: string
  updated_by: string
  created_by_name: string
  updated_by_name: string
  created_at: string
  updated_at: string
  latest_committed_at: string | null
}

// 关联对象信息
export interface RelationObj {
  obj_id: string
  obj_version: string
  obj_name: string
  obj_type_name: string
}

// API返回的提示词结构
export interface ApiPrompt {
  id: number
  workspace_id: number
  prompt_key: string
  prompt_basic: PromptBasic
  prompt_draft: any | null
  prompt_commit: any | null
  relation_obj: RelationObj[]
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

// 前端展示用的提示词接口（保持原有结构兼容性）
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
  // 新增字段
  prompt_key: string
  updated_by: string
  isDraftEdited?: boolean // 是否有未提交的草稿修改
  associations?: {
    relationObjs?: RelationObj[]
  }
  // 最近提交时间
  latest_committed_at?: string | null
}

// 创建提示词请求
export interface CreatePromptRequest {
  updated_by: string
  prompt_key: string
  prompt_name: string
  prompt_description: string
  workspace_id?: string
  content?: string
  category?: string
  language?: string
}

// 创建提示词响应
export interface CreatePromptResponse {
  prompt_id: number
  msg: string
  code: number
}

// 更新提示词请求
export interface UpdatePromptRequest extends Partial<CreatePromptRequest> {
  id: string
}

// 编辑提示词基本信息请求
export interface EditPromptBasicInfoRequest {
  prompt_id: number
  prompt_name: string
  prompt_description: string
}

// 编辑提示词基本信息响应
export interface EditPromptBasicInfoResponse {
  msg: string
  code: number
}

// 删除提示词请求
export interface DeletePromptRequest {
  prompt_id: number
  workspace_id: string
}

// 删除提示词响应
export interface DeletePromptResponse {
  msg: string
  code: number
}

// API原始列表响应
export interface ApiPromptListResponse {
  prompts: ApiPrompt[]
  users: ApiUser[]
  total: number
  msg: string
  code: number
}

// 前端使用的提示词列表响应
export interface PromptListResponse {
  prompts: Prompt[]
  total: number
  page: number
  pageSize: number
}

// 提示词消息接口
export interface PromptMessage {
  role: 'system' | 'user' | 'assistant' | 'placeholder'
  reasoning_content: string | null
  content: string
  parts: any | null
  tool_call_id: string | null
  tool_calls: any | null
  key: string
}

// 变量定义接口
export interface VariableDef {
  key: string
  desc: string
  type: 'string' | 'placeholder'
}

// 提示词模板接口
export interface PromptTemplate {
  template_type: 'normal' | 'jinja2'
  messages: PromptMessage[]
  variable_defs: VariableDef[]
}

// 工具函数接口
export interface ToolFunction {
  name: string
  description: string
  parameters: string // JSON字符串
}

// 工具接口
export interface Tool {
  type: 'function'
  function: ToolFunction
}

// 工具调用配置接口
export interface ToolCallConfig {
  tool_choice: 'auto' | 'none'
  debug_mode?: boolean // 单步调试模式
}

// 提示词模型配置接口
export interface PromptModelConfig {
  models_id: string | null
  max_tokens: number
  temperature: number
  top_k: number | null
  top_p: number | null
  presence_penalty: number | null
  frequency_penalty: number | null
  json_mode: boolean | null
  // 支持动态参数
  [key: string]: any
}

// 提示词详情接口
export interface PromptDetail {
  prompt_template: PromptTemplate
  tools: Tool[]
  tool_call_config: ToolCallConfig
  prompt_model_config: PromptModelConfig
}

// 草稿信息接口
export interface DraftInfo {
  user_id?: string // 可选，后端可从 token 解析用户身份
  base_version: string
  is_modified: boolean
  is_draft_edited?: boolean // 新增字段：是否有未提交的草稿编辑
  created_at: string
  updated_at: string
  space_id: string // 新增字段：工作空间ID
}

// 提交信息接口
export interface CommitInfo {
  // 根据实际API返回结构补充
  [key: string]: any
}

// 提示词草稿接口
export interface PromptDraft {
  detail: PromptDetail
  draft_info: DraftInfo
}

// 提示词提交接口
export interface PromptCommit {
  detail: PromptDetail
  commit_info: CommitInfo | null
}

// API返回的提示词详情结构
export interface ApiPromptDetail {
  id: number
  workspace_id: number
  prompt_key: string
  prompt_basic: PromptBasic
  prompt_draft: PromptDraft | null
  prompt_commit: PromptCommit | null
}

// 获取提示词详情响应
export interface GetPromptDetailResponse {
  prompt: ApiPromptDetail[]
  default_config: PromptDetail | null
  msg: string
  code: number
}

// 获取提示词详情请求参数
export interface GetPromptDetailRequest {
  workspace_id: string
  with_commit: boolean
  with_draft: boolean
  with_default_config: boolean
  commit_version?: string
}

// 保存草稿相关接口定义
export interface DraftMessage {
  content: string
  role: 'system' | 'user' | 'assistant' | 'placeholder'
  key: string
}

export interface DraftVariableDef {
  key: string
  type: 'string' | 'placeholder'
  desc: string
}

export interface DraftModelConfig {
  models_name: string
  models_id: string
  temperature: number
  max_tokens: number
  // 支持动态参数
  [key: string]: any
}

export interface DraftToolCallConfig {
  tool_choice: 'auto' | 'none'
  debug_mode?: boolean // 单步调试模式
}

// JSON Schema 参数类型
export interface JsonSchemaParameter {
  type: 'object'
  properties: {
    [key: string]: {
      type: string
      description: string
    }
  }
  required: string[]
  additionalProperties: boolean
}

export interface DraftTool {
  type: 'function'
  function: {
    name: string
    description: string
    parameters: string // JSON Schema 字符串格式
  }
}

export interface DraftDetail {
  prompt_template: {
    template_type: 'normal' | 'jinja2'
    messages: DraftMessage[]
    variable_defs: DraftVariableDef[]
  }
  prompt_model_config: DraftModelConfig
  tool_call_config: DraftToolCallConfig
  tools: DraftTool[]
}

export interface SaveDraftRequest {
  prompt_draft: {
    detail: DraftDetail
    draft_info: DraftInfo
  }
}

export interface SaveDraftResponse {
  draft_info: {
    base_version: string
    created_at: string
    is_modified: boolean
    updated_at: string
    user_id: string
    space_id: string
  }
  code: number
  msg: string
}

// 提交版本请求
export interface CommitVersionRequest {
  commit_version: string
  commit_description: string
}

// 提交版本响应
export interface CommitVersionResponse {
  code: number
  msg: string
}

// 还原为此版本请求
export interface RevertToVersionRequest {
  commit_version_reverting_from: string
}

// 还原为此版本响应
export interface RevertToVersionResponse {
  code: number
  msg: string
}

// 版本提交信息
export interface PromptCommitInfo {
  version: string
  base_version: string
  description: string
  committed_by: string
  committed_by_name: string
  committed_at: number
  relation_obj: RelationObj[]
}

// 获取版本列表请求参数
export interface GetVersionListRequest {
  page_size?: number
}

// 获取版本列表响应
export interface GetVersionListResponse {
  code: number
  msg: string
  prompt_commit_infos: PromptCommitInfo[]
}

// 调试相关接口
export interface DebugMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  tool_calls?: any[]
  tool_call_id?: string
}

export interface DebugVariableVal {
  key: string
  value?: string
  placeholder_messages?: Array<{
    id: string
    content: string
    role: 'system' | 'user' | 'assistant'
    parts: any[]
  }>
}

export interface DebugMockTool {
  name: string
  mock_value: string
  mock_response?: string
}

export interface DebugStreamingRequest {
  prompt_id: string
  user_id: string
  variable_vals: DebugVariableVal[]
  mock_tools: DebugMockTool[]
  prompt?: any // 包含 prompt_draft.detail.prompt_model_config.model_from
  messages?: any[]
  single_step_debug?: boolean
}

export interface DebugStreamingResponse {
  data: string
  message_id: string
  is_end: boolean
}

// 保存调试上下文请求
export interface SaveDebugContextRequest {
  prompt_id: string
  workspace_id?: string
  debug_context: DebugContext
}

// 模拟上下文
export interface MockContext {
  variable_vals: DebugVariableVal[]
  mock_tools: DebugMockTool[]
}

// 基础模拟变量
export interface BaseMockVariable {
  key: string
  value: string
}

// 基础模拟工具
export interface BaseMockTool {
  name: string
  mock_value: string
}

// 调试流式响应
export interface DebugStreamingResponse {
  delta: {
    content: string
    reasoning_content?: string
    role?: string
    tool_calls?: Array<{
      index: number
      id: string
      function: {
        arguments: string
        name: string
      }
      type: string
    }>
  } | null
  finish_reason: string | null
  usage: any | null
  debug_id: string
  debug_trace_key: string
}

// 消息上下文（用户和AI的对话记录）
export interface MockContext {
  role: 'user' | 'assistant'
  content: string
  reasoning_content?: string | null
  parts?: any[] | null
  tool_call_id?: string | null
  tool_calls?: any[] | null
  debug_id?: string | null
  input_tokens?: string | null
  output_tokens?: string | null
  cost_ms?: string | null
  msg_time?: string // 消息产生的时间
  // 编辑相关字段
  isEdit?: boolean
  // 工具调用相关字段
  tool_calls?: Array<{
    tool_call: {
      index: string
      id: string
      function_call: {
        name: string
        arguments: string
      }
      type: string
    }
    mock_response: string
    debug_trace_key: string
  }>
}

// 模拟变量（更新版本）
export interface MockVariable {
  key: string
  value: string
  desc: string
  type: string
  placeholder_messages?: Array<{
    id: string
    content: string
    role: string
    parts: any[]
  }> | null
}

// 模拟工具（更新版本）
export interface MockTool {
  name: string
  mock_response: string
}

// 调试核心数据
export interface DebugCore {
  mock_contexts: MockContext[]
  mock_variables: MockVariable[]
  mock_tools: MockTool[]
}

// 调试配置
export interface DebugConfig {
  single_step_debug: boolean
}

// 调试上下文
export interface DebugContext {
  debug_core: DebugCore
  debug_config: DebugConfig
}

// 保存调试上下文响应
export interface SaveDebugContextResponse {
  code: number
  msg: string
}

// 获取调试上下文响应
export interface GetDebugContextResponse {
  code: number
  msg: string
  debug_context?: GetMockContext
}

// 获取模拟上下文
export interface GetMockContext {
  debug_core: {
    mock_contexts: MockContext[]
    mock_variables: MockVariable[]
    mock_tools: MockTool[]
  }
  debug_config: DebugConfig
  compare_config?: {
    groups: any[]
  }
}

// 克隆提示词请求
export interface ClonePromptRequest {
  user_id: string
  workspace_id: string
  commit_version: string
  cloned_prompt_name: string
  cloned_prompt_key: string
  cloned_prompt_description: string
}

// 克隆提示词响应
export interface ClonePromptResponse {
  cloned_prompt_id: number
  msg: string
  code: number
}

// 调试历史项
export interface DebugHistoryItem {
  id: string
  prompt_id: string
  workspace_id: string
  prompt_key: string
  version: string
  input_tokens: string
  output_tokens: string
  cost_ms: string | null
  status_code: number | null
  debugged_by: string
  debug_id: string
  debug_step: number
  started_at: string | null
  ended_at: string | null
}

// 获取调试历史列表请求
export interface DebugHistoryListRequest {
  prompt_id: string
  workspace_id: string
  page_size?: number
  page_token?: string | null
}

// 获取调试历史列表响应
export interface DebugHistoryListResponse {
  debug_history: DebugHistoryItem[]
  has_more: boolean
  next_page_token: string | null
}

// API响应包装器
export interface PromptApiResponse<T> {
  code: number
  msg: string
  data?: T
}

// 错误响应
export interface PromptApiError {
  code: number
  msg: string
  error?: string
  details?: Record<string, any>
}
