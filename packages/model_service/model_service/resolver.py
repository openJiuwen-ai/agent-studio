# -*- coding: utf-8 -*-
"""OBS 元数据与 auth 解析、三层缓存、refresh。

移植自 Java ``ModelStorageService`` 与 ``ModelAuthStorageService``（V2 直查；authId 在 IR 中
确定，不再遍历扫描）。

- ``model-service/ir/{modelServiceId}.json`` → ``ModelServiceBase``（{type, data}）
- ``model-auth/auth/{projectId}/{providerId}/{authId}.json`` → ``ProviderAuth``
- 三层缓存：L1 内存(60s) → L2 Redis → OBS；``refresh=True`` 时旁路缓存直读 OBS 并回填。
- 平台模型（``project_id`` 属于 ``PLATFORM_PROJECT_IDS``）Redis 无 TTL；其余使用默认 TTL。
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

from .env_resolver import has_env_placeholder, resolve_env_placeholders

# OBS 对象 key 模板（对应 Java ModelStorageService / ModelAuthStorageService 的路径规则）。
MODEL_PATH = "model-service/ir/%s.json"
AUTH_PATH = "model-auth/auth/%s/%s/%s.json"          # projectId / providerId / authId
AUTH_LIST_PATH = "model-auth/auth/%s/%s/"             # projectId / providerId（V1 列举回退）

# 平台模型判定：project_id == "SYSTEM"（对应 Java isPlatformModel）。
PLATFORM_PROJECT_IDS = {"SYSTEM"}

_logger = logging.getLogger("model_service.resolver")


class ModelServiceError(Exception):
    """模型服务粗粒度异常，code 复用 Java ``StudioError`` 名串。

    ``upstream_status`` / ``upstream_body`` 仅在 ``MD_INVOKE_MODEL_SERVICE_FAIL`` 等
    上游调用失败场景携带，用于在 facade 层无损重建旧 Java ``ErrorRsp`` 契约
    （透传上游真实 status、原始 body 进 ``details[0].error_msg``）。
    """

    def __init__(self, code: str, msg: str = "", *,
                 upstream_status: Optional[int] = None,
                 upstream_body: Optional[str] = None):
        self.code = code
        self.msg = msg
        self.upstream_status = upstream_status
        self.upstream_body = upstream_body
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


@dataclass(frozen=True)
class ResolveCtx:
    """单次策略解析的共享上下文（``project_id`` / ``workspace_id`` / ``refresh`` / ``env_vars``）。

    将 ``_build_strategy`` / ``_build_detail`` 等 private 解析函数的关联参数收敛为一个具名对象，
    降低参数个数（G.FNM.03）。``auth_id`` 因路由场景下逐子模型不同（取自 ``auth_id_list``），
    不并入 ctx，仍作为独立参数传入。
    """
    project_id: str
    workspace_id: str
    refresh: bool = False
    env_vars: Optional[dict] = None



def _load_aes_gcm_decrypt():
    """Lazily import AES-GCM decrypt; returns None if pycryptodome is unavailable."""
    try:
        from Crypto.Cipher import AES  # type: ignore
    except Exception:  # pragma: no cover - fallback when crypto dep missing
        return None
    return AES


def _try_aes_gcm_decrypt(value: str) -> Optional[str]:
    """Attempt to AES-GCM-decrypt ``value`` using ``SYSTEM_CRYPT_KEY``.

    Mirrors Java ``AesGcmCipher`` wire layout: ``hex(nonce 12B) + hex(ciphertext) + hex(tag 16B)``
    (i.e. raw = nonce || ct || tag). Used to unwrap at-rest auth values the Java manager encrypted
    before syncing to OBS; this is NOT the import/export "ENCRYPTED" PoC path (that was removed).

    Returns None if (a) env says NoOp, (b) key not configured, (c) value doesn't look like a hex
    ciphertext of sufficient length, or (d) tag verification fails — callers treat None as "not
    ciphertext" and return the original value.
    """
    crypt_name = os.environ.get("SYSTEM_CRYPT_NAME", "")
    if crypt_name and crypt_name.upper() not in ("AES_GCM", "AES-GCM"):
        return None
    key_hex = os.environ.get("SYSTEM_CRYPT_KEY", "")
    if not key_hex:
        return None
    if not value or len(value) < 2 * (12 + 16 + 1):  # nonce(12)+tag(16)+>=1B ct
        return None
    try:
        key = bytes.fromhex(key_hex)
        raw = bytes.fromhex(value)
    except ValueError:
        return None
    nonce, tag, ct = raw[:12], raw[-16:], raw[12:-16]
    aes_gcm = _load_aes_gcm_decrypt()
    if aes_gcm is None:
        return None
    try:
        return aes_gcm.new(key, aes_gcm.MODE_GCM, nonce=nonce).decrypt_and_verify(ct, tag).decode("utf-8")
    except ValueError:
        # UnicodeDecodeError 是 ValueError 子类，并入此类；密钥/nonce/tag 校验失败或
        # 解密后非合法 UTF-8 均视为"非本布局密文"，返回 None 让调用方回退原值。
        return None


def decrypt(value: str) -> str:
    """Decrypt an at-rest auth value (API key / header).

    Tries AES-GCM first when ``SYSTEM_CRYPT_NAME=AES_GCM`` + ``SYSTEM_CRYPT_KEY`` are set and the
    value is a hex ciphertext in the Java AesGcmCipher layout. Returns the original string
    otherwise (plaintext / MASKED placeholder / non-hex values).
    """
    if not value:
        return value
    plain = _try_aes_gcm_decrypt(value)
    return plain if plain is not None else value


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
    env_vars: Optional[dict] = None,
) -> Optional[ModelStrategy]:
    """解析模型服务策略（对应 Java ``ModelStorageService.queryModelStrategy``）。

    Args:
        model_service_id: 模型服务 ID（OBS 对象 key 的一部分）。
        project_id: 调用方 projectId，用于平台模型的 auth 查询路径。
        workspace_id: 工作空间 ID。
        auth_id: auth ID；为空时不解析 auth。
        refresh: 是否旁路缓存、强制读 OBS 并回填。
        env_vars: 环境变量 dict（``load_environment_variables`` 产出）。``api_url`` 含
            ``${_env.plugin_url_params.VAR}`` 占位符时用于替换为真实值；``None`` 时跳过
            解析（向后兼容，等价于历史 verbatim 行为）。

    Returns:
        ``ModelStrategy``；OBS 中不存在该对象时返回 None。
    """
    metadata = await _query_model_metadata(model_service_id, refresh)
    if metadata is None:
        return None
    ctx = ResolveCtx(project_id=project_id, workspace_id=workspace_id,
                     refresh=refresh, env_vars=env_vars)
    return await _build_strategy(metadata, ctx, auth_id)


async def _build_strategy(
    metadata: dict, ctx: ResolveCtx, auth_id: str = "",
) -> ModelStrategy:
    mtype = metadata.get("type")
    data = metadata.get("data") or {}
    if mtype == "router":
        return await _build_router_strategy(data, ctx)
    model = _model_from_data(data)
    detail = await _build_detail(model, ctx, auth_id)
    return ModelStrategy(type=StrategyType.MODEL, name=model.model_name, models=[detail])


async def _build_router_strategy(
    data: dict, ctx: ResolveCtx,
) -> ModelStrategy:
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
        child = await _query_model_metadata(mid, ctx.refresh)
        if child is None:
            raise ModelServiceError("MD_MODEL_ROUTER_INVALID", f"router miss model {mid}")
        child_model = _model_from_data(child.get("data") or {})
        aid = auth_ids[min(idx, len(auth_ids) - 1)]
        details.append(await _build_detail(child_model, ctx, aid))

    return ModelStrategy(
        type=StrategyType.ROUTER,
        name=data.get("strategy_key") or "",
        models=details,
        retry_count=int(data.get("strategy_retry_count") or 0),
        strategy_timeout_ms=int(data.get("strategy_timeout") or 600_000),
    )


async def _build_detail(
    model: ModelServiceBase, ctx: ResolveCtx, auth_id: str = "",
) -> ModelServiceDetail:
    """构造单模型 detail（对应 Java ``getModelServiceDetail``）。

    解析 auth；``available`` 取决于 auth 是否存在（free model 当前恒为 False）。
    authId 为空时回退到 V1 列举（对应 Java ``queryProviderAuth`` → ``queryProviderAuthV1``），
    按 workspace 匹配取 auth，与 Java 网关"不传 authId 也能用"的行为一致。

    api_url 含 ``${_env.plugin_url_params.VAR}`` 占位符时，用 env_vars 替换为真实值
    （跨环境迁移的字面量 apiUrl 在此解析，与管理侧 ``UrlCheckUtils.validateEnvVarPlaceholders``
    校验同源）。无占位符或 env_vars 为 None 时跳过、保持 verbatim（向后兼容）。缺变量
    fail-fast 抛 ``MD_ENV_VAR_UNRESOLVED``（对应 Java ``MODEL_ENV_VAR_UNRESOLVED`` / 1083）。
    """
    if has_env_placeholder(model.api_url):
        model = replace(
            model, api_url=resolve_env_placeholders(model.api_url, ctx.env_vars),
        )
    auth_proj = _auth_project_id(model.project_id, ctx.project_id)
    if auth_id:
        auth = await _query_auth(auth_proj, model.provider_id, auth_id, ctx.refresh)
    else:
        auth = await _query_auth_v1(
            auth_proj, model.provider_id, ctx.workspace_id, model.workspace_id, ctx.refresh
        )
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
    from .ports import get_storage_provider, get_model_cache, StorageNotFoundError

    key = MODEL_PATH % model_id
    t_start = time.perf_counter()
    cache = get_model_cache()
    if cache is not None and not refresh:
        try:
            cached, source = await cache.aget_with_source(key)
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
    if cache is not None:
        try:
            await cache.aput(key, metadata, ttl=_cache_ttl_for_model(metadata))
        except Exception as e:
            _logger.warning("model-service cache write failed key=%s: %s", key, e)
    performance_logger.info(
        f"model_service_load|{round((time.perf_counter() - t_start) * 1000)}|obs")
    return metadata


async def _query_auth(project_id, provider_id, auth_id, refresh) -> Optional[ProviderAuth]:
    """读取 auth（V2 直查，对应 Java ``queryProviderAuthV2``）：缓存 → OBS，带性能日志与降级。"""
    from openjiuwen.core.common.logging import performance_logger
    from .ports import get_storage_provider, get_auth_cache, StorageNotFoundError

    key = AUTH_PATH % (project_id, provider_id, auth_id)
    t_start = time.perf_counter()
    cache = get_auth_cache()
    if cache is not None and not refresh:
        try:
            cached, source = await cache.aget_with_source(key)
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
    if cache is not None:
        try:
            # auth 缓存使用默认 TTL（5min），与 Java ModelAuthStorageService 一致。
            await cache.aput(key, auth_data)
        except Exception as e:
            _logger.warning("model-auth cache write failed key=%s: %s", key, e)
    performance_logger.info(
        f"model_auth_load|{round((time.perf_counter() - t_start) * 1000)}|obs")
    return _auth_from_data(auth_data)


async def _query_auth_v1(project_id, provider_id, workspace_id, model_workspace, refresh) -> Optional[ProviderAuth]:
    """V1 回退：authId 为空时列 ``model-auth/auth/{projectId}/{providerId}/`` 目录取 auth。

    移植自 Java ``ModelAuthStorageService.getProviderAuthFromObsV1``（旧数据兼容路径，
    Java 日志 "Query provider auth from old data."）。不写 L2 缓存（与 Java V1 仅用 localCache 一致，
    且 V1 是 rare/legacy 路径）。

    - 列举目录下对象；空 → None。
    - workspaceId 为空 → 取第一个 ``.json`` 对象。
    - 否则按 auth 的 workspaceId 匹配请求 workspaceId 或模型自带 workspaceId，命中即取。
    - 无命中 → None。
    """
    from openjiuwen.core.common.logging import performance_logger
    from .ports import get_storage_provider, StorageNotFoundError

    prefix = AUTH_LIST_PATH % (project_id, provider_id)
    t_start = time.perf_counter()
    storage = get_storage_provider()
    try:
        keys = await storage.list_keys(prefix)
    except Exception as e:
        raise ModelServiceError("MD_OBS_READ_ERROR", f"list auth {prefix}: {e}") from e
    keys = [k for k in keys if k.endswith(".json")]
    if not keys:
        return None

    async def _read(key):
        try:
            return await storage.get_content(key)
        except StorageNotFoundError:
            return None
        except Exception as e:
            raise ModelServiceError("MD_OBS_READ_ERROR", f"read auth {key}: {e}") from e

    selected = None
    if not workspace_id:
        selected = await _read(keys[0])
        if selected is None:
            return None
        data = json.loads(selected)
    else:
        for key in keys:
            content = await _read(key)
            if content is None:
                continue
            data = json.loads(content)
            aw = str(
                data.get("workspace_id")
                if data.get("workspace_id") is not None
                else data.get("workspaceId", "")
            )
            if aw == workspace_id or (model_workspace and aw == model_workspace):
                selected = content
                break
        if selected is None:
            return None
        data = json.loads(selected)

    performance_logger.info(
        f"model_auth_load|{round((time.perf_counter() - t_start) * 1000)}|obs-v1")
    return _auth_from_data(data)


def _auth_from_data(auth_data: dict) -> Optional[ProviderAuth]:
    """由 auth JSON 构造 ``ProviderAuth``（对应 Java ``getProviderAuth``）。

    字段名兼容 camelCase（Java ``ProviderAuthData`` 实际写入格式）与 snake_case
    （ref-commit 测试 fixture 格式）两种，避免与 OBS 真实数据格式漂移。

    - ``API_KEY``：取 ``auth_info["API Key"]`` 作为 api_key。
    - ``CUSTOM_APIKEY``：``auth_info`` 各项作为自定义 header，**原样保留键**（含 ``cust-`` 前缀）；
      ``cust-`` 前缀剥离 + request-over-config 由调用点 ``resolve_outbound_headers`` 处理，非此处。
    """
    def _get(snake: str, camel: str):
        return auth_data.get(snake) if auth_data.get(snake) is not None else auth_data.get(camel)

    auth_id = str(auth_data.get("id", ""))
    auth_type = _get("auth_type", "authType") or ""
    raw = _get("auth_info", "authInfo") or ""
    if auth_type == "API_KEY":
        info = json.loads(raw) if raw else {}
        return ProviderAuth(auth_id=auth_id, auth_type="API_KEY",
                            auth_info={"api_key": decrypt(info.get("API Key", ""))})
    if auth_type == "CUSTOM_APIKEY":
        info = json.loads(raw) if raw else {}
        return ProviderAuth(auth_id=auth_id, auth_type="CUSTOM_APIKEY",
                            auth_info={k: decrypt(v) for k, v in info.items()})
    return ProviderAuth(auth_id=auth_id, auth_type=auth_type, auth_info={})
