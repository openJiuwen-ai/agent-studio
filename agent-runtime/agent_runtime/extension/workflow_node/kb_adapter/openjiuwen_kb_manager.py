# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""openjiuwen 知识库生命周期管理器 — 封装 SimpleKnowledgeBase 的创建、上传、检索、删除。

支持多种向量库后端（Milvus / Chroma / PGVector），通过 OPENJIUWEN_STORE_PROVIDER 环境变量切换。
Embedding 模型通过 model_config 参数动态解析（复用 agent_builder 模型中心）。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openjiuwen.core.foundation.store.base_embedding import EmbeddingConfig
from openjiuwen.core.foundation.store.base_reranker import RerankerConfig
from openjiuwen.core.retrieval.common.config import (
    KnowledgeBaseConfig,
    RetrievalConfig,
    StoreType,
    VectorStoreConfig,
)
from openjiuwen.core.retrieval.common.document import Document
from openjiuwen.core.retrieval.common.retrieval_result import RetrievalResult
from openjiuwen.core.retrieval.embedding.api_embedding import APIEmbedding
from openjiuwen.core.retrieval.indexing.processor.chunker import get_chunker
from openjiuwen.core.retrieval.indexing.processor.parser.auto_parser import AutoParser
from openjiuwen.core.retrieval.reranker.standard_reranker import StandardReranker
from openjiuwen.core.retrieval.simple_knowledge_base import SimpleKnowledgeBase
from openjiuwen.core.retrieval.vector_store.base import VectorStore

from agent_runtime.common.config import settings

logger = logging.getLogger(__name__)

_COLLECTION_PREFIX = "kb_"
_COLLECTION_SUFFIX = "_chunks"

_STORE_PROVIDER_MILVUS = "milvus"
_STORE_PROVIDER_CHROMA = "chroma"
_STORE_PROVIDER_PGVECTOR = "pgvector"

_DEFAULT_PROJECT_ID = "0"
_DEFAULT_INDEX_TYPE = "hybrid"


def _collection_name(kb_id: str) -> str:
    """根据 kb_id 生成 collection 名称。"""
    return f"{_COLLECTION_PREFIX}{kb_id}{_COLLECTION_SUFFIX}"


def _resolve_store_type(provider: str) -> StoreType:
    """将字符串映射为 StoreType 枚举。"""
    mapping = {
        _STORE_PROVIDER_MILVUS: StoreType.Milvus,
        _STORE_PROVIDER_CHROMA: StoreType.Chroma,
        _STORE_PROVIDER_PGVECTOR: StoreType.PGVector,
    }
    result = mapping.get(provider.lower())
    if result is None:
        raise ValueError(
            f"Unsupported store_provider: {provider}. "
            f"Available: {list(mapping.keys())}"
        )
    return result


