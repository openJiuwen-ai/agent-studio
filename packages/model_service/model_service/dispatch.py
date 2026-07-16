# -*- coding: utf-8 -*-
"""按 interfaceProtocol 选择底层 client，并提供 embedding / rerank 入口。

移植自 Java ``RuntimeRequestAdapterFactory``，但收敛为两种协议：quirk adapter 全部移除，
当前仅实现 OPENAI 格式，ANTHROPIC 预留接口。OPENAI 协议下由 ``StudioModelClient`` 内联
``AsyncOpenAI`` 调用并复用 ``OpenAIModelClient`` 的 ``_parse_*``；本模块负责把解析出的
model / auth 归一为 ``ResolvedConnection``。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .resolver import InterfaceProtocol, ModelServiceBase, ModelServiceError, ProviderAuth

# OBS 原始 interfaceProtocol 字符串 → 两值归一。当前仅 OPENAI；ANTHROPIC 预留。
_PROTOCOL_MAP = {
    "openai": InterfaceProtocol.OPENAI,
    "multi_openai": InterfaceProtocol.OPENAI,
    "maasv2": InterfaceProtocol.OPENAI,
    "qwen": InterfaceProtocol.OPENAI,
    "zhipu": InterfaceProtocol.OPENAI,
    "standard": InterfaceProtocol.OPENAI,   # 样例 JSON 中 interface_protocol 为 STANDARD
    "anthropic": InterfaceProtocol.ANTHROPIC,   # 预留，当前未实现
}


def normalize_protocol(raw: str) -> InterfaceProtocol:
    """OBS 原始字符串映射为 OPENAI / ANTHROPIC；未知协议默认 OPENAI（对应 Java factory 行为）。"""
    return _PROTOCOL_MAP.get((raw or "").strip().lower(), InterfaceProtocol.OPENAI)


@dataclass
class ResolvedConnection:
    """单模型一次调用的连接参数（由 auth 解析而来），交给 ``StudioModelClient._invoke_one_model``。"""

    api_base: str
    api_key: str
    custom_headers: Optional[dict]
    model_name: str
    interface_protocol: InterfaceProtocol
    timeout: float
    verify_ssl: bool


def _normalize_api_base(url: str) -> str:
    """标准化 API base URL，去除末尾 ``/chat/completions``（对应旧 OBSModelConfigProvider._normalize_api_base）。"""
    url = (url or "").rstrip("/")
    if url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    return url


def build_httpx_client(api_base: str, verify_ssl: bool, ssl_cert: Optional[str] = None):
    """构造 httpx.AsyncClient，网络层与 openjiuwen ``OpenAIModelClient._create_async_openai_client`` 一致。

    复用父类的代理与严格 SSL 能力，仅保留对 api_base / verify_ssl / ssl_cert 的控制：

    - ``proxy``：取 ``UrlUtils.get_global_proxy_url(api_base)``，由环境变量
      （``http_proxy`` / ``https_proxy``，带 ``NO_PROXY`` 旁路）驱动；api_base 用 conn 真实目标，
      使 ``NO_PROXY`` 按真实 hostname 判定。
    - ``verify``：``verify_ssl=True`` 时构造 ``SslUtils.create_strict_ssl_context(ssl_cert)``
      严格 TLS context（TLS1.2+、锁定 cipher、可选 CA）；``verify_ssl=False`` 时直传 False。
      ``verify_ssl=True`` 需配 ``ssl_cert``，与父类契约一致。

    api_key / api_base / max_retries 仍由调用方从 conn 取，属 OBS 解析结果，不在此处处理。
    """
    import httpx
    from openjiuwen.core.common.security.ssl_utils import SslUtils
    from openjiuwen.core.common.security.url_utils import UrlUtils
    verify = SslUtils.create_strict_ssl_context(ssl_cert) if verify_ssl else verify_ssl
    return httpx.AsyncClient(
        proxy=UrlUtils.get_global_proxy_url(api_base),
        verify=verify,
    )


def _settings_llm():
    """timeout / verify_ssl 兜底取自 settings.llm（对应旧 OBSModelConfigProvider 的 base=settings.llm）。"""
    from agent_runtime.common.config import settings   # 延迟导入：agent_runtime 顶层反向 import model_service，顶层导入会循环
    return settings.llm


def get_chat_connection(model: ModelServiceBase, auth: Optional[ProviderAuth]) -> ResolvedConnection:
    """OPENAI 协议下，把 model + auth 归一为 ``ResolvedConnection``。

    对应 Java ``AuthAdapterFactory`` 与 ``doChatCompletions`` 的 auth-null 检查：

    - auth 为空 → fail-fast 抛 ``MD_PROVIDER_AUTH_DATA_NOT_EXIST``。
    - ``API_KEY``：api_key 取 ``auth_info["api_key"]``，无 custom_headers。
    - ``CUSTOM_APIKEY``：api_key 用占位，custom_headers 取 auth_info。

    ANTHROPIC 协议当前抛 ``PROTOCOL_NOT_SUPPORTED``，后续在此委托 openjiuwen
    ``AnthropicModelClient``。
    """
    if model.interface_protocol == InterfaceProtocol.ANTHROPIC:
        # 预留接口：后续在此委托 AnthropicModelClient（其响应解析无法复用 OpenAI _parse_*）。
        raise ModelServiceError("PROTOCOL_NOT_SUPPORTED", "ANTHROPIC 协议待实现（预留接口）")
    if auth is None:
        raise ModelServiceError("MD_PROVIDER_AUTH_DATA_NOT_EXIST",
                                f"auth not configured for model {model.id}")

    api_key = "sk-placeholder"
    custom_headers: Optional[dict] = None
    if auth.auth_type == "API_KEY":
        api_key = auth.auth_info.get("api_key", "") or "sk-placeholder"
    elif auth.auth_type == "CUSTOM_APIKEY":
        custom_headers = auth.auth_info or None
    # 其它 auth_type：保持占位 api_key，由模型端拒绝。

    base = _settings_llm()
    return ResolvedConnection(
        api_base=_normalize_api_base(model.api_url),
        api_key=api_key,
        custom_headers=custom_headers,
        model_name=model.model_name,
        interface_protocol=model.interface_protocol,
        timeout=base.timeout,
        verify_ssl=base.ssl_verify,
    )


# embedding / rerank：openjiuwen Model 无此抽象，单独提供入口。

async def embed(model, auth, request) -> object:
    """embedding 入口，供 agent-builder ``/v1/agent-builder/embeddings`` facade 调用。

    使用 openai SDK ``AsyncOpenAI().embeddings.create()``（与 chat 路径同源），请求体
    ``EmbeddingRequest`` → ``{model, input: List[str]}``（对应 Java ``maas_embedding``）。
    连接参数由 ``get_chat_connection`` 派生。
    """
    from openai import AsyncOpenAI
    conn = get_chat_connection(model, auth)
    client = AsyncOpenAI(api_key=conn.api_key, base_url=conn.api_base,
                         http_client=build_httpx_client(conn.api_base, conn.verify_ssl),
                         timeout=conn.timeout)
    try:
        resp = await client.embeddings.create(model=conn.model_name, input=request.input)
        return resp
    finally:
        await client.close()


async def rerank(model, auth, request) -> object:
    """rerank 入口，供 agent-builder ``/v1/agent-builder/rerank`` facade 调用。

    rerank 无 SDK 可用（非 OpenAI API），需用 httpx 移植 Java ``maas_rerank`` adapter
    （``RankDocumentsRequest`` → ``{model, query, documents}``，响应解析 + topN 截断）。当前未实现。
    """
    raise ModelServiceError("NOT_IMPLEMENTED", "rerank httpx port 待实现")
