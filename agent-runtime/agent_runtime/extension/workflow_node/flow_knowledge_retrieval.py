#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import uuid as uuid_lib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Union

from agent_runtime.common.kb_config_providers import OBSKnowledgeBaseConfigProvider
from common_utils.redis_manager import get_redis_client
from agent_runtime.extension.workflow_node.kb_adapter.base import KBSearchResult, KBServiceAdapter
from agent_runtime.extension.workflow_node.kb_adapter.factory import KBAdapterFactory
from openjiuwen.core.common.constants.constant import USER_FIELDS
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import LogEventType, workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent

JIUWEN_KNOWLEDGE_RETRIEVAL_TYPE = "jiuwen.knowledgeRetrieval"
KNOWLEDGE_IMAGE_CACHE_PREFIX = "knowledge:image:"
KNOWLEDGE_FILE_CACHE_PREFIX = "knowledge:file:"
KNOWLEDGE_FILE_TYPE_DOC = "doc"
KNOWLEDGE_FILE_TYPE_FAQ = "faq"
IMAGE_ID_PATTERN = re.compile(r"\{(img-[a-z0-9-]+)}", re.IGNORECASE)
RETRIEVAL_IMAGE_FORMAT = "![img](https://agent_arts_knowledge_img_url/{})"


@dataclass
class FlowKnowledgeRetrievalConfig:
    """知识库检索节点配置"""

    connection_id: str = ""
    knowledge_base_ids: List[str] = field(default_factory=list)
    retrieval_config: Dict = field(default_factory=dict)


