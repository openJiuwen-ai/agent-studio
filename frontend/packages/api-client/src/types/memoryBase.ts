// 记忆库相关类型定义

// 创建记忆库请求 (V2)
export interface CreateMemoryBaseRequest {
  space_id: string
  name: string
  description?: string
  embedding_model_config_id: number // Embedding 模型配置ID（必填）
  llm_model_config_id: number // LLM 模型ID (记忆库专用)
}
// 文档处理策略配置
export interface ParsingStrategy {
  strategy_type: string
  strategy_config?: Record<string, any>
}

export interface SegmentationStrategy {
  strategy_type: string
  strategy_config: {
    max_tokens?: number
    chunk_overlap_percent?: number
  }
}

export interface IndexingStrategy {
  enable_graph_enhancement?: boolean
  llm_model_config_id?: number
}
// 文档项类型
export interface DocumentItem {
  id: string;
  name: string;
  memoryBaseId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  updatedAt: string;
  size: number;
  type: string;
}

// 获取文档列表请求
export interface GetDocumentsListRequest {
  space_id: string
  mb_id: string
  page: number
  size: number
}

// 获取文档列表响应
export interface GetDocumentsListResponse {
  code: number
  message: string
  data: {
    items: DocumentItem[]
    total: number
    page: number
    size: number
  }
}

// 更新文档请求
export interface UpdateDocumentRequest {
  space_id: string
  mb_id: string
  document_id: string
  document_name: string
}

// 更新文档响应
export interface UpdateDocumentResponse {
  code: number
  message: string
}

// 删除文档请求
export interface DeleteDocumentsRequest {
  space_id: string
  mb_id: string
  document_ids: string[]
}

// 删除文档响应
export interface DeleteDocumentsResponse {
  code: number
  message: string
}
// 文档处理请求
export interface ProcessDocumentsRequest {
  space_id: string
  mb_id: string
  doc_id_list: string[]
  parsing_strategy: ParsingStrategy
  segmentation_strategy: SegmentationStrategy
  indexing_strategy: IndexingStrategy
}

// 文档处理响应
export interface ProcessDocumentsResponse {
  code: number
  message: string
  data: {
    task_id: string
    processed_count: number
    failed_count: number
    failed_docs: string[]
  }
}

// 文档状态项
export interface DocumentStatusItem {
  id: string
  doc_id?: string // 文档ID
  status: string
  name?: string
  error_msg?: string // 错误信息
}

// 查询文档状态请求
export interface GetDocumentStatusRequest {
  space_id: string
  mb_id: string
  doc_id_list: string[]
}

// 查询文档状态响应
export interface GetDocumentStatusResponse {
  code: number
  message: string
  data: {
    items: DocumentStatusItem[]
  }
}
// 创建记忆库响应 (V2)
export interface CreateMemoryBaseResponse {
  mdb_id: string
}

// 获取记忆库列表请求
export interface GetMemoryBasesRequest {
  space_id: string
  page: number
  page_size: number
}

// 记忆库列表项
export interface MemoryBaseItem {
  mdb_id: string;
  name: string;
  description?: string;
  status: 'active' | 'processing' | 'error' | 'inactive';
  space_id: string;
  created_at: string;
  updated_at: string;
  embedding_model_config_id: number; // Embedding 模型配置ID
  llm_model_config_id: number; // LLM 模型ID (记忆库专用)
}

// 搜索结果记忆库项
export interface SearchMemoryBaseItem {
  mdb_id: string
  space_id: string
  name: string
  description: string
  embedding_model_config_id: number
  llm_model_config_id: number
  create_time: number
  update_time: number
}

// 获取记忆库列表响应
export interface GetMemoryBasesResponse {
  code: number
  message: string
  data: {
    items: MemoryBaseItem[]
    total: number
    page: number
    size: number
  }
}

// 记忆库基础信息
export interface MemoryBase {
  mdb_id: string
  name: string
  description?: string
  status: 'active' | 'processing' | 'error' | 'inactive'
  size: number
  space_id: string
  created_at: string
  updated_at: string
  embedding_model_config_id: number // Embedding 模型配置ID
  llm_model_config_id: number // LLM 模型ID (记忆库专用)
}

// 更新记忆库请求
export interface UpdateMemoryBaseRequest {
  space_id: string
  mdb_id?: string
  name: string
  description?: string
  llm_model_config_id?: number // 可更新记忆库配置
}

// 更新记忆库响应
export interface UpdateMemoryBaseResponse {
  code: number
  message: string
}

