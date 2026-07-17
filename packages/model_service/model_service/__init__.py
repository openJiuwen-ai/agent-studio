# -*- coding: utf-8 -*-
"""模型调用机制层共享包（runtime / agent-builder 共用）。

机制层（OBS 解析 / 鉴权 / 策略 / 审计）从 Java ``studio-runtime-service`` 移植，集中于此包，
供 runtime 进程内调用与 agent-builder HTTP facade 复用，避免两套实现漂移。各模块 docstring
标注对应的 Java 源类。导入本包即触发 ``StudioModelClient`` 注册进 openjiuwen client registry
（``client_provider="studio"``）。
"""

from .resolver import (
    InterfaceProtocol, ModelServiceBase, ModelServiceDetail, ModelStrategy,
    ProviderAuth, StrategyType, resolve_strategy,
)
from .authz import assert_project_id_trusted, check_authz, extract_project_id
from .policy import AuditLog, alarm, invoke_with_strategy, record_audit
from .dispatch import build_httpx_client, embed, get_chat_connection, normalize_protocol, rerank
from .client import StudioModelClient

__all__ = [
    # resolver
    "InterfaceProtocol", "ModelServiceBase", "ModelServiceDetail", "ModelStrategy",
    "ProviderAuth", "StrategyType", "resolve_strategy",
    # authz
    "extract_project_id", "assert_project_id_trusted", "check_authz",
    # policy
    "AuditLog", "record_audit", "alarm", "invoke_with_strategy",
    # dispatch
    "get_chat_connection", "normalize_protocol", "embed", "rerank", "build_httpx_client",
    # client
    "StudioModelClient",
]
