#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.


from typing import Any, Dict, List

import aiohttp

from openjiuwen.core.common.logging import workflow_logger

from .base import DatasetSearchRequest, KBSearchResult, KBServiceAdapter
from .customer_header_inject import inject_customer_headers_to_kb


class RagFlowAdapter(KBServiceAdapter):

    async def search(
        self,
        query: str,
        *,
        connection_config: dict,
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:
        all_results: List[KBSearchResult] = []

        top_k = retrieval_params.get("topK", 10)
        score_threshold = retrieval_params.get("scoreThreshold", 0.0)

        endpoint = connection_config.get("endpoint", "")

        if not endpoint:
            raise RuntimeError("RAGFlow endpoint is empty")

        extra_params = connection_config.get("extra_params", {})
        authorization = extra_params.get("APIKey", "") or connection_config.get("authorization", "")
        if not authorization:
            raise RuntimeError("RAGFlow authorization is empty")

        # 构建 HTTP 请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {authorization}",
        }

        # 客户 Header 改写（同构，剥 cust- 前缀 + captured 覆盖）
        inject_customer_headers_to_kb(headers)

        # 收集所有知识库的 dataset_id（external_id）
        dataset_ids = []
        for kb in knowledge_bases:
            external_id = kb.get("external_id", "")
            kb_id = kb.get("knowledge_base_id", "")
            if not external_id:
                workflow_logger.warning(
                    f"KB {kb_id} has no external_id, skip"
                )
                continue
            dataset_ids.append(external_id)

        if not dataset_ids:
            raise RuntimeError(
                "No valid dataset_ids found in knowledge_bases for RAGFlow",

            )

        try:
            results = await self._search_datasets(
                DatasetSearchRequest(
                    endpoint=endpoint,
                    query=query,
                    dataset_ids=dataset_ids,
                    headers=headers,
                    retrieval_params=retrieval_params,
                )
            )
            all_results.extend(results)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"RAGFlow search failed: {e}"
            ) from e

        # 按 score 降序排列，截取 top_k
        all_results.sort(key=lambda r: r.score, reverse=True)
        all_results = all_results[:top_k]

        # 过滤低于阈值的结果
        if score_threshold > 0:
            all_results = [
                r for r in all_results if r.score >= score_threshold
            ]

        return all_results

    async def _search_datasets(
        self,
        request: DatasetSearchRequest,
    ) -> List[KBSearchResult]:
        endpoint = request.endpoint
        query = request.query
        dataset_ids = request.dataset_ids
        headers = request.headers
        retrieval_params = request.retrieval_params
        top_k = retrieval_params.get("topK", 10)
        score_threshold = retrieval_params.get("scoreThreshold", 0.0)

        url = f"{endpoint.rstrip('/')}/api/v1/retrieval"

        # 构建请求体
        body: Dict[str, Any] = {
            "question": query,
            "dataset_ids": dataset_ids,
            "page": 1,
            "page_size": top_k,
        }

        # 透传可选检索参数（RAGFlow API 使用 snake_case）
        if score_threshold > 0:
            body["similarity_threshold"] = score_threshold

        if "vectorSimilarityWeight" in retrieval_params:
            body["vector_similarity_weight"] = retrieval_params["vectorSimilarityWeight"]
        if "keyword" in retrieval_params:
            body["keyword"] = retrieval_params["keyword"]
        if "rerankId" in retrieval_params:
            body["rerank_id"] = retrieval_params["rerankId"]
        if "highlight" in retrieval_params:
            body["highlight"] = retrieval_params["highlight"]
        if "crossLanguages" in retrieval_params:
            body["cross_languages"] = retrieval_params["crossLanguages"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if not resp.ok:
                        text = await resp.text()
                        raise RuntimeError(f"RAGFlow API error: status={resp.status}, body={text[:500]}")

                    resp_data = await resp.json()
                    return self.parse_response(resp_data)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"RAGFlow HTTP request failed: {e}"
            ) from e

    @staticmethod
    def parse_response(resp_data: dict) -> List[KBSearchResult]:
        results = []

        # 检查响应状态码
        code = resp_data.get("code")
        if code != 0:
            raise RuntimeError(
                f"RAGFlow API returned non-zero code: {code}, "
                f"message: {resp_data.get('message', '')}",

            )

        data = resp_data.get("data", {})
        chunks = data.get("chunks", [])
        if not chunks:
            return []

        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue

            text = chunk.get("content", "")
            if not text:
                continue

            score = chunk.get("similarity", 0.0)

            # 将 chunk 剩余字段放入 metadata
            metadata = {
                k: v
                for k, v in chunk.items()
                if k not in ("content", "similarity")
            }

            doc_name = (
                chunk.get("document_keyword", "")
                or chunk.get("docnm_kwd", "")
                or chunk.get("title", "")
                or chunk.get("document_name", "")
                or chunk.get("documentName", "")
            )

            results.append(
                KBSearchResult(
                    text=text,
                    score=float(score),
                    source=chunk.get("dataset_id",
                              chunk.get("datasetId",
                                  chunk.get("kb_id", ""))),
                    knowledge_base_id=chunk.get("dataset_id",
                                        chunk.get("datasetId",
                                            chunk.get("kb_id", ""))),
                    file_id=chunk.get("document_id",
                               chunk.get("documentId",
                                   chunk.get("doc_id",
                                       chunk.get("chunk_id", "")))),
                    document_name=doc_name,
                    # Java 端同样用 documentKeyword 填充 subtitle
                    subtitle=doc_name,
                    knowledge_base_type=chunk.get("knowledge_base_type",
                                          chunk.get("knowledgeBaseType", "")),
                    type="faq" if score > 0.9 else "doc",
                    metadata=metadata,
                )
            )

        return results
