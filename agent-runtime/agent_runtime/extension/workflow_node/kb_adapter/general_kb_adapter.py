#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.


from typing import Any, Dict, List

import aiohttp

from openjiuwen.core.common.logging import workflow_logger

from .base import DatasetSearchRequest, KBSearchResult, KBServiceAdapter
from .customer_header_inject import inject_customer_headers_to_kb


# 检索模式映射
_SEARCH_METHOD_MAP = {
    "doc": "doc",
    "faq": "faq",
    "mix": "mix",
    "keyword": "keyword",
}


class GeneralKBAdapter(KBServiceAdapter):

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
        extra_params = connection_config.get("extra_params", {})
        api_key = extra_params.get("apiKey", "") or connection_config.get("authorization", "")

        if not endpoint:
            raise RuntimeError("General KB endpoint is empty")
        if not api_key:
            raise RuntimeError("General KB apiKey is empty")

        # 构建 HTTP 请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # 客户 Header 改写（同构，剥 cust- 前缀 + captured 覆盖）
        inject_customer_headers_to_kb(headers)

        # 收集所有知识库的 external_id
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
                "No valid knowledge_base_ids found in knowledge_bases for General KB",

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
                f"General KB search failed: {e}"
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
        top_k = request.retrieval_params.get("topK", 10)
        score_threshold = request.retrieval_params.get("scoreThreshold", 0.0)
        search_mode = request.retrieval_params.get("searchMode", "doc")

        url = f"{endpoint.rstrip('/')}/knowledge-bases/retrieve"

        # 检索模式
        method = _SEARCH_METHOD_MAP.get(search_mode.lower(), "doc")

        # 构建请求体（Java 对齐：offset = (pageNum-1) * pageSize, limit = pageSize, topK = pageSize）
        body: Dict[str, Any] = {
            "knowledge_base_ids": dataset_ids,
            "query": query,
            "method": method,
            "offset": 0,
            "limit": top_k,
            "top_k": top_k,
        }

        # 从检索参数传入 search_threshold（Java: searchThreshold/recallThreshold）
        if score_threshold > 0:
            body["search_threshold"] = score_threshold

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
                        raise RuntimeError(f"General KB API error: status={resp.status}, body={text[:500]}")

                    resp_data = await resp.json()
                    return self.parse_response(resp_data)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"General KB HTTP request failed: {e}"
            ) from e

    @staticmethod
    def parse_response(resp_data: dict) -> List[KBSearchResult]:

        results = []

        search_result_list = resp_data.get("search_result_list", [])
        if not search_result_list:
            return []

        for item in search_result_list:
            if not isinstance(item, dict):
                continue

            text = item.get("content", "")
            if not text:
                continue

            score = item.get("score", 0.0)

            # 将剩余字段放入 metadata
            metadata = {
                k: v
                for k, v in item.items()
                if k not in ("content", "score")
            }

            results.append(
                KBSearchResult(
                    text=text,
                    score=float(score),
                    source=item.get("knowledge_base_id",
                              item.get("datasetId", "")),
                    knowledge_base_id=item.get("knowledge_base_id",
                                       item.get("datasetId", "")),
                    file_id=item.get("file_id",
                              item.get("fileId",
                                  item.get("documentId",
                                      item.get("document_id", "")))),
                    document_name=item.get("title",
                                    item.get("documentName",
                                        item.get("document_name", ""))),
                    subtitle=item.get("subtitle", ""),
                    type=item.get("type",
                           item.get("doc_type", "doc")),
                    metadata=metadata,
                )
            )

        return results