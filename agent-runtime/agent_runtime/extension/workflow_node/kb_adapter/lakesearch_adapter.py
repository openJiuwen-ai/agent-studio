#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.


import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

from agent_runtime.common.config import settings
from openjiuwen.core.common.logging import workflow_logger

from .base import KBSearchResult, KBServiceAdapter
from .customer_header_inject import inject_customer_headers_to_kb

_EXCLUDED_METADATA_KEYS = frozenset({
    "content", "text", "score",
    "file_id", "fileId", "chunk_id", "chunkId",
    "title", "subtitle", "doc_type", "docType",
    "repo_id", "repoId",
})


@dataclass
class LakeSearchRequest:

    endpoint: str
    project_id: str
    app_id: str
    repo_ids: List[str]
    query: str
    top_k: int
    headers: Dict[str, Any]
    search_mode: str = "doc"
    tags: List[str] = field(default_factory=list)


class LakeSearchAdapter(KBServiceAdapter):

    async def search(
        self,
        query: str,
        *,
        connection_config: dict,
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:

        top_k = retrieval_params.get("topK", 10)
        score_threshold = retrieval_params.get("scoreThreshold", 0.0)
        search_mode = retrieval_params.get("searchMode", "doc")
        tags = retrieval_params.get("tags", [])

        endpoint = connection_config.get("endpoint", "")
        auth_mode = connection_config.get("auth_mode", "BASIC")
        authorization = connection_config.get("authorization", "")
        extra_params = connection_config.get("extra_params", {})

        if not endpoint:
            raise RuntimeError("LakeSearch endpoint is empty")

        # 构建 HTTP 请求头（支持 BASIC / TOKEN / KERBEROS 三种认证模式）
        headers = {"Content-Type": "application/json"}

        if auth_mode.upper() == "KERBEROS":
            kerberos_config = self._extract_kerberos_config(extra_params)
            if not kerberos_config:
                raise ValueError(
                    "KERBEROS auth mode requires: host_names, cluster_ips, "
                    "user_keytab_file, krb5_file in connection params"
                )
            headers["_kerberos_config"] = kerberos_config
        elif authorization:
            if auth_mode.upper() == "BASIC":
                headers["Authorization"] = f"Basic {authorization}"
            elif auth_mode.upper() == "TOKEN":
                headers["Authorization"] = f"Bearer {authorization}"
            else:
                headers["Authorization"] = authorization

        # 客户 Header 改写（同构，剥 cust- 前缀 + captured 覆盖）
        inject_customer_headers_to_kb(headers)

        # project_id / app_id 必须由 OBS 连接配置提供，缺失直接报错，不兜底
        project_id = extra_params.get("project_id", "")
        app_id = extra_params.get("app_id", "")
        if not project_id or not app_id:
            raise ValueError(
                "LakeSearch connection requires project_id and app_id in connection params "
                "(from OBS), but they are missing"
            )

        # 收集有效的知识库 external_id
        repo_ids = []
        for kb in knowledge_bases:
            external_id = kb.get("external_id", "")
            kb_id = kb.get("knowledge_base_id", "")
            if not external_id:
                workflow_logger.warning(
                    f"KB {kb_id} has no external_id, skip"
                )
                continue
            repo_ids.append(external_id)

        if not repo_ids:
            return []

        # 对齐 Java 端逻辑：用 repo_id + extra_repo_ids 在单次 HTTP 请求中检索多个知识库
        # Java: SearchTextReq.builder.repoId(first).extraRepoIds(rest).build
        request = LakeSearchRequest(
            endpoint=endpoint,
            project_id=project_id,
            app_id=app_id,
            repo_ids=repo_ids,
            query=query,
            top_k=top_k,
            headers=headers,
            search_mode=search_mode,
            tags=tags,
        )
        all_results = await self._search_multi_kb(request)

        # 按 score 降序排列，截取 top_k
        all_results.sort(key=lambda r: r.score, reverse=True)
        all_results = all_results[:top_k]

        # 过滤低于阈值的结果
        if score_threshold > 0:
            all_results = [
                r for r in all_results if r.score >= score_threshold
            ]

        return all_results

    async def _search_multi_kb(
        self,
        request: LakeSearchRequest,
    ) -> List[KBSearchResult]:
        """对齐 Java 端：单次 HTTP 请求，repo_id + extra_repo_ids 检索多个知识库。"""

        endpoint = request.endpoint
        project_id = request.project_id
        app_id = request.app_id
        repo_ids = request.repo_ids
        query = request.query
        top_k = request.top_k
        headers = request.headers
        search_mode = request.search_mode
        tags = request.tags

        url = (
            f"{endpoint.rstrip('/')}/v1/{project_id}"
            f"/applications/{app_id}"
            f"/uni-search/experience/searchtext"
        )

        # 搜索模式映射
        scope = "doc"
        if search_mode.lower() == "faq":
            scope = "faq"
        elif search_mode.lower() == "keyword":
            scope = "keyword"
        elif search_mode.lower() == "mix":
            scope = "mix"

        # 对齐 Java SearchTextRequestBody：repoId + extraRepoIds
        body = {
            "repo_id": repo_ids[0],
            "content": query,
            "page_num": 1,
            "page_size": min(top_k, 50),
            "scope": scope,
        }
        # 多知识库时设置 extra_repo_ids（对齐 Java LakeSearchService：排除主 repo，主 repo 已在 repo_id 中）
        # Java: .extraRepoIds(knowledgeRepos.stream.filter(item -> !item.equals(knowledgeRepoId)).toList)
        if len(repo_ids) > 1:
            body["extra_repo_ids"] = repo_ids[1:]

        # 标签过滤
        if tags:
            if isinstance(tags, list):
                body["filter_string"] = f"tags:({' OR '.join(str(tag) for tag in tags)})"
            else:
                body["filter_string"] = str(tags)

        # Kerberos 认证处理：从 headers 提取 Kerberos 配置，生成 Negotiate token
        kerberos_config = headers.pop("_kerberos_config", None)
        if kerberos_config:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            host_names = kerberos_config.get("host_names", [])
            hostname = host_names[0] if host_names else parsed.hostname

            if not hostname:
                raise RuntimeError(
                    "Cannot extract hostname for Kerberos service principal"
                )

            try:
                auth_header = await self._build_kerberos_auth_header(hostname, kerberos_config)
                headers["Authorization"] = auth_header
                workflow_logger.debug(
                    "Built Kerberos Negotiate token for service principal HTTP@%s", hostname
                )
            except ImportError as e:
                raise RuntimeError(
                    f"Kerberos authentication failed: gssapi library not installed. {e}"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"Kerberos authentication failed: {e}"
                ) from e

        try:
            # 对齐旧版：LakeSearch 端点常为自签证书，默认关闭 TLS 证书校验
            # （旧版 HttpClientUtils.createIgnoreVerifySsl 的同等语义）。
            # KB_SSL_VERIFY=true 时恢复校验（端点使用受信任证书时）。
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                    ssl=None if settings.kb.ssl_verify else False,
                ) as resp:
                    if not resp.ok:
                        text = await resp.text()
                        raise RuntimeError(f"LakeSearch API error: status={resp.status}, body={text[:500]}")

                    resp_text = await resp.text()
                    try:
                        resp_data = json.loads(resp_text)
                    except (json.JSONDecodeError, TypeError):
                        resp_data = resp_text

                    if isinstance(resp_data, str):
                        resp_data = json.loads(resp_data)

                    return self.parse_response(resp_data, repo_ids[0])

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"LakeSearch HTTP request failed: {e}"
            ) from e

    @staticmethod
    def parse_response(
        resp_data: dict, source: str
    ) -> List[KBSearchResult]:
        """解析 LakeSearch 响应，字段映射对齐 Java LakeSearchChatReferenceInfo。

        Java @JsonNaming(SnakeCaseStrategy) → JSON 字段为 snake_case:
          fileId → file_id, chunkId → chunk_id, docType → doc_type,
          filePath → file_path, repoId → repo_id
        同时兼容 camelCase 响应。
        """
        results = []
        doc_list = resp_data.get("doc_list", [])
        if not doc_list:
            doc_list = resp_data.get("docList", [])
        if not doc_list:
            doc_list = resp_data.get("data", {}).get("doc_list", [])

        for doc in doc_list:
            if not isinstance(doc, dict):
                continue
            text = doc.get("content", "") or doc.get("text", "")
            score = doc.get("score", 0.0)
            if not text:
                continue

            # repo_id 优先从文档自身取（多知识库检索时每个结果属于不同 repo）
            doc_repo_id = doc.get("repo_id", doc.get("repoId", "")) or source

            metadata = {
                k: v
                for k, v in doc.items()
                if k not in _EXCLUDED_METADATA_KEYS
            }
            results.append(
                KBSearchResult(
                    text=text,
                    score=float(score),
                    source=doc_repo_id,
                    knowledge_base_id=doc_repo_id,
                    file_id=doc.get("file_id",
                              doc.get("fileId", "")),
                    document_name=doc.get("title", ""),
                    subtitle=doc.get("subtitle", ""),
                    type=doc.get("doc_type",
                          doc.get("docType",
                              doc.get("type", "doc"))),
                    metadata=metadata,
                )
            )

        return results

    def _extract_kerberos_config(self, extra_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        host_names = extra_params.get("host_names", "")
        cluster_ips = extra_params.get("cluster_ips", "")
        keytab = extra_params.get("user_keytab_file", "")
        krb5 = extra_params.get("krb5_file", "")
        port = extra_params.get("port", "")
        protocol = extra_params.get("protocol", "https")

        if not all([host_names, cluster_ips, keytab, krb5]):
            return None

        return {
            "host_names": host_names.split(",") if host_names else [],
            "cluster_ips": cluster_ips.split(",") if cluster_ips else [],
            "port": port,
            "protocol": protocol,
            "keytab_path": keytab,
            "krb5_conf_path": krb5,
        }

    async def _build_kerberos_auth_header(
        self, hostname: str, kerberos_config: Dict[str, Any]
    ) -> str:

        from agent_runtime.common.kerberos_auth import get_spnego_token

        service_principal = f"HTTP@{hostname}"
        keytab_path = kerberos_config["keytab_path"]
        krb5_conf_path = kerberos_config["krb5_conf_path"]

        # GSSAPI 调用是阻塞的，需要在 executor 中运行
        loop = asyncio.get_event_loop()
        token = await loop.run_in_executor(
            None,
            get_spnego_token,
            service_principal,
            keytab_path,
            krb5_conf_path,
            None,  # client_principal (auto-infer from keytab)
        )

        return f"Negotiate {token}"
