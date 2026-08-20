# -*- coding: utf-8 -*-
"""model_service 与宿主（agent_runtime / agent_builder）的解耦端口。

model_service 作为共享机制层（OBS 解析 / 鉴权 / 策略 / 审计 / 客户端），**不直接 import
任何宿主包**（不 import agent_runtime，也不 import jiuwen）。storage / llm settings /
request-context / cache 由宿主在启动时通过 ``set_*`` 注入：

- agent_runtime：注入其 ``S3StorageProvider``（经 ``wrap_storage`` 翻译 not-found）、
  ``settings.llm``、``_request_ctx`` 请求头、``jiuwen`` 的 ``cache_model_*_queue``。
- agent_builder：注入其 ``storage_bridge``（直接 raise 本模块 ``StorageNotFoundError``）、
  ``config_bridge.settings.llm``、``request_context_bridge`` 请求头；cache 可不注入（跳过 L2）。

未注入而调用 getter 时抛 ``RuntimeError``（fail-fast，避免静默漂移到错误实现）。
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Protocol, runtime_checkable

# OBS 对象不存在异常，复用共享包 storage 的定义（agent_runtime / agent_builder 共用同一类），
# 使 model_service resolver 的 ``except StorageNotFoundError`` 与共享 storage provider 抛出的异常一致。
from storage.exceptions import StorageNotFoundError


# customer Header 强类型，引用公共 customer_header 模块（不反向依赖 runtime/宿主）
@runtime_checkable
class StorageProvider(Protocol):
    """对象存储提供者协议（agent_runtime / agent_builder 各自实现）。"""

    async def get_content(self, key: str) -> str:
        """读取对象文本内容；对象不存在抛 ``StorageNotFoundError``。"""

    async def list_keys(self, prefix: str) -> "list[str]":
        """列举前缀下的对象 key 列表。"""


@runtime_checkable
class LLMSettingsLike(Protocol):
    """LLM 连接参数协议（timeout / ssl_verify），取自宿主 settings.llm。"""

    timeout: float
    ssl_verify: bool


@runtime_checkable
class CacheQueueLike(Protocol):
    """多级缓存队列协议（可选）；未注入则 resolver 跳过 L1/L2 直读 OBS。"""

    async def aget_with_source(self, key: str) -> Any:
        """返回 (value, source) 二元组；未命中返回 (None, '')。"""

    async def aput(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """写入缓存。"""


# ── registry ───────────────────────────────────────────────────────────────────

# ── registry ───────────────────────────────────────────────────────────────────

# 哨兵：区分“未注册”（回退到 agent_runtime/jiuwen）与“显式注册为 None”（禁用该项）。
# 直接用 None 表示禁用会与“未注册”混淆，导致 set_cache_queues(None,None) 反而触发回退。
_UNSET = object()

_storage_factory: Optional[Callable[[], StorageProvider]] = None
_llm_settings_factory: Optional[Callable[[], LLMSettingsLike]] = None
_request_headers_fn: Optional[Callable[[], dict]] = None
_model_cache: Any = _UNSET
_auth_cache: Any = _UNSET


def set_storage_provider(factory: Optional[Callable[[], StorageProvider]]) -> None:
    """注册 storage provider 工厂（每次解析时调用，返回当前应使用的 provider 实例）。"""
    global _storage_factory
    _storage_factory = factory


def get_storage_provider() -> StorageProvider:
    if _storage_factory is not None:
        return _storage_factory()
    # 回退：共享包 storage 的 get_storage_provider（agent_runtime / agent_builder 均在其
    # lifespan 注册了 settings + 初始化 S3）。model_service 自身不 import 任何宿主。
    import storage
    return storage.get_storage_provider()


def set_llm_settings(factory: Optional[Callable[[], LLMSettingsLike]]) -> None:
    global _llm_settings_factory
    _llm_settings_factory = factory


def get_llm_settings() -> LLMSettingsLike:
    if _llm_settings_factory is not None:
        return _llm_settings_factory()
    from agent_runtime.common.config import settings
    return settings.llm


def set_request_headers(fn: Optional[Callable[[], dict]]) -> None:
    """注册请求头提供者（返回当前请求的 headers dict；StudioModelClient._resolve_inputs 用）。"""
    global _request_headers_fn
    _request_headers_fn = fn


def get_request_headers() -> dict:
    if _request_headers_fn is not None:
        try:
            return _request_headers_fn() or {}
        except Exception:
            return {}
    try:
        from agent_runtime.context.request_context import _request_ctx
        ctx = _request_ctx.get()
        return ctx.headers if ctx else {}
    except Exception:
        return {}


# ── 独立 customer Header provider（强类型，不退化为无 provenance 的 dict） ──

_customer_headers_fn: Optional[Callable[[], dict[str, str]]] = None


def set_request_customer_headers(fn: Optional[Callable[[], dict[str, str]]]) -> None:
    """注册客户 Header 提供者（返回当前请求的 customer headers dict[str, str]）。

    model_service.ports 只暴露 provider 注册/读取端口，不拥有宿主上下文，
    也不把强类型值退化为无 provenance 的 dict[str, str]。
    无请求上下文时返回空 customer headers，不得回退静态认证 Header。
    """
    global _customer_headers_fn
    _customer_headers_fn = fn


def get_request_customer_headers() -> dict[str, str]:
    """获取当前请求的客户 Header（dict[str, str]）。

    无注册或无上下文时返回空 dict（host-free：不回退 agent_runtime 宿主上下文）。
    """
    if _customer_headers_fn is not None:
        try:
            return _customer_headers_fn() or {}
        except Exception:
            return {}
    # 未注册 → 返回空（不反向 import agent_runtime，不回退静态认证 Header）
    return {}


def set_cache_queues(
    model_cache: Optional[CacheQueueLike] = None,
    auth_cache: Optional[CacheQueueLike] = None,
) -> None:
    """注册 model-service / auth 的 L2 缓存队列（可选；None 表示该项跳过缓存）。"""
    global _model_cache, _auth_cache
    _model_cache = model_cache
    _auth_cache = auth_cache


def get_model_cache() -> Optional[CacheQueueLike]:
    if _model_cache is not _UNSET:
        return _model_cache  # 显式注册（含 None=禁用）
    # 未注册 → 回退 jiuwen（仅 agent_runtime 宿主 / 既有测试）
    try:
        from jiuwen.serve.controllers.execution.open_utils import cache_model_service_queue
        return cache_model_service_queue
    except Exception:
        return None


def get_auth_cache() -> Optional[CacheQueueLike]:
    if _auth_cache is not _UNSET:
        return _auth_cache  # 显式注册（含 None=禁用）
    try:
        from jiuwen.serve.controllers.execution.open_utils import cache_model_auth_queue
        return cache_model_auth_queue
    except Exception:
        return None


# ── 适配 helper ─────────────────────────────────────────────────────────────────


def wrap_storage(provider: Any, not_found_exc: type) -> StorageProvider:
    """包装宿主 storage provider，把宿主的 not-found 异常翻译为本模块 ``StorageNotFoundError``。

    供 agent_runtime 使用（其 ``S3StorageProvider`` 抛 ``agent_runtime...StorageNotFoundError``）；
    agent_builder 的 storage_bridge 直接抛本模块异常，无需包装。

    返回的对象实现 ``get_content`` / ``list_keys``（list_keys 透传，不翻译）。
    """

    class _AdaptedStorage:
        async def get_content(self, key: str) -> str:
            try:
                return await provider.get_content(key)
            except not_found_exc as e:
                raise StorageNotFoundError(str(e)) from e

        async def list_keys(self, prefix: str) -> "list[str]":
            return await provider.list_keys(prefix)

    return _AdaptedStorage()

