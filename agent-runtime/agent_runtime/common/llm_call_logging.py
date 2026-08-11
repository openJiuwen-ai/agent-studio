# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""
LLM 调用日志 — 通过 callback framework 记录模型请求体和响应内容

使用 openjiuwen callback framework 的 LLM_INPUT / LLM_OUTPUT / LLM_CALL_ERROR 事件，
在模型调用前后打印请求体和响应内容，与旧版日志格式对齐。

特点：
- 自动覆盖所有 ModelClient（OpenAI / SiliconFlow / DeepSeek 等均触发相同事件）
- 依赖 SDK 公开的 callback 接口，升级更安全
- 模型请求体/响应内容/token 用量/延迟/tool_calls 为 INFO 级别，默认输出；错误日志为 ERROR 级别
- 错误回调无条件注册（始终可见）；input/output 回调仅在 WORKFLOW_LOG_LEVEL ≤ INFO 时注册（WARNING 下零开销）

日志格式示例：
    model call request data: {"model": "xxx", "stream": false, "messages": [...]}
    model call response data: 好的，已收到您的指令。
    model call token usage: {"input_tokens": 25, "output_tokens": 18, "total_tokens": 43, ...}
    model call latency: {"first_token_time": "0.15s", "total_latency": 1.23, ...}
