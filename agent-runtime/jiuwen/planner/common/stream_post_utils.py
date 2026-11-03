#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""
@Copyright: Copyright (C) 2023-2023 Huawei Inc
@Project:
@Author: jiuwen planner
@Date: 2024-05-15
@LastEditTime: 2024-05-15 14:54:38
@Description: stream post
"""

import copy
import json
import time
from datetime import datetime
from typing import List, Optional

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.language_model.base import (
    LanguageModelInput,
    BaseChatModel,
)
from jiuwen.common.llm_service.messages import AIMessage, UsageMetadata
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import format_exception_reason
from jiuwen.insight.manager import TraceManager
from jiuwen.planner.common.plan_constants import LlmOutput, FunctionCallSchema

LATENCY = "latency"
MODEL_LATENCY = "model_latency"
TOTAL_LATENCY = "total_latency"
WAIT_LATENCY = "wait_latency"
CONTENT = "content"
MODEL_STAT = "model_stat"
MODEL_USAGE = "model_usage"
USAGE_METADATA = "usage_metadata"
FINISH_REASON = "finish_reason"


def _iso_delta_ms(end_iso: str, start_iso: str) -> Optional[float]:
    """两个 ISO 时间戳的毫秒差；缺失或解析失败返回 None（不抛错）"""
    if not end_iso or not start_iso:
        return None
    try:
        delta = datetime.fromisoformat(end_iso) - datetime.fromisoformat(start_iso)
    except (ValueError, TypeError):
        return None
    return delta.total_seconds() * 1000.0


def build_usage_metadata(
    usage: Optional[UsageMetadata], tpot_ms: Optional[float] = None
) -> dict:
    """构造 openjiuwen core OTel handler 约定键名的 usage_metadata 载荷。

    handler（OtelAgentHandler._set_llm_response_attrs）只认这些扁平键：
    token/成本键在载荷存在时无条件落属性、缺键由 or 0/"" 兜底；first_token_time
    按 str() 后 float() 解析（数值与数值串均可），直传 ISO 串会被 ValueError
    守卫跳过。TTFT 由模型层双时间戳（first_token_time/requests_start_time，
    ISO 串）换算，消费端 gen_ai.response.time_to_first_chunk 按 GenAI semconv
    为秒（double），故直接给出 float 秒值。

    构造器承诺不抛：发射点的求值位置（emit_trace_event 实参位、业务 try
    内、发射器尾部）形态各异，边界输入（usage_metadata 类型异常等）抛错
    会把遥测故障灌进业务分支——异常只告警并降级为空载荷（缺数据不注入）。
    """
    try:
        return _build_usage_metadata_impl(usage, tpot_ms)
    except Exception as e:
        logger.warning(
            f"build_usage_metadata failed, skip injection: {e}",
            simple_log="build_usage_metadata failed",
        )
        return {}


def _build_usage_metadata_impl(
    usage: Optional[UsageMetadata], tpot_ms: Optional[float] = None
) -> dict:
    has_tpot = tpot_ms is not None and tpot_ms > 0
    if usage is None:
        # finish 块缺失（如 finish_reason=length 截断、流提前结束）时无 usage，
        # 但 _format_yield_result 的掐表不依赖 finish 块：TPOT 可算即产出
        # 仅含时延键的载荷，不随 usage 缺席被静默丢弃
        if has_tpot:
            return {"inter_token_latency_ms": round(tpot_ms, 2)}
        return {}
    ttft_ms = _iso_delta_ms(usage.first_token_time, usage.requests_start_time)
    has_ttft = ttft_ms is not None and ttft_ms >= 0
    # 真实用量判活只看 token/成本字段：qwen 成功路径总会回填 model_name，
    # 若计入判活，上游缺 usage 字段（token 全 0）时仍会产出全零用量载荷，
    # 违背「缺数据路径不注入键」契约；model_name 仅在有真实用量时随带输出
    usage_signals = (
        usage.input_tokens,
        usage.output_tokens,
        usage.total_tokens,
        usage.cache_tokens,
        usage.reasoning_tokens,
        usage.input_cost,
        usage.output_cost,
        usage.total_cost,
    )
    has_usage = any(usage_signals)
    # 全空 usage（模型错误 / 未上报用量的默认构造）且无任何可算时延 → 视为
    # 缺数据：不产出全零载荷，维持「缺数据路径不注入键」契约。时延信号
    # 独立判活：token 未上报但时间戳在（model_wrapper 无条件打点）或掐表
    # 可算（tpot）时，仍产出仅含时延键的载荷，不虚构 token 键
    if not has_usage:
        if not has_ttft and not has_tpot:
            return {}
    usage_dict: dict = {}
    if has_usage:
        # total_tokens 一并输出：core handler 不消费该键（schema 透明、透传
        # 无害），但用量桥/insight 侧按 input+output 推 total 会与
        # model_usage.total_tokens 口径分裂——仅上报 total 的实现下甚至全零
        usage_dict = {
            "input_tokens": usage.input_tokens or 0,
            "output_tokens": usage.output_tokens or 0,
            "total_tokens": usage.total_tokens or 0,
            "model_name": usage.model_name or "",
            "total_cost": usage.total_cost or 0.0,
            "input_cost": usage.input_cost or 0.0,
            "output_cost": usage.output_cost or 0.0,
        }
        if usage.cache_tokens:
            usage_dict["cache_tokens"] = usage.cache_tokens
        if usage.reasoning_tokens:
            usage_dict["reasoning_tokens"] = usage.reasoning_tokens
    if has_ttft:
        # 毫秒差须 /1000 换算为秒值 float，否则 span 属性被放大 1000 倍
        usage_dict["first_token_time"] = round(ttft_ms / 1000, 6)
    if has_tpot:
        usage_dict["inter_token_latency_ms"] = round(tpot_ms, 2)
    return usage_dict


def build_finish_reason(usage: Optional[UsageMetadata]) -> str:
    """取 finish_reason；空值或占位值不产出（避免覆盖载荷已有键）"""
    if usage is None:
        return ""
    reason = usage.finish_reason or ""
    return "" if reason == "null" else reason


def build_llm_end_payload(
    content: str,
    usage_metadata: Optional[UsageMetadata],
    total_time: float,
    tpot_ms: Optional[float] = None,
) -> dict:
    """构造 on_llm_end 的 output_on_insights 载荷（含 OTel 双写键）。

    供无既有时延/用量链路的发射点（task_plan / task_understanding /
    PlanExecute StepExecute）复用：content/latency 与既有发射点形状一致，
    model_usage/usage_metadata/finish_reason 按 core handler 约定键名双写，
    缺数据不注入（与其它发射点同一契约）。

    与 build_usage_metadata 同一承诺：构造不抛。求值点常在业务 try 内
    （emit_trace_event 实参位），构造失败只降级为 content/latency 基础
    载荷，不把遥测故障灌进业务分支。content 契约允许
    List[Union[str, Dict]]，非 str 统一兜底为空串（不外泄畸形形态）。
    """
    safe_content = content if isinstance(content, str) else ""
    try:
        return _build_llm_end_payload_impl(safe_content, usage_metadata, total_time, tpot_ms)
    except Exception as e:
        logger.warning(
            f"build_llm_end_payload failed, degrade to base payload: {e}",
            simple_log="build_llm_end_payload failed",
        )
        return {"role": "assistant", "content": safe_content, LATENCY: {"total_latency": total_time}}


def _build_llm_end_payload_impl(
    content: str,
    usage_metadata: Optional[UsageMetadata],
    total_time: float,
    tpot_ms: Optional[float] = None,
) -> dict:
    output_on_insights: dict = {"role": "assistant", "content": content or ""}
    output_on_insights[LATENCY] = {"total_latency": total_time}
    has_tokens = usage_metadata is not None and any(
        (
            usage_metadata.input_tokens,
            usage_metadata.output_tokens,
            usage_metadata.total_tokens,
        )
    )
    if has_tokens:
        output_on_insights[MODEL_USAGE] = {
            "input_tokens": usage_metadata.input_tokens,
            "output_tokens": usage_metadata.output_tokens,
            "total_tokens": usage_metadata.total_tokens,
        }
    usage_dict = build_usage_metadata(usage_metadata, tpot_ms)
    if usage_dict:
        output_on_insights[USAGE_METADATA] = usage_dict
    finish_reason = build_finish_reason(usage_metadata)
    if finish_reason:
        output_on_insights[FINISH_REASON] = finish_reason
    return output_on_insights


def convert_ai_message_to_llm_output(llm_message: AIMessage) -> LlmOutput:
    """convert AIMessage to LLM output"""
    role = "assistant" if llm_message.type == "ai" else llm_message.type
    content = llm_message.content if isinstance(llm_message.content, str) else ""
    if not llm_message.tool_calls:
        return LlmOutput(role=role, content=content)

    if isinstance(llm_message.tool_calls, List):  # 适配生成多插件结果
        function_call_list = list()
        for item in llm_message.tool_calls:
            function_name = item.name
            if not function_name:
                continue
            function_call_item = FunctionCallSchema(name=function_name)
            try:
                arguments = json.dumps(item.args, ensure_ascii=False)
                function_call_item.arguments = arguments
                tool_call_id = item.id
                if tool_call_id:
                    function_call_item.tool_call_id = tool_call_id
                function_call_list.append(function_call_item)
                logger.info(
                    f"After invoke LLM, content is generated, function call list result = {function_call_item.dict()}"
                )
            except ValueError:
                logger.error("Failed to dump LLM generated function call's arguments")
        return LlmOutput(
            role=role, content=content, function_call_list=function_call_list
        )

    function_name = llm_message.tool_calls.name
    if not function_name:
        logger.info(
            f"After invoke LLM, No function call, Only content: {dict(content=content)}",
            simple_log="After invoke LLM, No function call",
        )
        return LlmOutput(role=role, content=content)

    function_call = FunctionCallSchema(name=function_name)
    try:
        arguments = json.dumps(llm_message.tool_calls.args, ensure_ascii=False)
        function_call.arguments = arguments
        tool_call_id = llm_message.tool_calls.id
        if tool_call_id:
            function_call.tool_call_id = tool_call_id
        logger.info(
            f"After invoke LLM, content is generated, function call result = {function_call.dict()}"
        )
    except ValueError:
        logger.error("Failed to dump LLM generated function call's arguments")
    return LlmOutput(role=role, content=content, function_call=function_call)


async def _format_yield_result(
    result,
    llm_output,
    time_dict,
    model_stat=None,
    model_usage=None,
    thinking_enabled=False,
    finish_usage=None,
):
    total_time = 0.0
    start_time = time.time()
    reasoning_content = ""
    first_chunk_elapsed = None  # 首内容块到达耗时（inter-token 起点）
    last_chunk_elapsed = None  # 末内容块到达耗时
    chunk_count = 0
    llm_output.update(dict(role="assistant", content="", latency=0.0))
    async for item in result:
        total_time += (
            (time.time() - start_time) if (time.time() - start_time) > 0 else 0.0
        )
        if isinstance(item, AIMessage):
            # usage_metadata 可为 None（AIMessage 声明 Optional；非逐块挂 usage
            # 的模型实现），此时按普通内容块处理，不得在判 finish 时解引用崩溃
            item_usage = getattr(item, "usage_metadata", None)
            if item_usage is not None and item_usage.finish_reason in [
                "stop",
                "function_call",
            ]:  # only process last message
                reasoning_content = process_finish_item(
                    item,
                    llm_output,
                    model_stat,
                    model_usage,
                    reasoning_content,
                    finish_usage,
                )
            else:
                if item.content:
                    if first_chunk_elapsed is None:
                        first_chunk_elapsed = total_time
                    last_chunk_elapsed = total_time
                    chunk_count += 1
                    yield dict(role="assistant", content=item.content)
                if hasattr(item, "reasoning_content") and item.reasoning_content:
                    reasoning_content += item.reasoning_content
                    yield dict(role="assistant", think=item.reasoning_content)
        start_time = time.time()

    # thinking_enabled=True时，添加reason_content字段，允许为空
    if thinking_enabled:
        llm_output["reasoning_content"] = reasoning_content
    yield dict(llm_output=llm_output)
    time_dict.update(dict(total_latency=round(total_time, 2)))
    # inter-token（TPOT）：首末内容块间隔均值；单块/零块无意义不产出。
    # 掐表来自 time.time()（单位秒），×1000 换算后入 *_ms 键
    if isinstance(finish_usage, dict) and chunk_count > 1:
        if first_chunk_elapsed is not None and last_chunk_elapsed is not None:
            finish_usage["tpot_ms"] = (last_chunk_elapsed - first_chunk_elapsed) * 1000 / (
                chunk_count - 1
            )


def process_finish_item(
    item, llm_output, model_stat, model_usage, reasoning_content, finish_usage=None
):
    """Process finish item and update llm output with model stat and usage"""
    llm_output.update(
        convert_ai_message_to_llm_output(item).dict(exclude_defaults=True)
    )
    if isinstance(model_stat, dict):
        model_dict = {}
        try:
            model_dict = item.usage_metadata.model_stats
        except Exception:
            logger.error("Failed to get model stat dict")
        model_stat.update(model_dict)
        # 更新token消耗信息
        model_usage["input_tokens"] = item.usage_metadata.input_tokens
        model_usage["output_tokens"] = item.usage_metadata.output_tokens
        model_usage["total_tokens"] = item.usage_metadata.total_tokens
    # OTel 双写：暂存 finish 块的 usage_metadata，供发射点构造约定键名载荷
    if isinstance(finish_usage, dict):
        finish_usage["usage"] = item.usage_metadata
    if hasattr(item, "reasoning_content") and item.reasoning_content:
        reasoning_content += item.reasoning_content
    return reasoning_content


def _process_time_info_by_llm_output(llm_output, time_dict):
    if llm_output.get(LATENCY):
        time_dict[MODEL_LATENCY] = round(llm_output.get(LATENCY), 2)
        if time_dict.get(MODEL_LATENCY) > time_dict.get(TOTAL_LATENCY):
            time_dict[TOTAL_LATENCY] = time_dict.get(MODEL_LATENCY)
        time_dict[WAIT_LATENCY] = round(
            time_dict.get(TOTAL_LATENCY) - time_dict.get(MODEL_LATENCY), 2
        )
        time_dict[WAIT_LATENCY] = (
            0.0 if time_dict[WAIT_LATENCY] < 0.0 else time_dict[WAIT_LATENCY]
        )
    else:
        time_dict[MODEL_LATENCY] = None
        time_dict[WAIT_LATENCY] = None
    yield dict(time_consumption=time_dict)


def create_trace_manager(llm: BaseChatModel, functions, trace_handlers):
    """create trace manager"""
    model_class = type(llm).__name__
    model_name = llm.model_name if hasattr(llm, "model_name") else "undefined"

    return TraceManager.generate_manager(
        trace_handlers,
        {
            "class_name": model_class,
            "instance_attributes": dict(
                model=model_name,
                temperature=llm.temperature if hasattr(llm, "temperature") else 1.0,
                top_p=llm.top_p if hasattr(llm, "top_p") else 0.95,
                functions=functions,
            ),
        },
    )


def create_trace_manager_safely(llm: BaseChatModel, functions, trace_handlers):
    """create_trace_manager 的兜底版：初始化失败返回 None（遥测停用）。

    generate_manager 对非法 trace_handlers 形态可能抛错；plan/invoke 等
    业务路径原本没有遥测依赖，初始化异常外传会把遥测故障变成业务故障
    （规划重抛 / 理解兜底被跳过 / 步骤落入 error 分支）。失败只告警，
    配合 emit_trace_event 的 None 容忍静默停用事件发射。
    """
    try:
        return create_trace_manager(
            llm=llm, functions=functions, trace_handlers=trace_handlers
        )
    except Exception as e:
        logger.warning(
            f"trace manager init failed, telemetry disabled: {e}",
            simple_log="trace manager init failed",
        )
        return None


async def emit_trace_event(trace_manager, method_name, *args):
    """安全发射 TraceManager 事件：handler 异常不外传，manager 为 None 时跳过。

    insight 层 _trace_event 直接调用 handler(*args) 并传播异常、无兜底；
    遥测事件若与业务逻辑共用 try 块，任一 handler 抛错会把成功的 LLM 调用
    误判进业务失败分支（规划被重抛 / 理解兜底 is_complex=False / 步骤变
    error）。此处统一兜底：遥测失败只告警，不改变调用方业务语义；manager
    初始化失败（create_trace_manager_safely 返回 None）时事件直接跳过
    （初始化处已告警，不重复）。
    """
    if trace_manager is None:
        return
    try:
        await getattr(trace_manager, method_name)(*args)
    except Exception as e:
        logger.warning(
            f"trace event {method_name} emit failed: {e}",
            simple_log="trace event emit failed",
        )


def insert_contexts_before_user_query(contexts, messages):
    """insert contexts before user query"""
    insert_index = -1
    for index, item in enumerate(messages):
        if item.get("role", "") != "system":
            insert_index = index
            break
    if insert_index >= 0:
        user_msgs = contexts[0::2]
        assistant_msgs = contexts[1::2]
        contexts_msg = []
        for user, assistant in zip(user_msgs, assistant_msgs):
            contexts_msg.append(dict(role="user", content=user))
            contexts_msg.append(dict(role="assistant", content=assistant))
        return messages[:insert_index] + contexts_msg + messages[insert_index:]
    return messages


async def stream_function_call(
    messages: List[dict],
    functions,
    llm: BaseChatModel,
    contexts: List[str] = None,
    trace_handlers=None,
    **kwargs,
):
    """Get llm stream output with functions"""
    if contexts:
        messages = insert_contexts_before_user_query(contexts, messages)
    trace_manager = create_trace_manager(llm, functions, trace_handlers)
    await trace_manager.on_llm_start(messages)

    # Combined output dictionary to reduce local variables
    output_data_for_insights = {
        "llm_output": dict(),
        "time_dict": dict(),
        "model_stat": dict(),
        "model_usage": dict(),
        "finish_usage": dict(),
    }
    try:
        result = await llm.astream(
            LanguageModelInput(
                messages=ModelUtil.switch_message(messages), tools=functions
            ),
            **kwargs,
        )
        async for format_result in _format_yield_result(
            result,
            output_data_for_insights["llm_output"],
            output_data_for_insights["time_dict"],
            output_data_for_insights["model_stat"],
            output_data_for_insights["model_usage"],
            finish_usage=output_data_for_insights["finish_usage"],
        ):
            yield format_result

    except Exception as e:
        await trace_manager.on_llm_error(BaseException("stream function call error"))
        raise JiuWenBaseException(
            error_code=StatusCode.INVOKE_LLM_FAILED.value[0],
            message=format_exception_reason(e, reason="stream function call error"),
        ) from e
    for output in _process_time_info_by_llm_output(
        output_data_for_insights["llm_output"], output_data_for_insights["time_dict"]
    ):
        yield output

    # display output on insights, including timer info
    output_on_insights: dict = copy.deepcopy(output_data_for_insights["llm_output"])
    output_on_insights.update({LATENCY: output_data_for_insights["time_dict"]})
    output_on_insights.update({MODEL_STAT: output_data_for_insights["model_stat"]})
    output_on_insights.update({MODEL_USAGE: output_data_for_insights["model_usage"]})
    # OTel 双写：按 core handler 约定键名补用量/成本/时延（缺数据时为空，跳过注入）
    finish_usage = output_data_for_insights["finish_usage"]
    usage_dict = build_usage_metadata(
        finish_usage.get("usage"), finish_usage.get("tpot_ms")
    )
    if usage_dict:
        output_on_insights[USAGE_METADATA] = usage_dict
    finish_reason = build_finish_reason(finish_usage.get("usage"))
    if finish_reason:
        output_on_insights[FINISH_REASON] = finish_reason
    await trace_manager.on_llm_end(output_on_insights)
