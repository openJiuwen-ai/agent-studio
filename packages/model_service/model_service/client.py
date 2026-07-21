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

import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from openjiuwen.core.foundation.llm.model_clients.openai_model_client import OpenAIModelClient
from openjiuwen.core.runner.callback import trigger
from openjiuwen.core.runner.callback.events import LLMCallEvents

from . import authz, dispatch, policy, resolver


@dataclass
class _ResolveInputs:
    model_service_id: str
    auth_id: str
    workspace_id: str
    project_id: str
    refresh: bool


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
