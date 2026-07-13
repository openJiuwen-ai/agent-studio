# -*- coding: utf-8 -*-
"""OBS 元数据与 auth 解析、三层缓存、refresh。

移植自 Java ``ModelStorageService`` 与 ``ModelAuthStorageService``（V2 直查；authId 在 IR 中
确定，不再遍历扫描）。

- ``model-service/ir/{modelServiceId}.json`` → ``ModelServiceBase``（{type, data}）
- ``model-auth/auth/{projectId}/{providerId}/{authId}.json`` → ``ProviderAuth``
- 三层缓存：L1 内存(60s) → L2 Redis → OBS；``refresh=True`` 时旁路缓存直读 OBS 并回填。
- 平台模型（``project_id`` 属于 ``PLATFORM_PROJECT_IDS``）Redis 无 TTL；其余使用默认 TTL。
- 加解密预留接口，当前明文直通（见 ``decrypt``）。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# OBS 对象 key 模板（对应 Java ModelStorageService / ModelAuthStorageService 的路径规则）。
MODEL_PATH = "model-service/ir/%s.json"
AUTH_PATH = "model-auth/auth/%s/%s/%s.json"          # projectId / providerId / authId

# 平台模型判定：project_id == "SYSTEM"（对应 Java isPlatformModel）。
PLATFORM_PROJECT_IDS = {"SYSTEM"}

_logger = logging.getLogger("model_service.resolver")


class ModelServiceError(Exception):
    """模型服务粗粒度异常，code 复用 Java ``StudioError`` 名串。"""

    def __init__(self, code: str, msg: str = ""):
        self.code = code
        self.msg = msg
        super().__init__(f"[{code}] {msg}")


class InterfaceProtocol(str, Enum):
    """interfaceProtocol 归一为两种格式，由 ``dispatch.normalize_protocol`` 映射。"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class ModelServiceBase:
    id: str
    model_name: str
    api_url: str
    provider_id: str
    interface_protocol: InterfaceProtocol
    project_id: str
    workspace_id: str
    auth_id: str
    throttling_policy: Optional[int] = None      # 限流字段，当前未使用


@dataclass
class ProviderAuth:
    auth_id: str
    auth_type: str            # "API_KEY" | "CUSTOM_APIKEY"
    auth_info: dict           # API_KEY → {"api_key": ...}；CUSTOM_APIKEY → {header: value}


@dataclass
class ModelServiceDetail:
    model: ModelServiceBase
    auth: Optional[ProviderAuth]
    available: bool
    is_free_model: bool       # 保留字段，当前恒为 False


class StrategyType(str, Enum):
    MODEL = "model"           # 单模型
    ROUTER = "router"         # 多模型 failover


@dataclass
class ModelStrategy:
    type: StrategyType
    name: str
    models: list[ModelServiceDetail]
    retry_count: int = 0
    strategy_timeout_ms: int = 600_000          # 默认 10min，对应 Java defaultTimeout


def decrypt(value: str) -> str:
    """加解密预留接口：当前明文直通。接入真实加解密时替换此函数即可。"""
    return value


def _is_platform(project_id: str) -> bool:
    return project_id in PLATFORM_PROJECT_IDS


def _auth_project_id(model_project_id: str, caller_project_id: str) -> str:
    """auth 查询使用的 projectId（对应 Java ``getModelServiceDetail``）。

    模型本身为平台模型时用调用方 projectId，否则用模型自身的 projectId。
    """
    return caller_project_id if _is_platform(model_project_id) else model_project_id


def _cache_ttl_for_model(metadata: dict) -> Optional[int]:
    """计算 model-service 缓存 TTL：平台模型返回 -1（无 TTL），其余返回 None（用默认 TTL）。"""
    if metadata.get("type") == "router":
        return None
    data = metadata.get("data") or {}
    return -1 if _is_platform(str(data.get("project_id", ""))) else None


