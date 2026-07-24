# -*- coding: utf-8 -*-
"""``StudioModelClient``：注册为 openjiuwen ``client_provider="studio"``。

继承 ``OpenAIModelClient``，override ``invoke`` / ``stream``：内联 ``AsyncOpenAI`` 调用并复用
父类 ``_parse_response`` / ``_parse_stream_chunk`` / ``_astream_with_parser``（协议解析不重写）。
不委托 ``super().invoke()``，以避免单次 attempt 内重复触发 CALL 级事件与嵌套 SDK ``max_retries``；
failover 循环委托 ``policy.invoke_with_strategy``。当前仅支持 OPENAI 协议，ANTHROPIC 在 dispatch 预留。

``ModelClientConfig`` 入参形态：``client_provider="studio"``，``api_base`` / ``api_key`` 为占位
（``BaseModelClient._validate_config`` 要求非空），解析所需输入放 extra 字段
（``ModelClientConfig`` 设 ``extra="allow"``）：``model_service_id`` / ``auth_id`` / ``refresh``。
projectId 取自请求头（``authz.extract_project_id``），不放 config。
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from openai import AsyncOpenAI

from openjiuwen.core.foundation.llm.model_clients.openai_model_client import OpenAIModelClient
from openjiuwen.core.runner.callback import trigger
from openjiuwen.core.runner.callback.events import LLMCallEvents

from . import authz, dispatch, policy, resolver

logger = logging.getLogger(__name__)


@dataclass
class _ResolveInputs:
    model_service_id: str
    auth_id: str
    workspace_id: str
    project_id: str
    refresh: bool


@dataclass
class _VerbatimCall:
    """``_invoke_verbatim`` 的单次调用入参集合（G.FNM.03：参数过多且相关，具名封装）。"""

    params: dict
    stream: bool
    input_kwargs: dict
    output_parser: Any
    timeout: Any


# 非 OpenAI（非常规路径）端点判定与响应适配，供 ``StudioModelClient._invoke_verbatim`` 使用。


_OPENAI_VERSION_BASE_RE = re.compile(r"^/v\d+$")


def _is_verbatim_endpoint(api_url: str) -> bool:
    """判断 ``api_url`` 是否为「非 OpenAI 兼容」的 verbatim 端点。

    OpenAI SDK 调 ``chat.completions.create`` 时必在 ``base_url`` 后拼
    ``/chat/completions``；对只认 verbatim 路径的 mock / 自定义 HTTP 端点会 404 →
    ``NotFoundError``。判定走 URL path 形状（与 ``dispatch._normalize_api_base`` 同源约定）：

    - 末尾 ``/chat/completions``（完整 OpenAI 端点，SDK 重组装）→ False
    - 路径为空 / 根（裸 host base，SDK 拼）→ False
    - 路径形如 ``/v1`` ``/v2``（版本 base，SDK 拼）→ False
    - 其余（mock 非常规路径，如 ``/xxx/yyy``）→ True（走 httpx verbatim 直发）
    """
    path = urlparse((api_url or "").strip()).path.rstrip("/")
    if not path:
        return False
    if path.endswith("/chat/completions"):
        return False
    if _OPENAI_VERSION_BASE_RE.match(path):
        return False
    return True


def _build_verbatim_body(params: dict) -> dict:
    """由 ``_build_request_params`` 的 OpenAI 格式参数构造 httpx JSON body。

    剔除 SDK 专用的传输层键（``extra_headers`` / ``custom_headers`` / ``tracer_*``），
    把 ``extra_body`` 合并进 body 顶层（对齐 OpenAI SDK ``create()`` 的 ``extra_body`` 语义）。
    """
    body: dict = {}
    for key, value in params.items():
        if key.startswith("tracer_"):
            continue
        if key in ("extra_headers", "custom_headers"):
            continue
        body[key] = value
    extra_body = body.pop("extra_body", None)
    if isinstance(extra_body, dict):
        body.update(extra_body)
    return body


def _build_verbatim_headers(conn, params: dict) -> dict:
    """verbatim 分支鉴权头（对齐 agent_builder facade ``_auth_headers``）。

    ``API_KEY`` → ``Authorization: Bearer <api_key>``；``CUSTOM_APIKEY`` → ``auth_info`` 各项。
    再叠加 ``params`` 中携带的请求级 ``extra_headers`` / ``custom_headers``。
    """
    headers = {"Content-Type": "application/json"}
    if conn.custom_headers:
        headers.update(conn.custom_headers)
    else:
        headers["Authorization"] = f"Bearer {conn.api_key}"
    extra_headers = params.get("extra_headers")
    if isinstance(extra_headers, dict):
        headers.update(extra_headers)
    custom_headers = params.get("custom_headers")
    if isinstance(custom_headers, dict):
        headers.update(custom_headers)
    return headers


class _AttrDict:
    """把 httpx 返回的 OpenAI 格式 JSON dict 递归包成属性访问对象。

    使其能被 ``OpenAIModelClient._parse_response`` / ``_parse_stream_chunk`` 当作 SDK
    响应对象消费（它们按 ``response.choices[0].message`` / ``chunk.choices`` 等属性方式读取）。
    缺省行为对齐 SDK pydantic 模型：未出现的字段按 ``None`` 返回（``hasattr`` 恒真，真值由
    ``and`` 守卫），从而与父类解析逻辑无缝兼容。
    """

    __slots__ = ("_d",)

    def __init__(self, d: dict):
        object.__setattr__(self, "_d", d)

    def __getattr__(self, name):
        if name == "_d":                       # 避免构造期 slot 未就绪时的递归
            raise AttributeError(name)
        d = self._d
        return _wrap(d[name]) if isinstance(d, dict) and name in d else None

    def __bool__(self):
        return bool(self._d)

    def __getitem__(self, key):
        return _wrap(self._d[key])

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def model_dump(self):
        """对齐 pydantic ``model_dump``，供 ``_normalize_logprobs`` 取回原始 dict。"""
        return self._d


def _wrap(value: Any) -> Any:
    """递归把 dict → ``_AttrDict``、list → 元素逐个包装，标量原样返回。"""
    if isinstance(value, dict):
        return _AttrDict(value)
    if isinstance(value, list):
        return [_wrap(item) for item in value]
    return value


class StudioModelClient(OpenAIModelClient):
    """注册为 openjiuwen ``llm_studio``（``BaseModelClient.__init_subclass__`` 自动注册）。"""

    __client_name__ = "studio"
    __client_type__ = "llm"

    # 解析输入：取自 config extra 字段与请求头。

    def _resolve_inputs(self) -> _ResolveInputs:
        cfg = self.model_client_config
        model_service_id = getattr(cfg, "model_service_id", "") or ""
        auth_id = getattr(cfg, "auth_id", "") or ""
        refresh = bool(getattr(cfg, "refresh", False))
        headers = _request_headers()
        project_id = authz.extract_project_id(headers)
        workspace_id = (
            (headers.get("X-Workspace-Id") or headers.get("x-workspace-id") or "")
            if headers else ""
        )
        return _ResolveInputs(model_service_id, auth_id, workspace_id, project_id, refresh)

    # openjiuwen 入口

    async def invoke(self, messages, *, tools=None, temperature=None, top_p=None,
                     model=None, max_tokens=None, stop=None, output_parser=None,
                     timeout=None, **kwargs):
        inputs = self._resolve_inputs()
        strategy = await resolver.resolve_strategy(
            inputs.model_service_id, inputs.project_id, inputs.workspace_id, inputs.auth_id,
            refresh=inputs.refresh,
        )
        if strategy is None:
            raise resolver.ModelServiceError("MD_MODEL_SERVICE_NOT_PUBLISH",
                                             f"model service not found: {inputs.model_service_id}")
        audit = self._new_audit(strategy, inputs, stream=False)
        start = time.monotonic()
        try:
            result = await policy.invoke_with_strategy(
                strategy,
                lambda detail, stream: self._invoke_one_model(
                    detail, stream, messages,
                    tools=tools, temperature=temperature, top_p=top_p,
                    max_tokens=max_tokens, stop=stop, output_parser=output_parser,
                    timeout=timeout, **kwargs,
                ),
                stream=False,
                on_attempt=lambda d: self._apply_audit_detail(audit, d),
            )
            audit.status = "success"
            return result
        except Exception as e:
            audit.status = "fail"
            audit.reason = str(e)
            policy.alarm("LLM", inputs.model_service_id, str(e))
            raise
        finally:
            audit.duration_ms = int((time.monotonic() - start) * 1000)
            policy.record_audit(audit)

    async def stream(self, messages, *, tools=None, temperature=None, top_p=None,
                     model=None, max_tokens=None, stop=None, output_parser=None,
                     timeout=None, **kwargs):
        inputs = self._resolve_inputs()
        strategy = await resolver.resolve_strategy(
            inputs.model_service_id, inputs.project_id, inputs.workspace_id, inputs.auth_id,
            refresh=inputs.refresh,
        )
        if strategy is None:
            raise resolver.ModelServiceError("MD_MODEL_SERVICE_NOT_PUBLISH",
                                             f"model service not found: {inputs.model_service_id}")
        audit = self._new_audit(strategy, inputs, stream=True)
        start = time.monotonic()
        # invoke_with_strategy 返回解析后的 chunk 异步迭代器；连接级错误在 await create() 时抛出，
        # 可被 policy 循环 failover；流中途错误不重试（与 Java 一致）。
        chunk_iter = await policy.invoke_with_strategy(
            strategy,
            lambda detail, stream: self._invoke_one_model(
                detail, stream, messages,
                tools=tools, temperature=temperature, top_p=top_p,
                max_tokens=max_tokens, stop=stop, output_parser=output_parser,
                timeout=timeout, **kwargs,
            ),
            stream=True,
            on_attempt=lambda d: self._apply_audit_detail(audit, d),
        )
        try:
            async for chunk in chunk_iter:
                yield chunk
            audit.status = "success"
        except Exception as e:
            audit.status = "fail"
            audit.reason = str(e)
            policy.alarm("LLM", inputs.model_service_id, str(e))
            raise
        finally:
            audit.duration_ms = int((time.monotonic() - start) * 1000)
            policy.record_audit(audit)

    # 单模型单次实际调用，由 policy 每次 attempt 调用。

    async def _invoke_one_model(self, detail, stream, messages, *,
                                tools=None, temperature=None, top_p=None,
                                max_tokens=None, stop=None, output_parser=None,
                                timeout=None, **kwargs):
        """单模型单次调用：内联 openai SDK，复用父类解析，并手动触发 CALL 级事件。

        由于不委托 ``super().invoke()``，父类方法体内的 ``LLM_INPUT`` / ``LLM_OUTPUT`` /
        ``LLM_CALL_ERROR`` trigger 不会自动触发，依赖这些事件的订阅者（如 ``llm_call_logging``）
        会失效，故在此手动补回。同时把 ``frequency_penalty`` / ``presence_penalty`` / ``stop``
        等超参随 ``LLM_INPUT`` 传递（对应 issue #1198）。

        - ``_is_verbatim_endpoint(api_url)`` 为真（非 OpenAI 非常规路径端点）时转入
          ``_invoke_verbatim``：httpx 直发 ``api_url``，避免 SDK 强拼 ``/chat/completions`` 404。
        - stream=False：返回 AssistantMessage。
        - stream=True：返回解析后的 chunk 异步迭代器；连接错误在 await create() 时抛出（可 failover），
          流中途错误在 ``_parsed`` 内触发 ``LLM_CALL_ERROR``。
        """
        conn = dispatch.get_chat_connection(detail.model, detail.auth)
        params = self._build_request_params(
            messages=messages, tools=tools, temperature=temperature, top_p=top_p,
            model=conn.model_name, stop=stop, max_tokens=max_tokens, stream=stream, **kwargs,
        )
        if conn.custom_headers:
            params["extra_headers"] = conn.custom_headers
        # return_token_ids 需放入 body 供 vLLM（对应父类处理）。
        if "return_token_ids" in params:
            extra_body = dict(params.get("extra_body") or {})
            extra_body["return_token_ids"] = params.pop("return_token_ids")
            params["extra_body"] = extra_body

        # CALL 级事件公共参数；frequency_penalty / presence_penalty / stop 一并传递（对应 #1198）。
        _extra_event_kwargs = {
            k: params[k] for k in ("frequency_penalty", "presence_penalty", "stop")
            if params.get(k) is not None
        }
        _model_name = params.get("model")
        _provider = self.model_client_config.client_provider
        _input_kwargs = dict(
            model_name=_model_name, model_provider=_provider,
            messages=params.get("messages"), tools=params.get("tools"),
            temperature=params.get("temperature"), top_p=params.get("top_p"),
            max_tokens=params.get("max_tokens"), **_extra_event_kwargs,
        )

        # 非 OpenAI（非常规路径）端点：OpenAI SDK 会强拼 /chat/completions 导致 404，
        # 改走 httpx verbatim 直发 detail.model.api_url，复用父类 _parse_response / _parse_stream_chunk。
        if _is_verbatim_endpoint(detail.model.api_url):
            return await self._invoke_verbatim(
                detail, conn,
                _VerbatimCall(params, stream, _input_kwargs, output_parser, timeout),
            )

        client = AsyncOpenAI(
            api_key=conn.api_key,
            base_url=conn.api_base,
            http_client=dispatch.build_httpx_client(
                conn.api_base, conn.verify_ssl, self.model_client_config.ssl_cert),
            timeout=timeout if timeout is not None else conn.timeout,
            max_retries=0,   # 单层重试：failover 由 policy 循环负责，避免 SDK 嵌套重试
        )

        try:
            if stream:
                # 对应父类 stream 分支，补 include_usage。
                stream_options = params.get("stream_options")
                if isinstance(stream_options, dict):
                    stream_options.setdefault("include_usage", True)
                elif stream_options is None:
                    params["stream_options"] = {"include_usage": True}

                # 过滤掉 tracer 相关参数，OpenAI SDK 不认识这些参数，保证控制器执行
                openai_params = {k: v for k, v in params.items() if not k.startswith("tracer_")}

                await trigger(LLMCallEvents.LLM_INPUT, is_stream=True, **_input_kwargs, params=params)
                response_stream = await client.chat.completions.create(**openai_params)

                async def _parsed():
                    final_message = None
                    try:
                        if output_parser:
                            async for parsed in self._astream_with_parser(response_stream, output_parser):
                                final_message = parsed if final_message is None else final_message + parsed
                                yield parsed
                        else:
                            async for chunk in response_stream:
                                parsed = self._parse_stream_chunk(chunk)
                                if parsed:
                                    final_message = parsed if final_message is None else final_message + parsed
                                    yield parsed
                    except Exception as e:
                        await trigger(LLMCallEvents.LLM_CALL_ERROR, is_stream=True,
                                      model_name=_model_name, model_provider=_provider, error=e)
                        raise
                    else:
                        if final_message is not None:
                            await trigger(LLMCallEvents.LLM_OUTPUT, is_stream=True,
                                          model_name=_model_name, model_provider=_provider,
                                          response=final_message.content,
                                          usage=final_message.usage_metadata,
                                          tool_calls=final_message.tool_calls)
                    finally:
                        await client.close()
                return _parsed()
            else:
                # 过滤掉 tracer 相关参数，OpenAI SDK 不认识这些参数，保证控制器执行
                openai_params = {k: v for k, v in params.items() if not k.startswith("tracer_")}

                await trigger(LLMCallEvents.LLM_INPUT, is_stream=False, **_input_kwargs, params=params)
                response = await client.chat.completions.create(**openai_params)
                await client.close()
                assistant_message = await self._parse_response(response, output_parser)
                await trigger(LLMCallEvents.LLM_OUTPUT, is_stream=False,
                              model_name=_model_name, model_provider=_provider,
                              response=assistant_message.content,
                              usage=assistant_message.usage_metadata,
                              tool_calls=assistant_message.tool_calls)
                return assistant_message
        except Exception as e:
            # 覆盖非流 create/parse 失败与流 create 失败；流中途错误已在 _parsed 内触发。
            await client.close()
            await trigger(LLMCallEvents.LLM_CALL_ERROR, is_stream=stream,
                          model_name=_model_name, model_provider=_provider, error=e)
            raise

    async def _invoke_verbatim(self, detail, conn, call):
        """非 OpenAI 端点的 verbatim httpx 直发分支（复用父类响应解析）。

        ``_invoke_one_model`` 在 ``_is_verbatim_endpoint(detail.model.api_url)`` 为真时转入本分支：
        用 httpx 直接 POST 到 ``detail.model.api_url``（**不拼** ``/chat/completions``），请求体取
        ``_build_request_params`` 的 OpenAI 格式参数（``_build_verbatim_body``），鉴权头取
        ``_build_verbatim_headers``；响应 JSON 经 ``_wrap`` 包成属性访问对象后复用
        ``_parse_response`` / ``_parse_stream_chunk`` 解析。CALL 级事件触发与 SDK 分支一致。

        - stream=False：返回 AssistantMessage；非 2xx 抛 ``MD_INVOKE_MODEL_SERVICE_FAIL``。
        - stream=True：返回解析后的 chunk 异步迭代器（SSE ``data:`` 行逐帧解析）；连接 /
          状态码错误在 send 时抛出（可 failover），流中途错误在 ``_parsed`` 内触发 ``LLM_CALL_ERROR``。
        """
        params = call.params
        stream = call.stream
        input_kwargs = call.input_kwargs
        output_parser = call.output_parser
        timeout = call.timeout
        url = detail.model.api_url
        _model_name = input_kwargs["model_name"]
        _provider = input_kwargs["model_provider"]
        client = dispatch.build_httpx_client(
            url, conn.verify_ssl, self.model_client_config.ssl_cert)

        try:
            if stream:
                # 对齐父类 stream 分支：补 include_usage。
                stream_options = params.get("stream_options")
                if isinstance(stream_options, dict):
                    stream_options.setdefault("include_usage", True)
                elif stream_options is None:
                    params["stream_options"] = {"include_usage": True}

                headers = _build_verbatim_headers(conn, params)
                body = _build_verbatim_body(params)
                await trigger(LLMCallEvents.LLM_INPUT, is_stream=True,
                              **input_kwargs, params=params)
                req = client.build_request(
                    "POST", url, json=body, headers=headers,
                    timeout=timeout if timeout is not None else conn.timeout,
                )
                resp = await client.send(req, stream=True)
                if resp.status_code >= 300:
                    text = (await resp.aread()).decode("utf-8", "ignore")
                    await resp.aclose()
                    raise resolver.ModelServiceError(
                        "MD_INVOKE_MODEL_SERVICE_FAIL",
                        f"upstream {url} returned {resp.status_code}: {text}",
                    )

                async def _parsed():
                    final_message = None
                    try:
                        async for line in resp.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data_str = line[5:].strip()
                            if not data_str or data_str == "[DONE]":
                                continue
                            try:
                                chunk_dict = json.loads(data_str)
                            except json.JSONDecodeError:
                                # 单帧畸形数据不应中断整条 SSE 流，降级到 debug 并跳过该帧。
                                logger.debug("skip malformed SSE data chunk: %r",
                                             data_str[:120])
                                continue
                            parsed = self._parse_stream_chunk(_wrap(chunk_dict))
                            if parsed:
                                final_message = (
                                    parsed if final_message is None
                                    else final_message + parsed
                                )
                                yield parsed
                    except Exception as e:
                        await trigger(LLMCallEvents.LLM_CALL_ERROR, is_stream=True,
                                      model_name=_model_name, model_provider=_provider,
                                      error=e)
                        raise
                    else:
                        if final_message is not None:
                            await trigger(LLMCallEvents.LLM_OUTPUT, is_stream=True,
                                          model_name=_model_name, model_provider=_provider,
                                          response=final_message.content,
                                          usage=final_message.usage_metadata,
                                          tool_calls=final_message.tool_calls)
                    finally:
                        await resp.aclose()
                        await client.aclose()
                return _parsed()

            # 非流：httpx POST → 解析 JSON → _parse_response。
            headers = _build_verbatim_headers(conn, params)
            body = _build_verbatim_body(params)
            await trigger(LLMCallEvents.LLM_INPUT, is_stream=False,
                          **input_kwargs, params=params)
            resp = await client.post(
                url, json=body, headers=headers,
                timeout=timeout if timeout is not None else conn.timeout,
            )
            if resp.status_code >= 300:
                raise resolver.ModelServiceError(
                    "MD_INVOKE_MODEL_SERVICE_FAIL",
                    f"upstream {url} returned {resp.status_code}: {resp.text}",
                )
            data = resp.json()
            assistant_message = await self._parse_response(_wrap(data), output_parser)
            await client.aclose()
            await trigger(LLMCallEvents.LLM_OUTPUT, is_stream=False,
                          model_name=_model_name, model_provider=_provider,
                          response=assistant_message.content,
                          usage=assistant_message.usage_metadata,
                          tool_calls=assistant_message.tool_calls)
            return assistant_message
        except Exception as e:
            # 覆盖非流 post/parse/状态码失败与流 send/状态码失败；流中途错误已在 _parsed 内触发。
            await client.aclose()
            await trigger(LLMCallEvents.LLM_CALL_ERROR, is_stream=stream,
                          model_name=_model_name, model_provider=_provider, error=e)
            raise

    # 审计填充

    def _new_audit(self, strategy, inputs, *, stream: bool) -> policy.AuditLog:
        m = strategy.models[0].model
        return policy.AuditLog(
            model_id=m.id, model_name=m.model_name, api_url=m.api_url, stream=stream,
            status="fail", duration_ms=0,
            project_id=inputs.project_id,
            workspace_id=inputs.workspace_id,
            auth_id=strategy.models[0].auth.auth_id if strategy.models[0].auth else "",
            provider_id=m.provider_id,
        )

    @staticmethod
    def _apply_audit_detail(audit: "policy.AuditLog", detail) -> None:
        """``on_attempt`` 回调：把审计归因到本次实际调用的模型。

        ROUTER failover 时，若 m1 失败后 failover 到 m2 成功，原审计固定指向 ``models[0]``（m1）
        却记 success，丢失 failover 可观测性。每次 attempt 前按真实 detail 覆写 model / auth 字段：
        成功时指向命中模型，全部失败时指向最后尝试的模型。
        """
        m = detail.model
        audit.model_id = m.id
        audit.model_name = m.model_name
        audit.api_url = m.api_url
        audit.provider_id = m.provider_id
        if detail.auth:
            audit.auth_id = detail.auth.auth_id


def _request_headers() -> dict:
    """从请求上下文取请求头。

    经 ``ports.set_request_headers`` 由宿主注入：agent_runtime 注入其
    ``_request_ctx.get().headers``，agent_builder 注入其 ``request_context_bridge``。
    """
    from .ports import get_request_headers
    return get_request_headers()
