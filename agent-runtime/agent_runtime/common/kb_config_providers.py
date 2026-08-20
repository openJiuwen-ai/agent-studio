#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.


import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent_runtime.common.ir_interfaces import KnowledgeBaseConfigProvider
from agent_runtime.context.request_context import _request_ctx
from storage import get_storage_provider
from common_utils.crypto_tool import CryptTool
from openjiuwen.core.common.logging import workflow_logger


_SECRET_PARAM_CODES = frozenset(
    {"apiKey", "APIKey", "AppCode", "password", "authorization"}
)



@dataclass
class KBConnectionConfig:
    """知识库连接配置 — 从 OBS 连接文件的解析"""

    connection_id: str = ""
    connector_type: str = ""        # LakeSearch / KooSearch / RagFlow
    connector_name: str = ""
    knowledge_source: str = ""      # 知识源模式：LakeSearch / KooSearch / CUSTOM（来自 OBS knowledgeSource）
    endpoint: str = ""
    auth_mode: str = ""             # BASIC / TOKEN / NONE
    authorization: str = ""         # Basic Auth 凭证 或 Token
    extra_params: Dict[str, Any] = field(default_factory=dict)
    used_abilities: List[str] = field(default_factory=list)
    model_config: Dict[str, Any] = field(default_factory=dict)
    reranker_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KBReferenceConfig:
    """知识库引用配置 — 从 OBS 知识库文件的顶层字段解析"""

    knowledge_base_id: str = ""
    knowledge_base_name: str = ""
    type: str = ""                  # INTERNAL / EXTERNAL
    external_id: str = ""           # 外部系统中的索引/库 ID
    status: str = ""
    connection_id: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class KBRetrievalConfig:
    """知识库检索完整配置 — Provider 的返回值"""

    connection: KBConnectionConfig = field(default_factory=KBConnectionConfig)
    knowledge_bases: List[KBReferenceConfig] = field(default_factory=list)
    retrieval_params: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# OBS 文件路径常量
# ---------------------------------------------------------------------------

_OBS_CONNECTION_PATH_TEMPLATE = "kb-connection/ir/connection/{connection_id}.json"
_OBS_KB_PATH_TEMPLATE = "kb-connection/ir/knowledge-base/{knowledge_base_id}.json"

# L1 缓存：进程内内存缓存，TTL 控制
_cache: Dict[str, dict] = {}
_cache_ts: Dict[str, float] = {}
_CACHE_TTL_SECONDS = 300  # 5 分钟


def _get_cached(key: str) -> Optional[dict]:
    """从 L1 内存缓存获取，过期返回 None"""
    if key in _cache:
        ts = _cache_ts.get(key, 0)
        if time.time() - ts < _CACHE_TTL_SECONDS:
            return _cache[key]
        # 过期清理
        _cache.pop(key, None)
        _cache_ts.pop(key, None)
    return None


def _set_cached(key: str, value: dict) -> None:
    """写入 L1 内存缓存"""
    _cache[key] = value
    _cache_ts[key] = time.time()


def _copy_configs(configs: dict) -> dict:
    """浅拷贝配置，避免外部修改影响缓存"""
    if not configs:
        return {}
    return dict(configs)


# ---------------------------------------------------------------------------
# EnvVarKBConfigProvider
# ---------------------------------------------------------------------------


class EnvVarKBConfigProvider(KnowledgeBaseConfigProvider):

    async def get_kb_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> dict:
        import os

        raw_configs = ir_node.get("configs", {})
        configs = _copy_configs(raw_configs)
        retrieval_config = configs.get("retrievalConfig", {})

        connection = KBConnectionConfig(
            connection_id="env_default",
            connector_type=os.environ.get("KB_CONNECTOR_TYPE", "LakeSearch"),
            endpoint=os.environ.get("KB_ENDPOINT", ""),
            auth_mode=os.environ.get("KB_AUTH_MODE", "BASIC"),
            authorization=os.environ.get("KB_AUTHORIZATION", ""),
        )

        knowledge_bases = []
        kb_ids = configs.get("knowledgeBaseIds", [])
        for kb_id in kb_ids:
            knowledge_bases.append(
                KBReferenceConfig(
                    knowledge_base_id=kb_id,
                    external_id=os.environ.get("KB_EXTERNAL_ID", kb_id),
                    connection_id="env_default",
                )
            )

        kb_config = KBRetrievalConfig(
            connection=connection,
            knowledge_bases=knowledge_bases,
            retrieval_params=_normalize_retrieval_config(retrieval_config),
        )

        return {
            "connection": connection.__dict__,
            "knowledge_bases": [kb.__dict__ for kb in knowledge_bases],
            "retrieval_params": kb_config.retrieval_params,
        }