// 记忆条目类型
export interface MemoryItem {
  name: string // 记忆条目名称
  id: string
  mb_id: string
  content: string // 记忆内容
  created_at: string
  updated_at: string
  type: string
  expire_time?: string // 记忆条目过期时间
}

// 获取记忆条目列表请求
export interface GetMemoriesListRequest {
  space_id: string
  mb_id: string
  page: number
  size: number
  expire_status?: 'valid' | 'expired' // 筛选：有效/过期记忆
}

// 获取记忆条目列表响应
export interface GetMemoriesListResponse {
  code: number
  message: string
  data: {
    items: MemoryItem[]
    total: number
    page: number
    size: number
  }
}

// 更新记忆条目请求
export interface UpdateMemoryRequest {
  space_id: string
  mb_id: string
  memory_id: string
  memory_name: string
  content: string // 更新记忆内容
  expire_time?: string // 更新过期时间
}

// 更新记忆条目响应
export interface UpdateMemoryResponse {
  code: number
  message: string
}

// 删除记忆条目请求
export interface DeleteMemoriesRequest {
  space_id: string
  mb_id: string
  memory_ids: string[]
}

// 删除记忆条目响应
export interface DeleteMemoriesResponse {
  code: number
  message: string
}

// 记忆处理策略配置（解析/分割/索引）
export interface MemoryParsingStrategy {
  strategy_type: string // 记忆内容解析策略（文本/结构化数据）
  strategy_config?: Record<string, any>
}

export interface MemorySegmentationStrategy {
  strategy_type: string
  strategy_config: {
    max_tokens?: number // 最大Token数
    chunk_overlap_percent?: number // 重叠百分比
  }
}

export interface MemoryIndexingStrategy {
  enable_graph_enhancement?: boolean // 是否启用图谱增强
  llm_model_config_id?: number // LLM模型ID
}

// 处理记忆条目请求
export interface ProcessMemoriesRequest {
  space_id: string
  mb_id: string
  memory_id_list: string[]
  parsing_strategy: MemoryParsingStrategy
  segmentation_strategy: MemorySegmentationStrategy
  indexing_strategy: MemoryIndexingStrategy
}

// 处理记忆条目响应
export interface ProcessMemoriesResponse {
  code: number
  message: string
  data: {
    task_id: string
    processed_count: number
    failed_count: number
    failed_memories: string[]
  }
}

// 记忆状态项
export interface MemoryStatusItem {
  id: string
  memory_id?: string // 记忆ID
  status: string // 处理状态（processing/success/error）
  name?: string
  error_msg?: string // 错误信息
}

// 查询记忆状态请求
export interface GetMemoryStatusRequest {
  space_id: string
  mb_id: string
  memory_id_list: string[]
}

// 查询记忆状态响应
export interface GetMemoryStatusResponse {
  code: number
  message: string
  data: {
    items: MemoryStatusItem[]
  }
}

// 删除记忆库请求
export interface DeleteMemoryBaseRequest {
  space_id: string
  mdb_id: string
}

// 删除记忆库响应
export interface DeleteMemoryBaseResponse {
  code: number
  message: string
  data: null
}

// 获取记忆库详情请求
export interface GetMemoryBaseDetailRequest {
  id: string
  space_id: string
}

// 获取记忆库详情响应
export interface GetMemoryBaseDetailResponse {
  code: number
  message: string
  data: MemoryBase
}

// 批量添加记忆条目请求
export interface BatchAddMemoriesRequest {
  space_id: string
  mb_id: string
  memories: Array<{
    name: string
    content: string
    expire_time?: string
    metadata?: Record<string, any>
  }>
}

// 批量添加记忆条目响应
export interface BatchAddMemoriesResponse {
  code: number
  message: string
  data?: string[] // 添加成功的记忆ID列表
}

// 搜索记忆库请求
export interface SearchMemoryBaseRequest {
  space_id: string
  query: string
  page?: number
  page_size?: number
  memory_type?: 'short-term' | 'long-term' | 'temporary' // 筛选记忆类型
}

// 搜索记忆库响应
export interface SearchMemoryBaseResponse {
  code: number
  message: string
  data: {
    memory_bases: SearchMemoryBaseItem[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}

// 清理过期记忆请求
export interface CleanExpiredMemoriesRequest {
  space_id: string
  mb_id: string
}

// 清理过期记忆响应
export interface CleanExpiredMemoriesResponse {
  code: number
  message: string
  data: {
    cleaned_count: number // 清理的过期记忆数量
  }
}