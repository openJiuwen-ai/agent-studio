# -*- coding: UTF-8 -*-
"""团队对话事件 —— 事件构造 + SSE 序列化 + jiuwen chunk 转换（无状态纯函数）。

枚举/常量声明在 common/constants.py；请求级事件通道对象在 event/channel.py。
监督者与子 Agent 复用 adapt_stream_chunk：llm_output→message、llm_reasoning→reasoning、
llm_usage→usage、answer→final_text（tracer_agent 由子 Agent 循环单独处理，因需工具解析）。
"""

import json
from dataclasses import dataclass, field

from agent_runtime.supervisor.common.constants import OutputSchemaType, TeamEventField, TeamEventType


# ---------------------------------------------------------------- 事件构造

def _build_event(event_type: TeamEventType, execution_id: str, data: dict, index: int | None = None) -> dict:
    """组装标准事件结构：{event, data, executionId, index?}"""
    event = {
        TeamEventField.EVENT: event_type.value,
        TeamEventField.DATA: data,
        TeamEventField.EXECUTION_ID: execution_id,
    }
    if index is not None:
        event[TeamEventField.INDEX] = index
    return event


def build_user_message(execution_id: str, conversation_id: str, query: str, index: int | None = None) -> dict:
    return _build_event(TeamEventType.USER_MESSAGE, execution_id,
                        {TeamEventField.CONVERSATION_ID: conversation_id, TeamEventField.QUERY: query}, index)


def build_run_start(execution_id: str, index: int | None = None) -> dict:
    return _build_event(TeamEventType.RUN_START, execution_id, {}, index)


def build_message(execution_id: str, delta: str, agent_id: str | None = None,
                  sub_execution_id: str | None = None, index: int | None = None) -> dict:
    data = {TeamEventField.DELTA: delta}
    if agent_id is not None:
        data[TeamEventField.AGENT_ID] = agent_id
    if sub_execution_id is not None:
        data[TeamEventField.SUB_EXECUTION_ID] = sub_execution_id
    return _build_event(TeamEventType.MESSAGE, execution_id, data, index)


def build_reasoning(execution_id: str, content: str, agent_id: str | None = None,
                    sub_execution_id: str | None = None, index: int | None = None) -> dict:
    data = {TeamEventField.CONTENT: content}
    if agent_id is not None:
        data[TeamEventField.AGENT_ID] = agent_id
    if sub_execution_id is not None:
        data[TeamEventField.SUB_EXECUTION_ID] = sub_execution_id
    return _build_event(TeamEventType.REASONING, execution_id, data, index)


def build_tool_call(execution_id: str, tool_call_id: str, tool_name: str,
                    arguments: dict | None = None, agent_id: str | None = None,
                    sub_execution_id: str | None = None, index: int | None = None) -> dict:
    data = {
        TeamEventField.TOOL_CALL_ID: tool_call_id,
        TeamEventField.TOOL_NAME: tool_name,
    }
    if arguments is not None:
        data[TeamEventField.ARGUMENTS] = arguments
    if agent_id is not None:
        data[TeamEventField.AGENT_ID] = agent_id
    if sub_execution_id is not None:
        data[TeamEventField.SUB_EXECUTION_ID] = sub_execution_id
    return _build_event(TeamEventType.TOOL_CALL, execution_id, data, index)


def build_tool_result(execution_id: str, tool_call_id: str, tool_name: str,
                      result: str | None = None, agent_id: str | None = None,
                      sub_execution_id: str | None = None, index: int | None = None) -> dict:
    data = {
        TeamEventField.TOOL_CALL_ID: tool_call_id,
        TeamEventField.TOOL_NAME: tool_name,
    }
    if result is not None:
        data[TeamEventField.RESULT] = result
    if agent_id is not None:
        data[TeamEventField.AGENT_ID] = agent_id
    if sub_execution_id is not None:
        data[TeamEventField.SUB_EXECUTION_ID] = sub_execution_id
    return _build_event(TeamEventType.TOOL_RESULT, execution_id, data, index)


def build_sub_start(execution_id: str, sub_execution_id: str, agent_id: str, index: int | None = None) -> dict:
    return _build_event(TeamEventType.SUB_START, execution_id,
                        {TeamEventField.SUB_EXECUTION_ID: sub_execution_id, TeamEventField.AGENT_ID: agent_id}, index)