def _normalize_retrieval_config(raw: dict) -> dict:
    """直接返回原始检索参数，不做驼峰→下划线转换"""
    if not raw:
        return {}
    return dict(raw)


# ---------------------------------------------------------------------------
# OBSKnowledgeBaseConfigProvider
# ---------------------------------------------------------------------------


class OBSKnowledgeBaseConfigProvider(KnowledgeBaseConfigProvider):


    async def get_kb_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> dict:

        raw_configs = ir_node.get("configs", {})
        configs = _copy_configs(raw_configs)
        connection_id = configs.get("connectionId", "")

        if not connection_id:
            workflow_logger.warning(
                "Knowledge retrieval node missing connection_id, "
                "falling back to environment variables"
            )
            fallback = EnvVarKBConfigProvider()
            return await fallback.get_kb_config(ir_node, global_config)

        # 1. 从连接文件加载连接配置
        connection = await self._load_connection_config(connection_id)

        # 2. 从知识库文件加载知识库引用配置（获取 externalId）
        knowledge_bases: List[KBReferenceConfig] = []
        kb_ids = configs.get("knowledgeBaseIds", [])
        is_custom = (connection and connection.knowledge_source == "CUSTOM") if connection else False
        for kb_id in kb_ids:
            kb_ref = await self._load_kb_reference(kb_id)
            if kb_ref is not None:
                knowledge_bases.append(kb_ref)
            elif is_custom:
                # CUSTOM 模式：知识库不在本地 DB，OBS 无 reference 文件，
                # 直接用 KB ID 作为 external_id（CUSTOM 知识库的 ID 就是 LakeSearch 侧的 repo_id）
                knowledge_bases.append(
                    KBReferenceConfig(
                        knowledge_base_id=kb_id,
                        external_id=kb_id,
                        connection_id=connection_id,
                    )
                )
                workflow_logger.info(
                    f"CUSTOM mode: using kb_id as external_id: kb_id={kb_id}"
                )
            else:
                workflow_logger.warning(
                    f"Failed to load KB reference from OBS: kb_id={kb_id}"
                )

        if connection is None:
            connection = KBConnectionConfig(connection_id=connection_id)

        # 3. 合并 HTTP 请求头中的认证信息
        self._merge_auth_headers(connection)

        # 4. 提取并标准化检索参数
        retrieval_params = _normalize_retrieval_config(
            configs.get("retrievalConfig", {})
        )

        workflow_logger.info(
            f"KB config loaded: connection_id={connection_id}, "
            f"connector_type={connection.connector_type}, "
            f"kb_count={len(knowledge_bases)}"
        )

        return {
            "connection": connection.__dict__,
            "knowledge_bases": [kb.__dict__ for kb in knowledge_bases],
            "retrieval_params": retrieval_params,
        }

    async def _load_connection_config(self, connection_id: str) -> Optional[KBConnectionConfig]:

        cache_key = f"conn:{connection_id}"
        cached = _get_cached(cache_key)
        if cached:
            return self._parse_connection(cached)

        object_key = _OBS_CONNECTION_PATH_TEMPLATE.format(connection_id=connection_id)
        try:
            storage = get_storage_provider()
            content = await storage.get_content(object_key)
            data = json.loads(content)
        except Exception as e:
            workflow_logger.warning(
                f"Failed to load connection file from OBS: "
                f"connection_id={connection_id}, error={e}"
            )
            return None

        _set_cached(cache_key, data)
        return self._parse_connection(data)

    def _parse_connection(self, connection_data: dict) -> KBConnectionConfig:

        if not connection_data:
            return KBConnectionConfig()

        params_dict = {}
        for param in connection_data.get("params", []):
            code = param.get("code", "")
            value = param.get("value", "")
            # SECRET 类型参数在 OBS 中以密文存储，读取时解密
            if code in _SECRET_PARAM_CODES and value:
                value = CryptTool().decrypt(value)
            params_dict[code] = value

        connector_id = connection_data.get("connectorId", "")

        # authorization 为空但有 user_name + password 时，自动生成 Basic Auth
        authorization = params_dict.get("authorization", "")
        auth_mode = params_dict.get("auth_mode", "")

        if not authorization:
            user_name = params_dict.get("user_name", "")
            password = params_dict.get("password", "")
            if user_name and password:
                import base64
                auth_str = base64.b64encode(f"{user_name}:{password}".encode()).decode()
                authorization = auth_str  # adapter 会加 "Basic " 前缀
                auth_mode = "BASIC"

        # openjiuwen 连接文件中 model_config 以 JSON 字符串存储在 params 里
        model_config: Dict[str, Any] = {}
        mc_raw = params_dict.get("model_config", "")
        if mc_raw:
            try:
                model_config = json.loads(mc_raw)
            except (json.JSONDecodeError, TypeError):
                workflow_logger.warning(f"Failed to parse model_config JSON: {mc_raw}")

        reranker_config: Dict[str, Any] = {}
        rc_raw = params_dict.get("reranker_config", "")
        if rc_raw:
            try:
                reranker_config = json.loads(rc_raw)
            except (json.JSONDecodeError, TypeError):
                workflow_logger.warning(f"Failed to parse reranker_config JSON: {rc_raw}")

        return KBConnectionConfig(
            connection_id=connection_data.get("connectionId", ""),
            connector_type=connector_id,
            connector_name=connection_data.get("connectorName", ""),
            knowledge_source=connection_data.get("knowledgeSource", ""),
            endpoint=params_dict.get("endpoint", ""),
            auth_mode=auth_mode,
            authorization=authorization,
            extra_params=params_dict,
            used_abilities=connection_data.get("usedAbilities", []),
            model_config=model_config,
            reranker_config=reranker_config,
        )

    async def _load_kb_reference(self, knowledge_base_id: str) -> Optional[KBReferenceConfig]:

        cache_key = f"kb:{knowledge_base_id}"
        cached = _get_cached(cache_key)
        if cached:
            return self._parse_kb_reference(cached)

        object_key = _OBS_KB_PATH_TEMPLATE.format(knowledge_base_id=knowledge_base_id)
        try:
            storage = get_storage_provider()
            content = await storage.get_content(object_key)
            data = json.loads(content)
        except Exception as e:
            workflow_logger.warning(
                f"Failed to load KB file from OBS: "
                f"kb_id={knowledge_base_id}, error={e}"
            )
            return None

        _set_cached(cache_key, data)
        return self._parse_kb_reference(data)

    @staticmethod
    def _parse_kb_reference(kb_data: dict) -> Optional[KBReferenceConfig]:

        if not kb_data:
            return None

        return KBReferenceConfig(
            knowledge_base_id=kb_data.get("knowledgeBaseId", ""),
            knowledge_base_name=kb_data.get("knowledgeBaseName", ""),
            type=kb_data.get("type", ""),
            external_id=kb_data.get("externalId", ""),
            status=kb_data.get("status", ""),
            connection_id=kb_data.get("connectionId", ""),
            tags=kb_data.get("tags", []) or [],
        )

    def _merge_auth_headers(self, connection: KBConnectionConfig) -> None:
        ctx = _request_ctx.get()
        if not ctx or not ctx.headers:
            return

        if connection.authorization:
            return

        # 仅 LakeSearch 系列和 Custom（底层也是 LakeSearchAdapter）允许用用户 token 兜底。
        # LakeSearchInside / Custom 在 KBAdapterFactory 中都映射到 LakeSearchAdapter。
        # RAGFlow / KooSearch / General 等外部服务使用独立凭证，
        # 用户 token 不可作为鉴权信息，不应填充。
        connector_type = (connection.connector_type or "").lower()
        if not (connector_type.startswith("lakesearch")
                or connector_type in ("custom", "")):
            return

        auth_token = (
            ctx.headers.get("x-auth-token", "")
            or ctx.headers.get("X-Auth-Token", "")
        )
        if auth_token:
            connection.authorization = auth_token
            connection.auth_mode = connection.auth_mode or "TOKEN"
