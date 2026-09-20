"""LongTermMemoryDefaultIndex — 6-field OpenSearch index for long-term memory.

A `BaseMemoryIndex` implementation that stores memory documents in a single
global OpenSearch index (default `long_term_memory_default`), mirroring the
legacy memory-service schema:

    user_id        keyword   用户标识
    app_id         keyword   记忆库 ID (scope_id)
    memory_type    keyword   记忆类型 (新版枚举: user_profile/semantic_memory/...)
    content_vector knn_vector 记忆正文向量 (dim 由 embedding 模型决定)
    content        text      记忆正文原文 (index=False, doc_values=False)
    last_updated   long      更新时间 (毫秒)

与 SDK 自带的 `SimpleMemoryIndex` 不同，正文存储在 OpenSearch 的 `content`
字段（与向量同文档，原子写入），不再写入 Redis KV。检索时一次 OpenSearch
KNN 查询即可返回正文，无需二次查 Redis。

memory_type 存新版枚举值（user_profile/semantic_memory/episodic_memory/
summary/variable），与 agent-core 抽取产出一致。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from openjiuwen.core.foundation.store.base_memory_index import BaseMemoryIndex, MemoryDoc
from openjiuwen.core.common.logging import memory_logger as _mem_logger

from agent_runtime.memory.adapter.opensearch_vector_store import OpenSearchVectorStore

logger = logging.getLogger(__name__)

# OpenSearch 字段名
FIELD_USER_ID = "user_id"
FIELD_APP_ID = "app_id"
FIELD_MEMORY_TYPE = "memory_type"
FIELD_CONTENT_VECTOR = "content_vector"
FIELD_CONTENT = "content"
FIELD_LAST_UPDATED = "last_updated"

DEFAULT_INDEX_NAME = "long_term_memory_default"


def _build_index_mapping(dim: int) -> dict:
    """构建 6 字段索引 mapping。"""
    return {
        "properties": {
            FIELD_USER_ID: {"type": "keyword"},
            FIELD_APP_ID: {"type": "keyword"},
            FIELD_MEMORY_TYPE: {"type": "keyword"},
            FIELD_CONTENT_VECTOR: {
                "type": "knn_vector",
                "dimension": dim,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "faiss",
                },
            },
            FIELD_CONTENT: {"type": "text", "index": False, "doc_values": False},
            FIELD_LAST_UPDATED: {"type": "long"},
        }
    }


def _build_filter(user_id: str, scope_id: str, mem_type: Optional[str] = None) -> dict:
    """构建 OpenSearch term 过滤条件。user_id 不转小写（与现网一致）。"""
    filters = {FIELD_USER_ID: user_id, FIELD_APP_ID: scope_id}
    if mem_type:
        filters[FIELD_MEMORY_TYPE] = mem_type
    return filters


def _doc_to_store_doc(doc: MemoryDoc, user_id: str, scope_id: str, embedding: list[float]) -> dict:
    """MemoryDoc → OpenSearch 6 字段文档。"""
    ts = doc.timestamp
    if ts is None:
        ts = datetime.now(timezone.utc)
    last_updated = int(ts.timestamp() * 1000)
    return {
        FIELD_USER_ID: user_id,
        FIELD_APP_ID: scope_id,
        FIELD_MEMORY_TYPE: doc.type,
        FIELD_CONTENT: doc.text,
        FIELD_CONTENT_VECTOR: embedding,
        FIELD_LAST_UPDATED: last_updated,
    }


def _store_doc_to_memory_doc(fields: dict, mem_id: str) -> MemoryDoc:
    """OpenSearch 文档 → MemoryDoc。"""
    last_updated = fields.get(FIELD_LAST_UPDATED)
    timestamp = None
    if last_updated:
        try:
            timestamp = datetime.fromtimestamp(last_updated / 1000.0, tz=timezone.utc)
        except (ValueError, OSError):
            timestamp = None
    return MemoryDoc(
        id=mem_id,
        text=fields.get(FIELD_CONTENT, ""),
        type=fields.get(FIELD_MEMORY_TYPE, ""),
        timestamp=timestamp,
    )


class LongTermMemoryDefaultIndex(BaseMemoryIndex):
    """6 字段 OpenSearch 索引实现，正文存 OpenSearch，不写 Redis 正文。"""

    def __init__(
        self,
        vector_store: OpenSearchVectorStore,
        embedding_model: Any,
        index_name: str = DEFAULT_INDEX_NAME,
    ):
        self._vector_store = vector_store
        self._embedding_model = embedding_model
        self._index_name = index_name
        self._dim: Optional[int] = None
        self._index_ensured = False
        self._codec: Any = None
        self._schema_version = 0

    # ------------------------------------------------------------------ #
    #  索引初始化                                                          #
    # ------------------------------------------------------------------ #

    async def _ensure_index(self, dim: int) -> None:
        """确保索引存在，按 6 字段 mapping 创建（若不存在）。

        防御：``_index_ensured`` 标志只代表"本进程曾建过索引"，不代表索引当前仍存在
        （可能被外部删除，如 UI"删除全部"按钮）。因此标志为 True 时仍需校验索引真实
        存在，否则后续 ``add_docs`` 会因索引不存在触发 OpenSearch 动态映射，把
        ``content_vector`` 建成 ``float`` 而非 ``knn_vector``，导致 knn 检索失败。
        """
        if self._index_ensured and self._dim == dim:
            # 标志为 True，但索引可能已被外部删除，必须校验真实存在
            if await self._index_exists():
                return
            # 索引被外部删除，重置标志并重建（按正确 knn_vector mapping）
            _mem_logger.warning(
                "Index %s was removed externally; recreating with knn_vector mapping",
                self._index_name,
            )
            self._index_ensured = False
        self._dim = dim
        mapping = _build_index_mapping(dim)
        settings = {"index": {"knn": True}}
        await self._vector_store.create_index_with_mapping(
            self._index_name, mappings=mapping, settings=settings
        )
        self._index_ensured = True

    async def _index_exists(self) -> bool:
        """检查索引是否存在（读方法在索引不存在时优雅返回空）。"""
        try:
            return await self._vector_store.collection_exists(self._index_name)
        except Exception:
            return False

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化。返回向量列表。"""
        if self._embedding_model is None:
            raise RuntimeError(
                "embedding model not initialized — cannot vectorize memory content"
            )
        return await self._embedding_model.embed_documents(texts)

    async def _embed_query(self, query: str) -> list[float]:
        if self._embedding_model is None:
            raise RuntimeError(
                "embedding model not initialized — cannot vectorize query"
            )
        return await self._embedding_model.embed_query(query)

    def set_storage_codec(self, codec: Any) -> None:
        """设置正文编解码器（可选，当前实现不加密 content）。"""
        self._codec = codec

    # ------------------------------------------------------------------ #
    #  BaseMemoryIndex 抽象方法实现                                        #
    # ------------------------------------------------------------------ #

    async def add_memories(self, user_id: str, scope_id: str, memories: list[MemoryDoc]):
        """写入记忆条目（6 字段文档，含正文与向量，原子写入 OpenSearch）。"""
        if not memories:
            return
        # Filter out empty-text memories to avoid embedding errors
        memories = [m for m in memories if m.text and m.text.strip()]
        if not memories:
            return
        texts = [m.text for m in memories]
        embeddings = await self._embed(texts)
        if embeddings:
            await self._ensure_index(len(embeddings[0]))

        docs = []
        for doc, emb in zip(memories, embeddings):
            store_doc = _doc_to_store_doc(doc, user_id, scope_id, emb)
            store_doc["id"] = doc.id  # add_docs 用 id 作 OpenSearch _id
            docs.append(store_doc)
        await self._vector_store.add_docs(self._index_name, docs)

    async def update_memories(self, user_id: str, scope_id: str, memories: list[MemoryDoc]):
        """更新记忆：先删旧 ID，再写新文档（与 SimpleMemoryIndex 策略一致）。"""
        if not memories:
            return
        ids = [m.id for m in memories]
        await self.delete_memories(user_id, scope_id, ids)
        await self.add_memories(user_id, scope_id, memories)

    async def delete_memories(self, user_id: str, scope_id: str, ids: list[str]):
        """按 ID 删除记忆（限定 user+scope 防越权）。"""
        if not ids:
            return
        if not await self._index_exists():
            return
        # 先按 user+scope+id 精确过滤再删（delete_docs_by_ids 不带 scope 限制）
        filters = _build_filter(user_id, scope_id)
        must = [{"term": {k: v}} for k, v in filters.items()]
        body = {
            "query": {
                "bool": {
                    "filter": must,
                    "must": [{"terms": {"_id": [str(i) for i in ids]}}],
                }
            }
        }
        await self._vector_store.delete_by_query(self._index_name, body)

    async def delete_by_user(self, user_id: str):
        """删除某用户所有记忆（跨所有 scope）。"""
        if not await self._index_exists():
            return
        body = {"query": {"term": {FIELD_USER_ID: user_id}}}
        await self._vector_store.delete_by_query(self._index_name, body)

    async def delete_by_scope(self, scope_id: str):
        """删除某记忆库所有记忆（跨所有用户）。"""
        if not await self._index_exists():
            return
        body = {"query": {"term": {FIELD_APP_ID: scope_id}}}
        await self._vector_store.delete_by_query(self._index_name, body)

    async def delete_by_user_and_scope(self, user_id: str, scope_id: str):
        """清空某用户在某记忆库的所有记忆。"""
        if not await self._index_exists():
            return
        filters = _build_filter(user_id, scope_id)
        await self._vector_store.delete_docs_by_filters(self._index_name, filters)

    async def search(
        self,
        user_id: str,
        scope_id: str,
        query: str,
        mem_types: list[str] | None = None,
        top_k: int = 10,
    ) -> list[tuple[MemoryDoc, float]]:
        """向量检索：query→embedding→KNN+filter，一次返回正文。"""
        if not query:
            return []
        if not await self._index_exists():
            return []
        query_vec = await self._embed_query(query)
        filters = _build_filter(user_id, scope_id)
        # mem_types 过滤：单类型用 term，多类型用 terms
        if mem_types:
            if len(mem_types) == 1:
                filters[FIELD_MEMORY_TYPE] = mem_types[0]
            else:
                # search 方法签名 filters 是 dict，多值需特殊处理；这里退化为逐类型查询
                results: list[tuple[MemoryDoc, float]] = []
                for mt in mem_types:
                    f = {**filters, FIELD_MEMORY_TYPE: mt}
                    hits = await self._vector_store.search(
                        self._index_name,
                        query_vec,
                        vector_field=FIELD_CONTENT_VECTOR,
                        top_k=top_k,
                        filters=f,
                    )
                    for h in hits:
                        doc = _store_doc_to_memory_doc(h.fields, h.fields.get("id", ""))
                        results.append((doc, h.score))
                results.sort(key=lambda x: x[1], reverse=True)
                return results[:top_k]

        hits = await self._vector_store.search(
            self._index_name,
            query_vec,
            vector_field=FIELD_CONTENT_VECTOR,
            top_k=top_k,
            filters=filters,
        )
        return [
            (_store_doc_to_memory_doc(h.fields, h.fields.get("id", "")), h.score)
            for h in hits
        ]

    async def get_by_id(self, user_id: str, scope_id: str, mem_id: str) -> MemoryDoc | None:
        """按 ID 取单条记忆（限定 user+scope）。"""
        if not await self._index_exists():
            return None
        filters = _build_filter(user_id, scope_id)
        must = [{"term": {k: v}} for k, v in filters.items()]
        body = {
            "size": 1,
            "query": {
                "bool": {
                    "filter": must,
                    "must": [{"ids": {"values": [str(mem_id)]}}],
                }
            },
        }
        resp = await self._vector_store.raw_search(self._index_name, body)
        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            return None
        source = hits[0]["_source"]
        source["id"] = hits[0]["_id"]
        return _store_doc_to_memory_doc(source, source.get("id", ""))

    async def list_memories(
        self,
        user_id: str,
        scope_id: str,
        offset: int = 0,
        limit: int = 100,
        mem_types: list[str] | None = None,
    ) -> list[MemoryDoc]:
        """分页列表（非向量查询，按 last_updated 倒序）。"""
        if not await self._index_exists():
            return []
        filters = _build_filter(user_id, scope_id)
        # 处理多类型：用 terms 查询
        if mem_types:
            # 单类型：过滤后直接分页，offset 只应用一次
            if len(mem_types) == 1:
                f = {**filters, FIELD_MEMORY_TYPE: mem_types[0]}
                hits = await self._vector_store.list_docs_by_filter(
                    self._index_name,
                    f,
                    offset=offset,
                    limit=limit,
                    sort=(FIELD_LAST_UPDATED, "desc"),
                )
                return [
                    _store_doc_to_memory_doc(h.fields, h.fields.get("id", ""))
                    for h in hits
                ]
            # 多类型：每类取回覆盖请求窗口的原始行（offset=0），合并排序后
            # 统一切片——若 per-type 查询各自带 offset，offset 会被应用两次，
            # page>=2 恒返回空
            docs: list[MemoryDoc] = []
            for mt in mem_types:
                f = {**filters, FIELD_MEMORY_TYPE: mt}
                hits = await self._vector_store.list_docs_by_filter(
                    self._index_name,
                    f,
                    offset=0,
                    limit=offset + limit,
                    sort=(FIELD_LAST_UPDATED, "desc"),
                )
                for h in hits:
                    docs.append(_store_doc_to_memory_doc(h.fields, h.fields.get("id", "")))
            # 多类型时按 type 顺序、时间倒序
            type_order = {mt: i for i, mt in enumerate(mem_types)}
            docs.sort(
                key=lambda d: (
                    type_order.get(d.type, len(type_order)),
                    -(d.timestamp.timestamp() if d.timestamp else 0),
                )
            )
            return docs[offset:offset + limit]

        hits = await self._vector_store.list_docs_by_filter(
            self._index_name,
            filters,
            offset=offset,
            limit=limit,
            sort=(FIELD_LAST_UPDATED, "desc"),
        )
        return [
            _store_doc_to_memory_doc(h.fields, h.fields.get("id", "")) for h in hits
        ]

    def get_schema_version(self) -> int:
        return self._schema_version

    def update_schema_version(self, version: int) -> None:
        self._schema_version = version

    async def create_backup(self) -> str:
        """创建备份标识（OpenSearch snapshot 由运维侧管理，此处仅返回占位 id）。"""
        import uuid

        return str(uuid.uuid4())

    async def restore_backup(self, backup_id: str) -> None:
        """恢复备份（由 OpenSearch snapshot 运维侧完成，此处空实现）。"""
        logger.info("restore_backup called: %s (managed by OpenSearch snapshot)", backup_id)

    async def cleanup_backup(self, backup_id: str) -> None:
        """清理备份标识。"""
        logger.info("cleanup_backup called: %s", backup_id)

    async def list_user_scopes(self) -> list[tuple[str, str]]:
        """聚合索引中所有 (user_id, app_id) 组合（迁移/管理用）。"""
        if not await self._index_exists():
            return []
        body = {
            "size": 0,
            "aggs": {
                "user_scopes": {
                    "composite": {
                        "size": 1000,
                        "sources": [
                            {FIELD_USER_ID: {"terms": {"field": FIELD_USER_ID}}},
                            {FIELD_APP_ID: {"terms": {"field": FIELD_APP_ID}}},
                        ],
                    }
                }
            },
        }
        resp = await self._vector_store.raw_search(self._index_name, body)
        buckets = (
            resp.get("aggregations", {}).get("user_scopes", {}).get("buckets", [])
        )
        return [(b["key"][FIELD_USER_ID], b["key"][FIELD_APP_ID]) for b in buckets]