def _validate_model_config(model_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """校验 model_config 必传且包含 model_service_id。"""
    if not model_config or not model_config.get("model_service_id"):
        raise ValueError("model_config with model_service_id is required")
    return model_config


@dataclass
class KBSearchOptions:
    """知识库检索可选参数。"""

    model_config: Optional[Dict[str, Any]] = None
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None
    index_type: str = "vector"
    reranker_config: Optional[Dict[str, Any]] = None


class OpenJiuwenKBManager:
    """openjiuwen 知识库管理器（单例）。

    封装 SimpleKnowledgeBase 的完整生命周期：
    create_kb → upload_documents → search → delete_kb

    向量库后端通过 OPENJIUWEN_STORE_PROVIDER 配置：
    - milvus（默认）：生产推荐，URI 设为 http://host:19530；本地开发可装 milvus-lite 后设为文件路径
    - chroma：嵌入式零依赖，OPENJIUWEN_CHROMA_PATH 指定本地存储目录
    - pgvector：需 PostgreSQL + pgvector 扩展，OPENJIUWEN_PG_URI 指定连接串

    Embedding 模型通过 model_config 参数动态解析（复用 agent_builder 模型中心）。
    """

    _instance: Optional["OpenJiuwenKBManager"] = None

    def __new__(cls) -> "OpenJiuwenKBManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        kb_settings = settings.openjiuwen_kb
        self._store_provider: str = kb_settings.store_provider.lower()
        self._distance_metric: str = kb_settings.distance_metric
        self._chunk_size: int = kb_settings.chunk_size
        self._chunk_overlap: int = kb_settings.chunk_overlap
        self._embed_model_cache: Dict[str, APIEmbedding] = {}
        self._kb_cache: Dict[str, SimpleKnowledgeBase] = {}
        self._reranker_cache: Dict[str, StandardReranker] = {}
        self._store_type: StoreType = _resolve_store_type(self._store_provider)
        self._store_kwargs: Dict[str, Any] = self._collect_store_kwargs(kb_settings)
        self._initialized = True

    @staticmethod
    def _collect_store_kwargs(kb_settings) -> Dict[str, Any]:
        """根据 store_provider 收集对应的连接参数。"""
        provider = kb_settings.store_provider.lower()
        if provider == _STORE_PROVIDER_MILVUS:
            return {
                "milvus_uri": kb_settings.milvus_uri,
                "milvus_token": kb_settings.milvus_token or None,
                "database_name": kb_settings.milvus_database,
            }
        if provider == _STORE_PROVIDER_CHROMA:
            return {"chroma_path": kb_settings.chroma_path}
        if provider == _STORE_PROVIDER_PGVECTOR:
            return {"pg_uri": kb_settings.pg_uri}
        raise ValueError(f"Unsupported store_provider: {provider}")

    async def _resolve_embedding_config(self, model_config: Dict[str, Any]) -> EmbeddingConfig:
        """通过模型中心解析 embedding 配置。"""
        from model_service import dispatch, resolver

        model_service_id = model_config.get("model_service_id", "")
        workspace_id = model_config.get("workspace_id", "")
        project_id = model_config.get("project_id", _DEFAULT_PROJECT_ID)
        auth_id = model_config.get("auth_id", "")

        strategy = await resolver.resolve_strategy(
            model_service_id, project_id, workspace_id, auth_id, refresh=False,
        )
        if strategy is None:
            raise ValueError(f"Model service not found: {model_service_id}")

        detail = strategy.models[0]
        conn = dispatch.get_chat_connection(detail.model, detail.auth)
        return EmbeddingConfig(
            model_name=conn.model_name,
            base_url=detail.model.api_url,
            api_key=conn.api_key,
        )

    def _get_embed_model(self, kb_id: str, embed_config: EmbeddingConfig) -> APIEmbedding:
        """获取或创建 KB 级 Embedding 实例。"""
        if kb_id not in self._embed_model_cache:
            self._embed_model_cache[kb_id] = APIEmbedding(config=embed_config)
        return self._embed_model_cache[kb_id]

    async def _resolve_reranker_config(self, model_config: Dict[str, Any]) -> RerankerConfig:
        """通过模型中心解析 reranker 配置。"""
        from model_service import dispatch, resolver

        model_service_id = model_config.get("model_service_id", "")
        workspace_id = model_config.get("workspace_id", "")
        project_id = model_config.get("project_id", _DEFAULT_PROJECT_ID)
        auth_id = model_config.get("auth_id", "")

        strategy = await resolver.resolve_strategy(
            model_service_id, project_id, workspace_id, auth_id, refresh=False,
        )
        if strategy is None:
            raise ValueError(f"Reranker model service not found: {model_service_id}")

        detail = strategy.models[0]
        conn = dispatch.get_chat_connection(detail.model, detail.auth)
        return RerankerConfig(
            api_base=detail.model.api_url,
            model_name=conn.model_name,
            api_key=conn.api_key,
        )

    async def _get_reranker(self, kb_id: str, reranker_config: Dict[str, Any]) -> StandardReranker:
        """获取或创建 KB 级 Reranker 实例。"""
        if kb_id not in self._reranker_cache:
            config = await self._resolve_reranker_config(reranker_config)
            self._reranker_cache[kb_id] = StandardReranker(config=config)
        return self._reranker_cache[kb_id]

    def _build_vector_store_config(self, kb_id: str) -> VectorStoreConfig:
        """构建 VectorStoreConfig。"""
        database_name = self._store_kwargs.get("database_name", "")
        return VectorStoreConfig(
            store_provider=self._store_type,
            collection_name=_collection_name(kb_id),
            database_name=database_name,
            distance_metric=self._distance_metric,
        )

    def _create_vector_store(self, vs_config: VectorStoreConfig) -> VectorStore:
        """根据 store_provider 创建 VectorStore 实例。"""
        if self._store_provider == _STORE_PROVIDER_MILVUS:
            from openjiuwen.core.retrieval.vector_store.milvus_store import MilvusVectorStore

            return MilvusVectorStore(
                config=vs_config,
                milvus_uri=self._store_kwargs["milvus_uri"],
                milvus_token=self._store_kwargs["milvus_token"],
            )
        if self._store_provider == _STORE_PROVIDER_CHROMA:
            from openjiuwen.core.retrieval.vector_store.chroma_store import ChromaVectorStore

            return ChromaVectorStore(
                config=vs_config,
                chroma_path=self._store_kwargs["chroma_path"],
            )
        if self._store_provider == _STORE_PROVIDER_PGVECTOR:
            from openjiuwen.core.retrieval.vector_store.pg_store import PGVectorStore

            return PGVectorStore(
                config=vs_config,
                pg_uri=self._store_kwargs["pg_uri"],
            )
        raise ValueError(f"Unsupported store_provider: {self._store_provider}")

    def _create_indexer(self, vs_config: VectorStoreConfig):
        """根据 store_provider 创建 Indexer 实例。"""
        if self._store_provider == _STORE_PROVIDER_MILVUS:
            from openjiuwen.core.retrieval.indexing.indexer.milvus_indexer import MilvusIndexer

            return MilvusIndexer(
                config=vs_config,
                milvus_uri=self._store_kwargs["milvus_uri"],
                milvus_token=self._store_kwargs["milvus_token"],
            )
        if self._store_provider == _STORE_PROVIDER_CHROMA:
            from openjiuwen.core.retrieval.indexing.indexer.chroma_indexer import ChromaIndexer

            return ChromaIndexer(
                config=vs_config,
                chroma_path=self._store_kwargs["chroma_path"],
            )
        if self._store_provider == _STORE_PROVIDER_PGVECTOR:
            from openjiuwen.core.retrieval.indexing.indexer.milvus_indexer import MilvusIndexer

            logger.warning("PGVector indexer not yet supported, falling back to Milvus indexer")
            return MilvusIndexer(
                config=vs_config,
                milvus_uri=self._store_kwargs["pg_uri"],
            )
        raise ValueError(f"Unsupported store_provider: {self._store_provider}")

    def _build_kb(
        self,
        kb_id: str,
        embed_model: APIEmbedding,
        index_type: str = _DEFAULT_INDEX_TYPE,
    ) -> SimpleKnowledgeBase:
        """构建 SimpleKnowledgeBase 实例（含 VectorStore + Indexer + Chunker + Parser）。"""
        vs_config = self._build_vector_store_config(kb_id)
        vector_store = self._create_vector_store(vs_config)
        index_manager = self._create_indexer(vs_config)
        kb_config = KnowledgeBaseConfig(
            kb_id=kb_id,
            index_type=index_type,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        chunker = get_chunker(
            "hybrid",
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        parser = AutoParser()

        return SimpleKnowledgeBase(
            config=kb_config,
            vector_store=vector_store,
            index_manager=index_manager,
            embed_model=embed_model,
            chunker=chunker,
            parser=parser,
        )

    async def _get_or_build_kb(
        self,
        kb_id: str,
        model_config: Optional[Dict[str, Any]] = None,
        index_type: str = _DEFAULT_INDEX_TYPE,
    ) -> SimpleKnowledgeBase:
        """从缓存获取 KB，或解析模型配置后构建新 KB。

        若 KB 已缓存但 index_type 不同，更新检索模式以支持动态切换。
        """
        kb = self._kb_cache.get(kb_id)
        if kb is not None:
            if kb.config.index_type != index_type:
                kb.config.index_type = index_type
                kb.retriever = None
            return kb
        _validate_model_config(model_config)
        embed_config = await self._resolve_embedding_config(model_config)
        embed_model = self._get_embed_model(kb_id, embed_config)
        kb = self._build_kb(kb_id, embed_model=embed_model, index_type=index_type)
        self._kb_cache[kb_id] = kb
        return kb

    async def create_kb(
        self,
        kb_id: str,
        model_config: Dict[str, Any],
        kb_name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """创建知识库（在向量库中创建对应 collection）。"""
        _validate_model_config(model_config)
        if kb_id in self._kb_cache:
            logger.info("KB '%s' already cached, skipping creation", kb_id)
            return {"success": True, "message": "KB already exists"}

        embed_config = await self._resolve_embedding_config(model_config)
        embed_model = self._get_embed_model(kb_id, embed_config)
        kb = self._build_kb(kb_id, embed_model=embed_model)
        self._kb_cache[kb_id] = kb
        logger.info("Created KB '%s' (name=%s, store=%s)", kb_id, kb_name, self._store_provider)
        return {"success": True, "message": "KB created successfully"}

    async def upload_documents(
        self,
        kb_id: str,
        file_paths: List[str],
        model_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """上传文档到知识库：Parser → Chunker → Embedding → VectorStore。"""
        kb = await self._get_or_build_kb(kb_id, model_config)

        parser = AutoParser()
        all_docs: List[Document] = []
        for file_path in file_paths:
            docs = await parser.parse(doc=file_path)
            all_docs.extend(docs)

        if not all_docs:
            return {"success": False, "doc_count": 0, "message": "No documents parsed"}

        doc_ids = await kb.add_documents(all_docs)
        logger.info("Uploaded %d documents (%d chunks) to KB '%s'", len(all_docs), len(doc_ids), kb_id)
        return {
            "success": True,
            "doc_count": len(all_docs),
            "message": f"Uploaded {len(all_docs)} documents",
        }

    async def search(
        self,
        kb_id: str,
        query: str,
        options: Optional[KBSearchOptions] = None,
    ) -> List[Dict[str, Any]]:
        """检索知识库：query → embedding → vector search → [rerank] → top_k results。"""
        opts = options or KBSearchOptions()
        kb = await self._get_or_build_kb(kb_id, opts.model_config, index_type=opts.index_type)

        retrieval_config = RetrievalConfig(top_k=opts.top_k, filters=opts.filters)
        results: List[RetrievalResult] = await kb.retrieve(
            query=query,
            config=retrieval_config,
        )

        if opts.reranker_config and results:
            try:
                reranker = await self._get_reranker(kb_id, opts.reranker_config)
                doc_texts = [r.text for r in results]
                scores = await reranker.rerank(query=query, doc=doc_texts)
                for r in results:
                    r.score = scores.get(r.text, 0.0)
            except Exception as e:
                logger.warning("Rerank failed for KB '%s', using original scores: %s", kb_id, e)

        results.sort(key=lambda r: r.score, reverse=True)
        return [
            {
                "text": r.text,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results[:opts.top_k]
        ]

    async def delete_kb(self, kb_id: str) -> Dict[str, Any]:
        """删除知识库（删除 collection + 清理缓存）。"""
        collection = _collection_name(kb_id)

        vs_config = self._build_vector_store_config(kb_id)
        vector_store = self._create_vector_store(vs_config)
        try:
            await vector_store.delete_table(collection)
        except Exception as e:
            logger.warning("Failed to delete collection '%s': %s", collection, e)

        self._kb_cache.pop(kb_id, None)
        self._embed_model_cache.pop(kb_id, None)
        self._reranker_cache.pop(kb_id, None)
        logger.info("Deleted KB '%s'", kb_id)
        return {"success": True, "message": "KB deleted successfully"}

    async def list_kbs(self, kb_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """列出知识库存在状态。"""
        if kb_ids is None:
            return [{"kb_id": kb_id, "exists": True} for kb_id in self._kb_cache]

        results = []
        for kb_id in kb_ids:
            vs_config = self._build_vector_store_config(kb_id)
            vs = self._create_vector_store(vs_config)
            exists = await vs.table_exists(_collection_name(kb_id))
            results.append({"kb_id": kb_id, "exists": exists})
        return results
