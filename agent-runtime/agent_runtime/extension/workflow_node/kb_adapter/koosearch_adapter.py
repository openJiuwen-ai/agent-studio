#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.


from typing import Any, Dict, List

import aiohttp

from openjiuwen.core.common.logging import workflow_logger

from .base import DatasetSearchRequest, KBSearchResult, KBServiceAdapter
from .customer_header_inject import inject_customer_headers_to_kb


# 搜索模式映射
_SEARCH_SCOPE_MAP = {
    "doc": "doc",
    "faq": "faq",
    "mix": "mix",
    "keyword": "keyword",
}


class KooSearchAdapter(KBServiceAdapter):

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
        app_code = extra_params.get("AppCode", "") or connection_config.get("authorization", "")

        if not endpoint:
            raise RuntimeError("KooSearch endpoint is empty")
        if not app_code:
            raise RuntimeError("KooSearch AppCode is empty")

        # 构建 HTTP 请求头
        headers = {
            "Content-Type": "application/json",
            "X-Apig-AppCode": app_code,
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
                "No valid dataset_ids found in knowledge_bases for KooSearch",

            )

        try:
            results = await self._search_datasets(
                DatasetSearchRequest(
                    endpoint=endpoint,
                    query=query,
                    dataset_ids=dataset_ids,
                    headers=headers,
                    retrieval_params=retrieval_params,
                    extra_params=extra_params,
                )
            )
            all_results.extend(results)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"KooSearch search failed: {e}"
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
        extra_params = request.extra_params
        top_k = request.retrieval_params.get("topK", 10)
        search_mode = request.retrieval_params.get("searchMode", "doc")
        tags = request.retrieval_params.get("tags", [])

        project_id = extra_params.get("project_id", "")
        application_id = extra_params.get("application_id", "")

        if project_id and application_id:
            url = (
                f"{endpoint.rstrip('/')}/{application_id}"
                f"/v1/{project_id}/applications/{application_id}"
                f"/uni-search/experience/searchtext"
            )
        else:
            url = f"{endpoint.rstrip('/')}/uni-search/experience/searchtext"

        # 构建请求体
        body: Dict[str, Any] = {
            "repo_id": dataset_ids[0] if dataset_ids else "",
            "content": query,
            "extra_repo_ids": dataset_ids[1:] if len(dataset_ids) > 1 else dataset_ids,
            "page_num": 1,
            "page_size": top_k,
        }

        # 标签过滤
        if tags:
            if isinstance(tags, list):
                body["filter_string"] = f"tags:({' OR '.join(str(tag) for tag in tags)})"
            else:
                body["filter_string"] = str(tags)

        # 搜索模式
        scope = _SEARCH_SCOPE_MAP.get(search_mode.lower(), "doc")
        body["scope"] = scope

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
                        raise RuntimeError(f"KooSearch API error: status={resp.status}, body={text[:500]}")

                    resp_data = await resp.json()
                    return self.parse_response(resp_data)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"KooSearch HTTP request failed: {e}"
            ) from e

    @staticmethod
    def parse_response(resp_data: dict) -> List[KBSearchResult]:
        results = []
        doc_list = resp_data.get("doc_list", [])
        if not doc_list:
            # 可能直接返回列表
            if isinstance(resp_data, list):
                doc_list = resp_data
            else:
                return []

        for doc in doc_list:
            if not isinstance(doc, dict):
                continue

            text = doc.get("content", "")
            if not text:
                continue

            score = doc.get("score", 0.0)
            repo_id = doc.get("repo_id", "")

            # 将 doc 剩余字段放入 metadata
            metadata = {
                k: v
                for k, v in doc.items()
                if k not in ("content", "score")
            }

            results.append(
                KBSearchResult(
                    text=text,
                    score=float(score),
                    source=repo_id,
                    knowledge_base_id=repo_id,
                    file_id=doc.get("file_id",
                              doc.get("fileId",
                                  doc.get("documentId",
                                      doc.get("document_id", "")))),
                    document_name=doc.get("title",
                                    doc.get("documentName",
                                        doc.get("document_name", ""))),
                    subtitle=doc.get("subtitle", ""),
                    type=doc.get("doc_type",
                           doc.get("docType",
                               doc.get("type", "doc"))),
                    metadata=metadata,
                )
            )

        return results
