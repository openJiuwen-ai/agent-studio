// 知识库相关类型定义

// 创建知识库请求 (V2)
export interface CreateKnowledgeBaseRequest {
  space_id: string
  name: string
  description?: string
  embedding_model_config_id: number // Embedding 模型配置ID（必填）
  config?: Record<string, any>
}

// 创建知识库响应 (V2)
export interface CreateKnowledgeBaseResponse {
  id: string
}

// 获取知识库列表请求
export interface GetKnowledgeBasesRequest {
  space_id: string
  page: number
  size: number
}

// 知识库列表项
export interface KnowledgeBaseItem {
  name: string
  desc: string
  id: string
  type: string
  embedding_model_config_id?: number
  created_at: string
  updated_at: string
  // DeepSearch 知识库 ID，未同步则为 null
  ds_kb_id?: string | null
  // 知识库状态：indexed=已就绪，其他=处理中/失败
  status?: string
}

// 搜索结果知识库项
export interface SearchKnowledgeBaseItem {
  id: string
  space_id: string
  name: string
  description: string
  embedding_model_config_id?: number
  config?: Record<string, any>
  create_time: number
  update_time: number
}

// 获取知识库列表响应
export interface GetKnowledgeBasesResponse {
  code: number
  message: string
  data: {
    items: KnowledgeBaseItem[]
    total: number
    page: number
    size: number
  }
}

// 知识库基础信息
export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  type: 'document' | 'weblink' | 'web' | 'api' | 'database'
  status: 'active' | 'processing' | 'error' | 'inactive'
  documentCount: number
  size: number
  space_id: string
  created_at: string
  updated_at: string
  created_by: string
}

// 更新知识库请求
export interface UpdateKnowledgeBaseRequest {
  space_id: string
  kb_id: string
  name: string
  desc: string
}

// 更新知识库响应
export interface UpdateKnowledgeBaseResponse {
  code: number
  message: string
}

// 文档项类型
export interface DocumentItem {
  name: string
  id: string
  created_at: string
  updated_at: string
}

// 获取文档列表请求
export interface GetDocumentsListRequest {
  space_id: string
  kb_id: string
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
  kb_id: string
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
  kb_id: string
  document_ids: string[]
}

// 删除文档响应
export interface DeleteDocumentsResponse {
  code: number
  message: string
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
  llm_model_id?: number
}