async def resolve_strategy(
    model_service_id: str,
    project_id: str,
    workspace_id: str,
    auth_id: str,
    *,
    refresh: bool = False,
) -> Optional[ModelStrategy]:
    """解析模型服务策略（对应 Java ``ModelStorageService.queryModelStrategy``）。

    Args:
        model_service_id: 模型服务 ID（OBS 对象 key 的一部分）。
        project_id: 调用方 projectId，用于平台模型的 auth 查询路径。
        workspace_id: 工作空间 ID。
        auth_id: auth ID；为空时不解析 auth。
        refresh: 是否旁路缓存、强制读 OBS 并回填。

    Returns:
        ``ModelStrategy``；OBS 中不存在该对象时返回 None。
    """
    metadata = await _query_model_metadata(model_service_id, refresh)
    if metadata is None:
        return None
    return await _build_strategy(metadata, project_id, workspace_id, auth_id, refresh)


async def _build_strategy(metadata, project_id, workspace_id, auth_id, refresh) -> ModelStrategy:
    mtype = metadata.get("type")
    data = metadata.get("data") or {}
    if mtype == "router":
        return await _build_router_strategy(data, project_id, workspace_id, refresh)
    model = _model_from_data(data)
    detail = await _build_detail(model, project_id, workspace_id, auth_id, refresh)
    return ModelStrategy(type=StrategyType.MODEL, name=model.model_name, models=[detail])


async def _build_router_strategy(data, project_id, workspace_id, refresh) -> ModelStrategy:
    """构造 ROUTER 策略（对应 Java ``getRouterStrategy``）。

    拆分 ``service_id_list`` / ``auth_id_list``，逐子模型解析，并携带 ``strategy_timeout`` /
    ``strategy_retry_count``。字段名对齐 Java ``RouterStrategyEntity``（全 snake_case）。
    """
    service_id_list = data.get("service_id_list") or ""
    model_ids = [s for s in service_id_list.split(",") if s]
    if not model_ids:
        raise ModelServiceError("UNEXPECTED_ERROR", "Router strategy config is invalid.")
    auth_id_list = data.get("auth_id_list") or ""
    auth_ids = [a for a in auth_id_list.split(",") if a] if auth_id_list else [""]

    details: list[ModelServiceDetail] = []
    for idx, mid in enumerate(model_ids):
        child = await _query_model_metadata(mid, refresh)
        if child is None:
            raise ModelServiceError("MD_MODEL_ROUTER_INVALID", f"router miss model {mid}")
        child_model = _model_from_data(child.get("data") or {})
        aid = auth_ids[min(idx, len(auth_ids) - 1)]
        details.append(await _build_detail(child_model, project_id, workspace_id, aid, refresh))

    return ModelStrategy(
        type=StrategyType.ROUTER,
        name=data.get("strategy_key") or "",
        models=details,
        retry_count=int(data.get("strategy_retry_count") or 0),
        strategy_timeout_ms=int(data.get("strategy_timeout") or 600_000),
    )


async def _build_detail(model, project_id, workspace_id, auth_id, refresh) -> ModelServiceDetail:
    """构造单模型 detail（对应 Java ``getModelServiceDetail``）。

    解析 auth；``available`` 取决于 auth 是否存在（free model 当前恒为 False）。
    """
    auth_proj = _auth_project_id(model.project_id, project_id)
    auth = await _query_auth(auth_proj, model.provider_id, auth_id, refresh) if auth_id else None
    available = auth is not None
    return ModelServiceDetail(model=model, auth=auth, available=available, is_free_model=False)


def _model_from_data(data: dict) -> ModelServiceBase:
    # 延迟导入 normalize_protocol，避免与 dispatch 的循环依赖。
    from .dispatch import normalize_protocol
    return ModelServiceBase(
        id=str(data.get("id", "")),
        model_name=data.get("model_name", ""),
        api_url=data.get("api_url", ""),
        provider_id=str(data.get("provider_id", "")),
        interface_protocol=normalize_protocol(data.get("interface_protocol", "")),
        project_id=str(data.get("project_id", "")),
        workspace_id=str(data.get("workspace_id", "")),
        auth_id=str(data.get("auth_metadata_id", "")),
    )