def build_sub_done(execution_id: str, sub_execution_id: str, agent_id: str, text: str,
                   index: int | None = None) -> dict:
    return _build_event(TeamEventType.SUB_DONE, execution_id,
                        {TeamEventField.SUB_EXECUTION_ID: sub_execution_id,
                         TeamEventField.AGENT_ID: agent_id, TeamEventField.TEXT: text}, index)


def build_run_done(execution_id: str, text: str, index: int | None = None) -> dict:
    return _build_event(TeamEventType.RUN_DONE, execution_id, {TeamEventField.TEXT: text}, index)


def build_usage(execution_id: str, input_tokens: int, output_tokens: int, total_tokens: int,
                latency_ms: int | None = None, agent_id: str | None = None, index: int | None = None) -> dict:
    data = {
        TeamEventField.INPUT_TOKENS: input_tokens,
        TeamEventField.OUTPUT_TOKENS: output_tokens,
        TeamEventField.TOTAL_TOKENS: total_tokens,
    }
    if latency_ms is not None:
        data[TeamEventField.LATENCY_MS] = latency_ms
    if agent_id is not None:
        data[TeamEventField.AGENT_ID] = agent_id
    return _build_event(TeamEventType.USAGE, execution_id, data, index)


def build_skill_activated(
    execution_id: str,
    skill_id: str,
    name: str,
    version_id: str,
    index: int | None = None,
) -> dict:
    return _build_event(TeamEventType.SKILL_ACTIVATED, execution_id, {
        TeamEventField.SKILL_ID: skill_id,
        TeamEventField.NAME: name,
        TeamEventField.VERSION_ID: version_id,
    }, index)


def build_error(execution_id: str, code: str | int, message: str, index: int | None = None) -> dict:
    return _build_event(TeamEventType.ERROR, execution_id,
                        {TeamEventField.CODE: code, TeamEventField.MESSAGE: message}, index)


# ---------------------------------------------------------------- SSE 序列化

def sse_line(event_dict: dict) -> str:
    """序列化为 SSE 一行：data: {json}\n\n（复用平台格式）"""
    return f"data: {json.dumps(event_dict, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------- chunk → 事件

@dataclass
class StreamCtx:
    """一次 stream 消费的上下文（监督者或某次子 Agent 执行）。

    agent_id 为 None 表示监督者（事件不带 agentId）；子 Agent 带 agent_id/sub_execution_id。
    answer_text（权威）优先于 accumulated_text（llm_output 累加兜底），保证 final_text 与 message 增量拼接一致。
    """

    execution_id: str
    agent_id: str | None = None
    sub_execution_id: str | None = None
    accumulated_text: str = field(default="", init=False)
    answer_text: str = field(default="", init=False)

    @property
    def final_text(self) -> str:
        return self.answer_text or self.accumulated_text


def adapt_stream_chunk(chunk, ctx: StreamCtx) -> list[dict]:
    """把 jiuwen OutputSchema 转成事件 dict 列表（监督者/子 Agent 共用）。

    llm_output → message、llm_reasoning → reasoning、llm_usage → usage、
    answer → final_text（result_type=error 转 error 事件）。tracer_agent 不在此处理
    （子 Agent 循环单独解析为工具事件）。
    """
    events = []
    chunk_type = getattr(chunk, "type", "")
    payload = getattr(chunk, "payload", {}) or {}

    if chunk_type == OutputSchemaType.LLM_OUTPUT.value:
        content = payload.get("content", "") or ""
        if content:
            ctx.accumulated_text += content
            events.append(build_message(ctx.execution_id, content, ctx.agent_id, ctx.sub_execution_id))
    elif chunk_type == OutputSchemaType.LLM_REASONING.value:
        content = payload.get("content", "") or ""
        if content:
            events.append(build_reasoning(ctx.execution_id, content, ctx.agent_id, ctx.sub_execution_id))
    elif chunk_type == OutputSchemaType.LLM_USAGE.value:
        usage = payload.get("usage_metadata", {}) or {}
        events.append(build_usage(
            ctx.execution_id,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=payload.get("total_latency_ms"),
            agent_id=ctx.agent_id,
        ))
    elif chunk_type == OutputSchemaType.ANSWER.value:
        if payload.get("result_type", "") == "error":
            events.append(build_error(ctx.execution_id, code=103004, message=str(payload.get("output", ""))))
        else:
            output_text = payload.get("output", "") or ""
            if output_text:
                ctx.answer_text = output_text
    return events