// 文档处理请求
export interface ProcessDocumentsRequest {
  space_id: string
  kb_id: string
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
  kb_id: string
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

// 删除知识库请求
export interface DeleteKnowledgeBaseRequest {
  space_id: string
  kb_id: string
}

// 删除知识库响应（data.deleted_kb_ids 为本次删除涉及的所有 kb_id，供前端从列表移除对应卡片）
export interface DeleteKnowledgeBaseResponse {
  code: number
  message: string
  data: { deleted_kb_ids?: string[] } | null
}

// 获取知识库详情请求
export interface GetKnowledgeBaseDetailRequest {
  id: string
  space_id: string
}

// 获取知识库详情响应
export interface GetKnowledgeBaseDetailResponse {
  code: number
  message: string
  data: KnowledgeBase
}

// 上传文件请求
export interface UploadFilesRequest {
  files: File[]
  space_id: string
  kb_id: string
  metadata?: string
}

// 上传文件响应
export interface UploadFilesResponse {
  code: number
  message: string
  data?: string[] // 上传成功的文件ID列表
}

// 文件设置请求
export interface FileSettingsRequest {
  space_id: string
  kb_id: string
  file_id_list: string[]
  parsing_strategy: {
    strategy_type: string
    strategy_config: Record<string, any>
  }
  segmentation_strategy: {
    strategy_type: string
    strategy_config: {
      separator?: string
      max_tokens?: number
      remove_extra_spaces?: boolean
      remove_urls_emails?: boolean
    }
  }
  indexing_strategy: {
    ennabele_graph_enhancement: boolean
  }
}

// 文件设置响应
export interface FileSettingsResponse {
  code: number
  message: string
  data: null
}

// 搜索知识库请求
export interface SearchKnowledgeBaseRequest {
  space_id: string
  query: string
  page?: number
  page_size?: number
}

// 搜索知识库响应
export interface SearchKnowledgeBaseResponse {
  code: number
  message: string
  data: {
    knowledge_bases: SearchKnowledgeBaseItem[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}

// Weblink 相关类型
export interface WeblinkItem {
  name: string
  id: string
  url: string
  created_at: string
  updated_at: string
}

export interface AddWeblinksRequest {
  space_id: string
  kb_id: string
  urls: string[]
}

export interface AddWeblinksResponse {
  code: number
  message: string
  data: {
    success_count: number
    failed_count: number
    links: Array<{ id: string; url: string; name: string; status: string }>
  }
}

export interface GetWeblinksListRequest {
  space_id: string
  kb_id: string
  page: number
  size: number
}

export interface GetWeblinksListResponse {
  code: number
  message: string
  data: {
    items: WeblinkItem[]
    total: number
    page: number
    size: number
  }
}

export interface ProcessWeblinksRequest {
  space_id: string
  kb_id: string
  weblink_id_list: string[]
  parsing_strategy: ParsingStrategy
  segmentation_strategy: SegmentationStrategy
  indexing_strategy: IndexingStrategy
}

export interface ProcessWeblinksResponse {
  code: number
  message: string
  data: {
    task_id: string
    processed_count: number
    failed_count: number
    failed_links: string[]
  }
}

export interface UpdateWeblinkRequest {
  space_id: string
  kb_id: string
  weblink_id: string
  weblink_name: string
}

export interface DeleteWeblinksRequest {
  space_id: string
  kb_id: string
  weblink_ids: string[]
}

export interface GetWeblinkStatusRequest {
  space_id: string
  kb_id: string
  weblink_id_list: string[]
  refresh_names?: boolean
}

// 同步至 DeepSearch - 上传请求/响应
export interface SyncUploadRequest {
  space_id: string
  kb_id: string
  /** DeepSearch 侧嵌入模型配置 ID，同步时在 Deep Search 创建知识库使用 */
  deepsearch_embedding_model_config_id?: number | null
}

export interface SyncUploadResponse {
  code: number
  message: string
  data?: { ds_kb_id: string; uploaded_count: number; doc_id_list?: string[] }
}

// 同步至 DeepSearch - 处理/建索引请求
export interface SyncProcessRequest {
  space_id: string
  ds_kb_id: string
  /** Studio 源知识库 ID */
  studio_kb_id?: string
  /** 建索引前服务端会再次探测 Embedding API 并刷新 DS 配置 */
  deepsearch_embedding_model_config_id?: number
  /** 可为空：无可索引文档时服务端跳过 DeepSearch process */
  doc_id_list: string[]
  parsing_strategy?: { strategy_type: string; strategy_config?: Record<string, unknown> }
  segmentation_strategy?: { strategy_type: string; strategy_config: Record<string, unknown> }
  indexing_strategy?: { enable_graph_enhancement?: boolean; llm_model_id?: number }
}

export interface SyncProcessResponse {
  code: number
  message: string
  data?: {
    task_id?: string
    processed_count?: number
    failed_count?: number
    failed_docs?: string[]
    skipped?: boolean
  }
}

// DeepSearch 知识库列表请求
export interface DeepSearchKnowledgeBaseListRequest {
  space_id: string
  page: number
  size: number
}

export interface DeepSearchKnowledgeBaseListItem {
  id: string
  name: string
  desc?: string
  status?: string
  created_at?: string
  updated_at?: string
}

export interface DeepSearchKnowledgeBaseListResponse {
  code: number
  message: string
  data?: {
    items?: DeepSearchKnowledgeBaseListItem[]
    total?: number
    page?: number
    size?: number
  }
}

// DeepSearch 侧 Embedding 配置列表（供同步时选择嵌入模型）
export interface DeepSearchEmbeddingConfigListRequest {
  space_id: string
  page?: number
  size?: number
}

export interface DeepSearchEmbeddingConfigListItem {
  id: number
  model_name: string
}

export interface DeepSearchEmbeddingConfigListResponse {
  code: number
  message: string
  data?: {
    items?: DeepSearchEmbeddingConfigListItem[]
    total?: number
    page?: number
    size?: number
  }
}

export interface DeepSearchRuntimeConfigRequest {
  space_id: string
  kb_id: string
}

export interface DeepSearchRuntimeConfigResponse {
  code: number
  message: string
  data?: {
    retrieve_config?: {
      milvus_host?: string
      milvus_port?: number
      database_name?: string
      collection_name?: string
      embedder_model_name?: string
      embedder_api_key?: string | null
      embedder_base_url?: string
      embedder_timeout?: number
    }
  }
}