async def _query_model_metadata(model_id: str, refresh: bool) -> Optional[dict]:
    """读取模型元数据：缓存 → OBS，带性能日志与降级。"""
    from openjiuwen.core.common.logging import performance_logger
    from agent_runtime.storage import get_storage_provider
    from agent_runtime.common.ir_interfaces import StorageNotFoundError
    from jiuwen.serve.controllers.execution.open_utils import cache_model_service_queue

    key = MODEL_PATH % model_id
    t_start = time.perf_counter()
    if not refresh:
        try:
            cached, source = await cache_model_service_queue.aget_with_source(key)
            if cached is not None:
                performance_logger.info(
                    f"model_service_load|{round((time.perf_counter() - t_start) * 1000)}|{source}")
                return cached
        except Exception as e:   # 缓存层异常，降级到 OBS 并告警
            _logger.warning("model-service cache read failed key=%s: %s", key, e)

    storage = get_storage_provider()
    try:
        content = await storage.get_content(key)
    except StorageNotFoundError:
        return None                       # 对象不存在视为未配置
    except Exception as e:                # 传输 / 解析失败视为 OBS 不可达
        raise ModelServiceError("MD_OBS_READ_ERROR", f"read model metadata {key}: {e}") from e
    try:
        metadata = json.loads(content)
    except Exception as e:
        raise ModelServiceError("MD_OBS_READ_ERROR", f"parse model metadata {key}: {e}") from e
    try:
        await cache_model_service_queue.aput(key, metadata, ttl=_cache_ttl_for_model(metadata))
    except Exception as e:
        _logger.warning("model-service cache write failed key=%s: %s", key, e)
    performance_logger.info(
        f"model_service_load|{round((time.perf_counter() - t_start) * 1000)}|obs")
    return metadata


async def _query_auth(project_id, provider_id, auth_id, refresh) -> Optional[ProviderAuth]:
    """读取 auth（V2 直查，对应 Java ``queryProviderAuthV2``）：缓存 → OBS，带性能日志与降级。"""
    from openjiuwen.core.common.logging import performance_logger
    from agent_runtime.storage import get_storage_provider
    from agent_runtime.common.ir_interfaces import StorageNotFoundError
    from jiuwen.serve.controllers.execution.open_utils import cache_model_auth_queue

    key = AUTH_PATH % (project_id, provider_id, auth_id)
    t_start = time.perf_counter()
    if not refresh:
        try:
            cached, source = await cache_model_auth_queue.aget_with_source(key)
            if cached is not None:
                performance_logger.info(
                    f"model_auth_load|{round((time.perf_counter() - t_start) * 1000)}|{source}")
                return _auth_from_data(cached)
        except Exception as e:
            _logger.warning("model-auth cache read failed key=%s: %s", key, e)

    storage = get_storage_provider()
    try:
        content = await storage.get_content(key)
    except StorageNotFoundError:
        return None                       # auth 不存在视为未配置
    except Exception as e:
        raise ModelServiceError("MD_OBS_READ_ERROR", f"read auth {key}: {e}") from e
    try:
        auth_data = json.loads(content)
    except Exception as e:
        raise ModelServiceError("MD_OBS_READ_ERROR", f"parse auth {key}: {e}") from e
    try:
        # auth 缓存使用默认 TTL（5min），与 Java ModelAuthStorageService 一致。
        await cache_model_auth_queue.aput(key, auth_data)
    except Exception as e:
        _logger.warning("model-auth cache write failed key=%s: %s", key, e)
    performance_logger.info(
        f"model_auth_load|{round((time.perf_counter() - t_start) * 1000)}|obs")
    return _auth_from_data(auth_data)


def _auth_from_data(auth_data: dict) -> Optional[ProviderAuth]:
    """由 auth JSON 构造 ``ProviderAuth``（对应 Java ``getProviderAuth``）。

    - ``API_KEY``：取 ``auth_info["API Key"]`` 作为 api_key。
    - ``CUSTOM_APIKEY``：``auth_info`` 各项作为自定义 header，``cust-`` 前缀剥离。
    """
    auth_id = str(auth_data.get("id", ""))
    auth_type = auth_data.get("auth_type", "")
    raw = auth_data.get("auth_info", "")
    if auth_type == "API_KEY":
        info = json.loads(raw) if raw else {}
        return ProviderAuth(auth_id=auth_id, auth_type="API_KEY",
                            auth_info={"api_key": decrypt(info.get("API Key", ""))})
    if auth_type == "CUSTOM_APIKEY":
        info = json.loads(raw) if raw else {}
        return ProviderAuth(auth_id=auth_id, auth_type="CUSTOM_APIKEY",
                            auth_info={k: decrypt(v) for k, v in info.items()})
    return ProviderAuth(auth_id=auth_id, auth_type=auth_type, auth_info={})
