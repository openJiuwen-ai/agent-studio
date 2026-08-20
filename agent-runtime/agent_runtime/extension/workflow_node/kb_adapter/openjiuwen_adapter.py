# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""OpenJiuwen 知识库检索适配器 — 供工作流知识检索节点调用。"""

import logging
from typing import List

from openjiuwen.core.common.logging import workflow_logger

from .base import KBSearchResult, KBServiceAdapter
from .openjiuwen_kb_manager import KBSearchOptions, OpenJiuwenKBManager

logger = logging.getLogger(__name__)

_VALID_INDEX_TYPES = {"vector", "bm25", "hybrid"}

_SEARCH_MODE_MAP = {"doc": "vector", "keyword": "bm25", "mix": "hybrid"}


class OpenJiuwenKBAdapter(KBServiceAdapter):
    """openjiuwen 本地知识库检索适配器。

    直接调用 OpenJiuwenKBManager.search() 进行本地向量检索，
    无需 HTTP 调用外部 RAG 服务。
    """

    async def search(
        self,
        query: str,
        *,
        connection_config: dict,
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:
        """检索 openjiuwen 本地知识库。"""
        top_k = int(retrieval_params.get("topK", 5))
        score_threshold = float(retrieval_params.get("scoreThreshold", 0.0))
        search_mode = retrieval_params.get("searchMode", "")
        index_type = _SEARCH_MODE_MAP.get(search_mode, retrieval_params.get("indexType", "vector"))
        if index_type not in _VALID_INDEX_TYPES:
            logger.warning("Unsupported indexType '%s', falling back to 'vector'", index_type)
            index_type = "vector"

        model_config = connection_config.get("model_config") if connection_config else None
        if not model_config or not model_config.get("model_service_id"):
            raise ValueError("connection_config.model_config with model_service_id is required")
        reranker_config = connection_config.get("reranker_config") if connection_config else None

        manager = OpenJiuwenKBManager()
        results: List[KBSearchResult] = []

        for kb in knowledge_bases:
            kb_id = kb.get("external_id") or kb.get("knowledge_base_id") or kb.get("id", "")
            if not kb_id:
                workflow_logger.warning("Skipping KB with no id: %s", kb)
                continue

            raw_results = await manager.search(
                kb_id=str(kb_id),
                query=query,
                options=KBSearchOptions(
                    model_config=model_config,
                    top_k=top_k,
                    index_type=index_type,
                    reranker_config=reranker_config,
                ),
            )

            for item in raw_results:
                score = float(item.get("score", 0.0))
                if score < score_threshold:
                    continue
                results.append(
                    KBSearchResult(
                        text=item.get("text", ""),
                        score=score,
                        metadata=item.get("metadata", {}),
                        knowledge_base_id=str(kb_id),
                        knowledge_base_type="INTERNAL",
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
