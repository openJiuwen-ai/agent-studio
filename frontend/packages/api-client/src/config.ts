// API配置文件
export const API_CONFIG = {
  // 基础API URL - 可以通过环境变量或参数配置
  // 开发环境使用相对路径，会被vite代理处理
  // 生产环境使用完整URL
  BASE_URL:
    (typeof process !== 'undefined' && process.env?.VITE_API_BASE_URL) ||
    (typeof window !== 'undefined' && (window as unknown as { __API_BASE_URL__?: string }).__API_BASE_URL__) ||
    '/api/v1', // 默认使用相对路径，在开发环境会被vite代理处理

  // 请求超时时间（毫秒）
  TIMEOUT: 300000,

  // 流式请求超时时间（毫秒）- 用于SSE流式响应
  STREAM_TIMEOUT: 300000,

  // 重试次数
  MAX_RETRIES: 3,

  // 重试延迟（毫秒）
  RETRY_DELAY: 1000,

  // 请求头配置
  HEADERS: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },

  // 认证相关配置
  AUTH: {
    TOKEN_KEY: 'auth_token',
    REFRESH_TOKEN_KEY: 'refresh_token',
    TOKEN_EXPIRY_KEY: 'token_expiry',
  },

  // 分页配置
  PAGINATION: {
    DEFAULT_PAGE_SIZE: 20,
    MAX_PAGE_SIZE: 100,
  },

  // 缓存配置
  CACHE: {
    DEFAULT_TTL: 5 * 60 * 1000, // 5分钟
    MAX_CACHE_SIZE: 100,
  },

  // 环境配置
  IS_DEV:
    (typeof process !== 'undefined' && process.env?.NODE_ENV === 'development') ||
    (typeof window !== 'undefined' && (window as unknown as { __DEV?: boolean }).__DEV__),
  IS_PROD:
    (typeof process !== 'undefined' && process.env?.NODE_ENV === 'production') ||
    (typeof window !== 'undefined' && (window as unknown as { __PROD?: boolean }).__PROD__),
  IS_TEST:
    (typeof process !== 'undefined' && process.env?.NODE_ENV === 'test') ||
    (typeof window !== 'undefined' && (window as unknown as { __TEST?: boolean }).__TEST__),
}

// 配置更新函数
export const updateApiConfig = (newConfig: Partial<typeof API_CONFIG>) => {
  Object.assign(API_CONFIG, newConfig)
}

// 设置基础 URL 的便捷函数
export const setApiBaseUrl = (baseUrl: string) => {
  API_CONFIG.BASE_URL = baseUrl
}

