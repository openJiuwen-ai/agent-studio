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
from typing import List

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.language_model.base import (
    LanguageModelInput,
    BaseChatModel,
)
from jiuwen.common.llm_service.messages import AIMessage
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
):
    total_time = 0.0
    start_time = time.time()
    reasoning_content = ""
    llm_output.update(dict(role="assistant", content="", latency=0.0))
    async for item in result:
        total_time += (
            (time.time() - start_time) if (time.time() - start_time) > 0 else 0.0
        )
        if isinstance(item, AIMessage):
            if item.usage_metadata.finish_reason in [
                "stop",
                "function_call",
            ]:  # only process last message
                reasoning_content = process_finish_item(
                    item, llm_output, model_stat, model_usage, reasoning_content
                )
            else:
                if item.content:
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


def process_finish_item(item, llm_output, model_stat, model_usage, reasoning_content):
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
    await trace_manager.on_llm_end(output_on_insights)