"""

import json

from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.callback.events import LLMCallEvents
from openjiuwen.core.runner.callback.utils import get_callback_framework

# 标记是否已注册，避免重复注册
_registered: bool = False

# UsageMetadata 中所有有意义的字段（排除默认为 0 / "" 的哨兵值）
_USAGE_TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'total_tokens', 'cache_tokens')
_USAGE_COST_FIELDS = ('input_cost', 'output_cost', 'total_cost')
_USAGE_LATENCY_FIELDS = ('first_token_time', 'total_latency', 'request_start_time')
_USAGE_META_FIELDS = ('model_name', 'task_id')

# 日志级别数值映射
_LOG_LEVEL_MAP = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


def _is_llm_call_logging_enabled() -> bool:
    """检查是否注册 input/output 详情回调（仅控制详情，不含 error）。

    需同时满足两个条件：
    - MODEL_CALL_LOGGING_ENABLED=true（功能开关，默认关闭）；
    - WORKFLOW_LOG_LEVEL ≤ INFO（级别门控，WARNING 下省掉 json.dumps 开销）。

    错误回调不受此函数约束，始终注册。
    每次调用时新建 Settings 实例以读取最新环境变量（Settings 单例在 import 时
    缓存，无法感知运行期环境变量变更）。
    """
    from agent_runtime.common.config import LlmCallLoggingSettings, WorkflowLogSettings
    if not LlmCallLoggingSettings().enabled:
        return False
    configured_level = _LOG_LEVEL_MAP.get(WorkflowLogSettings().level.upper(), 20)
    return configured_level <= _LOG_LEVEL_MAP["INFO"]


def register_llm_call_logging_callbacks() -> None:
    """注册 LLM 调用日志回调。

    应在服务启动时调用（server.py lifespan 中）。

    注册策略分两档：
    - LLM_CALL_ERROR：无条件注册。错误回调仅在调用失败时触发，成功路径零开销；
      错误是低频高重要事件，应始终可见，不受 MODEL_CALL_LOGGING_ENABLED 开关与
      WORKFLOW_LOG_LEVEL 门控约束。
    - LLM_INPUT / LLM_OUTPUT：需 MODEL_CALL_LOGGING_ENABLED=true 且
      WORKFLOW_LOG_LEVEL ≤ INFO 才注册。开关默认关闭；门控用于在 WARNING/ERROR
      级别下省掉回调体里 json.dumps(完整 messages) 的开销。

    重复调用为幂等操作，不会重复注册。
    """
    global _registered
    if _registered:
        return

    fw = get_callback_framework()

    # 错误回调无条件注册：低频（仅出错时触发）、高重要，不应受级别门控
    @fw.on(LLMCallEvents.LLM_CALL_ERROR)
    async def _log_error(model_name=None, model_provider=None, error=None, **kwargs):
        """打印模型调用错误"""
        workflow_logger.error(
            "model call error, model=%s, provider=%s, is_stream=%s, error=%s",
            model_name or "unknown",
            model_provider or "unknown",
            kwargs.get("is_stream", False),
            error,
        )

    # 检查 WORKFLOW_LOG_LEVEL，INFO 及更细级别才注册 input/output 回调
    if not _is_llm_call_logging_enabled():
        _registered = True  # 标记为"已决定"，后续调用不再重复检查
        return

    @fw.on(LLMCallEvents.LLM_INPUT)
    async def _log_request(model_name=None, model_provider=None, messages=None,
                           tools=None, temperature=None, top_p=None,
                           max_tokens=None, **kwargs):
        """打印模型请求体"""
        params = kwargs.get("params")
        if params is not None:
            # trigger 携带完整 pre-send params 时，构造 wire-body 等效内容：
            # extra_body 解包到顶层，extra_headers 排除（属 HTTP 头非 body）。
            request_data = {k: v for k, v in params.items()
                            if k not in ("extra_headers", "extra_body")}
            extra_body = params.get("extra_body")
            if isinstance(extra_body, dict):
                request_data.update(extra_body)
            # model_provider 为元数据，不在 wire body 中，单独补充。
            if model_provider:
                request_data["model_provider"] = model_provider
        else:
            # trigger 未带 params 的路径（如直接使用 OpenAIModelClient 的非 studio 调用）。
            request_data = {}
            if model_name:
                request_data["model"] = model_name
            if model_provider:
                request_data["model_provider"] = model_provider
            request_data["stream"] = kwargs.get("is_stream", False)
            if temperature is not None:
                request_data["temperature"] = temperature
            if top_p is not None:
                request_data["top_p"] = top_p
            if max_tokens is not None:
                request_data["max_tokens"] = max_tokens
            # messages 已是 SDK _build_request_params() 转换后的 dict 格式
            if messages is not None:
                request_data["messages"] = messages
            if tools:
                request_data["tools"] = tools

            # 从 kwargs 中提取 SDK trigger 传递的额外参数（如 frequency_penalty、presence_penalty、stop 等）
            _extra_param_keys = ("frequency_penalty", "presence_penalty", "stop")
            for key in _extra_param_keys:
                val = kwargs.get(key)
                if val is not None:
                    request_data[key] = val

        try:
            request_json = json.dumps(request_data, ensure_ascii=False)
        except (TypeError, ValueError):
            request_json = str(request_data)

        workflow_logger.info("model call request data: %s", request_json)

    @fw.on(LLMCallEvents.LLM_OUTPUT)
    async def _log_response(model_name=None, model_provider=None, response=None,
                            usage=None, tool_calls=None, result=None, **kwargs):
        """打印模型响应日志

        非流式调用通过 response 参数传递内容；
        流式调用（SiliconFlow / InferenceAffinity 等）通过 result 参数传递。
        """
        # response（非流式）或 result（流式），优先 response
        output = response or result
        if output:
            workflow_logger.info("model call response data: %s", output)
        else:
            workflow_logger.info("model call response data: ")

        # token usage + cost
        if usage is not None:
            usage_dict = _extract_usage_dict(usage)
            if usage_dict:
                workflow_logger.info(
                    "model call token usage: %s",
                    json.dumps(usage_dict, ensure_ascii=False),
                )

            latency_dict = _extract_latency_dict(usage, model_name, model_provider,
                                                 kwargs.get("is_stream"))
            if latency_dict:
                workflow_logger.info(
                    "model call latency: %s",
                    json.dumps(latency_dict, ensure_ascii=False),
                )

        # tool_calls
        if tool_calls:
            tc_list = []
            for tc in tool_calls:
                tc_info = {
                    "id": getattr(tc, 'id', ''),
                    "name": getattr(tc, 'name', ''),
                }
                arguments = getattr(tc, 'arguments', '')
                if arguments:
                    tc_info["arguments"] = arguments
                tc_list.append(tc_info)
            workflow_logger.info(
                "model call tool_calls: %s",
                json.dumps(tc_list, ensure_ascii=False),
            )

    _registered = True
    workflow_logger.debug("LLM call logging callbacks registered via callback framework")


def reset_registration_state() -> None:
    """重置注册标志，使后续 register_llm_call_logging_callbacks() 重新执行注册逻辑。

    供测试在用例间清理模块级注册状态使用；生产代码不应调用。
    """
    global _registered
    _registered = False


def _extract_usage_dict(usage) -> dict:
    """从 UsageMetadata 提取 token 计数 + 费用字段

    跳过 None 值和默认零值（UsageMetadata 默认 input_tokens=0 等）。
    对于 token 计数字段，0 视为无意义默认值；对费用字段同理。
    """
    usage_dict = {}
    for field in _USAGE_TOKEN_FIELDS:
        val = getattr(usage, field, None)
        if val is not None and val != 0:
            usage_dict[field] = val
    for field in _USAGE_COST_FIELDS:
        val = getattr(usage, field, None)
        if val is not None and val != 0:
            usage_dict[field] = val
    return usage_dict


def _extract_latency_dict(usage, model_name: str | None = None,
                          model_provider: str | None = None,
                          is_stream: bool | None = None) -> dict:
    """从 UsageMetadata 提取延迟 + 元信息字段

    跳过 None 值、空字符串和零值（UsageMetadata 默认 total_latency=0.0 等）。
    """
    latency_dict = {}
    for field in _USAGE_LATENCY_FIELDS:
        val = getattr(usage, field, None)
        if val is not None and val != 0 and val != "":
            latency_dict[field] = val
    for field in _USAGE_META_FIELDS:
        val = getattr(usage, field, None)
        if val is not None and val != 0 and val != "":
            latency_dict[field] = val
    if model_name:
        latency_dict["model_name"] = model_name
    if model_provider:
        latency_dict["model_provider"] = model_provider
    if is_stream is not None:
        latency_dict["is_stream"] = is_stream
    return latency_dict