// API端点常量
export const API_ENDPOINTS = {
  // 认证相关
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    REGISTER: '/auth/register',
    CHANGE_PASSWORD: '/auth/change-password',
    RESET_PASSWORD: '/auth/reset-password',
    FORGOT_PASSWORD: '/auth/send-reset-code',
    SEND_CODE: '/auth/send-code',
    VERIFY_ACCESS_TOKEN: '/auth/verify_access_token',
  },

  // 用户管理
  USERS: {
    LIST: '/users',
    DETAIL: '/users/:id',
    CREATE: '/users',
    UPDATE: '/users/:id',
    DELETE: '/users/:id',
    ROLES: '/users/roles',
    PERMISSIONS: '/users/permissions',
  },

  // 工作流管理
  WORKFLOWS: {
    LIST: '/workflows/list',
    CREATE: '/workflows/create',
    CANVAS: '/workflows/canvas',
    SAVE: '/workflows/save',
    DELETE: '/workflows/delete',
    UPDATE: '/workflows/update',
    COPY: '/workflows/copy',
    SEARCH: '/workflows/search',
    PUBLISH: '/workflows/publish',
    VERSION_LIST: '/workflows/version_list',
    DELETE_PUBLISH_VERSION: '/workflows/delete_publish',
    EXECUTION_LOGS_LIST: '/workflows/get_execution_logs_create_list',
    EXECUTION_LOG_DETAIL: '/workflows/get_execution_log',
    ENTER_EXECUTION_DEBUG: '/workflows/enter_execution_logs_debug',
    GET_UPLOAD_URL: '/workflows/get_upload_url',
    GET_DOWNLOAD_URL: '/workflows/get_download_url',
  },

  // 执行管理
  EXECUTION: {
    WORKFLOW: '/execution/workflow',
    WORKFLOW_CANCEL: '/execution/workflow/cancel',
    USERINPUT: '/execution/userInput',
    WORKFLOW_VALIDATE: '/execution/workflow/validate',
    AGENT: '/execution/agent',
    AGENT_RESET: '/execution/agent/reset',
    AGENT_USERINPUT: '/execution/agent/userInput',
    PLUGIN: '/execution/plugin',
    COMPONENT: '/execution/component',
    COMPONENT_CANCEL: '/execution/component/cancel',
    GET_TRACE_SUMMARY_LIST: '/execution/get_trace_summary_list',
    GET_TRACE_SUMMARY_BY_TRACE_ID: '/execution/get_trace_summary_by_trace_id',
  },

  // 代理管理
  AGENTS: {
    LIST: '/agents/list',
    SEARCH: '/agents/search',
    DETAIL: '/agents/get_agent_info',
    CREATE: '/agents/create',
    SAVE: '/agents/save',
    UPDATE: '/agents/update',
    DELETE: '/agents/delete',
    COPY: '/agents/copy',
    PUBLISH: '/agents/publish',
    EXPORT: '/agents/export',
    IMPORT: '/agents/import',
    VERSION_LIST: '/agents/version_list',
    DELETE_PUBLISH_VERSION: '/agents/delete_publish',
    EXECUTE: '/agents/:id/execute',
    TRAIN: '/agents/:id/train',
    DEPLOY: '/agents/:id/deploy',
  },

  // 模型管理
  MODELS: {
    LIST: '/models/',
    DETAIL: '/models/:id/',
    CREATE: '/models/',
    UPDATE: '/models/:id/',
    DELETE: '/models/:id/',
    TEST: '/models/:id/test/',
    METRICS: '/models/:id/metrics/',
  },

  // 提示词管理
  PROMPTS: {
    LIST: '/prompts/list',
    DETAIL: '/prompts/:id',
    CREATE: '/prompts/',
    UPDATE: '/prompts/:id',
    DELETE: '/prompts/:id',
    CLONE: '/prompts/:id/clone',
    SAVE_DRAFT: '/prompts/:id/drafts/save',
    GET_DRAFT: '/prompts/:id/drafts',
    COMMIT_DRAFT: '/prompts/:id/drafts/commit',
    LIST_COMMITS: '/prompts/:id/commits/list',
    REVERT_FROM_COMMIT: '/prompts/:id/drafts/revert_from_commit',
    BUILD: '/prompts/tuning/build',
    // 调试相关
    DEBUG_STREAMING: '/prompts/:id/debug_streaming',
    SAVE_DEBUG_CONTEXT: '/prompts/:id/debug_context/save',
    GET_DEBUG_CONTEXT: '/prompts/:id/debug_context/get',
    DEBUG_HISTORY_LIST: '/prompts/:id/debug_history/list',
  },

  // 分析统计
  ANALYTICS: {
    OVERVIEW: '/analytics/overview',
    WORKFLOW_STATS: '/analytics/workflows',
    AGENT_STATS: '/analytics/agents',
    USER_STATS: '/analytics/users',
    PERFORMANCE: '/analytics/performance',
    REPORTS: '/analytics/reports',
  },

  // 系统设置
  SETTINGS: {
    SYSTEM: '/settings/system',
    SECURITY: '/settings/security',
    NOTIFICATIONS: '/settings/notifications',
    INTEGRATIONS: '/settings/integrations',
  },

  // 文件管理
  FILES: {
    UPLOAD: '/files/upload',
    DOWNLOAD: '/files/:id/download',
    DELETE: '/files/:id',
    LIST: '/files',
    METADATA: '/files/:id/metadata',
  },

  // 日志管理
  LOGS: {
    SYSTEM: '/logs/system',
    WORKFLOW: '/logs/workflow',
    USER: '/logs/user',
    ERROR: '/logs/error',
    AUDIT: '/logs/audit',
  },

  // 空间管理
  SPACE: {
    LIST: '/spaces/',
    DETAIL: '/spaces/:id/',
    CREATE: '/spaces/',
    UPDATE: '/spaces/:id/',
    DELETE: '/spaces/:id/',
    USER_SPACES: '/spaces/user/',
  },

  // 关联成员管理
  RELATED: {
    PROMPT_LIST: '/related/prompt/list/:spaceId',
    PROMPT_REGISTER: '/related/prompt/:spaceId',
    PROMPT_DELETE: '/related/prompt/:spaceId',
  },

  // 自优化管理
  SELF_OPTIMIZATION: {
    CREATE_JOB: '/prompts/tuning/templates_optimization/jobs',
    GET_JOB_LIST: '/prompts/tuning/templates_optimization/jobs/get_infos',
    DELETE_JOB: '/prompts/tuning/templates_optimization/jobs/:jobId',
    DATA_CHECK: '/prompts/tuning/templates_optimization/data_check',
    JOB_DETAIL: '/prompts/tuning/templates_optimization/jobs/:jobId',
    SAVE_JOB_DRAFT: '/prompts/tuning/templates_optimization/job_draft/save',
    GET_JOB_DRAFT: '/prompts/tuning/templates_optimization/job_draft/get',
    JOB_HISTORY: '/prompts/tuning/templates_optimization/job_history/:jobId',
  },

  // 反馈优化管理
  FEEDBACK_OPTIMIZATION: {
    OPTIMIZE_FEEDBACK: '/prompts/tuning/optimize_feedback',
    OPTIMIZE_BADCASE: '/prompts/tuning/optimize_badcase',
    QUICK_OPTIMIZE: '/prompts/tuning/build',
  },

  // 提示词模型管理
  PROMPT_MODELS: {
    LIST: '/llm/models/list',
    DETAIL: '/llm/model/:modelId',
  },

  // 标签管理
  TAGS: {
    LIST: '/tags/list',
    CREATE: '/tags/create',
    SEARCH: '/tags/search',
    GET_BY_ID: '/tags/:id',
    GET: '/tags',
    UPDATE: '/tags/:id',
    DELETE: '/tags/delete',
    GET_OR_CREATE: '/tags/get-or-create',
    BATCH_CREATE: '/tags/batch',
  },

  // 插件管理
  PLUGINS: {
    CREATE: '/plugin/create',
    GET: '/plugin/get',
    UPDATE: '/plugin/update',
    DELETE: '/plugin/delete',
    LIST: '/plugin/list',
    GET_MARKET: '/plugin/get_market',
    PUBLISH: '/plugin/publish',
    PUBLISH_GET: '/plugin/publish_get',
    PUBLISH_LIST: '/plugin/publish_list',
    PUBLISH_DELETE: '/plugin/publish_delete',
    CREATE_API: '/plugin/create_api',
    UPDATE_API: '/plugin/update_api',
    DELETE_API: '/plugin/delete_api',
    GET_API: '/plugin/get_api',
    LIST_API: '/plugin/list_api',
    CREATE_CODE: '/plugin/create_code',
    UPDATE_CODE: '/plugin/update_code',
    DELETE_CODE: '/plugin/delete_code',
    GET_CODE: '/plugin/get_code',
    LIST_CODE: '/plugin/list_code',
  },

  // 可观测性管理
  OBSERVABILITY: {
    TRACE_LIST: '/observability/spans/list',
    TRACE_TREE: '/observability/traces',
  },

  // 知识库管理
  KNOWLEDGE_BASES: {
    LIST: '/knowledge-base/list',
    DETAIL: '/knowledge-bases/:id',
    CREATE: '/knowledge-base/create',
    UPDATE: '/knowledge-base/update',
    DELETE: '/knowledge-base/delete',
    GET_REFERENCING_AGENTS: '/knowledge-base/get-referencing-agents',
    SEARCH: '/knowledge-base/search',
    STATISTICS: '/knowledge-bases/statistics',
    UPLOAD: '/knowledge-base/upload',
    PROCESS: '/knowledge-base/process',
    STATUS: '/knowledge-base/documents/status',
    FILE_SETTINGS: '/knowledge-base/filesettings',
    DOCUMENTS_LIST: '/knowledge-base/documents/list',
    DOCUMENTS: '/knowledge-bases/:id/documents',
    DOCUMENT_DELETE: '/knowledge-bases/:id/documents/:documentId',
    REPROCESS: '/knowledge-bases/:id/reprocess',
    EXPORT: '/knowledge-bases/:id/export',
    SHARE: '/knowledge-bases/:id/share',
    UNSHARE: '/knowledge-bases/:id/share/:userId',
  },
  // 记忆库管理
  MEMORY_BASES: {
    CREATE: '/memory/repo/create',
    LIST: '/memory/repo/list',
    DETAIL: '/memory-bases/:id/detail',
    UPDATE: '/memory/repo/update',
    DELETE: '/memory/repo/delete',
    UPLOAD: '/memory-bases/upload',
    GET_REFERENCING_AGENTS: '/memory-bases/referencing-agents',
    BATCH_ADD: '/memory-bases/memories/batch-add',
    MEMORIES_LIST: '/memory-bases/memories/list',
    PROCESS: '/memory-bases/memories/process',
    STATUS: '/memory-bases/memories/status',
    SEARCH: '/memory/repo/search',
    SETTINGS: '/memory-base/settings',
    CLEAN_EXPIRED: '/memory-bases/memories/clean-expired'
  }
}

// HTTP状态码常量
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
} as const

// 错误类型常量
export const ERROR_TYPES = {
  NETWORK: 'NETWORK_ERROR',
  AUTH: 'AUTH_ERROR',
  VALIDATION: 'VALIDATION_ERROR',
  SERVER: 'SERVER_ERROR',
  TIMEOUT: 'TIMEOUT_ERROR',
  UNKNOWN: 'UNKNOWN_ERROR',
} as const