class FlowKnowledgeRetrieval(WorkflowComponent):

    # 全局 Provider 实例（进程级共享，OBS 读取带缓存）
    _kb_provider: Optional[OBSKnowledgeBaseConfigProvider] = None

    def __init__(self, conf: Union[FlowKnowledgeRetrievalConfig, dict, None] = None):
        super().__init__()
        self._conf: Optional[FlowKnowledgeRetrievalConfig] = None
        self._kb_config: Optional[dict] = None  # 从 OBS 加载的完整配置
        if conf is not None:
            self._init_conf(conf)

    @classmethod
    def set_kb_provider(cls, provider: OBSKnowledgeBaseConfigProvider) -> None:
        cls._kb_provider = provider

    def _init_conf(self, conf: Union[FlowKnowledgeRetrievalConfig, dict]) -> None:
        try:
            if isinstance(conf, dict):
                self._conf = FlowKnowledgeRetrievalConfig(
                    connection_id=conf.get("connectionId", ""),
                    knowledge_base_ids=conf.get("knowledgeBaseIds", []),
                    retrieval_config=conf.get("retrievalConfig", {}),
                )
            else:
                self._conf = conf
        except Exception as e:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="flow_knowledge_retrieval",
                reason=str(e),
                workflow="n/a",
                cause=e,
            ) from e

    def init(self, conf=None, **kwargs):
        """兼容遗留工作流引擎的两阶段初始化"""
        if conf is not None:
            self._init_conf(conf)
        super().init(**kwargs)

    @property
    def config(self) -> FlowKnowledgeRetrievalConfig:
        """获取节点配置"""
        return self._conf

    @property
    def node_type(self) -> str:
        """获取节点类型标识"""
        return JIUWEN_KNOWLEDGE_RETRIEVAL_TYPE

    def component_type(self) -> str:
        """获取组件类型标识"""
        return JIUWEN_KNOWLEDGE_RETRIEVAL_TYPE

    @staticmethod
    def _resolve_query_from_session(session: Session) -> str:
        try:
            # 1. 从 global_state 读取 query（commit_user_inputs 写入，引擎启动前即已 commit）
            query = session.get_global_state("query")
            if isinstance(query, str) and query.strip():
                workflow_logger.info(
                    "FlowKnowledgeRetrieval resolved query from global_state: len=%d",
                    len(query),
                )
                return query

            # 2. 从 io-state 读取 Start 节点已 commit 的 userFields.query
            start_user_fields_query = session.get_state("node_start.userFields.query")
            if isinstance(start_user_fields_query, str) and start_user_fields_query.strip():
                workflow_logger.info(
                    "FlowKnowledgeRetrieval resolved query from io_state node_start.userFields.query: len=%d",
                    len(start_user_fields_query),
                )
                return start_user_fields_query

            # 3. 从 io-state 读取 Start 节点的 systemFields.query
            #    （如果 _post_invoke 已执行，systemFields 已 commit）
            start_system_fields_query = session.get_state("node_start.systemFields.query")
            if isinstance(start_system_fields_query, str) and start_system_fields_query.strip():
                workflow_logger.info(
                    "FlowKnowledgeRetrieval resolved query from io_state node_start.systemFields.query: len=%d",
                    len(start_system_fields_query),
                )
                return start_system_fields_query

            # 4. 从 io-state 顶层读取 query（commit_user_inputs 写入）
            top_query = session.get_state("query")
            if isinstance(top_query, str) and top_query.strip():
                workflow_logger.info(
                    "FlowKnowledgeRetrieval resolved query from io_state top-level: len=%d",
                    len(top_query),
                )
                return top_query

            # 5. 最后尝试：遍历 Start 节点的 userFields 中所有值，找非空字符串
            start_user_fields = session.get_state("node_start.userFields")
            if isinstance(start_user_fields, dict):
                for k, v in start_user_fields.items():
                    if isinstance(v, str) and v.strip():
                        workflow_logger.info(
                            "FlowKnowledgeRetrieval resolved query from io_state node_start.userFields.%s: len=%d",
                            k, len(v),
                        )
                        return v

            workflow_logger.warning(
                "FlowKnowledgeRetrieval _resolve_query_from_session: "
                "query not found in any source. "
                "global_state_query=%r, start_user_fields_query=%r, "
                "start_system_fields_query=%r, top_query=%r",
                repr(query)[:100] if query else None,
                repr(start_user_fields_query)[:100] if start_user_fields_query else None,
                repr(start_system_fields_query)[:100] if start_system_fields_query else None,
                repr(top_query)[:100] if top_query else None,
            )
        except Exception as e:
            workflow_logger.warning(
                "FlowKnowledgeRetrieval _resolve_query_from_session failed: %s", e,
            )
        return ""

    async def ensure_kb_config(self) -> dict:
        """确保知识库配置已加载

        通过 Provider 从 OBS 加载连接和知识库配置。
        """
        if self._kb_config is not None:
            return self._kb_config

        # 通过 Provider 从 OBS 加载
        if self._kb_provider is None:
            self._kb_provider = OBSKnowledgeBaseConfigProvider()

        ir_node = {
            "configs": {
                "connectionId": self._conf.connection_id,
                "knowledgeBaseIds": self._conf.knowledge_base_ids,
                "retrievalConfig": self._conf.retrieval_config,
            }
        }

        self._kb_config = await self._kb_provider.get_kb_config(ir_node)
        return self._kb_config

    async def _search_with_faq_fallback(
        self,
        adapter: KBServiceAdapter,
        query: str,
        connection_config: dict,
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:
        """FAQ 优先搜索：先尝试 FAQ 模式，FAQ 无结果则回退到用户指定的模式。"""
        need_faq = retrieval_params.get("needExtrasFaqSearch", False)

        if need_faq:
            faq_params = dict(retrieval_params)
            faq_params["searchMode"] = "faq"

            workflow_logger.info(
                "FlowKnowledgeRetrieval FAQ priority search: trying FAQ mode first"
            )

            faq_results = await adapter.search(
                query=query,
                connection_config=connection_config,
                knowledge_bases=knowledge_bases,
                retrieval_params=faq_params,
            )

            if faq_results:
                for item in faq_results:
                    item.type = "faq"
                workflow_logger.info(
                    "FlowKnowledgeRetrieval FAQ search returned %d results, returning immediately",
                    len(faq_results),
                )
                return faq_results

            workflow_logger.info(
                "FlowKnowledgeRetrieval FAQ search returned empty, falling through to normal search"
            )

        # 回退到普通搜索
        results = await adapter.search(
            query=query,
            connection_config=connection_config,
            knowledge_bases=knowledge_bases,
            retrieval_params=retrieval_params,
        )
        result_type = "faq" if str(retrieval_params.get("searchMode", "")).lower() == "faq" else "doc"
        for item in results:
            item.type = result_type
        return results

    @staticmethod
    def _build_external_to_kb_maps(knowledge_bases: list) -> tuple[Dict[str, str], Dict[str, str]]:
        external_to_internal: Dict[str, str] = {}
        internal_to_type: Dict[str, str] = {}
        for kb in knowledge_bases:
            internal_id = kb.get("knowledge_base_id", "")
            external_id = kb.get("external_id", "")
            kb_type = kb.get("type", "")
            if internal_id:
                external_to_internal[internal_id] = internal_id
                internal_to_type[internal_id] = kb_type
            if external_id and internal_id:
                external_to_internal[external_id] = internal_id
        return external_to_internal, internal_to_type

    @staticmethod
    def _generate_image_access_key() -> str:
        uuid_text = str(uuid_lib.uuid4())
        return base64.urlsafe_b64encode(uuid_text.encode("utf-8")).decode("ascii").rstrip("=")

    @staticmethod
    def _replace_image_access_key_and_format(content: str, retrieve_image: bool) -> tuple[str, Dict[str, str]]:
        if not content:
            return content, {}
        if not retrieve_image:
            return IMAGE_ID_PATTERN.sub("", content), {}

        image_access_map: Dict[str, str] = {}

        def replace(match: re.Match) -> str:
            image_id = match.group(1)
            access_key = FlowKnowledgeRetrieval._generate_image_access_key()
            image_access_map[image_id] = access_key
            return RETRIEVAL_IMAGE_FORMAT.format(access_key)

        return IMAGE_ID_PATTERN.sub(replace, content), image_access_map

    async def _cache_redis(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            redis_client = get_redis_client()
            await redis_client.set(key, value, ex=ttl_seconds)
        except Exception as e:
            workflow_logger.warning("FlowKnowledgeRetrieval failed to cache redis key=%s: %s", key, e)

    async def normalize_results_like_java(
        self,
        results: List[KBSearchResult],
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:

        external_to_internal, internal_to_type = self._build_external_to_kb_maps(knowledge_bases)
        retrieve_image = bool(retrieval_params.get("retrieveImage", False))
        validity_days = int(os.environ.get("KNOWLEDGE_RETRIEVAL_IMAGE_VALIDITY_DAYS", "7"))
        ttl_seconds = max(validity_days, 1) * 24 * 60 * 60
        local_file_id_cache: Dict[str, str] = {}

        for item in results:
            source_id = item.source or item.knowledge_base_id
            internal_id = external_to_internal.get(source_id) or external_to_internal.get(item.knowledge_base_id)
            if internal_id:
                item.knowledge_base_id = internal_id
                item.knowledge_base_type = internal_to_type.get(internal_id, item.knowledge_base_type)

            real_file_id = item.file_id
            if real_file_id and item.knowledge_base_id:
                file_type = KNOWLEDGE_FILE_TYPE_FAQ if item.type == "faq" else KNOWLEDGE_FILE_TYPE_DOC
                cache_key = f"{item.knowledge_base_id}:{real_file_id}"
                virtual_file_id = local_file_id_cache.get(cache_key)
                if virtual_file_id is None:
                    virtual_file_id = str(uuid_lib.uuid4())
                    local_file_id_cache[cache_key] = virtual_file_id
                    await self._cache_redis(
                        KNOWLEDGE_FILE_CACHE_PREFIX + virtual_file_id,
                        f"{item.knowledge_base_id},{file_type},{real_file_id}",
                        ttl_seconds,
                    )
                item.file_id = virtual_file_id

            processed_content, image_access_map = self._replace_image_access_key_and_format(
                item.text, retrieve_image
            )
            if processed_content != item.text:
                item.text = processed_content
            if image_access_map and item.knowledge_base_id:
                for image_id, access_key in image_access_map.items():
                    await self._cache_redis(
                        KNOWLEDGE_IMAGE_CACHE_PREFIX + access_key,
                        f"{item.knowledge_base_id},{image_id}",
                        ttl_seconds,
                    )

        return results

    @staticmethod
    def is_custom_source(connection_config: dict) -> bool:
        """判断连接是否为 CUSTOM 知识源（来自 OBS knowledgeSource 字段）。"""
        return str(connection_config.get("knowledge_source", "")).upper() == "CUSTOM"

    async def _retrieve_custom(
        self,
        adapter: KBServiceAdapter,
        query: str,
        connection_config: dict,
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:

        all_tags = []
        for kb in knowledge_bases:
            tags = kb.get("tags", [])
            if tags:
                if isinstance(tags, list):
                    all_tags.extend(tags)
                else:
                    all_tags.append(str(tags))

        custom_params = dict(retrieval_params)
        if all_tags:
            custom_params["tags"] = all_tags
        # CUSTOM 不做分数过滤，剔除阈值避免适配器内 score_threshold>0 过滤多删结果
        custom_params.pop("scoreThreshold", None)
        custom_params.pop("recallThreshold", None)
        # CUSTOM 用知识库 id 作为 repo_id（覆盖 external_id）
        custom_kbs = []
        for kb in knowledge_bases:
            item = dict(kb)
            item["external_id"] = kb.get("knowledge_base_id", "") or kb.get("external_id", "")
            custom_kbs.append(item)

        results = await adapter.search(
            query=query,
            connection_config=connection_config,
            knowledge_bases=custom_kbs,
            retrieval_params=custom_params,
        )
        return results

    async def search_knowledge_repo(
        self,
        adapter: KBServiceAdapter,
        query: str,
        connection_config: dict,
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:
        """知识库搜索编排：过滤已关闭 KB，收集 tags，按需执行多知识库并行检索。"""
        # CUSTOM 知识源走专属语义（不过滤 CLOSE、不阈值过滤、不 FAQ 回退、不归一化）
        if self.is_custom_source(connection_config):
            return await self._retrieve_custom(
                adapter=adapter, query=query,
                connection_config=connection_config,
                knowledge_bases=knowledge_bases,
                retrieval_params=retrieval_params,
            )

        # 过滤已关闭的知识库
        active_kbs = [
            kb for kb in knowledge_bases
            if kb.get("status", "").upper() != "CLOSE"
        ]

        if not active_kbs:
            workflow_logger.warning("All knowledge bases are closed or filtered out")
            return []

        all_tags = []
        for kb in active_kbs:
            tags = kb.get("tags", [])
            if tags:
                if isinstance(tags, list):
                    all_tags.extend(tags)
                else:
                    all_tags.append(str(tags))

        if all_tags:
            retrieval_params = dict(retrieval_params)
            retrieval_params["tags"] = all_tags

        connector_type = connection_config.get("connector_type", "")
        top_k = retrieval_params.get("topK", 10)

        # 仅 KooSearchInside 且多 KB 时走多源并行路由
        if connector_type.lower() == "koosearchinside" and len(active_kbs) > 1:
            results = await self._multi_retrieve_kb(
                adapter=adapter, query=query,
                connection_config=connection_config,
                knowledge_bases=active_kbs,
                retrieval_params=retrieval_params,
            )
        else:
            results = await self._search_with_faq_fallback(
                adapter=adapter, query=query,
                connection_config=connection_config,
                knowledge_bases=active_kbs,
                retrieval_params=retrieval_params,
            )

        # 应用 recallThreshold 分数过滤
        recall_threshold = retrieval_params.get(
            "recallThreshold",
            retrieval_params.get("scoreThreshold", 0.0),
        )
        if recall_threshold > 0:
            results = [r for r in results if r.score >= recall_threshold]

        # 按 score 降序排列后截取 top_k
        results.sort(key=lambda r: r.score, reverse=True)
        if len(results) > top_k:
            results = results[:top_k]

        return results

    async def _multi_retrieve_kb(
        self,
        adapter: KBServiceAdapter,
        query: str,
        connection_config: dict,
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:
        """多知识库并行检索（按 connection_id 分组后并行搜索，结果合并排序）。"""
        top_k = retrieval_params.get("topK", 10)

        # 按 connection_id 分组
        groups = defaultdict(list)
        for kb in knowledge_bases:
            conn_id = kb.get("connection_id", kb.get("knowledge_base_connection_id", "default"))
            groups[conn_id].append(kb)

        # 并行搜索各组
        async def search_group(kb_group: list) -> List[KBSearchResult]:
            return await self._search_with_faq_fallback(
                adapter=adapter, query=query,
                connection_config=connection_config,
                knowledge_bases=kb_group,
                retrieval_params=retrieval_params,
            )

        tasks = [search_group(group) for group in groups.values()]
        group_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 展平结果
        all_results: List[KBSearchResult] = []
        for grp_res in group_results:
            if isinstance(grp_res, Exception):
                workflow_logger.error(f"Multi-KB search group failed: {grp_res}")
                continue
            all_results.extend(grp_res)

        # KooSearchScoreMergingStrategy：展平 → 按 score 降序 → topK
        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:top_k]

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        try:
            # 诊断：打印 inputs 完整结构，帮助定位 query 取值问题
            workflow_logger.info(
                "FlowKnowledgeRetrieval invoke started",
                event_type=LogEventType.WORKFLOW_COMPONENT_START,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_KNOWLEDGE_RETRIEVAL_TYPE,
                session_id=session.get_session_id(),
                metadata={
                    "inputs_type": type(inputs).__name__,
                    "inputs_keys": list(inputs.keys()) if isinstance(inputs, dict) else "not_dict",
                    "inputs_repr": repr(inputs)[:1000] if inputs else "None",
                },
            )

            inputs_user_fields = inputs.get(USER_FIELDS) if isinstance(inputs, dict) else None
            query = None
            if isinstance(inputs_user_fields, dict):
                query = inputs_user_fields.get("query")
            if query is None or (isinstance(query, str) and not query.strip()):
                query = self._resolve_query_from_session(session)

            workflow_logger.info(
                "FlowKnowledgeRetrieval query resolution result",
                event_type=LogEventType.WORKFLOW_COMPONENT_START,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_KNOWLEDGE_RETRIEVAL_TYPE,
                session_id=session.get_session_id(),
                metadata={
                    "query_length": len(query) if query else 0,
                    "query_preview": repr(query)[:200] if query else "EMPTY",
                },
            )

            if not query or not query.strip():
                # 诊断：打印 session 中的所有状态
                diag = {}
                try:
                    gs = session.get_global_state()
                    diag["global_state_keys"] = list(gs.keys()) if isinstance(gs, dict) else type(gs).__name__
                    diag["global_state_query"] = repr(session.get_global_state("query"))
                    io_top = session.get_state()
                    diag["io_state_top_keys"] = (
                        list(io_top.keys()) if isinstance(io_top, dict) else type(io_top).__name__
                    )
                    start_all = session.get_state("node_start")
                    diag["node_start_keys"] = (
                        list(start_all.keys()) if isinstance(start_all, dict) else type(start_all).__name__
                    )
                    start_uf = session.get_state("node_start.userFields")
                    diag["node_start_userFields"] = repr(start_uf)[:300] if start_uf else "None"
                except Exception as e:
                    diag["diag_error"] = str(e)

                raise build_error(
                    StatusCode.COMPONENT_KNOWLEDGE_RETRIEVAL_INPUT_PARAM_ERROR,
                    comp_id="flow_knowledge_retrieval",
                    error_msg=(
                        f"Query must be a non-empty string. "
                        f"inputs={repr(inputs)[:300]}. "
                        f"session_diag={diag}"
                    ),
                    workflow="n/a",
                )

            # 2. 加载知识库配置
            kb_config = await self.ensure_kb_config()

            connection_config = kb_config.get("connection", {})
            knowledge_bases = kb_config.get("knowledge_bases", [])
            retrieval_params = kb_config.get("retrieval_params", {})

            connector_type = connection_config.get("connector_type", "LakeSearch")

            # 3. 根据 connector_type 创建适配器并检索
            try:
                adapter = KBAdapterFactory.create(connector_type)
            except ValueError as e:
                raise build_error(
                    StatusCode.COMPONENT_KNOWLEDGE_RETRIEVAL_INVOKE_CALL_FAILED,
                    comp_id="flow_knowledge_retrieval",
                    error_msg=str(e),
                    workflow="n/a",
                ) from e

            results: List[KBSearchResult] = await self.search_knowledge_repo(
                adapter=adapter,
                query=query,
                connection_config=connection_config,
                knowledge_bases=knowledge_bases,
                retrieval_params=retrieval_params,
            )
            # CUSTOM 知识源不做 file_id 虚拟化 / 图片处理
            if not self.is_custom_source(connection_config):
                results = await self.normalize_results_like_java(
                    results,
                    knowledge_bases,
                    retrieval_params,
                )

            # 5. 分配检索 ID（UUID per invoke）和序号
            retrieval_id = uuid_lib.uuid4().hex
            for i, r in enumerate(results, start=1):
                r.retrieval_id = retrieval_id
                if r.serial_number == 0:
                    r.serial_number = i

            # 6. 格式化输出
            output_list = [
                {
                    "content": r.text,
                    "text": r.text,
                    "score": r.score,
                    "knowledge_base_id": r.knowledge_base_id,
                    "knowledge_base_type": r.knowledge_base_type,
                    "file_id": r.file_id,
                    "document_name": r.document_name,
                    "subtitle": r.subtitle,
                    "serial_number": r.serial_number,
                    "retrieval_id": r.retrieval_id,
                    "type": r.type,
                    "source": r.source,
                    "metadata": r.metadata,
                }
                for r in results
            ]
            output = {
                USER_FIELDS: {
                    "output_list": output_list,
                },
            }

            workflow_logger.info(
                "FlowKnowledgeRetrieval invoke completed, results=%s",
                json.dumps(output_list, ensure_ascii=False, default=str),
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_KNOWLEDGE_RETRIEVAL_TYPE,
                session_id=session.get_session_id(),
                metadata={"num_results": len(results)},
            )

            return output

        except Exception as e:
            workflow_logger.error(
                "FlowKnowledgeRetrieval invoke failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_KNOWLEDGE_RETRIEVAL_TYPE,
                session_id=session.get_session_id(),
                exception=e,
            )
            raise build_error(
                StatusCode.COMPONENT_KNOWLEDGE_RETRIEVAL_INVOKE_CALL_FAILED,
                comp_id=session.get_component_id(),
                ability="invoke",
                error_msg=str(e),
                workflow=session.get_workflow_id(),
                cause=e,
            ) from e

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:

        result = await self.invoke(inputs, session, context)
        yield result


__all__ = [
    "FlowKnowledgeRetrieval",
    "FlowKnowledgeRetrievalConfig",
    "JIUWEN_KNOWLEDGE_RETRIEVAL_TYPE",
]
